"""
prepare_data.py  -  turn the big MICS_*.parquet files into small, CLEAN tables for the dashboard.

    python prepare_data.py
    python prepare_data.py "C:\\Users\\DELL\\Desktop\\MICS\\parquet"
    python prepare_data.py "C:\\Users\\DELL\\Desktop\\MICS\\parquet" "C:\\Users\\DELL\\Desktop\\MICS\\dashboard\\data"

What it does (the "harmonisation layer")
  * one value for the same thing:  Rural / RURAL / 2.0  ->  Rural     Male / MALE / 1.0  ->  Male  ...
  * the same concept stored in several columns (weights, wealth quintile, area, age ...) -> ONE column
  * household facts (area, wealth quintile) are copied from MICS_Households onto every person table
  * indicators are computed as 0/1 flags (e.g. improved water, stunted, skilled birth attendant)
  * only completed interviews with a sample weight > 0 are kept
  * writes  hh / women / men / children / births / siblings / nets / c5to17 (/ members)  .parquet
    and  coverage.csv  +  prep_log.txt  (what was mapped, what could not be mapped)

Original files are never changed.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

DEFAULT_IN = r"C:\Users\DELL\Desktop\MICS\parquet"
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


# ----------------------------------------------------------------------------- helpers
PROV = {"GB": "Gilgit-Baltistan", "KPK": "Khyber Pakhtunkhwa", "KP": "Khyber Pakhtunkhwa"}
PSHORT = {"Gilgit-Baltistan": "GB", "Khyber Pakhtunkhwa": "KP"}


def S(x):
    s = x.astype("string").str.strip().str.upper()
    return s.mask(s == "")                      # empty text (blank cell in labelled files) = no answer


def num(x):
    return pd.to_numeric(x, errors="coerce")


def NA(index):
    return pd.Series(np.nan, index=index, dtype="float64")


def OBJ(index):
    return pd.Series(pd.NA, index=index, dtype="object")


def col(df, name):
    return df[name] if name in df.columns else pd.Series(pd.NA, index=df.index, dtype="object")


def coalesce(df, names):
    out = OBJ(df.index)
    for n in names:
        if n in df.columns:
            out = out.where(out.notna(), df[n].astype("object"))
    return out


def coalesce_num(df, names, lo=None, hi=None):
    out = NA(df.index)
    for n in names:
        if n in df.columns:
            v = num(df[n])
            if lo is not None:
                v = v.where((v >= lo) & (v <= hi))
            out = out.where(out.notna(), v)
    return out


# the same district / division is spelt differently in different surveys: bring them to one spelling
NAME_FIX = {
    # Balochistan
    "Chaghi": "Chagai", "Jaffarabad": "Jafarabad", "Qilla Abdullah": "Killa Abdullah", "Qilla Saifullah": "Killa Saifullah",
    "Musakhail": "Musakhel", "Naseerabad": "Nasirabad", "Nushki": "Noshki", "Panjgoor": "Panjgur", "Sheerani": "Sherani", "Sibbi": "Sibi",
    # Khyber Pakhtunkhwa
    "Abbotabad": "Abbottabad", "Hari Pur": "Haripur", "Laki Marwat": "Lakki Marwat", "Nowshehra": "Nowshera", "Tor Ghar": "Torghar",
    # Sindh / Punjab divisions
    "Tando Muhmmad Khan": "Tando Muhammad Khan", "Mirpurkhas": "Mirpur Khas", "Dg Khan": "D.G.Khan",
}


def clean_name(x):
    """tidy a place name: single spaces, Title Case, one agreed spelling"""
    s = x.astype("string").str.replace(r"\s+", " ", regex=True).str.strip().str.title()
    return s.replace(NAME_FIX)


def m_area(x):
    s = S(x)
    r = OBJ(x.index)
    r[s.str.contains("URBAN", na=False)] = "Urban"
    r[s.str.contains("RURAL", na=False)] = "Rural"
    r[s.isin(["1", "1.0"])] = "Urban"      # MICS standard: 1 = Urban, 2 = Rural
    r[s.isin(["2", "2.0"])] = "Rural"
    return r


def m_sex(x):
    s = S(x)
    r = OBJ(x.index)
    r[s.isin(["MALE", "M", "BOY", "1", "1.0"])] = "Male"
    r[s.isin(["FEMALE", "F", "GIRL", "2", "2.0"])] = "Female"
    return r


WEALTH = ["Poorest", "Second", "Middle", "Fourth", "Richest"]


def m_wealth(x):
    s = S(x)
    r = OBJ(x.index)
    for lab, keys in zip(WEALTH, (["POOREST", "LOWEST", "1", "1.0"], ["SECOND", "2", "2.0"], ["MIDDLE", "3", "3.0"],
                                   ["FOURTH", "4", "4.0"], ["RICHEST", "HIGHEST", "5", "5.0"])):
        r[s.isin(keys)] = lab
    return r


EDU = ["None / pre-primary", "Primary", "Middle", "Secondary", "Higher"]


def m_edu(x):
    s = S(x)
    r = OBJ(x.index)
    r[s.str.contains("NONE|PRE-PRIMARY|PRE-SCHOOL|PRESCHOOL|NO EDUCATION|PRE PRIMARY", na=False)] = EDU[0]
    r[s.str.contains("PRIMARY", na=False) & ~s.str.contains("PRE", na=False)] = EDU[1]
    r[s.str.contains("MIDDLE|LOWER SECONDARY", na=False)] = EDU[2]
    r[s.str.contains("SECONDARY|MATRIC", na=False) & ~s.str.contains("LOWER|HIGHER", na=False)] = EDU[3]
    r[s.str.contains("HIGHER", na=False) & ~s.str.contains("HIGHER SECONDARY", na=False)] = EDU[4]
    r[s.str.contains("HIGHER SECONDARY|\\+", na=False, regex=True)] = EDU[3]
    # numeric codes (Punjab files converted without labels): 0 none, 1 primary, 2 middle, 3 secondary, 4 higher
    for k, lab in zip(["0", "1", "2", "3", "4"], EDU):
        r[s.isin([k, k + ".0"])] = lab
    return r


def yn(x):
    """Yes -> 1, No -> 0, everything else (DK, missing, no response, blank) -> NaN"""
    s = S(x)
    r = NA(x.index)
    r[s.str.startswith("YES", na=False) | s.isin(["1", "1.0"])] = 1.0
    r[s.isin(["NO", "2", "2.0"])] = 0.0
    return r


def any_yes(df, cols):
    """1 if any Yes, 0 if answered but all No, NaN if all blank"""
    if not cols:
        return NA(df.index)
    m = pd.concat([yn(df[c]) for c in cols], axis=1)
    out = m.max(axis=1, skipna=True)
    return out


JUNK = {"MISSING", "NO RESPONSE", "?", "DK", "NO", "0", "0.0", "2", "2.0", "8", "8.0", "9", "9.0", "NR", "NOT ASKED"}


def ticked(x):
    """check-box style column: a letter (A, B ...) or the label text means 'yes'; blank / No / DK means not ticked"""
    s = S(x)
    return (s.notna() & ~s.isin(JUNK)).fillna(False).to_numpy(bool)


def any_ticked(df, cols):
    if not cols:
        return np.zeros(len(df), bool)
    m = np.zeros(len(df), bool)
    for c in cols:
        m |= ticked(df[c])
    return m


def answered(df, cols):
    if not cols:
        return np.zeros(len(df), bool)
    m = np.zeros(len(df), bool)
    for c in cols:
        s = S(df[c])
        m |= (s.notna() & ~s.isin(["MISSING", "NO RESPONSE", "?"])).fillna(False).to_numpy(bool)
    return m


def completed(x):
    s = S(x)
    return s.str.startswith("COMPLETED", na=False) | s.isin(["1", "1.0"])


def cols_like(df_cols, pattern, flags=re.I):
    return [c for c in df_cols if re.search(pattern, c, flags)]


AGE_BINS_W = [15, 20, 25, 30, 35, 40, 45, 50]
AGE_LAB_W = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49"]


def age_grp(a, bins=AGE_BINS_W, labels=AGE_LAB_W):
    return pd.cut(a, bins=bins, labels=labels, right=False).astype("object")


def read(path, want_regex=None, want_cols=None, extra=()):
    names = pq.ParquetFile(path).schema_arrow.names
    keep = ["Province", "Year", "Source file"] + KEYPAIRS_C + KEYPAIRS_H
    sel = list(keep) + [c for c in extra if c in names]
    if want_cols:
        sel += [c for c in want_cols if c in names]
    if want_regex:
        sel += [c for c in names if re.search(want_regex, c, re.I)]
    sel = list(dict.fromkeys(c for c in sel if c in names))
    return pd.read_parquet(path, columns=sel)


KEYPAIRS_C = ["Cluster number", "Cluster number [HH1]", "Cluster number.1", "Cluster number [WM1]", "Cluster number [UF1]", "Cluster number [AN1]", "Cluster number.2"]
KEYPAIRS_H = ["Household number", "Household number [HH2]", "Household number.1", "Household number [WM2]", "Household number [UF2]", "Household number [AN2]", "Household number.2"]


def base(df):
    out = pd.DataFrame(index=df.index)
    p = df["Province"].astype("string").str.strip()
    out["Province"] = p.map(lambda v: PROV.get(v.upper(), v.capitalize() if v.islower() else v) if isinstance(v, str) else v)
    out["Year"] = num(df["Year"]).astype("Int64")
    out["Survey"] = out["Province"].map(lambda v: PSHORT.get(v, v)).astype(str) + " " + out["Year"].astype(str)
    out["_k1"] = df["Source file"].astype("string").str.strip().str.upper()
    cl = coalesce_num(df, [c for c in KEYPAIRS_C if c in df.columns])
    hn = coalesce_num(df, [c for c in KEYPAIRS_H if c in df.columns])
    out["_k2"] = cl.astype("Int64")
    out["_k3"] = hn.astype("Int64")
    return out


# ----------------------------------------------------------------------------- households
WATER_GRP = [
    ("Piped water", r"PIPED|TAP|STANDPIPE"),
    ("Tube well / pump", r"TUBE WELL|BOREHOLE|HAND PUMP|MOTORIZED|MOTORISED|PUMP"),
    ("Protected well / spring", r"PROTECTED"),
    ("Bottled / filtered / rain", r"BOTTLED|PACKAGED|FILTER|FILTRATION|RAIN|KIOSK"),
    ("Tanker / cart", r"TANKER|CART"),
    ("Unprotected well / spring", r"UNPROTECTED"),
    ("Surface water", r"SURFACE|POND|TOBA|RIVER|CANAL"),
    ("Other", r"OTHER"),
]


def water_group(x):
    s = S(x)
    r = OBJ(x.index)
    # order matters: UNPROTECTED first, then surface / cart, then the improved ones
    r[s.str.contains("OTHER", na=False)] = "Other"
    r[s.str.contains("PIPED|TAP|STANDPIPE", na=False)] = "Piped water"
    r[s.str.contains("TUBE WELL|BOREHOLE|HAND PUMP|MOTORI[ZS]ED|PUMP", na=False)] = "Tube well / pump"
    r[s.str.contains("RAIN|BOTTLED|PACKAGED|KIOSK|FILTER|FILTRATION", na=False)] = "Bottled / filtered / rain"
    r[s.str.contains("PROTECTED", na=False)] = "Protected well / spring"
    r[s.str.contains("TANKER|CART", na=False)] = "Tanker / cart"
    r[s.str.contains("SURFACE|POND|TOBA|RIVER|CANAL", na=False)] = "Surface water"
    r[s.str.contains("UNPROTECTED", na=False)] = "Unprotected well / spring"
    r[s.isin(["MISSING", "NO RESPONSE", "DK"])] = pd.NA
    return r


IMPROVED_WATER = {"Piped water", "Tube well / pump", "Protected well / spring", "Bottled / filtered / rain", "Tanker / cart"}   # JMP 2017 / MICS6: tanker-truck and cart with small tank are improved
WATER_ORDER = [g for g, _ in WATER_GRP]

TOILET_ORDER = ["Flush to sewer / septic / pit", "Pit latrine with slab / VIP / composting",
                "Other unimproved (open drain, no slab, bucket)", "Open defecation (no facility)"]


def toilet_group(x):
    s = S(x)
    r = OBJ(x.index)
    r[s.notna()] = TOILET_ORDER[2]
    r[s.str.contains("FLUSH", na=False) & s.str.contains("SEWER|SEPTIC|PIT|SOAKAGE", na=False)
      & ~s.str.contains("OPEN DRAIN|SOMEWHERE|DK|UNKNOWN", na=False)] = TOILET_ORDER[0]
    r[s.str.contains("FLUSH", na=False) & s.str.contains("UNKNOWN|DK|DON'T KNOW|NOT SURE", na=False)] = TOILET_ORDER[0]   # JMP: flush to unknown place = improved
    r[s.str.contains("VENTILATED|VIP|WITH SLAB|COMPOST", na=False) & ~s.str.contains("WITHOUT", na=False)] = TOILET_ORDER[1]
    r[s.str.contains("NO FACILITY|BUSH|FIELD", na=False)] = TOILET_ORDER[3]
    r[s.isin(["MISSING", "NO RESPONSE", "DK"])] = pd.NA
    return r


CLEAN_STOVE = ("NATURAL GAS|LIQUEFIED PETROLEUM|LPG|COOKING GAS|BIOGAS|ELECTRI|SOLAR")
DIRTY_STOVE = ("TRADITIONAL SOLID|THREE STONE|MANUFACTURED SOLID|LIQUID FUEL|WOOD|DUNG|CROP|STRAW|SHRUB|GRASS|CHARCOAL|COAL|KEROSENE")


def clean_fuel(fuel, stove):
    out = NA(fuel.index)
    for x in (fuel, stove):
        s = S(x)
        v = NA(x.index)
        v[s.str.contains(DIRTY_STOVE, na=False)] = 0.0
        v[s.str.contains(CLEAN_STOVE, na=False)] = 1.0
        out = out.where(out.notna(), v)
    return out


def build_hh(path):
    log("\n== Households")
    df = read(path, r"^(Area|Area of residence|Area\.1|Area \(Original\)|District|Districts|Division|Household sample weight|Wealth index quintiles?|"
                    r"Result of HH interview|Number of HH members|Number of rooms( used)? for sleeping|Number of rooms used for sleeping|"
                    r"Main source of drinking water|Type of toilet facility|Water available at the place for handwashing|Electricity|"
                    r"Household have electricity|Type of fuel using for cooking|Type of cookstove mainly used for cooking|"
                    r"Sex of household head|Education of (head of )?household head|Education of head of household|"
                    r"Treat water to make safer for drinking|Number of mosquito nets|Age of household head|"
                    r"Television|Household have: Television|Refrigerator|Refrigerator/freezer|Refrigerator / freezer|Household have: Refrigerator|"
                    r"Mobile telephone|Any member have a mobile telephone|Motorcycle or scooter|Motorcycle / Scooter / Rickshaw|Motorcycle / scooter|"
                    r"Any member of household own: Motorcycle or scooter|Any household member have account in Bank, PO or National Saving Centre|"
                    r"Any household member have account in Bank, Post office or national saving centre|Any household member own bank account|"
                    r"Household owns the dwelling)$")
    b = base(df)
    b["w"] = coalesce_num(df, ["Household sample weight"])
    b["Area"] = m_area(coalesce(df, ["Area", "Area of residence", "Area.1", "Area (Original)"]))
    b["Wealth"] = m_wealth(coalesce(df, ["Wealth index quintile", "Wealth index quintiles"]))
    b["District"] = clean_name(S(coalesce(df, ["District", "Districts"])))
    b["Division"] = clean_name(S(df["Division"] if "Division" in df else OBJ(df.index)))
    wg = water_group(col(df, "Main source of drinking water"))
    b["WaterSource"] = wg
    b["water_improved"] = wg.map(lambda v: np.nan if pd.isna(v) else float(v in IMPROVED_WATER))
    b["water_piped"] = wg.map(lambda v: np.nan if pd.isna(v) else float(v == "Piped water"))
    tg = toilet_group(col(df, "Type of toilet facility"))
    b["ToiletType"] = tg
    b["sanitation_improved"] = tg.map(lambda v: np.nan if pd.isna(v) else float(v in TOILET_ORDER[:2]))
    b["open_defecation"] = tg.map(lambda v: np.nan if pd.isna(v) else float(v == TOILET_ORDER[3]))
    hw = S(col(df, "Water available at the place for handwashing"))
    b["handwash_water"] = np.where(hw.eq("WATER IS AVAILABLE").fillna(False).to_numpy(bool), 1.0,
                                   np.where(hw.eq("WATER IS NOT AVAILABLE").fillna(False).to_numpy(bool), 0.0, np.nan))
    b["electricity"] = yn(coalesce(df, ["Electricity", "Household have electricity"]))
    b["clean_fuel"] = clean_fuel(col(df, "Type of fuel using for cooking"), col(df, "Type of cookstove mainly used for cooking"))
    b["treat_water"] = yn(col(df, "Treat water to make safer for drinking"))
    b["hh_size"] = coalesce_num(df, ["Number of HH members"], 1, 60)
    rooms = coalesce_num(df, ["Number of rooms used for sleeping", "Number of rooms for sleeping"], 1, 20)
    b["rooms"] = rooms
    b["crowded"] = np.where(rooms.notna() & b["hh_size"].notna(), (b["hh_size"] / rooms > 3).astype(float), np.nan)
    b["female_head"] = m_sex(col(df, "Sex of household head")).map(lambda v: np.nan if pd.isna(v) else float(v == "Female"))
    b["head_edu"] = m_edu(coalesce(df, ["Education of household head", "Education of head of household"]))
    b["head_age"] = coalesce_num(df, ["Age of household head"], 10, 99)
    b["nets"] = coalesce_num(df, ["Number of mosquito nets"], 0, 30)
    b["has_tv"] = yn(coalesce(df, ["Television", "Household have: Television"]))
    b["has_fridge"] = yn(coalesce(df, ["Refrigerator", "Refrigerator/freezer", "Refrigerator / freezer", "Household have: Refrigerator"]))
    b["has_mobile"] = yn(coalesce(df, ["Mobile telephone", "Any member have a mobile telephone"]))
    b["has_motorbike"] = yn(coalesce(df, ["Motorcycle or scooter", "Motorcycle / Scooter / Rickshaw", "Motorcycle / scooter", "Any member of household own: Motorcycle or scooter"]))
    b["has_bank"] = yn(coalesce(df, ["Any household member have account in Bank, PO or National Saving Centre",
                                      "Any household member have account in Bank, Post office or national saving centre", "Any household member own bank account"]))
    _dw = S(col(df, "Household owns the dwelling"))
    b["rents_home"] = np.where(_dw.eq("RENT").fillna(False).to_numpy(bool), 1.0, np.where(_dw.isin(["OWN", "OTHER", "OTHER (NOT OWNED OR RENTED)"]).fillna(False).to_numpy(bool), 0.0, np.nan))
    b["completed"] = b["w"] > 0
    cov = b.groupby("Survey").agg(sampled=("w", "size"), completed=("completed", "sum")).reset_index()
    cov["response_rate"] = cov["completed"] / cov["sampled"]
    keyed = b[["_k1", "_k2", "_k3", "Area", "Wealth", "District", "Division"]].drop_duplicates(["_k1", "_k2", "_k3"])
    b = b[b["completed"]].drop(columns="completed").reset_index(drop=True)
    return b, cov, keyed


# ----------------------------------------------------------------------------- generic person-table finishing
def attach_hh(b, keyed):
    m = b.merge(keyed.rename(columns={"Area": "hhArea", "Wealth": "hhWealth", "District": "hhDistrict", "Division": "hhDivision"}),
                on=["_k1", "_k2", "_k3"], how="left")
    matched = m["hhArea"].notna() | m["hhWealth"].notna()
    by = matched.groupby(m["Survey"]).mean()
    low = by[by < 0.95]
    if len(low):
        log("   note: rows matched to a household record are below 95% for", {k: f"{v:.0%}" for k, v in low.items()},
            "- Area / Wealth then come from the table's own columns")
    return m, matched


def finish_dims(b, df, own_area_cols, own_wealth_cols, keyed, tname):
    own_area = m_area(coalesce(df, own_area_cols)) if own_area_cols else OBJ(df.index)
    own_wealth = m_wealth(coalesce(df, own_wealth_cols)) if own_wealth_cols else OBJ(df.index)
    b = b.copy()
    b["Area"] = own_area
    b["Wealth"] = own_wealth
    m, matched = attach_hh(b, keyed)
    m["Area"] = m["hhArea"].where(m["hhArea"].notna(), m["Area"])      # household table is the cleanest source
    m["Wealth"] = m["hhWealth"].where(m["hhWealth"].notna(), m["Wealth"])
    m["District"] = m["hhDistrict"]
    m["Division"] = m["hhDivision"]
    log(f"   {tname}: matched to a household row for {matched.mean():.1%} of rows; "
        f"Area known {m['Area'].notna().mean():.1%}, Wealth known {m['Wealth'].notna().mean():.1%}")
    return m.drop(columns=["hhArea", "hhWealth", "hhDistrict", "hhDivision"])


def final(m, keep_w=True):
    m = m.drop(columns=[c for c in m.columns if c.startswith("_k")])
    if keep_w:
        m = m[m["w"] > 0]
    return m.reset_index(drop=True)


def survey_fill(m, cols, tname):
    g = m.groupby("Survey")
    rows = []
    for c in cols:
        if c in m:
            rows.append(g[c].apply(lambda s: s.notna().mean()).rename(c))
    if rows:
        t = pd.concat(rows, axis=1).round(2)
        log(f"-- {tname}: share of rows with a value, per survey (0 = this survey does not have the question)")
        log(t.to_string())


# ----------------------------------------------------------------------------- women
def method_label(c):
    s = re.sub(r"^Current method:\s*", "", c).strip()
    u = s.upper()
    if "STERIL" in u:
        return "Sterilisation"
    if "IUD" in u:
        return "IUD"
    if "INJECT" in u:
        return "Injectables"
    if "IMPLANT" in u:
        return "Implants"
    if "PILL" in u:
        return "Pill"
    if "MALE CONDOM" in u or u.startswith("MALE CONDOM"):
        return "Condom"
    if "CONDOM" in u:
        return "Condom"
    if "ABSTIN" in u or "RHYTHM" in u:
        return "Periodic abstinence"
    if "WITHDRAW" in u:
        return "Withdrawal"
    return "Other methods"


WIFE_REASONS = {"goes out": "Goes out without telling husband", "neglects": "Neglects the children",
                "argues": "Argues with husband", "refuses sex": "Refuses sex with husband", "burns": "Burns the food"}


def wife_beating(df, names):
    wb = [c for c in names if "wife beating" in c.lower() and c in df.columns]
    out = {}
    for key, lab in WIFE_REASONS.items():
        cs = [c for c in wb if key in c.lower()]
        out[lab] = any_yes(df, cs).clip(upper=1) if cs else NA(df.index)
    anyv = pd.concat(out.values(), axis=1).max(axis=1, skipna=True)
    return out, anyv


def build_women(path, keyed):
    log("\n== Women")
    names = pq.ParquetFile(path).schema_arrow.names
    df = read(path, r"^(Result of woman's interview|Age of woman|Age of respondent \(calculated\)|Ever attended school|Education|Women's Education|"
                    r"Area|Area of residence|Area \[HH6\]|Area \(Original\)|Wealth index quintiles?|Women's sample weight|Woman's sample weight|"
                    r"Currently using a method to avoid pregnancy|Currently married|Delivery by caesarean section|Place of delivery|"
                    r"Received antenatal care|Times received antenatal care|Received prenatal care|Times received prenatal care|"
                    r"Any tetanus toxoid injection during last pregnancy|Ever given birth|Currently smoking cigarettes|Children ever born(\.1| \[(CEB|CM10|CM11)\])?|"
                    r"Age at (first )?marriage(\.1| \[(WAGEM|MA9|MA11)\])?|Age at first marriage of woman|Age at first marriage/union)$|"
                    r"^Antenatal care:|^Prenatal care provider:|^Assistance at delivery:|^Current method:|wife beating justi")
    b = base(df)
    b["w"] = coalesce_num(df, ["Women's sample weight", "Woman's sample weight"])
    ok = completed(col(df, "Result of woman's interview"))
    b = b.copy()
    age = coalesce_num(df, ["Age of woman", "Age of respondent (calculated)"], 15, 49)
    b["Age"] = age
    b["AgeGroup"] = age_grp(age)
    raw_edu = coalesce(df, ["Education", "Women's Education"])
    edu = m_edu(raw_edu)
    s_raw = S(raw_edu)
    # Punjab 2011 / 2014 store the education level as 1-5 (1 = none ... 5 = higher); Punjab 2017 uses 0-4 (checked against the share with no schooling)
    shifted = b["Survey"].isin(["Punjab 2011", "Punjab 2014"]) & s_raw.str.match(r"^[1-5](\.0)?$", na=False).fillna(False)
    for k, lab in zip("12345", EDU):
        edu[shifted & s_raw.str.startswith(k).fillna(False)] = lab
    b["Education"] = edu
    b["ever_school"] = yn(col(df, "Ever attended school"))
    # contraception (among currently married women when that is known)
    married = yn(col(df, "Currently married"))
    use = yn(col(df, "Currently using a method to avoid pregnancy"))
    use = use.where(~(married == 0))
    b["contraception"] = use
    mcols = [c for c in names if c.startswith("Current method:") and not c.endswith("Missing")]
    mlab = {c: method_label(c) for c in mcols}
    method = OBJ(df.index)
    for c in mcols:
        t = pd.Series(ticked(df[c]), index=df.index)
        method = method.where(method.notna() | ~t, mlab[c])
    b["Method"] = method.where(use == 1)
    # attitudes
    reasons, anywb = wife_beating(df, names)
    for lab, v in reasons.items():
        b["WB: " + lab] = v
    b["wife_beating_any"] = anywb
    # delivery
    asc = [c for c in names if c.startswith("Assistance at delivery:")]
    skilled_c = [c for c in asc if re.search(r"doctor|nurse|midwife|mid wife|LHV|health visitor", c, re.I)]
    pl = S(col(df, "Place of delivery"))
    delivered = answered(df, asc) | (pl.notna() & ~pl.isin(["MISSING", "NO RESPONSE", "?"])).fillna(False).to_numpy(bool)
    b["skilled_birth"] = np.where(delivered, any_ticked(df, skilled_c).astype(float), np.nan)
    fac = NA(df.index)
    fac[pl.str.contains("HOME|RESIDENCE|TBA|ELSEWHERE", na=False)] = 0.0
    fac[pl.str.match(r"^1\d(\.0)?$", na=False)] = 0.0                  # numeric codes 11, 12 = home
    fac[pl.str.match(r"^[23]\d(\.0)?$", na=False)] = 1.0               # numeric codes 21-36 = public / private facility
    fac[pl.str.contains("HOSPITAL|CLINIC|HEALTH CENT|DISPENSARY|BHU|RHC|MATERNITY|MCH|THQ|DHQ|GOVT|GOVERNMENT|PRIVATE|PUBLIC|MEDICAL|FACILITY|TEACHING|SECTOR", na=False)
        & ~pl.str.contains("HOME|RESIDENCE", na=False)] = 1.0
    fac[pl.str.contains("MATERNITY", na=False)] = 1.0                  # private maternity home is a facility
    b["facility_birth"] = fac
    b["tetanus_preg"] = yn(col(df, "Any tetanus toxoid injection during last pregnancy"))
    b["caesarean"] = yn(col(df, "Delivery by caesarean section"))
    # antenatal care
    anc_c = [c for c in names if c.startswith("Antenatal care:") or c.startswith("Prenatal care provider:")]
    anc_sk = [c for c in anc_c if re.search(r"doctor|nurse|midwife|mid wife|LHV|health visitor", c, re.I)]
    recv = yn(coalesce(df, ["Received antenatal care", "Received prenatal care"]))
    anc_ans = recv.notna().to_numpy(bool) | answered(df, anc_c)
    b["anc_any"] = recv.where(recv.notna(), pd.Series(np.where(answered(df, anc_c), 1.0, np.nan), index=df.index))
    b["anc_skilled"] = np.where(anc_ans, any_ticked(df, anc_sk).astype(float), np.nan)
    times = coalesce_num(df, ["Times received antenatal care", "Times received prenatal care"], 0, 30)
    b["anc_4plus"] = np.where(times.notna(), (times >= 4).astype(float), np.nan)
    b["Area"] = m_area(coalesce(df, ["Area", "Area of residence", "Area [HH6]", "Area (Original)"]))
    b["Wealth"] = m_wealth(coalesce(df, ["Wealth index quintile", "Wealth index quintiles"]))
    b2 = b.copy()
    own_area, own_w = b2["Area"], b2["Wealth"]
    m, matched = attach_hh(b2.drop(columns=["Area", "Wealth"]), keyed)
    m["Area"] = m["hhArea"].where(m["hhArea"].notna(), own_area.values)
    m["Wealth"] = m["hhWealth"].where(m["hhWealth"].notna(), own_w.values)
    m["District"], m["Division"] = m["hhDistrict"], m["hhDivision"]
    log(f"   women: matched to a household row for {matched.mean():.1%}; Area known {m['Area'].notna().mean():.1%}, Wealth known {m['Wealth'].notna().mean():.1%}")
    m = m.drop(columns=["hhArea", "hhWealth", "hhDistrict", "hhDivision"])
    # CEB / WAGEM are the standard MICS computed variables; their column name differs by survey, so take the first one present
    m["children_born"] = coalesce_num(df, ["Children ever born [CEB]", "Children ever born.1", "Children ever born [CM10]", "Children ever born [CM11]",
                                           "Children ever born"], 0, 25).values
    m["marr_age"] = coalesce_num(df, ["Age at first marriage [WAGEM]", "Age at marriage [WAGEM]", "Age at first marriage.1", "Age at first marriage of woman",
                                      "Age at first marriage/union", "Age at first marriage [MA9]", "Age at first marriage [MA11]", "Age at marriage [MA9]",
                                      "Age at first marriage", "Age at marriage"], 8, 49).values
    m = m[ok.values]
    m = final(m)
    survey_fill(m, ["children_born", "marr_age"], "women fertility / marriage")
    survey_fill(m, ["Education", "ever_school", "contraception", "wife_beating_any", "skilled_birth", "facility_birth", "caesarean",
                    "anc_skilled", "anc_4plus", "Area", "Wealth"], "women")
    log("   unmapped Place of delivery values (top):",
        S(col(df, "Place of delivery"))[fac.isna() & pl.notna()].value_counts().head(6).to_dict())
    return m


# ----------------------------------------------------------------------------- men
def build_men(path, keyed):
    log("\n== Men")
    names = pq.ParquetFile(path).schema_arrow.names
    df = read(path, r"^(Result of man's interview|Age of man|Ever attended school|Education|Area|Area\.1|Wealth index quintiles?|Men's sample weight)$|wife beating justi")
    b = base(df)
    b["w"] = coalesce_num(df, ["Men's sample weight"])
    ok = completed(col(df, "Result of man's interview"))
    age = coalesce_num(df, ["Age of man"], 15, 49)
    b["Age"] = age
    b["AgeGroup"] = age_grp(age)
    b["Education"] = m_edu(col(df, "Education"))
    b["ever_school"] = yn(col(df, "Ever attended school"))
    reasons, anywb = wife_beating(df, names)
    for lab, v in reasons.items():
        b["WB: " + lab] = v
    b["wife_beating_any"] = anywb
    own_area = m_area(coalesce(df, ["Area", "Area.1"]))
    own_w = m_wealth(coalesce(df, ["Wealth index quintile", "Wealth index quintiles"]))
    m, matched = attach_hh(b, keyed)
    m["Area"] = m["hhArea"].where(m["hhArea"].notna(), own_area.values)
    m["Wealth"] = m["hhWealth"].where(m["hhWealth"].notna(), own_w.values)
    m["District"], m["Division"] = m["hhDistrict"], m["hhDivision"]
    log(f"   men: matched {matched.mean():.1%}; Area known {m['Area'].notna().mean():.1%}, Wealth known {m['Wealth'].notna().mean():.1%}")
    m = m.drop(columns=["hhArea", "hhWealth", "hhDistrict", "hhDivision"])
    m = final(m[ok.values])
    survey_fill(m, ["Education", "ever_school", "wife_beating_any"], "men")
    return m


# ----------------------------------------------------------------------------- children under 5
def anthro(df, z, flag, lo=-6, hi=6):
    v = coalesce_num(df, [z], lo, hi)
    if flag in df.columns:
        f = S(df[flag])
        v = v.where(~f.isin(["ERROR FLAG", "1", "1.0"]))
    return v


def card_year(df, names):
    flag = pd.Series(False, index=df.index)
    seen = pd.Series(False, index=df.index)
    for c in names:
        s = df[c].astype("string").str.strip()
        yr = s.str.match(r"^(19|20)\d\d(\.0)?$", na=False)
        flag |= yr
        seen |= s.notna()
    return flag, seen


def build_u5(path, keyed):
    log("\n== Children under 5")
    names = pq.ParquetFile(path).schema_arrow.names
    pats = (r"^(Result of interview for children under 5|Sex|Area|Area of residence|Area \[HH6\]|Area \(Original\)|Wealth index quintiles?|"
            r"Age \(months\)|Age \(in months\)(\.\d)?|Age in days|Children's sample weight|Children under 5's sample weight|"
            r"Mother's education|Mother's Education_1|Highest level of education attended \(Mother/Caretaker\)|"
            r"Attends early childhood education programme|Currently attending early childhood education programme|"
            r"Ever attended pre-school/katchi/ECE programe|"
            r"Height for age z-score WHO|Weight for age z-score WHO|Weight for height z-score WHO|"
            r"Height for age flag WHO|Weight for age flag WHO|Weight for height flag WHO)$|"
            r"^Year( of)? (BCG|Polio|PENTA|Penta|Pentavalent|Pentavelent|DPT|Measles)|^Child ever given (BCG|Polio|Penta|Pentavelent|Pentavalent|DPT|Measles)|"
            r"^(Child had diarrhoea in last 2 weeks|Child ill with fever in last 2 weeks|Drank fluid made from special packet \(ORS\)|Child given ORS packet solution|"
            r"Child received a Vitamin A dose within the last 6 months|Child given Vitamin A dose within last 6 months|Received a vitamin a dose like \(this/any of these\) within the last 6 months)$")
    df = read(path, pats)
    b = base(df)
    b["w"] = coalesce_num(df, ["Children's sample weight", "Children under 5's sample weight"])
    ok = completed(col(df, "Result of interview for children under 5"))
    b["Sex"] = m_sex(col(df, "Sex"))
    months = coalesce_num(df, ["Age (months)", "Age (in months)", "Age (in months).1", "Age (in months).2"], 0, 59)
    days = coalesce_num(df, ["Age in days"], 0, 1830) / 30.4375
    months = months.where(months.notna(), days.round().where(days < 60))
    b["AgeMonths"] = months
    b["AgeGroup"] = pd.cut(months, bins=[0, 6, 12, 24, 36, 48, 60], labels=["0-5 m", "6-11 m", "12-23 m", "24-35 m", "36-47 m", "48-59 m"],
                          right=False).astype("object")
    b["MotherEdu"] = m_edu(coalesce(df, ["Mother's education", "Mother's Education", "Mother's Education_1", "Highest level of education attended (Mother/Caretaker)"]))
    haz = anthro(df, "Height for age z-score WHO", "Height for age flag WHO")
    waz = anthro(df, "Weight for age z-score WHO", "Weight for age flag WHO")
    whz = anthro(df, "Weight for height z-score WHO", "Weight for height flag WHO")
    # a survey whose average HAZ is implausible is not used (documented in the log)
    tmp = pd.DataFrame({"s": b["Survey"], "haz": haz})
    mean = tmp.groupby("s")["haz"].mean()
    bad = mean[(mean > -0.5) | (mean < -3.5)].index.tolist()
    if bad:
        log("   !! WHO z-scores look invalid (mean HAZ outside -3.5..-0.5) and are NOT used for:", bad)
        for z in (haz, waz, whz):
            z[b["Survey"].isin(bad)] = np.nan
    for z, name in ((haz, "stunted"), (waz, "underweight"), (whz, "wasted")):
        b[name] = np.where(z.notna(), (z < -2).astype(float), np.nan)
    b["severely_stunted"] = np.where(haz.notna(), (haz < -3).astype(float), np.nan)
    b["haz"], b["waz"], b["whz"] = haz, waz, whz
    b["diarrhoea"] = yn(col(df, "Child had diarrhoea in last 2 weeks"))
    b["fever"] = yn(col(df, "Child ill with fever in last 2 weeks"))
    _ors = yn(coalesce(df, ["Drank fluid made from special packet (ORS)", "Child given ORS packet solution"]))
    b["ors"] = np.where(b["diarrhoea"].eq(1).to_numpy(bool), _ors, np.nan)                 # only children who had diarrhoea
    b["vitamin_a"] = yn(coalesce(df, ["Child received a Vitamin A dose within the last 6 months", "Child given Vitamin A dose within last 6 months",
                                       "Received a vitamin a dose like (this/any of these) within the last 6 months"]))
    groups = {
        "BCG": (r"^Year of BCG", r"^Child ever given BCG"),
        "Polio": (r"^Year of Polio", r"^Child ever given Polio"),
        "Penta/DPT": (r"^Year of (PENTA|Penta|Pentavalent|Pentavelent|DPT)", r"^Child ever given (Penta|Pentavelent|Pentavalent|DPT)"),
        "Measles": (r"^Year( of)? Measles", r"^Child ever given Measles"),
    }
    for g, (ycols, rcols) in groups.items():
        yc = cols_like(names, ycols)
        rc = cols_like(names, rcols)
        has_card, seen = card_year(df, [c for c in yc if c in df.columns]) if yc else (pd.Series(False, index=df.index), pd.Series(False, index=df.index))
        recall = any_yes(df, [c for c in rc if c in df.columns])
        got = np.where(has_card | (recall == 1), 1.0, np.where(recall == 0, 0.0, np.where(seen, 0.0, np.nan)))
        b["vacc_" + g] = got
    ece = yn(coalesce(df, ["Attends early childhood education programme", "Currently attending early childhood education programme",
                           "Ever attended pre-school/katchi/ECE programe"]))
    b["ece"] = ece
    own_area = m_area(coalesce(df, ["Area", "Area of residence", "Area [HH6]", "Area (Original)"]))
    own_w = m_wealth(coalesce(df, ["Wealth index quintile", "Wealth index quintiles"]))
    m, matched = attach_hh(b, keyed)
    m["Area"] = m["hhArea"].where(m["hhArea"].notna(), own_area.values)
    m["Wealth"] = m["hhWealth"].where(m["hhWealth"].notna(), own_w.values)
    m["District"], m["Division"] = m["hhDistrict"], m["hhDivision"]
    log(f"   u5: matched {matched.mean():.1%}; Area known {m['Area'].notna().mean():.1%}, Wealth known {m['Wealth'].notna().mean():.1%}")
    m = m.drop(columns=["hhArea", "hhWealth", "hhDistrict", "hhDivision"])
    m = final(m[ok.values])
    kids = m[(m["AgeMonths"] >= 12) & (m["AgeMonths"] < 36)]
    survey_fill(m, ["Sex", "AgeMonths", "stunted", "wasted", "underweight", "MotherEdu", "ece", "diarrhoea", "fever", "ors", "vitamin_a"], "children U5")
    survey_fill(kids, ["vacc_BCG", "vacc_Polio", "vacc_Penta/DPT", "vacc_Measles"], "children 12-35 months (immunisation)")
    return m


# ----------------------------------------------------------------------------- birth history
def build_births(path, keyed):
    log("\n== Birth history")
    df = read(path, r"^(Sex of child|Sex of newborns|Sex of newborn|Still alive|Year of birth|Age at death months \(imputed\)|Birth order|Previous birth interval|Mother's age at birth|"
                    r"Area|Area\.1|Wealth index quintiles?|Woman's sample weight|Women's sample weight)$")
    b = base(df)
    b["w"] = coalesce_num(df, ["Woman's sample weight", "Women's sample weight"])
    b["Sex"] = m_sex(coalesce(df, ["Sex of child", "Sex of newborns", "Sex of newborn"]))
    alive = yn(col(df, "Still alive"))
    b["alive"] = alive
    adm = coalesce_num(df, ["Age at death months (imputed)"], 0, 1200)
    b["age_death_m"] = adm
    byear = coalesce_num(df, ["Year of birth"], 1950, 2025)
    b["birth_year"] = byear
    b["yrs_before"] = num(df["Year"]) - byear
    died = alive == 0
    b["died"] = np.where(alive.notna(), died.astype(float), np.nan)
    ad = adm.where(died)
    b["died_neonatal"] = np.where(alive.notna(), (died & (ad < 1)).astype(float), np.nan)
    b["died_infant"] = np.where(alive.notna(), (died & (ad < 12)).astype(float), np.nan)
    b["died_u5"] = np.where(alive.notna(), (died & (ad < 60)).astype(float), np.nan)
    bo = S(col(df, "Birth order")).str.replace(".0", "", regex=False)
    b["BirthOrder"] = bo.where(bo.isin(["1", "2-3", "4-6", "7+"]))
    iv = S(col(df, "Previous birth interval"))
    b["BirthInterval"] = iv.where(iv.isin(["FIRST BIRTH", "<2 YEARS", "2 YEARS", "3 YEARS", "4+ YEARS"])).str.capitalize()
    ma = S(col(df, "Mother's age at birth"))
    b["MotherAgeAtBirth"] = ma.where(ma.isin(["<20", "20-34", "35+"]))
    own_area = m_area(coalesce(df, ["Area", "Area.1"]))
    own_w = m_wealth(coalesce(df, ["Wealth index quintile", "Wealth index quintiles"]))
    m, matched = attach_hh(b, keyed)
    m["Area"] = m["hhArea"].where(m["hhArea"].notna(), own_area.values)
    m["Wealth"] = m["hhWealth"].where(m["hhWealth"].notna(), own_w.values)
    m["District"], m["Division"] = m["hhDistrict"], m["hhDivision"]
    log(f"   births: matched {matched.mean():.1%}; Area known {m['Area'].notna().mean():.1%}, Wealth known {m['Wealth'].notna().mean():.1%}")
    m = final(m.drop(columns=["hhArea", "hhWealth", "hhDistrict", "hhDivision"]))
    survey_fill(m, ["Sex", "died", "age_death_m", "BirthOrder", "BirthInterval", "MotherAgeAtBirth"], "births")
    return m


# ----------------------------------------------------------------------------- sibling history
def build_sibs(path, keyed):
    log("\n== Sibling history")
    df = read(path, r"^(Sibling's gender|Sibling still alive|Age of sibling|Age at death of sibling|Years since death|Death due to an act of violence|"
                    r"Death due to an accident|Area|Wealth index quintiles?|Woman's sample weight|Women's sample weight|Education)$")
    b = base(df)
    b["w"] = coalesce_num(df, ["Woman's sample weight", "Women's sample weight"])
    b["Sex"] = m_sex(col(df, "Sibling's gender"))
    alive = yn(col(df, "Sibling still alive"))
    b["dead"] = np.where(alive.notna(), (alive == 0).astype(float), np.nan)
    b["age_alive"] = coalesce_num(df, ["Age of sibling"], 0, 99).where(alive == 1)
    b["age_at_death"] = coalesce_num(df, ["Age at death of sibling"], 0, 99).where(alive == 0)
    b["years_since_death"] = coalesce_num(df, ["Years since death"], 0, 99).where(alive == 0)
    b["death_violence"] = yn(col(df, "Death due to an act of violence")).where(alive == 0)
    b["death_accident"] = yn(col(df, "Death due to an accident")).where(alive == 0)
    own_area = m_area(col(df, "Area"))
    own_w = m_wealth(coalesce(df, ["Wealth index quintile", "Wealth index quintiles"]))
    m, matched = attach_hh(b, keyed)
    m["Area"] = m["hhArea"].where(m["hhArea"].notna(), own_area.values)
    m["Wealth"] = m["hhWealth"].where(m["hhWealth"].notna(), own_w.values)
    m["District"], m["Division"] = m["hhDistrict"], m["hhDivision"]
    log(f"   siblings: matched {matched.mean():.1%}")
    m = final(m.drop(columns=["hhArea", "hhWealth", "hhDistrict", "hhDivision"]))
    survey_fill(m, ["Sex", "dead", "age_at_death", "death_violence"], "siblings")
    return m


# ----------------------------------------------------------------------------- mosquito nets
def build_nets(path, keyed):
    log("\n== Mosquito nets")
    df = read(path, r"^(Mosquito net observed|Persons slept under mosquito net last night|Number of mosquito nets|Months ago net obtained|"
                    r"Area|Wealth index quintiles?|Household sample weight|Long Lasting ITN)$")
    b = base(df)
    b["w"] = coalesce_num(df, ["Household sample weight"])
    obs = S(col(df, "Mosquito net observed"))
    b["observed"] = np.where(obs.str.startswith("OBSERVED", na=False), 1.0, np.where(obs.str.startswith("NOT OBSERVED", na=False), 0.0, np.nan))
    b["slept"] = yn(col(df, "Persons slept under mosquito net last night"))   # Yes/No per net
    b["hh_nets"] = coalesce_num(df, ["Number of mosquito nets"], 0, 30)
    b["net_age_m"] = coalesce_num(df, ["Months ago net obtained"], 0, 300)
    b["lln"] = yn(col(df, "Long Lasting ITN"))
    own_area = m_area(col(df, "Area"))
    own_w = m_wealth(coalesce(df, ["Wealth index quintile", "Wealth index quintiles"]))
    m, matched = attach_hh(b, keyed)
    m["Area"] = m["hhArea"].where(m["hhArea"].notna(), own_area.values)
    m["Wealth"] = m["hhWealth"].where(m["hhWealth"].notna(), own_w.values)
    m["District"], m["Division"] = m["hhDistrict"], m["hhDivision"]
    log(f"   nets: matched {matched.mean():.1%}")
    m = final(m.drop(columns=["hhArea", "hhWealth", "hhDistrict", "hhDivision"]))
    survey_fill(m, ["observed", "slept", "hh_nets"], "nets")
    return m


# ----------------------------------------------------------------------------- children 5-17
def build_c5(path, keyed):
    log("\n== Children 5-17")
    names = pq.ParquetFile(path).schema_arrow.names
    df = read(path, r"^(Age of child|Age|Sex|HL4|Area|Wealth index quintiles?|Children 5-17's sample weight|Mother's education|"
                    r"Ever attended school or early childhood programme|Attended school or early childhood programme during current school year|"
                    r"Engaged in any other activity for income in past week|Worked or helped on garden in past week|"
                    r"Child needs to be physically punished to be brought up properly|Number of hours engaged in past week)$|"
                    r"^Household chores in past week|^Child has difficulty|^Compared with children of the same age, child has difficulty")
    b = base(df)
    b["w"] = coalesce_num(df, ["Children 5-17's sample weight"])
    age = coalesce_num(df, ["Age of child", "Age"], 5, 17)
    b["Age"] = age
    b["AgeGroup"] = pd.cut(age, bins=[5, 8, 11, 14, 18], labels=["5-7", "8-10", "11-13", "14-17"], right=False).astype("object")
    b["Sex"] = m_sex(coalesce(df, ["Sex", "HL4"]))          # Sindh 2018 stores the child's sex as HL4
    b["MotherEdu"] = m_edu(col(df, "Mother's education"))
    b["ever_school"] = yn(col(df, "Ever attended school or early childhood programme"))
    b["attending"] = yn(col(df, "Attended school or early childhood programme during current school year"))
    b.loc[b["ever_school"] == 0, "attending"] = 0.0     # asked only of children who ever attended: never attended = not attending now
    b["works_income"] = yn(col(df, "Engaged in any other activity for income in past week"))
    chores = [c for c in names if c.startswith("Household chores in past week")]
    b["chores"] = any_yes(df, chores)
    b["punish_endorse"] = yn(col(df, "Child needs to be physically punished to be brought up properly"))
    fd = [c for c in names if re.match(r"^(Child has difficulty|Compared with children of the same age, child has difficulty)", c)]
    sev = pd.concat([S(df[c]).str.contains("A LOT|CANNOT", na=False).where(df[c].notna()).astype("float") for c in fd], axis=1) if fd else None
    b["func_difficulty"] = sev.max(axis=1, skipna=True) if sev is not None else NA(df.index)
    own_area = m_area(col(df, "Area"))
    own_w = m_wealth(coalesce(df, ["Wealth index quintile", "Wealth index quintiles"]))
    m, matched = attach_hh(b, keyed)
    m["Area"] = m["hhArea"].where(m["hhArea"].notna(), own_area.values)
    m["Wealth"] = m["hhWealth"].where(m["hhWealth"].notna(), own_w.values)
    m["District"], m["Division"] = m["hhDistrict"], m["hhDivision"]
    log(f"   children 5-17: matched {matched.mean():.1%}")
    m = final(m.drop(columns=["hhArea", "hhWealth", "hhDistrict", "hhDivision"]))
    survey_fill(m, ["Sex", "Age", "ever_school", "attending", "works_income", "chores", "punish_endorse", "func_difficulty"], "children 5-17")
    return m


# ----------------------------------------------------------------------------- household members (optional)
def build_members(path, keyed):
    log("\n== Household members (optional file found)")
    names = pq.ParquetFile(path).schema_arrow.names
    age_cols = [c for c in names if re.match(r"^Age(\.\d+)?$|^Age \[HL6\]$", c)]
    df = read(path, None, ["Sex", "Area", "Wealth index quintile", "Household sample weight", "Education of household head",
                           "Highest level of education attended", "Ever attended school or pre-school"] + age_cols)
    b = base(df)
    b["w"] = coalesce_num(df, ["Household sample weight"])
    a = OBJ(df.index)
    for c in age_cols:
        a = a.where(a.notna(), df[c].astype("object"))
    s = S(a).str.replace("+", "", regex=False)
    age = num(s).where(lambda x: (x >= 0) & (x <= 99))
    b["Age"] = age
    b["AgeGroup"] = pd.cut(age, bins=list(range(0, 85, 5)) + [120], labels=[f"{i}-{i + 4}" for i in range(0, 80, 5)] + ["80+"], right=False).astype("object")
    b["Sex"] = m_sex(col(df, "Sex"))
    own_area = m_area(col(df, "Area"))
    own_w = m_wealth(col(df, "Wealth index quintile"))
    m, matched = attach_hh(b, keyed)
    m["Area"] = m["hhArea"].where(m["hhArea"].notna(), own_area.values)
    m["Wealth"] = m["hhWealth"].where(m["hhWealth"].notna(), own_w.values)
    m["District"], m["Division"] = m["hhDistrict"], m["hhDivision"]
    m = final(m.drop(columns=["hhArea", "hhWealth", "hhDistrict", "hhDivision"]))
    survey_fill(m, ["Sex", "Age", "Area", "Wealth"], "members")
    return m


# ----------------------------------------------------------------------------- main
def audit_labels(out):
    """final check: in every text column of every cleaned table, report values that differ only by case / spaces / punctuation"""
    import re as _re
    log("\n== Label audit (text values that differ only by upper/lower case, spaces or punctuation)")
    found = 0
    for f in sorted(Path(out).glob("*.parquet")):
        d = pd.read_parquet(f)
        for c in d.columns:
            if d[c].dtype.kind in "fiub" or str(d[c].dtype) in ("Float64", "Int64", "boolean"):
                continue
            u = pd.Series(d[c].dropna().astype(str).unique())
            if len(u) > 3000:
                continue
            key = u.map(lambda t: _re.sub(r"[^a-z0-9<>]", "", t.lower()))
            dup = u.groupby(key.values).agg(list)
            for v in dup[dup.map(len) > 1]:
                found += 1
                log(f"   {f.stem}.{c}: {v}")
    log("   none found" if not found else f"   {found} group(s) found - check them")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src = Path(args[0]) if args else Path(DEFAULT_IN)
    out = Path(args[1]) if len(args) > 1 else src.parent / "dashboard_data"
    if not src.is_dir():
        sys.exit(f"Input folder not found: {src}")
    out.mkdir(parents=True, exist_ok=True)

    def P(name):
        p = src / f"MICS_{name}.parquet"
        if not p.exists():                                # also accept an upload prefix like 1234abcd-MICS_Women.parquet
            cand = sorted(src.glob(f"*MICS_{name}.parquet"))
            p = cand[0] if cand else p
        return p

    hh_path = P("Households")
    if not hh_path.exists():
        sys.exit(f"MICS_Households.parquet not found in {src}")
    hh, cov, keyed = build_hh(hh_path)
    hh.drop(columns=[c for c in hh.columns if c.startswith("_k")]).to_parquet(out / "hh.parquet", index=False)
    survey_fill(hh, ["has_tv", "has_fridge", "has_mobile", "has_motorbike", "has_bank", "rents_home"], "households assets")
    survey_fill(hh, ["Area", "Wealth", "water_improved", "sanitation_improved", "electricity", "clean_fuel", "handwash_water",
                     "crowded", "female_head", "head_edu", "District"], "households")

    jobs = [("women", "Women", build_women), ("men", "Men", build_men), ("children", "Children_U5", build_u5),
            ("births", "BirthHistory", build_births), ("siblings", "SiblingHistory", build_sibs),
            ("nets", "MosquitoNets", build_nets), ("c5to17", "Children_5to17", build_c5), ("members", "HouseholdMembers", build_members)]
    sizes = {"households": cov.set_index("Survey")["completed"]}
    for key, fname, fn in jobs:
        p = P(fname)
        if not p.exists():
            log(f"\n-- {fname}: file not found, page section will show 'data not loaded'")
            continue
        d = fn(p, keyed)
        d.to_parquet(out / f"{key}.parquet", index=False)
        sizes[key] = d.groupby("Survey").size()
    covdf = pd.DataFrame(sizes).fillna(0).astype(int)
    covdf.index.name = "Survey"
    covdf = covdf.join(cov.set_index("Survey")[["sampled", "response_rate"]]).reset_index()
    covdf.to_csv(out / "coverage.csv", index=False)
    audit_labels(out)
    (out / "prep_log.txt").write_text("\n".join(LOG), encoding="utf-8")
    print("\nDone ->", out)


if __name__ == "__main__":
    main()
