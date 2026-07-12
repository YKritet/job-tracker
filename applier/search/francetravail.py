"""France Travail — Playwright-based scraper (Angular SPA)."""
from __future__ import annotations
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from .base import BaseSearcher, JobResult

_BASE = "https://candidat.francetravail.fr"

_CARD_SELECTORS = [
    '[data-id-offre]',
    'li.result',
    'article[data-id]',
    '.c-card-job',
    '.result-item',
    'app-result-item',
    '.offre-result',
]


class FranceTravailSearcher(BaseSearcher):
    def search(self, keywords: str, location: str = "France", count: int = 50) -> list[JobResult]:
        return _pw_search(keywords, location, count)


def _pw_search(keywords: str, location: str, count: int) -> list[JobResult]:
    loc_param = (
        f"&lieuTravail={quote_plus(location)}"
        if location and location.lower() not in ("france", "fr", "")
        else ""
    )
    url = (
        f"{_BASE}/offres/recherche"
        f"?motsCles={quote_plus(keywords)}"
        f"&offresPartenaires=true&tri=0{loc_param}"
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
                '#pecCookieButton',
                'button[data-action*="cookie"]',
                'button[aria-label*="accepter"]',
                'button[id*="accept"]',
                '.pec-cookie__btn',
            ]:
                try:
                    page.click(sel, timeout=2_000)
                    break
                except PWTimeout:
                    pass

            # wait for Angular to render job cards
            loaded = False
            for sel in _CARD_SELECTORS:
                try:
                    page.wait_for_selector(sel, timeout=12_000)
                    loaded = True
                    break
                except PWTimeout:
                    continue

            if not loaded:
                browser.close()
                return []

            cards = []
            for sel in _CARD_SELECTORS:
                cards = page.query_selector_all(sel)
                if cards:
                    break

            for card in cards[:count]:
                offre_id = card.get_attribute('data-id-offre') or ""

                title_el = (
                    card.query_selector('.media-heading-title')
                    or card.query_selector('h2 a')
                    or card.query_selector('h3 a')
                    or card.query_selector('[class*="title"] a')
                    or card.query_selector('a[data-label="offre"]')
                )
                company_el = (
                    card.query_selector('.subtext .subtext-company')
                    or card.query_selector('[class*="company"]')
                    or card.query_selector('[class*="entreprise"]')
                )
                loc_el = (
                    card.query_selector('.subtext .location')
                    or card.query_selector('[class*="location"]')
                    or card.query_selector('[class*="lieu"]')
                )
                contract_el = (
                    card.query_selector('.contrat')
                    or card.query_selector('[class*="contract"]')
                    or card.query_selector('[class*="typeContrat"]')
                )

                if not title_el:
                    continue
                title = title_el.inner_text().strip()
                if not title:
                    continue

                if offre_id:
                    job_url = f"{_BASE}/offres/recherche/detail/{offre_id}"
                else:
                    link = (
                        card.query_selector('a[href*="detail"]')
                        or card.query_selector('a[href*="offres"]')
                        or card.query_selector('a[href]')
                    )
                    if link:
                        href = link.get_attribute('href') or ""
                        job_url = href if href.startswith('http') else f"{_BASE}{href}"
                    else:
                        continue

                results.append(JobResult(
                    title=title,
                    company=company_el.inner_text().strip() if company_el else "",
                    location=loc_el.inner_text().strip() if loc_el else location,
                    url=job_url,
                    platform="France Travail",
                    contract=contract_el.inner_text().strip() if contract_el else "",
                ))

            browser.close()
    except Exception:
        pass

    return results
