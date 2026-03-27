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

@pytest.mark.web
@pytest.mark.cleanup
def test_00_cleanup_applications(web_driver, test_data, config, settings):
    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    cchq_application_page = CCHQApplicationPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_home_page.verify_home_page_title("Welcome")

    with allure.step("Delete all test generated applications"):
        app_names = cchq_home_page.get_all_application_name()
        for app in app_names:
            if app == '':
                print("no test app present")
            else:
                cchq_home_page.open_application(app)
                cchq_application_page.delete_all_application(app)

