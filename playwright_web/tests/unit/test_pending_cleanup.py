import textwrap

from utils import pending_cleanup

SOURCE = textwrap.dedent(
    '''\
    import pytest


    @pytest.mark.replaced_by_pr(1406)
    def test_dashboard(page):
        assert old_layout(page)


    @pytest.mark.pending_prod(pr=1406)
    def test_dashboard_pr1406(page):
        assert new_layout(page)


    @pytest.mark.pending_prod(pr=1406)
    def test_clear_data_menu(page):
        assert menu(page)


    @pytest.mark.pending_prod(pr=1583)
    def test_still_waiting(page):
        assert later(page)


    def test_untouched(page):
        assert True
    '''
)


def test_marked_prs_lists_every_pr_on_a_marker():
    assert pending_cleanup.marked_prs(SOURCE) == {1406, 1583}


def test_deployed_pr_deletes_original_releases_copy_and_renames_it():
    cleaned, changes = pending_cleanup.clean_source(SOURCE, deployed={1406})
    assert "old_layout" not in cleaned
    assert "replaced_by_pr" not in cleaned
    assert "def test_dashboard(page):\n    assert new_layout(page)" in cleaned
    assert "test_dashboard_pr1406" not in cleaned
    assert "def test_clear_data_menu" in cleaned and "pending_prod(pr=1406)" not in cleaned
    assert "@pytest.mark.pending_prod(pr=1583)\ndef test_still_waiting" in cleaned
    assert "def test_untouched" in cleaned
    assert "\n\n\n\n" not in cleaned
    compile(cleaned, "cleaned.py", "exec")
    assert any("deleted test_dashboard" in c for c in changes)
    assert any("renamed test_dashboard_pr1406 -> test_dashboard" in c for c in changes)


def test_nothing_deployed_changes_nothing():
    cleaned, changes = pending_cleanup.clean_source(SOURCE, deployed=set())
    assert cleaned == SOURCE and changes == []


def test_copy_waiting_on_a_second_pr_keeps_its_name_and_other_marker():
    source = textwrap.dedent(
        '''\
        import pytest


        @pytest.mark.pending_prod(pr=1406)
        @pytest.mark.pending_prod(pr=1583)
        def test_x_pr1406(page):
            pass
        '''
    )
    cleaned, _ = pending_cleanup.clean_source(source, deployed={1406})
    assert "pending_prod(pr=1406)" not in cleaned
    assert "@pytest.mark.pending_prod(pr=1583)\ndef test_x_pr1406(page):" in cleaned


def test_copy_is_not_renamed_onto_a_name_still_in_use():
    source = textwrap.dedent(
        '''\
        import pytest


        def test_x(page):
            pass


        @pytest.mark.pending_prod(pr=1406)
        def test_x_pr1406(page):
            pass
        '''
    )
    cleaned, _ = pending_cleanup.clean_source(source, deployed={1406})
    assert "def test_x_pr1406(page):" in cleaned and "pending_prod" not in cleaned


def test_crlf_files_stay_crlf():
    cleaned, _ = pending_cleanup.clean_source(SOURCE.replace("\n", "\r\n"), deployed={1406})
    assert "\r\n" in cleaned and "\n" not in cleaned.replace("\r\n", "")


def test_run_edits_files_and_reports_leftovers(tmp_path, monkeypatch):
    tests_dir = tmp_path / "playwright_web" / "tests"
    tests_dir.mkdir(parents=True)
    test_file = tests_dir / "test_dash.py"
    test_file.write_text(SOURCE, encoding="utf-8")
    locators = tmp_path / "web_locators.yaml"
    locators.write_text("page:\n  menu_pr1406: \"//x\"\n  other: \"//y\"\n", encoding="utf-8")
    pending = tmp_path / "test_plans" / "pending"
    pending.mkdir(parents=True)
    (pending / "connect-pr-1406.yaml").write_text("connect_pr: 1406\n", encoding="utf-8")
    monkeypatch.setattr(pending_cleanup, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pending_cleanup, "TEST_DIRS", [tests_dir])
    monkeypatch.setattr(pending_cleanup, "KEY_FILES", [locators])
    monkeypatch.setattr(pending_cleanup, "PENDING_DIR", pending)
    in_prod = {1406}
    monkeypatch.setattr(pending_cleanup.pr_gating, "pr_in_build", lambda pr, sha, **_: pr in in_prod)

    summary = pending_cleanup.run(deployed_sha="abc123def4567890")

    assert "#1406" in summary and "#1583" not in summary.splitlines()[0]
    assert "playwright_web/tests/test_dash.py" in summary
    assert "menu_pr1406" in summary and "other" not in summary
    assert "test_plans/pending/connect-pr-1406.yaml" in summary
    assert "old_layout" not in test_file.read_text(encoding="utf-8")


def test_run_dry_run_leaves_files_alone(tmp_path, monkeypatch):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_dash.py"
    test_file.write_text(SOURCE, encoding="utf-8")
    monkeypatch.setattr(pending_cleanup, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pending_cleanup, "TEST_DIRS", [tests_dir])
    monkeypatch.setattr(pending_cleanup, "KEY_FILES", [])
    monkeypatch.setattr(pending_cleanup, "PENDING_DIR", tmp_path / "pending")
    monkeypatch.setattr(pending_cleanup.pr_gating, "pr_in_build", lambda pr, sha, **_: True)

    assert "deleted test_dashboard" in pending_cleanup.run(deployed_sha="abc123def4567890", dry_run=True)
    assert test_file.read_text(encoding="utf-8") == SOURCE


def test_run_with_nothing_in_prod_returns_empty(tmp_path, monkeypatch):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_dash.py").write_text(SOURCE, encoding="utf-8")
    monkeypatch.setattr(pending_cleanup, "TEST_DIRS", [tests_dir])
    monkeypatch.setattr(pending_cleanup.pr_gating, "pr_in_build", lambda pr, sha, **_: False)
    assert pending_cleanup.run(deployed_sha="abc123def4567890") == ""
