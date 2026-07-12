import httpx
from bs4 import BeautifulSoup

from .base import BaseSearcher, JobResult

_BASE = "https://www.aeroemploi.com"
_SEARCH = f"{_BASE}/offres-emplois"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class AeroEmploiSearcher(BaseSearcher):
    def search(self, keywords: str, location: str, count: int = 50) -> list[JobResult]:
        params = {"q": keywords, "location": location}
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

        cards = (
            soup.select(".job-item")
            or soup.select(".offre-item")
            or soup.select(".job-offer")
            or soup.select(".jobs-item")
            or soup.select("article")
            or soup.select("li.job")
            or soup.select("[class*='offer']")
        )

        for card in cards[:count]:
            title_el = (
                card.select_one("h2 a")
                or card.select_one("h3 a")
                or card.select_one(".job-title a")
                or card.select_one("[class*='title'] a")
                or card.select_one("a[href*='/offre']")
                or card.select_one("a[href*='/emploi']")
            )
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = href if href.startswith("http") else f"{_BASE}{href}"

            company_el = card.select_one(
                "[class*='company'], [class*='entreprise'], [class*='recruteur']"
            )
            company = company_el.get_text(strip=True) if company_el else ""

            loc_el = card.select_one(
                "[class*='location'], [class*='lieu'], [class*='ville']"
            )
            loc = loc_el.get_text(strip=True) if loc_el else location

            contract_el = card.select_one(
                "[class*='contract'], [class*='contrat'], [class*='type']"
            )
            contract = contract_el.get_text(strip=True) if contract_el else ""

            if not title or not url:
                continue

            results.append(JobResult(
                title=title,
                company=company,
                location=loc,
                url=url,
                platform="AeroEmploi",
                contract=contract,
            ))

        return results
