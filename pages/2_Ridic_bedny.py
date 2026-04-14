import streamlit as st

from utils.bedny_lib import load_df, save_df, is_open_status, format_date_cz, mark_done, today_prague

st.set_page_config(page_title="Řidič - bedny", layout="centered")

st.title("🚚 Bedny k vyzvednutí")
st.caption("Klikni pouze na zákazníka, kde jsi bedny opravdu vyzvedl.")

df = load_df()

open_df = df[df["stav"].apply(is_open_status)].copy()
open_df = open_df.sort_values(by=["datum_rozvozu", "firma"], na_position="last")

if open_df.empty:
    st.success("Žádné bedny k vyzvednutí.")
else:
    for _, row in open_df.iterrows():
        with st.container(border=True):
            po_terminu = row["datum_rozvozu"] < today_prague() if row["datum_rozvozu"] else False

            titulek = f"{row['firma']}"
            if po_terminu:
                titulek += "  ⚠️"

            st.markdown(f"### {titulek}")
            st.write(f"**Adresa:** {row['adresa']}")
            st.write(f"**Telefon:** {row['telefon'] or '—'}")
            st.write(f"**Rozvoz:** {format_date_cz(row['datum_rozvozu'])}")

            if str(row["poznamka"]).strip():
                st.write(f"**Poznámka:** {row['poznamka']}")

            if st.button(f"✅ VYZVEDNUTO", key=f"done_{int(row['id'])}", use_container_width=True):
                df = mark_done(df, int(row["id"]), "řidič")
                save_df(df)
                st.success(f"Hotovo: {row['firma']}")
                st.rerun()
