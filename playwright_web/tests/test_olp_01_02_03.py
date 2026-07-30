from flows.olp_setup import full_olp_setup


def test_olp_01_02_03_setup_budget_in_connect(page, test_data, config, settings):
    full_olp_setup(page, config, settings, test_data)
