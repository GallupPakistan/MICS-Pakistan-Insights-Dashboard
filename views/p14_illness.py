import pandas as pd
import plotly.express as px
import streamlit as st

import common as C

ILL = ["Diarrhoea in last 2 weeks", "Fever in last 2 weeks"]
CARE = ["ORS given (children with diarrhoea)", "Vitamin A in last 6 months"]
SHORT = {"Diarrhoea in last 2 weeks": "Diarrhoea", "Fever in last 2 weeks": "Fever", "ORS given (children with diarrhoea)": "ORS for diarrhoea",
         "Vitamin A in last 6 months": "Vitamin A"}
AGE = ["0-5 m", "6-11 m", "12-23 m", "24-35 m", "36-47 m", "48-59 m"]
CO_COL = {"Diarrhoea only": "#2E7FB8", "Fever only": "#E8A317", "Both": "#D1495B", "Neither": "#B8C4D0"}


def render():
    C.page_header("Child illness & care", "Diarrhoea and fever in children under 5, and whether they got ORS and vitamin A", ":material/sick:")
    k = C.apply(C.load("children"), "children")
    if k is None or k.empty or "diarrhoea" not in k.columns:
        C.no_data()
        return
    C.kpi_row(ILL + CARE, cols=4, labels=SHORT)
    st.caption("Illness is reported by the mother for the two weeks before the interview (lower is better). ORS is counted only among children who had diarrhoea.")
    by = C.safe_dim(ILL + CARE)

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        C.multi_bar(CARE, by, "Care and prevention: ORS and vitamin A", key="il1", labels=SHORT, height=440)
    with b:
        r = C.rate(k, "diarrhoea", [by, "AgeGroup"])
        C.line_chart(r, "AgeGroup", by, "Diarrhoea by child's age", key="il2", xorder=AGE, height=440)
    st.caption("Diarrhoea usually peaks between 6 and 23 months, when babies start eating other foods and crawling.")

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        C.bar_chart(C.ind_rate("ORS given (children with diarrhoea)", ["Wealth", by if by != "Wealth" else "Province"]), "Wealth",
                    "Children with diarrhoea who got ORS, by wealth", "%", color=by if by != "Wealth" else "Province", key="il3")
    with b:
        r = C.rate(k, "vitamin_a", ["MotherEdu", by if by != "MotherEdu" else "Province"])
        C.bar_chart(r, "MotherEdu", "Vitamin A in the last 6 months, by mother's education", "%", color=by if by != "MotherEdu" else "Province", key="il4")
        C.availability_note(C.ind_rate("Vitamin A in last 6 months", "Survey"), "vitamin A")

    st.markdown("---")
    ind = st.selectbox("Indicator to follow over time", ILL + CARE, key="il_ind", format_func=lambda x: SHORT[x])
    a, b = st.columns(2)
    with a:
        r = C.ind_rate(ind, "Survey")
        C.trend_chart(r, f"{SHORT[ind]} over time", "%", key="il5")
        C.availability_note(r, SHORT[ind].lower())
    with b:
        ua = C.ind_rate(ind, ["Survey", "Area"])
        C.bar_chart(ua, "Survey", f"{SHORT[ind]}: urban vs rural", "%", color="Area", key="il6")

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        pv = C.ind_rate("Diarrhoea in last 2 weeks", ["Survey", "Wealth"])
        if not pv.empty:
            pv = pv.assign(Survey=pv["Survey"].astype(str), Wealth=pv["Wealth"].astype(str)).pivot_table(index="Survey", columns="Wealth", values="value")
            pv = pv.reindex(index=C.survey_order(pv.index), columns=[w for w in C.WEALTH if w in pv.columns])
            C.heatmap(pv, "Diarrhoea by survey and wealth quintile (lower is better)", "%", key="il7", reverse=True, xlabel="Wealth quintile", colorscale="RdYlGn")
        else:
            C.no_data()
    with b:
        kk = k[k["diarrhoea"].notna() & k["fever"].notna()].copy()
        if kk.empty:
            C.no_data()
        else:
            kk["Illness"] = "Neither"
            kk.loc[(kk["diarrhoea"] == 1) & (kk["fever"] == 0), "Illness"] = "Diarrhoea only"
            kk.loc[(kk["diarrhoea"] == 0) & (kk["fever"] == 1), "Illness"] = "Fever only"
            kk.loc[(kk["diarrhoea"] == 1) & (kk["fever"] == 1), "Illness"] = "Both"
            d = C.dist(kk, "Illness", by)
            C.dist_chart(d, "Illness", by, "Children ill with diarrhoea, fever, both or neither", cmap=CO_COL, order=list(CO_COL), key="il8", cat_label="Illness", height=430)
    st.caption("The right chart shows how often the two illnesses come together. It leaves out surveys that did not ask about fever (Punjab 2011).")
