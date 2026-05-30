from pathlib import Path

import pandas as pd
import streamlit as st

from src.db_handler import save_analysis_history
from src.ocr_engine import extract_composition_text
from src.recommender import get_risk_status
from src.risk_analyzer import analyze_text


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALLERGEN_DATA_PATH = PROJECT_ROOT / "data" / "allergen_keywords.csv"

SAMPLE_COMPOSITION = (
    "tepung terigu, gula, susu bubuk, lesitin kedelai, "
    "tartrazin, natrium benzoat"
)


st.set_page_config(
    page_title="Analisis Komposisi | SafeBite AI",
    layout="wide",
)


@st.cache_data
def load_allergen_options(file_path: str) -> list[str]:
    allergen_table = pd.read_csv(file_path)
    return allergen_table["category"].dropna().tolist()


def format_category(category: str) -> str:
    return category.replace("_", " ").title()


def parse_custom_allergies(custom_allergies: str) -> list[str]:
    return [
        allergy.strip()
        for allergy in custom_allergies.split(",")
        if allergy.strip()
    ]


def matches_to_dataframe(matches: list[dict]) -> pd.DataFrame:
    rows = []

    for match in matches:
        rows.append(
            {
                "Kategori": format_category(match.get("category", "")),
                "Keyword Terdeteksi": ", ".join(match.get("matched_keywords", [])),
                "Level Risiko": match.get("risk_level", "").title(),
                "Keterangan": match.get("description", ""),
            }
        )

    return pd.DataFrame(rows)


def show_status(status_result: dict) -> None:
    message = f"{status_result['status']}: {status_result['recommendation']}"
    risk_level = status_result["risk_level"]

    if risk_level == "high":
        st.error(message)
    elif risk_level == "medium":
        st.warning(message)
    elif risk_level == "low":
        st.info(message)
    else:
        st.success(message)

    for reason in status_result["reasons"]:
        st.write(f"- {reason}")


def show_profile_allergy_warning(status_result: dict) -> None:
    matched_allergens = status_result["matched_profile_allergens"]

    st.subheader("Peringatan Alergi Profil")

    if not matched_allergens:
        st.success("Tidak ada alergen yang cocok dengan profil pengguna.")
        return

    st.error(
        "Komposisi mengandung alergen yang sesuai dengan profil pengguna: "
        + ", ".join(
            format_category(allergen["category"])
            for allergen in matched_allergens
            if allergen.get("category")
        )
    )

    st.dataframe(
        matches_to_dataframe(matched_allergens),
        hide_index=True,
        width="stretch",
    )


def show_match_table(title: str, matches: list[dict]) -> None:
    st.subheader(title)

    if not matches:
        st.info("Tidak ada keyword yang terdeteksi.")
        return

    st.dataframe(
        matches_to_dataframe(matches),
        hide_index=True,
        width="stretch",
    )


if "composition_input" not in st.session_state:
    st.session_state["composition_input"] = ""


st.title("Analisis Komposisi")
st.caption("Masukkan teks komposisi makanan atau minuman kemasan untuk dianalisis.")

with st.sidebar:
    st.header("Profil Alergi")

    selected_allergies = st.multiselect(
        "Alergi yang diketahui",
        options=load_allergen_options(str(ALLERGEN_DATA_PATH)),
        format_func=format_category,
    )

    custom_allergies = st.text_input(
        "Alergi tambahan",
        placeholder="Contoh: susu, gluten, kedelai",
    )

if st.button("Gunakan Contoh"):
    st.session_state["composition_input"] = SAMPLE_COMPOSITION

with st.form("composition_analysis_form"):
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
        key="composition_input",
        height=180,
        placeholder=SAMPLE_COMPOSITION,
    )

    notes = st.text_area(
        "Catatan tambahan",
        height=90,
        placeholder="Contoh: varian rasa, ukuran kemasan, atau sumber data",
    )

    submitted = st.form_submit_button("Analisis Komposisi", type="primary")

if submitted:
    input_type = "manual_text"

    if input_mode == "Upload gambar label":
        if uploaded_image is None:
            st.warning("Upload gambar label terlebih dahulu.")
            st.stop()

        with st.spinner("Membaca teks komposisi dari gambar..."):
            try:
                composition_text = extract_composition_text(uploaded_image.getvalue())
                input_type = "image_ocr"
            except Exception as error:
                st.error(f"OCR gagal membaca gambar: {error}")
                st.stop()

    if not composition_text.strip():
        st.warning("Masukkan teks komposisi terlebih dahulu.")
        st.stop()

    user_allergies = selected_allergies + parse_custom_allergies(custom_allergies)
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
    metric_col_3.metric("Jumlah Temuan", status_result["total_findings"])

    show_status(status_result)
    show_profile_allergy_warning(status_result)

    if input_type == "image_ocr":
        with st.expander("Teks Hasil OCR"):
            st.write(composition_text)

    with st.expander("Teks Setelah Dibersihkan"):
        st.write(analysis_result["cleaned_text"])

    allergen_tab, additive_tab, risk_tab = st.tabs(
        ["Alergen", "Aditif", "Risiko Konsumsi"]
    )

    with allergen_tab:
        show_match_table("Alergen Terdeteksi", analysis_result["allergens"])

    with additive_tab:
        show_match_table("Aditif Terdeteksi", analysis_result["additives"])

    with risk_tab:
        show_match_table("Risiko Konsumsi Terdeteksi", analysis_result["risks"])
