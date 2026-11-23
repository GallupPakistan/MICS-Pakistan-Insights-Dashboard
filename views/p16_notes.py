import streamlit as st

import common as C


def render():
    C.page_header("Data notes & definitions", "How the numbers are built, what they mean and what they do not mean", ":material/menu_book:")
    st.info("**Counts any dose, so these figures are higher than the official full-course coverage.** Vaccination charts show children who received at least one dose.",
            icon=":material/info:")
    t1, t2, t3 = st.tabs(["Method", "Indicator definitions", "Survey coverage"])
    with t1:
        st.markdown("""
* **One survey = one province in one year** (e.g. *Punjab 2017*). Compare change over time only within a province.
* **Weighted percentages** use the sample weight of each table. Groups with fewer than the minimum records (sidebar) are hidden.
* **Confidence intervals** are approximate (effective sample size, no clustering), so they are slightly optimistic.
* **Figures not split by survey use the latest survey of each province** (Punjab 2017, Sindh 2018, KP 2019, Balochistan 2019, GB 2016), so survey years are not mixed. Trend charts use all surveys. Picking surveys in the sidebar overrides this.
* **Population-weighted by default**: each survey is weighted to its province's 2023 census population, so a value over several provinces approximates Pakistan. Single-province values are unaffected.
* **Water and sanitation follow the JMP 2017 / MICS6 definitions**: tanker-truck and cart with small tank count as improved water sources (they did not in MICS4/5 reports), and a flush toilet to an unknown place counts as improved sanitation.
* **Vaccination** = any dose by card or mother's report, children 12-35 months. Not full-course coverage.
* **Missing questions** (for example no marriage-age question in some surveys) are left out, never shown as zero.
* **Every table and chart can be downloaded**: the camera icon on a chart saves a PNG, and *Show / download the numbers* gives a CSV.""")
    with t2:
        rows = [dict(Indicator=k, Table=v[0], Unit=v[2], Better=("higher" if v[3] > 0 else "lower" if v[3] < 0 else "n/a"), Definition=v[5]) for k, v in C.IND.items()]
        import pandas as pd
        C.show_table(pd.DataFrame(rows), "indicator_definitions", "Show / download all indicator definitions")
    with t3:
        cov = C.coverage()
        if cov.empty:
            C.no_data()
        else:
            C.show_table(cov, "survey_coverage_notes", "Show / download survey coverage")
        try:
            st.code((C.data_dir() / "prep_log.txt").read_text(encoding="utf-8"), language="text")
        except Exception:
            pass
