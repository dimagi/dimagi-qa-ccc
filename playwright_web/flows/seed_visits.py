"""Seed delivery visits for the one-way review tests (VV_31-35).

Review actions use up visits, so the tests top the pool up themselves: submit the
delivery form in HQ Web Apps as the seeded Connect worker ("Log in as"), which Connect
records as that worker's pending visits (proven on prod 2026-10-16)."""

import time
from urllib.parse import urlsplit

from pages.cchq_login_page import LoginPage
from pages.cchq_web_apps_page import WebAppsPage


def seed_review_visits(context, config, settings, data, count):
    """Submit `count` delivery forms as the worker. Returns the entity names used."""
    page = context.new_page()
    try:
        LoginPage(page).valid_login_cchq(config, settings)  # reuses the context's HQ session
        parts = urlsplit(config.get("cchq_url"))
        web_apps = WebAppsPage(page)
        web_apps.open(f"{parts.scheme}://{parts.netloc}", data["hq_domain"])
        web_apps.log_in_as(data["hq_worker_username"])
        stamp = int(time.time())
        names = []
        for i in range(count):
            web_apps.open_form(data["hq_app_name"], data["hq_module"], data["hq_form"])
            name = f"auto-seed-{stamp}-{i}"
            web_apps.fill_delivery_form(name, data["seed_entity_id"], data["seed_location"])
            web_apps.submit()
            names.append(name)
        return names
    finally:
        page.close()
