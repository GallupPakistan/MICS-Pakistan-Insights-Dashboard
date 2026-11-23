import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

import common as C

AGES = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49"]
MARR_BANDS = ["Under 15", "15-17", "18-19", "20-24", "25 and over"]
MARR_COL = {"Under 15": "#B3261E", "15-17": "#E8A317", "18-19": "#9CCC65", "20-24": "#2E9E6B", "25 and over": "#0B5FA5"}


def _mean(d, col):
    d = d[d[col].notna() & d["w"].notna()]
    return float((d[col] * d["w"]).sum() / d["w"].sum()) if len(d) and d["w"].sum() else np.nan


def render():
    C.page_header("Fertility & marriage", "How many children women have had, and how early they married", ":material/family_restroom:")
    w = C.apply(C.load("women"), "women")
    if w is None or w.empty or "children_born" not in w.columns:
        C.no_data()
        return
    old = w[w["Age"] >= 45]
    mar = w[(w["Age"] >= 25) & w["marr_age"].notna()].copy()
    mar["early"] = (mar["marr_age"] < 18).astype(float)
    k = st.columns(4)
    with k[0]:
        C.kpi("Children ever born per woman", f"{_mean(w, 'children_born'):.1f}", help="Average number of live births per woman aged 15-49 (all women, weighted).")
    with k[1]:
        C.kpi("Completed fertility (women 45-49)", f"{_mean(old, 'children_born'):.1f}", help="Average number of children born to women aged 45-49, who have almost finished childbearing.")
    with k[2]:
        C.kpi("Age at first marriage (women 25-49)", f"{_mean(mar, 'marr_age'):.1f} years" if len(mar) else "n/a",
              help="Average age at first marriage among ever-married women aged 25-49 (asked in 8 of 10 surveys).")
    with k[3]:
        C.kpi("Married before 18 (women 25-49)", f"{_mean(mar, 'early') * 100:.0f}%" if len(mar) else "n/a", help="Ever-married women aged 25-49 who married before age 18.")
    st.caption("Averages are weighted. Children ever born uses the standard MICS variable (CEB) and marriage age the computed age at first marriage (WAGEM, ever-married women only); both are available for all 10 surveys.")
    by = C.safe_dim(["Contraceptive use"])
    if by not in w.columns:
        by = "Province"

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        r = C.wmean(w, "children_born", [by, "AgeGroup"])
        C.line_chart(r, "AgeGroup", by, "Children ever born, by woman's age", unit="children", ytitle="children per woman", key="fe1", xorder=AGES)
    with b:
        r = C.wmean(w, "children_born", "Education")
        C.bar_chart(r, "Education", "Children ever born, by woman's education (women 15-49)", "children", ytitle="children per woman", key="fe2", ci=False)
    st.caption("Left: the line climbs until about age 35 and then flattens, so the right-hand end is each group's completed family size.")

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        r = C.wmean(old, "children_born", "Survey")
        C.bar_chart(r, "Survey", "Completed fertility by survey (women 45-49)", "children", ytitle="children per woman", key="fe3", ci=False, sort=False)
    with b:
        r = C.wmean(mar, "marr_age", "Education")
        C.bar_chart(r, "Education", "Age at first marriage, by education (women 25-49)", "years", ytitle="years", key="fe4", ci=False)

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        if mar.empty:
            C.no_data()
        else:
            mar["MarrBand"] = pd.cut(mar["marr_age"], bins=[0, 15, 18, 20, 25, 100], labels=MARR_BANDS, right=False).astype("object")
            d = C.dist(mar, "MarrBand", by)
            C.dist_chart(d, "MarrBand", by, "Age at first marriage (women 25-49)", cmap=MARR_COL, order=MARR_BANDS, key="fe5", cat_label="Age at marriage", height=430)
    with b:
        r = C.rate(mar, "early", ["Wealth", by if by != "Wealth" else "Province"])
        C.bar_chart(r, "Wealth", "Married before 18, by wealth quintile (women 25-49)", "%", color=by if by != "Wealth" else "Province", key="fe6", height=430)
    st.caption("Colours on the left run from red (married very young) to blue (25 or older). Surveys without a marriage-age question are left out.")

