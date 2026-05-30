import unittest

from src.ocr_correction import correct_ocr_text
from src.risk_analyzer import analyze_text


class OcrCorrectionTest(unittest.TestCase):
    def test_correct_ocr_text_handles_empty_input(self):
        self.assertEqual(correct_ocr_text(None), "")
        self.assertEqual(correct_ocr_text(""), "")

    def test_correct_ocr_text_fixes_common_allergen_ocr_errors(self):
        raw_text = "Sal Lestin Kedela) Mlk Powder Contains @iuten Talur Buouk"

        corrected_text = correct_ocr_text(raw_text)

        self.assertIn("lesitin kedelai", corrected_text)
        self.assertIn("milk powder", corrected_text)
        self.assertIn("gluten", corrected_text)
        self.assertIn("telur", corrected_text)
        self.assertIn("bubuk", corrected_text)

    def test_correct_ocr_text_fixes_soy_lecithin_variants(self):
        raw_text = "Sovlecin 42N dan soy leciihin"

        corrected_text = correct_ocr_text(raw_text)

        self.assertIn("soy lecithin", corrected_text)

    def test_corrected_ocr_text_can_be_analyzed_for_allergens(self):
        raw_text = "Sal Lestin Kedela Mlk Powder Contains @iuten Talur"

        analysis_result = analyze_text(correct_ocr_text(raw_text))
        detected_categories = {
            match["category"]
            for match in analysis_result["allergens"]
        }

        self.assertTrue({"kedelai", "susu", "gluten", "telur"} <= detected_categories)


if __name__ == "__main__":
    unittest.main()
