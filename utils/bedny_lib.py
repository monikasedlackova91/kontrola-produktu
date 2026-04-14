import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

APP_TZ = ZoneInfo("Europe/Prague")
DATA_DIR = os.environ.get("DATA_DIR", "/data")

BEDNY_FILE = os.path.join(DATA_DIR, "bedny_vyzvednuti.xlsx")
SHEET_NAME = "bedny"

COLUMNS = [
    "id",
    "firma",
    "adresa",
    "telefon",
    "datum_rozvozu",
    "poznamka",
    "pocet_beden",
    "vraceno_beden",
    "stav",
    "ridic",
    "datum_vyzvednuti",
    "vytvoril",
    "created_at",
    "updated_at",
]

OPEN_STATUSES = ["čeká na vyzvednutí", "naplánováno", "volat předem"]
DONE_STATUS = "vyzvednuto"


def now_prague():
    return datetime.now(APP_TZ)


def today_prague():
    return now_prague().date()


def clean(v):
    if pd.isna(v):
        return ""
    return str(v).strip()


def clean_int(v, default=0):
    try:
        if pd.isna(v) or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def save_df(df: pd.DataFrame):
    ensure_data_dir()
    with pd.ExcelWriter(BEDNY_FILE, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)


def ensure_file():
    ensure_data_dir()
    if not os.path.exists(BEDNY_FILE):
        df = pd.DataFrame(columns=COLUMNS)
        save_df(df)


def load_df() -> pd.DataFrame:
    ensure_file()

    try:
        df = pd.read_excel(BEDNY_FILE, sheet_name=SHEET_NAME)
    except Exception:
        df = pd.DataFrame(columns=COLUMNS)

    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[COLUMNS].copy()

    for col in ["firma", "adresa", "telefon", "poznamka", "stav", "ridic", "vytvoril"]:
        df[col] = df[col].astype(str).str.strip()

    for col in ["pocet_beden", "vraceno_beden"]:
        df[col] = df[col].apply(clean_int)

    for col in ["datum_rozvozu", "datum_vyzvednuti"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    save_df(df)
    return df


def next_id(df: pd.DataFrame) -> int:
    if df.empty:
        return 1
    nums = pd.to_numeric(df["id"], errors="coerce").fillna(0)
    return int(nums.max()) + 1


def format_date_cz(d):
    if pd.isna(d) or d in [None, ""]:
        return ""
    try:
        return pd.to_datetime(d).strftime("%d.%m.%Y")
    except Exception:
        return str(d)


def is_open_status(status: str) -> bool:
    return clean(status).lower() in [s.lower() for s in OPEN_STATUSES]


def add_task(df: pd.DataFrame, firma, adresa, telefon, datum_rozvozu, poznamka, stav, vytvoril, pocet_beden):
    ts = now_prague().strftime("%Y-%m-%d %H:%M:%S")
    pocet = clean_int(pocet_beden, 0)

    new_row = {
        "id": next_id(df),
        "firma": clean(firma),
        "adresa": clean(adresa),
        "telefon": clean(telefon),
        "datum_rozvozu": datum_rozvozu,
        "poznamka": clean(poznamka),
        "pocet_beden": pocet,
        "vraceno_beden": 0,
        "stav": clean(stav),
        "ridic": "",
        "datum_vyzvednuti": pd.NaT,
        "vytvoril": clean(vytvoril),
        "created_at": ts,
        "updated_at": ts,
    }
    return pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)


def mark_done(df: pd.DataFrame, row_id: int, ridic: str = "řidič", vraceno_beden: int = 0):
    idx = df.index[df["id"] == row_id]
    if len(idx) == 0:
        return df

    i = idx[0]
    ts = now_prague().strftime("%Y-%m-%d %H:%M:%S")
    df.at[i, "stav"] = DONE_STATUS
    df.at[i, "ridic"] = clean(ridic)
    df.at[i, "vraceno_beden"] = clean_int(vraceno_beden, 0)
    df.at[i, "datum_vyzvednuti"] = pd.Timestamp(today_prague())
    df.at[i, "updated_at"] = ts
    return df


def reopen_task(df: pd.DataFrame, row_id: int):
    idx = df.index[df["id"] == row_id]
    if len(idx) == 0:
        return df

    i = idx[0]
    ts = now_prague().strftime("%Y-%m-%d %H:%M:%S")
    df.at[i, "stav"] = "čeká na vyzvednutí"
    df.at[i, "ridic"] = ""
    df.at[i, "vraceno_beden"] = 0
    df.at[i, "datum_vyzvednuti"] = pd.NaT
    df.at[i, "updated_at"] = ts
    return df


def delete_task(df: pd.DataFrame, row_id: int):
    return df[df["id"] != row_id].copy()
