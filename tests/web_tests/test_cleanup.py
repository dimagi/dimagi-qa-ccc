import allure
import pytest
from pygments.lexers import data

from pages.web_pages.cchq_application_web_page import CCHQApplicationPage
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.cchq_messaging_web_page import MessagingPage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage

@allure.feature("MISC")
@allure.story("Delete all script generated apps")
@allure.tag("cleanup")
@allure.description("""
  Covered manual test cases:
  - MISC : Delete all script generated apps 
  """)


# Belt and braces on top of the app_list locator, which already limits this job to
# the timestamped throwaway copies - it matches only names containing "Learn App ["
# or "Delivery App [" AND a colon.
#
# That colon is the whole protection, and it is accidental. On 2026-08-08 this job
# deleted the long-lived tasking opportunity's apps because they were still named
# "Learn App [04/08/2026 : 15:37]", which matches. They have since been renamed to
# "[DO NOT DELETE] ... [Tasking Flow]", which no longer matches - but only because
# that name happens to contain no colon. Name a kept app "[Tasking : v2]" and it is
# back in scope.
#
# So the markers below are the explicit guard: whatever the locator returns, an app
# carrying one is never deleted. Matched anywhere in the name and case-insensitively,
# so nothing needs adding here when a new protected app is created.
#
# Connect stores apps by id, not name, so renaming an app to carry a marker changes
# nothing for the tests that use it.
PROTECTED_APP_MARKERS = (
    "[Master]",          # the Learn/Delivery masters every OLP run copies
    "[DO NOT DELETE]",   # the long-lived tasking opportunity's Learn/Deliver apps
)


def is_protected_app(app_name):
    """True if the name carries a protection marker anywhere in it.

    Marker-based on purpose: no per-app list to maintain, so a new
    "[DO NOT DELETE] ..." app is protected the moment it is named, with no code
    change. Case-insensitive because the marker gets typed by hand on HQ and
    "[MASTER]" is as likely as "[Master]"; substring rather than prefix so a marker
    still counts if someone puts it after the app name.
    """
    haystack = (app_name or "").casefold()
    return any(marker.casefold() in haystack for marker in PROTECTED_APP_MARKERS)


@pytest.mark.web
@pytest.mark.cleanup
def test_00_cleanup_applications(web_driver, test_data, config, settings):
    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    cchq_application_page = CCHQApplicationPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.dismiss_guide_popup()

    with allure.step("Delete all test generated applications"):
        app_names = cchq_home_page.get_all_application_name()
        protected, deleted = [], []
        for app in app_names:
            if app == '':
                print("no test app present")
                continue
            if is_protected_app(app):
                # Logged rather than skipped silently: a surprise deletion is much
                # harder to diagnose than a surprise survival.
                protected.append(app)
                print(f"PROTECTED - not deleting: {app}")
                continue
            cchq_home_page.open_application(app)
            cchq_application_page.delete_all_application(app)
            deleted.append(app)

        print(f"Cleanup summary: {len(deleted)} deleted, {len(protected)} protected")
        print(f"  protected: {protected}")
        print(f"  deleted:   {deleted}")

