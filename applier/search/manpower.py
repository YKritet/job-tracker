import httpx
from bs4 import BeautifulSoup

from .base import BaseSearcher, JobResult

_BASE = "https://www.manpower.fr"
_SEARCH = f"{_BASE}/offres-emploi"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class ManpowerSearcher(BaseSearcher):
    def search(self, keywords: str, location: str, count: int = 50) -> list[JobResult]:
        params = {"q": keywords, "lieu": location}
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
            soup.select(".job-result")
            or soup.select(".offer-card")
            or soup.select("[class*='JobOffer']")
            or soup.select("[class*='job-offer']")
            or soup.select("article")
        )

        for card in cards[:count]:
            title_el = (
                card.select_one("h2 a")
                or card.select_one("h3 a")
                or card.select_one("[class*='title'] a")
                or card.select_one("a[href*='/offre/']")
                or card.select_one("a[href*='/emploi/']")
            )
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = href if href.startswith("http") else f"{_BASE}{href}"

            company_el = card.select_one(
                "[class*='company'], [class*='client'], [class*='entreprise']"
            )
            company = company_el.get_text(strip=True) if company_el else "Manpower"

            loc_el = card.select_one(
                "[class*='location'], [class*='city'], [class*='lieu'], [class*='ville']"
            )
            loc = loc_el.get_text(strip=True) if loc_el else location

            contract_el = card.select_one("[class*='contract'], [class*='contrat']")
            contract = contract_el.get_text(strip=True) if contract_el else ""

            if not title or not url:
                continue

            results.append(JobResult(
                title=title,
                company=company,
                location=loc,
                url=url,
                platform="Manpower",
                contract=contract,
            ))

        return results
