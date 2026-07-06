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


from utils.helpers import ConfigLoader, SettingsLoader, TestDataLoader


def test_config_loader_defaults_to_prod():
    config = ConfigLoader(env=None)
    assert config.env == "prod"
    assert config.get("cchq_url") == "https://www.commcarehq.org/a/connectqa-automation-prod/login/"


def test_config_loader_stage_env():
    config = ConfigLoader(env="stage")
    assert config.get("connect_url") == "https://connect-staging.dimagi.com"


def test_settings_loader_env_var_takes_precedence(monkeypatch):
    monkeypatch.setenv("TEST_ENV_VAR", "from-env")
    settings = SettingsLoader()
    assert settings.get(section="creds", key="hq_username", env_var="TEST_ENV_VAR") == "from-env"


def test_settings_loader_returns_default_when_missing():
    settings = SettingsLoader()
    assert settings.get(section="nope", key="nope", default="fallback") == "fallback"


def test_test_data_loader_loads_olp_1():
    data = TestDataLoader()
    olp1 = data.get("OLP_1")
    assert olp1["opportunity_name"] == "Demo Opportunity"
