import pandas as pd
import plotly.express as px
import streamlit as st

import common as C

MORT = ["Neonatal deaths per 1,000 births", "Infant deaths per 1,000 births", "Under-5 deaths per 1,000 births (births 5-9 years ago)"]
SHORT = dict(zip(MORT, ["Neonatal (first month)", "Infant (before age 1)", "Under-5 (births 5-9 yrs ago)"]))


def render():
    C.page_header("Child mortality & sibling survival", "Deaths among children born to women 15-49 (birth history) and among their brothers and sisters (sibling history)", ":material/monitor_heart:")
    b = C.apply(C.load("births"), "births")
    if b is None or b.empty:
        C.no_data("Birth history exists only for Balochistan 2019, KP 2019, Punjab 2017 and Sindh 2018. Select at least one of these surveys.")
        return
    C.kpi_row(MORT, labels=SHORT)
    st.caption("Crude rates from the birth history: deaths per 1,000 births in the 10 years before the survey (under-5: births 5-9 years before, so every child had 5 years of exposure). "
               "They are indicative and not the official adjusted MICS mortality rates.")
    by = C.safe_dim(MORT)
    st.markdown("---")
    C.multi_bar(MORT, by, "Mortality rates (deaths per 1,000 births)", key="d1", labels=SHORT, height=450)
    st.caption("Values are deaths per 1,000 births.")

    ind = C.side().selectbox("Indicator", MORT, key="mort_ind", format_func=lambda x: SHORT[x])
    a, c = st.columns(2)
    with a:
        C.bar_chart(C.ind_rate(ind, ["Wealth", by if by != "Wealth" else "Province"]), "Wealth", f"{SHORT[ind]} by wealth quintile", "per 1,000",
                    color=by if by != "Wealth" else "Province", key="d2")
    with c:
        C.bar_chart(C.ind_rate(ind, ["Survey", "Area"]), "Survey", f"{SHORT[ind]}: urban vs rural", "per 1,000", color="Area", key="d3")
    a, c = st.columns(2)
    with a:
        if "Sex" in b.columns:
            C.bar_chart(C.ind_rate(ind, ["Survey", "Sex"]), "Survey", f"{SHORT[ind]}: boys vs girls", "per 1,000", color="Sex", key="d4")
    with c:
        df, col, unit, pol, where, desc = C.ind_data(ind)
        r = C.rate(df, col, ["BirthInterval", by], scale=1000.0, where=where)
        C.bar_chart(r, "BirthInterval", f"{SHORT[ind]} by interval since the previous birth", "per 1,000", color=by, key="d5")
        st.caption("Short intervals (< 2 years) are a known risk factor for child death.")
    a, c = st.columns(2)
    with a:
        r = C.rate(df, col, ["MotherAgeAtBirth", by], scale=1000.0, where=where)
        C.bar_chart(r, "MotherAgeAtBirth", f"{SHORT[ind]} by mother's age at birth", "per 1,000", color=by, key="d6")
    with c:
        r = C.rate(df, col, ["BirthOrder", by], scale=1000.0, where=where)
        C.bar_chart(r, "BirthOrder", f"{SHORT[ind]} by birth order", "per 1,000", color=by, key="d7")

    st.markdown("---")
    st.markdown("##### Sibling survival (women's brothers and sisters)")
    s = C.apply(C.load("siblings"), "siblings")
    if s is None or s.empty:
        C.no_data()
        return
    a, c = st.columns(2)
    with a:
        C.bar_chart(C.ind_rate("Siblings who died", ["Survey", "Sex"]), "Survey", "Share of listed siblings who have died", "%", color="Sex", key="d8")
    with c:
        dd = s[s["age_at_death"].notna()].copy()
        if dd.empty:
            C.no_data()
        else:
            dd["ageband"] = pd.cut(dd["age_at_death"], [-1, 0, 4, 14, 24, 39, 59, 120], labels=["< 1 year", "1-4", "5-14", "15-24", "25-39", "40-59", "60+"]).astype(object)
            d = C.dist(dd, "ageband", "Survey")
            C.dist_chart(d, "ageband", "Survey", "Age at death of deceased siblings", order=["< 1 year", "1-4", "5-14", "15-24", "25-39", "40-59", "60+"], key="d9",
                         height=430, cat_label="Age at death")
    a = st.container()
    with a:
        r = C.rate(s, "death_violence", ["Survey"])
        r2 = C.rate(s, "death_accident", ["Survey"])
        if r.empty and r2.empty:
            C.no_data()
        else:
            both = pd.concat([r.assign(Cause="Violence"), r2.assign(Cause="Accident")])
            both["Survey"] = both["Survey"].astype(str)
            both["label"] = both["value"].map(lambda v: f"{v:.1f}%")
            fig = px.bar(both, x="Survey", y="value", color="Cause", barmode="group", text="label", color_discrete_map={"Violence": C.BAD, "Accident": C.PROV_COLORS["Balochistan"]},
                         category_orders={"Survey": C.survey_order(both["Survey"])}, title="Deaths due to violence or accident (% of deceased siblings)",
                         labels={"value": "% of deceased siblings"}, hover_data={"n": ":,", "label": False})
            fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=11)
            fig.update_yaxes(range=[0, max(both["value"].max(), 1) * 1.25])
            fig.update_xaxes(tickangle=-30, title="")
            C.style(fig, 400, legend_title="Cause")
            C.show(fig, key="d10")
