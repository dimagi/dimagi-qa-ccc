"""Release pending_prod tests once their commcare-connect PR is on prod.

The QA agent never edits a test in place for a Connect PR: the updated or new test
is marked @pytest.mark.pending_prod(pr=<n>) and the original it replaces
@pytest.mark.replaced_by_pr(<n>) (see utils/pr_gating.py). Once PR <n> is in the
production deployment, prod runs the copies for good, so the pair can be collapsed:

  * tests marked replaced_by_pr(<n>) are deleted
  * pending_prod(pr=<n>) markers are removed; a copy named <name>_pr<n> whose
    original is gone, and that waits on no other PR, is renamed back to <name>

Locator and test-data keys with a _pr<n> suffix, and test_plans/pending files, are
only listed in the summary: renaming keys safely needs a person, and the pending
files are moved into the master plans by the skill's finalize mode after QA tests.

Usage (from playwright_web/):
    python -m utils.pending_cleanup [--deployed-sha SHA] [--dry-run] [--summary FILE]
"""

import argparse
import ast
import os
import re
import sys
from pathlib import Path

from utils import pr_gating

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DIRS = [REPO_ROOT / "playwright_web" / "tests", REPO_ROOT / "tests"]
KEY_FILES = [REPO_ROOT / "playwright_web" / "locators" / "web_locators.yaml", REPO_ROOT / "test_data" / "web_test_data.yaml"]
PENDING_DIR = REPO_ROOT / "test_plans" / "pending"
MARKERS = (pr_gating.PENDING_MARKER, pr_gating.REPLACED_MARKER)


def _marker_decorator(decorator):
    """(marker name, PR) for @pytest.mark.<pending_prod|replaced_by_pr>(...), else None."""
    if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
        return None
    name = decorator.func.attr
    owner = decorator.func.value
    if name not in MARKERS or not (isinstance(owner, ast.Attribute) and owner.attr == "mark"):
        return None
    value = next((kw.value for kw in decorator.keywords if kw.arg == "pr"), decorator.args[0] if decorator.args else None)
    if not isinstance(value, ast.Constant):
        raise ValueError(f"line {decorator.lineno}: {name} needs a literal PR number")
    return name, int(value.value)


def marked_tests(source):
    """Every test function carrying a gating marker, as dicts (name, node, markers)."""
    tests = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            markers = [(d, m) for d in node.decorator_list if (m := _marker_decorator(d))]
            if markers:
                tests.append({"name": node.name, "node": node, "markers": markers})
    return tests


def marked_prs(source):
    return {pr for test in marked_tests(source) for _, (_, pr) in test["markers"]}


def clean_source(source, deployed):
    """Return (new source, list of change descriptions) for the deployed PR set."""
    lines = source.splitlines(keepends=True)
    tests = marked_tests(source)
    defined = {n.name for n in ast.walk(ast.parse(source)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    deleted, edits, changes = set(), [], []  # edits: (start, end, replacement lines) on 1-based line ranges

    for test in tests:
        node = test["node"]
        if any(name == pr_gating.REPLACED_MARKER and pr in deployed for _, (name, pr) in test["markers"]):
            start = min(d.lineno for d in node.decorator_list)
            edits.append((start, node.end_lineno, []))
            deleted.add(node.name)
            changes.append(f"deleted {node.name} (replaced_by_pr, PR in prod)")

    for test in tests:
        node = test["node"]
        if node.name in deleted:
            continue
        released = [(d, pr) for d, (name, pr) in test["markers"] if name == pr_gating.PENDING_MARKER and pr in deployed]
        for decorator, pr in released:
            edits.append((decorator.lineno, decorator.end_lineno, []))
            changes.append(f"{node.name}: removed pending_prod(pr={pr})")
        still_pending = [pr for _, (name, pr) in test["markers"] if name == pr_gating.PENDING_MARKER and pr not in deployed]
        match = re.fullmatch(r"(.+)_pr(\d+)", node.name)
        if released and match and not still_pending:
            base = match.group(1)
            if base not in defined or base in deleted:
                def_line = node.lineno
                text = lines[def_line - 1]
                edits.append((def_line, def_line, [text.replace(f"def {node.name}(", f"def {base}(", 1)]))
                changes.append(f"renamed {node.name} -> {base}")

    for start, end, replacement in sorted(edits, key=lambda edit: edit[0], reverse=True):
        lines[start - 1:end] = replacement
    cleaned = re.sub(r"\n{4,}", "\n\n\n", "".join(lines).replace("\r\n", "\n"))
    if "\r\n" in source:
        cleaned = cleaned.replace("\n", "\r\n")
    return cleaned, changes


def leftover_keys(prs):
    """Locator / test-data keys ending in _pr<n> for the released PRs, for a person to tidy."""
    found = []
    for path in KEY_FILES:
        if not path.exists():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            key = re.match(r"\s*([A-Za-z0-9_]+_pr(\d+))\s*:", line)
            if key and int(key.group(2)) in prs:
                found.append(f"{path.relative_to(REPO_ROOT).as_posix()}:{number} {key.group(1)}")
    return found


def run(deployed_sha=None, dry_run=False, fetch=None, token=None):
    """Clean every test file; return a markdown summary ('' when nothing was in prod)."""
    files = [p for d in TEST_DIRS if d.exists() for p in sorted(d.rglob("test_*.py"))]
    # Only files that mention a marker are parsed, so an unrelated file that doesn't
    # parse (tests/web_tests/test_cleanup.py today) can't stop the clean-up.
    sources = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in MARKERS):
            sources[path] = text
    all_prs = set().union(*(marked_prs(source) for source in sources.values())) if sources else set()
    if not all_prs:
        return ""
    if not deployed_sha:
        deployed_sha = pr_gating.latest_deployed_sha("prod", fetch=fetch, token=token)
    deployed = {pr for pr in all_prs if pr_gating.pr_in_build(pr, deployed_sha, fetch=fetch, token=token)}
    if not deployed:
        return ""

    lines = [f"Connect PRs now in the production deployment ({deployed_sha[:12]}): "
             + ", ".join(f"#{pr}" for pr in sorted(deployed)), "", "### Test changes"]
    for path, source in sources.items():
        cleaned, changes = clean_source(source, deployed)
        if changes:
            if not dry_run:
                path.write_bytes(cleaned.encode("utf-8"))
            lines.append(f"- `{path.relative_to(REPO_ROOT).as_posix()}`")
            lines.extend(f"  - {change}" for change in changes)

    keys = leftover_keys(deployed)
    lines += ["", "### Left for a person"]
    if keys:
        lines.append("Keys with a `_pr<n>` suffix for these PRs; rename or delete them once nothing uses the old ones:")
        lines.extend(f"- `{key}`" for key in keys)
    pending = [p for pr in sorted(deployed) if (p := PENDING_DIR / f"connect-pr-{pr}.yaml").exists()]
    if pending:
        lines.append("Pending test plans to move into the master plans with the skill's finalize mode once QA has tested them:")
        lines.extend(f"- `{p.relative_to(REPO_ROOT).as_posix()}`" for p in pending)
    if not keys and not pending:
        lines.append("Nothing.")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--deployed-sha", help="production commcare-connect commit (default: latest successful deployment)")
    parser.add_argument("--dry-run", action="store_true", help="report without editing files")
    parser.add_argument("--summary", help="also write the markdown summary to this file")
    args = parser.parse_args()
    summary = run(deployed_sha=args.deployed_sha, dry_run=args.dry_run, token=os.environ.get("GITHUB_TOKEN"))
    print(summary or "No pending_prod / replaced_by_pr tests belong to a PR that is in prod.")
    if args.summary:
        Path(args.summary).write_text(summary, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
