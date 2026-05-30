import pandas as pd
import streamlit as st

from src.db_handler import get_analysis_detail, get_analysis_history


st.set_page_config(
    page_title="Riwayat Analisis | SafeBite AI",
    layout="wide",
)


def format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "-"


st.title("Riwayat Analisis")
st.caption("Data hasil analisis yang tersimpan di SQLite.")

history = get_analysis_history(limit=100)

if not history:
    st.info("Belum ada riwayat analisis yang tersimpan.")
    st.stop()

history_table = pd.DataFrame(history)
history_table["user_allergies"] = history_table["user_allergies"].apply(format_list)

st.dataframe(
    history_table.rename(
        columns={
            "id": "ID",
            "created_at": "Waktu",
            "product_name": "Produk",
            "brand_name": "Merek",
            "status": "Status",
            "risk_level": "Level Risiko",
            "total_findings": "Temuan",
            "user_allergies": "Profil Alergi",
            "input_text": "Komposisi",
        }
    ),
    hide_index=True,
    width="stretch",
)

selected_id = st.number_input(
    "Lihat detail ID",
    min_value=1,
    max_value=max(item["id"] for item in history),
    value=history[0]["id"],
    step=1,
)

detail = get_analysis_detail(int(selected_id))

if detail is None:
    st.warning("Data dengan ID tersebut tidak ditemukan.")
    st.stop()

st.subheader("Detail Analisis")

detail_col_1, detail_col_2, detail_col_3 = st.columns(3)
detail_col_1.metric("Status", detail["status"])
detail_col_2.metric("Level Risiko", detail["risk_level"].title())
detail_col_3.metric("Temuan", detail["total_findings"])

st.write(f"Produk: {detail['product_name'] or '-'}")
st.write(f"Merek: {detail['brand_name'] or '-'}")
st.write(f"Profil alergi: {format_list(detail['user_allergies'])}")

with st.expander("Teks Komposisi"):
    st.write(detail["input_text"])

with st.expander("Catatan"):
    st.write(detail["notes"] or "-")

with st.expander("Alasan Status"):
    for reason in detail["reasons"]:
        st.write(f"- {reason}")

allergen_tab, additive_tab, risk_tab = st.tabs(
    ["Alergen", "Aditif", "Risiko Konsumsi"]
)

with allergen_tab:
    st.json(detail["allergens"])

with additive_tab:
    st.json(detail["additives"])

with risk_tab:
    st.json(detail["risks"])
