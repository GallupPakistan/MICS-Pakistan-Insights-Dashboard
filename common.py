"""Shared code for the MICS Pakistan dashboard: data loading, filters, weighted statistics, charts, KPI cards."""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# keep working on both older and newer Streamlit versions
STRETCH = {"width": "stretch"} if "width" in __import__("inspect").signature(st.plotly_chart).parameters else {"use_container_width": True}

PLOT_CONFIG = {"displaylogo": False, "toImageButtonOptions": {"format": "png", "scale": 3, "filename": "mics_chart"},
               "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def _wrap_title(fig, limit=44):
    """long chart titles are cut off at the chart edge: break them over two or three lines instead"""
    try:
        t = fig.layout.title.text
        if not t or "<br>" in t or len(t) <= limit:
            return
        import textwrap
        lines = textwrap.wrap(t, width=int(max(limit - 6, len(t) / np.ceil(len(t) / (limit - 6)) + 4)))
        fig.update_layout(title_text="<br>".join(lines))
        mt = fig.layout.margin.t or 60
        fig.update_layout(margin_t=max(mt, 60) + 21 * (len(lines) - 1))
    except Exception:
        pass


def show(fig, key=None):
    """draw a chart (camera icon in the chart toolbar downloads it as a sharp PNG)"""
    _wrap_title(fig)
    try:   # horizontal bars with the value written past the bar end need a little space on the right
        if any(getattr(t, "type", "") == "bar" and getattr(t, "orientation", None) == "h" and getattr(t, "textposition", None) == "outside" for t in fig.data):
            fig.update_layout(margin_r=max(fig.layout.margin.r or 0, 56))
    except Exception:
        pass
    st.plotly_chart(fig, **STRETCH, key=key, config=PLOT_CONFIG)


# ----------------------------------------------------------------------------- data location
def data_dir() -> Path:
    here = Path(__file__).resolve().parent
    for p in (os.environ.get("MICS_DASH_DATA"), here / "data", here.parent / "dashboard_data", here / "dashboard_data"):
        if p and Path(p).is_dir() and (Path(p) / "hh.parquet").exists():
            return Path(p)
    return here / "data"


TABLES = {"hh": "Households", "women": "Women", "men": "Men", "children": "Children under 5", "births": "Birth history",
          "siblings": "Sibling history", "nets": "Mosquito nets", "c5to17": "Children 5-17", "members": "Household members"}
CATS = ["Province", "Survey", "Area", "Wealth", "Sex", "Education", "MotherEdu", "head_edu", "AgeGroup", "District", "Division", "Method",
        "WaterSource", "ToiletType", "BirthOrder", "BirthInterval", "MotherAgeAtBirth"]


@st.cache_resource(show_spinner="Loading data ...")
def load(name: str):
    p = data_dir() / f"{name}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    for c in CATS:
        if c in df.columns:
            df[c] = df[c].astype("category")
    return df


def data_ready() -> bool:
    return (data_dir() / "hh.parquet").exists()


@st.cache_data
def coverage():
    p = data_dir() / "coverage.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


# ----------------------------------------------------------------------------- colours (the same colour always means the same thing)
PROV_COLORS = {"Punjab": "#0B5FA5", "Sindh": "#D1495B", "Khyber Pakhtunkhwa": "#2E9E6B", "Balochistan": "#E8A317", "Gilgit-Baltistan": "#8E5BA8"}
PROV_ORDER = ["Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan", "Gilgit-Baltistan"]
PSHORT = {"Gilgit-Baltistan": "GB", "Khyber Pakhtunkhwa": "KP"}
AREA_COLORS = {"Urban": "#6A3D9A", "Rural": "#B8860B"}
SEX_COLORS = {"Male": "#2C7FB8", "Female": "#E7298A"}
WEALTH = ["Poorest", "Second", "Middle", "Fourth", "Richest"]
WEALTH_COLORS = dict(zip(WEALTH, ["#B2182B", "#EF8A62", "#F2C14E", "#67A9CF", "#2166AC"]))
EDU = ["None / pre-primary", "Primary", "Middle", "Secondary", "Higher"]
EDU_COLORS = dict(zip(EDU, ["#B2182B", "#EF8A62", "#F2C14E", "#67A9CF", "#2166AC"]))
GOOD, BAD, NEUTRAL = "#2E7D32", "#C62828", "#546E7A"
CAT_COLORS = ["#0B5FA5", "#D1495B", "#2E9E6B", "#E8A317", "#8E5BA8", "#17A2B8", "#7F7F7F", "#A0522D", "#E377C2", "#BCBD22"]
STATUS_COLORS = {"Piped water": "#0B5FA5", "Tube well / pump": "#17A2B8", "Protected well / spring": "#2E9E6B",
                 "Bottled / filtered / rain": "#7FC8A9", "Tanker / cart": "#E8A317", "Unprotected well / spring": "#E4572E",
                 "Surface water": "#8C2D04", "Other": "#9AA5B1"}
TOILET_COLORS = {"Flush to sewer / septic / pit": "#0B5FA5", "Pit latrine with slab / VIP / composting": "#2E9E6B",
                 "Other unimproved (open drain, no slab, bucket)": "#E8A317", "Open defecation (no facility)": "#C62828"}


def _mix(hex_color, f):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (int(c + (255 - c) * f) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def survey_province(s: str) -> str:
    rev = {"GB": "Gilgit-Baltistan", "KP": "Khyber Pakhtunkhwa"}
    key = s.rsplit(" ", 1)[0]
    return rev.get(key, key)


def survey_colors(surveys):
    """a survey gets its province colour; older surveys of the same province are lighter"""
    out = {}
    for prov in PROV_ORDER:
        ss = sorted([s for s in surveys if survey_province(s) == prov], key=lambda s: int(s.rsplit(" ", 1)[1]))
        for i, s in enumerate(ss):
            f = 0.0 if i == len(ss) - 1 else 0.45 if len(ss) == 2 else 0.55 - 0.3 * i / max(len(ss) - 1, 1)
            out[s] = _mix(PROV_COLORS[prov], f)
    return out


def survey_order(surveys):
    key = lambda s: (PROV_ORDER.index(survey_province(s)) if survey_province(s) in PROV_ORDER else 9, int(s.rsplit(" ", 1)[1]))
    return sorted(set(surveys), key=key)


def color_map(dim, values):
    values = [v for v in pd.unique(pd.Series(values).astype(str)) if v != "nan"]
    if dim == "Province":
        return {v: PROV_COLORS.get(v, "#888") for v in values}
    if dim == "Survey":
        return survey_colors(values)
    if dim == "Area":
        return {v: AREA_COLORS.get(v, "#888") for v in values}
    if dim == "Sex":
        return {v: SEX_COLORS.get(v, "#888") for v in values}
    if dim == "Wealth":
        return {v: WEALTH_COLORS.get(v, "#888") for v in values}
    if dim in ("Education", "MotherEdu", "head_edu"):
        return {v: EDU_COLORS.get(v, "#888") for v in values}
    return {v: CAT_COLORS[i % len(CAT_COLORS)] for i, v in enumerate(values)}


def cat_order(dim, values):
    values = list(pd.unique(pd.Series(values).astype(str)))
    if dim == "Province":
        return [p for p in PROV_ORDER if p in values]
    if dim == "Survey":
        return survey_order(values)
    if dim == "Area":
        return [a for a in ("Urban", "Rural") if a in values]
    if dim == "Wealth":
        return [w for w in WEALTH if w in values]
    if dim in ("Education", "MotherEdu", "head_edu"):
        return [e for e in EDU if e in values]
    if dim == "Sex":
        return [s for s in ("Male", "Female") if s in values]
    if dim in FIXED_ORDER:
        known = [v for v in FIXED_ORDER[dim] if v in values]
        return known + sorted(v for v in values if v not in known)
    if dim == "AgeGroup":
        return sorted(values, key=lambda v: float(str(v).replace("+", "-").split("-")[0].split()[0]) if str(v)[:1].isdigit() else 999)
    return sorted(values)


FIXED_ORDER = {"BirthInterval": ["First birth", "<2 years", "2 years", "3 years", "4+ years"],
               "MotherAgeAtBirth": ["<20", "20-34", "35+"], "BirthOrder": ["1", "2-3", "4-6", "7+"]}

DIM_LABEL = {"Province": "Province", "Survey": "Survey (province + year)", "Area": "Area (urban / rural)", "Wealth": "Wealth quintile",
             "Sex": "Sex", "Education": "Education", "MotherEdu": "Mother's education", "head_edu": "Head's education",
             "AgeGroup": "Age group", "District": "District", "Method": "Method", "WaterSource": "Water source", "ToiletType": "Toilet type",
             "BirthOrder": "Birth order", "BirthInterval": "Interval since previous birth", "MotherAgeAtBirth": "Mother's age at birth"}

# ----------------------------------------------------------------------------- filters (drawn in the sidebar by app.py)
FKEY = "flt_"


# Population of each province (2023 census, rounded; edit here if you prefer other figures). Used only when
# "Population-weighted (Pakistan)" is switched on, to turn the five provincial surveys into one national estimate.
POP = {"Punjab": 127_700_000, "Sindh": 55_700_000, "Khyber Pakhtunkhwa": 40_900_000, "Balochistan": 14_900_000, "Gilgit-Baltistan": 1_500_000}


def get_filters() -> dict:
    ss = st.session_state
    return dict(
        provinces=ss.get(FKEY + "prov") or PROV_ORDER,
        surveys=ss.get(FKEY + "surv") or [],
        areas=ss.get(FKEY + "area") or ["Urban", "Rural"],
        wealth=ss.get(FKEY + "wealth") or WEALTH,
        sexes=ss.get(FKEY + "sex") or ["Male", "Female"],
        districts=ss.get(FKEY + "dist") or [],
        compare=ss.get(FKEY + "cmp", "Province"),
        min_n=ss.get(FKEY + "minn", 50),
        show_ci=ss.get(FKEY + "ci", False),
        pop=ss.get(FKEY + "pop", True),
    )


def all_surveys():
    hh = load("hh")
    return survey_order(hh["Survey"].astype(str).unique()) if hh is not None else []


@st.cache_data(show_spinner=False)
def _pop_factor(table, provinces, surveys):
    """weight multiplier per SURVEY so that the weights of each survey add up to its province population
    (each survey then stands for its whole province; combined with the latest-survey rule this gives a Pakistan estimate)"""
    df = load(table)
    if df is None:
        return {}
    d = df[df["Province"].isin(provinces) & df["Survey"].isin(surveys)]
    tot = d.groupby("Survey", observed=True)["w"].sum()
    return {s: POP[survey_province(str(s))] / t for s, t in tot.items() if survey_province(str(s)) in POP and t > 0}


def apply(df, table=None, sex=True):
    """apply the sidebar filters to a table"""
    if df is None:
        return None
    F = get_filters()
    out = _apply(df, F, sex)
    if F["pop"] and table:
        surveys = F["surveys"] or all_surveys()
        fac = _pop_factor(table, tuple(F["provinces"]), tuple(surveys))
        if fac:
            out = out.assign(w=out["w"].to_numpy() * out["Survey"].astype(str).map(fac).fillna(0).to_numpy())
    return out


def _apply(df, F, sex=True):
    m = df["Province"].isin(F["provinces"])
    surveys = F["surveys"] or all_surveys()
    m &= df["Survey"].isin(surveys)
    if len(F["areas"]) < 2:
        m &= df["Area"].isin(F["areas"])
    if len(F["wealth"]) < 5:
        m &= df["Wealth"].isin(F["wealth"])
    if sex and "Sex" in df.columns and len(F["sexes"]) < 2:
        m &= df["Sex"].isin(F["sexes"])
    if F["districts"] and "District" in df.columns:
        m &= df["District"].isin(F["districts"])
    return df[m]


def latest_only(d, by=()):
    """A figure that is NOT split by survey would otherwise mix survey rounds (e.g. Punjab 2011 + 2014 + 2017).
    Unless the user picked surveys in the sidebar, keep only the most recent survey of each province that has data."""
    by = [by] if isinstance(by, str) else list(by)
    if d is None or d.empty or "Survey" in by or "Survey" not in d.columns or get_filters()["surveys"]:
        return d
    sv = d["Survey"].astype(str)
    yr = sv.str.rsplit(" ", n=1).str[1].astype(int)
    prov = sv.str.rsplit(" ", n=1).str[0]
    last = yr.groupby(prov).transform("max")
    return d[(yr == last).to_numpy()]


def compare_dim(df, allowed=("Province", "Survey", "Area", "Wealth", "Sex")):
    c = get_filters()["compare"]
    return c if (c in allowed and c in df.columns) else "Province"


# ----------------------------------------------------------------------------- weighted statistics
def rate(df, col, by, scale=100.0, where=None, min_n=None):
    """weighted share (0/1 flag) per group. Columns: by..., value, n, neff, lo, hi (95% CI, approx.)"""
    by = [by] if isinstance(by, str) else list(by)
    if df is None or col not in df.columns:
        return pd.DataFrame(columns=by + ["value", "n", "neff", "lo", "hi"])
    d = df if where is None else df[where(df)]
    d = latest_only(d[d[col].notna()], by)
    if d.empty:
        return pd.DataFrame(columns=by + ["value", "n", "neff", "lo", "hi"])
    d = d.assign(_v=d[col].astype(float) * d["w"], _w2=d["w"] ** 2)
    g = d.groupby(by, observed=True, dropna=True)
    out = g.agg(sv=("_v", "sum"), sw=("w", "sum"), sw2=("_w2", "sum"), n=("w", "size")).reset_index()
    out["p"] = out["sv"] / out["sw"]
    out["neff"] = out["sw"] ** 2 / out["sw2"]
    se = np.sqrt(out["p"] * (1 - out["p"]) / out["neff"])
    out["value"] = out["p"] * scale
    out["lo"] = (out["p"] - 1.96 * se).clip(lower=0) * scale
    out["hi"] = (out["p"] + 1.96 * se).clip(upper=1) * scale
    mn = get_filters()["min_n"] if min_n is None else min_n
    out = out[out["n"] >= mn]
    return out.drop(columns=["sv", "sw", "sw2", "p"])


def wmean(df, col, by, where=None):
    by = [by] if isinstance(by, str) else list(by)
    d = df if where is None else df[where(df)]
    d = latest_only(d[d[col].notna()], by)
    if d.empty:
        return pd.DataFrame(columns=by + ["value", "n"])
    d = d.assign(_v=d[col].astype(float) * d["w"])
    g = d.groupby(by, observed=True, dropna=True).agg(sv=("_v", "sum"), sw=("w", "sum"), n=("w", "size")).reset_index()
    g["value"] = g["sv"] / g["sw"]
    return g[g["n"] >= get_filters()["min_n"]].drop(columns=["sv", "sw"])


def dist(df, cat, by, order=None):
    """weighted % distribution of a categorical column inside each group"""
    by = [by] if isinstance(by, str) else list(by)
    d = latest_only(df[df[cat].notna()], by)
    if d.empty:
        return pd.DataFrame(columns=by + [cat, "pct", "n"])
    g = d.groupby(by + [cat], observed=True).agg(sw=("w", "sum"), n=("w", "size")).reset_index()
    tot = g.groupby(by, observed=True)["sw"].transform("sum")
    nn = g.groupby(by, observed=True)["n"].transform("sum")
    g["pct"] = g["sw"] / tot * 100
    g["n_group"] = nn
    g = g[g["n_group"] >= get_filters()["min_n"]]
    return g.drop(columns=["sw", "n"])


# ----------------------------------------------------------------------------- indicator registry
# key: (table, column, label, unit, polarity (+1 higher is better, -1 higher is worse, 0 neutral), subset, definition)
def imm(d):
    return (d["AgeMonths"] >= 12) & (d["AgeMonths"] < 36)


def u3to5(d):
    return (d["AgeMonths"] >= 36) & (d["AgeMonths"] < 60)


def births0_9(d):
    return (d["yrs_before"] >= 0) & (d["yrs_before"] <= 9)


def births5_9(d):
    return (d["yrs_before"] >= 5) & (d["yrs_before"] <= 9)


IND = {
    "Improved drinking water": ("hh", "water_improved", "%", +1, None, "Households whose main drinking-water source is improved (JMP 2017 / MICS6): piped, tube well / pump, protected well or spring, bottled / filtered, rain water, tanker-truck or cart with small tank."),
    "Piped water": ("hh", "water_piped", "%", +1, None, "Households with piped water (into dwelling, yard, neighbour or public tap)."),
    "Improved sanitation": ("hh", "sanitation_improved", "%", +1, None, "Households using a flush toilet to sewer / septic tank / pit / unknown place, or a pit latrine with slab / VIP / composting toilet (JMP definition; sharing is not considered)."),
    "Open defecation": ("hh", "open_defecation", "%", -1, None, "Households with no toilet facility (bush / field)."),
    "Handwashing water available": ("hh", "handwash_water", "%", +1, None, "Households where water is available at the place for handwashing (among households observed)."),
    "Electricity": ("hh", "electricity", "%", +1, None, "Households with electricity (grid or off-grid)."),
    "Clean cooking fuel / stove": ("hh", "clean_fuel", "%", +1, None, "Households cooking mainly with natural gas, LPG, biogas, electricity or solar."),
    "Crowded sleeping rooms": ("hh", "crowded", "%", -1, None, "Households with more than 3 members per sleeping room."),
    "Female-headed households": ("hh", "female_head", "%", 0, None, "Households headed by a woman."),
    "Contraceptive use": ("women", "contraception", "%", +1, None, "Women 15-49 (currently married where known) using a method to avoid pregnancy."),
    "Skilled birth attendant": ("women", "skilled_birth", "%", +1, None, "Women with a birth in the last two years assisted by a doctor, nurse / midwife, LHV or community midwife."),
    "Facility delivery": ("women", "facility_birth", "%", +1, None, "Last births (last two years) that took place in a public or private health facility."),
    "Caesarean section": ("women", "caesarean", "%", 0, None, "Last births (last two years) by caesarean section."),
    "Antenatal care by skilled provider": ("women", "anc_skilled", "%", +1, None, "Women with a recent birth who saw a doctor, nurse / midwife or LHV during pregnancy."),
    "Four or more antenatal visits": ("women", "anc_4plus", "%", +1, None, "Women with a recent birth who had 4+ antenatal visits (among those who gave a number of visits)."),
    "Tetanus injection in last pregnancy": ("women", "tetanus_preg", "%", +1, None, "Women with a recent birth who received a tetanus toxoid injection during the last pregnancy."),
    "Women: wife beating justified": ("women", "wife_beating_any", "%", -1, None, "Women who think a husband is justified in beating his wife for at least one of five reasons."),
    "Men: wife beating justified": ("men", "wife_beating_any", "%", -1, None, "Men who think a husband is justified in beating his wife for at least one of five reasons."),
    "Women ever attended school": ("women", "ever_school", "%", +1, None, "Women 15-49 who ever attended school."),
    "Men ever attended school": ("men", "ever_school", "%", +1, None, "Men 15-49 who ever attended school."),
    "Stunting (height-for-age < -2 SD)": ("children", "stunted", "%", -1, None, "Children under 5 with height-for-age z-score below -2 (WHO standards)."),
    "Severe stunting (< -3 SD)": ("children", "severely_stunted", "%", -1, None, "Children under 5 with height-for-age z-score below -3."),
    "Wasting (weight-for-height < -2 SD)": ("children", "wasted", "%", -1, None, "Children under 5 with weight-for-height z-score below -2."),
    "Underweight (weight-for-age < -2 SD)": ("children", "underweight", "%", -1, None, "Children under 5 with weight-for-age z-score below -2."),
    "BCG: at least one dose (12-35 months)": ("children", "vacc_BCG", "%", +1, imm, "Children aged 12-35 months who received BCG (vaccination card or mother's report). Counts any dose, so this is higher than the official full-course coverage."),
    "Polio: at least one dose (12-35 months)": ("children", "vacc_Polio", "%", +1, imm, "Children aged 12-35 months who received polio vaccine (any dose, card or mother's report; includes campaign doses). Counts any dose, so this is higher than the official full-course coverage."),
    "Penta / DPT: at least one dose (12-35 months)": ("children", "vacc_Penta/DPT", "%", +1, imm, "Children aged 12-35 months who received at least one Penta / DPT dose. Counts any dose, so this is higher than the official full-course coverage."),
    "Measles: at least one dose (12-35 months)": ("children", "vacc_Measles", "%", +1, imm, "Children aged 12-35 months who received a measles-containing vaccine. Counts any dose, so this is higher than the official full-course coverage."),
    "Early childhood education (36-59 months)": ("children", "ece", "%", +1, u3to5, "Children aged 36-59 months attending an early childhood education programme."),
    "Neonatal deaths per 1,000 births": ("births", "died_neonatal", "per 1,000", -1, births0_9, "Births in the 10 years before the survey that died in the first month (crude, not adjusted)."),
    "Infant deaths per 1,000 births": ("births", "died_infant", "per 1,000", -1, births0_9, "Births in the 10 years before the survey that died before age 1 (crude)."),
    "Under-5 deaths per 1,000 births (births 5-9 years ago)": ("births", "died_u5", "per 1,000", -1, births5_9, "Births 5-9 years before the survey that died before age 5 (full exposure, crude)."),
    "Siblings who died": ("siblings", "dead", "%", -1, None, "Siblings listed by women 15-49 who have died."),
    "Children 5-17 ever attended school": ("c5to17", "ever_school", "%", +1, None, "Children 5-17 who ever attended school or an early childhood programme."),
    "Children 5-17 attending school now": ("c5to17", "attending", "%", +1, None, "Children 5-17 attending school or an early childhood programme in the current school year, out of all children 5-17 (children who never attended count as not attending)."),
    "Children 5-17 doing paid / income work": ("c5to17", "works_income", "%", -1, None, "Children 5-17 who did an activity for income in the past week."),
    "Children 5-17 doing household chores": ("c5to17", "chores", "%", 0, None, "Children 5-17 who did at least one household chore in the past week."),
    "Children 5-17 with functional difficulty": ("c5to17", "func_difficulty", "%", -1, None, "Children 5-17 with 'a lot of difficulty' or 'cannot do' in at least one domain."),
    "Television": ("hh", "has_tv", "%", +1, None, "Households that own a television."),
    "Refrigerator": ("hh", "has_fridge", "%", +1, None, "Households that own a refrigerator / freezer."),
    "Mobile phone in household": ("hh", "has_mobile", "%", +1, None, "Households where at least one member owns a mobile phone (not asked in Punjab 2011)."),
    "Motorcycle / scooter": ("hh", "has_motorbike", "%", +1, None, "Households that own a motorcycle or scooter."),
    "Bank account in household": ("hh", "has_bank", "%", +1, None, "Households where at least one member has an account in a bank, post office or national savings centre (not asked in Balochistan 2010, Punjab 2011)."),
    "Rented dwelling": ("hh", "rents_home", "%", 0, None, "Households that rent their dwelling (the others own it or live in it free of rent)."),
    "Diarrhoea in last 2 weeks": ("children", "diarrhoea", "%", -1, None, "Children under 5 who had diarrhoea in the two weeks before the interview."),
    "Fever in last 2 weeks": ("children", "fever", "%", -1, None, "Children under 5 who had a fever in the two weeks before the interview (not asked in Punjab 2011)."),
    "ORS given (children with diarrhoea)": ("children", "ors", "%", +1, None, "Among children with diarrhoea in the last 2 weeks, the share who drank oral rehydration salts (ORS packet or fluid)."),
    "Vitamin A in last 6 months": ("children", "vitamin_a", "%", +1, None, "Children under 5 who received a vitamin A dose in the last 6 months (not asked in Balochistan 2010; Sindh 2014 asked about the last 12 months, so it is left out)."),
    "Nets slept under last night": ("nets", "slept", "%", +1, None, "Nets that someone slept under the night before the survey (among nets listed in the household; Balochistan and Sindh only)."),
    "Mosquito nets observed": ("nets", "observed", "%", +1, None, "Nets seen by the interviewer (among nets listed in the household)."),
}

MAP_INDICATORS = [k for k in IND if IND[k][0] in ("hh", "women", "children", "births")]


def ind_scale(unit):
    return 1000.0 if unit == "per 1,000" else 100.0


def ind_data(key, sex=True):
    table, col, unit, pol, where, desc = IND[key][0], IND[key][1], IND[key][2], IND[key][3], IND[key][4], IND[key][5]
    df = apply(load(table), table, sex=sex)
    return df, col, unit, pol, where, desc


def ind_rate(key, by, **kw):
    df, col, unit, pol, where, desc = ind_data(key)
    if df is None:
        return pd.DataFrame()
    need = [by] if isinstance(by, str) else list(by)
    if any(b not in df.columns for b in need):
        return pd.DataFrame()
    return rate(df, col, by, scale=ind_scale(unit), where=where, **kw)


def ind_dims(key):
    """which grouping columns exist for this indicator's table"""
    t = IND[key][0]
    df = load(t)
    return [] if df is None else [c for c in ("Province", "Survey", "Area", "Wealth", "Sex") if c in df.columns]


def safe_dim(keys, dim="compare"):
    """the compare-by dimension if every indicator's table has it, else Province"""
    keys = [keys] if isinstance(keys, str) else keys
    d = get_filters()["compare"] if dim == "compare" else dim
    return d if all(d in ind_dims(k) for k in keys) else "Province"


def fmt(v, unit="%", d=1):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    return f"{v:,.{d}f}%" if unit == "%" else f"{v:,.0f}" if unit == "per 1,000" else f"{v:,.{d}f}"


# ----------------------------------------------------------------------------- layout helpers
PAGE_EMOJI = {"Overview": "📋", "Households": "🏠", "Water": "💧", "Wealth": "⚖️", "Maternal": "🤰", "Child immunisation": "💉",
              "Child nutrition": "🍼", "Child mortality": "🩺", "Education": "🎓", "Compare & data": "🔎", "Compare two": "🆚", "Inequality": "📊", "Assets": "📱", "Child illness": "🤒", "Fertility": "👨‍👩‍👧"}
KPI_EMOJI = [("water", "💧"), ("sanitation", "🚽"), ("electric", "💡"), ("stunt", "📏"), ("wast", "⚖️"), ("underweight", "⚖️"), ("birth", "🤱"),
             ("vaccin", "💉"), ("dose", "💉"), ("measles", "💉"), ("immunis", "💉"), ("antenatal", "🩺"), ("household", "🏠"), ("women", "👩"), ("men ", "👨"),
             ("children", "👶"), ("survey", "🗂️"), ("mortality", "🩺"), ("school", "🎓"), ("educat", "🎓"), ("fuel", "🔥"), ("hand", "🧼"), ("television", "📺"), ("refrigerator", "🧊"), ("mobile", "📱"), ("motorcycle", "🏍️"), ("bank", "🏦"), ("rent", "🏘️"), ("diarrh", "💧"),
             ("fever", "🌡️"), ("ors", "🧂"), ("vitamin", "🍊"), ("marri", "💍"), ("fertil", "👨‍👩‍👧")]


def page_header(title, subtitle, icon="", badge=None):
    """navy banner (breadcrumb, title, subtitle, one big number) + a slim bar showing the active filters"""
    F = get_filters()
    surveys = [s for s in (F["surveys"] or all_surveys()) if survey_province(s) in F["provinces"]]
    emoji = next((e for k, e in PAGE_EMOJI.items() if title.startswith(k)), "📊")
    bval, blab = badge if badge else (str(len(surveys)), "surveys selected")
    st.markdown(
        f"<div class='hero'><div><div class='crumb'>🏠 Dashboard / {title}</div><h1>{emoji} {title}</h1><div class='sub'>{subtitle}</div></div>"
        f"<div class='badge'><b>{bval}</b><span>{blab}</span></div></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='filterbar'><b>Active filters</b> &nbsp; Provinces: {', '.join(PSHORT.get(p, p) for p in F['provinces'])} &nbsp;|&nbsp; "
        f"Area: {', '.join(F['areas'])} "
        f"&nbsp;|&nbsp; Wealth: {'all quintiles' if len(F['wealth']) == 5 else ', '.join(F['wealth'])} "
        f"&nbsp;|&nbsp; Districts: {len(F['districts']) or 'all'} &nbsp;|&nbsp; Compare by: <b>{DIM_LABEL.get(F['compare'], F['compare'])}</b> "
        f"&nbsp;|&nbsp; Weights: <b>{'population-weighted Pakistan' if F['pop'] else 'survey sample weights'}</b>"
        f"&nbsp;|&nbsp; Snapshots: <b>{'surveys you picked' if F['surveys'] else 'latest survey of each province'}</b></div>",
        unsafe_allow_html=True)
    (st.iframe if hasattr(st, 'iframe') else __import__('streamlit.components.v1', fromlist=['html']).html)("<button onclick=\"window.parent.print()\" style='float:right;padding:6px 14px;border:1px solid #0B5FA5;background:#fff;color:#0B5FA5;"
             "border-radius:8px;font-weight:600;cursor:pointer'>⬇ Save this page as PDF</button>", **({'height': 50} if hasattr(st, 'iframe') else {'height': 50}))


def takeaway(text):
    st.markdown(f"<div class='takeaway'>📌 <b>Key takeaway:</b> {text}</div>", unsafe_allow_html=True)


def no_data(msg="No data for the current filters. Widen the filters in the sidebar."):
    st.info(msg, icon=":material/filter_alt_off:")


def kpi(label, value, unit="%", delta=None, polarity=0, help=None, n=None, d=1):
    """one KPI card (value + optional change)"""
    shown = fmt(value, unit, d) if not isinstance(value, str) else value
    if unit == "per 1,000" and not isinstance(value, str) and shown != "n/a":
        shown += " per 1,000"
    dtxt = None
    dcol = "off"
    if delta is not None and not (isinstance(delta, float) and np.isnan(delta)):
        dtxt = f"{delta:+.1f} {'pp' if unit == '%' else 'per 1,000'}".strip()
        dcol = "off" if polarity == 0 else ("normal" if polarity > 0 else "inverse")
    low = f"{label.lower()} "
    ico = next((e for k, e in KPI_EMOJI if k in low), "📌")
    st.metric(f"{ico} {label}", shown, delta=dtxt, delta_color=dcol, help=help, border=True)


def latest_change(key, df_rate_by_survey):
    """change between the first and the last survey of a single province (pp); None if it can not be computed"""
    if df_rate_by_survey is None or df_rate_by_survey.empty:
        return None
    t = df_rate_by_survey.copy()
    t["prov"] = t["Survey"].astype(str).map(survey_province)
    if t["prov"].nunique() != 1 or len(t) < 2:
        return None
    t["yr"] = t["Survey"].astype(str).str.rsplit(" ", n=1).str[1].astype(int)
    t = t.sort_values("yr")
    return t["value"].iloc[-1] - t["value"].iloc[0]


def overall(key):
    """pooled value for the active filters (and the change over time if one province is selected)"""
    df, col, unit, pol, where, desc = ind_data(key)
    if df is None or df.empty:
        return np.nan, None, 0, unit, pol, desc
    d = df if where is None else df[where(df)]
    d = latest_only(d[d[col].notna()])
    if d.empty:
        return np.nan, None, 0, unit, pol, desc
    val = (d[col].astype(float) * d["w"]).sum() / d["w"].sum() * ind_scale(unit)
    bs = rate(df, col, "Survey", scale=ind_scale(unit), where=where, min_n=1)
    return val, latest_change(key, bs), len(d), unit, pol, desc


def kpi_row(keys, cols=None, labels=None):
    cols = st.columns(cols or len(keys))
    for c, k in zip(cols, keys):
        with c:
            val, delta, n, unit, pol, desc = overall(k)
            kpi((labels or {}).get(k, k), val, unit, delta, pol, help=f"{desc}  (n = {n:,} records)")


def show_table(df, name, label="Show / download the numbers"):
    with st.expander(label):
        st.dataframe(df, **STRETCH, hide_index=True)
        st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8-sig"), file_name=f"{name}.csv", mime="text/csv", key=f"dl_{name}")


def availability_note(rt, what="this indicator"):
    F = get_filters()
    sel = [s for s in (F["surveys"] or all_surveys()) if survey_province(s) in F["provinces"]]
    have = set(rt["Survey"].astype(str)) if "Survey" in rt.columns else set()
    if "Survey" in rt.columns and sel:
        miss = [s for s in survey_order(sel) if s not in have]
        if miss:
            st.caption(f"Not available / too few records for {what} in: {', '.join(miss)}.")


# ----------------------------------------------------------------------------- charts
LAYOUT = dict(template="plotly_white", paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font=dict(family="Inter, Segoe UI, Arial, sans-serif", size=13, color="#1B2733"),
              margin=dict(l=10, r=10, t=60, b=10), hoverlabel=dict(font_size=13),
              legend=dict(orientation="h", yref="container", yanchor="bottom", y=0.01, xanchor="left", x=0, title_text="", font=dict(size=12)),
              title=dict(x=0, xanchor="left", font=dict(size=16)))


def style(fig, height=420, legend_title=None, legend=True, bottom=None):
    fig.update_layout(**LAYOUT)
    fig.update_layout(height=height, uniformtext=dict(minsize=10, mode="hide"))
    if legend_title:
        fig.update_layout(legend_title_text=legend_title + ":")
    fig.update_layout(showlegend=legend)
    fig.update_xaxes(automargin=True)
    fig.update_layout(margin_r=28)
    names = [str(t.name) for t in fig.data if getattr(t, "name", None) and t.showlegend is not False]
    need = 20
    if legend:
        width = 440                                           # a half-width chart is about this wide
        rows = max(1, int(np.ceil(sum(len(n) * 8.2 + 56 for n in names) / width))) if names else 1
        need = 70 + 22 * rows + (22 if legend_title else 0)   # x tick labels + legend rows
        if rows > 3:                                          # many legend entries: grow the chart so the plot area keeps its size
            fig.update_layout(height=height + 22 * (rows - 3))
    fig.update_layout(margin=dict(l=10, r=28, t=60, b=max(bottom or 0, need) if legend else (bottom if bottom is not None else 20)))
    fig.update_xaxes(automargin=True, showgrid=False)
    fig.update_yaxes(automargin=True, gridcolor="#E3E9F0", linecolor="#9FB0C3")
    return fig


TABLE_NOUN = {"hh": "households", "women": "women", "men": "men", "children": "children", "c5to17": "children",
              "births": "births", "siblings": "siblings", "nets": "household members"}


def pct_axis(keys):
    """'% of children' when every indicator is about the same kind of record, otherwise '% of records'"""
    nouns = {TABLE_NOUN.get(IND[k][0], "records") for k in keys if k in IND}
    return f"% of {nouns.pop()}" if len(nouns) == 1 else "% of records"


def unit_axis(unit):
    return "% of records" if unit == "%" else ("deaths per 1,000 births" if unit == "per 1,000" else unit)


CROWDED = 16          # more bars than this in one grouped chart -> no value labels on the bars (hover still shows them)


def _short_axis(fig, by, orient="v"):
    """long province names (Khyber Pakhtunkhwa, Gilgit-Baltistan) overlap on a category axis: show KP / GB instead"""
    if by != "Province":
        return
    ax = fig.update_yaxes if orient == "h" else fig.update_xaxes
    vals = [p for p in PROV_ORDER]
    ax(tickmode="array", tickvals=vals, ticktext=[PSHORT.get(p, p) for p in vals], tickangle=0)


def bar_chart(rt, by, title, unit="%", color=None, height=420, orient="v", sort=True, ci=None, ytitle=None, key=None):
    """grouped / simple bar chart of rates. by = x category, color = optional second dimension"""
    if rt is None or rt.empty:
        no_data()
        return
    ci = get_filters()["show_ci"] if ci is None else ci
    d = rt.copy()
    d[by] = d[by].astype(str)
    cdim = color or by
    if color:
        d[color] = d[color].astype(str)
    xorder = cat_order(by, d[by])
    if sort and not color and by in ("Survey", "Province", "District", "Method", "AgeGroup") and by not in ("AgeGroup",):
        xorder = list(d.sort_values("value", ascending=False)[by])
    cmap = color_map(cdim, d[cdim])
    d["label"] = d["value"].map(lambda v: (f"{v:.0f}{'%' if unit == '%' else ''}" if unit in ("%", "per 1,000") else f"{v:.1f}") if color else fmt(v, unit, 1))
    kw = dict(x=by, y="value", color=cdim, color_discrete_map=cmap, text="label", barmode=("group" if color else "relative"),
              category_orders={by: xorder, cdim: cat_order(cdim, d[cdim])},
              labels={by: DIM_LABEL.get(by, by), cdim: DIM_LABEL.get(cdim, cdim), "value": ytitle or unit_axis(unit)},
              hover_data={"n": ":,", "label": False})
    if ci:
        d["err_plus"] = d["hi"] - d["value"]
        d["err_minus"] = d["value"] - d["lo"]
        kw.update(error_y="err_plus", error_y_minus="err_minus")
    if orient == "h":
        kw.update(x="value", y=by, orientation="h", labels=kw["labels"], category_orders={by: xorder[::-1], cdim: cat_order(cdim, d[cdim])})
        if ci:
            kw.pop("error_y"), kw.pop("error_y_minus")
            kw.update(error_x="err_plus", error_x_minus="err_minus")
    fig = px.bar(d, title=title, **kw)
    fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=11, opacity=1)
    if color and len(d) > CROWDED:                    # too many bars side by side: value labels would collide, keep them in the hover
        fig.update_traces(text=None, texttemplate=None)
    _short_axis(fig, by, orient)
    if orient == "h":
        fig.update_xaxes(range=[0, max(d["value"].max() * 1.18, 1)], title=ytitle or unit_axis(unit))
    else:
        fig.update_yaxes(range=[0, max(d["hi"].max() if ci else d["value"].max(), 1) * 1.18], title=ytitle or unit_axis(unit))
        fig.update_xaxes(tickangle=-30 if by in ("Survey", "District") else 0)
    show_leg = bool(color)
    style(fig, height, legend_title=DIM_LABEL.get(cdim, cdim), legend=show_leg, bottom=None if show_leg else 20)
    if orient == "h":
        fig.update_yaxes(title=None)
    else:
        fig.update_xaxes(title=None, tickangle=0 if by == "Province" else (-30 if (d[by].nunique() > 4 or by in ("Survey", "District")) else 0))
    show(fig, key=key)


def trend_chart(rt, title, unit="%", height=500, ytitle=None, key=None, color="Province"):
    """one line per province across survey years (every marker is one survey)"""
    if rt is None or rt.empty:
        no_data()
        return
    d = rt.copy()
    d["Province"] = d["Survey"].astype(str).map(survey_province)
    d["Year"] = d["Survey"].astype(str).str.rsplit(" ", n=1).str[1].astype(int)
    d = d.sort_values(["Province", "Year"])
    d["label"] = d["value"].map(lambda v: fmt(v, unit, 1))
    ymax_ = max(d["value"].max(), 1)
    fig = px.line(d, x="Year", y="value", color="Province", markers=True, text="label", color_discrete_map=PROV_COLORS,
                  category_orders={"Province": cat_order("Province", d["Province"])}, title=title,
                  labels={"value": ytitle or unit_axis(unit), "Year": "Survey year"}, hover_data={"n": ":,", "Survey": True, "label": False})
    # every label sits ABOVE its point when it can; where labels would collide it moves below / to the side (greedy, no overlaps)
    pts = [(ti, pi, float(x), float(y)) for ti, tr in enumerate(fig.data) for pi, (x, y) in enumerate(zip(tr.x, tr.y))]
    yrs_ = sorted(d["Year"].unique())
    xspan = (max(yrs_) - min(yrs_)) + 1.6
    wu = 48.0 / (430.0 / xspan)                      # label width in "years" (about 40 px)
    hu = 20.0 / max(150.0, height - 230.0) * ymax_ * 1.22                 # label height in value units (about 17 px)
    gap = 0.035 * ymax_
    def box(x, y, pos):
        v = (y + gap, y + gap + hu) if pos.startswith("top") else (y - gap - hu, y - gap)
        h = (x - wu / 2, x + wu / 2) if pos.endswith("center") else (x, x + wu) if pos.endswith("right") else (x - wu, x)
        return h[0], v[0], h[1], v[1]
    def hit(a, c):
        return a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]
    samples = []                                      # points along every line, so a label avoids sitting on a line
    for ti, tr in enumerate(fig.data):
        xs, ys = [float(v) for v in tr.x], [float(v) for v in tr.y]
        for (x0, y0), (x1, y1) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
            for f_ in np.linspace(0, 1, max(2, int((x1 - x0) / 0.2))):
                samples.append((ti, x0 + (x1 - x0) * f_, y0 + (y1 - y0) * f_))
    placed, pos, hide = [], {}, set()
    markers = {(ti, pi): (x - 0.12, y - 0.03 * ymax_, x + 0.12, y + 0.03 * ymax_) for ti, pi, x, y in pts}
    for ti, pi, x, y in sorted(pts, key=lambda t: (-t[3], t[2])):
        best, best_cost = None, 1e9
        for cand in ("top center", "bottom center", "top right", "bottom right", "top left", "bottom left"):
            bx = box(x, y, cand)
            cost = (sum(3 for o in placed if hit(bx, o)) + sum(3 for k_, m in markers.items() if k_ != (ti, pi) and hit(bx, m))
                    + sum(1 for tj, sx, sy in samples if bx[0] < sx < bx[2] and bx[1] < sy < bx[3] and not (tj == ti and abs(sx - x) < 0.45)))
            if cost < best_cost:
                best, best_cost = cand, cost
            if cost == 0:
                break
        pos[(ti, pi)] = best or "top center"
        if best_cost >= 3 and any(hit(box(x, y, best), o) for o in placed):   # no free spot: leave the label to the hover tooltip instead of overlapping
            hide.add((ti, pi))
        placed.append(box(x, y, pos[(ti, pi)]))
    fig.update_traces(line_width=3, marker_size=9, textfont_size=12, cliponaxis=False)
    for ti, tr in enumerate(fig.data):
        tr.textposition = [pos[(ti, pi)] for pi in range(len(tr.x))]
        last = len(tr.x) - 1                          # only the latest survey of each province gets a label; the rest are in the hover
        tr.text = ["" if ((ti, pi) in hide or pi != last) else t_ for pi, t_ in enumerate(tr.text)]
    yrs = sorted(d["Year"].unique())
    fig.update_xaxes(tickmode="array", tickvals=yrs, ticktext=[(str(y) if i == 0 else "'" + str(y)[2:]) for i, y in enumerate(yrs)],
                     range=[min(yrs) - 0.8, max(yrs) + 0.8], tickangle=0, tickfont_size=11)   # 2010, '11, '14 ... fits without overlapping
    ytop = max(d["value"].max(), 1) * 1.22
    if unit == "%":                                   # a percentage axis should not run far past 100
        ytop = min(ytop, 112)
        fig.update_yaxes(tickvals=[0, 20, 40, 60, 80, 100])
    fig.update_yaxes(range=[0, ytop])
    style(fig, height, legend_title="Province")
    show(fig, key=key)


def dist_chart(dd, cat, by, title, cmap=None, order=None, height=430, key=None, cat_label=None):
    """100% stacked horizontal bars: share of each category inside each group"""
    if dd is None or dd.empty:
        no_data()
        return
    d = dd.copy()
    d[by] = d[by].astype(str)
    d[cat] = d[cat].astype(str)
    d["txt"] = d["pct"].map(lambda v: f"{v:.0f}%" if v >= 5 else "")
    order = order or sorted(d[cat].unique())
    cmap = cmap or {c: CAT_COLORS[i % len(CAT_COLORS)] for i, c in enumerate(order)}
    fig = px.bar(d, y=by, x="pct", color=cat, orientation="h", text="txt", color_discrete_map=cmap,
                 category_orders={cat: order, by: cat_order(by, d[by])[::-1]}, title=title,
                 labels={"pct": "% of records in the group", by: DIM_LABEL.get(by, by), cat: cat_label or cat}, hover_data={"txt": False, "n_group": ":,"})
    fig.update_traces(textposition="inside", insidetextanchor="middle", textfont=dict(size=11, color="white"))
    fig.update_xaxes(range=[0, 100], title="% of records in the group")
    style(fig, height, legend_title=cat_label or cat, bottom=150)
    fig.update_yaxes(title=None)
    show(fig, key=key)


def heatmap(pivot, title, unit="%", height=460, key=None, colorscale="RdYlGn", reverse=False, xlabel="", ylabel="", digits=1, zcolor=None, cbar_title=None):
    """zcolor (optional, same shape as pivot) sets the cell colour while the text still shows the real values"""
    if pivot is None or pivot.empty:
        no_data()
        return
    z = pivot.values.astype(float)
    text = np.where(np.isnan(z), "not asked", np.vectorize(lambda v: fmt(v, unit, digits) if not np.isnan(v) else "")(z))
    cz = z if zcolor is None else np.asarray(zcolor, dtype=float)
    cbar = dict(title=dict(text=cbar_title or unit_axis(unit), side="right"), thickness=14)
    if zcolor is not None:
        cbar.update(tickvals=[0, 1], ticktext=["worse", "better"])
    fig = go.Figure(go.Heatmap(z=cz, x=list(pivot.columns), y=list(pivot.index), text=text, texttemplate="%{text}", textfont=dict(size=12),
                               colorscale=colorscale, reversescale=reverse, xgap=2, ygap=2, colorbar=cbar,
                               hovertemplate="%{y}<br>%{x}: %{text}<extra></extra>"))
    fig.update_layout(title=title, xaxis_title=xlabel, yaxis_title=ylabel, yaxis=dict(autorange="reversed"))
    style(fig, height, legend=False, bottom=90)
    fig.update_xaxes(side="bottom", tickangle=-35)
    show(fig, key=key)


def weighted_hist(df, col, title, bins, xlabel, by="Province", height=400, key=None, vline=None):
    d = df[df[col].notna()].copy()
    if d.empty:
        no_data()
        return
    d["bin"] = pd.cut(d[col], bins=bins)
    g = d.groupby([by, "bin"], observed=True)["w"].sum().reset_index()
    g["pct"] = g["w"] / g.groupby(by, observed=True)["w"].transform("sum") * 100
    g["x"] = g["bin"].map(lambda b: (b.left + b.right) / 2).astype(float)
    g[by] = g[by].astype(str)
    cmap = color_map(by, g[by])
    fig = px.line(g.sort_values("x"), x="x", y="pct", color=by, color_discrete_map=cmap, title=title,
                  category_orders={by: cat_order(by, g[by])}, labels={"x": xlabel, "pct": "% of children", by: DIM_LABEL.get(by, by)})
    fig.update_traces(line_width=2.5, line_shape="spline")
    if vline is not None:
        fig.add_vline(x=vline, line_dash="dash", line_color="#444", annotation_text=f"cut-off ({vline})", annotation_position="top")
    style(fig, height, legend_title=DIM_LABEL.get(by, by))
    show(fig, key=key)


# ----------------------------------------------------------------------------- map
COORDS = {"Punjab": (31.2, 72.6), "Sindh": (26.0, 68.7), "Khyber Pakhtunkhwa": (34.3, 72.0), "Balochistan": (28.4, 65.4),
          "Gilgit-Baltistan": (36.2, 74.6)}


@st.cache_resource
def _geojson():
    import json
    p = Path(__file__).resolve().parent / "pakistan_provinces.geojson"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def province_map(key_ind, scope="Latest survey of each province", height=560, key=None):
    """filled province map (no internet / map tiles needed): colour = indicator value, grey = no survey in the selection"""
    gj = _geojson()
    df, col, unit, pol, where, desc = ind_data(key_ind)
    if df is None or df.empty:
        no_data()
        return None
    rt = rate(df, col, "Survey", scale=ind_scale(unit), where=where, min_n=1)
    if rt.empty:
        no_data("This indicator is not available for the selected provinces / surveys.")
        return None
    rt["Province"] = rt["Survey"].astype(str).map(survey_province)
    rt["Year"] = rt["Survey"].astype(str).str.rsplit(" ", n=1).str[1].astype(int)
    rt = rt.sort_values("Year")
    rt = rt.groupby("Province").tail(1) if scope.startswith("Latest") else rt.groupby("Province").head(1)
    info = {r.Province: r for r in rt.itertuples()}
    if gj is None:
        no_data("pakistan_provinces.geojson is missing next to app.py.")
        return rt[["Province", "Survey", "value", "n"]]
    ids = [f["properties"]["id"] for f in gj["features"]]
    src = {i: ("Khyber Pakhtunkhwa" if i == "FATA" else i) for i in ids}
    has = [i for i in ids if src[i] in info]
    none = [i for i in ids if src[i] not in info]
    z = [info[src[i]].value for i in has]
    txt = [f"<b>{src[i]}</b><br>{info[src[i]].Survey}<br>{fmt(info[src[i]].value, unit, 1)}<br>n = {info[src[i]].n:,}" for i in has]
    scale = "RdYlGn" if pol > 0 else "RdYlGn_r" if pol < 0 else "Blues"
    lo, hi = min(z), max(z)
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    from plotly.colors import sample_colorscale
    fig = go.Figure()

    def ring_xy(geom):
        rings = geom["coordinates"] if geom["type"] == "Polygon" else [r for poly in geom["coordinates"] for r in poly]
        xs, ys = [], []
        for ring in rings:
            xs += [p[0] for p in ring] + [None]
            ys += [p[1] for p in ring] + [None]
        return xs, ys

    for f in gj["features"]:
        pid = f["properties"]["id"]
        xs, ys = ring_xy(f["geometry"])
        if pid in has:
            r = info[src[pid]]
            t = (r.value - lo) / (hi - lo)
            colr = sample_colorscale(scale, [min(max(t, 0), 1)])[0]
            hv = f"<b>{src[pid]}</b><br>{r.Survey}<br>{fmt(r.value, unit, 1)}<br>n = {r.n:,}"
        else:
            colr = "#D5DBE1"
            hv = f"<b>{pid}</b><br>no survey in the selection"
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=colr, line=dict(color="white", width=1.6), hoveron="fills",
                                 text=hv, hoverinfo="text", showlegend=False))
    labs = [p for p in info]
    def _txt(p):
        t = (info[p].value - lo) / (hi - lo)
        c = sample_colorscale(scale, [min(max(t, 0), 1)])[0]
        rgb = [int(v) for v in c.strip("rgb()").split(",")]
        return "#FFFFFF" if (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) < 140 else "#111111"
    fig.add_trace(go.Scatter(x=[COORDS[p][1] for p in labs], y=[COORDS[p][0] for p in labs], mode="text",
                             text=[f"<b>{PSHORT.get(p, p)}</b><br>{fmt(info[p].value, unit, 1)}" for p in labs],
                             textfont=dict(size=13, color=[_txt(p) for p in labs]), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers", hoverinfo="skip", showlegend=False,
                             marker=dict(size=1, color=[lo], colorscale=scale, cmin=lo, cmax=hi, showscale=True,
                                         colorbar=dict(title=dict(text=("% of records" if unit == "%" else unit), side="right"), thickness=16, len=0.75))))
    fig.update_layout(title=f"{key_ind} - {scope.lower()}")
    style(fig, height, legend=False, bottom=10)
    fig.update_xaxes(visible=False, range=[60.3, 77.8], showgrid=False, zeroline=False, fixedrange=True)
    fig.update_yaxes(visible=False, range=[23.2, 37.4], showgrid=False, zeroline=False, scaleanchor="x", scaleratio=1.16, fixedrange=True)
    show(fig, key=key)
    st.caption("Province colour = indicator value for the survey shown (see colour bar; green = better, red = worse where that is clear). Grey = no survey in the selection "
               "(Azad Kashmir and Islamabad were not surveyed; FATA is shown with the Khyber Pakhtunkhwa value). Hover for the survey year and sample size.")
    return rt[["Province", "Survey", "value", "n"]]


def multi_bar(keys, by, title, height=450, key=None, labels=None):
    """several indicators side by side (x) split by one group (colour)"""
    parts = []
    for k in keys:
        r = ind_rate(k, by)
        if r is not None and not r.empty:
            r = r.copy()
            r["Indicator"] = (labels or {}).get(k, k)
            parts.append(r)
    if not parts:
        no_data()
        return None
    d = pd.concat(parts)
    d[by] = d[by].astype(str)
    unit = IND[keys[0]][2]
    d["label"] = d["value"].map(lambda v: f"{v:.0f}{'%' if unit == '%' else ''}")
    ind_order = [(labels or {}).get(k, k) for k in keys]
    fig = px.bar(d, x="Indicator", y="value", color=by, barmode="group", text="label", color_discrete_map=color_map(by, d[by]),
                 category_orders={by: cat_order(by, d[by]), "Indicator": ind_order}, title=title,
                 labels={"value": unit_axis(unit), by: DIM_LABEL.get(by, by)}, hover_data={"n": ":,", "label": False})
    fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=11)
    if len(d) > CROWDED:                              # many groups x many indicators: labels would overlap
        fig.update_traces(text=None, texttemplate=None)
    fig.update_yaxes(range=[0, max(d["value"].max(), 1) * 1.18], title=unit_axis(unit))
    fig.update_xaxes(title="", tickangle=0)
    style(fig, height, legend_title=DIM_LABEL.get(by, by))
    show(fig, key=key)
    return d


def line_chart(rt, x, color, title, unit="%", height=420, key=None, xorder=None, ytitle=None):
    """lines across an ordered category (e.g. age group) - one line per group"""
    if rt is None or rt.empty:
        no_data()
        return
    d = rt.copy()
    d[x] = d[x].astype(str)
    d[color] = d[color].astype(str)
    d["label"] = d["value"].map(lambda v: fmt(v, unit, 0))
    xo = xorder or cat_order(x, d[x])
    d["_xo"] = d[x].map({v: i for i, v in enumerate(xo)}).fillna(len(xo))
    d = d.sort_values([color, "_xo"])                 # lines must join points in the category order, not alphabetically
    fig = px.line(d, x=x, y="value", color=color, markers=True, color_discrete_map=color_map(color, d[color]),
                  category_orders={x: xo, color: cat_order(color, d[color])}, title=title,
                  labels={"value": ytitle or unit_axis(unit), x: DIM_LABEL.get(x, x), color: DIM_LABEL.get(color, color)},
                  hover_data={"n": ":,", "label": False})
    fig.update_traces(line_width=2.8, marker_size=8)
    fig.update_yaxes(range=[0, max(d["value"].max(), 1) * 1.15])
    style(fig, height, legend_title=DIM_LABEL.get(color, color))
    show(fig, key=key)


def gap_chart(rt_a, rt_b, name_a, name_b, title, unit="%", polarity=0, key=None, height=420):
    """difference (b minus a) per survey as a bar: colour tells whether the gap is favourable"""
    if rt_a is None or rt_b is None or rt_a.empty or rt_b.empty:
        no_data("Not enough data to compute the gap for these filters.")
        return None
    m = rt_a[["Survey", "value", "n"]].merge(rt_b[["Survey", "value", "n"]], on="Survey", suffixes=("_a", "_b"))
    if m.empty:
        no_data("Not enough data to compute the gap for these filters.")
        return None
    m["gap"] = m["value_b"] - m["value_a"]
    fav = m["gap"] * (polarity if polarity else 1)
    m["Direction"] = np.where(polarity == 0, "Difference", np.where(fav >= 0, "Favours " + name_b, "Favours " + name_a))
    # a gap is an inequality, so it is never painted "good" green: one colour per direction, the bar length shows the size
    cmap = {"Difference": NEUTRAL, f"Favours {name_b}": "#0B5FA5", f"Favours {name_a}": "#E8A317"}
    gu = "percentage points" if unit == "%" else ("deaths per 1,000 births" if unit == "per 1,000" else unit)
    gs = "pp" if unit == "%" else ("per 1,000" if unit == "per 1,000" else unit)
    m["label"] = m["gap"].map(lambda v: f"{v:+.1f}")
    m["Survey"] = m["Survey"].astype(str)
    fig = px.bar(m, x="Survey", y="gap", color="Direction", color_discrete_map=cmap, text="label", title=title,
                 category_orders={"Survey": survey_order(m["Survey"])}, labels={"gap": f"{name_b} minus {name_a} ({gu})"},
                 hover_data={"value_a": ":.1f", "value_b": ":.1f", "label": False})
    fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=11)
    fig.add_hline(y=0, line_color="#444")
    ymax = max(abs(m["gap"]).max(), 1) * 1.3
    fig.update_yaxes(range=[-ymax, ymax] if (m["gap"] < 0).any() else [0, ymax], title=f"{name_b} minus {name_a} ({gs})")
    fig.update_xaxes(tickangle=-30, title="")
    style(fig, height, legend_title="Colour")
    show(fig, key=key)
    return m


# ----------------------------------------------------------------------------- two-group comparison and inequality
def group_rate(key, crit):
    """weighted value + standard error for one group defined by crit = {surveys, areas, wealth, sexes} (sidebar filters are NOT used)"""
    table, col, unit, pol, where, desc = IND[key]
    df = load(table)
    if df is None or col not in df.columns:
        return None
    m = pd.Series(True, index=df.index)
    if crit.get("surveys"):
        m &= df["Survey"].isin(crit["surveys"])
    if crit.get("areas") and len(crit["areas"]) < 2:
        m &= df["Area"].isin(crit["areas"])
    if crit.get("wealth") and len(crit["wealth"]) < 5:
        m &= df["Wealth"].isin(crit["wealth"])
    if crit.get("sexes") and "Sex" in df.columns and len(crit["sexes"]) < 2:
        m &= df["Sex"].isin(crit["sexes"])
    d = df[m]
    if where is not None:
        d = d[where(d)]
    d = d[d[col].notna()]
    if len(d) < 30:
        return None
    w = d["w"].to_numpy()
    x = d[col].astype(float).to_numpy()
    p = (w * x).sum() / w.sum()
    neff = w.sum() ** 2 / (w ** 2).sum()
    sc = ind_scale(unit)
    se = np.sqrt(p * (1 - p) / neff)
    return dict(value=p * sc, se=se * sc, n=len(d), lo=max(p - 1.96 * se, 0) * sc, hi=min(p + 1.96 * se, 1) * sc)


def p_two_sided(z):
    import math
    return math.erfc(abs(z) / math.sqrt(2))


def inequality(key):
    """slope index (SII), relative index (RII) and concentration index per survey, using the wealth quintiles"""
    df, col, unit, pol, where, desc = ind_data(key)
    if df is None or df.empty:
        return pd.DataFrame()
    d = df if where is None else df[where(df)]
    d = d[d[col].notna() & d["Wealth"].notna()]
    rows = []
    for sv, g in d.groupby("Survey", observed=True):
        t = g.assign(_x=g[col].astype(float) * g["w"]).groupby("Wealth", observed=True).agg(sx=("_x", "sum"), sw=("w", "sum"), n=("w", "size"))
        t = t.reindex([w for w in WEALTH if w in t.index])
        if len(t) < 5 or (t["n"] < 20).any():
            continue
        t["p"] = t["sx"] / t["sw"]
        t["s"] = t["sw"] / t["sw"].sum()
        t["r"] = t["s"].cumsum() - t["s"] / 2
        rbar = (t["s"] * t["r"]).sum()
        pbar = (t["s"] * t["p"]).sum()
        var = (t["s"] * (t["r"] - rbar) ** 2).sum()
        b = (t["s"] * (t["r"] - rbar) * (t["p"] - pbar)).sum() / var
        a = pbar - b * rbar
        hi_, lo_ = a + b, a
        rows.append(dict(Survey=str(sv), SII=b * ind_scale(unit), RII=(hi_ / lo_ if lo_ > 0 else np.nan),
                         CI=2 * (t["s"] * t["p"] * t["r"]).sum() / pbar - 1 if pbar > 0 else np.nan, n=int(t["n"].sum()),
                         poorest=t["p"].iloc[0] * ind_scale(unit), richest=t["p"].iloc[-1] * ind_scale(unit)))
    return pd.DataFrame(rows)
