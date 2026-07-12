import re
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
    skills: list[str] = field(default_factory=list)  # required certifications + skills
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


TAG_NAMES: list[str] = [name for name, _ in _TAG_RULES]


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


# ── Skills & certifications detection ────────────────────────────────────────
# Regex-based: labels are extracted from job text, not from a hardcoded catalogue.
# CACES and permis variants are discovered dynamically (any R\d{3} / any class letter).
# Named certs (HACCP, SST…) and software tools match their literal acronyms in the text.

_MATCHERS: list[tuple[re.Pattern, callable]] = [
    # ── CACES & Permis (dynamic: extract R-number / class letter) ─────────────
    (re.compile(r'\bcaces\s*r?\s*(\d{3})\b', re.I), lambda m: f"CACES R{m.group(1)}"),
    (re.compile(r'\bcaces\s+(\d)\b', re.I),          lambda m: f"CACES {m.group(1)}"),  # old notation
    (re.compile(r'\bpermis\s+([a-z]{1,2}(?:/[a-z]{1,2})*)\b', re.I),
     lambda m: f"permis {m.group(1).upper()}"),

    # ── Habilitation électrique — specific NF C 18-510 levels ─────────────────
    # (source: INRS, egpp-electricite.fr, leadika.fr — each level appears in job postings)
    # Specific level captures come BEFORE the generic catch-all
    (re.compile(
        r'\bhab(?:ilitation)?\s*(?:[eé]lec\w*\s*)?'
        r'(b0|h0v|h0|bs|br|bc|b1v|b1|b2v|b2|be|h1|h2|hc)\b',
        re.I
    ), lambda m: f"hab. {m.group(1).upper()}"),
    # Generic catch-all for "habilitation électrique" without explicit level
    (re.compile(r'\bhabilitation\s+[eé]lec\w*', re.I), lambda _: "habilitation élec."),

    # ── Safety & regulatory (French mandatory certs) ──────────────────────────
    # source: INRS, France Travail, SAD'S Intérim guide 2026
    (re.compile(r'\bhaccp\b', re.I),                             lambda _: "HACCP"),
    (re.compile(r'\b(?:sst|psc\s*[12])\b|secouriste\s+du\s+travail', re.I), lambda _: "SST"),
    (re.compile(r'\baipr\b', re.I),                              lambda _: "AIPR"),
    (re.compile(r'\badr\b', re.I),                               lambda _: "ADR"),
    (re.compile(r'\batex\b', re.I),                              lambda _: "ATEX"),
    (re.compile(r'\bfimo\b', re.I),                              lambda _: "FIMO"),
    (re.compile(r'\bfc[o0]s?\b', re.I),                         lambda _: "FCO"),
    (re.compile(r'\bqhse\b', re.I),                              lambda _: "QHSE"),
    (re.compile(r'\bcqp\b', re.I),                               lambda _: "CQP"),
    (re.compile(r'\bvae\b', re.I),                               lambda _: "VAE"),

    # ── Bureautique & numérique (France Compétences / RS certs) ──────────────
    # source: francecompetences.fr, opcodirect.fr 2026
    (re.compile(r'\btosa\b', re.I),                              lambda _: "TOSA"),
    (re.compile(r'\bpix\b', re.I),                               lambda _: "PIX"),
    (re.compile(r'\bvoltaire\b', re.I),                          lambda _: "Voltaire"),
    (re.compile(r'\btoeic\b', re.I),                             lambda _: "TOEIC"),
    (re.compile(r'\btoefl\b', re.I),                             lambda _: "TOEFL"),
    (re.compile(r'\bdelf\b', re.I),                              lambda _: "DELF"),
    (re.compile(r'\bdalf\b', re.I),                              lambda _: "DALF"),
    (re.compile(r'\bqualiopi\b', re.I),                          lambda _: "Qualiopi"),

    # ── ISO & quality standards ───────────────────────────────────────────────
    (re.compile(r'\biso\s*9001\b', re.I),                        lambda _: "ISO 9001"),
    (re.compile(r'\biso\s*14001\b', re.I),                       lambda _: "ISO 14001"),
    (re.compile(r'\biso\s*45001\b', re.I),                       lambda _: "ISO 45001"),
    (re.compile(r'\biso\s*27001\b', re.I),                       lambda _: "ISO 27001"),
    (re.compile(r'\biso\s*22000\b', re.I),                       lambda _: "ISO 22000"),

    # ── Project management & agile ────────────────────────────────────────────
    # source: PMI, opcodirect.fr, guide-formations-certifiantes.com 2025-2026
    (re.compile(r'\bpmp\b', re.I),                               lambda _: "PMP"),
    (re.compile(r'\bcapm\b', re.I),                              lambda _: "CAPM"),
    (re.compile(r'\bprince\s*2\b', re.I),                        lambda _: "PRINCE2"),
    (re.compile(r'\bscrum\s*master\b|\bcsm\b|\bpsm\b', re.I),   lambda _: "Scrum Master"),
    (re.compile(r'\bproduct\s*owner\b|\bcppo\b', re.I),          lambda _: "Product Owner"),
    (re.compile(r'\bsafe\s*agile\b|\bsafe\s*\d\b', re.I),       lambda _: "SAFe"),
    (re.compile(r'\blean\s*six\s*sigma\b|\blss\b', re.I),        lambda _: "Lean Six Sigma"),
    (re.compile(r'\bsix\s*sigma\b', re.I),                       lambda _: "Six Sigma"),
    (re.compile(r'\bitil\b', re.I),                              lambda _: "ITIL"),
    (re.compile(r'\bpmo\b', re.I),                               lambda _: "PMO"),

    # ── Cloud & DevOps certifications ─────────────────────────────────────────
    # source: silicon.fr Benchmarks IT 2026, s-quaar.fr top 7 certif IT 2025
    # AWS — 68% FR senior IT jobs require cloud cert (IDC France 2025)
    (re.compile(r'\baws\s+certifi|\baws\s+solutions?\s+architect\b|'
                r'\baws\s+developer\b|\baws\s+sysops\b|\baws\s+devops\b', re.I),
     lambda _: "AWS Certified"),
    # Azure — dominant in grand comptes / ESN (silicon.fr 2026)
    (re.compile(r'\bazure\s+certifi|\baz-\d{3}\b|\bmicrosoft\s+certifi.*azure\b', re.I),
     lambda _: "Azure Certified"),
    # GCP — fastest growing; data/AI demand surge (universite-yde2.org 2025)
    (re.compile(r'\bgcp\s+certifi|google\s+cloud\s+(?:certifi|engineer|architect)\b', re.I),
     lambda _: "GCP Certified"),
    # Kubernetes / containers
    (re.compile(r'\bcka\b|kubernetes\s+administrator\b', re.I), lambda _: "CKA"),
    (re.compile(r'\bckad\b', re.I),                             lambda _: "CKAD"),
    # IaC
    (re.compile(r'\bterraform\s+(?:certifi|associate)\b|\bhashicorp\s+certifi', re.I),
     lambda _: "Terraform"),
    # Networking
    (re.compile(r'\bccna\b', re.I),                             lambda _: "CCNA"),
    (re.compile(r'\bccnp\b', re.I),                             lambda _: "CCNP"),
    # Security
    (re.compile(r'\bcissp\b', re.I),                            lambda _: "CISSP"),
    (re.compile(r'\bceh\b|certified\s+ethical\s+hacker\b', re.I), lambda _: "CEH"),
    (re.compile(r'\bcomptia\b|comptia\s*[as]\+', re.I),         lambda _: "CompTIA"),
    # Linux
    (re.compile(r'\brhcsa\b|\brhce\b|\bred\s+hat\s+certifi', re.I), lambda _: "Red Hat"),

    # ── Finance & comptabilité (RNCP highly demanded — guide-formations 2025) ──
    (re.compile(r'\bdcg\b', re.I),                              lambda _: "DCG"),
    (re.compile(r'\bdscg\b', re.I),                             lambda _: "DSCG"),
    (re.compile(r'\bgestionnaire\s+de\s+paie\b|certifi.*paie\b', re.I), lambda _: "Gestionnaire de paie"),

    # ── Digital marketing certifications ─────────────────────────────────────
    # source: activ-projets.com, blogdumoderateur.com 2025
    # GA4 — in 68% of FR digital marketing job offers (LinkedIn 2024)
    (re.compile(r'\bga4\b|google\s+analytics\s*4\b|google\s+analytics?\s+certifi', re.I),
     lambda _: "Google Analytics"),
    (re.compile(r'\bgoogle\s+ads?\s+certifi', re.I),            lambda _: "Google Ads"),
    # Meta Blueprint — reference for paid social (activ-projets.com 2025)
    (re.compile(r'\bmeta\s+blueprint\b|facebook\s+blueprint\b', re.I), lambda _: "Meta Blueprint"),
    # HubSpot — 200k companies recognize it (activ-projets.com 2025)
    (re.compile(r'\bhubspot\b', re.I),                          lambda _: "HubSpot"),
    # SEO tools with certs (effetpapillon.fr 2025)
    (re.compile(r'\bsemrush\b', re.I),                          lambda _: "SEMrush"),
    (re.compile(r'\byoast\b', re.I),                            lambda _: "Yoast"),

    # ── Software tools ────────────────────────────────────────────────────────
    (re.compile(r'\bexcel\b', re.I),                            lambda _: "Excel"),
    (re.compile(r'\bpower\s*bi\b', re.I),                       lambda _: "Power BI"),
    (re.compile(r'\btableau\b', re.I),                          lambda _: "Tableau"),
    (re.compile(r'\bsap\b', re.I),                              lambda _: "SAP"),
    (re.compile(r'\bwms\b', re.I),                              lambda _: "WMS"),
    (re.compile(r'\btms\b', re.I),                              lambda _: "TMS"),
    (re.compile(r'\berp\b', re.I),                              lambda _: "ERP"),
    (re.compile(r'\bcrm\b', re.I),                              lambda _: "CRM"),
    (re.compile(r'\bsalesforce\b', re.I),                       lambda _: "Salesforce"),
    (re.compile(r'\bjira\b', re.I),                             lambda _: "Jira"),
    (re.compile(r'\bconfluence\b', re.I),                       lambda _: "Confluence"),
    (re.compile(r'\bpython\b', re.I),                           lambda _: "Python"),
    (re.compile(r'\bjavascript\b|\btypescript\b', re.I),        lambda _: "JavaScript"),
    (re.compile(r'\bsql\b|\bmysql\b|\bpostgresql\b', re.I),    lambda _: "SQL"),
    (re.compile(r'\bautocad\b', re.I),                          lambda _: "AutoCAD"),
    (re.compile(r'\bsolidworks\b', re.I),                       lambda _: "SolidWorks"),
    (re.compile(r'\brevit\b', re.I),                            lambda _: "Revit"),

    # ── Languages ─────────────────────────────────────────────────────────────
    (re.compile(r'\banglais\b|\benglish\b', re.I),              lambda _: "anglais"),
    (re.compile(r'\bespagnol\b|\bspanish\b', re.I),             lambda _: "espagnol"),
    (re.compile(r'\ballemand\b|\bgerman\b', re.I),              lambda _: "allemand"),
    (re.compile(r'\barabe\b|\barabic\b', re.I),                 lambda _: "arabe"),
    (re.compile(r'\bchinois\b|\bmandarin\b', re.I),             lambda _: "chinois"),
    (re.compile(r'\bitalien\b|\bitalian\b', re.I),              lambda _: "italien"),
    (re.compile(r'\bportugais\b|\bportuguese\b', re.I),         lambda _: "portugais"),
]

# Descriptions for known labels; CACES, permis, and hab. levels get auto-generated.
_SKILL_DESCS: dict[str, str] = {
    # ── Habilitation électrique levels (NF C 18-510, source: INRS / egpp-electricite.fr) ──
    "hab. B0":            "B0 — travaux non-électriques au voisinage basse tension (peintre, manutentionnaire en local élec.)",
    "hab. H0":            "H0 — voisinage simple haute tension sans intervention électrique",
    "hab. H0V":           "H0V — voisinage renforcé haute tension (chantier près de postes HTA)",
    "hab. BS":            "BS — remplacement à l'identique sur circuit existant (BT), ex. remplacement fusible/lampe",
    "hab. BR":            "BR — chargé d'intervention générale BT (dépannage, raccordements, consignation pour compte propre)",
    "hab. BC":            "BC — chargé de consignation BT (mise hors tension sécurisée avant intervention tierce)",
    "hab. B1":            "B1 — exécutant de travaux BT hors tension",
    "hab. B1V":           "B1V — exécutant de travaux BT sous tension ou au voisinage",
    "hab. B2":            "B2 — chargé de travaux BT hors tension",
    "hab. B2V":           "B2V — chargé de travaux BT sous tension ou au voisinage",
    "hab. BE":            "BE — opérations spéciales BT (essais, mesures, manœuvres)",
    "hab. H1":            "H1 — exécutant de travaux haute tension hors tension",
    "hab. H2":            "H2 — chargé de travaux haute tension hors tension",
    "hab. HC":            "HC — chargé de consignation haute tension",
    "habilitation élec.": "Habilitation électrique (norme NF C 18-510) — obligatoire pour tout travail en environnement électrique",
    # ── Safety & regulatory ────────────────────────────────────────────────────
    "HACCP":              "HACCP — Hazard Analysis Critical Control Point — obligatoire en restauration/agroalimentaire (paquet hygiène UE). Cert à vie, ~14h, finançable CPF",
    "SST":                "SST / PSC1 — Sauveteur Secouriste du Travail — premiers secours certifiés INRS, exigé sur chantiers BTP et industrie",
    "AIPR":               "AIPR — Autorisation d'Intervention à Proximité des Réseaux — obligatoire travaux fibre/télécom/TP (arrêté 2012)",
    "ADR":                "ADR — transport de marchandises dangereuses par route — obligatoire chauffeurs concernés (accord européen)",
    "ATEX":               "ATEX — Atmosphères Explosibles — habilitation obligatoire pour travailler en zones à risque d'explosion (raffineries, chimie, silos)",
    "FIMO":               "FIMO — Formation Initiale Minimale Obligatoire — requis conducteurs PL/SPL (PTAC > 3,5 t). 140h initiale",
    "FCO":                "FCO — Formation Continue Obligatoire — recyclage tous les 5 ans pour conducteurs routiers (35h)",
    "QHSE":               "QHSE — Qualité Hygiène Sécurité Environnement — norme transverse industrie / BTP / logistique",
    "CQP":                "CQP — Certificat de Qualification Professionnelle — certification de branche (ex: CQP Cariste, CQP Agent restauration, CQP Conducteur). Reconnu RNCP",
    "VAE":                "VAE — Validation des Acquis de l'Expérience — obtenir un diplôme/titre RNCP par l'expérience sans formation formelle",
    # ── Bureautique / numérique ────────────────────────────────────────────────
    "TOSA":               "TOSA — certification bureautique (Excel, Word, PowerPoint, Outlook) inscrite au Répertoire Spécifique (RS) France Compétences, finançable CPF",
    "PIX":                "PIX — certification compétences numériques de base (Éducation Nationale / France Compétences) — 5 domaines, niveaux 1–8",
    "Voltaire":           "Voltaire — certification orthographe et grammaire française — score Voltaire exigé en secrétariat, assistanat, rédaction",
    "TOEIC":              "TOEIC — Test of English for International Communication — score standard exigé par employeurs FR (>785 = bon niveau B2)",
    "TOEFL":              "TOEFL iBT — Test of English as a Foreign Language — plutôt exigé pour candidatures anglophone/international",
    "DELF":               "DELF — Diplôme d'Études en Langue Française — niveau A1 à B2 (délivrés par le CIEP/France Éducation)",
    "DALF":               "DALF — Diplôme Approfondi de Langue Française — niveaux C1/C2 pour locuteurs avancés",
    "Qualiopi":           "Qualiopi — label qualité organismes de formation (obligatoire pour financement CPF depuis 2022)",
    # ── ISO / qualité ──────────────────────────────────────────────────────────
    "ISO 9001":           "ISO 9001 — management de la qualité (processus, amélioration continue) — référence universelle",
    "ISO 14001":          "ISO 14001 — management environnemental (empreinte carbone, déchets)",
    "ISO 45001":          "ISO 45001 — santé et sécurité au travail (remplace OHSAS 18001)",
    "ISO 27001":          "ISO 27001 — sécurité des systèmes d'information (SMSI)",
    "ISO 22000":          "ISO 22000 — sécurité des denrées alimentaires (agroalimentaire, traiteurs)",
    # ── Project management ─────────────────────────────────────────────────────
    "PMP":                "PMP — Project Management Professional (PMI) — 68% offres IT senior l'exigent. Examen 180 questions, 35h PDU requis",
    "CAPM":               "CAPM — Certified Associate Project Management (PMI) — version entrée de gamme du PMP, accessible sans expérience",
    "PRINCE2":            "PRINCE2 — méthode structurée gestion de projet (UK gov, UE, finance). Foundation + Practitioner",
    "Scrum Master":       "Scrum Master Certifié (CSM Scrum Alliance / PSM Scrum.org) — facilitation sprint, backlog, rétrospectives",
    "Product Owner":      "Product Owner Certifié (CSPO / PSPO) — gestion backlog produit, priorisation, user stories",
    "SAFe":               "SAFe — Scaled Agile Framework (SPC, RTE, SA) — agile à l'échelle entreprise (>100 collaborateurs)",
    "Lean Six Sigma":     "Lean Six Sigma Green Belt / Black Belt — réduction défauts (DMAIC) + élimination gaspillages (Lean)",
    "Six Sigma":          "Six Sigma — méthode qualité DMAIC — vise 3,4 défauts par million d'opportunités",
    "ITIL":               "ITIL 4 — gestion des services IT (ITSM) — Foundation très demandé ESN, DSI, help-desk senior",
    "PMO":                "PMO — Project/Programme Management Office — coordination multi-projets et reporting portefeuille",
    # ── Cloud & DevOps ─────────────────────────────────────────────────────────
    "AWS Certified":      "AWS Certified — leader mondial cloud (32% part de marché). Solutions Architect Associate = sésame recruteurs FR. Salaire moyen +25% après certif",
    "Azure Certified":    "Microsoft Azure Certified (AZ-900, AZ-104, AZ-204…) — dominant grands comptes & ESN françaises. +2M certifiés mondialement en 2025",
    "GCP Certified":      "Google Cloud Certified (Professional Cloud Architect / Data Engineer) — croissance la plus rapide des 3 clouds. Très demandé data/IA",
    "CKA":                "CKA — Certified Kubernetes Administrator (CNCF) — standard DevOps/cloud-native, exigé postes SRE, Platform Engineer",
    "CKAD":               "CKAD — Certified Kubernetes Application Developer (CNCF) — pour développeurs déployant sur K8s",
    "Terraform":          "HashiCorp Terraform Associate — Infrastructure as Code (IaC) — standard DevOps multi-cloud, exigé cloud engineers",
    "CCNA":               "CCNA — Cisco Certified Network Associate — réseaux, routage, switching, sécurité de base. Sésame techniciens réseau",
    "CCNP":               "CCNP — Cisco Certified Network Professional — niveau avancé (Enterprise / Security / Data Center)",
    "CISSP":              "CISSP — Certified Information Systems Security Professional (ISC²) — référence cybersécurité senior en France",
    "CEH":                "CEH — Certified Ethical Hacker (EC-Council) — tests d'intrusion, pentest, Red Team",
    "CompTIA":            "CompTIA A+ / Network+ / Security+ — certifications IT entry-level reconnues mondialement (helpdesk, technicien réseau)",
    "Red Hat":            "Red Hat Certified (RHCSA / RHCE) — administration Linux/Enterprise — très demandé en infrastructure on-prem",
    # ── Finance & compta ───────────────────────────────────────────────────────
    "DCG":                "DCG — Diplôme de Comptabilité et de Gestion (niveau 6, Bac+3) — référence comptabilité en France, RNCP",
    "DSCG":               "DSCG — Diplôme Supérieur de Comptabilité et de Gestion (niveau 7, Bac+5) — voie expert-comptable",
    "Gestionnaire de paie": "Gestionnaire de paie (titre RNCP) — une des certifications les plus demandées en France. Forte demande toutes tailles entreprise",
    # ── Digital marketing ──────────────────────────────────────────────────────
    "Google Analytics":   "Google Analytics (GA4) Individual Qualification — en 68% des offres marketing FR (LinkedIn 2024). Gratuit via Google Skillshop",
    "Google Ads":         "Google Ads Certification (Search, Display, Shopping) — gratuit via Google Skillshop. Standard agences pub",
    "Meta Blueprint":     "Meta Blueprint — référence publicité Facebook/Instagram. Meta Certified Media Buying Professional = niveau avancé (~150€)",
    "HubSpot":            "HubSpot Academy — certifications gratuites (inbound, SEO, social media, email). Reconnues par 200k+ entreprises (2025)",
    "SEMrush":            "SEMrush Academy — certifications SEO/SEM gratuites (SEO Toolkit, Content Marketing, PPC) — crédibles pour postes SEO",
    "Yoast":              "Yoast Academy — certification SEO WordPress (gratuite/payante) — valorisée éditeurs web, content managers",
    # ── Software tools ─────────────────────────────────────────────────────────
    "Excel":              "Maîtrise Excel — TCD, formules avancées, Power Query, VBA. Certifiable via TOSA Excel",
    "Power BI":           "Microsoft Power BI — dashboards et analyse de données business (DA-100 = certif officielle Microsoft)",
    "Tableau":            "Tableau — visualisation de données et BI. Tableau Desktop Specialist = certif officielle",
    "SAP":                "SAP ERP — logiciel de gestion d'entreprise (modules MM, WM, EWM, SD, FI). Certification SAP officielle disponible",
    "WMS":                "WMS — Warehouse Management System (Manhattan, Reflex, Generix, SAP EWM…) — pilotage informatisé d'entrepôt",
    "TMS":                "TMS — Transport Management System (Generix, Oracle TMS, SAP TM…) — planification et suivi des transports",
    "ERP":                "ERP — Enterprise Resource Planning (SAP, Oracle, Sage, Cegid, Microsoft Dynamics…)",
    "CRM":                "CRM — Customer Relationship Management (Salesforce, HubSpot, Dynamics 365…)",
    "Salesforce":         "Salesforce — plateforme CRM n°1 mondial. Salesforce Administrator / Developer certif très demandées",
    "Jira":               "Jira (Atlassian) — gestion de projet agile, ticketing — standard tech/ESN/startups",
    "Confluence":         "Confluence (Atlassian) — base de connaissances & documentation — souvent associé à Jira",
    "Python":             "Python — langage de programmation data, automatisation, backend, IA",
    "JavaScript":         "JavaScript / TypeScript — développement web front & back (React, Node.js, Vue…)",
    "SQL":                "SQL — requêtes bases de données relationnelles (MySQL, PostgreSQL, Oracle, SQL Server)",
    "AutoCAD":            "AutoCAD (Autodesk) — dessin assisté par ordinateur — BTP, architecture, industrie mécanique",
    "SolidWorks":         "SolidWorks (Dassault Systèmes) — CAO 3D mécanique, conception industrielle, simulation",
    "Revit":              "Revit (Autodesk) — BIM pour architectes, ingénieurs structure et MEP",
    # ── Languages ──────────────────────────────────────────────────────────────
    "anglais":            "Anglais professionnel — souvent exigé B2/C1. Certifiable via TOEIC (score >785 = B2)",
    "espagnol":           "Espagnol professionnel (B2/C1) — fort atout export, Ibérie, Amérique latine",
    "allemand":           "Allemand professionnel — très valorisé industrie automobile et chimie (Renault, BASF…)",
    "arabe":              "Arabe (dialectal maghrébin ou standard) — valorisé relation client, secteur public, export MENA",
    "chinois":            "Chinois mandarin — fort atout import/export, achat, supply chain Asie",
    "italien":            "Italien professionnel — valorisé mode, luxe, agroalimentaire (partenariats franco-italiens)",
    "portugais":          "Portugais professionnel — valorisé export, logistique, relation client lusophone",
}


def skill_description(label: str) -> str:
    """Return a human-readable description for any detected skill label."""
    if label in _SKILL_DESCS:
        return _SKILL_DESCS[label]
    if label.startswith("CACES R"):
        return f"{label} — certification de conduite d'engins (référentiel {label[6:]})"
    if label.startswith("permis "):
        return f"Permis de conduire catégorie {label[7:]}"
    return label


def detect_skills(title: str, description: str = "") -> list[str]:
    """Extract all skills/certifications from job text (multi-match, regex-based)."""
    text = title + " " + description
    seen: set[str] = set()
    result: list[str] = []
    for pattern, make_label in _MATCHERS:
        for m in pattern.finditer(text):
            label = make_label(m)
            if label not in seen:
                seen.add(label)
                result.append(label)
    return result


class BaseSearcher(ABC):
    @abstractmethod
    def search(self, keywords: str, location: str, count: int = 50) -> list[JobResult]:
        ...
