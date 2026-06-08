from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class JobResult:
    title: str
    company: str
    location: str
    url: str
    platform: str
    contract: str = ""
    tags: list[str] = field(default_factory=list)
    pulled_at: str = ""  # ISO date string, set by main.py at search time

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return isinstance(other, JobResult) and self.url == other.url


# ── Auto-tagging ──────────────────────────────────────────────────────────
_TAG_RULES: list[tuple[str, list[str]]] = [
    ("IT",          ["développeur", "developer", "software", "devops", "cloud", "data",
                     "infrastructure", "sysadmin", "réseau", "network", "backend", "frontend",
                     "fullstack", "python", "java", "kubernetes", "platform", "sre", "architect"]),
    ("Security",    ["sécurité", "cybersécurité", "security", "rssi", "ciso", "soc",
                     "pentest", "vulnerability", "compliance", "audit sécurité"]),
    ("Sales",       ["commercial", "vente", "sales", "account executive", "business development",
                     "account manager", "closing", "chasseur", "prospection", "revenue"]),
    ("Marketing",   ["marketing", "digital", "seo", "sem", "brand", "communication",
                     "content", "growth", "acquisition", "crm", "emailing"]),
    ("Finance",     ["finance", "comptable", "comptabilité", "audit", "contrôle de gestion",
                     "trésorier", "trésorerie", "risk", "banking", "banque", "investment",
                     "private equity", "asset", "trading", "analyste financier"]),
    ("Consulting",  ["consultant", "conseil", "advisory", "management consulting",
                     "transformation", "stratégie"]),
    ("HR",          ["ressources humaines", "rh", "recrutement", "talent", "people",
                     "hrm", "paie", "formation"]),
    ("Product",     ["product manager", "product owner", "po ", "pm ", "roadmap",
                     "product management", "chef de produit"]),
    ("Operations",  ["opérations", "operations", "supply chain", "logistique", "logistics",
                     "projet", "project manager", "pmo", "lean", "process"]),
    ("Customer",    ["customer success", "customer experience", "support", "service client",
                     "account management", "relation client", "csm"]),
    ("Remote",      ["remote", "télétravail", "full remote", "100% remote"]),
]


def auto_tag(title: str, location: str = "", contract: str = "") -> list[str]:
    text = (title + " " + location + " " + contract).lower()
    tags = [tag for tag, kws in _TAG_RULES if any(kw in text for kw in kws)]
    return tags or ["Other"]


class BaseSearcher(ABC):
    @abstractmethod
    def search(self, keywords: str, location: str, count: int = 50) -> list[JobResult]:
        ...
