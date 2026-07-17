# Playwright Web Pilot

Python + pytest-playwright port of 2 tests from the Selenium web suite
(`test_olp_01_02_03`, `test_olp_04`), proving the framework pattern before
the rest of `tests/web_tests/` is ported.

## Setup

From the `playwright_web/` directory:

    pip install -r requirements.txt
    playwright install chromium

Copy `../settings-sample.cfg` to `../settings.cfg` (repo root) and fill in
`hq_username`/`hq_password` under `[creds]` if you haven't already for the
Selenium suite — both suites share the same file.

## Run

    pytest --env=stage
    pytest --env=prod

Runs Chromium headed by default (see `pytest.ini`).
