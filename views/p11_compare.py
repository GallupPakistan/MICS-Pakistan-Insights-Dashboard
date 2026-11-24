import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as C

DEFAULT = ["Improved drinking water", "Improved sanitation", "Electricity", "Clean cooking fuel / stove", "Contraceptive use", "Skilled birth attendant",
           "Facility delivery", "Four or more antenatal visits", "Stunting (height-for-age < -2 SD)", "Wasting (weight-for-height < -2 SD)",
           "Measles: at least one dose (12-35 months)", "BCG: at least one dose (12-35 months)", "Women ever attended school"]
A_COL, B_COL = "#0B5FA5", "#E8A317"


def _group_widgets(tag, default_survey):
    surveys = C.all_surveys()
    st.markdown(f"**Group {tag}**")
    sv = st.multiselect(f"Survey(s) - group {tag}", surveys, default=[default_survey] if default_survey in surveys else surveys[:1], key=f"cmp_sv_{tag}")
    ar = st.multiselect(f"Area - group {tag}", ["Urban", "Rural"], default=["Urban", "Rural"], key=f"cmp_ar_{tag}")
    we = st.multiselect(f"Wealth quintile - group {tag}", C.WEALTH, default=C.WEALTH, key=f"cmp_we_{tag}")
    sx = st.multiselect(f"Sex - group {tag}", ["Male", "Female"], default=["Male", "Female"], key=f"cmp_sx_{tag}")
    name = ", ".join(sv) if sv else "all surveys"
    extra = []
    if len(ar) == 1:
        extra.append(ar[0].lower())
    if 0 < len(we) < 5:
        extra.append("/".join(w.lower() for w in we))
    if len(sx) == 1:
        extra.append(sx[0].lower())
    if extra:
        name += " (" + ", ".join(extra) + ")"
    return dict(surveys=sv, areas=ar, wealth=we, sexes=sx), name


def label(tag, name):
    return f"{tag}: {name}"


def render():
    C.page_header("Compare two groups", "Put any two groups next to each other (two surveys, urban vs rural, poorest vs richest ...) and see which differences are statistically real", ":material/compare_arrows:")
    st.caption("This page uses the groups you define below and ignores the sidebar province / survey / area / wealth filters.")
    c1, c2 = st.columns(2)
    with c1:
        A, nameA = _group_widgets("A", "Punjab 2017")
    with c2:
        B, nameB = _group_widgets("B", "Sindh 2018")
    keys = [k for k in C.IND if C.IND[k][2] == "%"]
    sel = st.multiselect("Indicators to compare", keys, default=[k for k in DEFAULT if k in keys], key="cmp_inds")
    if not sel:
        C.no_data("Pick at least one indicator.")
        return
    rows = []
    for k in sel:
        a, b = C.group_rate(k, A), C.group_rate(k, B)
        if a is None or b is None:
            rows.append(dict(Indicator=k, A=None, B=None, Difference=None, p=None, Significant="not available in one of the groups", Polarity=C.IND[k][3]))
            continue
        diff = b["value"] - a["value"]
        z = diff / ((a["se"] ** 2 + b["se"] ** 2) ** 0.5) if (a["se"] ** 2 + b["se"] ** 2) > 0 else 0
        p = C.p_two_sided(z)
        rows.append(dict(Indicator=k, A=a["value"], A_lo=a["lo"], A_hi=a["hi"], A_n=a["n"], B=b["value"], B_lo=b["lo"], B_hi=b["hi"], B_n=b["n"],
                         Difference=diff, p=p, Significant=("yes (p < 0.001)" if p < 0.001 else "yes (p < 0.05)" if p < 0.05 else "no"), Polarity=C.IND[k][3]))
    t = pd.DataFrame(rows)
    ok = t[t["A"].notna()].copy()
    if ok.empty:
        C.no_data("None of the selected indicators has data in both groups. Choose other groups or indicators.")
        return
    st.markdown("---")
    k1, k2, k3 = st.columns(3)
    with k1:
        C.kpi("Indicators compared", f"{len(ok)} of {len(t)}")
    with k2:
        C.kpi("Statistically different (p < 0.05)", f"{int((ok['p'] < 0.05).sum())} of {len(ok)}", help="Two-sided z-test using the effective sample size (ignores clustering, so slightly optimistic).")
    with k3:
        fav = ok[(ok["p"] < 0.05) & (ok["Polarity"] != 0)]
        better = int(((fav["Difference"] * fav["Polarity"]) > 0).sum())
        C.kpi("Group B better than A", f"{better} of {len(fav)}", help="Among significant differences where 'better' is clear (e.g. higher coverage, lower stunting).")

    d2 = ok.sort_values("Difference")
    cols = []
    for r in d2.itertuples():
        if r.p >= 0.05:
            cols.append("#9AA5B1")
        elif r.Polarity == 0:
            cols.append(C.NEUTRAL)
        else:
            cols.append(C.GOOD if r.Difference * r.Polarity > 0 else C.BAD)
    fig2 = go.Figure(go.Bar(y=d2["Indicator"], x=d2["Difference"], orientation="h", marker_color=cols, text=d2["Difference"].map(lambda v: f"{v:+.1f}"),
                            textposition="outside", cliponaxis=False, showlegend=False))
    for name, colr in (("Group B better (significant)", C.GOOD), ("Group B worse (significant)", C.BAD), ("Difference without clear better / worse", C.NEUTRAL),
                       ("Not significant (p >= 0.05)", "#9AA5B1")):
        fig2.add_trace(go.Bar(y=[None], x=[None], marker_color=colr, name=name, orientation="h"))
    m = max(abs(d2["Difference"]).max(), 1) * 1.3
    fig2.update_layout(title="Difference: group B minus group A (percentage points)", xaxis_title="percentage points", barmode="group")
    fig2.update_xaxes(range=[-m, m], zeroline=True, zerolinecolor="#444")
    C.style(fig2, max(420, 70 + 45 * len(d2)), legend_title="Colour")
    C.show(fig2, key="cmp2")
    st.caption("Grey = the difference could be chance. Green / red = significant and clearly better / worse for group B (green when higher is better and B is higher, or lower is better and B is lower).")

    st.markdown("---")
    st.markdown("##### Deep dive")
    o = ok.sort_values("A")
    r1 = st.columns(2)
    with r1[0]:  # 1 confidence intervals
        f = go.Figure()
        for nm, v, lo, hi, col in ((label("A", nameA), "A", "A_lo", "A_hi", A_COL), (label("B", nameB), "B", "B_lo", "B_hi", B_COL)):
            f.add_trace(go.Scatter(x=o[v], y=o["Indicator"], mode="markers", name=nm, marker=dict(size=10, color=col),
                                   error_x=dict(type="data", symmetric=False, array=o[hi] - o[v], arrayminus=o[v] - o[lo], color=col)))
        f.update_layout(title="Values with 95% confidence intervals", xaxis_title="% (weighted)", yaxis_title="")
        C.style(f, max(420, 90 + 50 * len(o)), legend_title="Group")
        C.show(f, key="cmp3")
    with r1[1]:  # 2 scatter A vs B
        f = go.Figure(go.Scatter(x=o["A"], y=o["B"], mode="markers", text=o["Indicator"], marker=dict(size=12, color=[C.GOOD if p < 0.05 else "#9AA5B1" for p in o["p"]]),
                                 hovertemplate="%{text}<br>A: %{x:.1f}<br>B: %{y:.1f}<extra></extra>"))
        f.add_shape(type="line", x0=0, y0=0, x1=100, y1=100, line=dict(dash="dash", color="#444"))
        f.update_layout(title="Group A vs group B (above the line = higher in B; green = significant)", xaxis_title=f"A: {nameA} (%)", yaxis_title=f"B: {nameB} (%)")
        C.style(f, max(420, 90 + 50 * len(o)), legend=False, bottom=50)
        C.show(f, key="cmp4")
    out = t.copy()
    out = out.rename(columns={"A": f"Value {label('A', nameA)}", "B": f"Value {label('B', nameB)}", "p": "p-value", "Difference": "Difference B - A (pp)"}).drop(columns=["Polarity"])
    C.show_table(out.round(3), "two_group_comparison", "Show / download the comparison table")
