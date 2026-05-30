from pathlib import Path

import pandas as pd
import streamlit as st

from src.db_handler import count_analysis_history, save_analysis_history
from src.ocr_engine import extract_composition_text
from src.risk_analyzer import analyze_text
from src.recommender import get_risk_status


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

DATASET_FILES = {
    "Alergen": DATA_DIR / "allergen_keywords.csv",
    "Aditif": DATA_DIR / "additive_keywords.csv",
    "Risiko Konsumsi": DATA_DIR / "risk_keywords.csv",
}

SAMPLE_COMPOSITION = (
    "tepung terigu, gula, susu bubuk, lesitin kedelai, "
    "tartrazin, natrium benzoat"
)


def _set_page(title: str) -> None:
    st.set_page_config(
        page_title=f"{title} | SafeBite AI",
        layout="wide",
    )


@st.cache_data
def _load_dataset(file_path: str) -> pd.DataFrame:
    return pd.read_csv(file_path)


def _load_keyword_tables() -> dict[str, pd.DataFrame]:
    return {
        dataset_name: _load_dataset(str(file_path))
        for dataset_name, file_path in DATASET_FILES.items()
    }


def _split_user_allergies(selected_allergies: list[str], custom_allergies: str) -> list[str]:
    typed_allergies = [
        allergy.strip()
        for allergy in custom_allergies.split(",")
        if allergy.strip()
    ]

    return selected_allergies + typed_allergies


def _format_category(category: str) -> str:
    return category.replace("_", " ").title()


def _get_allergen_options() -> list[str]:
    allergen_table = _load_dataset(str(DATASET_FILES["Alergen"]))
    return allergen_table["category"].dropna().tolist()


def _render_status(status_result: dict) -> None:
    status_text = (
        f"{status_result['status']}: "
        f"{status_result['recommendation']}"
    )
    risk_level = status_result["risk_level"]

    if risk_level == "high":
        st.error(status_text)
    elif risk_level == "medium":
        st.warning(status_text)
    elif risk_level == "low":
        st.info(status_text)
    else:
        st.success(status_text)

    for reason in status_result["reasons"]:
        st.write(f"- {reason}")


def _render_profile_allergy_warning(status_result: dict) -> None:
    matched_allergens = status_result["matched_profile_allergens"]

    st.subheader("Peringatan Alergi Profil")

    if not matched_allergens:
        st.success("Tidak ada alergen yang cocok dengan profil pengguna.")
        return

    st.error(
        "Komposisi mengandung alergen yang sesuai dengan profil pengguna: "
        + ", ".join(
            _format_category(allergen["category"])
            for allergen in matched_allergens
            if allergen.get("category")
        )
    )

    st.dataframe(
        _matches_to_dataframe(matched_allergens),
        hide_index=True,
        width="stretch",
    )


def _matches_to_dataframe(matches: list[dict]) -> pd.DataFrame:
    rows = []

    for match in matches:
        rows.append(
            {
                "Kategori": _format_category(match.get("category", "")),
                "Keyword Terdeteksi": ", ".join(match.get("matched_keywords", [])),
                "Level Risiko": match.get("risk_level", "").title(),
                "Keterangan": match.get("description", ""),
            }
        )

    return pd.DataFrame(rows)


def _render_match_table(title: str, matches: list[dict]) -> None:
    st.subheader(title)

    if not matches:
        st.info("Tidak ada keyword yang terdeteksi.")
        return

    st.dataframe(
        _matches_to_dataframe(matches),
        hide_index=True,
        width="stretch",
    )


def render_analysis_page() -> None:
    _set_page("Analisis Komposisi")

    st.title("SafeBite AI")
    st.caption("Analisis komposisi makanan dan minuman kemasan berbasis keyword matching.")

    allergen_options = _get_allergen_options()

    with st.sidebar:
        st.header("Profil Pengguna")
        selected_allergies = st.multiselect(
            "Alergi yang diketahui",
            options=allergen_options,
            format_func=_format_category,
        )
        custom_allergies = st.text_input(
            "Alergi tambahan",
            placeholder="Contoh: susu, gluten",
        )

    product_col, brand_col = st.columns(2)
    with product_col:
        product_name = st.text_input(
            "Nama produk",
            placeholder="Contoh: Biskuit Cokelat",
        )
    with brand_col:
        brand_name = st.text_input(
            "Merek",
            placeholder="Contoh: SafeSnack",
        )

    input_mode = st.radio(
        "Sumber input",
        options=["Teks manual", "Upload gambar label"],
        horizontal=True,
    )

    uploaded_image = None

    if input_mode == "Upload gambar label":
        uploaded_image = st.file_uploader(
            "Gambar label komposisi",
            type=["jpg", "jpeg", "png"],
        )

    composition_text = st.text_area(
        "Teks komposisi",
        value=st.session_state.get("composition_text", ""),
        placeholder=SAMPLE_COMPOSITION,
        height=180,
    )

    notes = st.text_area(
        "Catatan tambahan",
        height=90,
        placeholder="Contoh: varian rasa, ukuran kemasan, atau sumber data",
    )

    button_col, sample_col = st.columns([1, 1])
    with button_col:
        analyze_clicked = st.button("Analisis Komposisi", type="primary")
    with sample_col:
        sample_clicked = st.button("Gunakan Contoh")

    if sample_clicked:
        st.session_state["composition_text"] = SAMPLE_COMPOSITION
        composition_text = SAMPLE_COMPOSITION

    if analyze_clicked or sample_clicked:
        input_type = "manual_text"

        if input_mode == "Upload gambar label" and not sample_clicked:
            if uploaded_image is None:
                st.warning("Upload gambar label terlebih dahulu.")
                return

            with st.spinner("Membaca teks komposisi dari gambar..."):
                try:
                    composition_text = extract_composition_text(uploaded_image.getvalue())
                    input_type = "image_ocr"
                except Exception as error:
                    st.error(f"OCR gagal membaca gambar: {error}")
                    return

        if not composition_text.strip():
            st.warning("Masukkan teks komposisi terlebih dahulu.")
            return

        user_allergies = _split_user_allergies(selected_allergies, custom_allergies)
        analysis_result = analyze_text(composition_text)
        status_result = get_risk_status(analysis_result, user_allergies)
        history_id = save_analysis_history(
            analysis_result=analysis_result,
            status_result=status_result,
            user_allergies=user_allergies,
            product_name=product_name,
            brand_name=brand_name,
            notes=notes,
            input_type=input_type,
        )

        st.divider()
        st.success(f"Hasil analisis tersimpan ke SQLite dengan ID #{history_id}.")

        metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
        metric_col_1.metric("Status", status_result["status"])
        metric_col_2.metric("Level Risiko", status_result["risk_level"].title())
        metric_col_3.metric("Temuan", status_result["total_findings"])

        _render_status(status_result)
        _render_profile_allergy_warning(status_result)

        if input_type == "image_ocr":
            with st.expander("Teks Hasil OCR"):
                st.write(composition_text)

        with st.expander("Teks Setelah Dibersihkan"):
            st.write(analysis_result["cleaned_text"])

        allergen_tab, additive_tab, risk_tab = st.tabs(
            ["Alergen", "Aditif", "Risiko Konsumsi"]
        )

        with allergen_tab:
            _render_match_table("Alergen Terdeteksi", analysis_result["allergens"])
        with additive_tab:
            _render_match_table("Aditif Terdeteksi", analysis_result["additives"])
        with risk_tab:
            _render_match_table("Risiko Konsumsi Terdeteksi", analysis_result["risks"])


def render_dataset_page() -> None:
    _set_page("Dataset Keyword")

    st.title("Dataset Keyword")
    st.caption("Data CSV yang digunakan untuk keyword matching SafeBite AI.")

    tables = _load_keyword_tables()
    tabs = st.tabs(list(tables.keys()))

    for tab, (dataset_name, table) in zip(tabs, tables.items()):
        with tab:
            keyword_count = table["keywords"].fillna("").apply(
                lambda value: len([item for item in value.split(",") if item.strip()])
            ).sum()

            metric_col_1, metric_col_2 = st.columns(2)
            metric_col_1.metric("Kategori", len(table))
            metric_col_2.metric("Keyword", int(keyword_count))

            st.dataframe(table, hide_index=True, width="stretch")


def render_dashboard_page() -> None:
    _set_page("Dashboard")

    st.title("Dashboard")
    st.caption("Ringkasan cakupan keyword SafeBite AI saat ini.")

    tables = _load_keyword_tables()
    summary_rows = []
    risk_rows = []

    for dataset_name, table in tables.items():
        keyword_count = table["keywords"].fillna("").apply(
            lambda value: len([item for item in value.split(",") if item.strip()])
        ).sum()

        summary_rows.append(
            {
                "Dataset": dataset_name,
                "Kategori": len(table),
                "Keyword": int(keyword_count),
            }
        )

        for risk_level, count in table["risk_level"].value_counts().items():
            risk_rows.append(
                {
                    "Dataset": dataset_name,
                    "Risk Level": risk_level.title(),
                    "Jumlah": count,
                }
            )

    summary_table = pd.DataFrame(summary_rows)
    risk_table = pd.DataFrame(risk_rows)

    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
    metric_col_1.metric("Dataset", len(tables))
    metric_col_2.metric("Kategori", int(summary_table["Kategori"].sum()))
    metric_col_3.metric("Keyword", int(summary_table["Keyword"].sum()))
    metric_col_4.metric("Riwayat", count_analysis_history())

    st.subheader("Cakupan Keyword")
    st.bar_chart(summary_table, x="Dataset", y="Keyword")

    st.subheader("Distribusi Level Risiko")
    risk_chart = risk_table.pivot_table(
        index="Risk Level",
        columns="Dataset",
        values="Jumlah",
        fill_value=0,
    )
    st.bar_chart(risk_chart)

    st.subheader("Ringkasan Dataset")
    st.dataframe(summary_table, hide_index=True, width="stretch")
