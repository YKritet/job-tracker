import html
import httpx
from .base import BaseSearcher, JobResult


def _fix_location(loc: str) -> str:
    """Fix mojibake (UTF-8 bytes read as Latin-1) in location strings."""
    if not loc:
        return "Remote"
    if all(ord(c) < 128 for c in loc):
        return loc
    try:
        return loc.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return "Remote"

API_URL = "https://remoteok.com/api"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


class RemoteOKSearcher(BaseSearcher):
    """RemoteOK public JSON API — 100% remote international jobs."""

    def search(self, keywords: str, location: str = "remote", count: int = 50) -> list[JobResult]:
        # Convert keywords to RemoteOK tag format
        tags = keywords.lower().replace(" ", "+")
        results: list[JobResult] = []

        with httpx.Client(timeout=20) as client:
            r = client.get(API_URL, params={"tags": tags}, headers=HEADERS)
            if r.status_code != 200:
                return results

            data = r.json()
            for job in data:
                if not isinstance(job, dict) or "position" not in job:
                    continue

                url = job.get("url", "")
                if not url:
                    slug = job.get("slug", "")
                    if slug:
                        url = f"https://remoteok.com/remote-jobs/{slug}"
                if not url:
                    continue

                results.append(JobResult(
                    title=html.unescape(job.get("position", "")),
                    company=html.unescape(job.get("company", "")),
                    location=_fix_location(html.unescape(job.get("location") or "")),
                    url=url,
                    platform="RemoteOK",
                    contract="Remote",
                ))

                if len(results) >= count:
                    break

        return results
