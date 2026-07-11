"""Welcome to the Jungle scraper — uses their public search API."""
from __future__ import annotations

import httpx

from .base import BaseSearcher, JobResult

# WTTJ public search endpoint (used by their own SPA, no auth required)
_API_URL = "https://api.welcometothejungle.com/api/v1/jobs"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": "https://www.welcometothejungle.com/",
    "Origin": "https://www.welcometothejungle.com",
}

_COUNTRY_MAP = {
    "France": "FR",
    "FR":     "FR",
    "Germany": "DE",
    "DE":      "DE",
    "UK":      "GB",
    "GB":      "GB",
    "Luxembourg": "LU",
    "LU":         "LU",
}


class WTTJSearcher(BaseSearcher):
    def search(self, keywords: str, location: str, count: int = 25) -> list[JobResult]:
        country = _COUNTRY_MAP.get(location, "FR")
        params = {
            "query": keywords,
            "country_code": country,
            "page": 1,
            "per_page": min(count, 30),
        }
        try:
            resp = httpx.get(
                _API_URL,
                params=params,
                headers=_HEADERS,
                timeout=20,
                follow_redirects=True,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"WTTJ HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"WTTJ request failed: {e}") from e
        except Exception as e:
            raise RuntimeError(f"WTTJ parse error: {e}") from e

        return _extract(data, location)


def _extract(data: dict, fallback_location: str) -> list[JobResult]:
    results: list[JobResult] = []
    jobs = data.get("jobs") or data.get("results") or []
    if not jobs and isinstance(data, list):
        jobs = data

    for j in jobs:
        # Flatten nested structures from the WTTJ API response
        title   = j.get("name") or j.get("title") or ""
        slug    = j.get("slug") or ""
        org     = j.get("organization") or j.get("company") or {}
        company = org.get("name") or org if isinstance(org, str) else ""
        office  = j.get("office") or {}
        city    = office.get("city") or fallback_location
        url     = (
            f"https://www.welcometothejungle.com/jobs/{slug}"
            if slug else j.get("url") or j.get("apply_url") or ""
        )
        contract_data = j.get("contract_type") or {}
        contract = (
            contract_data.get("name") if isinstance(contract_data, dict)
            else str(contract_data)
        ) or ""

        if not title or not url:
            continue

        results.append(JobResult(
            title=title,
            company=str(company),
            location=str(city),
            url=url,
            platform="WTTJ",
            contract=contract,
        ))

    return results
