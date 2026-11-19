import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import common as C
import extras as X


def render():
    C.page_header("Overview", "Pakistan MICS surveys 2010-2019: Balochistan, Gilgit-Baltistan, Khyber Pakhtunkhwa, Punjab and Sindh", ":material/dashboard:")
    hh, women, men, kids = (C.apply(C.load(t), t) for t in ("hh", "women", "men", "children"))
    c = st.columns(5)
    with c[0]:
        C.kpi("Surveys in selection", f"{hh['Survey'].nunique() if hh is not None else 0}", help="One survey = one province in one year.")
    with c[1]:
        C.kpi("Households surveyed", f"{len(hh):,}" if hh is not None else "n/a", help="Completed household interviews matching the filters.")
    with c[2]:
        C.kpi("Women 15-49 interviewed", f"{len(women):,}" if women is not None else "n/a")
    with c[3]:
        C.kpi("Men 15-49 interviewed", f"{len(men):,}" if men is not None else "n/a", help="Men were interviewed only in 4 surveys (Balochistan 2019, KP 2019, Punjab 2017, Sindh 2018).")
    with c[4]:
        C.kpi("Children under 5 surveyed", f"{len(kids):,}" if kids is not None else "n/a")

    _heads = ["Improved drinking water", "Improved sanitation", "Electricity", "Stunting (height-for-age < -2 SD)", "Skilled birth attendant", "Measles: at least one dose (12-35 months)"]
    _v = {}
    for _k in _heads:
        _rr = C.ind_rate(_k, "Survey")
        if _rr is not None and not _rr.empty and _rr["n"].sum() > 0:
            _v[_k] = float((_rr["value"] * _rr["n"]).sum() / _rr["n"].sum())
    _good = {k: v for k, v in _v.items() if C.IND[k][3] > 0}
    if len(_good) >= 2:
        _hi, _lo = max(_good, key=_good.get), min(_good, key=_good.get)
        C.takeaway(f"Among the headline services, <b>{_hi.lower()}</b> reaches the most people ({_good[_hi]:.0f}%) and <b>{_lo.lower()}</b> the fewest ({_good[_lo]:.0f}%). "
                   f"{('Stunting affects ' + format(_v['Stunting (height-for-age < -2 SD)'], '.0f') + '% of children under 5. ') if 'Stunting (height-for-age < -2 SD)' in _v else ''}"
                   f"Pooled over the selected surveys; use the filters to focus on one province.")
    st.markdown("##### Headline indicators (pooled over the selected surveys)")
    C.kpi_row(["Improved drinking water", "Improved sanitation", "Electricity"])
    C.kpi_row(["Stunting (height-for-age < -2 SD)", "Skilled birth attendant", "Measles: at least one dose (12-35 months)"])
    st.caption("Arrows show the change between the first and last survey when a single province is selected (pp = percentage points). "
               "Green = improvement, red = deterioration. Pooled values over several provinces are sample-weighted; switch on 'Population-weighted (Pakistan)' in the sidebar for a national estimate.")

    st.markdown("---")
    st.markdown("##### Map: where does each province stand?")
    cc = st.columns([3, 2])
    with cc[0]:
        ind = st.selectbox("Indicator", C.MAP_INDICATORS, index=C.MAP_INDICATORS.index("Improved sanitation"), key="ov_ind")
    with cc[1]:
        scope = st.radio("Survey shown", ["Latest survey of each province", "Earliest survey of each province"], key="ov_scope", horizontal=True)
    left, right = st.columns([3, 2])
    with left:
        mp = C.province_map(ind, scope, key="ov_map")
    with right:
        rt = C.ind_rate(ind, "Survey")
        if rt.empty:
            C.no_data()
        else:
            C.bar_chart(rt, "Survey", f"{ind} by survey", C.IND[ind][2], orient="h", height=560, key="ov_rank")
    if mp is not None:
        C.show_table(mp, "map_values")

    st.markdown("---")
    st.markdown("##### Survey coverage: how many records exist for each table")
    cov = C.coverage()
    if not cov.empty:
        F = C.get_filters()
        sel = [s for s in (F["surveys"] or C.all_surveys()) if C.survey_province(s) in F["provinces"]]
        cov = cov[cov["Survey"].isin(sel)].copy()
        cov["_o"] = cov["Survey"].map(lambda s: C.survey_order(sel).index(s))
        cov = cov.sort_values("_o")
        cols = [c for c in ("households", "women", "men", "children", "births", "siblings", "nets", "c5to17", "members") if c in cov.columns]
        nice = {"households": "Households", "women": "Women", "men": "Men", "children": "Children <5", "births": "Birth history",
                "siblings": "Sibling history", "nets": "Mosquito nets", "c5to17": "Children 5-17", "members": "HH members"}
        z = cov[cols].values.astype(float)
        zlog = np.where(z > 0, np.log10(np.maximum(z, 1)), np.nan)
        text = np.where(z > 0, np.vectorize(lambda v: f"{int(v):,}")(z), "no data")
        fig = go.Figure(go.Heatmap(z=zlog, x=[nice[c] for c in cols], y=list(cov["Survey"]), text=text, texttemplate="%{text}", textfont=dict(size=10),
                                   colorscale="Blues", xgap=3, ygap=3, showscale=True,
                                   colorbar=dict(title=dict(text="records (log scale)", side="right"), thickness=14, tickvals=[1, 2, 3, 4, 5],
                                                 ticktext=["10", "100", "1,000", "10,000", "100,000"]),
                                   hovertemplate="%{y} - %{x}: %{text}<extra></extra>"))
        fig.update_layout(title="Records per survey and table ('no data' = not collected)", yaxis=dict(autorange="reversed"))
        fig.update_xaxes(tickangle=-35)
        C.style(fig, 470, legend=False, bottom=95)
        fig.update_xaxes(side="bottom", tickangle=-35)
        a, b = st.columns([5, 3])
        with a:
            C.show(fig, key="ov_cov")
        with b:
            rr = cov[["Survey", "sampled", "households", "response_rate"]].copy()
            rr["rate"] = rr["response_rate"] * 100
            rr["label"] = rr["rate"].map(lambda v: f"{v:.0f}%")
            cm = C.survey_colors(list(rr["Survey"]))
            f2 = px.bar(rr, y="Survey", x="rate", orientation="h", text="label", color="Survey", color_discrete_map=cm, title="Household response rate",
                        category_orders={"Survey": C.survey_order(rr["Survey"])[::-1]}, labels={"rate": "% interviewed"},
                        hover_data={"sampled": ":,", "households": ":,", "label": False, "rate": ":.1f"})
            f2.update_traces(textposition="outside", cliponaxis=False)
            f2.update_xaxes(range=[0, 112])
            C.style(f2, 470, legend=False, bottom=40)
            C.show(f2, key="ov_rr")
        C.show_table(cov.drop(columns="_o"), "survey_coverage")

    with st.expander("How to read this dashboard"):
        st.markdown("""
* **Filters (left)** apply to every page: province, survey, area, sex, wealth quintile and district. *Compare charts by* chooses the colour split.
* **Each survey is one province in one year** (e.g. *Punjab 2017*). Changes over time are only meaningful **within** a province.
* Percentages are **weighted** with the survey sample weight of the table (household, woman, man or child weight). Groups with fewer than N records are hidden.
* Pooled numbers over several provinces are **not national estimates** (weights are normalised inside each survey, not by province population).
* The 'Compare & data explorer' page lets you build any comparison and download the numbers.""")

    X.deep_dive("ov", ["Improved drinking water","Improved sanitation","Electricity","Clean cooking fuel / stove","Skilled birth attendant","Stunting (height-for-age < -2 SD)","Measles: at least one dose (12-35 months)","Contraceptive use"], ["scorecard","area_gap","wealth_gap","gradient"])
