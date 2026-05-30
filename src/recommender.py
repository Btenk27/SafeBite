import csv
from pathlib import Path
from pprint import pprint

try:
    from src.text_cleaner import clean_text
except ModuleNotFoundError:
    from text_cleaner import clean_text


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALLERGEN_KEYWORD_FILE = PROJECT_ROOT / "data" / "allergen_keywords.csv"

RISK_LEVEL_SCORE = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
}

STATUS_BY_RISK_LEVEL = {
    "none": "Aman",
    "low": "Risiko Rendah",
    "medium": "Perlu Perhatian",
    "high": "Berisiko Tinggi",
}

RECOMMENDATION_BY_RISK_LEVEL = {
    "none": "Tidak ditemukan keyword risiko pada komposisi yang dianalisis.",
    "low": "Produk relatif aman, tetapi tetap konsumsi dalam jumlah wajar.",
    "medium": "Perhatikan frekuensi konsumsi dan cek kembali bahan yang terdeteksi.",
    "high": "Hindari produk ini jika memiliki alergi atau sensitivitas terkait bahan yang terdeteksi.",
}


def _normalize_profile_item(value: str) -> str:
    return clean_text(value).replace(" ", "_")


def _normalize_match_text(value: str) -> str:
    return clean_text(value).replace("_", " ")


def _normalize_user_allergies(user_allergies: list[str] | None) -> set[str]:
    if not user_allergies:
        return set()

    return {
        _normalize_profile_item(allergy)
        for allergy in user_allergies
        if _normalize_profile_item(allergy)
    }


def _load_allergen_aliases() -> dict[str, set[str]]:
    aliases = {}

    if not ALLERGEN_KEYWORD_FILE.exists():
        return aliases

    with ALLERGEN_KEYWORD_FILE.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            category = row.get("category", "").strip()
            keywords = [
                keyword.strip()
                for keyword in row.get("keywords", "").split(",")
                if keyword.strip()
            ]

            if category:
                aliases[category] = {category, *keywords}

    return aliases


def _is_same_allergy(profile_allergy: str, allergen_value: str) -> bool:
    normalized_profile = _normalize_match_text(profile_allergy)
    normalized_allergen = _normalize_match_text(allergen_value)

    if not normalized_profile or not normalized_allergen:
        return False

    return (
        normalized_profile == normalized_allergen
        or normalized_profile in normalized_allergen.split()
        or normalized_allergen in normalized_profile.split()
    )


def _get_sections(analysis_result: dict) -> dict[str, list[dict]]:
    return {
        "allergens": analysis_result.get("allergens", []) or [],
        "additives": analysis_result.get("additives", []) or [],
        "risks": analysis_result.get("risks", []) or [],
    }


def _get_highest_risk_level(sections: dict[str, list[dict]]) -> str:
    highest_level = "none"
    highest_score = RISK_LEVEL_SCORE[highest_level]

    for matches in sections.values():
        for match in matches:
            risk_level = match.get("risk_level", "none").lower()
            risk_score = RISK_LEVEL_SCORE.get(risk_level, 0)

            if risk_score > highest_score:
                highest_level = risk_level
                highest_score = risk_score

    return highest_level


def _get_matched_profile_allergens(
    allergen_matches: list[dict],
    user_allergies: set[str],
) -> list[dict]:
    if not user_allergies:
        return []

    matched_allergens = []
    allergen_aliases = _load_allergen_aliases()

    for allergen in allergen_matches:
        category = allergen.get("category", "")
        allergen_values = [
            category,
            *allergen.get("matched_keywords", []),
            *allergen_aliases.get(category, set()),
        ]

        if any(
            _is_same_allergy(user_allergy, allergen_value)
            for user_allergy in user_allergies
            for allergen_value in allergen_values
        ):
            matched_allergens.append(allergen)

    return matched_allergens


def _get_status_sections(
    sections: dict[str, list[dict]],
    matched_profile_allergens: list[dict],
) -> dict[str, list[dict]]:
    return {
        "allergens": matched_profile_allergens,
        "additives": sections["additives"],
        "risks": sections["risks"],
    }


def _get_detected_categories(sections: dict[str, list[dict]]) -> list[str]:
    categories = []

    for matches in sections.values():
        for match in matches:
            category = match.get("category", "")
            if category:
                categories.append(category)

    return categories


def _build_reasons(
    status_sections: dict[str, list[dict]],
    matched_profile_allergens: list[dict],
    highest_risk_level: str,
) -> list[str]:
    reasons = []

    if matched_profile_allergens:
        categories = [
            allergen["category"]
            for allergen in matched_profile_allergens
            if allergen.get("category")
        ]
        reasons.append(
            "Terdeteksi alergen yang sesuai dengan profil pengguna: "
            + ", ".join(categories)
        )

    high_risk_categories = [
        match["category"]
        for matches in status_sections.values()
        for match in matches
        if match.get("risk_level") == "high" and match.get("category")
    ]

    if high_risk_categories:
        reasons.append(
            "Terdeteksi kategori risiko tinggi: "
            + ", ".join(high_risk_categories)
        )

    if not reasons and highest_risk_level in {"low", "medium"}:
        categories = _get_detected_categories(status_sections)
        reasons.append(
            "Terdeteksi bahan yang perlu diperhatikan: "
            + ", ".join(categories)
        )

    if not reasons:
        reasons.append("Tidak ada keyword risiko yang cocok dengan data saat ini.")

    return reasons


def get_risk_status(
    analysis_result: dict | None,
    user_allergies: list[str] | None = None,
) -> dict:
    analysis_result = analysis_result or {}
    sections = _get_sections(analysis_result)
    normalized_user_allergies = _normalize_user_allergies(user_allergies)
    matched_profile_allergens = _get_matched_profile_allergens(
        sections["allergens"],
        normalized_user_allergies,
    )
    status_sections = _get_status_sections(sections, matched_profile_allergens)

    highest_risk_level = _get_highest_risk_level(status_sections)

    if matched_profile_allergens:
        highest_risk_level = "high"
        recommendation = (
            "Produk sebaiknya dihindari karena mengandung alergen yang sesuai "
            "dengan profil pengguna."
        )
    else:
        recommendation = RECOMMENDATION_BY_RISK_LEVEL[highest_risk_level]

    total_findings = sum(len(matches) for matches in sections.values())

    return {
        "status": STATUS_BY_RISK_LEVEL[highest_risk_level],
        "risk_level": highest_risk_level,
        "recommendation": recommendation,
        "reasons": _build_reasons(
            status_sections,
            matched_profile_allergens,
            highest_risk_level,
        ),
        "matched_profile_allergens": matched_profile_allergens,
        "total_findings": total_findings,
    }


def recommend_status(
    analysis_result: dict | None,
    user_allergies: list[str] | None = None,
) -> dict:
    return get_risk_status(analysis_result, user_allergies)


if __name__ == "__main__":
    try:
        from src.risk_analyzer import analyze_text
    except ModuleNotFoundError:
        from risk_analyzer import analyze_text

    sample_text = "tepung terigu, gula, susu bubuk, lesitin kedelai, tartrazin, natrium benzoat"
    sample_analysis = analyze_text(sample_text)

    pprint(get_risk_status(sample_analysis, user_allergies=["susu", "kedelai"]), sort_dicts=False)
