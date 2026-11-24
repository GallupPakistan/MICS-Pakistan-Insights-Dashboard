import pandas as pd
import streamlit as st

import common as C

NUT = ["Stunting (height-for-age < -2 SD)", "Wasting (weight-for-height < -2 SD)", "Underweight (weight-for-age < -2 SD)"]
SHORT = dict(zip(NUT, ["Stunting", "Wasting", "Underweight"]))


def render():
    C.page_header("Child nutrition", "Growth of children under 5 compared with the WHO child growth standards", ":material/child_care:")
    k = C.apply(C.load("children"), "children")
    if k is None or k.empty:
        C.no_data()
        return
    C.kpi_row(NUT + ["Severe stunting (< -3 SD)"], cols=4, labels={**SHORT, "Severe stunting (< -3 SD)": "Severe stunting"})
    st.caption("Lower is better for stunting, wasting and underweight. Only children with valid, plausible measurements are counted "
               "(Balochistan 2010 measured fewer than half of its children, so read that survey with care).")
    by = C.safe_dim(NUT)
    st.markdown("---")
    C.multi_bar(NUT, by, "Malnutrition indicators", key="n1", labels=SHORT, height=450)

    ind = C.side().selectbox("Indicator", NUT, key="nut_ind", format_func=lambda x: SHORT[x])
    a, b = st.columns(2)
    with a:
        C.trend_chart(C.ind_rate(ind, "Survey"), f"{SHORT[ind]} over time", "%", key="n2")
    with b:
        r = C.rate(k, C.IND[ind][1], [by, "AgeGroup"])
        C.line_chart(r, "AgeGroup", by, f"{SHORT[ind]} by child's age", height=500, key="n3", xorder=["0-5 m", "6-11 m", "12-23 m", "24-35 m", "36-47 m", "48-59 m"])
    st.caption("Stunting rises sharply after 6 months when complementary foods are introduced and usually peaks at 12-35 months.")

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        r = C.rate(k, C.IND[ind][1], ["MotherEdu", by if by != "MotherEdu" else "Province"])
        C.bar_chart(r, "MotherEdu", f"{SHORT[ind]} by mother's education", "%", color=by if by != "MotherEdu" else "Province", key="n4")
    with b:
        C.bar_chart(C.ind_rate(ind, ["Wealth", by if by != "Wealth" else "Province"]), "Wealth", f"{SHORT[ind]} by wealth quintile", "%",
                    color=by if by != "Wealth" else "Province", key="n5")
    a, b = st.columns(2)
    with a:
        C.weighted_hist(k, "haz", "Distribution of height-for-age z-score (stunting cut-off at -2)", list(range(-6, 7)), "height-for-age z-score (WHO)", by=by, key="n6", vline=-2)
        st.caption("A curve shifted to the left means more children are short for their age. Dashed line = stunting cut-off.")
    with b:
        rows = []
        for v in NUT:
            r = C.ind_rate(v, "Survey")
            if not r.empty:
                r = r.copy()
                r["Survey"] = r["Survey"].astype(str)
                rows.append(r.assign(Indicator=SHORT[v]))
        if rows:
            d = pd.concat(rows)
            pv = d.pivot(index="Survey", columns="Indicator", values="value")
            pv = pv.reindex(index=C.survey_order(pv.index), columns=[SHORT[v] for v in NUT if SHORT[v] in pv.columns])
            C.heatmap(pv, "Malnutrition by survey", "%", key="n7", reverse=True, xlabel="")
            st.caption("Red = higher prevalence (worse), green = lower prevalence (better).")
        else:
            C.no_data()
    a, b = st.columns(2)
    with a:
        if "Sex" in k.columns:
            C.bar_chart(C.ind_rate(ind, ["Survey", "Sex"]), "Survey", f"{SHORT[ind]}: boys vs girls", "%", color="Sex", key="n8")
    with b:
        C.bar_chart(C.ind_rate(ind, ["Survey", "Area"]), "Survey", f"{SHORT[ind]}: urban vs rural", "%", color="Area", key="n9")
