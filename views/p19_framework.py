"""Concept-map style infographics built from the live data: a hub-and-spoke of what drives service use,
(the technical table diagram and the how-to cards were removed: the Home page and Data notes already cover them)."""
import html
import math

import pandas as pd
import streamlit as st

import common as C

NAVY, INK = "#0B1F3A", "#243B53"
SPOKE_COL = ["#2C7FB8", "#2E9E6B", "#E8A317", "#7E57C2", "#D1495B", "#17A2B8"]
ABBR = {"Khyber Pakhtunkhwa": "KP", "Gilgit-Baltistan": "GB", "Balochistan": "Balochistan", "None / pre-primary": "None", "Higher": "Higher"}

OUTCOMES = {
    "Skilled birth attendant": dict(table="women", col="skilled_birth", spokes=["Wealth", "Education", "Area", "Province", "AgeGroup", "ANC"], who="women with a recent birth"),
    "Facility delivery": dict(table="women", col="facility_birth", spokes=["Wealth", "Education", "Area", "Province", "AgeGroup", "ANC"], who="women with a recent birth"),
    "Measles: at least one dose (12-35 months)": dict(table="children", col="vacc_Measles", spokes=["Wealth", "MotherEdu", "Area", "Province", "Sex"], who="children 12-35 months"),
}
SPOKE_NAME = {"Wealth": "Household wealth", "Education": "Mother's education", "MotherEdu": "Mother's education", "Area": "Place of residence",
              "Province": "Province", "AgeGroup": "Mother's age", "ANC": "Antenatal visits", "Sex": "Child's sex"}


def _short(x, n=11):
    x = ABBR.get(str(x), str(x))
    return x if len(x) <= n else x[: n - 1] + "…"


def _spoke(df, col, dim):
    if dim == "ANC":
        df = df.assign(ANC=df["anc_4plus"].map({1.0: "4+ visits", 0.0: "under 4"}))
    r = C.rate(df, col, dim)
    r = r[r["n"] >= 100].dropna(subset=["value"]) if not r.empty else r
    if r is None or len(r) < 2:
        return None
    lo, hi = r.loc[r["value"].idxmin()], r.loc[r["value"].idxmax()]
    return dict(lo_l=str(lo[dim]), lo_v=float(lo["value"]), hi_l=str(hi[dim]), hi_v=float(hi["value"]))


def hub_svg(title, spokes):
    W, H, cx, cy, R, rr = 1200, 780, 600, 390, 240, 80
    out = [f"<svg viewBox='0 0 {W} {H}' xmlns='http://www.w3.org/2000/svg' style='width:100%;height:auto;font-family:inherit'>"]
    n = len(spokes)
    for i, s in enumerate(spokes):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
        col = SPOKE_COL[i % len(SPOKE_COL)]
        out.append(f"<line x1='{cx}' y1='{cy}' x2='{x:.0f}' y2='{y:.0f}' stroke='{col}' stroke-width='3' stroke-dasharray='6 5' opacity='.7'/>")
    for i, s in enumerate(spokes):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
        col = SPOKE_COL[i % len(SPOKE_COL)]
        bx, by = cx + (R + 110) * math.cos(ang) * 1.35, cy + (R + 112) * math.sin(ang)
        gap = s["hi_v"] - s["lo_v"]
        txt = f"{s['hi_v'] / s['lo_v']:.1f}× higher" if s["lo_v"] >= 1 else f"+{gap:.0f} points"
        if abs(math.cos(ang)) < 0.3:
            ex, ey = bx, (by + 30 if math.sin(ang) < 0 else by - 30)
        else:
            ex, ey = bx - (108 if math.cos(ang) > 0 else -108), by
        d_ = math.hypot(ex - x, ey - y)
        out.append(f"<line x1='{x + (ex - x) * rr / d_:.0f}' y1='{y + (ey - y) * rr / d_:.0f}' x2='{ex:.0f}' y2='{ey:.0f}' stroke='{col}' stroke-width='1.5'/>")
        out.append(f"<ellipse cx='{bx:.0f}' cy='{by:.0f}' rx='108' ry='30' fill='{col}' fill-opacity='.16' stroke='{col}'/>")
        out.append(f"<text x='{bx:.0f}' y='{by - 3:.0f}' text-anchor='middle' font-size='12.5' font-weight='700' fill='{INK}'>{html.escape(_short(s['hi_l'], 14))} vs {html.escape(_short(s['lo_l'], 14))}</text>")
        out.append(f"<text x='{bx:.0f}' y='{by + 13:.0f}' text-anchor='middle' font-size='12.5' fill='{INK}'>{html.escape(txt)}</text>")
        out.append(f"<circle cx='{x:.0f}' cy='{y:.0f}' r='{rr}' fill='#fff' stroke='{col}' stroke-width='4'/>")
        out.append(f"<text x='{x:.0f}' y='{y - 22:.0f}' text-anchor='middle' font-size='13.5' font-weight='800' fill='{NAVY}'>{html.escape(s['name'])}</text>")
        out.append(f"<text x='{x:.0f}' y='{y + 2:.0f}' text-anchor='middle' font-size='12' fill='#B2182B'>▼ {html.escape(_short(s['lo_l'], 13))} {s['lo_v']:.0f}%</text>")
        out.append(f"<text x='{x:.0f}' y='{y + 22:.0f}' text-anchor='middle' font-size='12' fill='#1B7F4B'>▲ {html.escape(_short(s['hi_l'], 13))} {s['hi_v']:.0f}%</text>")
    out.append(f"<circle cx='{cx}' cy='{cy}' r='108' fill='{NAVY}'/>")
    words = title.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) > 16:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    y0 = cy - 9 * (len(lines) - 1)
    for j, ln in enumerate(lines):
        out.append(f"<text x='{cx}' y='{y0 + 18 * j + 5}' text-anchor='middle' font-size='15' font-weight='800' fill='#fff'>{html.escape(ln)}</text>")
    out.append("</svg>")
    return "".join(out)


def linkage_svg(tables):
    W, H = 1000, 560
    hub, rest = tables[0], tables[1:]
    out = [f"<svg viewBox='0 0 {W} {H}' xmlns='http://www.w3.org/2000/svg' style='width:100%;height:auto;font-family:inherit'>"]
    cols = ["#E8553E", "#E8A317", "#2C7FB8", "#2E9E6B", "#7E57C2", "#17A2B8", "#D1495B", "#7A8CA3"]
    hx0, hx1, hy = 30, 300, 280
    step = (H - 40 - 56) / max(1, len(rest) - 1)
    for i, (t, c) in enumerate(zip(rest, cols * 2)):
        yc = 20 + 28 + i * step
        out.append(f"<path d='M{hx1},{hy} C{hx1 + 110},{hy} {500 - 110},{yc} 500,{yc}' fill='none' stroke='{c}' stroke-width='3' opacity='.8'/>")
        out.append(f"<rect x='500' y='{yc - 28:.0f}' width='470' height='56' rx='14' fill='#fff' stroke='{c}' stroke-width='3'/>")
        out.append(f"<text x='520' y='{yc - 4:.0f}' font-size='15' font-weight='800' fill='{NAVY}'>{html.escape(t['name'])}</text>")
        out.append(f"<text x='950' y='{yc - 4:.0f}' text-anchor='end' font-size='13.5' fill='{INK}'>{t['rows']:,} rows · {html.escape(t['surveys'])}</text>")
        out.append(f"<text x='520' y='{yc + 16:.0f}' font-size='12.5' fill='#5B6B7F'>{html.escape(t['note'])}</text>")
    out.append(f"<rect x='{hx0}' y='{hy - 75}' width='{hx1 - hx0}' height='150' rx='26' fill='{NAVY}'/>")
    out.append(f"<text x='{(hx0 + hx1) / 2}' y='{hy - 22}' text-anchor='middle' font-size='22' font-weight='800' fill='#fff'>{html.escape(hub['name'])}</text>")
    out.append(f"<text x='{(hx0 + hx1) / 2}' y='{hy + 4}' text-anchor='middle' font-size='14' fill='#C9D6E8'>{hub['rows']:,} rows</text>")
    out.append(f"<text x='{(hx0 + hx1) / 2}' y='{hy + 24}' text-anchor='middle' font-size='13' fill='#C9D6E8'>{html.escape(hub['surveys'])}</text>")
    out.append(f"<text x='{(hx0 + hx1) / 2}' y='{hy + 50}' text-anchor='middle' font-size='11.5' fill='#9FB3CC'>link: survey + cluster + household</text>")
    out.append("</svg>")
    return "".join(out)


def render():
    C.page_header("Concept maps", "Three visual summaries drawn from your data: what goes with service use, how the tables connect, and how to use the dashboard", ":material/hub:")

    # ---- 1. hub and spoke ------------------------------------------------------------------
    st.markdown("##### 1. What goes with service use?")
    k = C.side().selectbox("Outcome in the centre", list(OUTCOMES), key="fw_out")
    cfg = OUTCOMES[k]
    df = C.apply(C.load(cfg["table"]), cfg["table"])
    spokes = []
    if df is not None and not df.empty:
        for dim in cfg["spokes"]:
            if dim in df.columns or dim == "ANC":
                s = _spoke(df, cfg["col"], dim)
                if s:
                    s["name"] = SPOKE_NAME[dim]
                    spokes.append(s)
    if len(spokes) < 3:
        C.no_data("Not enough groups with data for the current filters. Select more provinces or surveys.")
    else:
        st.markdown(hub_svg(k.split(":")[0] if "dose" not in k else "Measles vaccine (at least one dose)", spokes), unsafe_allow_html=True)
        best = max(spokes, key=lambda s: s["hi_v"] - s["lo_v"])
        C.takeaway(f"For this outcome the biggest difference is by {best['name'].lower()}: {best['hi_l']} {best['hi_v']:.0f}% against {best['lo_l']} {best['lo_v']:.0f}%. "
                   f"Each circle shows the lowest and highest group among {cfg['who']} in the selected surveys (groups under 100 records are left out).")
        st.caption("These are differences between groups, not proof of cause: for example, women who attend four or more antenatal visits may also be richer or live closer to a facility.")
