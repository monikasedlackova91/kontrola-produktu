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
EXPORT_SHEET = "export"


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

    required_columns = [
        "nazev",
        "typ",
        "recept",
        "updated_at",
        "updated_by"
    ]

    if not os.path.exists(RECEPTY_FILE):
        df = pd.DataFrame(columns=required_columns)
        df.to_excel(RECEPTY_FILE, index=False)
    else:
        try:
            df = pd.read_excel(RECEPTY_FILE, engine="openpyxl")
            df.columns = [str(c).strip() for c in df.columns]
            for col in required_columns:
                if col not in df.columns:
                    df[col] = ""
            df.to_excel(RECEPTY_FILE, index=False)
        except Exception as e:
            st.error(f"Chyba při kontrole recepty.xlsx: {e}")
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


def save_recepty(df):
    df.to_excel(RECEPTY_FILE, index=False)


def find_exact_col(columns, wanted_name):
    for c in columns:
        if str(c).strip().lower() == wanted_name.strip().lower():
            return c
    return None


def get_recept(nazev, typ):
    df = load_recepty()

    if df.empty:
        return "", "", ""

    df["nazev"] = df["nazev"].astype(str).str.strip()
    df["typ"] = df["typ"].astype(str).str.strip().str.lower()

    match = df[
        (df["nazev"] == str(nazev).strip()) &
        (df["typ"] == str(typ).strip().lower())
    ]

    if match.empty:
        return "", "", ""

    row = match.iloc[0]
    return (
        clean_value(row.get("recept", "")),
        clean_value(row.get("updated_at", "")),
        clean_value(row.get("updated_by", "")),
    )


def uloz_recept(nazev, typ, recept, jmeno):
    df = load_recepty()

    if df.empty:
        df = pd.DataFrame(columns=[
            "nazev",
            "typ",
            "recept",
            "updated_at",
            "updated_by"
        ])

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
        row_idx = matches[0]
        df.at[row_idx, "recept"] = recept
        df.at[row_idx, "updated_at"] = now_str
        df.at[row_idx, "updated_by"] = jmeno
    else:
        new_row = pd.DataFrame([{
            "nazev": nazev_clean,
            "typ": typ_clean,
            "recept": recept,
            "updated_at": now_str,
            "updated_by": jmeno
        }])
        df = pd.concat([df, new_row], ignore_index=True)

    save_recepty(df)


# ===== START =====
ensure_data_dir()
ensure_export_file()
ensure_recepty_file()

st.title("Recepty")
st.write("Vyber produkt, založ nový komponent nebo otevři už uložený recept.")

jmeno = st.selectbox(
    "Kdo upravuje",
    ["Monika", "Ondra", "Lenka", "Mája", "Iveta", "Tomáš", "Eva", "Anička", "Host"]
)

# ===== DATA =====
df_export = load_export()
df_recepty = load_recepty()

product_col = find_exact_col(df_export.columns, "Název produktu")

produkty = []
if product_col:
    df_export = df_export[df_export[product_col].notna()].copy()
    df_export[product_col] = df_export[product_col].astype(str).str.strip()
    produkty = sorted(df_export[product_col].drop_duplicates().tolist())

ulozene_recepty = []
if not df_recepty.empty:
    df_recepty["nazev"] = df_recepty["nazev"].astype(str).str.strip()
    df_recepty["typ"] = df_recepty["typ"].astype(str).str.strip().str.lower()
    df_recepty["zobrazeni"] = df_recepty.apply(
        lambda r: f"{clean_value(r['nazev'])} ({clean_value(r['typ'])})",
        axis=1
    )
    ulozene_recepty = sorted(df_recepty["zobrazeni"].drop_duplicates().tolist())

# ===== REŽIM =====
recept_mode = st.radio(
    "Co chceš udělat?",
    [
        "Produkt z exportu",
        "Nový komponent / vlastní recept",
        "Zobrazit uložený recept"
    ],
    index=0
)

nazev = ""
typ = ""

if recept_mode == "Produkt z exportu":
    selected = st.selectbox(
        "Produkt",
        produkty,
        index=None,
        placeholder="Klikni sem a začni psát název produktu"
    )

    if not selected:
        st.info("Nejdřív vyber produkt.")
        st.stop()

    nazev = selected
    typ = "produkt"

elif recept_mode == "Nový komponent / vlastní recept":
    vlastni_nazev = st.text_input(
        "Název receptu / komponentu",
        placeholder="např. lemon curd, malinové želé, tvarohový krém"
    )

    if clean_value(vlastni_nazev) == "":
        st.info("Zadej název receptu nebo komponentu.")
        st.stop()

    nazev = clean_value(vlastni_nazev)
    typ = "komponent"

else:
    selected_saved = st.selectbox(
        "Uložený recept",
        ulozene_recepty,
        index=None,
        placeholder="Vyber už uložený recept"
    )

    if not selected_saved:
        st.info("Vyber uložený recept.")
        st.stop()

    # rozparsování "název (typ)"
    if selected_saved.endswith(")") and " (" in selected_saved:
        nazev = selected_saved.rsplit(" (", 1)[0].strip()
        typ = selected_saved.rsplit(" (", 1)[1].replace(")", "").strip().lower()
    else:
        nazev = selected_saved.strip()
        typ = "komponent"

recept, updated_at, updated_by = get_recept(nazev, typ)

with st.container(border=True):
    st.subheader(nazev)
    st.caption(f"Typ: {typ}")

    if recept:
        st.caption(f"Naposledy upravil: {updated_by} | {updated_at}")
    else:
        st.caption("Recept zatím není vyplněný.")

    recept_text = st.text_area(
        "Recept / postup",
        value=recept,
        height=350,
        placeholder="Sem napiš celý recept nebo postup pro kuchyň..."
    )

    if st.button("💾 Uložit recept", use_container_width=True):
        if clean_value(recept_text) == "":
            st.error("Recept je prázdný.")
        else:
            uloz_recept(nazev, typ, recept_text, jmeno)
            st.success("Recept byl uložen.")
            st.rerun()

st.divider()
st.subheader("Stažení souboru")

if os.path.exists(RECEPTY_FILE):
    with open(RECEPTY_FILE, "rb") as f:
        st.download_button(
            label="📥 Stáhnout recepty.xlsx",
            data=f,
            file_name="recepty.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
