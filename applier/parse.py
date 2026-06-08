"""
CV parser: extracts text from a PDF, detects job categories via signal matching,
and generates a profiles/*.toml ready for `applier search`.
"""
import re
from pathlib import Path
from typing import Optional

from .query_library import CATEGORIES, LANGUAGE_MAP, FRENCH_CITIES


def _extract_text(pdf_path: Path) -> str:
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber is required: pip install pdfplumber")
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _find_email(text: str) -> str:
    # PDFs sometimes inject spaces mid-token; collapse spaces on lines with '@'
    candidates = []
    for line in text.splitlines():
        if "@" in line:
            candidates.append(line.replace(" ", ""))
    search_text = "\n".join(candidates) if candidates else text
    m = re.search(r"[a-zA-Z0-9.+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", search_text)
    return m.group(0) if m else ""


def _find_phone(text: str) -> str:
    m = re.search(r"(?:0|\+33[\s.\-]?)[1-9](?:[\s.\-]?\d{2}){4}", text)
    return m.group(0).strip() if m else ""


def _find_name(text: str) -> str:
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
            if not any(c.isdigit() for c in line) and "@" not in line and "/" not in line:
                return line
    return ""


def _find_languages(text: str) -> list[str]:
    lower = text.lower()
    return [code for code, kws in LANGUAGE_MAP.items() if any(kw in lower for kw in kws)] or ["fr"]


def _find_location(text: str) -> str:
    lower = text.lower()
    for city in FRENCH_CITIES:
        if city in lower:
            return city.title()
    return "France"


def _rank_categories(text: str) -> list[str]:
    lower = text.lower()
    scores: dict[str, int] = {}
    for cat, info in CATEGORIES.items():
        score = sum(1 for sig in info["signals"] if sig in lower)
        if score > 0:
            scores[cat] = score
    return [cat for cat, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]]


def _toml_str_list(items: list[str]) -> str:
    if not items:
        return "[]"
    lines = "".join(f'    "{item}",\n' for item in items)
    return f"[\n{lines}]"


def _toml_lang_list(langs: list[str]) -> str:
    return "[" + ", ".join(f'"{l}"' for l in langs) + "]"


def generate_profile(
    cv_path: Path,
    letter_path: Optional[Path] = None,
    output: Path = Path("profiles/auto.toml"),
    name_override: str = "",
) -> dict:
    cv_text = _extract_text(cv_path)
    combined = cv_text
    if letter_path and letter_path.exists():
        combined += "\n" + _extract_text(letter_path)

    name = name_override or _find_name(cv_text)
    email = _find_email(cv_text)
    phone = _find_phone(cv_text)
    langs = _find_languages(combined)
    location = _find_location(cv_text)
    categories = _rank_categories(combined)

    roles_fr: list[str] = []
    roles_en: list[str] = []
    for cat in categories:
        info = CATEGORIES[cat]
        for r in info["roles_fr"]:
            if r not in roles_fr:
                roles_fr.append(r)
        for r in info["roles_en"]:
            if r not in roles_en:
                roles_en.append(r)

    toml = f"""\
[candidate]
name = "{name}"
email = "{email}"
phone = "{phone}"
base_location = "{location}"
languages = {_toml_lang_list(langs)}

[aspirations]
# Auto-generated from CV — edit to refine
# Detected categories: {", ".join(categories) or "none detected — add roles manually"}
summary = "Add your job target summary here."
preferred_contract = "CDI"
open_to_cdd = true
open_to_international = false

[search]
roles_fr = {_toml_str_list(roles_fr)}
roles_en = {_toml_str_list(roles_en)}

[[search.locations]]
label = "France"
country = "FR"
linkedin_geo = 105015875
ft_location = ""

[[search.locations]]
label = "Paris"
country = "FR"
linkedin_geo = 104246759
ft_location = "Paris (75)"

[[search.locations]]
label = "Île-de-France"
country = "FR"
linkedin_geo = 104246759
ft_location = "Île-de-France"
"""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(toml, encoding="utf-8")

    return {
        "name": name,
        "email": email,
        "categories": categories,
        "roles_fr_count": len(roles_fr),
        "roles_en_count": len(roles_en),
    }
