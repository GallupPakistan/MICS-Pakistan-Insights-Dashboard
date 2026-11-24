"""Trend analysis: how each indicator changed between MICS rounds, province by province (all values weighted)."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as C

DIMS = {"No split": None, "Urban / rural": "Area", "Wealth quintile": "Wealth", "Boys / girls (where recorded)": "Sex"}
GAP = {"Area": ("Urban", "Rural"), "Wealth": ("Richest", "Poorest"), "Sex": ("Male", "Female")}
TAG = {"Area": "urban", "Wealth": "wealth", "Sex": "sex"}


def _year(s):
    return int(str(s).rsplit(" ", 1)[1])


def _cat(k):
    t = C.IND[k][0]
    if "dose" in k:
        return "Immunisation"
    if any(x in k for x in ("Stunting", "Wasting", "Underweight", "Vitamin")):
        return "Nutrition"
    if any(x in k for x in ("Diarrhoea", "Fever", "ORS")):
        return "Child illness"
    if any(x in k for x in ("water", "sanitation", "Open defecation", "Handwashing")):
        return "Water & sanitation"
    return {"hh": "Household", "women": "Women", "men": "Men", "children": "Children under 5", "births": "Mortality",
            "siblings": "Mortality", "c5to17": "Children 5-17", "nets": "Household", "members": "Household"}.get(t, "Other")


@st.cache_data(show_spinner=False)
def _trend_keys():
    """indicators that exist in at least two surveys of the same province (otherwise there is no trend to show)"""
    out = []
    for k, (t, col, *_r) in C.IND.items():
        df = C.load(t)
        if df is None or col not in df.columns:
            continue
        sv = df.loc[df[col].notna(), "Survey"].astype(str).unique()
        prov = pd.Series([C.survey_province(s) for s in sv])
        if (prov.value_counts() >= 2).any():
            out.append(k)
    return out


def _se(r):
    return (r["hi"] - r["lo"]) / 3.92


def _steps(rt, pol, unit):
    """one row per change between two surveys of a province: consecutive rounds, plus first -> latest when there are 3 rounds"""
    rows = []
    for prov, g in rt.groupby("Province"):
        g = g.sort_values("Year").reset_index(drop=True)
        pairs = [(i, i + 1) for i in range(len(g) - 1)]
        if len(g) > 2:
            pairs.append((0, len(g) - 1))
        for a, b in pairs:
            ra, rb = g.loc[a], g.loc[b]
            d = rb["value"] - ra["value"]
            se = np.sqrt(_se(ra) ** 2 + _se(rb) ** 2)
            z = d / se if se > 0 else np.nan
            sig = abs(z) >= 1.96 if z == z else False
            yrs = rb["Year"] - ra["Year"]
            if not sig:
                verdict = "No clear change"
            elif pol == 0:
                verdict = "Up" if d > 0 else "Down"
            else:
                verdict = "Better" if d * pol > 0 else "Worse"
            rows.append({"Province": prov, "Period": f"{ra['Year']} → {rb['Year']}" + (" (whole period)" if (a, b) == (0, len(g) - 1) and len(g) > 2 else ""),
                         "From": ra["value"], "To": rb["value"], "Change": d, "Per year": d / yrs if yrs else np.nan,
                         "Real change?": "yes" if sig else "no (within margin of error)", "Verdict": verdict})
    return pd.DataFrame(rows)


def _line(rt, title, color_col, colors, unit, show_ci, height=460, key=None):
    fig = go.Figure()
    order = C.cat_order(color_col, rt[color_col].astype(str).unique())
    for grp in order:
        g = rt[rt[color_col].astype(str) == grp].sort_values("Year")
        if g.empty:
            continue
        err = dict(type="data", symmetric=False, array=(g["hi"] - g["value"]).values, arrayminus=(g["value"] - g["lo"]).values,
                   thickness=1.2, width=4, color=colors.get(grp, "#888")) if show_ci else None
        lab = ["" for _ in range(len(g) - 1)] + [C.fmt(g["value"].iloc[-1], unit)]
        fig.add_trace(go.Scatter(x=g["Year"], y=g["value"], mode="lines+markers+text", name=C.PSHORT.get(grp, grp), text=lab, textposition="top center",
                                 line=dict(width=3, color=colors.get(grp, "#888")), marker=dict(size=9), error_y=err, cliponaxis=False,
                                 customdata=np.c_[g["Survey"].astype(str), g["n"]],
                                 hovertemplate="%{customdata[0]}<br>%{y:.1f}<br>n=%{customdata[1]:,}<extra>" + str(grp) + "</extra>"))
    yrs = sorted(rt["Year"].unique())
    fig.update_xaxes(tickmode="array", tickvals=yrs, ticktext=[(str(y) if i == 0 else "'" + str(y)[2:]) for i, y in enumerate(yrs)], tickangle=0,
                     range=[min(yrs) - 0.8, max(yrs) + 0.8], title="Survey year (start of fieldwork)")
    top = max(rt["hi"].max() if show_ci else rt["value"].max(), 1) * 1.15
    fig.update_yaxes(range=[0, min(top, 105) if unit == "%" else top], title=C.unit_axis(unit))
    fig.update_layout(title=title)
    C.style(fig, height)
    C.show(fig, key=key)


def render():
    C.page_header("Trend analysis", "How each indicator changed between survey rounds, province by province")
    keys = _trend_keys()
    if not keys:
        return C.no_data()
    st.info("Trends are only possible **within a province**: Punjab has 3 rounds (2011, 2014, 2017-18), Sindh, KP and Balochistan have 2, Gilgit-Baltistan has 1 "
            "(no trend). All values are weighted. Keep 'Year / round' on All to see every round; the other sidebar filters (province, area, "
            "sex, wealth, district) still apply.", icon=":material/info:")

    c1, c2, c3 = st.columns([2.2, 1.3, 1])
    cats = sorted({_cat(k) for k in keys})
    with c1:
        cat = C.side().selectbox("Topic", ["All topics"] + cats, key="tr_cat")
        pool = [k for k in keys if cat == "All topics" or _cat(k) == cat]
        dflt = "Stunting (height-for-age < -2 SD)" if "Stunting (height-for-age < -2 SD)" in pool else pool[0]
        ind = C.side().selectbox("Indicator", pool, index=pool.index(dflt), key="tr_ind", help=None)
    with c2:
        split = C.side().selectbox("Split the trend by", list(DIMS), index=1, key="tr_split")
    with c3:
        show_ci = C.side().toggle("95% confidence intervals", value=True, key="tr_ci", help="Vertical bars around each point. If the bars of two rounds overlap a lot, the change may be noise.")
    table, col, unit, pol, where, desc = C.IND[ind]
    st.caption(f"**{ind}**: {desc}  " + ("Higher is better." if pol > 0 else "Lower is better." if pol < 0 else "No better / worse direction (context indicator)."))

    rt = C.ind_rate(ind, "Survey")
    if rt.empty:
        return C.no_data()
    rt = rt.assign(Survey=rt["Survey"].astype(str))
    rt["Year"] = rt["Survey"].map(_year)
    rt["Province"] = rt["Survey"].map(C.survey_province)

    # ---- 1. trend by province + change table
    st.markdown("##### 1. Trend by province")
    _line(rt, f"{ind}: every survey round", "Province", C.PROV_COLORS, unit, show_ci, key="tr1")
    if True:
        steps = _steps(rt, pol, unit)
        if steps.empty:
            C.no_data("Only one survey per province for this indicator and these filters: no trend.")
        else:
            u = " pp" if unit == "%" else ""
            st.markdown("**What changed between rounds**")
            icon = {"Better": "🟢 Better", "Worse": "🔴 Worse", "No clear change": "⚪ No clear change", "Up": "🔵 Up", "Down": "🔵 Down"}
            show = pd.DataFrame({
                "Province": steps["Province"].map(lambda p: C.PSHORT.get(p, p)),
                "Period": steps["Period"].str.replace(" (whole period)", " (all)", regex=False),
                "Values": [f"{C.fmt(f, unit)} → {C.fmt(t, unit)}" for f, t in zip(steps["From"], steps["To"])],
                "Change": [f"{c:+.1f}{u} ({py:+.1f}/yr)" for c, py in zip(steps["Change"], steps["Per year"])],
                "Verdict": steps["Verdict"].map(icon)})
            st.dataframe(show, hide_index=True, **C.STRETCH, height=min(420, 38 + 35 * len(show)))
            st.caption("Change = later minus earlier survey (pp = percentage points; /yr = per year between the surveys). Better / Worse = the change is larger "
                       "than its 95% margin of error; 'No clear change' = it is within the margin (approximate test, cluster design not fully accounted for).")
    best = steps[steps["Period"].str.contains("whole") | ~steps["Province"].duplicated(keep=False)] if not steps.empty else steps
    if not best.empty and pol != 0:
        imp = best[best["Verdict"] == "Better"]["Province"].map(lambda p: C.PSHORT.get(p, p)).tolist()
        wor = best[best["Verdict"] == "Worse"]["Province"].map(lambda p: C.PSHORT.get(p, p)).tolist()
        flat = best[best["Verdict"] == "No clear change"]["Province"].map(lambda p: C.PSHORT.get(p, p)).tolist()
        parts = []
        if imp:
            parts.append(f"improved in {', '.join(imp)}")
        if wor:
            parts.append(f"got worse in {', '.join(wor)}")
        if flat:
            parts.append(f"showed no clear change in {', '.join(flat)}")
        if parts:
            C.takeaway(f"Over the surveys available, {ind.split(' (')[0].lower()} " + "; ".join(parts) + ".")

    # ---- 2. split by group
    dim = DIMS[split]
    if dim:
        st.markdown(f"##### 2. Trend by {split.lower()}: is the gap closing?")
        multi = rt.groupby("Province").size()
        provs = [p for p in C.PROV_ORDER if multi.get(p, 0) >= 2]
        if not provs:
            C.no_data("No province has two rounds for this indicator.")
        else:
            prov = C.side().radio("Split chart: province", provs, horizontal=True, key="tr_prov", format_func=lambda p: C.PSHORT.get(p, p))
            gr = C.ind_rate(ind, ["Survey", dim])
            gr = gr.assign(Survey=gr["Survey"].astype(str), **{dim: gr[dim].astype(str)}) if not gr.empty else gr
            if not gr.empty:
                gr["Year"] = gr["Survey"].map(_year)
                gr["Province"] = gr["Survey"].map(C.survey_province)
                gr = gr[gr["Province"] == prov]
            if gr.empty or gr["Survey"].nunique() < 2:
                C.no_data(f"Not enough data by {split.lower()} for {prov} (e.g. sex is not recorded for this indicator in every round).")
            else:
                colors = C.AREA_COLORS if dim == "Area" else C.WEALTH_COLORS if dim == "Wealth" else C.SEX_COLORS
                x, y = st.columns(2)
                with x:
                    _line(gr, f"{C.PSHORT.get(prov, prov)}: {ind.split(' (')[0]} by {split.lower()}", dim, colors, unit, show_ci, key="tr2")
                with y:
                    hi_g, lo_g = GAP[dim]
                    pv = gr.pivot_table(index=["Survey", "Year"], columns=dim, values=["value", "lo", "hi"]).reset_index().sort_values("Year")
                    if ("value", hi_g) in pv.columns and ("value", lo_g) in pv.columns:
                        gap = pv[("value", hi_g)] - pv[("value", lo_g)]
                        se = np.sqrt(((pv[("hi", hi_g)] - pv[("lo", hi_g)]) / 3.92) ** 2 + ((pv[("hi", lo_g)] - pv[("lo", lo_g)]) / 3.92) ** 2)
                        g2 = pd.DataFrame({"Year": pv["Year"].values, "Survey": pv["Survey"].values, "gap": gap.values, "se": se.values})
                        fig = go.Figure(go.Bar(x=g2["Year"], y=g2["gap"], marker_color="#0B5FA5",
                                               error_y=dict(type="data", array=1.96 * g2["se"], thickness=1.2, width=4) if show_ci else None,
                                               text=[f"{v:+.1f}" for v in g2["gap"]], textposition="inside", insidetextanchor="start", textfont=dict(color="#fff", size=13),
                                               customdata=g2["Survey"], hovertemplate="%{customdata}<br>gap %{y:+.1f}<extra></extra>"))
                        fig.add_hline(y=0, line_color="#9FB0C3")
                        fig.update_xaxes(tickmode="array", tickvals=g2["Year"], ticktext=g2["Survey"], tickangle=0, title="")
                        fig.update_yaxes(title=f"{hi_g} minus {lo_g} ({'pp' if unit == '%' else unit}, weighted)")
                        fig.update_layout(title=f"Gap: {hi_g.lower()} minus {lo_g.lower()}", showlegend=False)
                        C.style(fig, 460, legend=False)
                        C.show(fig, key="tr3")
                        first, last = g2["gap"].iloc[0], g2["gap"].iloc[-1]
                        trend = "narrowed" if abs(last) < abs(first) - 1 else "widened" if abs(last) > abs(first) + 1 else "stayed about the same"
                        st.caption(f"In {prov} the {hi_g.lower()}–{lo_g.lower()} gap {trend}: {first:+.1f} in {g2['Survey'].iloc[0]} → {last:+.1f} in "
                                   f"{g2['Survey'].iloc[-1]}. A bar near 0 means no gap.")
                    else:
                        C.no_data(f"{hi_g} or {lo_g} group missing for {prov}.")

    # ---- 3. all indicators for one province
    st.markdown(f"##### {3 if dim else 2}. Everything that changed in one province")
    multi_p = [p for p in C.PROV_ORDER if p in C.get_filters()["provinces"] and p != "Gilgit-Baltistan"]
    if not multi_p:
        return C.no_data("Select a province with at least two survey rounds in the sidebar.")
    c1, c2 = st.columns([1.4, 1])
    with c1:
        prov3 = C.side().radio("All changes: province", multi_p, horizontal=True, key="tr_prov3", format_func=lambda p: C.PSHORT.get(p, p))
    with c2:
        cat3 = C.side().selectbox("All changes: topic", ["All topics"] + cats, key="tr_cat3")
    rows = []
    for k in keys:
        if cat3 != "All topics" and _cat(k) != cat3:
            continue
        u_ = C.IND[k][2]
        if u_ != "%":
            continue
        r = C.ind_rate(k, "Survey")
        if r.empty:
            continue
        r = r.assign(Survey=r["Survey"].astype(str))
        r = r[r["Survey"].map(C.survey_province) == prov3]
        if r["Survey"].nunique() < 2:
            continue
        r["Year"] = r["Survey"].map(_year)
        r = r.sort_values("Year")
        f_, l_ = r.iloc[0], r.iloc[-1]
        d = l_["value"] - f_["value"]
        se = np.sqrt(_se(f_) ** 2 + _se(l_) ** 2)
        p_ = C.IND[k][3]
        sig = se > 0 and abs(d / se) >= 1.96
        rows.append(dict(Indicator=k, change=d, good=(d * p_ > 0) if p_ else None, sig=sig, first=f_["Survey"], last=l_["Survey"], f=f_["value"], l=l_["value"], pol=p_))
    if not rows:
        return C.no_data(f"No % indicator has two rounds in {prov3} for these filters.")
    t = pd.DataFrame(rows).sort_values("change")
    clr = ["#C9D3DE" if not s else ("#546E7A" if p_ == 0 else (C.GOOD if g else C.BAD)) for s, g, p_ in zip(t["sig"], t["good"], t["pol"])]
    fig = go.Figure(go.Bar(x=t["change"], y=t["Indicator"], orientation="h", marker_color=clr,
                           text=[f"{v:+.1f}" for v in t["change"]], textposition="outside", cliponaxis=False,
                           customdata=np.c_[t["first"], t["f"].round(1), t["last"], t["l"].round(1)],
                           hovertemplate="%{y}<br>%{customdata[0]}: %{customdata[1]}%<br>%{customdata[2]}: %{customdata[3]}%<br>change %{x:+.1f} pp<extra></extra>"))
    fig.add_vline(x=0, line_color="#9FB0C3")
    fig.update_xaxes(title="Change in percentage points, first to latest survey (weighted)")
    fig.update_yaxes(title="", automargin=True)
    fig.update_layout(title=f"{C.PSHORT.get(prov3, prov3)}: change from {t['first'].mode()[0]} to {t['last'].mode()[0]}", showlegend=False)
    C.style(fig, max(420, 120 + 26 * len(t)), legend=False)
    C.show(fig, key="tr4")
    nb, nw, nn = int(((t["good"] == True) & t["sig"]).sum()), int(((t["good"] == False) & t["sig"] & (t["pol"] != 0)).sum()), int((~t["sig"]).sum())  # noqa: E712
    st.caption(f"Green = real improvement, red = real deterioration, light grey = change within the margin of error, dark grey = real change in a context indicator. "
               f"In {C.PSHORT.get(prov3, prov3)}: {nb} improved, {nw} got worse, {nn} showed no clear change. Only % indicators are shown.")

    with st.expander("Reading trends correctly"):
        st.markdown(
            "* **Same province only.** Each MICS covers one province, so a trend is the same province in a later round. Comparing Punjab 2017 with Sindh 2014 is not a trend.\n"
            "* **Survey years** are the year fieldwork started (Punjab 2017 = fieldwork Dec 2017 - Mar 2018). The full list with fieldwork months is on the Home page.\n"
            "* **Definitions are harmonised** across MICS4, MICS5 and MICS6 (e.g. water and sanitation follow the JMP 2017 ladder in every round). Some questions changed "
            "between rounds; indicators that were not asked in a round are left out rather than shown as zero.\n"
            "* **Margins of error** are approximate (effective sample size from the weights, no cluster correction), so treat borderline 'real change' results with care.\n"
            "* **Population weighting** does not affect single-province trends.")
