import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as C

TABLE_CAT = {"hh": "Households & services", "women": "Women & maternal health", "men": "Men", "children": "Child health", "births": "Child mortality",
             "siblings": "Child mortality", "c5to17": "Children 5-17", "nets": "Households & services"}


# international reference values (only where a clear benchmark exists); everything else has no default target
REF_TARGETS = {
    "Improved drinking water": 100.0, "Improved sanitation": 100.0, "Electricity": 100.0, "Clean cooking fuel / stove": 100.0,
    "Handwashing water available": 100.0, "Open defecation": 0.0,
    "BCG: at least one dose (12-35 months)": 90.0, "Polio: at least one dose (12-35 months)": 90.0,
    "Penta / DPT: at least one dose (12-35 months)": 90.0, "Measles: at least one dose (12-35 months)": 90.0,
    "Skilled birth attendant": 90.0, "Wasting (weight-for-height < -2 SD)": 5.0,
}

def _cat(k):
    if "dose" in k:
        return "Immunisation"
    if any(x in k for x in ("Stunting", "Wasting", "Underweight", "Vitamin")):
        return "Nutrition"
    if any(x in k for x in ("Diarrhoea", "Fever", "ORS")):
        return "Child illness"
    if any(x in k for x in ("water", "sanitation", "Open defecation", "Handwashing")):
        return "Water & sanitation"
    if k in ("Television", "Refrigerator", "Mobile phone in household", "Motorcycle / scooter", "Bank account in household", "Rented dwelling"):
        return "Assets"
    return TABLE_CAT.get(C.IND[k][0], "Other")


def _spark(vals, color):
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    pts = [(6 + i * 68 / (len(vals) - 1), 24 - (v - lo) / rng * 18) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return (f"<svg width='82' height='30'><polyline fill='none' stroke='{color}' stroke-width='2' points='{line}'/>"
            f"<circle cx='{pts[0][0]:.1f}' cy='{pts[0][1]:.1f}' r='3' fill='{color}'/><circle cx='{pts[-1][0]:.1f}' cy='{pts[-1][1]:.1f}' r='3' fill='{color}'/></svg>")


def render():
    C.page_header("KPI scorecard", "Every indicator at a glance: what went up, what went down, and whether that is better or worse", ":material/fact_check:")
    provs = [p for p in C.PROV_ORDER if p in C.get_filters()["provinces"]]
    surveys = {p: C.survey_order([s for s in C.all_surveys() if C.survey_province(s) == p]) for p in provs}
    provs = [p for p in provs if len(surveys[p]) >= 2]
    if not provs:
        return C.no_data("Select a province with at least two surveys (Punjab, Sindh, KP, Balochistan or Gilgit-Baltistan) in the sidebar.")
    c = st.columns(3)
    with c[0]:
        prov = C.side().selectbox("Province", provs, key="sc_prov")
    sv = surveys[prov]
    with c[1]:
        first = C.side().selectbox("From survey", sv[:-1], index=0, key="sc_a")
    with c[2]:
        last = C.side().selectbox("To survey", [s for s in sv if C.survey_order([first, s]).index(s) > 0], index=None, placeholder="latest", key="sc_b") or sv[-1]
    rows, rates = [], {}
    for k, v in C.IND.items():
        r = C.ind_rate(k, "Survey")
        if r is None or r.empty:
            continue
        r = r.copy()
        r["Survey"] = r["Survey"].astype(str)
        rates[k] = r.set_index("Survey")
        r = rates[k][rates[k].index.isin(sv)]
        if first not in r.index or last not in r.index:
            continue
        series = [r.loc[s_, "value"] for s_ in sv if s_ in r.index]
        se = lambda s_: (r.loc[s_, "hi"] - r.loc[s_, "lo"]) / 3.92
        tot = (se(first) ** 2 + se(last) ** 2) ** 0.5
        ch = r.loc[last, "value"] - r.loc[first, "value"]
        sig = bool(abs(ch) / tot > 1.96) if tot == tot and tot > 0 else True   # unknown error -> do not hide the change
        rows.append(dict(k=k, cat=_cat(k), unit=v[2], pol=v[3], a=r.loc[first, "value"], b=r.loc[last, "value"], ch=ch, sig=sig, series=series))
    if not rows:
        return C.no_data(f"No indicator is available in both {first} and {last} for the current filters.")
    t = pd.DataFrame(rows)
    thr = 0.5
    t["status"] = [("Context" if p == 0 else "Stable" if (abs(ch) < thr or not sg) else "Better" if ch * p > 0 else "Worse") for ch, p, sg in zip(t["ch"], t["pol"], t["sig"])]
    k = st.columns(4)
    with k[0]:
        C.kpi("Indicators tracked", f"{len(t)}", unit="")
    with k[1]:
        C.kpi("Better", f"{(t['status'] == 'Better').sum()}", unit="")
    with k[2]:
        C.kpi("Worse", f"{(t['status'] == 'Worse').sum()}", unit="")
    with k[3]:
        C.kpi("Real change / within margin", f"{int(t['sig'].sum())} / {int((~t['sig']).sum())}", unit="", help="A change is 'real' when the confidence intervals of the two surveys do not overlap enough to be explained by sampling error (approx. 95%).")
    t_all = t.copy()
    bt, wt = t_all[t_all["status"] == "Better"].sort_values("ch", key=abs, ascending=False), t_all[t_all["status"] == "Worse"].sort_values("ch", key=abs, ascending=False)
    txt = (f"Between **{first}** and **{last}**, **{len(bt)}** of {len(t_all)} indicators got better and **{len(wt)}** got worse; "
           f"**{int((t_all['status'] == 'Stable').sum())}** showed no change beyond the margin of error.")
    if len(bt):
        txt += f" Biggest improvement: **{bt.iloc[0]['k']}** ({bt.iloc[0]['ch']:+.1f} {'points' if bt.iloc[0]['unit'] == '%' else bt.iloc[0]['unit']})."
    if len(wt):
        txt += f" Biggest decline: **{wt.iloc[0]['k']}** ({wt.iloc[0]['ch']:+.1f} {'points' if wt.iloc[0]['unit'] == '%' else wt.iloc[0]['unit']})."
    st.info(txt, icon=":material/summarize:")
    tg_ind = t_all[(t_all["pol"] != 0) & (t_all["unit"] == "%")]
    tdf = pd.DataFrame({"Indicator": tg_ind["k"].values, "Target (%)": [REF_TARGETS.get(k_, np.nan) for k_ in tg_ind["k"]]})
    with st.expander("Targets (reference values pre-filled; edit to use your own)"):
        st.caption("Pre-filled only where an international benchmark exists: universal access (100%) for water, sanitation, electricity, clean fuel and "
                   "handwashing (SDG 6 and 7), 0% open defecation (SDG 6.2), 90% vaccine coverage (Immunization Agenda 2030), 90% skilled birth "
                   "attendance, wasting below 5% (World Health Assembly 2025 target). Blank = no target shown.")
        ed = st.data_editor(tdf, hide_index=True, use_container_width=True if False else None, disabled=["Indicator"], key="sc_targets",
                            column_config={"Target (%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=1)})
    targets = {k_: float(v_) for k_, v_ in zip(ed["Indicator"], ed["Target (%)"]) if pd.notna(v_)}
    f = st.columns(2)
    with f[0]:
        cats = C.side().multiselect("Table: category", sorted(t["cat"].unique()), default=sorted(t["cat"].unique()), key="sc_cat")
    with f[1]:
        stat = C.side().multiselect("Table: status", ["Better", "Worse", "Stable", "Context"], default=["Better", "Worse", "Stable", "Context"], key="sc_st")
    t = t[t["cat"].isin(cats) & t["status"].isin(stat)].sort_values(["cat", "k"])
    COL = {"Better": "#2E7D32", "Worse": "#C0392B", "Stable": "#7A8CA3", "Context": "#7A8CA3"}
    DOT = {"Better": "🟢", "Worse": "🔴", "Stable": "⚪", "Context": "⚪"}
    css = ("<style>.sc{width:100%;border-collapse:collapse;font-size:14px;background:#fff;border:1px solid #DCE4EE}"
           ".sc th{background:#0B1F3A;color:#fff;text-align:center;padding:10px;font-weight:700}.sc th:first-child{text-align:left}"
           ".sc td{padding:9px 10px;border-top:1px solid #E3E9F0;text-align:center}.sc td:first-child{text-align:left}"
           ".sc small{color:#7A8CA3;display:block}</style>")
    body = ""
    for r in t.itertuples():
        u = "" if r.unit == "%" else f" {r.unit}"
        chs = f"{r.ch:+.1f} {'pp' if r.unit == '%' else r.unit}"
        arrow = "▲" if r.ch >= thr else "▼" if r.ch <= -thr else "▬"
        col = COL[r.status]
        tg_ = targets.get(r.k)
        if tg_ is None or r.unit != "%":
            tgs = "–"
        else:
            reached = (r.b >= tg_) if r.pol > 0 else (r.b <= tg_)
            tgs = f"{tg_:.0f}% · " + ("<span style='color:#2E7D32'>✔ reached</span>" if reached else f"{abs(tg_ - r.b):.1f} pp to go")
        body += (f"<tr><td>{r.k}<small>{r.cat}</small></td><td>{r.a:.1f}{'%' if r.unit == '%' else u}</td><td>{r.b:.1f}{'%' if r.unit == '%' else u}</td>"
                 f"<td>{_spark(r.series, col)}</td><td>{chs}</td><td>{'✔ real' if r.sig else '<span style=\"color:#7A8CA3\">within margin</span>'}</td><td>{DOT[r.status]} {r.status}</td><td style='color:{col};font-size:16px'>{arrow}</td><td>{tgs}</td></tr>")
    st.markdown(css + f"<table class='sc'><tr><th>Indicator</th><th>{first}</th><th>{last}</th><th>Trend</th><th>Change</th><th>Real change?</th><th>Status</th><th>Direction</th><th>Target / gap</th></tr>{body}</table>",
                unsafe_allow_html=True)
    st.caption("▲ = the value rose, ▼ = it fell. Colour says whether that is good: green = better, red = worse, grey = no clear better / worse (for example female-headed households) "
               "or a change under 0.5 points or one that is within the sampling margin of error. The trend line covers every survey of the province. Change is in percentage points (pp). Years differ by survey, so read changes within one province only.")
    C.show_table(t.drop(columns="series").round(2), "kpi_scorecard")

    st.markdown("---")
    st.markdown("##### Trends and movers")
    pc = t_all[t_all["unit"] == "%"].copy()
    GOOD, BAD, GREY = "#2E7D32", "#C0392B", "#7A8CA3"
    cc = lambda r: GREY if r.status in ("Context", "Stable") else (GOOD if r.status == "Better" else BAD)
    g1 = st.columns(2)
    with g1[0]:   # 1 slope chart
        fg = go.Figure()
        for r in pc.itertuples():
            fg.add_trace(go.Scatter(x=[first, last], y=[r.a, r.b], mode="lines+markers", line=dict(color=cc(r), width=2), marker=dict(size=7), name=r.k, showlegend=False,
                                    hovertemplate=r.k + "<br>%{x}: %{y:.1f}%<extra></extra>"))
        fg.update_layout(title=f"{first} to {last}: all % indicators", yaxis_title="% (weighted)", xaxis_title="")
        C.style(fg, 520, legend=False, bottom=40)
        C.show(fg, key="sc_slope")
    with g1[1]:   # 2 biggest movers
        mv = t_all[t_all["status"].isin(["Better", "Worse"])].copy()
        mv["size"] = mv["ch"].abs()
        top = pd.concat([mv[mv["status"] == "Better"].nlargest(5, "size"), mv[mv["status"] == "Worse"].nlargest(5, "size")]).sort_values("ch")
        if top.empty:
            C.no_data("No clear better / worse movers between these two surveys.")
        else:
            fm = go.Figure(go.Bar(y=[x[:42] for x in top["k"]], x=top["ch"], orientation="h", marker_color=[GOOD if x == "Better" else BAD for x in top["status"]],
                                  text=[f"{v:+.1f}" for v in top["ch"]], textposition="outside", cliponaxis=False))
            fm.add_vline(x=0, line_color="#444")
            fm.update_layout(title="Biggest movers: 5 most improved and 5 most worsened", xaxis_title="change (points)", yaxis_title="")
            m = max(top["ch"].abs().max(), 1) * 1.3
            fm.update_xaxes(range=[-m, m])
            C.style(fm, 520, legend=False, bottom=50)
            C.show(fm, key="sc_movers")
    # 3 category cards
    cards = ""
    for cat, g in t_all.groupby("cat"):
        b, w = int((g["status"] == "Better").sum()), int((g["status"] == "Worse").sum())
        col = GOOD if b > w else BAD if w > b else GREY
        cards += (f"<div style='flex:1 1 160px;background:#fff;border:1px solid #DCE4EE;border-left:4px solid {col};border-radius:10px;padding:10px 14px'>"
                  f"<div style='font-size:12px;color:#5B6B7F'>{cat}</div><div style='font-size:20px;font-weight:700;color:{col}'>{b} better · {w} worse</div>"
                  f"<div style='font-size:12px;color:#7A8CA3'>{len(g)} indicators</div></div>")
    st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:12px;margin:8px 0 14px'>{cards}</div>", unsafe_allow_html=True)
    # 5 gap table: is the urban-rural gap widening or narrowing?
    rows = []
    for r in pc.itertuples():
        ra = C.ind_rate(r.k, "Survey")
        rg = C.ind_rate(r.k, ["Survey", "Area"]) if "Area" in C.ind_dims(r.k) else None
        if rg is None or rg.empty:
            continue
        rg["Survey"] = rg["Survey"].astype(str)
        def gap(sv_):
            x = rg[rg["Survey"] == sv_].set_index(rg[rg["Survey"] == sv_]["Area"].astype(str))["value"]
            return x["Urban"] - x["Rural"] if "Urban" in x.index and "Rural" in x.index else None
        a_, b_ = gap(first), gap(last)
        if a_ is not None and b_ is not None:
            rows.append((r.k, a_, b_, b_ - a_))
    g2 = st.columns(1)[0]
    if rows:
        body = ""
        for k_, a_, b_, d_ in sorted(rows, key=lambda x: -abs(x[3])):
            word, col, ar = ("Widening", BAD, "▲") if d_ >= 0.5 else ("Narrowing", GOOD, "▼") if d_ <= -0.5 else ("Unchanged", GREY, "▬")
            if abs(b_) < abs(a_) - 0.5:
                word, col, ar = "Narrowing", GOOD, "▼"
            elif abs(b_) > abs(a_) + 0.5:
                word, col, ar = "Widening", BAD, "▲"
            body += f"<tr><td>{k_}</td><td>{a_:+.1f} pp</td><td>{b_:+.1f} pp</td><td style='color:{col};font-weight:600'>{word}</td><td style='color:{col};font-size:16px'>{ar}</td></tr>"
        st.markdown(f"<table class='sc'><tr><th>Urban minus rural gap</th><th>{first}</th><th>{last}</th><th>Gap is</th><th>Direction</th></tr>{body}</table>", unsafe_allow_html=True)
        st.caption("Gap = urban value minus rural value, in percentage points. 'Narrowing' means rural areas are catching up (or the urban lead shrank); 'widening' means the difference grew.")
    else:
        C.no_data("No indicator has an urban / rural split in both surveys.")
    # 8 heat strip
    sv_cols = [s_ for s_ in sv]
    hs = {}
    for r in pc.itertuples():
        rr = C.ind_rate(r.k, "Survey")
        if rr is None or rr.empty:
            continue
        rr = rr.assign(Survey=rr["Survey"].astype(str)).set_index("Survey")["value"]
        hs[r.k] = [(rr[s_] - rr[sv_cols[i - 1]]) * (r.pol or 0) if i and s_ in rr.index and sv_cols[i - 1] in rr.index else None for i, s_ in enumerate(sv_cols)]
    if hs:
        pv = pd.DataFrame(hs, index=sv_cols).T.astype(float)
        pv = pv.iloc[:, 1:]
        z = pv.values
        fh = go.Figure(go.Heatmap(z=z, x=list(pv.columns), y=[k_[:40] for k_ in pv.index], colorscale=[[0, BAD], [0.5, "#F2F2F2"], [1, GOOD]], zmid=0, xgap=2, ygap=2,
                                  text=np.where(np.isnan(z), "", np.vectorize(lambda v: f"{v:+.0f}" if not np.isnan(v) else "")(z)), texttemplate="%{text}",
                                  colorbar=dict(title=dict(text="points better (+) / worse (-)", side="right"), thickness=14),
                                  hovertemplate="%{y}<br>%{x}: %{z:+.1f} points vs previous survey<extra></extra>"))
        fh.update_layout(title="Heat strip: change vs previous survey", yaxis=dict(autorange="reversed"))
        C.style(fh, max(420, 90 + 28 * len(pv)), legend=False, bottom=60)
        C.show(fh, key="sc_strip")
        st.caption("Slope chart and heat strip: green = better, red = worse, grey = no clear better / worse direction.")

    st.markdown("---")
    st.markdown("##### Progress towards a target and province ranking")
    g3 = st.columns(2)
    with g3[0]:   # target progress
        cand = [k_ for k_ in pc[pc["pol"] != 0]["k"] if k_ in targets]
        dflt = [k_ for k_ in ("Improved sanitation", "Skilled birth attendant", "Measles: at least one dose (12-35 months)", "Wasting (weight-for-height < -2 SD)", "Electricity") if k_ in cand]
        sel = C.side().multiselect("Indicators for target tracking", cand, default=dflt, key="sc_tg_k")
        st.caption("Targets come from the 'Targets' table above (indicators without a target are not listed).")
        rows_ = pc[pc["k"].isin(sel)]
        if rows_.empty:
            C.no_data("Pick at least one indicator.")
        else:
            ft = go.Figure()
            for i, r in enumerate(rows_.itertuples()):
                tgt = targets[r.k]
                done = (r.b >= tgt) if r.pol > 0 else (r.b <= tgt)
                col = GOOD if done else ("#E8A317" if r.status == "Better" else BAD if r.status == "Worse" else GREY)
                ft.add_trace(go.Bar(y=[r.k[:38]], x=[r.b], orientation="h", marker_color=col, showlegend=False, text=f"{r.b:.0f}% (was {r.a:.0f}%)", textposition="auto",
                                    hovertemplate=f"{r.k}<br>{first}: {r.a:.1f}%<br>{last}: {r.b:.1f}%<br>target {tgt}%<extra></extra>"))
                ft.add_shape(type="line", x0=tgt, x1=tgt, y0=i - .42, y1=i + .42, line=dict(color="#0B1F3A", width=3))
            ft.update_layout(title=f"Latest value ({last}) vs target (dark marker)", xaxis_title="% (weighted)", yaxis_title="", barmode="overlay")
            ft.update_xaxes(range=[0, 100])
            ft.update_yaxes(autorange="reversed")
            C.style(ft, max(380, 110 + 55 * len(rows_)), legend=False, bottom=50)
            C.show(ft, key="sc_target")
            st.caption("Green = target reached, amber = improving but not there yet, red = moving the wrong way, grey = no clear change. Pre-filled targets are international reference values (see the Targets table).")
    with g3[1]:   # province rank
        ik = C.side().selectbox("Indicator for province ranking", list(pc["k"]), index=0, key="sc_rank_k")
        rr = C.ind_rate(ik, "Survey")
        pol = C.IND[ik][3]
        rows2 = []
        if rr is not None and not rr.empty:
            rr = rr.assign(Survey=rr["Survey"].astype(str)).set_index("Survey")["value"]
            for pv_ in C.get_filters()["provinces"]:
                ss = [s_ for s_ in C.survey_order([x for x in rr.index if C.survey_province(x) == pv_])]
                if len(ss) >= 2:
                    rows2.append(dict(p=pv_, s0=ss[0], s1=ss[-1], v0=rr[ss[0]], v1=rr[ss[-1]]))
        if len(rows2) < 2:
            C.no_data("Need at least two provinces with two surveys each (check the province filter).")
        else:
            d = pd.DataFrame(rows2)
            asc = pol < 0
            d["r0"] = d["v0"].rank(ascending=asc, method="min").astype(int)
            d["r1"] = d["v1"].rank(ascending=asc, method="min").astype(int)
            body = ""
            for r in d.sort_values("r1").itertuples():
                mv_ = r.r0 - r.r1
                ar, col = ("▲", GOOD) if mv_ > 0 else ("▼", BAD) if mv_ < 0 else ("▬", GREY)
                body += (f"<tr><td>{r.p}</td><td>#{r.r0}<small>{r.s0}: {r.v0:.1f}%</small></td><td>#{r.r1}<small>{r.s1}: {r.v1:.1f}%</small></td>"
                         f"<td style='color:{col};font-size:16px'>{ar} {abs(mv_) if mv_ else ''}</td></tr>")
            st.markdown(f"<table class='sc'><tr><th>Province</th><th>Rank, first survey</th><th>Rank, latest survey</th><th>Rank change</th></tr>{body}</table>", unsafe_allow_html=True)
            st.caption("Rank 1 = best" + (" (lowest value)" if asc else " (highest value)") + ". ▲ = moved up the ranking. Each province's own first and latest survey are used, "
                       "so the years differ between provinces.")

    st.markdown("---")
    st.markdown("##### All provinces side by side (latest survey of each province)")
    latest = {}
    for pv_ in C.PROV_ORDER:
        if pv_ in C.get_filters()["provinces"]:
            ss_ = C.survey_order([s_ for s_ in C.all_surveys() if C.survey_province(s_) == pv_])
            if ss_:
                latest[pv_] = ss_[-1]
    if len(latest) < 2:
        C.no_data("Set Province to All in the sidebar to compare provinces.")
    else:
        cats_p = C.side().multiselect("Province view: category", sorted(t_all["cat"].unique()), default=sorted(t_all["cat"].unique()), key="sc_pcat")
        body = ""
        csv_rows = []
        for r in t_all[t_all["cat"].isin(cats_p)].sort_values(["cat", "k"]).itertuples():
            if r.k not in rates:
                continue
            vals = {pv_: (rates[r.k].loc[sv_, "value"] if sv_ in rates[r.k].index else None) for pv_, sv_ in latest.items()}
            have = {k_: v_ for k_, v_ in vals.items() if v_ is not None and v_ == v_}
            if len(have) < 2:
                continue
            best = (max(have, key=have.get) if r.pol > 0 else min(have, key=have.get)) if r.pol != 0 else None
            worst = (min(have, key=have.get) if r.pol > 0 else max(have, key=have.get)) if r.pol != 0 else None
            u = "%" if r.unit == "%" else f" {r.unit}"
            cells = ""
            for pv_ in latest:
                v_ = vals[pv_]
                if v_ is None or v_ != v_:
                    cells += "<td style='color:#9AA5B1'>not asked</td>"
                    continue
                sty = "background:#DFF3E4;color:#1B5E20;font-weight:700" if pv_ == best else "background:#FBE3E0;color:#922B21" if pv_ == worst else ""
                cells += f"<td style='{sty}'>{v_:.1f}{u}</td>"
            spread = max(have.values()) - min(have.values())
            body += f"<tr><td>{r.k}<small>{r.cat}</small></td>{cells}<td>{spread:.1f}</td></tr>"
            csv_rows.append(dict(Indicator=r.k, **{f"{pv_} ({latest[pv_]})": vals[pv_] for pv_ in latest}, Spread=spread))
        head = "".join(f"<th>{pv_}<small style='color:#B8C7DA;display:block;font-weight:400'>{sv_}</small></th>" for pv_, sv_ in latest.items())
        st.markdown(f"<table class='sc'><tr><th>Indicator</th>{head}<th>Spread</th></tr>{body}</table>", unsafe_allow_html=True)
        st.caption("Green = best province for that indicator, red = weakest (indicators with no better / worse direction are not coloured). Spread = highest minus lowest. "
                   "Each province uses its own latest survey, so the years differ.")
        C.show_table(pd.DataFrame(csv_rows).round(2), "provinces_side_by_side", "Show / download the province table")
