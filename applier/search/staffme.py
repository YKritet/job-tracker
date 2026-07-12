"""Staffme — Playwright-based scraper (SPA, https://www.staffme.fr)."""
from __future__ import annotations

from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from .base import BaseSearcher, JobResult

_BASE = "https://www.staffme.fr"


class StaffmeSearcher(BaseSearcher):
    def search(self, keywords: str, location: str, count: int = 50) -> list[JobResult]:
        url = (
            f"{_BASE}/missions"
            f"?search={quote_plus(keywords)}"
            f"&location={quote_plus(location)}"
        )
        results: list[JobResult] = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
                ctx = browser.new_context(
                    locale="fr-FR",
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                )
                page = ctx.new_page()
                page.goto(url, timeout=30_000, wait_until="networkidle")

                # dismiss cookie consent
                for sel in [
                    'button[id*="accept"]', 'button[aria-label*="accepter"]',
                    'button[class*="cookie"]', '#tarteaucitronAllDenied2',
                    'button:has-text("Accepter")',
                ]:
                    try:
                        page.click(sel, timeout=2_000)
                        break
                    except PWTimeout:
                        pass

                _CARD_SELS = [
                    '.mission-card', '[class*="MissionCard"]', '[class*="mission-item"]',
                    'article.card', '[data-mission-id]', '.job-card',
                ]
                loaded = False
                for sel in _CARD_SELS:
                    try:
                        page.wait_for_selector(sel, timeout=10_000)
                        loaded = True
                        break
                    except PWTimeout:
                        continue

                if not loaded:
                    browser.close()
                    return []

                cards = []
                for sel in _CARD_SELS:
                    cards = page.query_selector_all(sel)
                    if cards:
                        break

                for card in cards[:count]:
                    title_el = (
                        card.query_selector('h2 a') or card.query_selector('h3 a')
                        or card.query_selector('[class*="title"] a')
                        or card.query_selector('a[class*="Title"]')
                    )
                    if not title_el:
                        title_el = card.query_selector('h2') or card.query_selector('h3')
                    if not title_el:
                        continue
                    title = title_el.inner_text().strip()
                    if not title:
                        continue

                    link = (
                        title_el if title_el.get_attribute('href') else
                        card.query_selector('a[href]')
                    )
                    href = link.get_attribute('href') if link else ""
                    job_url = href if href and href.startswith('http') else f"{_BASE}{href}" if href else ""
                    if not job_url:
                        continue

                    company_el = card.query_selector(
                        '[class*="company"], [class*="Company"], [class*="employer"]'
                    )
                    loc_el = card.query_selector(
                        '[class*="location"], [class*="Location"], [class*="city"]'
                    )
                    contract_el = card.query_selector(
                        '[class*="contract"], [class*="type"], .badge'
                    )

                    results.append(JobResult(
                        title=title,
                        company=company_el.inner_text().strip() if company_el else "",
                        location=loc_el.inner_text().strip() if loc_el else location,
                        url=job_url,
                        platform="Staffme",
                        contract=contract_el.inner_text().strip() if contract_el else "",
                    ))

                browser.close()
        except Exception:
            pass
        return results
