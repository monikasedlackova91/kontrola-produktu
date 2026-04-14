import os
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Kontrola produktů", layout="centered")

# ===== CESTY K SOUBORŮM =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", "/data")

DEFAULT_EXPORT_FILE = os.path.join(BASE_DIR, "export.xlsx")
EXPORT_FILE = os.path.join(DATA_DIR, "export.xlsx")
OPRAVY_FILE = os.path.join(DATA_DIR, "opravy.xlsx")
EXPORT_SHEET = "export"


def clean_value(v):
    if pd.isna(v):
        return ""
    return str(v).strip()


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def ensure_export_file():
    """
    Pokud ještě v /data není export.xlsx, zkopíruje se tam výchozí export.xlsx
    z repozitáře (vedle app.py).
    """
    ensure_data_dir()

    if not os.path.exists(EXPORT_FILE):
        if os.path.exists(DEFAULT_EXPORT_FILE):
            shutil.copy(DEFAULT_EXPORT_FILE, EXPORT_FILE)
        else:
            st.error(
                f"Nenašla jsem export.xlsx ani v {EXPORT_FILE}, ani výchozí soubor v {DEFAULT_EXPORT_FILE}."
            )
            st.stop()


def ensure_opravy_file():
    ensure_data_dir()

    if not os.path.exists(OPRAVY_FILE):
        df = pd.DataFrame(columns=[
            "datum",
            "jmeno",
            "produkt",
            "typ",
            "surovina",
            "puvodni_gramaz",
            "nova_gramaz",
            "poznamka",
            "stav"
        ])
        df.to_excel(OPRAVY_FILE, index=False)


def load_export():
    ensure_export_file()

    try:
        df = pd.read_excel(EXPORT_FILE, sheet_name=EXPORT_SHEET, engine="openpyxl")
    except Exception as e:
        st.error(f"Chyba při načítání export.xlsx: {e}")
        st.stop()

    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_opravy():
    ensure_opravy_file()

    try:
        df = pd.read_excel(OPRAVY_FILE, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Chyba při načítání oprav.xlsx: {e}")
        st.stop()


def save_opravy(df):
    ensure_data_dir()
    df.to_excel(OPRAVY_FILE, index=False)


def save_export(df):
    ensure_data_dir()
    df.to_excel(EXPORT_FILE, sheet_name=EXPORT_SHEET, index=False)


def uloz_opravu(jmeno, produkt, typ, surovina, puvodni, nova, poznamka):
    df_old = load_opravy()

    new_row = pd.DataFrame([{
        "datum": datetime.now(ZoneInfo("Europe/Prague")).strftime("%Y-%m-%d %H:%M:%S"),
        "jmeno": jmeno,
        "produkt": produkt,
        "typ": typ,
        "surovina": surovina,
        "puvodni_gramaz": puvodni,
        "nova_gramaz": nova,
        "poznamka": poznamka,
        "stav": "NOVÉ"
    }])

    df_new = pd.concat([df_old, new_row], ignore_index=True)
    save_opravy(df_new)


def find_exact_col(columns, wanted_name):
    for c in columns:
        if str(c).strip().lower() == wanted_name.strip().lower():
            return c
    return None


def find_startswith_col(columns, wanted_start):
    for c in columns:
        if str(c).strip().lower().startswith(wanted_start.strip().lower()):
            return c
    return None


def parse_product_row(row):
    items = []
    cols = list(row.index)

    col_zaklad = find_exact_col(cols, "Základ")
    col_pocet = find_exact_col(cols, "počet kusů pečiva")
    col_mazani = find_exact_col(cols, "mazání")
    col_hm_mazani = find_startswith_col(cols, "hmotnost suroviny")

    # Základ
    if col_zaklad:
        zaklad = clean_value(row[col_zaklad])
        if zaklad:
            hodnota = row[col_pocet] if col_pocet else ""
            if pd.isna(hodnota):
                hodnota = ""
            items.append({
                "typ": "Základ",
                "surovina": zaklad,
                "gramaz": hodnota
            })

    # Mazání
    if col_mazani:
        mazani = clean_value(row[col_mazani])
        if mazani:
            gramaz = row[col_hm_mazani] if col_hm_mazani else ""
            if pd.isna(gramaz):
                gramaz = ""
            items.append({
                "typ": "Mazání",
                "surovina": mazani,
                "gramaz": gramaz
            })

    # Složení 1..18
    for i in range(1, 19):
        col_slozeni = find_exact_col(cols, f"složení {i}")
        if not col_slozeni:
            col_slozeni = find_exact_col(cols, f"slozeni {i}")

        col_hmotnost = None
        for c in cols:
            c_text = str(c).strip().lower()
            if c_text.startswith(f"hmotnost {i}"):
                col_hmotnost = c
                break

        if col_slozeni:
            surovina = clean_value(row[col_slozeni])
            gramaz = row[col_hmotnost] if col_hmotnost else ""
            if pd.isna(gramaz):
                gramaz = ""

            if surovina:
                items.append({
                    "typ": "Složení",
                    "surovina": surovina,
                    "gramaz": gramaz
                })

    return items


def get_default_numeric_value(value):
    if pd.isna(value) or value == "":
        return 0.0

    try:
        return float(value)
    except Exception:
        return 0.0


def convert_number_for_excel(value):
    try:
        num = float(value)
        if abs(num - round(num)) < 0.000001:
            return int(round(num))
        return num
    except Exception:
        return value


def propsat_opravu_do_exportu(produkt, typ, surovina, nova_hodnota):
    """
    Vrací (True, zprava) při úspěchu, jinak (False, chyba).
    """
    try:
        df_export = pd.read_excel(EXPORT_FILE, sheet_name=EXPORT_SHEET, engine="openpyxl")
    except Exception as e:
        return False, f"Chyba při načtení export.xlsx: {e}"

    df_export.columns = [str(c).strip() for c in df_export.columns]

    product_col = find_exact_col(df_export.columns, "Název produktu")
    if not product_col:
        return False, "V export.xlsx chybí sloupec 'Název produktu'."

    df_export[product_col] = df_export[product_col].astype(str).str.strip()

    matches = df_export.index[df_export[product_col] == str(produkt).strip()].tolist()
    if not matches:
        return False, f"Produkt '{produkt}' nebyl v export.xlsx nalezen."

    row_idx = matches[0]
    cols = list(df_export.columns)
    nova_hodnota_excel = convert_number_for_excel(nova_hodnota)

    if clean_value(typ) == "Základ":
        col_zaklad = find_exact_col(cols, "Základ")
        col_pocet = find_exact_col(cols, "počet kusů pečiva")

        if not col_zaklad:
            return False, "V export.xlsx chybí sloupec 'Základ'."
        if not col_pocet:
            return False, "V export.xlsx chybí sloupec 'počet kusů pečiva'."

        export_surovina = clean_value(df_export.at[row_idx, col_zaklad])
        if export_surovina != clean_value(surovina):
            return False, (
                f"U produktu '{produkt}' nesedí základ. "
                f"V exportu je '{export_surovina}', ale oprava je pro '{surovina}'."
            )

        df_export.at[row_idx, col_pocet] = nova_hodnota_excel

    elif clean_value(typ) == "Mazání":
        col_mazani = find_exact_col(cols, "mazání")
        col_hm_mazani = find_startswith_col(cols, "hmotnost suroviny")

        if not col_mazani:
            return False, "V export.xlsx chybí sloupec 'mazání'."
        if not col_hm_mazani:
            return False, "V export.xlsx chybí sloupec začínající na 'hmotnost suroviny'."

        export_surovina = clean_value(df_export.at[row_idx, col_mazani])
        if export_surovina != clean_value(surovina):
            return False, (
                f"U produktu '{produkt}' nesedí mazání. "
                f"V exportu je '{export_surovina}', ale oprava je pro '{surovina}'."
            )

        df_export.at[row_idx, col_hm_mazani] = nova_hodnota_excel

    elif clean_value(typ) == "Složení":
        found = False

        for i in range(1, 19):
            col_slozeni = find_exact_col(cols, f"složení {i}")
            if not col_slozeni:
                col_slozeni = find_exact_col(cols, f"slozeni {i}")

            if not col_slozeni:
                continue

            export_surovina = clean_value(df_export.at[row_idx, col_slozeni])

            if export_surovina == clean_value(surovina):
                col_hmotnost = None
                for c in cols:
                    c_text = str(c).strip().lower()
                    if c_text.startswith(f"hmotnost {i}"):
                        col_hmotnost = c
                        break

                if not col_hmotnost:
                    return False, f"Nenašla jsem sloupec pro 'hmotnost {i}' u suroviny '{surovina}'."

                df_export.at[row_idx, col_hmotnost] = nova_hodnota_excel
                found = True
                break

        if not found:
            return False, f"U produktu '{produkt}' jsem nenašla ve složení surovinu '{surovina}'."

    else:
        return False, f"Neznámý typ položky: '{typ}'."

    try:
        save_export(df_export)
    except Exception as e:
        return False, f"Chyba při ukládání export.xlsx: {e}"

    return True, f"Oprava byla propsána do export.xlsx pro produkt '{produkt}'."


# ===== START APPKY =====
ensure_data_dir()
ensure_export_file()
ensure_opravy_file()

if "changes" not in st.session_state:
    st.session_state.changes = {}

st.title("Kontrola produktů")
st.write("Vyber produkt → uprav hodnoty → klikni uložit vše")

jmeno = st.selectbox(
    "Kdo upravuje",
    ["Monika", "Ondra", "Lenka", "Mája", "Iveta", "Eva", "Anička", "Host"]
)

df = load_export()

product_col = find_exact_col(df.columns, "Název produktu")
if not product_col:
    st.error("Nenašla jsem sloupec 'Název produktu'.")
    st.write("Dostupné sloupce:")
    st.write(df.columns.tolist())
    st.stop()

df = df[df[product_col].notna()].copy()
df[product_col] = df[product_col].astype(str).str.strip()

produkty = df[product_col].drop_duplicates().sort_values().tolist()

selected = st.selectbox(
    "Produkt (klikni sem a začni psát)",
    produkty,
    index=None,
    placeholder="Klikni sem a začni psát název produktu"
)

if not selected:
    st.info("Nejdřív vyber produkt ze seznamu.")
    st.stop()

product_rows = df[df[product_col] == selected].copy()

if product_rows.empty:
    st.warning("Vybraný produkt jsem nenašla.")
    st.stop()

row = product_rows.iloc[0]
slozeni = parse_product_row(row)

st.subheader(f"Produkt: {clean_value(row[product_col])}")

pocet_kusu = st.number_input(
    "Kolik kusů vyrábíme",
    min_value=1,
    step=1,
    value=1
)

if not slozeni:
    st.warning("U produktu jsem nenašla žádné složení.")
    st.stop()

with st.container(border=True):
    st.markdown("### 🧾 Co potřebujeme")
    st.markdown(f"**{clean_value(row[product_col])} ({pocet_kusu} ks)**")

    for item in slozeni:
        value = item["gramaz"]

        if pd.isna(value) or value == "":
            hodnota_txt = "❗ chybí"
        else:
            try:
                base_value = float(value)
            except Exception:
                base_value = 0.0

            total = base_value * pocet_kusu

            if item["typ"] == "Základ":
                hodnota_txt = f"{int(total)} ks"
            else:
                hodnota_txt = f"{int(total)} g"

        st.write(f"• {item['surovina']} – {hodnota_txt}")

st.divider()
st.markdown("### Úpravy")

st.session_state.changes = {
    k: v for k, v in st.session_state.changes.items()
    if v.get("produkt") == clean_value(row[product_col])
}

for idx, item in enumerate(slozeni):
    item_key = f"{selected}_{idx}"

    with st.container(border=True):
        st.markdown(f"**{item['typ']}**")
        st.write(f"**Surovina:** {item['surovina']}")

        puvodni = item["gramaz"]
        if pd.isna(puvodni) or puvodni == "":
            puvodni_display = ""
        else:
            puvodni_display = puvodni

        if item["typ"] == "Základ":
            aktualni_label = "Aktuální počet kusů"
            input_label = "Nový počet kusů"
            jednotka_text = "ks"
        else:
            aktualni_label = "Aktuální gramáž"
            input_label = "Nová gramáž"
            jednotka_text = "g"

        st.write(
            f"**{aktualni_label}:** {puvodni_display if puvodni_display != '' else 'NENÍ VYPLNĚNO'}"
        )

        if puvodni_display == "":
            st.warning(f"Chybí hodnota – doplň ji ({jednotka_text}).")

        default_value = get_default_numeric_value(puvodni_display)

        nova_hodnota = st.number_input(
            input_label,
            min_value=0.0,
            step=1.0,
            value=float(default_value),
            key=f"gram_{item_key}"
        )

        poznamka = st.text_input(
            "Poznámka",
            key=f"note_{item_key}",
            placeholder="např. chyběla gramáž / má být víc / má být méně"
        )

        st.session_state.changes[item_key] = {
            "produkt": clean_value(row[product_col]),
            "typ": item["typ"],
            "surovina": item["surovina"],
            "puvodni": puvodni_display,
            "nova": nova_hodnota,
            "poznamka": poznamka
        }

st.divider()

if st.button("💾 Uložit všechny změny", use_container_width=True):
    valid_changes = []
    invalid_items = []

    for change in st.session_state.changes.values():
        if change["produkt"] != clean_value(row[product_col]):
            continue

        nova_val = float(change["nova"])
        puvodni_raw = change["puvodni"]

        if puvodni_raw == "" or pd.isna(puvodni_raw):
            puvodni_num = None
        else:
            try:
                puvodni_num = float(puvodni_raw)
            except Exception:
                puvodni_num = None

        if puvodni_num is None:
            if nova_val > 0:
                valid_changes.append(change)
            else:
                invalid_items.append(change["surovina"])
            continue

        if abs(nova_val - puvodni_num) > 0.0001:
            valid_changes.append(change)

    if invalid_items:
        st.error("Tyto položky mají hodnotu 0 nebo méně: " + ", ".join(invalid_items))
    elif not valid_changes:
        st.warning("Nenašla jsem žádné skutečné změny k uložení.")
    else:
        for change in valid_changes:
            uloz_opravu(
                jmeno=jmeno,
                produkt=change["produkt"],
                typ=change["typ"],
                surovina=change["surovina"],
                puvodni=change["puvodni"],
                nova=change["nova"],
                poznamka=change["poznamka"]
            )

        st.success("Byly uloženy jen skutečně změněné hodnoty.")
        st.session_state.changes = {}
        st.rerun()

st.divider()
st.subheader("Schvalování oprav")

opravy_df = load_opravy()

if opravy_df.empty:
    st.info("Žádné opravy.")
else:
    opravy_df["stav"] = opravy_df["stav"].astype(str).str.strip()
    opravy_sorted = opravy_df[opravy_df["stav"] == "NOVÉ"].sort_values("datum", ascending=False)

    if opravy_sorted.empty:
        st.info("Žádné nové opravy.")
    else:
        for i, row_o in opravy_sorted.iterrows():
            with st.container(border=True):
                st.write(f"🕒 {row_o.get('datum', '')}")
                st.write(f"👤 {row_o.get('jmeno', '')}")
                st.write(f"🍽️ {row_o.get('produkt', '')}")
                st.write(f"📂 {row_o.get('typ', '')}")
                st.write(f"🥗 {row_o.get('surovina', '')}")

                typ_o = clean_value(row_o.get("typ", ""))
                jednotka = "ks" if typ_o == "Základ" else "g"

                st.write(f"**Původní hodnota:** {row_o.get('puvodni_gramaz', '')} {jednotka}")
                st.write(f"**Nová hodnota:** {row_o.get('nova_gramaz', '')} {jednotka}")

                poznamka_val = row_o.get("poznamka", "")
                if clean_value(poznamka_val):
                    st.write(f"📝 {poznamka_val}")

                stav_val = clean_value(row_o.get("stav", ""))
                st.write(f"📌 Stav: {stav_val}")

                col1, col2 = st.columns(2)

                if col1.button("✅ Schválit", key=f"sch_{i}"):
                    ok, msg = propsat_opravu_do_exportu(
                        produkt=row_o.get("produkt", ""),
                        typ=row_o.get("typ", ""),
                        surovina=row_o.get("surovina", ""),
                        nova_hodnota=row_o.get("nova_gramaz", "")
                    )

                    if ok:
                        opravy_df.at[i, "stav"] = "SCHVÁLENO"
                        save_opravy(opravy_df)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

                if col2.button("❌ Zamítnout", key=f"zam_{i}"):
                    opravy_df.at[i, "stav"] = "ZAMÍTNUTO"
                    save_opravy(opravy_df)
                    st.rerun()

st.divider()
st.subheader("Stažení souborů")

col_a, col_b = st.columns(2)

if os.path.exists(OPRAVY_FILE):
    with open(OPRAVY_FILE, "rb") as f:
        col_a.download_button(
            label="📥 Stáhnout opravy.xlsx",
            data=f,
            file_name="opravy.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if os.path.exists(EXPORT_FILE):
    with open(EXPORT_FILE, "rb") as f:
        col_b.download_button(
            label="📥 Stáhnout export.xlsx",
            data=f,
            file_name="export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

