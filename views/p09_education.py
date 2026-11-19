import pandas as pd
import plotly.express as px
import streamlit as st

import common as C

WB = ["Goes out without telling husband", "Neglects the children", "Argues with husband", "Refuses sex with husband", "Burns the food"]


def _both(col_w, col_m, by):
    w = C.apply(C.load("women"), "women")
    m = C.apply(C.load("men"), "men")
    parts = []
    if w is not None and col_w in w.columns:
        parts.append(C.rate(w, col_w, by).assign(Who="Women"))
    if m is not None and col_m in m.columns:
        parts.append(C.rate(m, col_m, by).assign(Who="Men"))
    return pd.concat(parts) if parts else pd.DataFrame()


def render():
    C.page_header("Education, gender & children 5-17", "Schooling and attitudes of adults, and the situation of school-age children", ":material/school:")
    tabs = st.tabs(["Women & men: education and attitudes", "Children 5-17", "Population structure"])
    by = C.safe_dim(["Women ever attended school"])

    with tabs[0]:
        C.kpi_row(["Women ever attended school", "Men ever attended school", "Women: wife beating justified", "Men: wife beating justified"])
        st.caption("Men were interviewed only in Balochistan 2019, KP 2019, Punjab 2017 and Sindh 2018.")
        w = C.apply(C.load("women"), "women")
        a, b = st.columns(2)
        with a:
            if w is not None and not w.empty:
                d = C.dist(w, "Education", by)
                C.dist_chart(d, "Education", by, "Women's highest level of education", cmap=C.EDU_COLORS, order=C.EDU, key="e1", cat_label="Education level")
            else:
                C.no_data()
        with b:
            bw = _both("ever_school", "ever_school", "Survey")
            if bw.empty:
                C.no_data()
            else:
                bw["Survey"] = bw["Survey"].astype(str)
                bw["label"] = bw["value"].map(lambda v: f"{v:.0f}%")
                fig = px.bar(bw, x="Survey", y="value", color="Who", barmode="group", text="label", color_discrete_map={"Women": C.SEX_COLORS["Female"], "Men": C.SEX_COLORS["Male"]},
                             category_orders={"Survey": C.survey_order(bw["Survey"]), "Who": ["Women", "Men"]}, title="Ever attended school: women vs men (15-49)",
                             labels={"value": "% who ever attended school"}, hover_data={"n": ":,", "label": False})
                fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=11)
                fig.update_yaxes(range=[0, 118])
                fig.update_xaxes(tickangle=-30, title="")
                C.style(fig, 430, legend_title="Respondent")
                C.show(fig, key="e2")
        st.markdown("##### Attitudes: is wife beating justified?")
        rows = []
        for who, tbl in (("Women", "women"), ("Men", "men")):
            df = C.apply(C.load(tbl), tbl)
            if df is None or df.empty:
                continue
            for r in WB:
                c = "WB: " + r
                if c in df.columns:
                    d = df[df[c].notna()]
                    if len(d) >= C.get_filters()["min_n"]:
                        rows.append(dict(Who=who, Reason=r, value=(d[c] * d["w"]).sum() / d["w"].sum() * 100, n=len(d)))
        if rows:
            t = pd.DataFrame(rows)
            t["label"] = t["value"].map(lambda v: f"{v:.0f}%")
            fig = px.bar(t, y="Reason", x="value", color="Who", barmode="group", orientation="h", text="label",
                         color_discrete_map={"Women": C.SEX_COLORS["Female"], "Men": C.SEX_COLORS["Male"]}, category_orders={"Reason": WB[::-1], "Who": ["Women", "Men"]},
                         title="% who think a husband is justified in beating his wife if she ...", labels={"value": "% of respondents"},
                         hover_data={"n": ":,", "label": False})
            fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=11)
            fig.update_xaxes(range=[0, max(t["value"].max(), 1) * 1.2])
            C.style(fig, 420, legend_title="Respondent")
            C.show(fig, key="e3")
        C.bar_chart(C.ind_rate("Women: wife beating justified", by), by,
                    "Women: wife beating justified (any of 5 reasons)", "%", key="e4")
        st.caption("Punjab 2011 did not ask these questions.")

    with tabs[1]:
        c5 = C.apply(C.load("c5to17"), "c5to17")
        if c5 is None or c5.empty:
            C.no_data("Children 5-17 were surveyed only in Balochistan 2019, KP 2019, Punjab 2017 and Sindh 2018.")
        else:
            C.kpi_row(["Children 5-17 attending school now", "Children 5-17 ever attended school", "Children 5-17 doing paid / income work",
                       "Children 5-17 doing household chores", "Children 5-17 with functional difficulty"], cols=5,
                      labels={"Children 5-17 attending school now": "Attending school now", "Children 5-17 ever attended school": "Ever attended school",
                              "Children 5-17 doing paid / income work": "Doing income work", "Children 5-17 doing household chores": "Doing chores",
                              "Children 5-17 with functional difficulty": "Functional difficulty"})
            by5 = C.safe_dim("Children 5-17 attending school now")
            ind = st.selectbox("Indicator", [k for k in C.IND if k.startswith("Children 5-17")], key="c5_ind", index=1)
            a, b = st.columns(2)
            with a:
                C.bar_chart(C.ind_rate(ind, by5), by5, f"{ind} by {C.DIM_LABEL.get(by5, by5).lower()}", "%", key="e6")
            with b:
                r = C.rate(c5, C.IND[ind][1], ["AgeGroup", by5])
                C.line_chart(r, "AgeGroup", by5, f"{ind} by child's age", key="e7", xorder=["5-7", "8-10", "11-13", "14-17"])
            a, b = st.columns(2)
            with a:
                if "Sex" in c5.columns:
                    C.bar_chart(C.ind_rate(ind, ["Survey", "Sex"]), "Survey", f"{ind}: boys vs girls", "%", color="Sex", key="e8")
                    st.caption("Sex is not recorded in Sindh 2018 for this table.")
            with b:
                C.bar_chart(C.ind_rate(ind, ["Wealth", "Province"]), "Wealth", f"{ind} by wealth quintile", "%", color="Province", key="e9")
            a, b = st.columns(2)
            with a:
                r = C.rate(c5, "attending", ["MotherEdu", "Province"])
                C.bar_chart(r, "MotherEdu", "Attending school by mother's education", "%", color="Province", key="e10")
            with b:
                C.bar_chart(C.ind_rate("Children 5-17 doing household chores", ["Survey", "Area"]), "Survey", "Doing household chores: urban vs rural", "%", color="Area", key="e11")
            st.caption("School attendance is reported for children with an answer on the current school year (the share answered varies by survey).")

    with tabs[2]:
        mem = C.apply(C.load("members"), "members")
        if mem is None or mem.empty:
            st.info("Population pyramids need the household-members table. Run prepare_data.py with MICS_HouseholdMembers.parquet in the input folder (it was not available "
                    "when this dashboard was built).", icon=":material/info:")
        else:
            mem = mem[mem["Sex"].notna() & mem["AgeGroup"].notna() & mem["Age"].notna()]
            have = C.survey_order(mem["Survey"].astype(str).unique())
            st.caption("Built from the household lists of every survey (age and sex of every household member, weighted).")
            if not have:
                C.no_data()
                return
            pick = st.selectbox("Survey shown in the pyramid", have, index=len(have) - 1, key="pyr_survey")
            cur = mem[mem["Survey"].astype(str) == pick]

            def wshare(df, cond):
                return (df["w"] * cond(df)).sum() / df["w"].sum() * 100

            def wmedian(df):
                d = df.sort_values("Age")
                cw = d["w"].cumsum() / d["w"].sum()
                return float(d["Age"][cw >= 0.5].iloc[0])

            k = st.columns(5)
            with k[0]:
                st.metric("👥 Household members in sample", f"{len(cur):,}", border=True)
            with k[1]:
                st.metric("🎂 Median age", f"{wmedian(cur):.0f} years", border=True)
            with k[2]:
                st.metric("🧒 Under 15 years", f"{wshare(cur, lambda d: d['Age'] < 15):.1f}%", border=True)
            with k[3]:
                st.metric("🧓 Aged 65 and over", f"{wshare(cur, lambda d: d['Age'] >= 65):.1f}%", border=True)
            with k[4]:
                work = wshare(cur, lambda d: (d["Age"] >= 15) & (d["Age"] < 65))
                dep = (100 - work) / work * 100 if work else float("nan")
                st.metric("⚖️ Dependency ratio (per 100)", f"{dep:.0f}", help="People under 15 and 65+ for every 100 people aged 15-64.", border=True)
            g = cur.groupby(["AgeGroup", "Sex"], observed=True)["w"].sum().reset_index()
            g["pct"] = g["w"] / g["w"].sum() * 100
            order = [f"{i}-{i + 4}" for i in range(0, 80, 5)] + ["80+"]
            g["signed"] = g.apply(lambda r: -r["pct"] if r["Sex"] == "Male" else r["pct"], axis=1)
            g["lab"] = g["pct"].map(lambda v: f"{v:.1f}%")
            fig = px.bar(g, y="AgeGroup", x="signed", color="Sex", orientation="h", color_discrete_map=C.SEX_COLORS, category_orders={"AgeGroup": order, "Sex": ["Male", "Female"]},
                         title=f"Population pyramid, {pick} (% of all household members)", labels={"signed": "% of population (males left, females right)", "AgeGroup": "Age group"},
                         hover_data={"lab": True, "signed": False})
            fig.update_layout(barmode="overlay")
            m = g["pct"].max() * 1.15
            fig.update_xaxes(range=[-m, m], tickvals=[-m * 0.8, -m * 0.4, 0, m * 0.4, m * 0.8], ticktext=[f"{m * 0.8:.1f}", f"{m * 0.4:.1f}", "0", f"{m * 0.4:.1f}", f"{m * 0.8:.1f}"])
            C.style(fig, 560, legend_title="Sex")
            C.show(fig, key="e12")
