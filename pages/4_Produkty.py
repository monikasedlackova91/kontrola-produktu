import os
import pandas as pd
import streamlit as st
from openpyxl import load_workbook

st.set_page_config(page_title="Produkty", page_icon="🍽️", layout="wide")

DATA_DIR = os.environ.get("DATA_DIR", "/data")
EXPORT_FILE = os.path.join(DATA_DIR, "export.xlsx")
EXPORT_SHEET = "export"


# ========= POMOCNÉ FUNKCE =========
def clean_text(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    return str(v).strip()


def to_number(v):
    if v in [None, ""]:
        return ""
    try:
        val = float(v)
        if val == 0:
            return ""
        return val
    except Exception:
        return ""


def load_export_df():
    if not os.path.exists(EXPORT_FILE):
        return pd.DataFrame()
    return pd.read_excel(EXPORT_FILE, sheet_name=EXPORT_SHEET)


def get_next_id(df):
    if "ID" not in df.columns:
        return ""
    ids = pd.to_numeric(df["ID"], errors="coerce").dropna()
    if ids.empty:
        return 1
    return int(ids.max()) + 1


def append_product_to_export(new_row_dict):
    wb = load_workbook(EXPORT_FILE)

    if EXPORT_SHEET not in wb.sheetnames:
        raise ValueError(f"List '{EXPORT_SHEET}' neexistuje.")

    ws = wb[EXPORT_SHEET]
    headers = [cell.value for cell in ws[1]]
    row_values = [new_row_dict.get(h, "") for h in headers]

    ws.append(row_values)
    wb.save(EXPORT_FILE)


def normalize_colname(name):
    return clean_text(name).lower()


def first_existing_col(df, possible_names):
    norm_map = {normalize_colname(c): c for c in df.columns}
    for name in possible_names:
        if normalize_colname(name) in norm_map:
            return norm_map[normalize_colname(name)]
    return None


def unique_nonempty_from_column(df, col_name):
    if not col_name or col_name not in df.columns:
        return []
    vals = []
    for v in df[col_name].tolist():
        txt = clean_text(v)
        if txt:
            vals.append(txt)
    return sorted(set(vals), key=lambda x: x.lower())


def collect_ingredient_options(df):
    ingredient_cols = []
    for c in df.columns:
        c_norm = normalize_colname(c)
        if "složení" in c_norm or "slozeni" in c_norm:
            ingredient_cols.append(c)

    vals = []
    for c in ingredient_cols:
        vals.extend([clean_text(v) for v in df[c].tolist() if clean_text(v)])

    return sorted(set(vals), key=lambda x: x.lower())


def resolve_value(new_value, selected_value):
    new_value = clean_text(new_value)
    selected_value = clean_text(selected_value)

    if new_value:
        return new_value
    if selected_value == "---":
        return ""
    return selected_value


def build_new_row(headers, df, values):
    row = {h: "" for h in headers}

    for h in headers:
        h_clean = normalize_colname(h)

        if h_clean == "id":
            row[h] = get_next_id(df)

        elif h_clean in ["název produktu", "nazev produktu"]:
            row[h] = clean_text(values["nazev_produktu"])

        elif h_clean == "kategorie":
            row[h] = clean_text(values["kategorie"])

        elif h_clean == "hmotnost":
            row[h] = to_number(values["hmotnost"])

        elif h_clean == "velikost":
            row[h] = to_number(values["velikost"])

        elif h_clean in ["základ", "zaklad"]:
            row[h] = clean_text(values["zaklad"])

        elif h_clean in ["počet ks", "pocet ks", "počet kusů", "pocet kusu"]:
            row[h] = to_number(values["pocet_ks"])

        elif h_clean in ["mazání", "mazani"]:
            row[h] = clean_text(values["mazani"])

        elif h_clean in ["hmotnost mazání", "hmotnost mazani"]:
            row[h] = to_number(values["hmotnost_mazani"])

        elif h_clean in ["složení 1", "slozeni 1"]:
            row[h] = clean_text(values["slozeni_1"])
        elif h_clean == "hmotnost 1":
            row[h] = to_number(values["hmotnost_1"])

        elif h_clean in ["složení 2", "slozeni 2"]:
            row[h] = clean_text(values["slozeni_2"])
        elif h_clean == "hmotnost 2":
            row[h] = to_number(values["hmotnost_2"])

        elif h_clean in ["složení 3", "slozeni 3"]:
            row[h] = clean_text(values["slozeni_3"])
        elif h_clean == "hmotnost 3":
            row[h] = to_number(values["hmotnost_3"])

        elif h_clean in ["složení 4", "slozeni 4"]:
            row[h] = clean_text(values["slozeni_4"])
        elif h_clean == "hmotnost 4":
            row[h] = to_number(values["hmotnost_4"])

        elif h_clean in ["složení 5", "slozeni 5"]:
            row[h] = clean_text(values["slozeni_5"])
        elif h_clean == "hmotnost 5":
            row[h] = to_number(values["hmotnost_5"])

    return row


# ========= UI =========
st.title("Produkty")
st.caption("Přidávání nových produktů do listu export")

try:
    export_df = load_export_df()
except Exception as e:
    st.error(f"Chyba při načtení exportu: {e}")
    st.stop()

if export_df.empty:
    st.error("Soubor export.xlsx nebo list 'export' nebyl nalezen / je prázdný.")
    st.stop()

headers = list(export_df.columns)

# ----- najdeme důležité sloupce -----
col_nazev = first_existing_col(export_df, ["Název produktu", "Nazev produktu"])
col_kategorie = first_existing_col(export_df, ["kategorie", "Kategorie"])
col_zaklad = first_existing_col(export_df, ["základ", "zaklad", "Základ"])
col_mazani = first_existing_col(export_df, ["mazání", "mazani", "Mazání", "Mazani"])

# ----- možnosti do dropdownů -----
default_categories = [
    "Bagety",
    "Chlebíčky",
    "Saláty",
    "Mísy a sety",
    "Mísy a setySaláty",
    "Sladké",
    "Dezerty",
    "Cukrárna",
    "Nápoje",
    "Nádobí",
    "Kanapky",
    "McKinsey",
    "Ostatní",
]

categories_existing = unique_nonempty_from_column(export_df, col_kategorie)
category_options = sorted(set(default_categories + categories_existing), key=lambda x: x.lower())

zaklad_options = unique_nonempty_from_column(export_df, col_zaklad)
mazani_options = unique_nonempty_from_column(export_df, col_mazani)
ingredient_options = collect_ingredient_options(export_df)

tab1, tab2 = st.tabs(["Seznam produktů", "Přidat produkt"])

with tab1:
    st.subheader("Aktuální produkty")

    search_text = st.text_input("Hledat produkt")
    filtered_df = export_df.copy()

    if search_text:
        if col_nazev and col_nazev in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df[col_nazev].astype(str).str.contains(search_text, case=False, na=False)
            ]

    cols_to_show = [c for c in ["ID", "Název produktu", "kategorie", "hmotnost", "velikost"] if c in filtered_df.columns]

    if cols_to_show:
        st.dataframe(filtered_df[cols_to_show], use_container_width=True, height=500)
    else:
        st.dataframe(filtered_df, use_container_width=True, height=500)

with tab2:
    st.subheader("Nový produkt")

    with st.form("novy_produkt_form", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            nazev_produktu = st.text_input("Název produktu *")

            selected_kategorie = st.selectbox(
                "Kategorie - vyber",
                ["---"] + category_options
            )
            nova_kategorie = st.text_input("Kategorie - nebo napiš novou")

            hmotnost = st.number_input("Hmotnost", min_value=0.0, step=1.0)
            velikost = st.number_input("Velikost", min_value=0.0, step=1.0)

            st.markdown("### Základ")

            selected_zaklad = st.selectbox(
                "Základ - vyber",
                ["---"] + zaklad_options
            )
            novy_zaklad = st.text_input("Základ - nebo napiš nový")

            pocet_ks = st.number_input("Počet ks", min_value=0.0, step=1.0)

            selected_mazani = st.selectbox(
                "Mazání - vyber",
                ["---"] + mazani_options
            )
            nove_mazani = st.text_input("Mazání - nebo napiš nové")

            hmotnost_mazani = st.number_input("Hmotnost mazání", min_value=0.0, step=1.0)

        with c2:
            st.markdown("### Složení")

            sel_slozeni_1 = st.selectbox("Složení 1 - vyber", ["---"] + ingredient_options)
            new_slozeni_1 = st.text_input("Složení 1 - nebo napiš nové")
            hmotnost_1 = st.number_input("Hmotnost 1", min_value=0.0, step=1.0)

            sel_slozeni_2 = st.selectbox("Složení 2 - vyber", ["---"] + ingredient_options)
            new_slozeni_2 = st.text_input("Složení 2 - nebo napiš nové")
            hmotnost_2 = st.number_input("Hmotnost 2", min_value=0.0, step=1.0)

            sel_slozeni_3 = st.selectbox("Složení 3 - vyber", ["---"] + ingredient_options)
            new_slozeni_3 = st.text_input("Složení 3 - nebo napiš nové")
            hmotnost_3 = st.number_input("Hmotnost 3", min_value=0.0, step=1.0)

            sel_slozeni_4 = st.selectbox("Složení 4 - vyber", ["---"] + ingredient_options)
            new_slozeni_4 = st.text_input("Složení 4 - nebo napiš nové")
            hmotnost_4 = st.number_input("Hmotnost 4", min_value=0.0, step=1.0)

            sel_slozeni_5 = st.selectbox("Složení 5 - vyber", ["---"] + ingredient_options)
            new_slozeni_5 = st.text_input("Složení 5 - nebo napiš nové")
            hmotnost_5 = st.number_input("Hmotnost 5", min_value=0.0, step=1.0)

        ulozit = st.form_submit_button("Uložit nový produkt")

    if ulozit:
        if not clean_text(nazev_produktu):
            st.error("Vyplň název produktu.")
            st.stop()

        if col_nazev and col_nazev in export_df.columns:
            dup = export_df[col_nazev].astype(str).str.strip().str.lower().eq(
                nazev_produktu.strip().lower()
            ).any()
            if dup:
                st.error("Takový produkt už v exportu existuje.")
                st.stop()

        final_kategorie = resolve_value(nova_kategorie, selected_kategorie)
        final_zaklad = resolve_value(novy_zaklad, selected_zaklad)
        final_mazani = resolve_value(nove_mazani, selected_mazani)

        final_slozeni_1 = resolve_value(new_slozeni_1, sel_slozeni_1)
        final_slozeni_2 = resolve_value(new_slozeni_2, sel_slozeni_2)
        final_slozeni_3 = resolve_value(new_slozeni_3, sel_slozeni_3)
        final_slozeni_4 = resolve_value(new_slozeni_4, sel_slozeni_4)
        final_slozeni_5 = resolve_value(new_slozeni_5, sel_slozeni_5)

        values = {
            "nazev_produktu": nazev_produktu,
            "kategorie": final_kategorie,
            "hmotnost": hmotnost,
            "velikost": velikost,
            "zaklad": final_zaklad,
            "pocet_ks": pocet_ks,
            "mazani": final_mazani,
            "hmotnost_mazani": hmotnost_mazani,
            "slozeni_1": final_slozeni_1,
            "hmotnost_1": hmotnost_1,
            "slozeni_2": final_slozeni_2,
            "hmotnost_2": hmotnost_2,
            "slozeni_3": final_slozeni_3,
            "hmotnost_3": hmotnost_3,
            "slozeni_4": final_slozeni_4,
            "hmotnost_4": hmotnost_4,
            "slozeni_5": final_slozeni_5,
            "hmotnost_5": hmotnost_5,
        }

        try:
            new_row = build_new_row(headers, export_df, values)
            append_product_to_export(new_row)
            st.success(f"Produkt '{nazev_produktu}' byl přidán.")
            st.rerun()
        except Exception as e:
            st.error(f"Uložení selhalo: {e}")
