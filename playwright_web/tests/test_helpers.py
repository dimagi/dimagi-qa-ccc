from utils.helpers import LocatorLoader


def test_locator_loader_converts_xpath():
    loader = LocatorLoader()
    result = loader.get("cchq_home_page", "welcome_title")
    assert result == "xpath=//h1[@class='mb-3 mt-5']"


def test_locator_loader_converts_id():
    loader = LocatorLoader()
    result = loader.get("cchq_login_page", "cookie_accept_button")
    assert result == "#hs-eu-confirmation-button"


def test_locator_loader_preserves_format_placeholders():
    loader = LocatorLoader()
    result = loader.get("cchq_home_page", "app_link")
    assert result == "xpath=(//li/a[contains(., '{name}')])[1]"
    assert result.format(name="Learn App") == "xpath=(//li/a[contains(., 'Learn App')])[1]"
