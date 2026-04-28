import os
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Recepty", layout="centered")

# =========================
# CESTY
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("DATA_DIR", "/data")

EXPORT_FILE = os.path.join(DATA_DIR, "export.xlsx")
DEFAULT_EXPORT_FILE = os.path.join(BASE_DIR, "export.xlsx")

RECEPTY_FILE = os.path.join(DATA_DIR, "recepty.xlsx")
RECEPTY_POLOZKY_FILE = os.path.join(DATA_DIR, "recepty_polozky.xlsx")

EXPORT_SHEET = "export"
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

        df = df[columns]
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


def load_recepty():
    df = pd.read_excel(RECEPTY_FILE, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    return df.fillna("")


def load_polozky():
    df = pd.read_excel(RECEPTY_POLOZKY_FILE, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    return df.fillna("")


def save_recepty(df):
    df.to_excel(RECEPTY_FILE, index=False)


def save_polozky(df):
    df.to_excel(RECEPTY_POLOZKY_FILE, index=False)


def norm_typ(typ):
    return clean_value(typ).lower()


def recipe_match(df, nazev, typ):
    if df.empty:
        return pd.Series(dtype=bool)

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

    out["poradi"] = pd.to_numeric(out["poradi"], errors="coerce").fillna(9999).astype(int)
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

    rows = []
    if items_df is not None and not items_df.empty:
        tmp = items_df.copy().fillna("")

        for i, r in tmp.iterrows():
            surovina = clean_value(r.get("surovina", ""))
            if not surovina:
                continue

            poradi = r.get("poradi", i + 1)
            try:
                poradi = int(float(poradi))
            except Exception:
                poradi = i + 1

            rows.append({
                "nazev": nazev,
                "typ": typ,
                "surovina": surovina,
                "mnozstvi": clean_value(r.get("mnozstvi", "")),
                "jednotka": clean_value(r.get("jednotka", "")),
                "popis": clean_value(r.get("popis", "")),
                "poradi": poradi,
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

    if clean_value(header.get("poznamka", "")):
        st.info(clean_value(header.get("poznamka", "")))

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


# =========================
# START
# =========================
ensure_files()

st.title("Kuchařka / recepty")
st.caption("Vyhledej recept a kuchyň uvidí jen to, co opravdu potřebuje.")

recepty = list_recipes()

tab1, tab2 = st.tabs(["🔎 Najít recept", "➕ Přidat nový recept"])


# =========================
# TAB 1 — NAJÍT
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

            with st.expander("✏️ Upravit tento recept"):
                header = get_recipe_header(nazev, typ) or {}
                items = get_recipe_items(nazev, typ)

                with st.form(f"edit_form_{nazev}_{typ}"):
                    jmeno = st.selectbox("Kdo upravuje", USERS)

                    new_nazev = st.text_input("Název receptu", value=nazev)
                    new_typ = st.selectbox(
                        "Typ",
                        TYPY,
                        index=TYPY.index(typ) if typ in TYPY else 0
                    )

                    st.markdown("#### Suroviny")

                    if items.empty:
                        edit_df = pd.DataFrame(columns=["surovina", "mnozstvi", "jednotka", "popis", "poradi"])
                    else:
                        edit_df = items.copy()

                    edited_items = st.data_editor(
                        edit_df,
                        use_container_width=True,
                        num_rows="dynamic",
                        hide_index=True,
                        column_config={
                            "surovina": st.column_config.TextColumn("Surovina", required=True),
                            "mnozstvi": st.column_config.TextColumn("Množství"),
                            "jednotka": st.column_config.SelectboxColumn("Jednotka", options=JEDNOTKY),
                            "popis": st.column_config.TextColumn("Poznámka k surovině"),
                            "poradi": st.column_config.NumberColumn("Pořadí", min_value=1, step=1),
                        },
                        column_order=["poradi", "surovina", "mnozstvi", "jednotka", "popis"],
                    )

                    st.markdown("#### Postup a poznámky")

                    postup = st.text_area(
                        "Postup",
                        value=clean_value(header.get("postup", "")),
                        height=260,
                        placeholder="Napiš postup tak, aby podle toho kuchyň opravdu mohla jet..."
                    )

                    poznamka = st.text_area(
                        "Obecná poznámka",
                        value=clean_value(header.get("poznamka", "")),
                        height=120,
                        placeholder="Např. péct den předem, krájet až studené, pozor na sražení krému..."
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
                            delete_recipe(nazev, typ)

                        st.success("Recept je uložený.")
                        st.rerun()

                    if delete_btn:
                        delete_recipe(nazev, typ)
                        st.success("Recept byl smazán.")
                        st.rerun()


# =========================
# TAB 2 — NOVÝ RECEPT
# =========================
with tab2:
    with st.form("new_recipe_form"):
        jmeno = st.selectbox("Kdo zadává", USERS, key="new_user")

        nazev = st.text_input(
            "Název receptu",
            placeholder="např. bábovka, lemon curd, roastbeef, vanilkový krém"
        )

        typ = st.selectbox("Typ", TYPY, index=0)

        st.markdown("#### Suroviny")

        start_df = pd.DataFrame([
            {"poradi": 1, "surovina": "", "mnozstvi": "", "jednotka": "g", "popis": ""},
        ])

        items_new = st.data_editor(
            start_df,
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "surovina": st.column_config.TextColumn("Surovina", required=True),
                "mnozstvi": st.column_config.TextColumn("Množství"),
                "jednotka": st.column_config.SelectboxColumn("Jednotka", options=JEDNOTKY),
                "popis": st.column_config.TextColumn("Poznámka k surovině"),
                "poradi": st.column_config.NumberColumn("Pořadí", min_value=1, step=1),
            },
            column_order=["poradi", "surovina", "mnozstvi", "jednotka", "popis"],
        )

        postup = st.text_area(
            "Postup",
            height=260,
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
