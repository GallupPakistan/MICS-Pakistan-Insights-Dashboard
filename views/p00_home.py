import base64
import html
import math
import textwrap
from pathlib import Path

import streamlit as st

import common as C

LOGO = Path(__file__).resolve().parent.parent / "assets" / "gallup_logo.png"

# (emoji, short label, indicator key, fill colour, text colour)
TILES = [
    ("💧", "Improved drinking water", "Improved drinking water", "#FFFFFF", "#0A3D91"),
    ("🚽", "Improved sanitation", "Improved sanitation", "#DCEBFA", "#0A3D91"),
    ("💡", "Electricity access", "Electricity", "#FFFFFF", "#0A3D91"),
    ("🍳", "Clean cooking fuel", "Clean cooking fuel / stove", "#F2B705", "#0B1F3A"),
    ("🤰", "Skilled birth attendant", "Skilled birth attendant", "#DCEBFA", "#0A3D91"),
    ("🩺", "4+ antenatal visits", "Four or more antenatal visits", "#FFFFFF", "#0A3D91"),
    ("💉", "Measles 1+ dose", "Measles: at least one dose (12-35 months)", "#2E9E6B", "#FFFFFF"),
    ("📏", "Stunted children", "Stunting (height-for-age < -2 SD)", "#DCEBFA", "#B2182B"),
    ("🎓", "Women ever at school", "Women ever attended school", "#FFFFFF", "#0A3D91"),
    ("👪", "Contraceptive use", "Contraceptive use", "#F2B705", "#0B1F3A"),
    ("📱", "Mobile phone at home", "Mobile phone in household", "#DCEBFA", "#0A3D91"),
]


def _pooled(k):
    """latest survey of each selected province, population-weighted (same value as the KPI cards)"""
    v = C.overall(k)[0]
    return None if v != v else float(v)


def _hex(cx, cy, r):
    pts = [(cx + r * math.cos(math.radians(60 * i - 30)), cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def honeycomb(vals):
    r = 92.0
    w = math.sqrt(3) * r
    rows = [(0, 4), (w / 2, 3), (0, 4)]
    out = [f"<svg viewBox='0 0 700 560' xmlns='http://www.w3.org/2000/svg' style='width:100%;height:auto;font-family:inherit'>"]
    idx = 0
    for ri, (off, cnt) in enumerate(rows):
        for ci in range(cnt):
            if idx >= len(vals):
                break
            emo, label, v, fill, ink = vals[idx]
            cx, cy = 56 + w / 2 + off + ci * (w + 4), 72 + r + ri * (1.5 * r + 3)
            out.append(f"<polygon points='{_hex(cx, cy, r - 3)}' fill='{fill}' stroke='rgba(255,255,255,.55)' stroke-width='3'/>")
            out.append(f"<text x='{cx:.0f}' y='{cy - 38:.0f}' text-anchor='middle' font-size='26'>{emo}</text>")
            out.append(f"<text x='{cx:.0f}' y='{cy + 2:.0f}' text-anchor='middle' font-size='32' font-weight='800' fill='{ink}'>{v}</text>")
            for j, ln in enumerate(textwrap.wrap(label, 14)[:2]):
                out.append(f"<text x='{cx:.0f}' y='{cy + 26 + 17 * j:.0f}' text-anchor='middle' font-size='14' font-weight='700' fill='{ink}' opacity='.9'>{html.escape(ln)}</text>")
            idx += 1
    out.append("</svg>")
    return "".join(out)


def render():
    vals = []
    for emo, label, key, fill, ink in TILES:
        if key in C.IND:
            v = _pooled(key)
            if v is not None:
                vals.append((emo, label, f"{v:.0f}%", fill, ink))
    logo = ""
    if LOGO.exists():
        b64 = base64.b64encode(LOGO.read_bytes()).decode()
        logo = f"<div style='background:#fff;border-radius:14px;padding:5px 12px;display:inline-block'><img src='data:image/png;base64,{b64}' style='height:44px;display:block'/></div>"
    hero = (
        "<style>.mhero{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:14px;align-items:center;background:linear-gradient(135deg,#072B6E 0%,#0A4AA8 55%,#1A82DB 100%);"
        "border-radius:18px;padding:16px 24px;color:#fff;box-shadow:0 6px 22px rgba(10,61,145,.25)}"
        "@media(max-width:760px){.mhero{grid-template-columns:1fr}}</style>"
        "<div class='mhero'><div>" + logo +
        "<div style='font-size:54px;font-weight:900;letter-spacing:2px;line-height:1;margin-top:12px'>MICS</div>"
        "<div style='font-size:11.5px;font-weight:700;letter-spacing:2.2px;margin-top:4px;opacity:.95'>MULTIPLE INDICATOR CLUSTER SURVEY</div>"
        "<div style='font-size:30px;font-weight:300;margin-top:4px'>Pakistan <b style=\"font-weight:800\">2010–2019</b></div>"
        "<div style='display:inline-block;margin-top:8px;background:#F2B705;color:#0B1F3A;font-weight:800;font-style:italic;padding:5px 14px;border-radius:6px;font-size:15px'>Key Findings Dashboard</div>"
        "<div style='margin-top:8px;font-size:12px;opacity:.9;line-height:1.4'>Punjab · Sindh · KP · Balochistan · Gilgit-Baltistan · 10 household surveys</div>"
        "</div><div>" + honeycomb(vals) + "</div></div>"
    )
    st.markdown(hero, unsafe_allow_html=True)
    st.caption("Hexagons show the latest survey of each province (Punjab 2017, Sindh 2018, KP 2019, Balochistan 2019, GB 2016), weighted by province population, "
               "i.e. a Pakistan estimate for about 2017-2019. Use the sidebar to change provinces or pick other survey years. "
               "Vaccination counts any dose, so it is higher than official full-course coverage.")

    n = {}
    for t in ("hh", "women", "children", "men"):
        try:
            n[t] = len(C.load(t))
        except Exception:
            n[t] = 0
    st.markdown("##### The survey in numbers")
    c = st.columns(5)
    with c[0]:
        C.kpi("Surveys", f"{len(C.all_surveys())}", unit="", help="Province-year surveys between 2010 and 2019.")
    with c[1]:
        C.kpi("Households", f"{n['hh']:,}", unit="")
    with c[2]:
        C.kpi("Women 15-49", f"{n['women']:,}", unit="")
    with c[3]:
        C.kpi("Children under 5", f"{n['children']:,}", unit="")
    with c[4]:
        C.kpi("Indicators", f"{len(C.IND)}", unit="", help="Every indicator has a definition on the Data notes page.")

    st.markdown("##### Explore the dashboard")
    cards = [("🏠", "Households & services", "Housing, water, sanitation, electricity and assets"), ("🤰", "Mother and newborn", "Antenatal care, skilled birth, facility delivery"),
             ("💉", "Child health", "Immunisation, nutrition, illness, mortality"), ("🎓", "Education and gender", "Schooling, women vs men, children 5-17"),
             ("⚖️", "Equity", "Wealth, urban-rural and district gaps"), ("📈", "Trends and scorecard", "What improved, what worsened, with targets"),
             ("🆚", "Compare and explore", "Any two groups, with significance tests"), ("📘", "Data notes", "Definitions, methods and survey coverage")]
    html_cards = "".join(
        f"<div style='flex:1 1 230px;background:#fff;border:1px solid #DCE4EE;border-radius:14px;padding:14px 16px'><div style='font-size:26px'>{e}</div>"
        f"<div style='font-weight:800;color:#0B1F3A;margin:4px 0 2px'>{t}</div><div style='font-size:13px;color:#5B6B7F;line-height:1.4'>{d}</div></div>" for e, t, d in cards)
    st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:12px'>{html_cards}</div>", unsafe_allow_html=True)
    st.caption("Use the pages in the left sidebar. The filters in the sidebar apply to every page, and the bar at the top of each page shows what is selected.")
