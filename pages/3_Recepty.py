import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Recepty", layout="centered")

# ===== CESTY =====
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("DATA_DIR", "/data")

EXPORT_FILE = os.path.join(DATA_DIR, "export.xlsx")
DEFAULT_EXPORT_FILE = os.path.join(BASE_DIR, "export.xlsx")

RECEPTY_FILE = os.path.join(DATA_DIR, "recepty.xlsx")
RECEPTY_POLOZKY_FILE = os.path.join(DATA_DIR, "recepty_polozky.xlsx")

EXPORT_SHEET = "export"


# ===== POMOCNÉ FUNKCE =====
def clean_value(v):
    if pd.isna(v):
        return ""
    return str(v).strip()


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def ensure_export_file():
    if not os.path.exists(EXPORT_FILE):
        if os.path.exists(DEFAULT_EXPORT_FILE):
            import shutil
            shutil.copy(DEFAULT_EXPORT_FILE, EXPORT_FILE)
        else:
            st.error("Nenašla jsem export.xlsx.")
            st.stop()


def ensure_recepty_file():
    ensure_data_dir()

    cols = ["nazev", "typ", "postup", "poznamka", "updated_at", "updated_by"]

    if not os.path.exists(RECEPTY_FILE):
        pd.DataFrame(columns=cols).to_excel(RECEPTY_FILE, index=False)
    else:
        try:
            df = pd.read_excel(RECEPTY_FILE, engine="openpyxl")
            df.columns = [str(c).strip() for c in df.columns]
            for c in cols:
                if c not in df.columns:
                    df[c] = ""
            df.to_excel(RECEPTY_FILE, index=False)
        except Exception as e:
            st.error(f"Chyba při kontrole recepty.xlsx: {e}")
            st.stop()


def ensure_recepty_polozky_file():
    ensure_data_dir()

    cols = ["nazev", "typ", "surovina", "mnozstvi", "jednotka", "popis", "poradi"]

    if not os.path.exists(RECEPTY_POLOZKY_FILE):
        pd.DataFrame(columns=cols).to_excel(RECEPTY_POLOZKY_FILE, index=False)
    else:
        try:
            df = pd.read_excel(RECEPTY_POLOZKY_FILE, engine="openpyxl")
            df.columns = [str(c).strip() for c in df.columns]
            for c in cols:
                if c not in df.columns:
                    df[c] = ""
            df.to_excel(RECEPTY_POLOZKY_FILE, index=False)
        except Exception as e:
            st.error(f"Chyba při kontrole recepty_polozky.xlsx: {e}")
            st.stop()


def load_export():
    ensure_export_file()
    try:
        df = pd.read_excel(EXPORT_FILE, sheet_name=EXPORT_SHEET, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Chyba při načítání export.xlsx: {e}")
        st.stop()


def load_recepty():
    ensure_recepty_file()
    try:
        df = pd.read_excel(RECEPTY_FILE, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Chyba při načítání recepty.xlsx: {e}")
        st.stop()


def load_recepty_polozky():
    ensure_recepty_polozky_file()
    try:
        df = pd.read_excel(RECEPTY_POLOZKY_FILE, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Chyba při načítání recepty_polozky.xlsx: {e}")
        st.stop()


def save_recepty(df):
    df.to_excel(RECEPTY_FILE, index=False)


def save_recepty_polozky(df):
    df.to_excel(RECEPTY_POLOZKY_FILE, index=False)


def find_exact_col(columns, wanted_name):
    for c in columns:
        if str(c).strip().lower() == wanted_name.strip().lower():
            return c
    return None


def get_recept_header(nazev, typ):
    df = load_recepty()
    if df.empty:
        return "", "", "", ""

    df["nazev"] = df["nazev"].astype(str).str.strip()
    df["typ"] = df["typ"].astype(str).str.strip().str.lower()

    match = df[
        (df["nazev"] == str(nazev).strip()) &
        (df["typ"] == str(typ).strip().lower())
    ]

    if match.empty:
        return "", "", "", ""

    row = match.iloc[0]
    return (
        clean_value(row.get("postup", "")),
        clean_value(row.get("poznamka", "")),
        clean_value(row.get("updated_at", "")),
        clean_value(row.get("updated_by", "")),
    )


def get_recept_items(nazev, typ):
    df = load_recepty_polozky()
    if df.empty:
        return pd.DataFrame(columns=["surovina", "mnozstvi", "jednotka", "popis", "poradi"])

    df["nazev"] = df["nazev"].astype(str).str.strip()
    df["typ"] = df["typ"].astype(str).str.strip().str.lower()

    out = df[
        (df["nazev"] == str(nazev).strip()) &
        (df["typ"] == str(typ).strip().lower())
    ].copy()

    if out.empty:
        return pd.DataFrame(columns=["surovina", "mnozstvi", "jednotka", "popis", "poradi"])

    if "poradi" in out.columns:
        out["poradi_num"] = pd.to_numeric(out["poradi"], errors="coerce").fillna(9999)
        out = out.sort_values(["poradi_num", "surovina"])

    return out


def uloz_recept_header(nazev, typ, postup, poznamka, jmeno):
    df = load_recepty()
    if df.empty:
        df = pd.DataFrame(columns=["nazev", "typ", "postup", "poznamka", "updated_at", "updated_by"])

    df["nazev"] = df["nazev"].astype(str).str.strip()
    df["typ"] = df["typ"].astype(str).str.strip().str.lower()

    nazev_clean = str(nazev).strip()
    typ_clean = str(typ).strip().lower()
    now_str = datetime.now(ZoneInfo("Europe/Prague")).strftime("%Y-%m-%d %H:%M:%S")

    matches = df.index[
        (df["nazev"] == nazev_clean) &
        (df["typ"] == typ_clean)
    ].tolist()

    if matches:
        i = matches[0]
        df.at[i, "postup"] = postup
        df.at[i, "poznamka"] = poznamka
        df.at[i, "updated_at"] = now_str
        df.at[i, "updated_by"] = jmeno
    else:
        new_row = pd.DataFrame([{
            "nazev": nazev_clean,
            "typ": typ_clean,
            "postup": postup,
            "poznamka": poznamka,
            "updated_at": now_str,
            "updated_by": jmeno
        }])
        df = pd.concat([df, new_row], ignore_index=True)

    save_recepty(df)


def uloz_recept_items(nazev, typ, items_df):
    df_all = load_recepty_polozky()

    if df_all.empty:
        df_all = pd.DataFrame(columns=["nazev", "typ", "surovina", "mnozstvi", "jednotka", "popis", "poradi"])

    df_all["nazev"] = df_all["nazev"].astype(str).str.strip()
    df_all["typ"] = df_all["typ"].astype(str).str.strip().str.lower()

    nazev_clean = str(nazev).strip()
    typ_clean = str(typ).strip().lower()

    df_all = df_all[
        ~(
            (df_all["nazev"] == nazev_clean) &
            (df_all["typ"] == typ_clean)
        )
    ].copy()

    if not items_df.empty:
        items_df = items_df.copy()
        items_df["nazev"] = nazev_clean
        items_df["typ"] = typ_clean
        items_df = items_df[["nazev", "typ", "surovina", "mnozstvi", "jednotka", "popis", "poradi"]]
        df_all = pd.concat([df_all, items_df], ignore_index=True)

    save_recepty_polozky(df_all)


# ===== START =====
ensure_data_dir()
ensure_export_file()
ensure_recepty_file()
ensure_recepty_polozky_file()

if "recept_new_items" not in st.session_state:
    st.session_state["recept_new_items"] = []

st.title("Recepty")
st.write("Recepty a komponenty ve stylu kuchyně.")

jmeno = st.selectbox(
    "Kdo upravuje",
    ["Monika", "Ondra", "Lenka", "Mája", "Iveta", "Tomáš", "Eva", "Anička", "Host"]
)

df_export = load_export()
product_col = find_exact_col(df_export.columns, "Název produktu")

produkty = []
if product_col:
    df_export = df_export[df_export[product_col].notna()].copy()
    df_export[product_col] = df_export[product_col].astype(str).str.strip()
    produkty = sorted(df_export[product_col].drop_duplicates().tolist())

df_recepty = load_recepty()
ulozene = []
if not df_recepty.empty:
    df_recepty["nazev"] = df_recepty["nazev"].astype(str).str.strip()
    df_recepty["typ"] = df_recepty["typ"].astype(str).str.strip().str.lower()
    df_recepty["zobrazeni"] = df_recepty.apply(
        lambda r: f"{clean_value(r['nazev'])} ({clean_value(r['typ'])})",
        axis=1
    )
    ulozene = sorted(df_recepty["zobrazeni"].drop_duplicates().tolist())

mode = st.radio(
    "Co chceš otevřít?",
    ["Produkt z exportu", "Nový komponent", "Uložený recept"],
    index=0
)

nazev = ""
typ = ""

if mode == "Produkt z exportu":
    vyber = st.selectbox(
        "Produkt",
        produkty,
        index=None,
        placeholder="Klikni sem a začni psát název produktu"
    )
    if not vyber:
        st.info("Nejdřív vyber produkt.")
        st.stop()
    nazev = vyber
    typ = "produkt"

elif mode == "Nový komponent":
    vlastni = st.text_input(
        "Název komponentu / receptu",
        placeholder="např. lemon curd, vanilkový krém, malinové želé"
    )
    if clean_value(vlastni) == "":
        st.info("Zadej název komponentu.")
        st.stop()
    nazev = clean_value(vlastni)
    typ = "komponent"

else:
    vyber_ulozeny = st.selectbox(
        "Uložený recept",
        ulozene,
        index=None,
        placeholder="Vyber už uložený recept"
    )
    if not vyber_ulozeny:
        st.info("Vyber uložený recept.")
        st.stop()

    if vyber_ulozeny.endswith(")") and " (" in vyber_ulozeny:
        nazev = vyber_ulozeny.rsplit(" (", 1)[0].strip()
        typ = vyber_ulozeny.rsplit(" (", 1)[1].replace(")", "").strip().lower()
    else:
        nazev = vyber_ulozeny.strip()
        typ = "komponent"

postup, poznamka_hlavni, updated_at, updated_by = get_recept_header(nazev, typ)
items_df = get_recept_items(nazev, typ)

st.subheader(nazev)
st.caption(f"Typ: {typ}")

if updated_at or updated_by:
    st.caption(f"Naposledy upravil: {updated_by} | {updated_at}")

st.divider()
st.markdown("### 🧾 Vypsané suroviny")

if items_df.empty and not st.session_state["recept_new_items"]:
    st.info("Recept zatím nemá žádné suroviny.")
else:
    for idx, r in items_df.reset_index(drop=True).iterrows():
        with st.container(border=True):
            st.write(f"**{clean_value(r.get('surovina', ''))}**")

            mnoz = clean_value(r.get("mnozstvi", ""))
            jed = clean_value(r.get("jednotka", ""))
            if mnoz or jed:
                st.write(f"Množství: {mnoz} {jed}".strip())

            popis = clean_value(r.get("popis", ""))
            if popis:
                st.caption(popis)

    for idx, r in enumerate(st.session_state["recept_new_items"]):
        with st.container(border=True):
            st.write(f"**{clean_value(r.get('surovina', ''))}**")
            mnoz = clean_value(r.get("mnozstvi", ""))
            jed = clean_value(r.get("jednotka", ""))
            if mnoz or jed:
                st.write(f"Množství: {mnoz} {jed}".strip())
            popis = clean_value(r.get("popis", ""))
            if popis:
                st.caption(popis)
            st.caption("Nová nepřidaná položka")

st.divider()
st.markdown("### Úpravy surovin receptu")

edit_rows = []
source_df = items_df.reset_index(drop=True).copy()

if source_df.empty:
    source_df = pd.DataFrame(columns=["surovina", "mnozstvi", "jednotka", "popis", "poradi"])

for idx, r in source_df.iterrows():
    with st.container(border=True):
        surovina = st.text_input("Surovina", value=clean_value(r.get("surovina", "")), key=f"s_{idx}")
        mnozstvi = st.text_input("Množství", value=clean_value(r.get("mnozstvi", "")), key=f"m_{idx}")

        current_jednotka = clean_value(r.get("jednotka", ""))
        jednotky = ["g", "kg", "ml", "l", "ks", ""]
        if current_jednotka not in jednotky:
            current_jednotka = ""

        jednotka = st.selectbox(
            "Jednotka",
            jednotky,
            index=jednotky.index(current_jednotka),
            key=f"j_{idx}"
        )

        popis = st.text_input("Poznámka / popis", value=clean_value(r.get("popis", "")), key=f"p_{idx}")

        poradi_raw = pd.to_numeric(r.get("poradi", 1), errors="coerce")
        if pd.isna(poradi_raw) or poradi_raw < 1:
            poradi_raw = 1

        poradi = st.number_input(
            "Pořadí",
            min_value=1,
            step=1,
            value=int(poradi_raw),
            key=f"o_{idx}"
        )

        if clean_value(surovina) != "":
            edit_rows.append({
                "surovina": clean_value(surovina),
                "mnozstvi": clean_value(mnozstvi),
                "jednotka": clean_value(jednotka),
                "popis": clean_value(popis),
                "poradi": int(poradi)
            })

with st.container(border=True):
    st.markdown("**➕ Přidat novou surovinu**")
    nova_surovina = st.text_input("Název nové suroviny", key="nova_surovina")
    nove_mnozstvi = st.text_input("Množství", key="nove_mnozstvi")
    nova_jednotka = st.selectbox("Jednotka", ["g", "kg", "ml", "l", "ks", ""], key="nova_jednotka")
    novy_popis = st.text_input("Poznámka / popis", key="novy_popis")
    nove_poradi = st.number_input(
        "Pořadí nové položky",
        min_value=1,
        step=1,
        value=max(len(edit_rows) + len(st.session_state["recept_new_items"]) + 1, 1),
        key="nove_poradi"
    )

    if st.button("Přidat novou surovinu do seznamu", use_container_width=True):
        if clean_value(nova_surovina) == "":
            st.error("Zadej název nové suroviny.")
        else:
            st.session_state["recept_new_items"].append({
                "surovina": clean_value(nova_surovina),
                "mnozstvi": clean_value(nove_mnozstvi),
                "jednotka": clean_value(nova_jednotka),
                "popis": clean_value(novy_popis),
                "poradi": int(nove_poradi)
            })
            st.success("Nová surovina přidána. Teď klikni na Uložit celý recept.")
            st.rerun()

for x in st.session_state["recept_new_items"]:
    if clean_value(x.get("surovina", "")) != "":
        edit_rows.append({
            "surovina": clean_value(x.get("surovina", "")),
            "mnozstvi": clean_value(x.get("mnozstvi", "")),
            "jednotka": clean_value(x.get("jednotka", "")),
            "popis": clean_value(x.get("popis", "")),
            "poradi": int(x.get("poradi", 1))
        })

st.divider()
st.markdown("### Postup a poznámky")

postup_text = st.text_area(
    "Postup",
    value=postup,
    height=220,
    placeholder="Sem napiš postup receptu..."
)

hlavni_poznamka_text = st.text_area(
    "Obecná poznámka",
    value=poznamka_hlavni,
    height=120,
    placeholder="Sem může a nemusí být poznámka / popis..."
)

if st.button("💾 Uložit celý recept", use_container_width=True):
    items_save_df = pd.DataFrame(
        edit_rows,
        columns=["surovina", "mnozstvi", "jednotka", "popis", "poradi"]
    )

    uloz_recept_header(
        nazev=nazev,
        typ=typ,
        postup=postup_text,
        poznamka=hlavni_poznamka_text,
        jmeno=jmeno
    )

    uloz_recept_items(
        nazev=nazev,
        typ=typ,
        items_df=items_save_df
    )

    st.session_state["recept_new_items"] = []
    st.success("Recept byl uložen.")
    st.rerun()

st.divider()
st.subheader("Stažení souborů")

col1, col2 = st.columns(2)

if os.path.exists(RECEPTY_FILE):
    with open(RECEPTY_FILE, "rb") as f:
        col1.download_button(
            label="📥 Stáhnout recepty.xlsx",
            data=f,
            file_name="recepty.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

if os.path.exists(RECEPTY_POLOZKY_FILE):
    with open(RECEPTY_POLOZKY_FILE, "rb") as f:
        col2.download_button(
            label="📥 Stáhnout recepty_polozky.xlsx",
            data=f,
            file_name="recepty_polozky.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
