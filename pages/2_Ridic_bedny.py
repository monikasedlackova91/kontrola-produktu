from datetime import timedelta

import pandas as pd
import streamlit as st

from utils.bedny_lib import (
    load_df,
    save_df,
    is_open_status,
    format_date_cz,
    mark_done,
    today_prague,
)

st.set_page_config(page_title="Řidič - bedny", layout="centered")

st.markdown("""
<style>
div.stButton > button {
    min-height: 58px;
    font-size: 22px;
    font-weight: 700;
    border-radius: 14px;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}
</style>
""", unsafe_allow_html=True)

st.title("🚚 Bedny k vyzvednutí")
st.caption("Klikni jen na zákazníka, kde jsi bedny opravdu vyzvedl.")

df = load_df()

open_df = df[df["stav"].apply(is_open_status)].copy()

if not open_df.empty:
    open_df["datum_rozvozu_dt"] = pd.to_datetime(open_df["datum_rozvozu"], errors="coerce").dt.date

    # po termínu až když je datum rozvozu starší než včerejšek
    open_df["po_terminu"] = open_df["datum_rozvozu_dt"].apply(
        lambda d: d < (today_prague() - timedelta(days=1)) if pd.notna(d) else False
    )

    # dnešní / včerejší / starší
    open_df["seradit_1"] = open_df["po_terminu"].apply(lambda x: 0 if x else 1)
    open_df["seradit_2"] = open_df["datum_rozvozu_dt"]

    open_df = open_df.sort_values(by=["seradit_1", "seradit_2", "firma"], na_position="last")

# Počítadla
if open_df.empty:
    overdue_count = 0
else:
    overdue_count = int(open_df["po_terminu"].sum())

a, b = st.columns(2)
a.metric("K vyzvednutí", len(open_df))
b.metric("Po termínu", overdue_count)

st.divider()

if open_df.empty:
    st.success("Žádné bedny k vyzvednutí.")
else:
    for _, row in open_df.iterrows():
        with st.container(border=True):
            po_terminu = bool(row["po_terminu"])

            titulek = f"{row['firma']}"
            if po_terminu:
                titulek += "  ⚠️ PO TERMÍNU"

            st.markdown(f"### {titulek}")
            st.write(f"**Adresa:** {row['adresa']}")
            st.write(f"**Telefon:** {row['telefon'] or '—'}")
            st.write(f"**Rozvoz:** {format_date_cz(row['datum_rozvozu'])}")

            if str(row["poznamka"]).strip():
                st.write(f"**Poznámka:** {row['poznamka']}")

            if st.button(
                "✅ VYZVEDNUTO",
                key=f"done_{int(row['id'])}",
                use_container_width=True
            ):
                df = mark_done(df, int(row["id"]), "řidič")
                save_df(df)
                st.success(f"Hotovo: {row['firma']}")
                st.rerun()
