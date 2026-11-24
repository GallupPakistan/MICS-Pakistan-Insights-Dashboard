import pandas as pd
import plotly.express as px
import streamlit as st

import common as C
import extras as X


def render():
    C.page_header("Compare & data explorer", "Build your own comparison of any indicator, download the numbers, and read the data notes", ":material/query_stats:")
    keys = list(C.IND)
    c = st.columns([3, 2, 2, 2])
    c_f = st.columns([3, 2, 2, 2])
    with c[0]:
        ind = C.side().selectbox("Indicator", keys, index=keys.index("Improved drinking water"), key="ex_ind")
    table = C.IND[ind][0]
    dims = C.ind_dims(ind)
    extra = {"hh": ["District"], "women": ["AgeGroup", "Education", "District"], "men": ["AgeGroup", "Education", "District"],
             "children": ["AgeGroup", "MotherEdu", "District"], "births": ["BirthOrder", "BirthInterval", "MotherAgeAtBirth"],
             "c5to17": ["AgeGroup", "MotherEdu"], "siblings": [], "nets": []}.get(table, [])
    df0 = C.load(table)
    dims = dims + [e for e in extra if df0 is not None and e in df0.columns]
    with c[1]:
        x = C.side().selectbox("Group on the x-axis / rows", dims, index=dims.index("Survey") if "Survey" in dims else 0, key="ex_x", format_func=lambda d: C.DIM_LABEL.get(d, d))
    with c[2]:
        col_opts = ["(none)"] + [d for d in dims if d != x]
        colour = C.side().selectbox("Split by (colour)", col_opts, index=(col_opts.index("Area") if "Area" in col_opts else 0), key="ex_c", format_func=lambda d: C.DIM_LABEL.get(d, d))
    with c[3]:
        kind = C.side().radio("Chart", ["Bars", "Lines", "Heatmap", "Table"], key="ex_k", horizontal=True)
    with c_f[1]:
        fac_opts = ["(none)"] + [d for d in dims if d not in (x, colour)]
        facet = C.side().selectbox("Small multiples (one panel per ...)", fac_opts, key="ex_f", format_func=lambda d: C.DIM_LABEL.get(d, d),
                             help="Splits the chart into one panel per group - a third dimension.")
    st.caption(C.IND[ind][5])
    unit = C.IND[ind][2]
    by = [x] + ([colour] if colour != "(none)" else []) + ([facet] if facet != "(none)" else [])
    r = C.ind_rate(ind, by)
    if r.empty:
        C.no_data("No data for this combination. Try different filters or groups.")
        return
    if kind == "Bars" and facet != "(none)":
        d = r.copy()
        for cc in by:
            d[cc] = d[cc].astype(str)
        cdim = colour if colour != "(none)" else x
        d["label"] = d["value"].map(lambda v: f"{v:.0f}{'%' if unit == '%' else ''}")
        fig = px.bar(d, x=x, y="value", color=cdim, facet_col=facet, facet_col_wrap=3, text="label", color_discrete_map=C.color_map(cdim, d[cdim]),
                     category_orders={x: C.cat_order(x, d[x]), cdim: C.cat_order(cdim, d[cdim]), facet: C.cat_order(facet, d[facet])},
                     labels={"value": C.unit_axis(unit), x: C.DIM_LABEL.get(x, x), cdim: C.DIM_LABEL.get(cdim, cdim)}, hover_data={"n": ":,", "label": False},
                     title=f"{ind}: one panel per {C.DIM_LABEL.get(facet, facet).lower()}")
        fig.update_traces(textposition="outside", cliponaxis=False, opacity=1, textfont_size=10)
        fig.update_yaxes(range=[0, max(d["value"].max(), 1) * 1.2])
        fig.update_xaxes(tickangle=-40, title=None)
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        rows = -(-d[facet].nunique() // 3)
        C.style(fig, 260 * rows + 200, legend_title=C.DIM_LABEL.get(cdim, cdim), legend=(cdim != x))
        C.show(fig, key="ex_facet")
    elif kind == "Bars":
        C.bar_chart(r, x, f"{ind} by {C.DIM_LABEL.get(x, x).lower()}", unit, color=None if colour == "(none)" else colour, key="ex_bar", height=500)
    elif kind == "Lines":
        if colour == "(none)":
            C.no_data("Pick a 'Split by' group to draw lines.")
        else:
            C.line_chart(r, x, colour, f"{ind} by {C.DIM_LABEL.get(x, x).lower()}", unit, key="ex_line", height=500)
    elif kind == "Heatmap":
        if colour == "(none)":
            C.no_data("Pick a 'Split by' group for the second axis of the heatmap.")
        else:
            rr = r.copy()
            rr[x], rr[colour] = rr[x].astype(str), rr[colour].astype(str)
            pv = rr.pivot(index=x, columns=colour, values="value")
            pv = pv.reindex(index=C.cat_order(x, pv.index), columns=C.cat_order(colour, pv.columns))
            pol = C.IND[ind][3]
            C.heatmap(pv, f"{ind}", unit, key="ex_heat", height=520, colorscale="RdYlGn" if pol else "Blues", reverse=(pol < 0),
                      xlabel=C.DIM_LABEL.get(colour, colour), ylabel=C.DIM_LABEL.get(x, x))
    out = r.copy()
    out.columns = [C.DIM_LABEL.get(c, c) if c in dims else {"value": "Value", "n": "Records (unweighted)", "neff": "Effective sample size", "lo": "95% CI low", "hi": "95% CI high"}.get(c, c) for c in out.columns]
    out = out.round(2)
    st.dataframe(out, **C.STRETCH, hide_index=True)
    st.download_button("Download this table (CSV)", out.to_csv(index=False).encode("utf-8-sig"), file_name="mics_comparison.csv", mime="text/csv", key="ex_dl")

    st.markdown("---")
    st.markdown("##### Data notes and limitations")
    st.markdown("""
* **What a 'survey' is.** Each survey is one province in one year (Punjab 2011 / 2014 / 2017, Sindh 2014 / 2018, KP 2016 / 2019, Balochistan 2010 / 2019, GB 2016). There is no single national MICS in this data set,
  so a value over several provinces uses the latest survey of each province, weighted by province population (sidebar toggle), as an approximate Pakistan estimate.
* **Harmonisation.** The same answer is stored in different ways across surveys (Rural / RURAL / 2.0, Male / MALE / 1.0, Completed / COMPLETED / 1.0). All of them were mapped to one value.
  The source CSVs carry the SPSS value labels for every survey (checked value-by-value against the original SPSS files); numeric-code rules remain only as a fallback.
  Area and wealth quintile always come from the household table where the household could be matched.
* **Weights.** Every percentage uses the sample weight that belongs to the table (household, woman, man, child under 5 or child 5-17). Records with weight 0 (incomplete interviews) are dropped.
* **Confidence intervals** are approximate (they use the effective sample size and ignore clustering), so true uncertainty is larger.
* **Questions that were not asked** in a survey simply have no bar (for example wife-beating attitudes in Punjab 2011, mosquito nets in Punjab / KP / GB, men's interviews before 2017).
* **Anthropometry.** Stunting, wasting and underweight use the WHO z-scores and only plausible values (-6 to +6, not flagged). Balochistan 2010 has valid measurements for fewer than half of its children.
* **Mortality** is calculated from the birth history as a crude proportion, not with the MICS life-table method.
* **District** names come from the household record and are spelled slightly differently across surveys.""")
    try:
        log = (C.data_dir() / "prep_log.txt").read_text(encoding="utf-8")
        with st.expander("Data preparation log (what was mapped, share of records with a value per survey)"):
            st.code(log, language="text")
    except Exception:
        pass

    X.deep_dive("ex", ["Improved drinking water","Electricity","Skilled birth attendant","Four or more antenatal visits","Stunting (height-for-age < -2 SD)","Measles: at least one dose (12-35 months)","Women ever attended school","Contraceptive use","Diarrhoea in last 2 weeks","Mobile phone in household"], ["scorecard","area_gap","wealth_gap","forest"])
