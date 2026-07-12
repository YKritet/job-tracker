"""Indeed France — Playwright-based scraper (bypasses RSS/bot blocks)."""
from __future__ import annotations
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from .base import BaseSearcher, JobResult

_BASE = "https://fr.indeed.com"


class IndeedFRSearcher(BaseSearcher):
    def search(self, keywords: str, location: str, count: int = 25) -> list[JobResult]:
        return _pw_search(keywords, location, count)


def _pw_search(keywords: str, location: str, count: int) -> list[JobResult]:
    url = (
        f"{_BASE}/emplois"
        f"?q={quote_plus(keywords)}"
        f"&l={quote_plus(location)}"
        f"&radius=50"
    )
    results: list[JobResult] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                locale="fr-FR",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.new_page()
            page.goto(url, timeout=30_000, wait_until="domcontentloaded")

            # dismiss cookie consent if present
            for sel in [
                'button[id*="onetrust-accept"]',
                'button[id*="cookie-accept"]',
                'button[aria-label*="cookie"]',
                '#onetrust-accept-btn-handler',
            ]:
                try:
                    page.click(sel, timeout=2_000)
                    break
                except PWTimeout:
                    pass

            try:
                page.wait_for_selector('[data-jk], .job_seen_beacon', timeout=15_000)
            except PWTimeout:
                browser.close()
                return []

            cards = (
                page.query_selector_all('[data-jk]')
                or page.query_selector_all('.job_seen_beacon')
            )

            for card in cards[:count]:
                jk = card.get_attribute('data-jk') or ""

                title_el = (
                    card.query_selector('h2.jobTitle span[title]')
                    or card.query_selector('h2.jobTitle span')
                    or card.query_selector('[data-testid="jobTitle"] span')
                    or card.query_selector('h2 a span')
                )
                company_el = (
                    card.query_selector('[data-testid="company-name"]')
                    or card.query_selector('.companyName')
                    or card.query_selector('[class*="companyName"]')
                )
                loc_el = (
                    card.query_selector('[data-testid="text-location"]')
                    or card.query_selector('.companyLocation')
                    or card.query_selector('[class*="companyLocation"]')
                )
                meta_el = (
                    card.query_selector('[data-testid="attribute_snippet_testid"]')
                    or card.query_selector('.salary-snippet-container')
                    or card.query_selector('.attribute_snippet')
                    or card.query_selector('[class*="metadata"]')
                )

                if not title_el:
                    continue
                title = title_el.inner_text().strip()
                if not title:
                    continue

                if jk:
                    job_url = f"{_BASE}/viewjob?jk={jk}"
                else:
                    link = (
                        card.query_selector('h2 a')
                        or card.query_selector('a[href*="viewjob"]')
                    )
                    href = link.get_attribute('href') if link else ""
                    job_url = href if href.startswith('http') else f"{_BASE}{href}" if href else ""

                if not job_url:
                    continue

                meta_text = meta_el.inner_text().strip() if meta_el else ""
                contract = ""
                for kw, label in [
                    ("cdi", "CDI"), ("cdd", "CDD"), ("intérim", "Intérim"),
                    ("stage", "Stage"), ("alternance", "Alternance"),
                    ("temps plein", "Temps plein"), ("temps partiel", "Temps partiel"),
                ]:
                    if kw in meta_text.lower():
                        contract = label
                        break
                if not contract and meta_text:
                    contract = meta_text[:60]

                results.append(JobResult(
                    title=title,
                    company=company_el.inner_text().strip() if company_el else "",
                    location=loc_el.inner_text().strip() if loc_el else location,
                    url=job_url,
                    platform="Indeed",
                    contract=contract,
                ))

            browser.close()
    except Exception:
        pass

    return results
