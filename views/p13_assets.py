import pandas as pd
import plotly.express as px
import streamlit as st

import common as C
import extras as X

ASSETS = ["Television", "Refrigerator", "Mobile phone in household", "Motorcycle / scooter", "Bank account in household"]
SHORT = dict(zip(ASSETS, ["Television", "Refrigerator", "Mobile phone", "Motorcycle", "Bank account"]))
ASSET_COL = dict(zip(ASSETS, ["#00897B", "#546E7A", "#F4511E", "#6D4C41", "#3949AB"]))      # one colour per asset (not used for provinces)
FLAG = {"Television": "has_tv", "Refrigerator": "has_fridge", "Mobile phone in household": "has_mobile",
        "Motorcycle / scooter": "has_motorbike", "Bank account in household": "has_bank"}


def render():
    C.page_header("Assets & connectivity", "What households own: television, refrigerator, phone, motorbike and a bank account", ":material/devices:")
    hh = C.apply(C.load("hh"), "hh")
    if hh is None or hh.empty or "has_tv" not in hh.columns:
        C.no_data()
        return
    C.kpi_row(ASSETS, cols=5, labels=SHORT)
    st.caption("Higher means more households own the item. Each asset was not asked in every survey, the notes under the charts list the surveys that are missing.")
    by = C.safe_dim(ASSETS)

    st.markdown("---")
    C.multi_bar(ASSETS, by, "Share of households owning each asset", key="as1", labels=SHORT, height=470)

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        rows = []
        for k in ASSETS:
            r = C.ind_rate(k, "Wealth")
            if not r.empty:
                rows.append(r.assign(Asset=SHORT[k]))
        if rows:
            d = pd.concat(rows)
            d["Wealth"] = d["Wealth"].astype(str)
            d = d.assign(_o=d["Wealth"].map(C.WEALTH.index)).sort_values(["Asset", "_o"])   # join points poorest -> richest
            fig = px.line(d, x="Wealth", y="value", color="Asset", markers=True, color_discrete_map={SHORT[k]: v for k, v in ASSET_COL.items()},
                          category_orders={"Wealth": C.WEALTH, "Asset": [SHORT[k] for k in ASSETS]}, title="Asset ladder: ownership from the poorest to the richest 20%",
                          labels={"value": "% of households owning it", "Wealth": "Wealth quintile"}, hover_data={"n": ":,"})
            fig.update_traces(line_width=2.8, marker_size=8)
            fig.update_yaxes(range=[0, 105])
            C.style(fig, 430, legend_title="Asset")
            C.show(fig, key="as2")
        else:
            C.no_data()
    with b:
        rows = []
        for k in ASSETS:
            r = C.ind_rate(k, "Area")
            if not r.empty:
                rows.append(r.assign(Asset=SHORT[k]))
        if rows:
            d = pd.concat(rows)
            d["Area"] = d["Area"].astype(str)
            d["label"] = d["value"].map(lambda v: f"{v:.0f}%")
            fig = px.bar(d, y="Asset", x="value", color="Area", orientation="h", barmode="group", text="label", color_discrete_map=C.AREA_COLORS,
                         category_orders={"Asset": [SHORT[k] for k in ASSETS][::-1], "Area": ["Urban", "Rural"]}, title="Urban and rural households",
                         labels={"value": "% of households owning it", "Asset": ""}, hover_data={"n": ":,", "label": False})
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_xaxes(range=[0, 115])
            C.style(fig, 430, legend_title="Area")
            C.show(fig, key="as3")
        else:
            C.no_data()
    st.caption("Left: the steeper the line, the more ownership depends on wealth. Right: the gap between the purple (urban) and gold (rural) bars is the urban advantage.")

    st.markdown("---")
    ind = C.side().selectbox("Asset to follow over time", ASSETS, key="as_ind", format_func=lambda x: SHORT[x])
    a, b = st.columns(2)
    with a:
        r = C.ind_rate(ind, "Survey")
        C.trend_chart(r, f"{SHORT[ind]} over time", "%", key="as4")
        C.availability_note(r, SHORT[ind].lower())
    with b:
        hh2 = hh[hh["female_head"].notna()].copy()
        hh2["Head"] = hh2["female_head"].map({0.0: "Male-headed", 1.0: "Female-headed"})
        rows = []
        for k in ASSETS:
            r = C.rate(hh2, FLAG[k], "Head")
            if not r.empty:
                rows.append(r.assign(Asset=SHORT[k]))
        if rows:
            d = pd.concat(rows)
            d["label"] = d["value"].map(lambda v: f"{v:.0f}%")
            fig = px.bar(d, x="Asset", y="value", color="Head", barmode="group", text="label", color_discrete_map={"Male-headed": "#2C7FB8", "Female-headed": "#E7298A"},
                         category_orders={"Asset": [SHORT[k] for k in ASSETS], "Head": ["Male-headed", "Female-headed"]}, title="Who heads the household: male or female",
                         labels={"value": "% of households owning it", "Asset": ""}, hover_data={"n": ":,", "label": False})
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_yaxes(range=[0, 115])
            C.style(fig, 500, legend_title="Household head")
            C.show(fig, key="as5")

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        r = C.rate(hh, "has_bank", ["head_edu", by if by != "head_edu" else "Province"])
        C.bar_chart(r, "head_edu", "Bank account by education of the household head", "%", color=by, key="as6", height=430)
    with b:
        C.bar_chart(C.ind_rate("Rented dwelling", [by, "Area"] if by != "Area" else ["Province", "Area"]), by if by != "Area" else "Province",
                    "Households renting their home", "%", color="Area", key="as7", height=430)
    st.caption("Renting is mostly an urban pattern. A low bank-account share among households whose head has no schooling shows who is left out of formal finance.")
    C.show_table(C.ind_rate("Bank account in household", [by if by != "Wealth" else "Province", "Wealth"]), "assets_bank_by_wealth")

    X.deep_dive("as", ["Television", "Refrigerator", "Mobile phone in household", "Motorcycle / scooter", "Bank account in household"], ["scorecard"])
