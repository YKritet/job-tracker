"""Monster France — HTML scraper (https://www.monster.fr)."""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from .base import BaseSearcher, JobResult

_BASE = "https://www.monster.fr"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class MonsterFRSearcher(BaseSearcher):
    def search(self, keywords: str, location: str, count: int = 50) -> list[JobResult]:
        url = f"{_BASE}/emploi/recherche/"
        try:
            resp = httpx.get(
                url,
                params={"q": keywords, "where": location},
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
            soup.select("[data-testid='svx-job-item']")
            or soup.select(".results-card")
            or soup.select("article.job-search-result")
            or soup.select(".JobCardStyle")
            or soup.select("[class*='JobCard']")
            or soup.select("section[data-jobid]")
        )

        for card in cards[:count]:
            title_el = (
                card.select_one("h2 a")
                or card.select_one("h3 a")
                or card.select_one("[data-testid='jobTitle'] a")
                or card.select_one("[class*='title'] a")
                or card.select_one("a[data-testid*='job']")
            )
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            job_url = href if href.startswith("http") else f"{_BASE}{href}"
            if not job_url or job_url == _BASE:
                continue

            company_el = card.select_one(
                "[data-testid='company'] *, [class*='company'], [class*='Company']"
            )
            loc_el = card.select_one(
                "[data-testid='location'] *, [class*='location'], [class*='Location']"
            )
            contract_el = card.select_one(
                "[class*='contract'], [class*='Contract'], [class*='jobType'], .badge"
            )

            results.append(JobResult(
                title=title,
                company=company_el.get_text(strip=True) if company_el else "",
                location=loc_el.get_text(strip=True) if loc_el else location,
                url=job_url,
                platform="Monster",
                contract=contract_el.get_text(strip=True) if contract_el else "",
            ))

        return results
