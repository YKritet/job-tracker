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
    poste: str = ""    # detected job-type category (livreur, conducteur, …)
    domain: str = ""   # detected sector (logistique, BTP, …)
    pulled_at: str = ""

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

# ── Poste detection (COL 1 of the search diagram) ────────────────────────
# Maps canonical poste label → title keywords that identify it
POSTE_KEYWORDS: dict[str, list[str]] = {
    "livreur":      ["livreur", "livraison", "coursier", "delivery driver", "chauffeur livreur"],
    "conducteur":   ["conducteur", "chauffeur spl", "chauffeur pl", "poids lourd", "spl ", "pl conducteur"],
    "ouvrier":      ["ouvrier", "agent de production", "opérateur de production", "manutentionnaire",
                     "agent logistique", "agent de conditionnement"],
    "stockiste":    ["stockiste", "cariste", "magasinier", "préparateur de commandes",
                     "gestionnaire de stock", "agent d'entrepôt"],
    "vendeur":      ["vendeur", "conseiller de vente", "hôte de caisse", "assistant vente",
                     "conseiller commercial magasin"],
    "it support":   ["technicien informatique", "support it", "helpdesk", "help desk",
                     "technicien de maintenance", "technicien réseau", "support technique"],
    "marketer":     ["traffic manager", "community manager", "chargé de communication",
                     "chargé de marketing", "digital marketing", "social media manager",
                     "growth hacker", "responsable marketing"],
    "gestion":      ["gestionnaire", "assistant de direction", "office manager",
                     "responsable administratif", "coordinateur", "chargé d'administration"],
    "ingénieur":    ["ingénieur", "engineer", "architecte logiciel", "développeur"],
    "facteur":      ["facteur", "agent de tri", "agent courrier", "distribution courrier"],
    "technicien":   ["technicien terrain", "technicien installateur", "technicien maintenance"],
    "opérateur":    ["opérateur de saisie", "agent de quai", "agent d'exploitation",
                     "opérateur logistique", "agent de sécurité"],
    "serrurier":    ["serrurier", "menuisier", "plombier", "électricien bâtiment",
                     "technicien de maintenance bâtiment", "chauffagiste"],
    "testeur":      ["testeur", "contrôleur qualité", "quality control", "agent qualité"],
}

# ── Domain detection (COL 2 of the search diagram) ───────────────────────
# Maps canonical domain label → title/company keywords that identify it
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "logistique":          ["logistique", "entrepôt", "supply chain", "warehouse",
                            "préparation de commandes", "fm logistic", "kuehne+nagel",
                            "db schenker", "geodis", "stef", "gefco", "dachser", "ceva",
                            "id logistics", "rhenus", "arvato", "fiege", "easydis"],
    "transport":           ["transport routier", "fret", "ratp", "sncf", "transdev", "keolis",
                            "stuart", "la poste", "chronopost", "dhl", "fedex", "amazon logistics",
                            "vnf", "transport de personnes"],
    "grande distribution": ["grande distribution", "supermarché", "hypermarché", "carrefour",
                            "leclerc", "intermarché", "auchan", "casino", "lidl", "aldi",
                            "système u", "fnac", "darty", "brico dépôt", "castorama",
                            "stokomani", "noz"],
    "btp":                 ["btp", "chantier", "construction", "bâtiment", "travaux publics",
                            "bouygues", "vinci construction", "eiffage", "spie", "génie civil",
                            "dalkia", "engie services", "onet", "derichebourg", "samsic"],
    "industrie":           ["industrie", "manufacture", "usine", "renault", "stellantis",
                            "safran", "thales", "valeo", "dassault", "l'oréal", "sanofi",
                            "air liquide", "faurecia", "essilor", "production industrielle"],
    "agroalimentaire":     ["agroalimentaire", "agro-alimentaire", "brioche pasquier",
                            "délifrance", "bonduelle", "lactalis", "fleury michon",
                            "soufflet", "pomona", "bel groupe", "production alimentaire"],
    "santé":               ["santé", "pharmacie", "médical", "hospitalier", "hôpital",
                            "clinique", "cerp", "mckesson", "alliance healthcare", "servier",
                            "téva", "soins", "paramédical"],
    "nettoyage":           ["nettoyage", "propreté", "facility management", "atalian",
                            "elior", "sodexo", "gsf", "initial", "rentokil", "onet propreté",
                            "agent d'entretien"],
    "télécom":             ["télécom", "telecom", "réseau fibre", "circet", "axians",
                            "sogetrel", "covage", "sfr", "orange", "bouygues telecom",
                            "déploiement réseau"],
    "it":                  ["informatique", "numérique", "data center", "equinix",
                            "ovhcloud", "ikoula", "développement logiciel", "cloud"],
    "événementiel":        ["événementiel", "évènement", "event", "accor", "gl events",
                            "havas events", "semmaris", "salon professionnel", "congrès"],
    "retail":              ["retail", "boutique", "commerce de détail", "magasin", "cdiscount"],
    "aéroport":            ["aéroport", "airport", "swissport", "air france", "dnata",
                            "aéroportuaire", "assistance aéroportuaire"],
    "imprimerie":          ["imprimerie", "packaging", "emballage", "cartonnage", "sérigraphie",
                            "reprographie"],
    "immobilier":          ["immobilier", "promotion immobilière", "property management",
                            "gestion locative", "transaction immobilière"],
}


def auto_tag(title: str, location: str = "", contract: str = "") -> list[str]:
    text = (title + " " + location + " " + contract).lower()
    tags = [tag for tag, kws in _TAG_RULES if any(kw in text for kw in kws)]
    return tags or ["Other"]


def detect_poste(title: str) -> str:
    text = title.lower()
    for poste, kws in POSTE_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return poste
    return ""


def detect_domain(title: str, company: str = "") -> str:
    text = (title + " " + company).lower()
    for domain, kws in DOMAIN_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return domain
    return ""


class BaseSearcher(ABC):
    @abstractmethod
    def search(self, keywords: str, location: str, count: int = 50) -> list[JobResult]:
        ...
