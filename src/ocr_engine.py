from functools import lru_cache
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

try:
    from src.ocr_correction import correct_ocr_text
except ModuleNotFoundError:
    from ocr_correction import correct_ocr_text


DEFAULT_LANGUAGES = ("id", "en")
EASYOCR_MODEL_DIR_ENV = "SAFEBITE_EASYOCR_MODEL_DIR"

COMPOSITION_MARKERS = (
    "komposisi",
    "composition",
    "ingredient",
    "ingredients",
    "bahan",
)

COMPOSITION_OCR_HINTS = (
    "kompos",
    "mposi",
    "ingred",
)

COMPOSITION_STOP_MARKERS = (
    "informasi nilai gizi",
    "nilai gizi",
    "nutrition facts",
    "nutrition information",
    "takaran saji",
    "serving size",
    "jumlah per sajian",
    "cara penyajian",
    "saran penyajian",
    "petunjuk penyajian",
    "bpom",
    "barcode",
    "kode produksi",
    "diproduksi",
    "produsen",
    "distributor",
    "layanan konsumen",
    "customer service",
    "netto",
    "berat bersih",
    "exp",
    "kedaluwarsa",
)

NUTRITION_COLUMN_MARKERS = (
    "energi",
    "energy",
    "lemak",
    "fat",
    "protein",
    "karbohidrat",
    "carbohydrate",
    "gizi",
    "nutrition",
    "vitamin",
    "kalsium",
    "calcium",
    "kolesterol",
    "cholesterol",
)

COMPOSITION_MARKER_PATTERN = re.compile(
    r"\b(?:komposisi|composition|ingredients?|bahan)\b\s*[:：-]?",
    re.IGNORECASE,
)


def _import_image_dependencies():
    try:
        import cv2
        import numpy as np
        from PIL import Image
    except ModuleNotFoundError as error:
        missing_package = error.name
        raise ModuleNotFoundError(
            f"Package '{missing_package}' belum tersedia. "
            "Install dependency project dengan: pip install -r requirements.txt"
        ) from error

    return cv2, np, Image


def _import_easyocr():
    try:
        import easyocr
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "Package 'easyocr' belum tersedia. "
            "Install dependency project dengan: pip install -r requirements.txt"
        ) from error

    return easyocr


def get_easyocr_model_storage_directory() -> str | None:
    configured_path = os.getenv(EASYOCR_MODEL_DIR_ENV, "").strip()

    if not configured_path:
        return None

    model_storage_path = Path(configured_path).expanduser()
    if not model_storage_path.is_absolute():
        model_storage_path = Path(__file__).resolve().parent.parent / model_storage_path

    model_storage_path.mkdir(parents=True, exist_ok=True)
    return str(model_storage_path)


def _normalize_languages(languages: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if not languages:
        return DEFAULT_LANGUAGES

    return tuple(
        dict.fromkeys(
            language.strip().lower()
            for language in languages
            if language.strip()
        )
    )


def _serialize_bbox(bbox: Any) -> list:
    if hasattr(bbox, "tolist"):
        return bbox.tolist()

    return [
        point.tolist() if hasattr(point, "tolist") else point
        for point in bbox
    ]


def _bbox_points(bbox: Any) -> list[tuple[float, float]]:
    points = []

    for point in _serialize_bbox(bbox):
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue

        try:
            points.append((float(point[0]), float(point[1])))
        except (TypeError, ValueError):
            continue

    return points


def _bbox_sort_key(detection: dict) -> tuple[float, float]:
    points = _bbox_points(detection.get("bbox", []))

    if not points:
        return (0.0, 0.0)

    top = min(point[1] for point in points)
    left = min(point[0] for point in points)

    return (top, left)


def _bbox_edges(detection: dict) -> tuple[float, float, float, float]:
    points = _bbox_points(detection.get("bbox", []))

    if not points:
        return (0.0, 0.0, 0.0, 0.0)

    left = min(point[0] for point in points)
    top = min(point[1] for point in points)
    right = max(point[0] for point in points)
    bottom = max(point[1] for point in points)

    return (left, top, right, bottom)


def _parse_detection(detection: Any) -> tuple[Any, str, float]:
    if len(detection) == 3:
        bbox, text, confidence = detection
        return bbox, text, float(confidence)

    if len(detection) == 2:
        bbox, text = detection
        return bbox, text, 0.0

    raise ValueError(f"Format hasil OCR tidak dikenali: {detection}")


def _normalize_line(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def _normalize_for_marker(text: str) -> str:
    normalized_text = str(text).lower()
    normalized_text = re.sub(r"[^a-z0-9\s]", " ", normalized_text)
    return re.sub(r"\s+", " ", normalized_text).strip()


def _is_composition_marker_token(token: str) -> bool:
    normalized_token = re.sub(r"[^a-z0-9]", "", token.lower())

    if normalized_token in COMPOSITION_MARKERS:
        return True

    return any(hint in normalized_token for hint in COMPOSITION_OCR_HINTS)


def _find_composition_marker_span(line: str) -> tuple[int, int] | None:
    marker_match = COMPOSITION_MARKER_PATTERN.search(line)

    if marker_match:
        return marker_match.span()

    for token_match in re.finditer(r"[A-Za-z0-9]+", line):
        if _is_composition_marker_token(token_match.group(0)):
            return token_match.span()

    return None


def _remove_composition_marker(line: str) -> str:
    marker_span = _find_composition_marker_span(line)

    if marker_span is None:
        return line

    return line[marker_span[1]:].lstrip(" :-;,.|")


def _find_stop_marker_index(line: str) -> int | None:
    normalized_line = _normalize_for_marker(line)

    for marker in COMPOSITION_STOP_MARKERS:
        marker_index = normalized_line.find(marker)
        if marker_index == -1:
            continue

        before_marker = normalized_line[:marker_index]
        return len(before_marker)

    return None


def _truncate_at_stop_marker(line: str) -> tuple[str, bool]:
    marker_index = _find_stop_marker_index(line)

    if marker_index is None:
        return line, False

    return line[:marker_index].strip(" :-;,.|"), True


def _is_nutrition_column_text(text: str) -> bool:
    normalized_text = _normalize_for_marker(text)
    return any(marker in normalized_text for marker in NUTRITION_COLUMN_MARKERS)


def format_ocr_detections(
    ocr_result: list[Any],
    paragraph: bool = False,
) -> tuple[str, list[dict]]:
    detections = []

    for detection in ocr_result:
        bbox, text, confidence = _parse_detection(detection)
        cleaned_text = _normalize_line(text)

        if not cleaned_text:
            continue

        detections.append(
            {
                "text": cleaned_text,
                "confidence": confidence,
                "bbox": _serialize_bbox(bbox),
            }
        )

    if not paragraph:
        detections = sorted(detections, key=_bbox_sort_key)

    separator = " " if paragraph else "\n"
    extracted_text = separator.join(
        detection["text"]
        for detection in detections
    ).strip()

    return extracted_text, detections


def extract_composition_section(text: str) -> str:
    if text is None:
        return ""

    lines = [
        _normalize_line(line)
        for line in str(text).splitlines()
        if _normalize_line(line)
    ]

    if not lines:
        return ""

    collected_lines = []
    collecting = False

    for line in lines:
        candidate_line = line

        if not collecting:
            marker_span = _find_composition_marker_span(line)
            if marker_span is None:
                continue

            collecting = True
            candidate_line = _remove_composition_marker(line)

        truncated_line, should_stop = _truncate_at_stop_marker(candidate_line)

        if truncated_line:
            collected_lines.append(truncated_line)

        if should_stop:
            break

    if collected_lines:
        return " ".join(collected_lines).strip()

    return " ".join(lines).strip()


def extract_composition_section_from_detections(detections: list[dict]) -> str:
    ordered_detections = sorted(
        [
            {
                **detection,
                "text": _normalize_line(detection.get("text", "")),
            }
            for detection in detections
            if _normalize_line(detection.get("text", ""))
        ],
        key=_bbox_sort_key,
    )

    if not ordered_detections:
        return ""

    marker_index = None
    marker_detection = None

    for index, detection in enumerate(ordered_detections):
        if _find_composition_marker_span(detection["text"]) is not None:
            marker_index = index
            marker_detection = detection
            break

    if marker_index is None or marker_detection is None:
        return extract_composition_section(
            "\n".join(detection["text"] for detection in ordered_detections)
        )

    all_edges = [_bbox_edges(detection) for detection in ordered_detections]
    document_left = min(edge[0] for edge in all_edges)
    document_right = max(edge[2] for edge in all_edges)
    document_width = max(document_right - document_left, 1.0)

    marker_left, marker_top, marker_right, marker_bottom = _bbox_edges(marker_detection)
    left_limit = max(document_left, marker_left - max(document_width * 0.08, 80.0))
    right_limit = document_right

    far_right_start = marker_left + (document_width * 0.55)
    far_right_detections = [
        detection
        for detection in ordered_detections[marker_index + 1 :]
        if _bbox_edges(detection)[0] > far_right_start
    ]

    if any(_is_nutrition_column_text(detection["text"]) for detection in far_right_detections):
        right_limit = marker_left + (document_width * 0.65)

    collected_lines = []
    y_tolerance = max((marker_bottom - marker_top) * 0.8, 20.0)

    for index, detection in enumerate(ordered_detections):
        left, top, _, _ = _bbox_edges(detection)

        if top < marker_top - y_tolerance:
            continue

        if left < left_limit or left > right_limit:
            continue

        if index < marker_index and top <= marker_bottom + y_tolerance:
            continue

        candidate_line = detection["text"]

        if index == marker_index:
            candidate_line = _remove_composition_marker(candidate_line)

        truncated_line, should_stop = _truncate_at_stop_marker(candidate_line)

        if truncated_line:
            collected_lines.append(truncated_line)

        if should_stop:
            break

    if collected_lines:
        return " ".join(collected_lines).strip()

    return extract_composition_section(
        "\n".join(detection["text"] for detection in ordered_detections)
    )


def _decode_image_bytes(image_bytes: bytes):
    cv2, np, _ = _import_image_dependencies()
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Data bytes tidak dapat dibaca sebagai gambar.")

    return image


def _load_with_pillow(image_path: Path):
    cv2, np, Image = _import_image_dependencies()

    try:
        try:
            from pillow_heif import register_heif_opener

            register_heif_opener()
        except ModuleNotFoundError:
            pass

        with Image.open(image_path) as image_file:
            rgb_image = image_file.convert("RGB")
    except Exception:
        return None

    image_array = np.array(rgb_image)
    return cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)


def _load_with_imagemagick(image_path: Path):
    magick_path = shutil.which("magick") or shutil.which("convert")

    if magick_path is None:
        return None

    command = [magick_path, str(image_path), "png:-"]
    process = subprocess.run(
        command,
        capture_output=True,
        check=False,
    )

    if process.returncode != 0 or not process.stdout:
        return None

    return _decode_image_bytes(process.stdout)


@lru_cache(maxsize=4)
def get_reader(
    languages: tuple[str, ...] = DEFAULT_LANGUAGES,
    gpu: bool = False,
):
    easyocr = _import_easyocr()
    reader_options = {"gpu": gpu}
    model_storage_directory = get_easyocr_model_storage_directory()

    if model_storage_directory:
        reader_options["model_storage_directory"] = model_storage_directory

    return easyocr.Reader(list(languages), **reader_options)


def load_image(image_source: str | Path | bytes | Any):
    cv2, np, Image = _import_image_dependencies()

    if isinstance(image_source, (str, Path)):
        image_path = Path(image_source)
        image = cv2.imread(str(image_path))

        if image is not None:
            return image

        image = _load_with_pillow(image_path)
        if image is not None:
            return image

        image = _load_with_imagemagick(image_path)
        if image is not None:
            return image

        raise ValueError(
            f"Gambar tidak dapat dibaca: {image_path}. "
            "Gunakan format JPG/PNG, atau install dukungan HEIC dengan: "
            "pip install pillow-heif."
        )

    if isinstance(image_source, bytes):
        return _decode_image_bytes(image_source)

    if isinstance(image_source, Image.Image):
        rgb_image = image_source.convert("RGB")
        image_array = np.array(rgb_image)
        return cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)

    if hasattr(image_source, "read"):
        return load_image(image_source.read())

    if hasattr(image_source, "shape"):
        return image_source

    raise TypeError("Format gambar tidak didukung oleh OCR engine.")


def preprocess_image(image_source: str | Path | bytes | Any):
    cv2, _, _ = _import_image_dependencies()
    image = load_image(image_source)

    if len(image.shape) == 2:
        grayscale_image = image
    elif image.shape[2] == 4:
        grayscale_image = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        grayscale_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    denoised_image = cv2.bilateralFilter(grayscale_image, 9, 75, 75)
    enhanced_image = cv2.equalizeHist(denoised_image)

    return enhanced_image


def extract_text_from_image(
    image_source: str | Path | bytes | Any,
    languages: list[str] | tuple[str, ...] | None = None,
    gpu: bool = False,
    paragraph: bool = False,
    preprocess: bool = True,
) -> dict:
    normalized_languages = _normalize_languages(languages)
    reader = get_reader(normalized_languages, gpu)
    image = preprocess_image(image_source) if preprocess else load_image(image_source)

    ocr_result = reader.readtext(image, detail=1, paragraph=paragraph)
    extracted_text, detections = format_ocr_detections(ocr_result, paragraph=paragraph)

    return {
        "text": extracted_text,
        "detections": detections,
        "languages": list(normalized_languages),
    }


def extract_text(
    image_source: str | Path | bytes | Any,
    languages: list[str] | tuple[str, ...] | None = None,
    gpu: bool = False,
    paragraph: bool = False,
    preprocess: bool = True,
) -> str:
    result = extract_text_from_image(
        image_source=image_source,
        languages=languages,
        gpu=gpu,
        paragraph=paragraph,
        preprocess=preprocess,
    )

    return result["text"]


def extract_composition_text(
    image_source: str | Path | bytes | Any,
    languages: list[str] | tuple[str, ...] | None = None,
) -> str:
    result = extract_text_from_image(
        image_source=image_source,
        languages=languages,
        gpu=False,
        paragraph=False,
        preprocess=True,
    )

    composition_text = (
        extract_composition_section_from_detections(result["detections"])
        or extract_composition_section(result["text"])
    )

    return correct_ocr_text(composition_text)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Gunakan: python src/ocr_engine.py path/ke/gambar.jpg")
        raise SystemExit(0)

    image_path = sys.argv[1]
    print(extract_composition_text(image_path))
