import re


OCR_CORRECTION_RULES = (
    # Gluten / wheat family.
    (r"@+\s*iuten", "gluten"),
    (r"\b[gcq]l[uvi1l]ten\b", "gluten"),
    (r"\b[il1|]uten\b", "gluten"),
    (r"\bgiuten\b", "gluten"),
    (r"\btepung\s+ter[il1|]gu\b", "tepung terigu"),
    (r"\bter[il1|]gu\b", "terigu"),
    # Milk family.
    (r"\bbu[0o]uk\b", "bubuk"),
    (r"\bm[il1|]k\s*powd(?:er|ar|eir)?\b", "milk powder"),
    (r"\bm[il1|]k\b", "milk"),
    (r"\bsusu\s+bub(?:uk|0uk|ouk|uok)\b", "susu bubuk"),
    (r"\bwhey\s*powd(?:er|ar|eir)?\b", "whey powder"),
    # Soy / soybean family.
    (r"\bkedel[ao]i?\b", "kedelai"),
    (r"\blest[il1|]n\s+kedelai\b", "lesitin kedelai"),
    (r"\bles[il1|]t[il1|]n\s+kedelai\b", "lesitin kedelai"),
    (r"\bl[ec3]s?[il1|]t[il1|]n\s+kedel[ao]i?\b", "lesitin kedelai"),
    (r"\blec[il1|]th[il1|]n\s+kedel[ao]i?\b", "lecithin kedelai"),
    (r"\bso[vy]lec[il1|]n\b", "soy lecithin"),
    (r"\bsoy\s*l[ec3]c?[il1|]th[il1|]n\b", "soy lecithin"),
    (r"\bsovlec[il1|]n\b", "soy lecithin"),
    # Egg family.
    (r"\bt[ae]l[uo]r\b", "telur"),
    (r"\bte[il1|]ur\b", "telur"),
    (r"\begg\s*powd(?:er|ar|eir)?\b", "egg powder"),
    # Peanut / tree nut family.
    (r"\bpean[uo]t[s]?\b", "peanut"),
    (r"\bkacang\s*tan[ao]h\b", "kacang tanah"),
    (r"\bkacang\s*met[ei]\b", "kacang mete"),
    # Seafood family.
    (r"\bshrim[pb]\b", "shrimp"),
    (r"\bud[ao]ng\b", "udang"),
    (r"\bkep[il1|]t[il1|]ng\b", "kepiting"),
    # Sesame / sulfite family.
    (r"\bses[ao]me\b", "sesame"),
    (r"\bw[il1|]jen\b", "wijen"),
    (r"\bsulf[il1|]te\b", "sulfite"),
    (r"\bsulf[il1|]t\b", "sulfit"),
)


def _normalize_spacing(text: str) -> str:
    corrected_text = re.sub(r"[ \t\r\f\v]+", " ", text)
    corrected_text = re.sub(r"\s+([,.;:)])", r"\1", corrected_text)
    corrected_text = re.sub(r"([(])\s+", r"\1", corrected_text)
    return corrected_text.strip()


def correct_ocr_text(text: str | None) -> str:
    if text is None:
        return ""

    corrected_text = str(text)

    for pattern, replacement in OCR_CORRECTION_RULES:
        corrected_text = re.sub(
            pattern,
            replacement,
            corrected_text,
            flags=re.IGNORECASE,
        )

    return _normalize_spacing(corrected_text)


if __name__ == "__main__":
    sample_text = "Sal Lestin Kedela) Mlk Powder Contains @iuten Talur Buouk"
    print(correct_ocr_text(sample_text))
