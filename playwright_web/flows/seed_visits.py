"""Seed delivery visits for the one-way review tests (VV_31-35).

Review actions use up visits, so the tests top the pool up themselves: submit the
delivery form in HQ Web Apps as the seeded Connect worker ("Log in as"), which Connect
records as that worker's pending visits (proven on prod 2026-10-16)."""

import time
from urllib.parse import urlsplit

from pages.cchq_login_page import LoginPage
from pages.cchq_web_apps_page import WebAppsPage


def _submit_one(web_apps, hq_url, data, name, attempts=3):
    """One delivery form. Web Apps (especially on staging, from a CI runner) sometimes stalls on
    a menu level after earlier submits; a fresh load + "Log in as" recovers, so retry from there
    instead of failing the whole seeding run."""
    for attempt in range(1, attempts + 1):
        try:
            web_apps.open_form(data["hq_app_name"], data["hq_module"], data["hq_form"])
            web_apps.fill_delivery_form(name, data["seed_entity_id"], data["seed_location"])
            web_apps.submit()
            return
        except Exception as exc:
            body = web_apps.page.inner_text("body")[:300] if not web_apps.page.is_closed() else ""
            print(f"Seed attempt {attempt}/{attempts} for {name} failed at {web_apps.page.url}: "
                  f"{type(exc).__name__}; page text: {body!r}")
            if attempt == attempts:
                raise
            web_apps.open(hq_url, data["hq_domain"])
            web_apps.log_in_as(data["hq_worker_username"])


def seed_review_visits(context, config, settings, data, count):
    """Submit `count` delivery forms as the worker. Returns the entity names used."""
    page = context.new_page()
    try:
        LoginPage(page).valid_login_cchq(config, settings)  # reuses the context's HQ session
        parts = urlsplit(config.get("cchq_url"))
        web_apps = WebAppsPage(page)
        hq_url = f"{parts.scheme}://{parts.netloc}"
        web_apps.open(hq_url, data["hq_domain"])
        web_apps.log_in_as(data["hq_worker_username"])
        stamp = int(time.time())
        names = []
        for i in range(count):
            name = f"auto-seed-{stamp}-{i}"
            _submit_one(web_apps, hq_url, data, name)
            names.append(name)
        return names
    finally:
        page.close()
