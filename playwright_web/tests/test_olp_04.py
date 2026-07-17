from pages.cchq_home_page import CCHQHomePage
from pages.cchq_login_page import LoginPage
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunities_page import ConnectOpportunitiesPage
from pages.connect_opportunity_dashboard_page import OpportunityDashboardPage


def test_olp_04_verify_opportunity_details_in_dashboard(page, test_data, config, settings):
    olp4_data = test_data.get("OLP_4")

    cchq_login_page = LoginPage(page)
    cchq_home_page = CCHQHomePage(page)

    cchq_login_page.valid_login_cchq(config, settings)
    cchq_home_page.verify_home_page_title("Welcome")

    connect_page = cchq_login_page.navigate_to_connect_page(config)
    connect_home_page = ConnectHomePage(connect_page)
    connect_opp_page = ConnectOpportunitiesPage(connect_page)
    opp_dashboard_page = OpportunityDashboardPage(connect_page)

    connect_home_page.signin_to_connect_page_using_cchq()
    connect_home_page.select_organization_from_list("PM_Automation_01")

    connect_opp_page.click_opportunity_in_opportunity(olp4_data["opportunity_name"])
    opp_dashboard_page.navigate_to_opportunity_and_verify_all_fields_present_in_connect(olp4_data)
