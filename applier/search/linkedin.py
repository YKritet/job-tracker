import httpx
from bs4 import BeautifulSoup
from .base import BaseSearcher, JobResult

GUEST_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

GEO_IDS: dict[str, int] = {
    "paris": 104246759,
    "île-de-france": 104246759,
    "france": 105015875,
    "luxembourg": 104042105,
    "germany": 101282230,
    "uk": 101165590,
    "london": 90009496,
    "berlin": 106967272,
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


class LinkedInSearcher(BaseSearcher):
    """LinkedIn job search via the public guest-jobs API (no auth required)."""

    def __init__(self, li_at: str = ""):
        pass  # li_at not needed for guest API

    def search(self, keywords: str, location: str = "france", count: int = 50) -> list[JobResult]:
        geo_id = GEO_IDS.get(location.lower())
        results: list[JobResult] = []

        with httpx.Client(timeout=20, follow_redirects=True) as client:
            start = 0
            while len(results) < count:
                params: dict = {
                    "keywords": keywords,
                    "location": location,
                    "start": start,
                }
                if geo_id:
                    params["geoId"] = geo_id

                r = client.get(GUEST_API, params=params, headers=HEADERS)
                if r.status_code != 200:
                    break

                soup = BeautifulSoup(r.text, "lxml")
                cards = soup.select(".job-search-card")
                if not cards:
                    break

                for card in cards:
                    urn = card.get("data-entity-urn", "")
                    job_id = urn.split(":")[-1] if urn else ""
                    if not job_id:
                        continue

                    title_el = card.select_one(".base-search-card__title")
                    company_el = card.select_one(".base-search-card__subtitle")
                    location_el = card.select_one(".job-search-card__location")

                    results.append(JobResult(
                        title=(title_el.get_text(strip=True) if title_el else ""),
                        company=(company_el.get_text(strip=True) if company_el else ""),
                        location=(location_el.get_text(strip=True) if location_el else location),
                        url=f"https://www.linkedin.com/jobs/view/{job_id}",
                        platform="LinkedIn",
                        contract="",
                    ))

                start += len(cards)
                if len(cards) < 10:
                    break

        return results[:count]
