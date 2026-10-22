"""Which of our scripts a commcare-connect PR is likely to break (QA agent, scenario A).

Reads the PR's unified diff and flags every locator in locators/web_locators.yaml
whose anchor - an element id, or a quoted literal in its XPath (button text, class,
data-bind, aria-label ...) - appears on a removed line and on no added line. Text
that moved or was reformatted in the same diff is not flagged. Each flagged
locator is traced to the page objects that read it and the tests that use those
pages, directly or through a flow.

It is a starting point for the agent, not a verdict: the agent still reads the
diff, confirms each hit, and looks for behaviour changes no locator captures.

    python -m utils.impact_check --pr 1406            # needs the gh CLI
    python -m utils.impact_check --diff connect.diff  # a saved `gh pr diff` output
    python -m utils.impact_check --pr 1406 --json
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PLAYWRIGHT_ROOT = Path(__file__).resolve().parents[1]
CONNECT_REPO = "dimagi/commcare-connect"
MIN_ANCHOR_LENGTH = 4
# Basenames too common to tie a changed Connect file to one page object on their own.
GENERIC_BASENAMES = {"views.py", "tables.py", "urls.py", "forms.py", "models.py", "filters.py", "__init__.py"}

_QUOTED = re.compile(r"'([^']*)'|\"([^\"]*)\"")
_PLACEHOLDER = re.compile(r"\{[^}]*\}")
_LOCATOR_GET = re.compile(r'locators\.get\(\s*"([a-z0-9_]+)"\s*,\s*"([a-z0-9_]+)"\s*\)')
_IMPORT = re.compile(r"^from (pages|flows)\.([a-z0-9_]+) import", re.MULTILINE)


@dataclass
class FileChange:
    path: str
    removed: list = field(default_factory=list)
    added: list = field(default_factory=list)


@dataclass
class LocatorHit:
    section: str
    key: str
    value: str
    anchor: str
    connect_file: str
    removed_line: str
    pages: list = field(default_factory=list)
    tests: list = field(default_factory=list)


def parse_diff(text):
    """Unified diff -> [FileChange] with the content of removed and added lines."""
    changes, current = [], None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            current = FileChange(path=line.split(" b/", 1)[-1])
            changes.append(current)
        elif current is None or line.startswith(("--- ", "+++ ")):
            continue
        elif line.startswith("-"):
            current.removed.append(line[1:])
        elif line.startswith("+"):
            current.added.append(line[1:])
    return changes


def locator_anchors(value):
    """Strings from a locator that must exist in Connect's HTML for it to match."""
    value = value.removeprefix("xpath=")
    if not value.startswith(("//", "(", ".//", "./")):
        candidates = [value]  # bare element id
    else:
        candidates = [single or double for single, double in _QUOTED.findall(value)]
    anchors = set()
    for candidate in candidates:
        # 'Learn {name}' -> 'Learn'; keep each fixed fragment around a format placeholder.
        for fragment in _PLACEHOLDER.split(candidate):
            fragment = fragment.strip()
            if len(fragment) >= MIN_ANCHOR_LENGTH:
                anchors.add(fragment)
    return anchors


def find_locator_hits(locators, changes):
    """Locators whose anchors vanish in the diff: on a removed line, on no added line."""
    added_text = "\n".join(line for change in changes for line in change.added)
    hits = []
    for section, entries in (locators or {}).items():
        for key, value in (entries or {}).items():
            if not isinstance(value, str):
                continue
            for anchor in sorted(locator_anchors(value)):
                if anchor in added_text:
                    continue
                removed_at = next(
                    ((change.path, line) for change in changes for line in change.removed if anchor in line), None
                )
                if removed_at:
                    hits.append(LocatorHit(section, key, value, anchor, removed_at[0], removed_at[1].strip()))
                    break
    return hits


def usage_index(root=PLAYWRIGHT_ROOT):
    """(section, key) -> page modules reading it; module -> tests importing it (directly or via a flow)."""
    locator_users = {}
    for path in sorted((root / "pages").glob("*.py")) + sorted((root / "flows").glob("*.py")):
        for section, key in _LOCATOR_GET.findall(path.read_text(encoding="utf-8")):
            locator_users.setdefault((section, key), set()).add(f"{path.parent.name}/{path.name}")

    flow_imports = {}
    for path in sorted((root / "flows").glob("*.py")):
        for package, module in _IMPORT.findall(path.read_text(encoding="utf-8")):
            flow_imports.setdefault(f"flows/{path.name}", set()).add(f"{package}/{module}.py")

    module_tests = {}
    for path in sorted((root / "tests").glob("test_*.py")):
        test = f"tests/{path.name}"
        for package, module in _IMPORT.findall(path.read_text(encoding="utf-8")):
            imported = f"{package}/{module}.py"
            module_tests.setdefault(imported, set()).add(test)
            for indirect in flow_imports.get(imported, ()):
                module_tests.setdefault(indirect, set()).add(test)
    return locator_users, module_tests


def find_doc_mentions(changes, root=PLAYWRIGHT_ROOT):
    """Page objects whose source names a changed Connect file (many cite the template or view they model)."""
    mentions = {}
    pages = {f"pages/{p.name}": p.read_text(encoding="utf-8") for p in sorted((root / "pages").glob("*.py"))}
    for change in changes:
        parts = change.path.split("/")
        needles = ["/".join(parts[-2:])] if len(parts) > 1 else []
        if parts[-1] not in GENERIC_BASENAMES:
            needles.append(parts[-1])
        for page, text in pages.items():
            if any(needle in text for needle in needles):
                mentions.setdefault(change.path, []).append(page)
    return mentions


def analyse(diff_text, root=PLAYWRIGHT_ROOT):
    changes = parse_diff(diff_text)
    with open(root / "locators" / "web_locators.yaml", encoding="utf-8") as f:
        locators = yaml.safe_load(f)
    locator_users, module_tests = usage_index(root)
    hits = find_locator_hits(locators, changes)
    for hit in hits:
        hit.pages = sorted(locator_users.get((hit.section, hit.key), ()))
        hit.tests = sorted({test for page in hit.pages for test in module_tests.get(page, ())})
    return {
        "changed_files": [change.path for change in changes],
        "locator_hits": [hit.__dict__ for hit in hits],
        "doc_mentions": find_doc_mentions(changes, root),
    }


def to_markdown(report, pr=None):
    title = f"Impact check for {CONNECT_REPO}#{pr}" if pr else "Impact check"
    lines = [f"## {title}", "", f"Changed Connect files: {len(report['changed_files'])}", ""]
    if report["locator_hits"]:
        lines += ["### Locators whose anchor disappears in the diff", "",
                  "| Locator | Anchor | Removed in | Pages | Tests |", "| --- | --- | --- | --- | --- |"]
        for hit in report["locator_hits"]:
            lines.append(
                f"| `{hit['section']}.{hit['key']}` | `{hit['anchor']}` | `{hit['connect_file']}` "
                f"| {', '.join(hit['pages']) or '-'} | {', '.join(hit['tests']) or '-'} |"
            )
    else:
        lines.append("No locator anchors disappear in this diff.")
    if report["doc_mentions"]:
        lines += ["", "### Page objects that cite a changed Connect file", ""]
        lines += [f"- `{path}`: {', '.join(pages)}" for path, pages in report["doc_mentions"].items()]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--pr", type=int, help=f"{CONNECT_REPO} PR number (diff fetched with gh)")
    source.add_argument("--diff", type=Path, help="path to a unified diff")
    parser.add_argument("--json", action="store_true", help="print JSON instead of markdown")
    args = parser.parse_args(argv)

    if args.pr:
        diff_text = subprocess.run(
            ["gh", "pr", "diff", str(args.pr), "--repo", CONNECT_REPO],
            check=True, capture_output=True, text=True, encoding="utf-8",
        ).stdout
    else:
        diff_text = args.diff.read_text(encoding="utf-8")

    report = analyse(diff_text)
    sys.stdout.write(json.dumps(report, indent=2) + "\n" if args.json else to_markdown(report, args.pr))


if __name__ == "__main__":
    main()
