import streamlit as st
import pandas as pd

from utils.bedny_lib import (
    load_df,
    save_df,
    add_task,
    is_open_status,
    format_date_cz,
    today_prague,
)

st.set_page_config(page_title="Bedny - kuchyně", layout="wide")

VEDOUCI = ["", "Monika", "Ondra", "Lenka", "Mája", "Iveta", "Eva", "Anička", "Host"]
STATUSES = ["čeká na vyzvednutí", "naplánováno", "volat předem"]

st.title("📦 Evidence beden k vyzvednutí")
st.caption("Sem vedoucí kuchyně zapisuje zákazníky, kde jsou bedny k vrácení.")

df = load_df()

with st.form("novy_zaznam", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        vytvoril = st.selectbox("Kdo zapisuje", VEDOUCI)
        firma = st.text_input("Firma *")
        adresa = st.text_input("Adresa *")
        telefon = st.text_input("Telefon")

    with col2:
        datum_rozvozu = st.date_input("Datum rozvozu *", value=today_prague(), format="DD.MM.YYYY")
        stav = st.selectbox("Stav", STATUSES)
        poznamka = st.text_area("Poznámka", placeholder="např. 4 bedny, volat předem, recepce")

    ulozit = st.form_submit_button("Uložit záznam")

if ulozit:
    if not str(firma).strip() or not str(adresa).strip():
        st.error("Firma a adresa jsou povinné.")
    else:
        df = add_task(df, firma, adresa, telefon, datum_rozvozu, poznamka, stav, vytvoril)
        save_df(df)
        st.success("Záznam uložen.")
        st.rerun()

st.divider()
st.subheader("Otevřené bedny k vyzvednutí")

active_df = df[df["stav"].apply(is_open_status)].copy()

if active_df.empty:
    st.info("Teď tu není nic otevřeného.")
else:
    show = active_df.copy()
    show["datum_rozvozu"] = show["datum_rozvozu"].apply(format_date_cz)
    show = show[["id", "firma", "adresa", "telefon", "datum_rozvozu", "poznamka", "stav", "vytvoril"]]
    st.dataframe(show, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Přehled všeho")

if df.empty:
    st.info("Zatím žádné záznamy.")
else:
    show_all = df.copy()
    show_all["datum_rozvozu"] = show_all["datum_rozvozu"].apply(format_date_cz)
    show_all["datum_vyzvednuti"] = show_all["datum_vyzvednuti"].apply(format_date_cz)
    show_all = show_all[
        ["id", "firma", "adresa", "telefon", "datum_rozvozu", "poznamka", "stav", "ridic", "datum_vyzvednuti", "vytvoril"]
    ]
    st.dataframe(show_all, use_container_width=True, hide_index=True)
