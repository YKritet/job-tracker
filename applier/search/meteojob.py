"""Meteojob — HTML scraper (https://www.meteojob.com)."""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from .base import BaseSearcher, JobResult

_BASE = "https://www.meteojob.com"
_SEARCH = f"{_BASE}/jobsearch/results"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": _BASE,
}


class MeteojobSearcher(BaseSearcher):
    def search(self, keywords: str, location: str, count: int = 50) -> list[JobResult]:
        try:
            resp = httpx.get(
                _SEARCH,
                params={"what": keywords, "where": location},
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
            soup.select("article.job-item")
            or soup.select(".job-result-item")
            or soup.select("[data-jobid]")
            or soup.select(".offerCard")
            or soup.select(".offerResult")
        )

        for card in cards[:count]:
            title_el = (
                card.select_one("h2 a")
                or card.select_one("h3 a")
                or card.select_one(".job-title a")
                or card.select_one("[class*='title'] a")
            )
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = href if href.startswith("http") else f"{_BASE}{href}"
            if not url:
                continue

            company_el = card.select_one(
                ".company-name, [class*='company'], .employer, [class*='employer']"
            )
            loc_el = card.select_one(
                ".location, [class*='location'], .city, [class*='city']"
            )
            contract_el = card.select_one(
                ".contract, [class*='contract'], .job-type, [class*='jobType']"
            )

            results.append(JobResult(
                title=title,
                company=company_el.get_text(strip=True) if company_el else "",
                location=loc_el.get_text(strip=True) if loc_el else location,
                url=url,
                platform="Meteojob",
                contract=contract_el.get_text(strip=True) if contract_el else "",
            ))

        return results
