"""Jobijoba — HTML scraper (https://www.jobijoba.com)."""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from .base import BaseSearcher, JobResult

_BASE = "https://www.jobijoba.com"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class JobijobaSearcher(BaseSearcher):
    def search(self, keywords: str, location: str, count: int = 50) -> list[JobResult]:
        kw_slug = keywords.replace(" ", "+")
        loc_slug = location.replace(" ", "+")
        url = f"{_BASE}/fr/offres-emploi?q={kw_slug}&l={loc_slug}"
        try:
            resp = httpx.get(
                url,
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
            soup.select("article.c-job-card")
            or soup.select(".job-offer-item")
            or soup.select("[data-job-id]")
            or soup.select(".JobCard")
            or soup.select(".job_summary")
            or soup.select("li.offer")
        )

        for card in cards[:count]:
            title_el = (
                card.select_one("h2 a")
                or card.select_one("h3 a")
                or card.select_one(".job-title a")
                or card.select_one("[class*='title'] a")
                or card.select_one("a[class*='Title']")
            )
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url_job = href if href.startswith("http") else f"{_BASE}{href}"
            if not url_job or url_job == _BASE:
                continue

            company_el = card.select_one(
                "[class*='company'], [class*='Company'], [class*='employer'], [class*='Employer']"
            )
            loc_el = card.select_one(
                "[class*='location'], [class*='Location'], [class*='city'], [class*='City']"
            )
            contract_el = card.select_one(
                "[class*='contract'], [class*='Contract'], [class*='type'], .badge"
            )

            results.append(JobResult(
                title=title,
                company=company_el.get_text(strip=True) if company_el else "",
                location=loc_el.get_text(strip=True) if loc_el else location,
                url=url_job,
                platform="Jobijoba",
                contract=contract_el.get_text(strip=True) if contract_el else "",
            ))

        return results
