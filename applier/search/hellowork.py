import httpx
from bs4 import BeautifulSoup

from .base import BaseSearcher, JobResult

_BASE = "https://www.hellowork.com"
_SEARCH = f"{_BASE}/fr-fr/emploi/recherche.html"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.5",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class HelloWorkSearcher(BaseSearcher):
    def search(self, keywords: str, location: str, count: int = 50) -> list[JobResult]:
        params = {"k": keywords, "l": location, "ray": 50}
        try:
            resp = httpx.get(
                _SEARCH, params=params, headers=_HEADERS,
                timeout=15, follow_redirects=True,
            )
            resp.raise_for_status()
        except Exception:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results: list[JobResult] = []

        # Cards — try data-cy first, fall back to <article>
        cards = (
            soup.select("[data-cy='job-item']")
            or soup.select("article[data-id]")
            or soup.select("article")
        )

        for card in cards[:count]:
            title_el = (
                card.select_one("[data-cy='job-title']")
                or card.select_one("h2")
                or card.select_one("h3")
            )
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            link = title_el.find("a") or card.select_one("a[href*='/emploi/'], a[href*='/offre']")
            if not link:
                link = card.select_one("a[href]")
            if not link:
                continue
            href = link.get("href", "")
            url = href if href.startswith("http") else f"{_BASE}{href}"

            company_el = card.select_one(
                "[data-cy='company-name'], [class*='company'], [class*='Company']"
            )
            company = company_el.get_text(strip=True) if company_el else ""

            loc_el = card.select_one(
                "[data-cy='job-location'], [class*='location'], [class*='Location']"
            )
            loc = loc_el.get_text(strip=True) if loc_el else location

            contract_el = card.select_one(
                "[data-cy='contract-type'], [class*='contract'], [class*='Contract']"
            )
            contract = contract_el.get_text(strip=True) if contract_el else ""

            if not title or not url:
                continue

            results.append(JobResult(
                title=title,
                company=company,
                location=loc,
                url=url,
                platform="HelloWork",
                contract=contract,
            ))

        return results
