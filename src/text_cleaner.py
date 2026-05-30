import re


def clean_text(text: str) -> str:
    """Clean ingredient composition text for keyword-based analysis."""
    if text is None:
        return ""

    cleaned_text = str(text).lower()
    cleaned_text = re.sub(r"[^a-z0-9\s-]", " ", cleaned_text)
    cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

    return cleaned_text
