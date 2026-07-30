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


def test_config_loader_falls_back_to_yaml_default():
    import yaml

    from utils.helpers import REPO_ROOT

    with open(REPO_ROOT / "config" / "env.yaml") as f:
        data = yaml.safe_load(f)

    config = ConfigLoader(env=None)
    assert config.env == data["default"]
    assert config.get("cchq_url") == data[data["default"]]["cchq_url"]


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


from utils.helpers import parse_org_and_opp


def test_parse_org_and_opp_from_dashboard_url():
    url = "https://connect-staging.dimagi.com/a/pm-automation-01/opportunity/612/"
    assert parse_org_and_opp(url) == ("pm-automation-01", "612")


def test_parse_org_and_opp_from_nested_page_url():
    url = "https://connect-staging.dimagi.com/a/my-org/opportunity/45/workers/tasks/?x=1"
    assert parse_org_and_opp(url) == ("my-org", "45")


def test_parse_org_and_opp_raises_on_non_opportunity_url():
    import pytest

    with pytest.raises(ValueError):
        parse_org_and_opp("https://connect-staging.dimagi.com/a/my-org/program/")
