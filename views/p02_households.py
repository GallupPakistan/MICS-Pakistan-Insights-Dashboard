import pandas as pd
import plotly.express as px
import streamlit as st

import common as C
import extras as X

HH_INDS = ["Electricity", "Clean cooking fuel / stove", "Crowded sleeping rooms", "Female-headed households", "Improved drinking water", "Improved sanitation"]


def render():
    C.page_header("Households & housing", "Who lives where, how crowded, and with what basic services", ":material/home:")
    hh = C.apply(C.load("hh"), "hh")
    if hh is None or hh.empty:
        C.no_data()
        return
    c = st.columns(5)
    with c[0]:
        v = (hh["hh_size"] * hh["w"]).sum() / hh.loc[hh["hh_size"].notna(), "w"].sum()
        C.kpi("Average household size", f"{v:.1f} members", help="Weighted mean number of usual household members.")
    for col, k in zip(c[1:], ["Female-headed households", "Electricity", "Clean cooking fuel / stove", "Crowded sleeping rooms"]):
        with col:
            val, delta, n, unit, pol, desc = C.overall(k)
            C.kpi(k, val, unit, delta, pol, help=f"{desc} (n = {n:,})")

    st.markdown("---")
    by = C.safe_dim(HH_INDS[0])
    ind = st.selectbox("Indicator", HH_INDS, key="hh_ind")
    a, b = st.columns(2)
    with a:
        C.bar_chart(C.ind_rate(ind, by), by, f"{ind} by {C.DIM_LABEL.get(by, by).lower()}", "%", height=500, key="hh_bar")
    with b:
        C.trend_chart(C.ind_rate(ind, "Survey"), f"{ind} over time", "%", key="hh_trend")
    st.caption(C.IND[ind][5])

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        r = C.wmean(hh, "hh_size", by)
        if r.empty:
            C.no_data()
        else:
            r = r.assign(label=r["value"].map(lambda v: f"{v:.1f}"))
            r[by] = r[by].astype(str)
            fig = px.bar(r, x=by, y="value", color=by, text="label", color_discrete_map=C.color_map(by, r[by]),
                         category_orders={by: C.cat_order(by, r[by])}, title="Average household size (members)",
                         labels={"value": "members per household", by: C.DIM_LABEL.get(by, by)}, hover_data={"n": ":,", "label": False})
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_yaxes(range=[0, r["value"].max() * 1.2])
            C.style(fig, 420, legend_title=C.DIM_LABEL.get(by, by))
            C.show(fig, key="hh_size")
    with b:
        d = C.dist(hh, "head_edu", by)
        C.dist_chart(d, "head_edu", by, "Education of the household head", cmap=C.EDU_COLORS, order=C.EDU, key="hh_edu", cat_label="Head's education")

    st.markdown("---")
    st.markdown("##### Mosquito nets (Balochistan 2010 and 2019, Sindh 2014 and 2018 only)")
    nets = C.apply(C.load("nets"), "nets")
    if nets is None or nets.empty:
        C.no_data("No mosquito-net records for the current filters (collected only in Balochistan and Sindh).")
    else:
        a, b, c3 = st.columns(3)
        with a:
            n_hh = nets.groupby("Survey", observed=True)["hh_nets"].mean().reset_index()
            n_hh["Survey"] = n_hh["Survey"].astype(str)
            n_hh = n_hh[n_hh["hh_nets"].notna()]
            n_hh["label"] = n_hh["hh_nets"].map(lambda v: f"{v:.1f}")
            fig = px.bar(n_hh, x="Survey", y="hh_nets", color="Survey", color_discrete_map=C.survey_colors(list(n_hh["Survey"])), text="label",
                         title="Nets per household that owns nets", labels={"hh_nets": "average number of nets"}, category_orders={"Survey": C.survey_order(n_hh["Survey"])})
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_yaxes(range=[0, n_hh["hh_nets"].max() * 1.25])
            C.style(fig, 380, legend=True)
            C.show(fig, key="nets1")
        with b:
            C.bar_chart(C.ind_rate("Mosquito nets observed", "Survey"), "Survey", "Nets seen by the interviewer", "%", key="nets2", height=380)
        with c3:
            d = C.dist(nets.assign(grp=pd.cut(nets["net_age_m"], [-1, 11, 23, 35, 300], labels=["< 1 year", "1-2 years", "2-3 years", "3+ years"]).astype(object)),
                       "grp", "Survey")
            C.dist_chart(d, "grp", "Survey", "Age of the net since obtained", order=["< 1 year", "1-2 years", "2-3 years", "3+ years"], key="nets3", height=380, cat_label="Net age")

    X.deep_dive("hh", ["Electricity", "Clean cooking fuel / stove", "Crowded sleeping rooms", "Female-headed households", "Rented dwelling"], ["scorecard", "wealth_gap"])
