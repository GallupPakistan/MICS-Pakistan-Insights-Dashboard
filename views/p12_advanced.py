import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import common as C
import extras as X


def render():
    C.page_header("Inequality & district rankings", "How unequal is an outcome across wealth groups, and which districts do best and worst", ":material/leaderboard:")
    tabs = st.tabs(["Inequality indices", "District rankings"])
    keys = list(C.IND)

    with tabs[0]:
        ind = st.selectbox("Indicator", keys, index=keys.index("Skilled birth attendant"), key="ineq_ind")
        table, col, unit, pol, where, desc = C.IND[ind]
        st.caption(desc)
        t = C.inequality(ind)
        if t.empty:
            C.no_data("Not enough records in every wealth quintile for this indicator and these filters (keep all wealth quintiles selected).")
        else:
            order = C.survey_order(t["Survey"])
            cm = C.survey_colors(order)
            t = t.set_index("Survey").loc[order].reset_index()
            c1, c2, c3 = st.columns(3)
            with c1:
                C.kpi("Surveys with an index", f"{len(t)}")
            with c2:
                C.kpi("Average slope index", f"{t['SII'].mean():+.1f}" + (" pp" if unit == "%" else " per 1,000"), help="Slope index of inequality: absolute gap between the richest and poorest end of the wealth ranking, using all five quintiles.")
            with c3:
                C.kpi("Average concentration index", f"{t['CI'].mean():+.3f}", help="Between -1 and +1. Positive = the outcome is concentrated among richer households, negative = among poorer ones, 0 = equal.")
            a, b = st.columns(2)
            with a:
                t["label"] = t["SII"].map(lambda v: f"{v:+.1f}")
                f = px.bar(t, x="Survey", y="SII", color="Survey", color_discrete_map=cm, text="label", category_orders={"Survey": order},
                           title="Slope index of inequality (" + ("percentage points" if unit == "%" else "deaths per 1,000 births") + ")", labels={"SII": "richest minus poorest, fitted on all quintiles (" + ("pp" if unit == "%" else "per 1,000") + ")"}, hover_data={"poorest": ":.1f", "richest": ":.1f", "n": ":,", "label": False})
                f.update_traces(textposition="outside", cliponaxis=False, opacity=1)
                f.add_hline(y=0, line_color="#444")
                m = max(abs(t["SII"]).max(), 1) * 1.3
                f.update_yaxes(range=[-m, m] if (t["SII"] < 0).any() else [0, m])
                f.update_xaxes(tickangle=-30, title=None)
                C.style(f, 430, legend=False, bottom=20)
                C.show(f, key="ineq1")
            with b:
                t["lab2"] = t["CI"].map(lambda v: f"{v:+.2f}")
                f = px.bar(t, x="Survey", y="CI", color="Survey", color_discrete_map=cm, text="lab2", category_orders={"Survey": order},
                           title="Concentration index (-1 to +1)", labels={"CI": "concentration index"}, hover_data={"RII": ":.2f", "n": ":,", "lab2": False})
                f.update_traces(textposition="outside", cliponaxis=False, opacity=1)
                f.add_hline(y=0, line_color="#444")
                m = max(abs(t["CI"]).max(), 0.05) * 1.35
                f.update_yaxes(range=[-m, m] if (t["CI"] < 0).any() else [0, m])
                f.update_xaxes(tickangle=-30, title=None)
                C.style(f, 430, legend=False, bottom=20)
                C.show(f, key="ineq2")
            st.caption("Bars are coloured by survey (province colour, older surveys lighter). Positive values mean better-off households have more of this outcome. "
                       "For 'bad' outcomes (e.g. stunting) a negative value means the burden falls on the poor. RII = ratio of the fitted value at the richest end to the poorest end.")
            C.show_table(t.drop(columns=["label", "lab2"], errors="ignore").round(3), "inequality_indices")

    with tabs[1]:
        c = st.columns([3, 2, 2, 2])
        with c[0]:
            ind2 = st.selectbox("Indicator", keys, index=keys.index("Improved sanitation"), key="dist_ind")
        df, col, unit, pol, where, desc = C.ind_data(ind2)
        have = C.survey_order(df["Survey"].astype(str).unique()) if df is not None and not df.empty else []
        if not have:
            C.no_data()
            return
        with c[1]:
            sv = st.selectbox("Survey", have, key="dist_sv")
        with c[2]:
            topn = st.slider("Districts shown", 5, 40, 20, key="dist_n")
        with c[3]:
            minn = st.slider("Minimum records per district", 20, 500, 100, step=10, key="dist_min")
        d = df[df["Survey"].astype(str) == sv]
        r = C.rate(d, col, "District", scale=C.ind_scale(unit), where=where, min_n=minn)
        if r.empty:
            C.no_data("No district has enough records. Lower the minimum or choose another survey.")
        else:
            r["District"] = r["District"].astype(str)
            r = r.sort_values("value", ascending=(pol < 0))   # best first
            best = r.head(topn)
            worst = r.tail(topn)
            show = r if len(r) <= 2 * topn else pd.concat([best, worst]).drop_duplicates("District")
            show = show.sort_values("value", ascending=True)
            prov = C.survey_province(sv)
            avg = (d[col].astype(float) * d["w"]).sum() / d["w"].sum() * C.ind_scale(unit)
            show["err_p"], show["err_m"] = show["hi"] - show["value"], show["value"] - show["lo"]
            show["label"] = show["value"].map(lambda v: C.fmt(v, unit, 1))
            f = go.Figure(go.Bar(y=show["District"], x=show["value"], orientation="h", marker_color=C.PROV_COLORS.get(prov, "#0B5FA5"), text=show["label"],
                                 textposition="outside", cliponaxis=False, error_x=dict(type="data", symmetric=False, array=show["err_p"], arrayminus=show["err_m"], color="#444", thickness=1.2),
                                 customdata=show[["n"]], hovertemplate="%{y}<br>%{x:.1f}<br>n = %{customdata[0]:,}<extra></extra>", name="District value (bar) with 95% CI (line)"))
            f.add_vline(x=avg, line_dash="dash", line_color="#444", annotation_text=f"survey average {C.fmt(avg, unit, 1)}", annotation_position="top")
            f.update_layout(title=f"{ind2}: districts of {sv}" + (" (best and worst shown)" if len(r) > 2 * topn else ""), xaxis_title=C.unit_axis(unit))
            f.update_xaxes(range=[0, max(show["hi"].max(), avg) * 1.15])
            C.style(f, max(460, 40 + 26 * len(show)), legend=False, bottom=20)
            C.show(f, key="dist1")
            st.caption("Bar = district value, thin line = 95% confidence interval, dashed line = average of the whole survey. "
                       + ("Higher is better, so the best districts are at the top." if pol > 0 else "Lower is better, so the best districts are at the bottom." if pol < 0 else ""))
            C.show_table(r.round(2), "district_ranking")

    X.deep_dive("ad", ["Four or more antenatal visits", "Antenatal care by skilled provider", "Caesarean section", "Wasting (weight-for-height < -2 SD)", "Underweight (weight-for-age < -2 SD)", "Children 5-17 attending school now"], ["scorecard", "area_gap", "trend", "province", "forest"])
