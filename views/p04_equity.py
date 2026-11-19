import pandas as pd
import streamlit as st

import common as C
import extras as X


def render():
    C.page_header("Wealth & equity", "How outcomes differ between the poorest and the richest households, and between urban and rural areas", ":material/balance:")
    keys = list(C.IND)
    ind = st.selectbox("Indicator", keys, index=keys.index("Improved sanitation"), key="eq_ind", help=C.IND[keys[0]][5])
    table, col, unit, pol, where, desc = C.IND[ind]
    st.caption(desc)
    r = C.ind_rate(ind, ["Survey", "Wealth"], min_n=1)
    if r.empty:
        C.no_data("This indicator is not available for the selected filters.")
        return
    r["Survey"], r["Wealth"] = r["Survey"].astype(str), r["Wealth"].astype(str)
    pu = C.ind_rate(ind, ["Survey", "Wealth"])
    poor = pu[pu["Wealth"].astype(str) == "Poorest"].copy()
    rich = pu[pu["Wealth"].astype(str) == "Richest"].copy()
    for t in (poor, rich):
        t["Survey"] = t["Survey"].astype(str)
    total = C.overall(ind)
    c = st.columns(4)
    pv_poor = (poor["value"] * poor["n"]).sum() / poor["n"].sum() if len(poor) else float("nan")
    pv_rich = (rich["value"] * rich["n"]).sum() / rich["n"].sum() if len(rich) else float("nan")
    with c[0]:
        C.kpi("All households / records", total[0], unit, help="Pooled over the selected surveys")
    with c[1]:
        C.kpi("Poorest quintile", pv_poor, unit)
    with c[2]:
        C.kpi("Richest quintile", pv_rich, unit)
    with c[3]:
        gap = pv_rich - pv_poor
        C.kpi("Gap (richest minus poorest)", f"{gap:+.1f} {'pp' if unit == '%' else 'per 1,000'}" if gap == gap else "n/a", help="Percentage points (deaths per 1,000 births for mortality). Green / red in the chart below show whether the gap favours the richest.")

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        by = "Province"
        rp = C.ind_rate(ind, ["Province", "Wealth"])
        C.bar_chart(rp, "Wealth", f"{ind} by wealth quintile", unit, color="Province", key="eq1")
    with b:
        pv = r.pivot(index="Survey", columns="Wealth", values="value")
        pv = pv.reindex(index=C.survey_order(pv.index), columns=[w for w in C.WEALTH if w in pv.columns])
        C.heatmap(pv, f"{ind}: survey x wealth quintile", unit, key="eq2", reverse=(pol < 0), colorscale="RdYlGn" if pol else "Blues", xlabel="Wealth quintile")
    st.caption("Wealth quintiles come from the MICS wealth index (Poorest = bottom 20% of households). Colours: red = poorest ... blue = richest in the left chart; "
               "in the heatmap green = better, red = worse (neutral indicators use blues).")

    a, b = st.columns(2)
    with a:
        if len(poor) and len(rich):
            C.gap_chart(poor, rich, "Poorest", "Richest", f"Wealth gap per survey: {ind}", unit, polarity=pol, key="eq3")
        else:
            C.no_data("Select all wealth quintiles to compute the wealth gap.")
    with b:
        ur = C.ind_rate(ind, ["Survey", "Area"])
        if not ur.empty:
            u = ur[ur["Area"].astype(str) == "Urban"].assign(Survey=lambda d: d["Survey"].astype(str))
            ru = ur[ur["Area"].astype(str) == "Rural"].assign(Survey=lambda d: d["Survey"].astype(str))
            C.gap_chart(ru, u, "Rural", "Urban", f"Urban-rural gap per survey: {ind}", unit, polarity=pol, key="eq4")
        else:
            C.no_data()
    if pol != 0:
        st.caption("Bar colour: green = the gap favours the better-off group (higher is better for this indicator) or the group with lower burden, red = it favours the other group. "
                   "Labels give the gap in " + ("percentage points." if unit == "%" else "deaths per 1,000 births."))
    C.show_table(r, "equity_numbers")

    X.deep_dive("eq", ["Improved sanitation", "Electricity", "Skilled birth attendant", "Stunting (height-for-age < -2 SD)", "Measles: at least one dose (12-35 months)", "Women ever attended school", "Contraceptive use"], ["scorecard", "area_gap", "wealth_gap", "forest", "province"])
