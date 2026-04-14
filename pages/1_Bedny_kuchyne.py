import streamlit as st
import pandas as pd

from utils.bedny_lib import (
    load_df,
    save_df,
    add_task,
    is_open_status,
    format_date_cz,
    today_prague,
    reopen_task,
    delete_task,
)

st.set_page_config(page_title="Bedny - kuchyně", layout="wide")

VEDOUCI = ["Tomáš", "Monika", "Ondra", "Lenka", "Mája", "Iveta", "Eva", "Anička", "Host"]
STATUSES = ["čeká na vyzvednutí", "naplánováno", "volat předem"]

st.title("📦 Evidence beden k vyzvednutí")
st.caption("Sem vedoucí kuchyně zapisuje zákazníky, kde jsou bedny k vrácení.")

df = load_df()

open_df = df[df["stav"].apply(is_open_status)].copy()
done_df = df[df["stav"] == "vyzvednuto"].copy()

a, b, c = st.columns(3)
a.metric("Otevřené", len(open_df))
b.metric("Vyzvednuto", len(done_df))
c.metric("Celkem", len(df))

st.divider()

with st.form("novy_zaznam", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        vytvoril = st.selectbox("Kdo zapisuje", VEDOUCI)
        firma = st.text_input("Firma *")
        adresa = st.text_input("Adresa *")
        telefon = st.text_input("Telefon")

    with col2:
        datum_rozvozu = st.date_input("Datum rozvozu *", value=today_prague(), format="DD.MM.YYYY")
        pocet_beden = st.number_input("Počet beden k vrácení", min_value=0, step=1, value=0)
        stav = st.selectbox("Stav", STATUSES)
        poznamka = st.text_area("Poznámka", placeholder="např. 4 bedny, volat předem, recepce")

    ulozit = st.form_submit_button("Uložit záznam")

if ulozit:
    if not str(firma).strip() or not str(adresa).strip():
        st.error("Firma a adresa jsou povinné.")
    else:
        df = add_task(df, firma, adresa, telefon, datum_rozvozu, poznamka, stav, vytvoril, pocet_beden)
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
    show = show[
        ["id", "firma", "adresa", "telefon", "datum_rozvozu", "pocet_beden", "poznamka", "stav", "vytvoril"]
    ]
    st.dataframe(show, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Přehled všeho")

if df.empty:
    st.info("Zatím žádné záznamy.")
else:
    show_all = df.copy()
    show_all["datum_rozvozu"] = show_all["datum_rozvozu"].apply(format_date_cz)
    show_all["datum_vyzvednuti"] = show_all["datum_vyzvednuti"].apply(format_date_cz)

    show_all["rozdil"] = show_all["pocet_beden"].fillna(0).astype(int) - show_all["vraceno_beden"].fillna(0).astype(int)

    show_all = show_all[
        [
            "id",
            "firma",
            "adresa",
            "telefon",
            "datum_rozvozu",
            "pocet_beden",
            "vraceno_beden",
            "rozdil",
            "poznamka",
            "stav",
            "ridic",
            "datum_vyzvednuti",
            "vytvoril",
        ]
    ]
    st.dataframe(show_all, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Opravy záznamů")

if df.empty:
    st.info("Není co upravovat.")
else:
    ids = [int(x) for x in pd.to_numeric(df["id"], errors="coerce").dropna().tolist()]
    vybrane_id = st.selectbox("Vyber ID záznamu", ids)

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("Vrátit na čeká na vyzvednutí", use_container_width=True):
            df = reopen_task(df, vybrane_id)
            save_df(df)
            st.success("Záznam vrácen zpět mezi otevřené.")
            st.rerun()

    with col_b:
        if st.button("Smazat záznam", use_container_width=True):
            df = delete_task(df, vybrane_id)
            save_df(df)
            st.success("Záznam smazán.")
            st.rerun()
