"""Three research-style graphics: co-coverage scatter, equiplot over time, bivariate district tile map -
each with a data-validity check next to it."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as C

VAC = ["vacc_BCG", "vacc_Polio", "vacc_Penta/DPT", "vacc_Measles"]
BIV = [["#E8E8E8", "#B5C0DA", "#6C83B5"], ["#B8D6BE", "#90B2B3", "#567994"], ["#73AE80", "#5A9178", "#2A5A5B"]]   # [y class][x class]
MIN_N = 50


def _units():
    """one row per district-in-survey: average coverage of the four vaccines and co-coverage (all four)"""
    c = C.apply(C.load("children"), "children")
    if c is None or c.empty:
        return pd.DataFrame()
    c = c[c[VAC].notna().all(axis=1) & c["District"].notna()].copy()
    rows = []
    for (s, d), g in c.groupby([c["Survey"].astype(str), c["District"].astype(str)], observed=True):
        if len(g) < MIN_N:
            continue
        w = g["w"].values
        avg = np.mean([np.average(g[v].astype(float), weights=w) for v in VAC]) * 100
        co = np.average((g[VAC].astype(float).sum(axis=1) == 4).astype(float), weights=w) * 100
        rows.append(dict(Survey=s, District=d, Province=C.survey_province(s), avg=avg, co=co, n=len(g)))
    return pd.DataFrame(rows)


def scatter_cocoverage():
    u = _units()
    if len(u) < 8:
        return C.no_data("Fewer than 8 districts have enough vaccination records for the current filters."), None
    x, y = u["avg"].values, u["co"].values
    b, a = np.polyfit(x, y, 1)
    xs = np.linspace(x.min(), x.max(), 60)
    res = y - (a + b * x)
    s = np.sqrt((res ** 2).sum() / (len(x) - 2))
    sxx = ((x - x.mean()) ** 2).sum()
    se = s * np.sqrt(1 / len(x) + (xs - x.mean()) ** 2 / sxx)
    r2 = 1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum()
    f = go.Figure()
    f.add_trace(go.Scatter(x=np.r_[xs, xs[::-1]], y=np.r_[a + b * xs + 1.97 * se, (a + b * xs - 1.97 * se)[::-1]], fill="toself", fillcolor="rgba(120,120,120,.22)",
                           line=dict(width=0), hoverinfo="skip", showlegend=False))
    f.add_trace(go.Scatter(x=[0, 100], y=[0, 100], mode="lines", line=dict(dash="dash", color="#9AA5B1"), showlegend=False, hoverinfo="skip"))
    f.add_trace(go.Scatter(x=xs, y=a + b * xs, mode="lines", line=dict(color="#111", width=3), name="Trend", showlegend=False, hoverinfo="skip"))
    for pv, g in u.groupby("Province"):
        f.add_trace(go.Scatter(x=g["avg"], y=g["co"], mode="markers", name=pv, marker=dict(size=np.clip(g["n"] ** 0.5 / 2.2, 7, 18), color=C.PROV_COLORS.get(pv, "#999"),
                               line=dict(width=1, color="#fff"), opacity=.9), customdata=np.c_[g["District"], g["Survey"], g["n"]],
                               hovertemplate="%{customdata[0]} (%{customdata[1]})<br>average coverage %{x:.1f}%<br>all four vaccines %{y:.1f}%<br>children: %{customdata[2]:,}<extra></extra>"))
    f.update_layout(title="Average coverage vs co-coverage (all four vaccines), one dot = one district in one survey",
                    xaxis_title="Average coverage of BCG, polio, penta/DPT and measles (at least one dose, %)", yaxis_title="Children with all four (%)")
    f.update_xaxes(range=[max(0, x.min() - 5), 102]); f.update_yaxes(range=[max(0, y.min() - 5), 102])
    C.style(f, 520, legend_title="Province")
    C.show(f, key="ev_cc")
    return None, dict(n=len(u), minn=int(u["n"].min()), r2=r2, slope=b, gap=float((u["avg"] - u["co"]).mean()), surveys=u["Survey"].nunique(), d=u["District"].nunique())


def equiplot():
    pct = [k for k, v in C.IND.items() if v[2] == "%" and "Wealth" in C.ind_dims(k)]
    c = st.columns(2)
    with c[0]:
        k = C.side().selectbox("Equiplot: indicator", pct, index=pct.index("Skilled birth attendant") if "Skilled birth attendant" in pct else 0, key="ev_eq_k")
    with c[1]:
        provs = [p for p in C.PROV_ORDER if p in C.get_filters()["provinces"]]
        prov = C.side().selectbox("Equiplot: province", provs, key="ev_eq_p")
    r = C.ind_rate(k, ["Survey", "Wealth"])
    if r is None or r.empty:
        return C.no_data(), None
    r = r.assign(Survey=r["Survey"].astype(str), Wealth=r["Wealth"].astype(str))
    r = r[r["Survey"].map(C.survey_province) == prov]
    if r.empty:
        return C.no_data("No survey of this province has data for the current filters."), None
    order = C.survey_order(list(r["Survey"].unique()))
    f = go.Figure()
    for s in order:
        g = r[r["Survey"] == s]
        if len(g) >= 2:
            f.add_trace(go.Scatter(x=[g["value"].min(), g["value"].max()], y=[s, s], mode="lines", line=dict(color="#0B3C49", width=2), showlegend=False, hoverinfo="skip"))
    for q in C.WEALTH:
        g = r[r["Wealth"] == q].set_index("Survey").reindex(order).dropna(subset=["value"])
        f.add_trace(go.Scatter(x=g["value"], y=g.index, mode="markers", name={"Poorest": "Q1 (poorest)", "Richest": "Q5 (richest)"}.get(q, f"Q{C.WEALTH.index(q) + 1}"),
                               marker=dict(size=17, color=C.WEALTH_COLORS[q], line=dict(width=1.5, color="#fff")), customdata=np.c_[g["n"]],
                               hovertemplate="%{y}<br>" + q + ": %{x:.1f}%<br>records: %{customdata[0]:,}<extra></extra>"))
    f.update_layout(title=f"{k} by wealth quintile, {prov}", xaxis_title="% (weighted)", yaxis_title="")
    f.update_yaxes(categoryorder="array", categoryarray=order, autorange="reversed")
    f.update_xaxes(range=[0, 100])
    C.style(f, max(380, 150 + 70 * len(order)), legend_title="Wealth")
    C.show(f, key="ev_eq")
    sp = r.groupby("Survey")["value"].agg(lambda s: s.max() - s.min())
    return None, dict(surveys=len(order), cells=len(r), minn=int(r["n"].min()), first=float(sp.reindex(order).iloc[0]), last=float(sp.reindex(order).iloc[-1]), first_s=order[0], last_s=order[-1])


def bivariate():
    pct = [k for k, v in C.IND.items() if v[2] == "%"]
    c = st.columns(3)
    with c[0]:
        kx = C.side().selectbox("Map tiles: indicator 1 (columns)", pct, index=pct.index("Measles: at least one dose (12-35 months)") if "Measles: at least one dose (12-35 months)" in pct else 0, key="ev_bx")
    with c[1]:
        ky = C.side().selectbox("Map tiles: indicator 2 (rows)", pct, index=pct.index("Skilled birth attendant") if "Skilled birth attendant" in pct else 1, key="ev_by")
    a, b = C.ind_rate(kx, ["Survey", "District"]), C.ind_rate(ky, ["Survey", "District"])
    if a is None or b is None or a.empty or b.empty:
        return C.no_data(), None
    m = a.merge(b, on=["Survey", "District"], suffixes=("_x", "_y"))
    m["Survey"] = m["Survey"].astype(str)
    m = m[(m["n_x"] >= MIN_N) & (m["n_y"] >= MIN_N)]
    if m.empty:
        return C.no_data("No district has both indicators with enough records."), None
    with c[2]:
        opts = C.survey_order(list(m["Survey"].unique()))
        latest = max(opts, key=lambda x: (m["Survey"].eq(x).sum() >= 6, int(x.rsplit(" ", 1)[1]), m["Survey"].eq(x).sum()))   # most recent survey with enough districts
        sv = C.side().selectbox("Map tiles: survey", opts, index=opts.index(latest), key="ev_bs")
    m = m[m["Survey"] == sv].sort_values("District").reset_index(drop=True)
    if len(m) < 6:
        return C.no_data("Fewer than 6 districts in this survey have both indicators."), None
    qx = pd.qcut(m["value_x"].rank(method="first"), 3, labels=False)
    qy = pd.qcut(m["value_y"].rank(method="first"), 3, labels=False)
    m["cls"] = qy * 3 + qx
    cols = 6
    m["col"] = m.index % cols
    m["row"] = m.index // cols
    z = np.full((m["row"].max() + 1, cols), np.nan)
    t = np.full(z.shape, "", dtype=object)
    h = np.full(z.shape, "", dtype=object)
    for r in m.itertuples():
        z[r.row, r.col] = r.cls
        t[r.row, r.col] = r.District.replace("Khyber ", "")[:13]
        h[r.row, r.col] = f"<b>{r.District}</b><br>{kx[:34]}: {r.value_x:.1f}%<br>{ky[:34]}: {r.value_y:.1f}%<br>records: {int(min(r.n_x, r.n_y)):,}"
    flat = [BIV[i // 3][i % 3] for i in range(9)]
    scale = []
    for i, col in enumerate(flat):
        scale += [[i / 9, col], [(i + 1) / 9, col]]
    f = go.Figure(go.Heatmap(z=z, text=t, texttemplate="%{text}", textfont=dict(size=11, color="#111"), customdata=h, hovertemplate="%{customdata}<extra></extra>", colorscale=scale, zmin=0, zmax=9,
                             showscale=False, xgap=4, ygap=4))
    f.update_layout(title=f"District tiles, {sv}: {len(m)} districts coloured by the two indicators (terciles within this survey)")
    f.update_xaxes(visible=False); f.update_yaxes(visible=False, autorange="reversed")
    left, right = st.columns([3, 1])
    with left:
        C.style(f, max(320, 70 * z.shape[0] + 110), legend=False, bottom=20)
        C.show(f, key="ev_biv")
    with right:
        lg = go.Figure(go.Heatmap(z=np.arange(9).reshape(3, 3)[::-1], colorscale=scale, zmin=0, zmax=9, showscale=False, xgap=3, ygap=3, hoverinfo="skip"))
        lg.update_xaxes(showticklabels=False, title=f"{kx.split(':')[0][:24]} →", title_font_size=11)
        lg.update_yaxes(showticklabels=False, title=f"{ky[:22]} →", title_font_size=11)
        lg.update_layout(title=dict(text="Legend", font_size=13))
        C.style(lg, 260, legend=False, bottom=50)
        C.show(lg, key="ev_leg")
        st.caption("Dark teal = high on both, grey = low on both, green = high 2 / low 1, blue = high 1 / low 2.")
    both_low = int(((qx == 0) & (qy == 0)).sum())
    return None, dict(n=len(m), minn=int(m[["n_x", "n_y"]].min().min()), both_low=both_low, sv=sv, wide=float(((m["hi_x"] - m["lo_x"]).median() + (m["hi_y"] - m["lo_y"]).median()) / 2))


def render():
    C.page_header("Research graphics", "Three graphic types used in research papers, built from your data, each with a validity check", ":material/science:")

    st.markdown("##### 1. Average coverage vs co-coverage")
    err, v1 = scatter_cocoverage()
    if v1:
        C.takeaway(f"Across {v1['n']} district-surveys, the share of children with all four vaccines is on average {v1['gap']:.0f} points below the average coverage of the single vaccines. "
                   f"Co-coverage can never be higher than average coverage, so every dot sits under the dashed line; the further below, the more children miss at least one vaccine.")
    with st.expander("Is my data valid for this graph?", expanded=True):
        if v1:
            ok = v1["minn"] >= MIN_N
            st.markdown(f"* **Units:** {v1['n']} districts-in-survey from {v1['surveys']} surveys ({v1['d']} different districts). Smallest district has {v1['minn']} children (rule: at least {MIN_N}). {'✅' if ok else '⚠️'}\n"
                        f"* **Who is counted:** children aged 12-35 months with an answer for all four vaccines (card or mother's recall); others are left out. Counts **any dose**, not full course.\n"
                        f"* **Weights:** each district value is weighted with the children's sample weight; the trend line itself is **not weighted** (every district counts once, whatever its size).\n"
                        f"* **Fit:** trend slope {v1['slope']:.2f}, R² = {v1['r2']:.2f}. The grey band is the 95% confidence band of the trend line, not of each district. A high R² is expected here because co-coverage is built from the same four vaccines as the average, so do not read it as a finding.\n"
                        f"* **Caution:** one district appears once per survey, so the same district can show up in several dots. District estimates from MICS have wide margins of error; read the pattern, not single dots.")
        else:
            st.write("Not enough data to check.")

    st.markdown("---")
    st.markdown("##### 2. Equiplot: the gap between rich and poor over time")
    err, v2 = equiplot() or (None, None)
    if v2:
        C.takeaway(f"Gap between the highest and lowest wealth group: {v2['first']:.0f} points in {v2['first_s']} and {v2['last']:.0f} points in {v2['last_s']}. "
                   "Dots close together mean equal access; a long line means a large gap.")
    with st.expander("Is my data valid for this graph?"):
        if v2:
            st.markdown(f"* **Cells:** {v2['cells']} survey × wealth-group estimates over {v2['surveys']} surveys; the smallest has {v2['minn']} records {'✅' if v2['minn'] >= MIN_N else '⚠️'}.\n"
                        "* **Wealth quintiles** are the survey's own wealth index, so Q1 in one survey is not exactly the same living standard as Q1 in another year.\n"
                        "* Years differ by province, so compare changes within one province only.")
        else:
            st.write("Not enough data to check.")

    st.markdown("---")
    st.markdown("##### 3. Two indicators at once across districts")
    err, v3 = bivariate() or (None, None)
    if v3:
        C.takeaway(f"In {v3['sv']}, {v3['both_low']} of {v3['n']} districts are in the lowest third on both indicators. These are the districts where both services are weak at the same time.")
    with st.expander("Is my data valid for this graph?"):
        if v3:
            st.markdown(f"* **Districts:** {v3['n']} with at least {MIN_N} records for both indicators (smallest: {v3['minn']}). Typical 95% margin of error ≈ ±{v3['wide'] / 2:.0f} points {'✅' if v3['wide'] / 2 < 10 else '⚠️'}.\n"
                        "* **Colours are relative:** thirds are made within the selected survey, so 'high' means high compared with the other districts, not high compared with a target.\n"
                        "* **This is a tile map, not a geographic map.** The dashboard only has province boundaries. A true district map needs a district boundary file (Pakistan admin level 2), which I can add if you supply one.")
        else:
            st.write("Not enough data to check.")
