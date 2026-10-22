from utils import impact_check

DIFF = """\
diff --git a/commcare_connect/templates/opportunity/opportunities_list.html b/commcare_connect/templates/opportunity/opportunities_list.html
--- a/commcare_connect/templates/opportunity/opportunities_list.html
+++ b/commcare_connect/templates/opportunity/opportunities_list.html
@@ -1,4 +1,4 @@
-  <button id="add-opportunity">Add Opportunity</button>
+  <button id="create-opportunity">Create Opportunity</button>
-  <span class="badge status-active">Active</span>
+  <span class="badge status-active">Active</span>
diff --git a/commcare_connect/opportunity/views.py b/commcare_connect/opportunity/views.py
--- a/commcare_connect/opportunity/views.py
+++ b/commcare_connect/opportunity/views.py
@@ -10,1 +10,1 @@
-    paginate_by = 20
+    paginate_by = 50
"""

LOCATORS = """\
opp_list:
  add_button: "add-opportunity"
  add_by_text: "//button[normalize-space()='Add Opportunity']"
  status_badge: "//span[contains(@class,'status-active')]"
  row_by_name: "//tr[.//a[contains(., '{name}')]]"
"""

PAGE = '''\
"""Opportunity list. Derived from opportunities_list.html and opportunity/views.py."""
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class OppListPage:
    ADD = locators.get(
        "opp_list", "add_button"
    )
    BADGE = locators.get("opp_list", "status_badge")
'''


def _fake_suite(tmp_path):
    for folder in ("pages", "flows", "tests", "locators"):
        (tmp_path / folder).mkdir()
    (tmp_path / "locators" / "web_locators.yaml").write_text(LOCATORS)
    (tmp_path / "pages" / "opp_list_page.py").write_text(PAGE)
    (tmp_path / "flows" / "opp_flow.py").write_text("from pages.opp_list_page import OppListPage\n")
    (tmp_path / "tests" / "test_direct.py").write_text("from pages.opp_list_page import OppListPage\n")
    (tmp_path / "tests" / "test_via_flow.py").write_text("from flows.opp_flow import something\n")
    (tmp_path / "tests" / "test_unrelated.py").write_text("from pages.other_page import Other\n")
    return tmp_path


def test_parse_diff_collects_removed_and_added_lines_per_file():
    changes = impact_check.parse_diff(DIFF)
    assert [c.path for c in changes] == [
        "commcare_connect/templates/opportunity/opportunities_list.html",
        "commcare_connect/opportunity/views.py",
    ]
    assert changes[0].removed[0].strip() == '<button id="add-opportunity">Add Opportunity</button>'
    assert changes[1].added == ["    paginate_by = 50"]


def test_locator_anchors_for_ids_xpath_literals_and_placeholders():
    assert impact_check.locator_anchors("add-opportunity") == {"add-opportunity"}
    assert impact_check.locator_anchors("//button[normalize-space()='Add Opportunity']") == {"Add Opportunity"}
    assert impact_check.locator_anchors("//tr[.//a[contains(., 'Opportunity {name} details')]]") == {"Opportunity", "details"}
    assert impact_check.locator_anchors("//div[@id='x']") == set()  # too short to match reliably


def test_anchor_removed_and_not_readded_is_a_hit_but_moved_text_is_not():
    import yaml

    hits = impact_check.find_locator_hits(yaml.safe_load(LOCATORS), impact_check.parse_diff(DIFF))
    assert {(h.section, h.key) for h in hits} == {("opp_list", "add_button"), ("opp_list", "add_by_text")}
    assert all(h.connect_file.endswith("opportunities_list.html") for h in hits)


def test_analyse_traces_hits_to_pages_and_tests_including_through_flows(tmp_path):
    report = impact_check.analyse(DIFF, root=_fake_suite(tmp_path))
    by_key = {hit["key"]: hit for hit in report["locator_hits"]}

    assert by_key["add_button"]["pages"] == ["pages/opp_list_page.py"]
    assert by_key["add_button"]["tests"] == ["tests/test_direct.py", "tests/test_via_flow.py"]
    # Read by no page object: still reported, with nothing to trace.
    assert by_key["add_by_text"]["pages"] == [] and by_key["add_by_text"]["tests"] == []


def test_doc_mentions_match_template_name_and_dir_qualified_views_only(tmp_path):
    report = impact_check.analyse(DIFF, root=_fake_suite(tmp_path))
    assert report["doc_mentions"] == {
        "commcare_connect/templates/opportunity/opportunities_list.html": ["pages/opp_list_page.py"],
        "commcare_connect/opportunity/views.py": ["pages/opp_list_page.py"],
    }


def test_markdown_report_lists_hits(tmp_path):
    markdown = impact_check.to_markdown(impact_check.analyse(DIFF, root=_fake_suite(tmp_path)), pr=1406)
    assert "Impact check for dimagi/commcare-connect#1406" in markdown
    assert "`opp_list.add_button` | `add-opportunity`" in markdown


def test_runs_against_the_real_suite_without_hits_for_an_empty_diff():
    report = impact_check.analyse("")
    assert report == {"changed_files": [], "locator_hits": [], "doc_mentions": {}}
