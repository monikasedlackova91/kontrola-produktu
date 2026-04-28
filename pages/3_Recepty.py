import os
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from auth import check_password

st.set_page_config(page_title="Recepty", layout="centered")

check_password()

# =========================
# CESTY
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("DATA_DIR", "/data")

EXPORT_FILE = os.path.join(DATA_DIR, "export.xlsx")
DEFAULT_EXPORT_FILE = os.path.join(BASE_DIR, "export.xlsx")

RECEPTY_FILE = os.path.join(DATA_DIR, "recepty.xlsx")
RECEPTY_POLOZKY_FILE = os.path.join(DATA_DIR, "recepty_polozky.xlsx")

APP_TZ = ZoneInfo("Europe/Prague")

USERS = ["Monika", "Ondra", "Lenka", "Mája", "Iveta", "Tomáš", "Eva", "Anička", "Host"]
TYPY = ["recept", "komponent", "produkt"]
JEDNOTKY = ["g", "kg", "ml", "l", "ks", "lžíce", "lžička", "špetka", "dle potřeby", ""]


# =========================
# POMOCNÉ FUNKCE
# =========================
def clean_value(v):
    if pd.isna(v):
        return ""
    return str(v).strip()


def now_str():
    return datetime.now(APP_TZ).strftime("%Y-%m-%d %H:%M:%S")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def ensure_export_file():
    ensure_data_dir()
    if not os.path.exists(EXPORT_FILE):
        if os.path.exists(DEFAULT_EXPORT_FILE):
            shutil.copy(DEFAULT_EXPORT_FILE, EXPORT_FILE)


def ensure_excel_file(path, columns):
    ensure_data_dir()

    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_excel(path, index=False)
        return

    try:
        df = pd.read_excel(path, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]

        for c in columns:
            if c not in df.columns:
                df[c] = ""

        df = df[columns].fillna("")
        df.to_excel(path, index=False)

    except Exception as e:
        st.error(f"Chyba při kontrole souboru {os.path.basename(path)}: {e}")
        st.stop()


def ensure_files():
    ensure_export_file()

    ensure_excel_file(
        RECEPTY_FILE,
        ["nazev", "typ", "postup", "poznamka", "created_at", "updated_at", "updated_by"]
    )

    ensure_excel_file(
        RECEPTY_POLOZKY_FILE,
        ["nazev", "typ", "surovina", "mnozstvi", "jednotka", "popis", "poradi"]
    )


def fix_items_types(df):
    base_cols = ["nazev", "typ", "surovina", "mnozstvi", "jednotka", "popis", "poradi"]

    if df is None or df.empty:
        df = pd.DataFrame(columns=base_cols)

    for c in base_cols:
        if c not in df.columns:
            df[c] = ""

    df = df.copy()

    df["nazev"] = df["nazev"].apply(clean_value).astype(str)
    df["typ"] = df["typ"].apply(clean_value).astype(str)
    df["surovina"] = df["surovina"].apply(clean_value).astype(str)
    df["mnozstvi"] = df["mnozstvi"].apply(clean_value).astype(str)
    df["jednotka"] = df["jednotka"].apply(clean_value).astype(str)
    df["popis"] = df["popis"].apply(clean_value).astype(str)

    df["poradi"] = pd.to_numeric(df["poradi"], errors="coerce").fillna(1).astype(int)
    df.loc[df["poradi"] < 1, "poradi"] = 1

    return df[base_cols]


def fix_editor_items(df):
    editor_cols = ["surovina", "mnozstvi", "jednotka", "popis", "poradi"]

    if df is None or df.empty:
        df = pd.DataFrame(columns=editor_cols)

    for c in editor_cols:
        if c not in df.columns:
            df[c] = ""

    df = df[editor_cols].copy()

    df["surovina"] = df["surovina"].apply(clean_value).astype(str)
    df["mnozstvi"] = df["mnozstvi"].apply(clean_value).astype(str)
    df["jednotka"] = df["jednotka"].apply(clean_value).astype(str)
    df["popis"] = df["popis"].apply(clean_value).astype(str)

    df["poradi"] = pd.to_numeric(df["poradi"], errors="coerce").fillna(1).astype(int)
    df.loc[df["poradi"] < 1, "poradi"] = 1

    return df


def load_recepty():
    df = pd.read_excel(RECEPTY_FILE, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    return df.fillna("")


def load_polozky():
    df = pd.read_excel(RECEPTY_POLOZKY_FILE, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.fillna("")
    return fix_items_types(df)


def save_recepty(df):
    df.to_excel(RECEPTY_FILE, index=False)


def save_polozky(df):
    df = fix_items_types(df)
    df.to_excel(RECEPTY_POLOZKY_FILE, index=False)


def norm_typ(typ):
    return clean_value(typ).lower()


def recipe_match(df, nazev, typ):
    if df.empty:
        return pd.Series([False] * len(df))

    if "nazev" not in df.columns:
        df["nazev"] = ""

    if "typ" not in df.columns:
        df["typ"] = ""

    return (
        df["nazev"].astype(str).str.strip().str.lower().eq(clean_value(nazev).lower())
        &
        df["typ"].astype(str).str.strip().str.lower().eq(norm_typ(typ))
    )


def get_recipe_header(nazev, typ):
    df = load_recepty()

    if df.empty:
        return None

    m = recipe_match(df, nazev, typ)
    if not m.any():
        return None

    return df[m].iloc[0].to_dict()


def get_recipe_items(nazev, typ):
    df = load_polozky()

    if df.empty:
        return pd.DataFrame(columns=["surovina", "mnozstvi", "jednotka", "popis", "poradi"])

    m = recipe_match(df, nazev, typ)
    out = df[m].copy()

    if out.empty:
        return pd.DataFrame(columns=["surovina", "mnozstvi", "jednotka", "popis", "poradi"])

    out = fix_items_types(out)
    out = out.sort_values(["poradi", "surovina"])

    return out[["surovina", "mnozstvi", "jednotka", "popis", "poradi"]].reset_index(drop=True)


def save_recipe(nazev, typ, postup, poznamka, updated_by, items_df):
    nazev = clean_value(nazev)
    typ = norm_typ(typ)

    if not nazev:
        st.error("Chybí název receptu.")
        st.stop()

    df_h = load_recepty()
    m = recipe_match(df_h, nazev, typ)
    cas = now_str()

    if m.any():
        idx = df_h[m].index[0]
        df_h.at[idx, "postup"] = clean_value(postup)
        df_h.at[idx, "poznamka"] = clean_value(poznamka)
        df_h.at[idx, "updated_at"] = cas
        df_h.at[idx, "updated_by"] = clean_value(updated_by)
    else:
        new_row = pd.DataFrame([{
            "nazev": nazev,
            "typ": typ,
            "postup": clean_value(postup),
            "poznamka": clean_value(poznamka),
            "created_at": cas,
            "updated_at": cas,
            "updated_by": clean_value(updated_by),
        }])
        df_h = pd.concat([df_h, new_row], ignore_index=True)

    save_recepty(df_h)

    df_i = load_polozky()

    if not df_i.empty:
        df_i = df_i[~recipe_match(df_i, nazev, typ)].copy()

    items_df = fix_editor_items(items_df)

    rows = []
    for i, r in items_df.iterrows():
        surovina = clean_value(r.get("surovina", ""))
        if not surovina:
            continue

        rows.append({
            "nazev": nazev,
            "typ": typ,
            "surovina": surovina,
            "mnozstvi": clean_value(r.get("mnozstvi", "")),
            "jednotka": clean_value(r.get("jednotka", "")),
            "popis": clean_value(r.get("popis", "")),
            "poradi": int(r.get("poradi", i + 1)),
        })

    if rows:
        df_i = pd.concat([df_i, pd.DataFrame(rows)], ignore_index=True)

    save_polozky(df_i)


def delete_recipe(nazev, typ):
    df_h = load_recepty()
    df_i = load_polozky()

    df_h = df_h[~recipe_match(df_h, nazev, typ)].copy()
    df_i = df_i[~recipe_match(df_i, nazev, typ)].copy()

    save_recepty(df_h)
    save_polozky(df_i)


def list_recipes():
    df = load_recepty()

    if df.empty:
        return []

    df["nazev"] = df["nazev"].astype(str).str.strip()
    df["typ"] = df["typ"].astype(str).str.strip().str.lower()
    df = df[df["nazev"] != ""].copy()

    df["label"] = df.apply(lambda r: f"{r['nazev']}  ·  {r['typ']}", axis=1)

    return sorted(df["label"].drop_duplicates().tolist())


def parse_label(label):
    if "  ·  " in label:
        a, b = label.rsplit("  ·  ", 1)
        return a.strip(), b.strip().lower()
    return label.strip(), "recept"


def display_recipe(nazev, typ):
    header = get_recipe_header(nazev, typ)
    items = get_recipe_items(nazev, typ)

    if not header:
        st.warning("Recept zatím není uložený.")
        return

    st.markdown(f"## {clean_value(header.get('nazev', nazev))}")
    st.caption(f"Typ: {clean_value(header.get('typ', typ))}")

    updated_by = clean_value(header.get("updated_by", ""))
    updated_at = clean_value(header.get("updated_at", ""))

    if updated_by or updated_at:
        st.caption(f"Naposledy upravil/a: {updated_by} | {updated_at}")

    poznamka = clean_value(header.get("poznamka", ""))
    if poznamka:
        st.info(poznamka)

    st.markdown("### Suroviny")

    if items.empty:
        st.write("_Bez vypsaných surovin._")
    else:
        for _, r in items.iterrows():
            surovina = clean_value(r.get("surovina", ""))
            mnozstvi = clean_value(r.get("mnozstvi", ""))
            jednotka = clean_value(r.get("jednotka", ""))
            popis = clean_value(r.get("popis", ""))

            line = f"**{surovina}**"

            if mnozstvi or jednotka:
                line += f" — {mnozstvi} {jednotka}".strip()

            st.markdown(line)

            if popis:
                st.caption(popis)

    st.markdown("### Postup")

    postup = clean_value(header.get("postup", ""))
    if postup:
        st.markdown(postup.replace("\n", "  \n"))
    else:
        st.write("_Postup zatím není vyplněný._")


def recipe_data_editor(df, key):
    df = fix_editor_items(df)

    return st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        key=key,
        column_config={
            "poradi": st.column_config.NumberColumn(
                "Pořadí",
                min_value=1,
                step=1
            ),
            "surovina": st.column_config.TextColumn(
                "Surovina",
                required=True
            ),
            "mnozstvi": st.column_config.TextColumn(
                "Množství",
                help="Může být číslo i text: 100, 0.5, špetka, dle potřeby."
            ),
            "jednotka": st.column_config.SelectboxColumn(
                "Jednotka",
                options=JEDNOTKY
            ),
            "popis": st.column_config.TextColumn(
                "Poznámka"
            ),
        },
        column_order=["poradi", "surovina", "mnozstvi", "jednotka", "popis"],
    )


# =========================
# START
# =========================
ensure_files()

st.title("Kuchařka / recepty")
st.caption("Na mobilu hlavně pro rychlé čtení receptů. Zadávání a větší úpravy jsou pohodlnější na počítači.")

recepty = list_recipes()

tab1, tab2 = st.tabs(["🔎 Najít recept", "➕ Přidat nový recept"])


# =========================
# TAB 1 — NAJÍT RECEPT
# =========================
with tab1:
    if not recepty:
        st.info("Zatím není uložený žádný recept.")
    else:
        vyber = st.selectbox(
            "Vyhledej recept",
            recepty,
            index=None,
            placeholder="Začni psát třeba bábovka, lemon curd, roastbeef..."
        )

        if vyber:
            nazev, typ = parse_label(vyber)

            st.divider()
            display_recipe(nazev, typ)

            st.divider()

            with st.expander("✏️ Upravit tento recept / pohodlnější na PC"):
                st.warning("Na telefonu může být úprava tabulky surovin méně pohodlná. Pro zadávání nových receptů je lepší počítač.")

                header = get_recipe_header(nazev, typ) or {}
                items = get_recipe_items(nazev, typ)

                with st.form(f"edit_form_{nazev}_{typ}"):
                    jmeno = st.selectbox("Kdo upravuje", USERS)

                    new_nazev = st.text_input("Název receptu", value=nazev)

                    current_typ = typ if typ in TYPY else "recept"
                    new_typ = st.selectbox(
                        "Typ",
                        TYPY,
                        index=TYPY.index(current_typ)
                    )

                    st.markdown("#### Suroviny")

                    if items.empty:
                        edit_df = pd.DataFrame(columns=["surovina", "mnozstvi", "jednotka", "popis", "poradi"])
                    else:
                        edit_df = items.copy()

                    edit_df = fix_editor_items(edit_df)

                    edited_items = recipe_data_editor(
                        edit_df,
                        key=f"editor_edit_{nazev}_{typ}"
                    )

                    st.markdown("#### Postup a poznámky")

                    postup = st.text_area(
                        "Postup",
                        value=clean_value(header.get("postup", "")),
                        height=260,
                        placeholder="Napiš postup tak, aby podle toho kuchyň mohla jet..."
                    )

                    poznamka = st.text_area(
                        "Obecná poznámka",
                        value=clean_value(header.get("poznamka", "")),
                        height=120,
                        placeholder="Např. péct den předem, krájet až studené..."
                    )

                    col_save, col_delete = st.columns(2)

                    save_btn = col_save.form_submit_button("💾 Uložit úpravy", use_container_width=True)
                    delete_btn = col_delete.form_submit_button("🗑️ Smazat recept", use_container_width=True)

                    if save_btn:
                        save_recipe(
                            nazev=new_nazev,
                            typ=new_typ,
                            postup=postup,
                            poznamka=poznamka,
                            updated_by=jmeno,
                            items_df=edited_items,
                        )

                        if clean_value(new_nazev).lower() != clean_value(nazev).lower() or norm_typ(new_typ) != norm_typ(typ):
                            delete_recipe(nazev=nazev, typ=typ)

                        st.success("Recept je uložený.")
                        st.rerun()

                    if delete_btn:
                        delete_recipe(nazev=nazev, typ=typ)
                        st.success("Recept byl smazán.")
                        st.rerun()


# =========================
# TAB 2 — NOVÝ RECEPT
# =========================
with tab2:
    st.info("Nový recept doporučuji zadávat hlavně na počítači, kvůli delšímu postupu a tabulce surovin.")

    with st.form("new_recipe_form"):
        jmeno = st.selectbox("Kdo zadává", USERS, key="new_user")

        nazev = st.text_input(
            "Název receptu",
            placeholder="např. bábovka, lemon curd, roastbeef, vanilkový krém"
        )

        typ = st.selectbox("Typ", TYPY, index=0)

        st.markdown("#### Suroviny")

        start_df = pd.DataFrame([
            {
                "poradi": 1,
                "surovina": "",
                "mnozstvi": "",
                "jednotka": "g",
                "popis": "",
            }
        ])

        start_df = fix_editor_items(start_df)

        items_new = recipe_data_editor(
            start_df,
            key="editor_new_recipe"
        )

        postup = st.text_area(
            "Postup",
            height=300,
            placeholder="1. Připrav...\n2. Smíchej...\n3. Peč..."
        )

        poznamka = st.text_area(
            "Obecná poznámka",
            height=120,
            placeholder="Např. množství je na 1 plech / 1 dort / 20 porcí..."
        )

        submitted = st.form_submit_button("💾 Uložit nový recept", use_container_width=True)

        if submitted:
            if not clean_value(nazev):
                st.error("Zadej název receptu.")
            else:
                save_recipe(
                    nazev=nazev,
                    typ=typ,
                    postup=postup,
                    poznamka=poznamka,
                    updated_by=jmeno,
                    items_df=items_new,
                )
                st.success("Nový recept je uložený.")
                st.rerun()


# =========================
# STAŽENÍ SOUBORŮ
# =========================
st.divider()

with st.expander("📥 Stáhnout soubory"):
    col1, col2 = st.columns(2)

    if os.path.exists(RECEPTY_FILE):
        with open(RECEPTY_FILE, "rb") as f:
            col1.download_button(
                "Stáhnout recepty.xlsx",
                data=f,
                file_name="recepty.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    if os.path.exists(RECEPTY_POLOZKY_FILE):
        with open(RECEPTY_POLOZKY_FILE, "rb") as f:
            col2.download_button(
                "Stáhnout recepty_polozky.xlsx",
                data=f,
                file_name="recepty_polozky.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
