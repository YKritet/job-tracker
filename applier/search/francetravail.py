import httpx
from bs4 import BeautifulSoup
from .base import BaseSearcher, JobResult

BASE = "https://candidat.francetravail.fr"
SEARCH_URL = f"{BASE}/offres/recherche"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}


class FranceTravailSearcher(BaseSearcher):
    """France Travail (ex Pôle Emploi) job search via website scraping."""

    def search(self, keywords: str, location: str = "France", count: int = 50) -> list[JobResult]:
        results: list[JobResult] = []
        params = {
            "motsCles": keywords,
            "offresPartenaires": "true",
            "tri": "0",
        }
        if location and location.lower() not in ("france", "fr"):
            params["lieuTravail"] = location

        with httpx.Client(timeout=20, follow_redirects=True) as client:
            r = client.get(SEARCH_URL, params=params, headers=HEADERS)
            if r.status_code != 200:
                return results

            soup = BeautifulSoup(r.text, "lxml")
            for card in soup.select("li.result"):
                offre_id = card.get("data-id-offre", "")
                if not offre_id:
                    continue

                title_el = card.select_one(".media-heading-title")
                subtext_el = card.select_one("p.subtext")
                contract_el = card.select_one("p.contrat")

                company = ""
                loc = ""
                if subtext_el:
                    span = subtext_el.find("span")
                    if span:
                        loc = span.get_text(strip=True)
                        span.extract()
                    raw = subtext_el.get_text(separator=" ")
                    company = " ".join(w for w in raw.split() if w != "-")

                contract = ""
                if contract_el:
                    parts = []
                    for t in contract_el.get_text(separator="\n").splitlines():
                        t = t.strip().lstrip("- ").strip()
                        if t:
                            parts.append(t)
                    contract = " · ".join(parts)

                results.append(JobResult(
                    title=(title_el.get_text(strip=True) if title_el else ""),
                    company=company,
                    location=loc or location,
                    url=f"{BASE}/offres/recherche/detail/{offre_id}",
                    platform="France Travail",
                    contract=contract,
                ))

                if len(results) >= count:
                    break

        return results
