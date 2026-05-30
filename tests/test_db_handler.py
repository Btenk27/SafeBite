import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import db_handler


class DbHandlerTest(unittest.TestCase):
    def test_database_path_can_be_configured_for_deploy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "persistent" / "safebite.db"

            with patch.dict(os.environ, {"SAFEBITE_DB_PATH": str(database_path)}):
                db_handler.init_db()

                self.assertEqual(db_handler.get_database_path(), database_path)
                self.assertTrue(database_path.exists())
                self.assertTrue(db_handler.get_database_info()["is_custom_path"])

    def test_save_analysis_history_persists_ui_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "safebite.db"

            analysis_result = {
                "input_text": "tepung terigu, susu bubuk",
                "cleaned_text": "tepung terigu susu bubuk",
                "allergens": [{"category": "susu", "matched_keywords": ["susu bubuk"]}],
                "additives": [],
                "risks": [],
            }
            status_result = {
                "status": "Berisiko Tinggi",
                "risk_level": "high",
                "recommendation": "Produk sebaiknya dihindari.",
                "reasons": ["Terdeteksi alergen yang sesuai dengan profil pengguna: susu"],
                "matched_profile_allergens": [
                    {"category": "susu", "matched_keywords": ["susu bubuk"]}
                ],
                "total_findings": 1,
            }

            with patch.dict(os.environ, {"SAFEBITE_DB_PATH": str(database_path)}):
                scan_id = db_handler.save_analysis_history(
                    analysis_result=analysis_result,
                    status_result=status_result,
                    user_allergies=["susu"],
                    product_name="Biskuit Susu",
                    brand_name="SafeSnack",
                    notes="uji deploy",
                    input_type="manual_text",
                )

                history = db_handler.get_analysis_history()
                detail = db_handler.get_analysis_detail(scan_id)

        self.assertEqual(history[0]["brand_name"], "SafeSnack")
        self.assertEqual(history[0]["user_allergies"], ["susu"])
        self.assertEqual(history[0]["total_findings"], 1)
        self.assertEqual(history[0]["input_text"], "tepung terigu, susu bubuk")
        self.assertEqual(detail["notes"], "uji deploy")
        self.assertEqual(detail["risk_level"], "high")
        self.assertEqual(detail["allergens"][0]["category"], "susu")


if __name__ == "__main__":
    unittest.main()
