import pytest

from utils import pr_gating

pytest_plugins = ["pytester"]


class _Marker:
    def __init__(self, name, *args, **kwargs):
        self.name, self.args, self.kwargs = name, args, kwargs


def test_marker_pr_reads_keyword_and_positional_forms():
    assert pr_gating.marker_pr(_Marker("pending_prod", pr=1406)) == 1406
    assert pr_gating.marker_pr(_Marker("replaced_by_pr", 1406)) == 1406
    assert pr_gating.marker_pr(_Marker("replaced_by_pr", "1583")) == 1583


def test_marker_pr_without_number_is_an_error():
    with pytest.raises(ValueError, match="needs a Connect PR number"):
        pr_gating.marker_pr(_Marker("pending_prod"))


def test_skip_reason_runs_copy_and_skips_original_once_pr_is_deployed():
    assert pr_gating.skip_reason({1406}, set(), deployed_prs={1406}) is None
    assert "is deployed" in pr_gating.skip_reason(set(), {1406}, deployed_prs={1406})


def test_skip_reason_runs_original_and_skips_copy_before_pr_is_deployed():
    assert "not in the deployed build" in pr_gating.skip_reason({1406}, set(), deployed_prs=set())
    assert pr_gating.skip_reason(set(), {1406}, deployed_prs=set()) is None


def test_skip_reason_copy_of_two_prs_needs_both_deployed():
    assert pr_gating.skip_reason({1406, 1583}, set(), deployed_prs={1406}) is not None
    assert pr_gating.skip_reason({1406, 1583}, set(), deployed_prs={1406, 1583}) is None


def test_parse_pr_list():
    assert pr_gating.parse_pr_list("1406, 1583,") == {1406, 1583}
    assert pr_gating.parse_pr_list("") == set()
    assert pr_gating.parse_pr_list(None) == set()


def _fake_github(prs, ancestors):
    """prs: {pr: (head_sha, merged, merge_sha)}; ancestors: shas contained in the deployed build."""

    def fetch(path):
        if "/pulls/" in path:
            head, merged, merge_sha = prs[int(path.rsplit("/", 1)[1])]
            return {"head": {"sha": head}, "merged": merged, "merge_commit_sha": merge_sha}
        base = path.rsplit("/", 1)[1].split("...")[0]
        return {"status": "ahead" if base in ancestors else "diverged"}

    return fetch


def test_pr_in_build_by_head_commit_for_unmerged_staging_branch():
    fetch = _fake_github({1406: ("head1", False, None)}, ancestors={"head1"})
    assert pr_gating.pr_in_build(1406, "deployed", fetch=fetch)


def test_pr_in_build_by_merge_commit_once_merged():
    fetch = _fake_github({1406: ("old-head", True, "merge1")}, ancestors={"merge1"})
    assert pr_gating.pr_in_build(1406, "deployed", fetch=fetch)


def test_pr_not_in_build():
    fetch = _fake_github({1406: ("head1", False, None)}, ancestors=set())
    assert not pr_gating.pr_in_build(1406, "deployed", fetch=fetch)


def test_resolve_prefers_explicit_pr_list_over_sha():
    def fetch(path):
        raise AssertionError("explicit --deployed-prs must not call GitHub")

    deployed, source = pr_gating.resolve_deployed_prs({1406}, "1406", "deployed", fetch=fetch)
    assert deployed == {1406} and source == "--deployed-prs"


def test_resolve_defaults_to_nothing_deployed():
    deployed, source = pr_gating.resolve_deployed_prs({1406}, None, None)
    assert deployed == set() and source.startswith("default")


def _fake_github_with_deployments(deployments, prs, contained):
    """deployments: {environment: [sha or (sha, latest_state), ...]} newest first (a bare sha
    means "success"); contained: {deployed_sha: shas in that build}."""
    calls = []
    by_id = {}
    listed = {}
    for environment, entries in deployments.items():
        listed[environment] = []
        for entry in entries:
            sha, state = (entry, "success") if isinstance(entry, str) else entry
            by_id[len(by_id) + 1] = state
            listed[environment].append({"id": len(by_id), "sha": sha})

    def fetch(path):
        calls.append(path)
        if "/statuses?" in path:
            state = by_id[int(path.split("/deployments/", 1)[1].split("/", 1)[0])]
            return [{"state": state}] if state else []
        if "/deployments?" in path:
            environment = path.split("environment=", 1)[1].split("&", 1)[0]
            return listed.get(environment, [])
        if "/pulls/" in path:
            head, merged, merge_sha = prs[int(path.rsplit("/", 1)[1])]
            return {"head": {"sha": head}, "merged": merged, "merge_commit_sha": merge_sha}
        base, deployed = path.rsplit("/", 1)[1].split("...")
        return {"status": "ahead" if base in contained.get(deployed, ()) else "diverged"}

    return fetch, calls


def test_latest_deployed_sha_maps_suite_env_to_deployment_environment():
    fetch, calls = _fake_github_with_deployments({"staging": ["stg1"], "production": ["prd1"]}, {}, {})
    assert pr_gating.latest_deployed_sha("stage", fetch=fetch) == "stg1"
    assert pr_gating.latest_deployed_sha("prod", fetch=fetch) == "prd1"
    assert "/deployments?environment=staging&" in calls[0]


def test_latest_deployed_sha_skips_failed_and_running_deploys():
    fetch, _ = _fake_github_with_deployments(
        {"staging": [("newest", "failure"), ("running", "in_progress"), ("no-status", None), "good", "older"]}, {}, {}
    )
    assert pr_gating.latest_deployed_sha("stage", fetch=fetch) == "good"


def test_latest_deployed_sha_without_a_successful_deployment_is_an_error():
    fetch, _ = _fake_github_with_deployments({"staging": [("only", "error")]}, {}, {})
    with pytest.raises(ValueError, match="no successful commcare-connect deployment to staging"):
        pr_gating.latest_deployed_sha("stage", fetch=fetch)
    fetch, _ = _fake_github_with_deployments({}, {}, {})
    with pytest.raises(ValueError, match="no successful commcare-connect deployment to staging"):
        pr_gating.latest_deployed_sha("stage", fetch=fetch)


def test_resolve_looks_up_the_latest_deployment_for_the_env():
    fetch, _ = _fake_github_with_deployments(
        {"staging": ["stg1"]},
        {1406: ("head1406", False, None), 1583: ("head1583", False, None)},
        {"stg1": {"head1406"}},
    )
    deployed, source = pr_gating.resolve_deployed_prs({1406, 1583}, test_env="stage", fetch=fetch)
    assert deployed == {1406}
    assert source == "latest staging deployment stg1"


def test_explicit_sha_wins_over_the_deployment_lookup():
    fetch, calls = _fake_github_with_deployments(
        {"staging": ["stg1"]}, {1406: ("head1406", False, None)}, {"manual": {"head1406"}}
    )
    deployed, source = pr_gating.resolve_deployed_prs({1406}, deployed_sha="manual", test_env="stage", fetch=fetch)
    assert deployed == {1406} and source == "deployed SHA manual"
    assert not any("/deployments" in call for call in calls)


SUITE = """
import pytest

@pytest.mark.replaced_by_pr(1406)
def test_original():
    pass

@pytest.mark.pending_prod(pr=1406)
def test_updated_copy():
    pass

def test_unrelated():
    pass
"""

GATING_CONFTEST = """
from utils import pr_gating

def pytest_addoption(parser):
    parser.addoption("--deployed-prs", default=None)
    parser.addoption("--deployed-sha", default=None)

def pytest_configure(config):
    config.addinivalue_line("markers", "pending_prod(pr): test")
    config.addinivalue_line("markers", "replaced_by_pr(pr): test")

def pytest_collection_modifyitems(config, items):
    pr_gating.select_tests(config, items)
"""


@pytest.fixture
def gated_suite(pytester, monkeypatch):
    monkeypatch.delenv("DEPLOYED_PRS", raising=False)
    monkeypatch.delenv("DEPLOYED_SHA", raising=False)
    pytester.makeconftest(GATING_CONFTEST)
    pytester.makepyfile(SUITE)
    return pytester


def test_suite_runs_originals_when_pr_not_deployed(gated_suite):
    result = gated_suite.runpytest_inprocess("-p", "no:playwright", "-rs")
    result.assert_outcomes(passed=2, skipped=1)
    result.stdout.fnmatch_lines(["*SKIPPED*pending_prod: Connect PR #1406 is not in the deployed build*"])


def test_suite_runs_copies_when_pr_deployed(gated_suite):
    result = gated_suite.runpytest_inprocess("-p", "no:playwright", "-rs", "--deployed-prs=1406")
    result.assert_outcomes(passed=2, skipped=1)
    result.stdout.fnmatch_lines(["*SKIPPED*replaced_by_pr: Connect PR #1406 is deployed*"])
