"""
Pakistan MICS dashboard  -  run with:   streamlit run app.py

Needs the cleaned tables made by prepare_data.py (folder 'data' next to this file, or set MICS_DASH_DATA).
"""
import streamlit as st

st.set_page_config(page_title="Pakistan MICS Dashboard", page_icon=":material/monitoring:", layout="wide", initial_sidebar_state="expanded")

import common as C  # noqa: E402
from views import (p01_overview, p02_households, p03_wash, p04_equity, p05_maternal, p06_immunisation, p07_nutrition,  # noqa: E402
                   p08_mortality, p09_education, p10_explorer, p11_compare, p12_advanced, p13_assets, p14_illness, p15_fertility, p16_notes, p17_men, p18_scorecard, p19_framework, p00_home, p20_equity_visuals)

st.markdown("""
<style>
  .block-container {padding-top: 2.4rem; padding-bottom: 3rem; max-width: 1500px;}
  /* ---- sidebar: dark navy, like the reference ---- */
  section[data-testid="stSidebar"] {min-width: 330px; background:#0B1F3A;}
  section[data-testid="stSidebar"] * {color:#F1F5F9;}
  section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] h5 {color:#FFFFFF; letter-spacing:.02em;}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a, section[data-testid="stSidebarNav"] a {border-radius:8px; margin:1px 0;}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {background:#21505F !important; font-weight:600;}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {background:#17335C;}
  section[data-testid="stSidebar"] hr {border-color:#24426E;}
  section[data-testid="stSidebar"] [data-baseweb="select"] > div {background:#17335C; border:1px solid #2C4F82;}
  section[data-testid="stSidebar"] span[data-baseweb="tag"] {background-color:#0F766E !important; border-radius:6px;}
  section[data-testid="stSidebar"] span[data-baseweb="tag"] span, section[data-testid="stSidebar"] span[data-baseweb="tag"] svg {color:#FFFFFF !important; fill:#FFFFFF !important;}
  section[data-testid="stSidebar"] button[kind="secondary"], section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {background:#17335C; border:1px solid #2C4F82; color:#FFFFFF;}
  section[data-testid="stSidebar"] [data-testid="stExpander"] {border:1px solid #24426E; border-radius:8px;}
  section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {color:#B6C4D6;}
  .keychip {display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:6px; vertical-align:middle; border:1px solid rgba(255,255,255,.5);}
  .keyrow {font-size:0.82rem; line-height:1.55;}
  .brand {display:flex; gap:10px; align-items:center; margin-top:14px; font-weight:700; font-size:1.05rem; color:#fff;}
  .brandsub {font-size:.78rem; color:#B6C4D6; margin-top:4px;}
  /* ---- page header banner ---- */
  .hero {background:linear-gradient(135deg,#0B1F3A 0%,#13305A 100%); border-left:6px solid #F97316; border-radius:14px; padding:18px 24px; display:flex; justify-content:space-between; align-items:center; gap:20px; margin-bottom:14px; box-shadow:0 2px 8px rgba(11,31,58,.18);}
  .hero .crumb {font-size:.8rem; color:#9FB3CC; margin-bottom:4px;}
  .hero h1 {font-size:1.9rem; margin:0; padding:0; color:#FFFFFF; font-weight:700; line-height:1.2;}
  .hero .sub {font-size:.92rem; color:#D5DFEC; margin-top:6px; max-width:900px;}
  .hero .badge {min-width:150px; text-align:center; border:1px solid #3A5A8A; border-radius:12px; padding:10px 16px; background:rgba(255,255,255,.05);}
  .hero .badge b {display:block; font-size:1.9rem; color:#FFFFFF; line-height:1.1;}
  .hero .badge span {font-size:.68rem; letter-spacing:.1em; color:#9FB3CC; text-transform:uppercase;}
  .filterbar {padding:8px 14px; background:#FFFFFF; border:1px solid #DCE4EE; border-left:4px solid #0F766E; border-radius:8px; font-size:.85rem; margin-bottom:14px; color:#14233A;}
  .takeaway {background:#E8F1FE; border:1px solid #C5D9F7; border-radius:10px; padding:12px 16px; margin:6px 0 16px 0; color:#14233A; font-size:.95rem;}
  /* ---- KPI cards: mint gradient + teal edge ---- */
  div[data-testid="stMetric"] {background:linear-gradient(135deg,#F2FBF8 0%,#FFFFFF 100%); border:1px solid #CFE9E2; border-left:5px solid #0F766E; border-radius:12px; padding:12px 14px; box-shadow:0 1px 4px rgba(15,118,110,.10);}
  div[data-testid="stMetricValue"] {font-size:clamp(1.05rem, 1.55vw, 1.75rem); font-weight:700; color:#0B1F3A; line-height:1.15;}
  div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] * {white-space:nowrap !important; overflow:visible !important; text-overflow:clip !important;}
  [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {white-space:normal !important; overflow:visible !important; text-overflow:clip !important; -webkit-line-clamp:unset !important; max-height:none !important;}
  [data-testid="stMetricLabel"] p {display:block !important;}
  [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {word-break:normal !important; overflow-wrap:normal !important;}
  [data-testid="stColumn"]:has([data-testid="stMetric"]) {min-width:150px !important;}
  [data-testid="stMetricLabel"] p {font-size:.85rem; color:#33475F;}
  [data-testid="stMetricLabel"] .stMarkdownEllipsis, [data-testid="stMetricLabel"] .stMarkdownEllipsis p, [data-testid="stMetricLabel"] label
      {white-space:normal !important; overflow:visible !important; text-overflow:clip !important; -webkit-line-clamp:unset !important; display:block !important; line-height:1.3;}
  [data-testid="stMetricLabel"] > div {min-width:0; flex:1 1 auto;}
  div[data-testid="stMetric"] {min-height:136px; height:100%; box-sizing:border-box;}
  [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {align-items:stretch;}
  [data-testid="stColumn"]:has([data-testid="stMetric"]), [data-testid="stColumn"]:has([data-testid="stMetric"]) > div, [data-testid="stColumn"]:has([data-testid="stMetric"]) [data-testid="stElementContainer"],
  [data-testid="stColumn"]:has([data-testid="stMetric"]) [data-testid="stMetric"] {height:100%;}
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stMetric"]) {border:none !important; padding:0 !important; background:transparent !important;}
  /* ---- charts sit on white cards ---- */
  div[data-testid="stPlotlyChart"] {background:#FFFFFF; border:1px solid #DCE4EE; border-radius:12px; padding:8px 8px 2px 8px; box-shadow:0 1px 3px rgba(11,31,58,.06);}
  div[data-testid="stHorizontalBlock"] {gap:1rem; align-items:stretch;}
  div[data-testid="stPlotlyChart"] {overflow:hidden; margin-bottom:.6rem;}
  .block-container {max-width:1500px;}
  div[data-testid="stElementContainer"]:has(.filterbar) {position:sticky; top:2.9rem; z-index:60; background:#F4F7FB;}
  @media print {section[data-testid="stSidebar"], header, .stDeployButton, iframe {display:none !important;} div[data-testid="stPlotlyChart"] {break-inside:avoid;}}
  div[data-testid="stMain"] div[data-testid="stExpander"], div[data-testid="stDataFrame"] {background:#FFFFFF; border-radius:10px;}
  .main h5 {color:#0B1F3A; border-bottom:2px solid #DCE4EE; padding-bottom:4px; margin-top:.4rem;}
  hr {border-color:#DCE4EE;}
</style>""", unsafe_allow_html=True)

PAGES = [
    (p00_home.render, "Home", "🏛️", "home"),
    (p01_overview.render, "Overview", "📋", "overview"),
    (p02_households.render, "Households & housing", "🏠", "households"),
    (p03_wash.render, "Water, sanitation & hygiene", "💧", "wash"),
    (p04_equity.render, "Wealth & equity", "⚖️", "equity"),
    (p05_maternal.render, "Maternal & newborn health", "🤰", "maternal"),
    (p06_immunisation.render, "Child immunisation", "💉", "immunisation"),
    (p07_nutrition.render, "Child nutrition", "🍼", "nutrition"),
    (p08_mortality.render, "Child mortality & siblings", "🩺", "mortality"),
    (p09_education.render, "Education, gender & children 5-17", "🎓", "education"),
    (p10_explorer.render, "Compare & data explorer", "🔎", "explorer"),
    (p11_compare.render, "Compare two groups", "🆚", "compare"),
    (p12_advanced.render, "Inequality & districts", "📊", "inequality"),
    (p13_assets.render, "Assets & connectivity", "📱", "assets"),
    (p14_illness.render, "Child illness & care", "🤒", "illness"),
    (p15_fertility.render, "Fertility & marriage", "👨‍👩‍👧", "fertility"),
    (p18_scorecard.render, "KPI scorecard", "📈", "scorecard"),
    (p17_men.render, "Women vs men", "👫", "men"),
    (p20_equity_visuals.render, "Research graphics", "🔬", "research"),
    (p19_framework.render, "Concept maps", "🧭", "concepts"),
    (p16_notes.render, "Data notes", "📘", "notes"),
]
pg = st.navigation([st.Page(f, title=t, icon=i, url_path=u, default=(u == "home")) for f, t, i, u in PAGES], position="sidebar", expanded=True)

# ----------------------------------------------------------------------------- filter state (kept in session + in the page address so a view can be shared)
K = C.FKEY
DEFAULTS = {"prov": list(C.PROV_ORDER), "surv": [], "area": ["Urban", "Rural"], "sex": ["Male", "Female"], "wealth": list(C.WEALTH), "dist": [],
            "cmp": "Province", "minn": 50, "ci": False, "pop": True}
PRESETS = {
    "Balochistan: rural, poorest 40%": {"prov": ["Balochistan"], "area": ["Rural"], "wealth": ["Poorest", "Second"]},
    "Punjab vs Sindh, latest surveys": {"prov": ["Punjab", "Sindh"], "surv": ["Punjab 2017", "Sindh 2018"], "cmp": "Province"},
    "Urban vs rural, all provinces": {"cmp": "Area"},
    "Richest vs poorest, all provinces": {"cmp": "Wealth"},
    "Girls and boys, latest surveys": {"surv": ["Punjab 2017", "Sindh 2018", "KP 2019", "Balochistan 2019", "GB 2016"], "cmp": "Sex"},
}


def _init_state():
    ss = st.session_state
    if ss.get("_flt_init"):
        return
    for k, v in DEFAULTS.items():
        ss[K + k] = list(v) if isinstance(v, list) else v
    qp = st.query_params
    for k, v in DEFAULTS.items():
        if k in qp:
            raw = qp[k]
            if isinstance(v, list):
                ss[K + k] = [x for x in str(raw).split("|") if x]
            elif isinstance(v, bool):
                ss[K + k] = str(raw) == "1"
            elif isinstance(v, int):
                try:
                    ss[K + k] = int(raw)
                except ValueError:
                    pass
            else:
                ss[K + k] = str(raw)
    ss["_flt_init"] = True


def _reset():
    for k, v in DEFAULTS.items():
        st.session_state[K + k] = list(v) if isinstance(v, list) else v


def _preset():
    name = st.session_state.get("preset_pick")
    if name in PRESETS:
        _reset()
        for k, v in PRESETS[name].items():
            st.session_state[K + k] = list(v) if isinstance(v, list) else v


def _write_query():
    ss = st.session_state
    q = {}
    for k, v in DEFAULTS.items():
        cur = ss.get(K + k, v)
        if cur != v:
            q[k] = "|".join(cur) if isinstance(cur, list) else ("1" if cur is True else str(cur))
    if dict(st.query_params) != q:
        st.query_params.from_dict(q)
    return q


with st.sidebar:
    st.markdown("### Filters")
    if not C.data_ready():
        st.error("Dashboard data not found.")
    else:
        _init_state()
        hh = C.load("hh")
        ss = st.session_state
        provs = [p for p in C.PROV_ORDER if p in set(hh["Province"].astype(str))]
        st.multiselect("Province", provs, key=K + "prov", help="Pick one or more provinces. Empty = all.")
        sel_p = ss.get(K + "prov") or provs
        surveys = [s for s in C.all_surveys() if C.survey_province(s) in sel_p]
        ss[K + "surv"] = [s for s in ss.get(K + "surv", []) if s in surveys]
        st.multiselect("Survey (province + year)", surveys, key=K + "surv", placeholder="Latest survey per province",
                       help="Each survey is one province in one year. Empty = trend and by-survey charts use every survey, and all other figures "
                            "(KPIs, province / area / wealth comparisons) use the latest survey of each province, so survey years are never mixed. "
                            "Pick surveys here to use exactly those instead.")
        st.multiselect("Area", ["Urban", "Rural"], key=K + "area")
        st.multiselect("Sex", ["Male", "Female"], key=K + "sex",
                       help="Applies to tables with a sex column (children, birth / sibling history, children 5-17, members).")
        st.multiselect("Wealth quintile", C.WEALTH, key=K + "wealth", help="Poorest 20% ... Richest 20% of households (wealth index).")
        dists = sorted(hh.loc[hh["Province"].isin(sel_p), "District"].dropna().astype(str).unique())
        ss[K + "dist"] = [d for d in ss.get(K + "dist", []) if d in dists]
        st.multiselect("District", dists, key=K + "dist", placeholder="All districts", help="Optional: narrow down to specific districts.")
        st.markdown("##### Display & weighting")
        st.selectbox("Compare charts by", ["Province", "Survey", "Area", "Wealth", "Sex"], key=K + "cmp",
                     format_func=lambda x: C.DIM_LABEL.get(x, x), help="The group that charts split their bars / lines by (where it makes sense).")
        st.slider("Hide groups with fewer than N records", 0, 500, step=10, key=K + "minn", help="Small groups give unreliable percentages.")
        st.toggle("Show 95% confidence intervals", key=K + "ci", help="Approximate (simple random sampling with effective sample size).")
        st.toggle("Population-weighted (Pakistan)", key=K + "pop",
                  help="On (default): each survey is re-weighted to its province's 2023 census population, so a figure over several provinces is a "
                       "Pakistan estimate instead of a mix driven by sample sizes. Values for a single province or survey do not change. "
                       "Azad Kashmir, Islamabad and FATA before 2018 are not covered.")
        with st.expander("Quick views & share"):
            st.selectbox("Ready-made views", list(PRESETS), index=None, placeholder="Pick a view ...", key="preset_pick", on_change=_preset)
            q = _write_query()
            st.caption("To share or bookmark the current view, copy the web address from your browser: it now contains these filters"
                       + (":" if q else " (none changed yet)."))
            if q:
                st.code("?" + "&".join(f"{k}={v}" for k, v in q.items()), language="text")
        st.markdown("##### Colour key")
        st.markdown("<div class='keyrow'>" + "<br>".join(
            f"<span class='keychip' style='background:{C.PROV_COLORS[p]}'></span>{p}" for p in provs) + "<br>"
            + "<br>".join(f"<span class='keychip' style='background:{c}'></span>{a}" for a, c in C.AREA_COLORS.items()) + "<br>"
            + "<br>".join(f"<span class='keychip' style='background:{c}'></span>{a}" for a, c in C.SEX_COLORS.items()) + "<br>"
            + "<br>".join(f"<span class='keychip' style='background:{C.WEALTH_COLORS[w]}'></span>{w}" for w in C.WEALTH) + "</div>",
            unsafe_allow_html=True)
        st.caption("Province colours are used for provinces and surveys (older surveys lighter). Area, sex and wealth colours are fixed too. "
                   "Chart toolbar: camera icon = download the chart as PNG.")
        st.button("Reset filters", on_click=_reset, **C.STRETCH)

        st.markdown("---")
        st.markdown("<div class='brand'><span style='font-size:1.8rem'>🇵🇰</span>Pakistan MICS Dashboard</div>"
                    "<div class='brandsub'>Multiple Indicator Cluster Surveys 2010-2019<br>Punjab, Sindh, KP, Balochistan, Gilgit-Baltistan</div>", unsafe_allow_html=True)

if not C.data_ready():
    st.title("Pakistan MICS dashboard")
    st.error(f"The cleaned data tables were not found in `{C.data_dir()}`.")
    st.markdown("Run the preparation step once, then reload this page:\n\n"
                "```\npython prepare_data.py \"C:\\Users\\DELL\\Desktop\\MICS\\parquet\" \"data\"\n```")
    st.stop()

pg.run()