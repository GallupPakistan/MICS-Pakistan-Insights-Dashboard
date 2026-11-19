import pandas as pd
import streamlit as st

import common as C


def render():
    C.page_header("Water, sanitation & hygiene", "Drinking-water source, toilet type and handwashing facilities of households", ":material/water_drop:")
    hh = C.apply(C.load("hh"), "hh")
    if hh is None or hh.empty:
        C.no_data()
        return
    C.kpi_row(["Improved drinking water", "Piped water", "Improved sanitation", "Open defecation", "Handwashing water available"])
    by = C.safe_dim("Improved sanitation")

    tabs = st.tabs(["Drinking water", "Sanitation", "Hygiene & equity"])
    with tabs[0]:
        a, b = st.columns(2)
        with a:
            C.bar_chart(C.ind_rate("Improved drinking water", by), by, f"Improved drinking water by {C.DIM_LABEL.get(by, by).lower()}", "%", key="w1")
        with b:
            C.trend_chart(C.ind_rate("Improved drinking water", "Survey"), "Improved drinking water over time", "%", key="w2")
        d = C.dist(hh, "WaterSource", by)
        C.dist_chart(d, "WaterSource", by, "Main source of drinking water (all sources)", cmap=C.STATUS_COLORS, order=list(C.STATUS_COLORS), key="w3",
                     height=480, cat_label="Water source")
        st.caption("Improved = piped, tube well / pump, protected well or spring, bottled / filtered / rain. Unimproved = tanker / cart, unprotected well or spring, surface water, other. "
                   "Local labels (e.g. 'motorized pump (dunky / turbine)', 'hand pump') were grouped under 'Tube well / pump'.")
    with tabs[1]:
        a, b = st.columns(2)
        with a:
            C.bar_chart(C.ind_rate("Improved sanitation", by), by, f"Improved sanitation by {C.DIM_LABEL.get(by, by).lower()}", "%", key="s1")
        with b:
            C.trend_chart(C.ind_rate("Open defecation", "Survey"), "Open defecation over time (lower is better)", "%", key="s2")
        d = C.dist(hh, "ToiletType", by)
        C.dist_chart(d, "ToiletType", by, "Type of toilet facility", cmap=C.TOILET_COLORS, order=list(C.TOILET_COLORS), key="s3", height=460, cat_label="Toilet type")
    with tabs[2]:
        a, b = st.columns(2)
        with a:
            C.bar_chart(C.ind_rate("Handwashing water available", by), by, "Water available at the handwashing place", "%", key="h1")
        with b:
            C.bar_chart(C.ind_rate("Improved sanitation", ["Survey", "Area"]), "Survey", "Improved sanitation: urban vs rural", "%", color="Area", key="h2")
        a, b = st.columns(2)
        with a:
            r = C.ind_rate("Improved sanitation", ["Survey", "Wealth"])
            if not r.empty:
                r["Survey"], r["Wealth"] = r["Survey"].astype(str), r["Wealth"].astype(str)
                pv = r.pivot(index="Survey", columns="Wealth", values="value")
                pv = pv.reindex(index=C.survey_order(pv.index), columns=[w for w in C.WEALTH if w in pv.columns])
                C.heatmap(pv, "Improved sanitation: survey x wealth quintile", "%", key="h3", xlabel="Wealth quintile")
            else:
                C.no_data()
        with b:
            r = C.ind_rate("Improved drinking water", ["Survey", "Wealth"])
            if not r.empty:
                r["Survey"], r["Wealth"] = r["Survey"].astype(str), r["Wealth"].astype(str)
                pv = r.pivot(index="Survey", columns="Wealth", values="value")
                pv = pv.reindex(index=C.survey_order(pv.index), columns=[w for w in C.WEALTH if w in pv.columns])
                C.heatmap(pv, "Improved drinking water: survey x wealth quintile", "%", key="h4", xlabel="Wealth quintile")
            else:
                C.no_data()
        st.caption("Heatmap colour: green = higher share, red = lower share. Blank cell = too few records.")
        tw = C.ind_rate("Improved drinking water", by)
        C.show_table(pd.concat([tw.assign(indicator="Improved drinking water"), C.ind_rate("Improved sanitation", by).assign(indicator="Improved sanitation")]), "wash_numbers")
