# Playwright Web Migration — Pilot Design

## Context

The existing web test suite (`tests/web_tests/`) is built on Selenium + Pytest, using a Page Object Model with YAML-defined locators (`locators/web_locators.yaml`) and a `BaseWebPage` class that wraps `WebDriverWait`/retry logic.

We're moving web automation to **Playwright**, using **Python + pytest-playwright** (not JS/TS) to stay consistent with the existing Python/Pytest ecosystem (Allure, Slack/email notifiers, `ConfigLoader`/`SettingsLoader`, CI patterns). This is a from-scratch project setup — no Playwright project exists yet.

This spec covers a **pilot**: proving out the framework pattern with 2 representative tests before porting the remaining 8. The existing Selenium tests are used as the source of truth for business logic, locators, and edge-case handling (iframe/popup dismissal, login flow quirks), but reimplemented idiomatically for Playwright rather than translated line-by-line — Playwright's auto-waiting locators remove the need for most of the manual wait/retry code that Selenium required.

## Pilot scope

Port 2 tests end-to-end:
- `test_olp_01_02_03` — HQ login → copy Learn App → copy Delivery App → navigate to Connect → sign in via CCHQ → select org → create opportunity → add payment unit → set up budget. (Foundational flow: login, navigation, forms, dropdowns.)
- `test_olp_04` — depends on an opportunity existing → navigates to dashboard → verifies opportunity details/cards. (Different pattern: read/verification-heavy.)

## Project structure

New folder inside the existing `dimagi-qa-ccc` repo, alongside (not replacing) the Selenium suite:

```
dimagi-qa-ccc/
└── playwright_web/
    ├── pages/              # Page Object classes (mirrors pages/web_pages/)
    │   ├── base_page.py
    │   ├── cchq_login_page.py
    │   ├── cchq_home_page.py
    │   ├── cchq_application_page.py
    │   ├── connect_home_page.py
    │   ├── connect_opportunities_page.py
    │   └── connect_opportunity_dashboard_page.py
    ├── locators/
    │   └── web_locators.yaml      # same shape as existing, Playwright-compatible selectors
    ├── tests/
    │   ├── conftest.py             # page/browser fixtures, config & test_data loading
    │   ├── test_olp_01_02_03.py
    │   └── test_olp_04.py
    ├── pytest.ini
    └── requirements.txt            # pytest-playwright, PyYAML
```

## Locators & Page Objects

- `web_locators.yaml` keeps the same shape (`page_name: element_name: selector`), including `{placeholder}` values for dynamic text.
- Most existing XPath strings carry over as-is (Playwright supports `page.locator("xpath=...")`).
- `BasePage` wraps common actions (`click`, `type`, `select_option`, `wait_for_url_contains`, `scroll_into_view`, etc.) — much thinner than today's `BaseWebPage` since Playwright auto-waits for actionability, eliminating most manual `WebDriverWait`/retry/staleness-handling code.
- **AI self-healing locator fallback is carried over**: on a locator-not-found failure, fall back to an OpenAI call (same `AI_HEALING_ENABLED`/`OPENAI_API_KEY` gating as today) to suggest an alternative selector from page content, adapted to Playwright's exception types.

## Config & test data

Reused by relative path from `playwright_web/` (same repo, no duplication):
- `config/env.yaml` — same `prod`/`stage` URLs, loaded via a `--env` pytest CLI option
- `settings.cfg` (`creds` section) — same HQ username/password loading, with env var override
- `test_data/web_test_data.yaml` — same `OLP_1`, `OLP_2`, `OLP_3`, `OLP_4` blocks

`ConfigLoader`/`SettingsLoader`/`TestDataLoader` from `utils/helpers.py` are ported largely as-is into `playwright_web/utils/` (pure Python, not Selenium-specific).

## Test execution & pilot flow

- `conftest.py` provides a `page` fixture (Playwright `Page` object), scoped per-test, launching **Chromium, headed by default**.
- Tests reproduce the same business logic as their Selenium counterparts, reimplemented idiomatically (no `time.sleep()` calls needed where Playwright's auto-wait covers it).
- Allure decorators are **dropped for the pilot** (no reporting wiring yet) — plain pytest test names/docstrings; Allure returns in the full reporting/CI pass.
- Run via `pytest -v playwright_web/tests --env=stage` (or `prod`), same convention as today.

## Out of scope for this pilot (deferred, not forgotten)

- Remaining 8 web test files (worker list, payments, worker visits, messaging, programs)
- Allure reporting, pytest-html, GitHub Actions CI, Slack/email notifications
- Cross-browser (Firefox/WebKit) coverage
- `test_cleanup.py` teardown-of-created-data logic

## Testing

Manual verification: run the 2 pilot tests locally against `stage` and confirm they pass end-to-end (opportunity gets created, dashboard shows correct details), matching what the Selenium versions currently verify.
