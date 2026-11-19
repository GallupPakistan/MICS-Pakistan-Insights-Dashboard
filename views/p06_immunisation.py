import numpy as np
import pandas as pd
import streamlit as st

import common as C
import extras as X

VAC = ["BCG: at least one dose (12-35 months)", "Polio: at least one dose (12-35 months)", "Penta / DPT: at least one dose (12-35 months)",
       "Measles: at least one dose (12-35 months)"]
SHORT = dict(zip(VAC, ["BCG", "Polio", "Penta / DPT", "Measles"]))


def render():
    C.page_header("Child immunisation", "Children aged 12-35 months who received at least one dose (vaccination card or mother's report)", ":material/vaccines:")
    k = C.apply(C.load("children"), "children")
    if k is None or k.empty:
        C.no_data()
        return
    st.info("**Counts any dose, so these figures are higher than the official full-course coverage.** "
            "Every chart on this page shows children who received at least one dose of the vaccine.", icon=":material/info:")
    C.kpi_row(VAC, labels=SHORT)
    st.caption("Polio is 'any dose' and includes campaign doses, which is why it is close to 100%. Measles needs at least one dose of a measles-containing vaccine. "
               "Surveys differ in how many vaccines they ask about, so compare within the same vaccine.")
    by = C.safe_dim(VAC)
    st.markdown("---")
    C.multi_bar(VAC, by, "Children who received at least one dose, by vaccine", key="i1", labels=SHORT, height=470)

    ind = st.selectbox("Vaccine", VAC, index=3, key="imm_ind", format_func=lambda x: SHORT[x])
    a, b = st.columns(2)
    with a:
        C.trend_chart(C.ind_rate(ind, "Survey"), f"{SHORT[ind]} (at least one dose) over time", "%", key="i2")
    with b:
        C.bar_chart(C.ind_rate(ind, ["Wealth", by if by != "Wealth" else "Province"]), "Wealth", f"{SHORT[ind]}, at least one dose, by wealth quintile", "%",
                    color=by if by != "Wealth" else "Province", height=500, key="i3")

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        recs = []
        for v in VAC:
            r = C.ind_rate(v, "Survey")
            if not r.empty:
                r = r.copy()
                r["Survey"] = r["Survey"].astype(str)
                recs.append(r.assign(Vaccine=SHORT[v]))
        if recs:
            d = pd.concat(recs)
            pv = d.pivot(index="Survey", columns="Vaccine", values="value")
            pv = pv.reindex(index=C.survey_order(pv.index), columns=[SHORT[v] for v in VAC if SHORT[v] in pv.columns])
            C.heatmap(pv, "At least one dose, by survey and vaccine", "%", key="i4", xlabel="")
            st.caption("Green = higher coverage, red = lower coverage.")
        else:
            C.no_data()
    with b:
        kk = k[C.imm(k)].copy()
        cols = ["vacc_BCG", "vacc_Polio", "vacc_Penta/DPT", "vacc_Measles"]
        have = kk[cols].notna().all(axis=1)
        kk = kk[have]
        kk["zero"] = (kk[cols].sum(axis=1) == 0).astype(float)
        kk["all4"] = (kk[cols].sum(axis=1) == 4).astype(float)
        zr = C.rate(kk, "zero", "Survey")
        ar = C.rate(kk, "all4", "Survey")
        if zr.empty:
            C.no_data("Zero-dose and all-vaccine shares need all four vaccines in the survey.")
        else:
            zr["Group"] = "No vaccine at all (zero-dose)"
            ar["Group"] = "All four vaccines (at least one dose each)"
            both = pd.concat([zr, ar])
            both["Survey"] = both["Survey"].astype(str)
            import plotly.express as px
            both["label"] = both["value"].map(lambda v: f"{v:.0f}%")
            fig = px.bar(both, x="Survey", y="value", color="Group", barmode="group", text="label",
                         color_discrete_map={"No vaccine at all (zero-dose)": C.BAD, "All four vaccines (at least one dose each)": C.GOOD},
                         category_orders={"Survey": C.survey_order(both["Survey"])}, title="Zero-dose children and fully covered children (12-35 months)",
                         labels={"value": "% of children aged 12-35 months"}, hover_data={"n": ":,", "label": False})
            fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=11)
            fig.update_yaxes(range=[0, max(both["value"].max(), 1) * 1.2])
            fig.update_xaxes(tickangle=-30, title="")
            C.style(fig, 430, legend_title="Group")
            C.show(fig, key="i5")
    a, b = st.columns(2)
    with a:
        C.bar_chart(C.ind_rate(ind, ["Survey", "Area"]), "Survey", f"{SHORT[ind]}, at least one dose: urban vs rural", "%", color="Area", key="i6")
    with b:
        if "Sex" in k.columns:
            C.bar_chart(C.ind_rate(ind, ["Survey", "Sex"]), "Survey", f"{SHORT[ind]}, at least one dose: boys vs girls", "%", color="Sex", key="i7")

    X.deep_dive("im", ["BCG: at least one dose (12-35 months)", "Polio: at least one dose (12-35 months)", "Penta / DPT: at least one dose (12-35 months)", "Measles: at least one dose (12-35 months)"], ["scorecard", "province"])
