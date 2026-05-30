import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.ocr_engine import (
    extract_composition_section_from_detections,
    extract_composition_section,
    extract_composition_text,
    format_ocr_detections,
    get_easyocr_model_storage_directory,
)


class OcrEngineTest(unittest.TestCase):
    def test_format_ocr_detections_sorts_lines_by_position(self):
        raw_detections = [
            ([[10, 40], [80, 40], [80, 55], [10, 55]], "susu bubuk", 0.91),
            ([[10, 10], [90, 10], [90, 25], [10, 25]], "Komposisi: gula", 0.95),
        ]

        text, detections = format_ocr_detections(raw_detections, paragraph=False)

        self.assertEqual(text, "Komposisi: gula\nsusu bubuk")
        self.assertEqual(
            [detection["text"] for detection in detections],
            ["Komposisi: gula", "susu bubuk"],
        )

    def test_extract_composition_section_keeps_only_ingredient_block(self):
        raw_text = "\n".join(
            [
                "Takaran saji 35g",
                "Energi total 140 kkal",
                "Komposisi: Tepung terigu, gula, susu bubuk,",
                "Lesitin kedelai, tartrazin, natrium benzoat",
                "Informasi Nilai Gizi",
                "BPOM RI 123456789",
            ]
        )

        result = extract_composition_section(raw_text)

        self.assertEqual(
            result,
            "Tepung terigu, gula, susu bubuk, Lesitin kedelai, tartrazin, natrium benzoat",
        )

    def test_extract_composition_section_falls_back_to_raw_text_without_marker(self):
        raw_text = "tepung terigu, gula, susu bubuk"

        self.assertEqual(extract_composition_section(raw_text), raw_text)

    def test_extract_composition_section_from_detections_ignores_far_right_column(self):
        detections = [
            {
                "text": "Komposisi:",
                "confidence": 0.84,
                "bbox": [[100, 100], [190, 100], [190, 120], [100, 120]],
            },
            {
                "text": "tepung terigu, gula",
                "confidence": 0.91,
                "bbox": [[220, 105], [500, 105], [500, 125], [220, 125]],
            },
            {
                "text": "Kalsium Calcium",
                "confidence": 0.88,
                "bbox": [[760, 105], [930, 105], [930, 125], [760, 125]],
            },
            {
                "text": "susu bubuk",
                "confidence": 0.91,
                "bbox": [[220, 140], [380, 140], [380, 160], [220, 160]],
            },
            {
                "text": "BPOM RI",
                "confidence": 0.9,
                "bbox": [[220, 210], [330, 210], [330, 230], [220, 230]],
            },
        ]

        result = extract_composition_section_from_detections(detections)

        self.assertEqual(result, "tepung terigu, gula susu bubuk")

    def test_extract_composition_text_uses_line_based_ocr_and_filters_section(self):
        with patch("src.ocr_engine.extract_text_from_image") as extract_mock:
            extract_mock.return_value = {
                "text": "Informasi Nilai Gizi\nKomposisi: gula, susu bubuk\nBPOM RI",
                "detections": [],
                "languages": ["id", "en"],
            }

            result = extract_composition_text("dummy-image")

        self.assertEqual(result, "gula, susu bubuk")
        self.assertFalse(extract_mock.call_args.kwargs["paragraph"])
        self.assertTrue(extract_mock.call_args.kwargs["preprocess"])

    def test_easyocr_model_storage_directory_can_use_persistent_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "easyocr-models"

            with patch.dict(os.environ, {"SAFEBITE_EASYOCR_MODEL_DIR": str(model_path)}):
                result = get_easyocr_model_storage_directory()
                self.assertTrue(model_path.exists())

        self.assertEqual(result, str(model_path))


if __name__ == "__main__":
    unittest.main()
