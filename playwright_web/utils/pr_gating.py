"""Pick each Connect PR's tests by what is actually deployed.

The QA agent never edits a test in place when a commcare-connect PR changes
behaviour we already cover - the environment the suite runs against may not have
that PR yet. Instead:

  * the updated or new test carries   @pytest.mark.pending_prod(pr=<n>)
  * the original it replaces carries  @pytest.mark.replaced_by_pr(<n>)

and every run decides per PR: if PR <n>'s code is in the deployed build, run the
pending_prod tests and skip the replaced_by_pr originals; if not, the reverse.
The rule is the same on stage and prod - staging is often deployed from PR or
combined branches, so "staging has every change" is not a safe assumption.

Which PRs are deployed comes from, in order:

  1. --deployed-prs / DEPLOYED_PRS   explicit comma-separated PR numbers (manual runs)
  2. --deployed-sha / DEPLOYED_SHA   the deployed commcare-connect commit; each marked
                                     PR is checked against it through the GitHub API
  3. neither                         no PR counts as deployed: originals run, copies
                                     skip - the safe default, matching prod before a deploy
"""

import json
import os
import urllib.request

import pytest

CONNECT_REPO = "dimagi/commcare-connect"
PENDING_MARKER = "pending_prod"
REPLACED_MARKER = "replaced_by_pr"


def marker_pr(marker):
    """PR number from pending_prod(pr=<n>) or replaced_by_pr(<n>) / replaced_by_pr(pr=<n>)."""
    value = marker.kwargs.get("pr", marker.args[0] if marker.args else None)
    if value is None:
        raise ValueError(f"@pytest.mark.{marker.name} needs a Connect PR number, e.g. {marker.name}(pr=1406)")
    return int(value)


def skip_reason(pending_prs, replaced_prs, deployed_prs):
    """Why a test must be skipped for this build, or None to run it.

    pending_prs / replaced_prs are the PR numbers on the test's pending_prod /
    replaced_by_pr markers; deployed_prs is the set of PRs in the deployed build.
    """
    for pr in sorted(pending_prs):
        if pr not in deployed_prs:
            return f"pending_prod: Connect PR #{pr} is not in the deployed build"
    for pr in sorted(replaced_prs):
        if pr in deployed_prs:
            return f"replaced_by_pr: Connect PR #{pr} is deployed; its updated copy runs instead"
    return None


def parse_pr_list(raw):
    """'1406, 1583' -> {1406, 1583}; empty or None -> empty set."""
    if not raw:
        return set()
    return {int(part) for part in raw.replace(" ", "").split(",") if part}


def _github_get(path, token=None):
    request = urllib.request.Request(f"https://api.github.com{path}")
    request.add_header("Accept", "application/vnd.github+json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def pr_in_build(pr, deployed_sha, fetch=None, token=None):
    """True when PR's code is contained in deployed_sha.

    The PR counts as deployed when its head commit - or, once merged, its merge
    commit - is an ancestor of (or equal to) the deployed commit. Connect merges
    with merge commits, so either check works for a merged PR; the head check also
    covers PR and combined branches deployed to staging before merge.
    """
    fetch = fetch or (lambda path: _github_get(path, token))
    details = fetch(f"/repos/{CONNECT_REPO}/pulls/{pr}")
    candidates = [details["head"]["sha"]]
    if details.get("merged") and details.get("merge_commit_sha"):
        candidates.append(details["merge_commit_sha"])
    for sha in candidates:
        comparison = fetch(f"/repos/{CONNECT_REPO}/compare/{sha}...{deployed_sha}")
        if comparison["status"] in ("ahead", "identical"):
            return True
    return False


def resolve_deployed_prs(marked_prs, deployed_prs_option=None, deployed_sha=None, fetch=None, token=None):
    """Return (deployed PR set, human-readable source) for the PRs the suite marks."""
    if deployed_prs_option:
        return parse_pr_list(deployed_prs_option), "--deployed-prs"
    if deployed_sha:
        deployed = {pr for pr in marked_prs if pr_in_build(pr, deployed_sha, fetch=fetch, token=token)}
        return deployed, f"deployed SHA {deployed_sha[:12]}"
    return set(), "default (no deployed SHA given: every marked PR treated as not deployed)"


def env_or_option(config, option, env_var):
    return config.getoption(option) or os.environ.get(env_var) or None


def select_tests(config, items, fetch=None):
    """pytest_collection_modifyitems body: add a skip to every test the deployed build rules out."""
    marked = []
    for item in items:
        pending = {marker_pr(m) for m in item.iter_markers(PENDING_MARKER)}
        replaced = {marker_pr(m) for m in item.iter_markers(REPLACED_MARKER)}
        if pending or replaced:
            marked.append((item, pending, replaced))
    if not marked:
        return

    marked_prs = set().union(*(pending | replaced for _, pending, replaced in marked))
    try:
        deployed, source = resolve_deployed_prs(
            marked_prs,
            deployed_prs_option=env_or_option(config, "--deployed-prs", "DEPLOYED_PRS"),
            deployed_sha=env_or_option(config, "--deployed-sha", "DEPLOYED_SHA"),
            fetch=fetch,
            token=os.environ.get("GITHUB_TOKEN"),
        )
    except Exception as exc:
        # Fail loudly: silently running the wrong copy of a test would hide real regressions.
        raise pytest.UsageError(f"Could not work out which Connect PRs are deployed: {exc}") from exc

    config._pr_gating_summary = (
        f"Connect PR gating ({source}): marked PRs {sorted(marked_prs)}, deployed {sorted(deployed & marked_prs)}"
    )
    for item, pending, replaced in marked:
        reason = skip_reason(pending, replaced, deployed)
        if reason:
            item.add_marker(pytest.mark.skip(reason=reason))
