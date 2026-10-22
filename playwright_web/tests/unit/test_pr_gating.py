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
