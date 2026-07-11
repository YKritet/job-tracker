"""Indeed France scraper — parses the public RSS feed (no JS required)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import urlencode

import httpx

from .base import BaseSearcher, JobResult

_RSS_URL = "https://fr.indeed.com/rss"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

# Indeed RSS namespaces
_NS = {"indeed": "https://www.indeed.com/about/rss"}


class IndeedFRSearcher(BaseSearcher):
    def search(self, keywords: str, location: str, count: int = 25) -> list[JobResult]:
        params = {
            "q": keywords,
            "l": location,
            "radius": "50",
            "limit": str(min(count, 25)),
            "lang": "fr",
        }
        try:
            resp = httpx.get(
                f"{_RSS_URL}?{urlencode(params)}",
                headers=_HEADERS,
                timeout=20,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Indeed FR HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Indeed FR request failed: {e}") from e

        return _parse_rss(resp.text, location)


def _parse_rss(xml_text: str, fallback_location: str) -> list[JobResult]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise RuntimeError(f"Indeed FR RSS parse error: {e}") from e

    results: list[JobResult] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        url   = (item.findtext("link")  or "").strip()
        if not title or not url:
            continue

        # Company: Indeed puts it in <source> or in the description
        company = (item.findtext("source") or "").strip()

        # Location: Indeed sometimes provides it in the description text
        location = fallback_location

        # Contract type from description text (best-effort)
        desc = (item.findtext("description") or "").lower()
        contract = ""
        for kw, label in [("cdi", "CDI"), ("cdd", "CDD"), ("freelance", "Freelance"),
                           ("intérim", "Intérim"), ("stage", "Stage"),
                           ("alternance", "Alternance")]:
            if kw in desc:
                contract = label
                break

        results.append(JobResult(
            title=title,
            company=company,
            location=location,
            url=url,
            platform="Indeed",
            contract=contract,
        ))

    return results
