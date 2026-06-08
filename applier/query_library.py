"""
Curated map of CV signals → job search queries.
Signals are lowercase keywords found in CV text.
"""

CATEGORIES: dict[str, dict] = {
    "it_commercial": {
        "signals": [
            "commercial", "vente", "sales", "technico-commercial", "b2b",
            "prospection", "closing", "portefeuille client", "chiffre d'affaires",
            "account manager", "business development", "account executive",
        ],
        "roles_fr": [
            "technico-commercial IT",
            "commercial IT matériel informatique",
            "ingénieur avant-vente informatique",
            "chargé d'affaires IT",
        ],
        "roles_en": [
            "IT sales engineer",
            "pre-sales engineer IT",
            "technical account manager",
            "IT business development",
        ],
    },
    "it_support": {
        "signals": [
            "support", "helpdesk", "help desk", "technicien", "technicien informatique",
            "maintenance", "incidents", "ticketing", "itsm", "l1", "l2", "n1", "n2",
            "dépannage", "troubleshooting", "assistance technique",
        ],
        "roles_fr": [
            "technicien support N2 N3",
            "technicien informatique",
            "administrateur systèmes et réseaux",
            "support informatique",
        ],
        "roles_en": [
            "IT support engineer",
            "desktop support specialist",
            "systems administrator",
            "IT technician",
        ],
    },
    "digital_workplace": {
        "signals": [
            "digital workplace", "microsoft 365", "office 365", "sharepoint",
            "teams", "intune", "endpoint", "poste de travail",
            "déploiement", "migration", "onboarding it",
        ],
        "roles_fr": [
            "digital workplace",
            "technicien poste de travail",
            "IT coordinator",
            "responsable IT PME",
        ],
        "roles_en": [
            "digital workplace specialist",
            "IT coordinator",
            "end user computing specialist",
        ],
    },
    "project_management": {
        "signals": [
            "chef de projet", "project manager", "agile", "scrum", "kanban",
            "pmo", "roadmap", "planning", "coordination projet", "pilotage",
            "gestion de projet",
        ],
        "roles_fr": [
            "chef de projet IT",
            "coordinateur projet digital",
            "chef de projet digital",
            "responsable transformation digitale",
        ],
        "roles_en": [
            "IT project manager",
            "digital project coordinator",
            "program manager IT",
        ],
    },
    "software_dev": {
        "signals": [
            "python", "java", "javascript", "typescript", "react", "vue",
            "développeur", "developer", "software engineer", "backend", "frontend",
            "fullstack", "full-stack", "api", "git", "docker", "kubernetes",
            "node", "django", "flask", "fastapi", "spring",
        ],
        "roles_fr": [
            "développeur Python",
            "développeur backend",
            "développeur fullstack",
            "ingénieur logiciel",
        ],
        "roles_en": [
            "software engineer",
            "backend developer",
            "fullstack developer",
            "Python developer",
        ],
    },
    "data": {
        "signals": [
            "sql", "power bi", "tableau", "data analyst", "pandas", "numpy",
            "machine learning", "statistiques", "business intelligence", "bi",
            "reporting", "datawarehouse", "etl", "data engineering",
        ],
        "roles_fr": [
            "data analyst",
            "business analyst",
            "analyste données",
            "chargé de reporting",
        ],
        "roles_en": [
            "data analyst",
            "business intelligence analyst",
            "data engineer",
        ],
    },
    "network_infra": {
        "signals": [
            "réseau", "cisco", "linux", "windows server", "azure", "aws",
            "firewall", "vpn", "tcp/ip", "active directory", "infrastructure it",
            "virtualisation", "vmware", "hyper-v", "cloud",
        ],
        "roles_fr": [
            "administrateur réseau",
            "ingénieur infrastructure",
            "administrateur systèmes",
            "responsable infrastructure IT",
        ],
        "roles_en": [
            "network engineer",
            "infrastructure engineer",
            "cloud engineer",
            "systems engineer",
        ],
    },
    "marketing_digital": {
        "signals": [
            "marketing digital", "seo", "sem", "content marketing",
            "réseaux sociaux", "community manager", "social media", "emailing",
            "google analytics", "google ads", "meta ads", "growth hacking",
        ],
        "roles_fr": [
            "chargé de marketing digital",
            "chef de projet digital",
            "responsable marketing digital",
            "community manager",
        ],
        "roles_en": [
            "digital marketing manager",
            "growth marketer",
            "digital project manager",
            "marketing coordinator",
        ],
    },
    "product": {
        "signals": [
            "product manager", "product owner", "chef de produit", "roadmap produit",
            "user stories", "backlog", "ux research", "design thinking",
        ],
        "roles_fr": [
            "product manager",
            "product owner",
            "chef de produit digital",
        ],
        "roles_en": [
            "product manager",
            "product owner",
            "digital product manager",
        ],
    },
    "cybersecurity": {
        "signals": [
            "sécurité informatique", "cybersécurité", "cybersecurity", "pentest",
            "soc analyst", "rssi", "ciso", "iso 27001", "rgpd", "audit sécurité",
            "vulnerability", "intrusion",
        ],
        "roles_fr": [
            "analyste cybersécurité",
            "consultant sécurité informatique",
            "ingénieur sécurité",
        ],
        "roles_en": [
            "cybersecurity analyst",
            "security engineer",
            "information security analyst",
        ],
    },
}

LANGUAGE_MAP: dict[str, list[str]] = {
    "fr": ["français", "french", "francophone", "langue maternelle"],
    "en": ["anglais", "english", "anglophone"],
    "ar": ["arabe", "arabic"],
    "es": ["espagnol", "spanish"],
    "de": ["allemand", "german"],
    "pt": ["portugais", "portuguese"],
    "zh": ["chinois", "chinese", "mandarin"],
}

FRENCH_CITIES = [
    "paris", "lyon", "marseille", "toulouse", "bordeaux", "nantes",
    "lille", "nice", "strasbourg", "rennes", "grenoble", "montpellier",
    "île-de-france", "hauts-de-seine", "val-de-marne",
    "arcueil", "boulogne", "versailles", "massy", "saclay",
]
