import allure
import pytest
from pages.web_pages.cchq_home_web_page import HomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_programs_web_page import ConnectProgramsPage

@allure.feature("PM")
@allure.story("Verify details of program and the status of invited NMs, also check create/view opportunities")
@allure.tag("PM_5", "PM_6", "PM_7")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - PM_5 : Verify that the ‘Program Acceptance Funnel’ within a program card has all the necessary information in it
  - PM_6 : Confirm user is able to see the status of all the NMs that they invited
  - PM_7 : Verify that user is only able to create/view opportunities when at least one NM has accepted the invite 
  """)

@pytest.mark.web
def test_pm_6_verify_status_of_invited_nms_and_create_or_view_opportunities(web_driver, test_data, config):
    pm_5_data = test_data.get("PM_5")
    pm_6_data = test_data.get("PM_6")
    pm_7_data = test_data.get("PM_7")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = HomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    connect_programs_page = ConnectProgramsPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Change Organization and navigate to Programs"):
        connect_home_page.select_organization_from_list(pm_5_data["org_name"])
        connect_home_page.click_programs_in_sidebar()

    # PM_5
    with allure.step("Verify Program details present for the created Program"):
        connect_programs_page.verify_program_info_present_for_a_program(pm_5_data["program_name"])

    # PM_6
    with allure.step("Verify Network Managers Status present in Program"):
        connect_programs_page.navigate_n_verify_status_for_nms_in_program(pm_6_data["program_name"])

    # PM_7
    with allure.step("Verify Create and View Opportunity for accepted Network Manager"):
        connect_programs_page.verify_create_opportunity_in_accepted_nm_in_program(pm_7_data["program_name"], pm_7_data["network_manager"])
        connect_programs_page.verify_view_opportunities_in_accepted_nm_in_program(pm_7_data["program_name"], pm_7_data["network_manager"])
