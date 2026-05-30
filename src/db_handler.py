import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_DIR = PROJECT_ROOT / "database"
DEFAULT_DATABASE_PATH = DEFAULT_DATABASE_DIR / "safebite.db"
DATABASE_PATH_ENV = "SAFEBITE_DB_PATH"

SCAN_HISTORY_EXTRA_COLUMNS = {
    "brand_name": "TEXT",
    "user_allergies": "TEXT",
    "risk_level": "TEXT",
    "reasons": "TEXT",
    "matched_profile_allergens": "TEXT",
    "total_findings": "INTEGER DEFAULT 0",
    "notes": "TEXT",
}


def get_database_path() -> Path:
    configured_path = os.getenv(DATABASE_PATH_ENV, "").strip()

    if configured_path:
        database_path = Path(configured_path).expanduser()
        if not database_path.is_absolute():
            database_path = PROJECT_ROOT / database_path
        return database_path

    return DEFAULT_DATABASE_PATH


def get_database_info() -> dict:
    configured_path = os.getenv(DATABASE_PATH_ENV, "").strip()

    return {
        "path": str(get_database_path()),
        "is_custom_path": bool(configured_path),
        "environment_variable": DATABASE_PATH_ENV,
    }


def get_connection() -> sqlite3.Connection:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_scan_history_columns(connection: sqlite3.Connection) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(scan_history)").fetchall()
    }

    for column_name, column_definition in SCAN_HISTORY_EXTRA_COLUMNS.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE scan_history ADD COLUMN {column_name} {column_definition}"
            )


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT,
                brand_name TEXT,
                input_type TEXT,
                original_text TEXT,
                cleaned_text TEXT,
                detected_allergens TEXT,
                detected_additives TEXT,
                detected_risks TEXT,
                risk_status TEXT,
                risk_level TEXT,
                recommendation TEXT,
                reasons TEXT,
                matched_profile_allergens TEXT,
                user_allergies TEXT,
                total_findings INTEGER DEFAULT 0,
                notes TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        _ensure_scan_history_columns(connection)


def _ensure_json_string(value: Any) -> str:
    if value is None:
        return "{}"

    if isinstance(value, str):
        return value

    return json.dumps(value, ensure_ascii=False)


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None

    return dict(row)


def _load_json(value: Any, default: Any) -> Any:
    if value is None or value == "":
        return default

    if isinstance(value, (dict, list)):
        return value

    if not isinstance(value, str):
        return default

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _get_total_findings(analysis_result: dict, status_result: dict) -> int:
    if status_result.get("total_findings") is not None:
        try:
            return int(status_result.get("total_findings", 0))
        except (TypeError, ValueError):
            pass

    return sum(
        len(analysis_result.get(section_name, []) or [])
        for section_name in ("allergens", "additives", "risks")
    )


def save_scan_result(
    product_name: str,
    input_type: str,
    original_text: str,
    cleaned_text: str,
    detected_allergens: str | dict | list,
    detected_additives: str | dict | list,
    detected_risks: str | dict | list,
    risk_status: str,
    recommendation: str,
    brand_name: str = "",
    user_allergies: str | dict | list | None = None,
    risk_level: str = "",
    reasons: str | dict | list | None = None,
    matched_profile_allergens: str | dict | list | None = None,
    total_findings: int = 0,
    notes: str = "",
) -> int:
    init_db()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO scan_history (
                product_name,
                brand_name,
                input_type,
                original_text,
                cleaned_text,
                detected_allergens,
                detected_additives,
                detected_risks,
                risk_status,
                risk_level,
                recommendation,
                reasons,
                matched_profile_allergens,
                user_allergies,
                total_findings,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_name,
                brand_name,
                input_type,
                original_text,
                cleaned_text,
                _ensure_json_string(detected_allergens),
                _ensure_json_string(detected_additives),
                _ensure_json_string(detected_risks),
                risk_status,
                risk_level,
                recommendation,
                _ensure_json_string(reasons or []),
                _ensure_json_string(matched_profile_allergens or []),
                _ensure_json_string(user_allergies or []),
                int(total_findings or 0),
                notes,
                created_at,
            ),
        )

        return int(cursor.lastrowid)


def get_scan_history() -> list[dict]:
    init_db()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                product_name,
                brand_name,
                input_type,
                risk_status,
                risk_level,
                recommendation,
                user_allergies,
                total_findings,
                original_text,
                created_at
            FROM scan_history
            ORDER BY id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_scan_detail(scan_id: int) -> dict | None:
    init_db()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM scan_history
            WHERE id = ?
            """,
            (scan_id,),
        ).fetchone()

    return _row_to_dict(row)


def delete_scan(scan_id: int) -> bool:
    init_db()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM scan_history
            WHERE id = ?
            """,
            (scan_id,),
        )

        return cursor.rowcount > 0


def initialize_database() -> None:
    init_db()


def save_analysis_history(
    analysis_result: dict,
    status_result: dict,
    user_allergies: list[str] | None = None,
    product_name: str = "",
    brand_name: str = "",
    notes: str = "",
    input_type: str = "manual_text",
) -> int:
    return save_scan_result(
        product_name=product_name,
        brand_name=brand_name,
        input_type=input_type,
        original_text=analysis_result.get("input_text", ""),
        cleaned_text=analysis_result.get("cleaned_text", ""),
        detected_allergens=analysis_result.get("allergens", []),
        detected_additives=analysis_result.get("additives", []),
        detected_risks=analysis_result.get("risks", []),
        risk_status=status_result.get("status", ""),
        risk_level=status_result.get("risk_level", ""),
        recommendation=status_result.get("recommendation", ""),
        reasons=status_result.get("reasons", []),
        matched_profile_allergens=status_result.get("matched_profile_allergens", []),
        user_allergies=user_allergies or [],
        total_findings=_get_total_findings(analysis_result, status_result),
        notes=notes,
    )


def get_analysis_history(limit: int = 50) -> list[dict]:
    history = get_scan_history()[:limit]

    return [
        {
            "id": item["id"],
            "created_at": item["created_at"],
            "product_name": item["product_name"],
            "brand_name": item.get("brand_name") or "",
            "status": item["risk_status"],
            "risk_level": item.get("risk_level") or item["risk_status"],
            "total_findings": int(item.get("total_findings") or 0),
            "user_allergies": _load_json(item.get("user_allergies"), []),
            "input_text": item.get("original_text") or "",
        }
        for item in history
    ]


def get_analysis_detail(analysis_id: int) -> dict | None:
    detail = get_scan_detail(analysis_id)

    if detail is None:
        return None

    reasons = _load_json(detail.get("reasons"), [])
    if not reasons and detail["recommendation"]:
        reasons = [detail["recommendation"]]

    return {
        "id": detail["id"],
        "created_at": detail["created_at"],
        "product_name": detail["product_name"],
        "brand_name": detail.get("brand_name") or "",
        "notes": detail.get("notes") or "",
        "input_text": detail["original_text"],
        "cleaned_text": detail["cleaned_text"],
        "user_allergies": _load_json(detail.get("user_allergies"), []),
        "status": detail["risk_status"],
        "risk_level": detail.get("risk_level") or detail["risk_status"],
        "recommendation": detail["recommendation"],
        "reasons": reasons,
        "matched_profile_allergens": _load_json(
            detail.get("matched_profile_allergens"),
            [],
        ),
        "allergens": _load_json(detail["detected_allergens"], []),
        "additives": _load_json(detail["detected_additives"], []),
        "risks": _load_json(detail["detected_risks"], []),
        "total_findings": int(detail.get("total_findings") or 0),
    }


def count_analysis_history() -> int:
    return len(get_scan_history())


if __name__ == "__main__":
    init_db()

    dummy_id = save_scan_result(
        product_name="Biskuit Susu",
        input_type="manual_text",
        original_text="tepung terigu, gula, susu bubuk, lesitin kedelai",
        cleaned_text="tepung terigu gula susu bubuk lesitin kedelai",
        detected_allergens='{"gluten": ["tepung terigu"], "susu": ["susu bubuk"], "kedelai": ["lesitin kedelai"]}',
        detected_additives="{}",
        detected_risks='{"gula_tinggi": ["gula"]}',
        risk_status="Risiko Personal Tinggi",
        recommendation="Produk mengandung alergen sesuai profil pengguna.",
    )

    print(f"Data dummy tersimpan dengan ID: {dummy_id}")
    print(get_scan_history())
