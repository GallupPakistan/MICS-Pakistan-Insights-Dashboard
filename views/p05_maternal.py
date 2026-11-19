import streamlit as st

import common as C
import extras as X

KEYS = ["Antenatal care by skilled provider", "Four or more antenatal visits", "Tetanus injection in last pregnancy", "Skilled birth attendant",
        "Facility delivery", "Caesarean section", "Contraceptive use"]
SHORT = {"Antenatal care by skilled provider": "ANC skilled", "Four or more antenatal visits": "4+ ANC visits", "Tetanus injection in last pregnancy": "Tetanus",
         "Skilled birth attendant": "Skilled birth", "Facility delivery": "Facility birth", "Caesarean section": "C-section", "Contraceptive use": "Contraception"}


def render():
    C.page_header("Maternal & newborn health", "Care during pregnancy and childbirth, and family planning (women aged 15-49)", ":material/pregnant_woman:")
    w = C.apply(C.load("women"), "women")
    if w is None or w.empty:
        C.no_data()
        return
    C.kpi_row(["Antenatal care by skilled provider", "Four or more antenatal visits", "Skilled birth attendant"])
    C.kpi_row(["Facility delivery", "Caesarean section", "Contraceptive use"])
    st.caption("Antenatal / delivery indicators refer to women's last birth in the two years before the survey; contraceptive use refers to all women (currently married where known).")
    by = C.safe_dim(KEYS)

    st.markdown("---")
    C.multi_bar(KEYS[:6], by, "Care along pregnancy and birth", key="m1", labels=SHORT, height=480)
    st.markdown("---")
    ind = st.selectbox("Indicator", KEYS, index=3, key="mat_ind")
    a, b = st.columns(2)
    with a:
        C.bar_chart(C.ind_rate(ind, by), by, f"{ind} by {C.DIM_LABEL.get(by, by).lower()}", "%", height=500, key="m2")
    with b:
        C.trend_chart(C.ind_rate(ind, "Survey"), f"{ind} over time", "%", key="m3")
    C.availability_note(C.ind_rate(ind, "Survey"), ind.lower())
    st.caption(C.IND[ind][5])

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        r = C.rate(w, "contraception", [by, "AgeGroup"])
        C.line_chart(r, "AgeGroup", by, "Contraceptive use by woman's age", key="m4", xorder=["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49"])
    with b:
        d = C.dist(w, "Method", by)
        C.dist_chart(d, "Method", by, "Method mix among women using contraception", order=["Sterilisation", "IUD", "Implants", "Injectables", "Pill", "Condom",
                                                                                         "Periodic abstinence", "Withdrawal", "Other methods"], key="m5", cat_label="Method")
    a, b = st.columns(2)
    with a:
        C.bar_chart(C.ind_rate("Skilled birth attendant", ["Wealth", by if by != "Wealth" else "Province"]), "Wealth",
                    "Skilled birth attendant by wealth quintile", "%", color=by if by != "Wealth" else "Province", key="m6")
    with b:
        C.bar_chart(C.ind_rate("Facility delivery", ["Survey", "Area"]), "Survey", "Facility delivery: urban vs rural", "%", color="Area", key="m7")

    X.deep_dive("mt", ["Skilled birth attendant", "Facility delivery", "Four or more antenatal visits", "Antenatal care by skilled provider", "Tetanus injection in last pregnancy", "Contraceptive use"], ["scorecard"])
