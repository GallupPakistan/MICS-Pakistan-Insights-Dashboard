import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as C

W_COL, M_COL = "#D1495B", "#0B5FA5"
REASONS = {"WB: Goes out without telling husband": "Goes out", "WB: Neglects the children": "Neglects kids",
           "WB: Argues with husband": "Argues", "WB: Refuses sex with husband": "Refuses sex", "WB: Burns the food": "Burns food"}


def _both():
    m = C.apply(C.load("men"), "men")
    w = C.apply(C.load("women"), "women")
    if m is None or m.empty or w is None:
        return None, None
    w = w[w["Survey"].isin(m["Survey"].unique())]   # only surveys where men were also interviewed
    return m, w


def _pair(m, w, col, by, scale=100.0):
    a, b = C.rate(w, col, by, scale=scale), C.rate(m, col, by, scale=scale)
    if a.empty or b.empty:
        return pd.DataFrame()
    a["Who"], b["Who"] = "Women 15-49", "Men 15-49"
    d = pd.concat([a, b])
    d[by] = d[by].astype(str)
    return d


def _grouped(d, by, title, key, order=None, height=420, ytitle="% (weighted)"):
    if d.empty:
        return C.no_data("Men were interviewed only in Balochistan 2019, KP 2019, Punjab 2017 and Sindh 2018. Select at least one of them in the sidebar.")
    f = go.Figure()
    for who, col in (("Women 15-49", W_COL), ("Men 15-49", M_COL)):
        g = d[d["Who"] == who]
        if order:
            g = g.set_index(by).reindex(order).reset_index()
        f.add_trace(go.Bar(x=g[by], y=g["value"], name=who, marker_color=col, text=g["value"].map(lambda v: "" if pd.isna(v) else f"{v:.0f}"),
                           textposition="outside", cliponaxis=False))
    f.update_layout(barmode="group", title=title, yaxis_title=ytitle, xaxis_title="")
    f.update_yaxes(range=[0, max(d["value"].max() * 1.2, 5)])
    C.style(f, height, legend_title="Group")
    C.show(f, key=key)


def render():
    _m = C.apply(C.load("men"), "men")
    _n = int(_m["Survey"].nunique()) if _m is not None and not _m.empty else 0
    C.page_header("Women vs men", "Where women and men aged 15-49 answer differently: schooling and attitudes to wife beating (surveys where men were interviewed)", ":material/wc:", badge=(str(_n), "surveys with men"))
    m, w = _both()
    if m is None:
        return C.no_data("No men's data for the current filters. Select Balochistan 2019, KP 2019, Punjab 2017 or Sindh 2018.")
    st.caption("Men were interviewed only in Balochistan 2019, KP 2019, Punjab 2017 and Sindh 2018, so only these surveys appear here. Women are limited to the same surveys.")
    wj, mj = C.rate(w, "wife_beating_any", "Province"), C.rate(m, "wife_beating_any", "Province")
    ws, ms = C.rate(w, "ever_school", "Province"), C.rate(m, "ever_school", "Province")
    pw = (w["wife_beating_any"].astype(float) * w["w"]).sum() / w.loc[w["wife_beating_any"].notna(), "w"].sum() * 100
    pm = (m["wife_beating_any"].astype(float) * m["w"]).sum() / m.loc[m["wife_beating_any"].notna(), "w"].sum() * 100
    sw = (w["ever_school"].astype(float) * w["w"]).sum() / w.loc[w["ever_school"].notna(), "w"].sum() * 100
    sm = (m["ever_school"].astype(float) * m["w"]).sum() / m.loc[m["ever_school"].notna(), "w"].sum() * 100
    c = st.columns(4)
    with c[0]:
        C.kpi("Men interviewed", f"{len(m):,}")
    with c[1]:
        C.kpi("Women say beating is justified", f"{pw:.1f}%", help="Women who think a husband is justified in beating his wife for at least one of five reasons.")
    with c[2]:
        C.kpi("Men say beating is justified", f"{pm:.1f}%", help="Same question asked to men.")
    with c[3]:
        C.kpi("Schooling gap (men minus women)", f"{sm - sw:+.1f} pp", unit="pp", help=f"Ever attended school: men {sm:.1f}%, women {sw:.1f}%.")
    C.takeaway(f"In the selected surveys {pw:.0f}% of women and {pm:.0f}% of men say a husband is justified in beating his wife for at least one reason. "
               f"{sm:.0f}% of men and {sw:.0f}% of women ever attended school.")
    st.markdown("---")
    r1 = st.columns(2)
    with r1[0]:
        d = _pair(m, w, "wife_beating_any", "Survey")
        _grouped(d, "Survey", "Beating justified (any reason): women vs men", "mn1", order=[s for s in C.survey_order(list(d["Survey"].unique()))] if not d.empty else None)
    with r1[1]:
        d = _pair(m, w, "ever_school", "Survey")
        _grouped(d, "Survey", "Ever attended school: women vs men", "mn2", order=[s for s in C.survey_order(list(d["Survey"].unique()))] if not d.empty else None)
    r2 = st.columns(2)
    with r2[0]:
        rows = []
        for col, nm in REASONS.items():
            a = (w[col].astype(float) * w["w"]).sum() / w.loc[w[col].notna(), "w"].sum() * 100 if w[col].notna().any() else None
            b = (m[col].astype(float) * m["w"]).sum() / m.loc[m[col].notna(), "w"].sum() * 100 if m[col].notna().any() else None
            rows += [dict(Reason=nm, Who="Women 15-49", value=a), dict(Reason=nm, Who="Men 15-49", value=b)]
        _grouped(pd.DataFrame(rows), "Reason", "Which reasons are accepted most", "mn3", order=list(REASONS.values()))
    with r2[1]:
        d = _pair(m, w, "wife_beating_any", "AgeGroup")
        _grouped(d, "AgeGroup", "Beating justified, by age group", "mn4", order=sorted(d["AgeGroup"].unique()) if not d.empty else None)
    r3 = st.columns(2)
    with r3[0]:
        d = _pair(m, w, "wife_beating_any", "Wealth")
        _grouped(d, "Wealth", "Beating justified, by wealth quintile", "mn5", order=[x for x in C.WEALTH if x in set(d["Wealth"])] if not d.empty else None)
    with r3[1]:
        d = _pair(m, w, "wife_beating_any", "Area")
        _grouped(d, "Area", "Beating justified, urban vs rural", "mn6")
    r4 = st.columns(2)
    with r4[0]:
        d = _pair(m, w, "wife_beating_any", "Education")
        _grouped(d, "Education", "Beating justified, by own education", "mn7", order=[x for x in C.EDU if x in set(d["Education"])] if not d.empty else None)
    with r4[1]:
        d = _pair(m, w, "ever_school", "Wealth")
        _grouped(d, "Wealth", "Ever attended school, by wealth quintile", "mn8", order=[x for x in C.WEALTH if x in set(d["Wealth"])] if not d.empty else None)
    st.caption("Both groups are weighted with their own survey weights. Attitude questions ask whether a husband is justified in beating his wife for any of five reasons.")
