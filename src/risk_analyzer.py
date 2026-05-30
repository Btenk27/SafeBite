import csv
import re
from pathlib import Path
from pprint import pprint

try:
    from src.text_cleaner import clean_text
except ModuleNotFoundError:
    from text_cleaner import clean_text


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

KEYWORD_FILES = {
    "allergens": DATA_DIR / "allergen_keywords.csv",
    "additives": DATA_DIR / "additive_keywords.csv",
    "risks": DATA_DIR / "risk_keywords.csv",
}

RISK_LEVEL_SCORE = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


def _load_keyword_rows(file_path: Path) -> list[dict]:
    rows = []

    with file_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            keywords = [
                keyword.strip()
                for keyword in row.get("keywords", "").split(",")
                if keyword.strip()
            ]

            rows.append(
                {
                    "category": row.get("category", "").strip(),
                    "keywords": keywords,
                    "description": (
                        row.get("description")
                        or row.get("message")
                        or ""
                    ).strip(),
                    "risk_level": row.get("risk_level", "").strip().lower(),
                }
            )

    return rows


def _contains_keyword(cleaned_text: str, cleaned_keyword: str) -> bool:
    if not cleaned_text or not cleaned_keyword:
        return False

    text_variants = {
        cleaned_text,
        cleaned_text.replace("-", " "),
    }

    keyword_variants = {
        cleaned_keyword,
        cleaned_keyword.replace("-", " "),
    }

    for text_variant in text_variants:
        for keyword_variant in keyword_variants:
            pattern = r"(?<![a-z0-9])" + re.escape(keyword_variant) + r"(?![a-z0-9])"
            if re.search(pattern, text_variant):
                return True

    return False


def _filter_specific_keywords(matched_keywords: list[str]) -> list[str]:
    indexed_keywords = [
        (index, keyword, clean_text(keyword).replace("-", " "))
        for index, keyword in enumerate(matched_keywords)
    ]
    selected_keywords = []

    for index, keyword, normalized_keyword in sorted(
        indexed_keywords,
        key=lambda item: len(item[2]),
        reverse=True,
    ):
        is_nested_keyword = any(
            _contains_keyword(selected_keyword[2], normalized_keyword)
            for selected_keyword in selected_keywords
        )

        if not is_nested_keyword:
            selected_keywords.append((index, keyword, normalized_keyword))

    return [
        keyword
        for index, keyword, _ in sorted(selected_keywords, key=lambda item: item[0])
    ]


def _find_matches(cleaned_text: str, keyword_rows: list[dict]) -> list[dict]:
    matches = []

    for row in keyword_rows:
        matched_keywords = []

        for keyword in row["keywords"]:
            cleaned_keyword = clean_text(keyword)
            if _contains_keyword(cleaned_text, cleaned_keyword):
                matched_keywords.append(keyword)

        if matched_keywords:
            matched_keywords = _filter_specific_keywords(matched_keywords)

            matches.append(
                {
                    "category": row["category"],
                    "matched_keywords": matched_keywords,
                    "description": row["description"],
                    "risk_level": row["risk_level"],
                }
            )

    return matches


def _get_highest_risk_level(result_sections: dict[str, list[dict]]) -> str:
    highest_level = "none"
    highest_score = 0

    for matches in result_sections.values():
        for match in matches:
            risk_level = match.get("risk_level", "").lower()
            risk_score = RISK_LEVEL_SCORE.get(risk_level, 0)

            if risk_score > highest_score:
                highest_level = risk_level
                highest_score = risk_score

    return highest_level


def analyze_text(text: str) -> dict:
    cleaned_text = clean_text(text)

    result_sections = {
        section_name: _find_matches(cleaned_text, _load_keyword_rows(file_path))
        for section_name, file_path in KEYWORD_FILES.items()
    }

    total_matches = sum(len(matches) for matches in result_sections.values())

    return {
        "input_text": text or "",
        "cleaned_text": cleaned_text,
        "allergens": result_sections["allergens"],
        "additives": result_sections["additives"],
        "risks": result_sections["risks"],
        "summary": {
            "total_matches": total_matches,
            "highest_risk_level": _get_highest_risk_level(result_sections),
        },
    }


def analyze_composition(text: str) -> dict:
    return analyze_text(text)


if __name__ == "__main__":
    sample_text = "tepung terigu, gula, susu bubuk, lesitin kedelai, tartrazin, natrium benzoat"
    pprint(analyze_text(sample_text), sort_dicts=False)
