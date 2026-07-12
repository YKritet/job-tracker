"""Optioncarriere — HTML scraper (https://www.optioncarriere.fr)."""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from .base import BaseSearcher, JobResult

_BASE = "https://www.optioncarriere.fr"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class OptionCarriereSearcher(BaseSearcher):
    def search(self, keywords: str, location: str, count: int = 50) -> list[JobResult]:
        try:
            resp = httpx.get(
                f"{_BASE}/emploi.php",
                params={"s": keywords, "l": location, "c": "FR"},
                headers=_HEADERS,
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except Exception:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results: list[JobResult] = []

        cards = (
            soup.select("article.job")
            or soup.select("li.job")
            or soup.select(".job-item")
            or soup.select("[class*='offer-card']")
            or soup.select(".offer")
            or soup.select("[class*='offre']")
        )

        for card in cards[:count]:
            title_el = (
                card.select_one("h2 a")
                or card.select_one("h3 a")
                or card.select_one(".job-title a")
                or card.select_one("[class*='title'] a")
                or card.select_one("a.job-link")
            )
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            job_url = href if href.startswith("http") else f"{_BASE}{href}"
            if not job_url or job_url == _BASE:
                continue

            company_el = card.select_one(
                ".company, [class*='company'], [class*='employer'], .org"
            )
            loc_el = card.select_one(
                ".location, [class*='location'], [class*='city'], .place"
            )
            contract_el = card.select_one(
                ".contract, [class*='contract'], [class*='type'], .badge, li.type"
            )

            results.append(JobResult(
                title=title,
                company=company_el.get_text(strip=True) if company_el else "",
                location=loc_el.get_text(strip=True) if loc_el else location,
                url=job_url,
                platform="OptionCarriere",
                contract=contract_el.get_text(strip=True) if contract_el else "",
            ))

        return results
