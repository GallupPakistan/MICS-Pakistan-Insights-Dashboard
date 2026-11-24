"""Extra, distinct chart types that every page can add as a 'Deep dive' section.
Each kind answers a different question, so no two charts repeat the same insight."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as C

GOOD, BAD, NEUTRAL = "#2E9E6B", "#D1495B", "#7A8CA3"


def _short(k, n=34):
    k = k.split(":")[0] if "at least one dose" in k else k
    return k if len(k) <= n else k[: n - 1] + "…"


def _long(keys, by):
    parts = []
    for k in keys:
        r = C.ind_rate(k, by)
        if r is not None and not r.empty:
            r = r.copy()
            r["Indicator"] = _short(k, 28)
            r["_key"] = k
            parts.append(r)
    return pd.concat(parts) if parts else pd.DataFrame()


def scorecard(keys, p, height=None):
    d = _long(keys, "Survey")
    if d.empty:
        return C.no_data()
    d["Survey"] = d["Survey"].astype(str)
    pv = d.pivot_table(index="Indicator", columns="Survey", values="value")
    pv = pv[[s for s in C.survey_order(list(pv.columns))]]
    pol = d.drop_duplicates("Indicator").set_index("Indicator")["_key"].map(lambda k: C.IND[k][3]).reindex(pv.index)
    # colour = how good the value is WITHIN its row (green = best survey, red = worst); lower-is-better rows are flipped
    lo, hi = pv.min(axis=1), pv.max(axis=1)
    sc = pv.sub(lo, axis=0).div((hi - lo).replace(0, np.nan), axis=0)
    flip = np.broadcast_to((pol.values < 0)[:, None], sc.shape)
    sc = pd.DataFrame(np.where(flip, 1 - sc.values, sc.values), index=sc.index, columns=sc.columns).fillna(0.5)
    sc[(pol.values == 0)] = 0.5                       # context indicators (no better / worse direction) stay neutral
    sc = sc.where(pv.notna())
    lab = {i: (i + " (lower = better)" if pol[i] < 0 else i + " (context)" if pol[i] == 0 else i) for i in pv.index}
    pv.index = [lab[i] for i in pv.index]
    pv.columns = [str(c) for c in pv.columns]
    C.heatmap(pv, "Scorecard: every indicator in every survey", "%", height=height or max(420, 150 + 44 * len(pv)), key=p + "_sc",
              colorscale="RdYlGn", digits=0, zcolor=sc.values, cbar_title="within the row")
    st.caption("Colours compare surveys within each row: green = best value of that indicator, red = worst (for 'lower = better' rows such as stunting, "
               "the lowest value is green). Compare change over time only within one province.")


def _gap(keys, dim, hi, lo, title, p):
    rows = []
    for k in keys:
        r = C.ind_rate(k, dim)
        if r is None or r.empty:
            continue
        r = r.assign(**{dim: r[dim].astype(str)}).set_index(dim)["value"]
        if hi in r.index and lo in r.index:
            rows.append((k, r[hi] - r[lo], C.IND[k][3]))
    if not rows:
        return C.no_data(f"No indicator in this page has both {hi} and {lo} values for the current filters.")
    t = pd.DataFrame(rows, columns=["k", "gap", "pol"]).sort_values("gap")
    cols = [NEUTRAL if pol == 0 else (GOOD if g * pol > 0 else BAD) for g, pol in zip(t["gap"], t["pol"])]
    f = go.Figure(go.Bar(y=[_short(k) for k in t["k"]], x=t["gap"], orientation="h", marker_color=cols,
                         text=t["gap"].map(lambda v: f"{v:+.1f}"), textposition="outside", cliponaxis=False,
                         hovertemplate="%{y}<br>%{x:+.1f} percentage points<extra></extra>"))
    f.add_vline(x=0, line_color="#444")
    f.update_layout(title=title, xaxis_title=f"{hi} − {lo} (points)", yaxis_title="")
    m = max(abs(t["gap"]).max(), 1) * 1.55          # room for the value label at the end of the longest bar
    f.update_xaxes(range=[-m, m])
    C.style(f, max(380, 110 + 44 * len(t)), legend=False, bottom=70)
    C.show(f, key=p)
    big = t.iloc[(t["gap"].abs()).argmax()]
    st.caption(f"Insight: the widest gap is {_short(big['k'])} ({big['gap']:+.1f} points, {hi} minus {lo}).")


def area_gap(keys, p):
    _gap(keys, "Area", "Urban", "Rural", "Urban–rural gap by indicator", p + "_ag")


def wealth_gap(keys, p):
    _gap(keys, "Wealth", "Richest", "Poorest", "Richest–poorest gap by indicator", p + "_wg")


def _pick(keys, p, label):
    """with many indicators a legend cannot fit in a half-width chart, so let the user choose up to 6"""
    if len(keys) <= 6:
        return keys
    return C.side().multiselect(label, keys, default=keys[:6], max_selections=6, key=p + "_pick") or keys[:1]


def gradient(keys, p):
    keys = _pick(keys, p, "Indicators to show (up to 6)")
    d = _long(keys, "Wealth")
    if d.empty:
        return C.no_data()
    d["Wealth"] = d["Wealth"].astype(str)
    f = go.Figure()
    for k, g in d.groupby("Indicator"):
        g = g.set_index("Wealth").reindex(C.WEALTH).reset_index()
        f.add_trace(go.Scatter(x=g["Wealth"], y=g["value"], mode="lines+markers", name=k, line=dict(width=3), marker=dict(size=8),
                               hovertemplate="%{x}<br>" + k + ": %{y:.1f}%<extra></extra>"))
    f.update_layout(title="Wealth gradient: from poorest to richest quintile", xaxis_title="Wealth quintile", yaxis_title=C.pct_axis(keys))
    f.update_yaxes(range=[0, 100])
    C.style(f, 420, legend_title="Indicator")
    C.show(f, key=p + "_gr")


def province_bars(keys, p):
    C.multi_bar(keys, "Province", "Province comparison (latest survey of each province)", height=450, key=p + "_pv", labels={k: _short(k, 24) for k in keys})


def sex_bars(keys, p):
    keys = [k for k in keys if "Sex" in C.ind_dims(k)]
    if not keys:
        return C.no_data("These indicators have no sex split.")
    C.multi_bar(keys, "Sex", "Women / girls vs men / boys", height=450, key=p + "_sx", labels={k: _short(k, 24) for k in keys})


def trend(keys, p):
    keys = _pick(keys, p, "Indicators to show (up to 6)")
    d = _long(keys, "Survey")
    if d.empty:
        return C.no_data()
    d["Survey"] = d["Survey"].astype(str)
    order = C.survey_order(list(d["Survey"].unique()))
    f = go.Figure()
    for k, g in d.groupby("Indicator"):
        g = g.set_index("Survey").reindex(order).reset_index()
        f.add_trace(go.Scatter(x=g["Survey"], y=g["value"], mode="lines+markers", name=k, connectgaps=False,
                               hovertemplate="%{x}<br>" + k + ": %{y:.1f}<extra></extra>"))
    f.update_layout(title="Indicators across surveys (oldest to newest)", xaxis_title="", yaxis_title=C.pct_axis(keys))
    f.update_xaxes(tickangle=-30)
    C.style(f, 450, legend_title="Indicator", bottom=150)
    C.show(f, key=p + "_tr")


def forest(keys, p):
    k = C.side().selectbox("Indicator for the confidence-interval chart", keys, key=p + "_fk")
    r = C.ind_rate(k, "Survey")
    if r is None or r.empty:
        return C.no_data()
    r = r.sort_values("value")
    unit = C.IND[k][2]
    f = go.Figure(go.Scatter(x=r["value"], y=r["Survey"].astype(str), mode="markers", marker=dict(size=11, color="#0B5FA5"),
                             error_x=dict(type="data", symmetric=False, array=r["hi"] - r["value"], arrayminus=r["value"] - r["lo"], color="#7A8CA3", thickness=2),
                             customdata=r[["n"]], hovertemplate="%{y}<br>%{x:.1f}<br>n = %{customdata[0]:,}<extra></extra>"))
    f.update_layout(title=f"{_short(k, 30)}: value with 95% CI", xaxis_title=C.unit_axis(unit), yaxis_title="")
    C.style(f, max(380, 120 + 40 * len(r)), legend=False, bottom=50)
    C.show(f, key=p + "_fo")


def scatter(keys, p):
    if len(keys) < 2:
        return C.no_data("Need two indicators.")
    c = st.columns(2)
    with c[0]:
        kx = C.side().selectbox("Scatter: horizontal axis", keys, index=0, key=p + "_sx_x")
    with c[1]:
        ky = C.side().selectbox("Scatter: vertical axis", keys, index=min(1, len(keys) - 1), key=p + "_sx_y")
    a, b = C.ind_rate(kx, "Survey"), C.ind_rate(ky, "Survey")
    if a is None or b is None or a.empty or b.empty:
        return C.no_data()
    m = a.merge(b, on="Survey", suffixes=("_x", "_y"))
    if len(m) < 2:
        return C.no_data("Fewer than two surveys have both indicators.")
    m["prov"] = m["Survey"].astype(str).map(C.survey_province)
    f = go.Figure(go.Scatter(x=m["value_x"], y=m["value_y"], mode="markers", text=m["Survey"].astype(str),
                             marker=dict(size=(m["n_x"] ** 0.5).clip(8, 40), color=[C.PROV_COLORS.get(x, "#999") for x in m["prov"]], opacity=.85, line=dict(width=1, color="white")),
                             hovertemplate="%{text}<br>x: %{x:.1f}<br>y: %{y:.1f}<extra></extra>"))
    f.update_layout(title=f"{_short(ky, 30)} vs {_short(kx, 30)} (one bubble per survey)", xaxis_title=_short(kx, 40), yaxis_title=_short(ky, 40))
    C.style(f, 450, legend=False, bottom=50)
    C.show(f, key=p + "_sc2")


def sample(tables, p):
    rows = []
    for t in tables:
        df = C.apply(C.load(t), t)
        if df is not None and not df.empty:
            n = df.groupby("Survey", observed=True).size()
            rows += [(s, t, v) for s, v in n.items() if v > 0]
    if not rows:
        return C.no_data()
    d = pd.DataFrame(rows, columns=["Survey", "Table", "n"])
    d["Survey"] = d["Survey"].astype(str)
    f = go.Figure()
    for t, g in d.groupby("Table"):
        f.add_trace(go.Bar(x=g["Survey"], y=g["n"], name=t))
    f.update_layout(barmode="group", title="Records behind these charts, per survey (unweighted counts)", yaxis_title="records (unweighted)", xaxis_title="")
    f.update_xaxes(categoryorder="array", categoryarray=C.survey_order(list(d["Survey"].unique())), tickangle=-30)
    C.style(f, 420, legend_title="Table", bottom=140)
    C.show(f, key=p + "_sm")


def drill(keys, p):
    c = st.columns(2)
    with c[0]:
        k = C.side().selectbox("Drill down: indicator", keys, key=p + "_k")
    with c[1]:
        dims = [d for d in ("Province", "Survey", "Area", "Wealth", "Sex") if d in C.ind_dims(k)]
        d = C.side().selectbox("Drill down: split by", dims, index=dims.index("Wealth") if "Wealth" in dims else 0, key=p + "_d")
    r = C.ind_rate(k, d)
    if r is None or r.empty:
        return C.no_data()
    C.bar_chart(r, d, f"Drill-down: {_short(k, 40)} by {C.DIM_LABEL.get(d, d).lower()}", C.IND[k][2], height=380, ci=True, key=p + "_dc")
    st.caption(f"Insight: {C.IND[k][5]}")


KINDS = dict(drill=drill, scorecard=scorecard, area_gap=area_gap, wealth_gap=wealth_gap, gradient=gradient, province=province_bars, sex=sex_bars,
             trend=trend, forest=forest, scatter=scatter)


def deep_dive(prefix, keys, kinds, tables=None, title="Deep dive"):
    """A section of extra charts in a 2-column grid. keys = indicators the page is about; kinds = which chart types to add."""
    st.markdown("---")
    st.markdown(f"##### {title}")
    kinds = list(kinds) + (["sample"] if tables else [])
    wide = [k for k in kinds if k == "scorecard"]            # the heatmap needs the full page width
    kinds = wide + [k for k in kinds if k != "scorecard"]
    for kd in wide:
        try:
            KINDS[kd](keys, f"{prefix}_{kd}")
        except Exception as e:
            st.warning(f"{kd} chart not available: {e}")
    kinds = kinds[len(wide):]
    for i in range(0, len(kinds), 2):
        cols = st.columns(2)
        for c, kd in zip(cols, kinds[i:i + 2]):
            with c:
                try:
                    if kd == "sample":
                        sample(tables, f"{prefix}_{kd}")
                    else:
                        KINDS[kd](keys, f"{prefix}_{kd}")
                except Exception as e:  # never break the page for an extra chart
                    st.warning(f"{kd} chart not available: {e}")