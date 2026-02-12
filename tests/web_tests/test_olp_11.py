import allure
import pytest
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage

@allure.feature("OLP")
@allure.story("Verify user can filter the opportunities based on the status")
@allure.tag("OLP_11")
@allure.description("""
  Covered manual test cases:
  - OLP_11 : Verify user can filter the opportunities based on the status
  """)

@pytest.mark.web
# @pytest.mark.bugasura("TES85")
def test_olp_11_apply_n_verify_filters_in_opportunities(web_driver, test_data, config, settings):
    olp11_data = test_data.get("OLP_11")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    connect_opp_page = ConnectOpportunitiesPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()
        if 'staging' in config.get("cchq_url"):
            connect_home_page.select_organization_from_list("PM_Automation_01")
        else:
            connect_home_page.select_organization_from_list("dg_connect")

        if 'staging' in config.get("cchq_url"):
            connect_home_page.select_organization_from_list(olp11_data["org_name_staging"])
        else:
            connect_home_page.select_organization_from_list(olp11_data["org_name"])

    with allure.step("Apply filter for Opportunities as Active"):
        connect_opp_page.apply_n_verify_filter_as_active_in_opportunities()

    with allure.step("Apply filter for Opportunities as Ended"):
        connect_opp_page.apply_n_verify_filter_as_ended_in_opportunities()

    with allure.step("Apply filter for Opportunities as Inactive"):
        connect_opp_page.apply_n_verify_filter_as_inactive_in_opportunities()