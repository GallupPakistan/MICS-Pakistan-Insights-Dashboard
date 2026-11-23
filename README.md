# MICS Pakistan Insights Dashboard

An interactive, survey-weighted analytics dashboard built on Pakistan's **Multiple Indicator Cluster Surveys (MICS)**.
It brings 10 provincial surveys (2010-2019) into one place and lets you explore **50 standardised indicators** on water and
sanitation, housing, maternal and newborn health, child nutrition, immunisation, mortality, education, gender attitudes and
household assets, with wealth, urban-rural and province comparisons.

**Live app:** https://mics-pakistan-insights-dashboard.streamlit.app/

Built with Python, Streamlit, Pandas and Plotly.

---

## Contents

1. [Key features](#key-features)
2. [Dashboard pages](#dashboard-pages)
3. [Data coverage](#data-coverage)
4. [Methodology](#methodology)
5. [Quick start](#quick-start)
6. [Rebuilding the data](#rebuilding-the-data)
7. [Project structure](#project-structure)
8. [Deployment](#deployment)
9. [Data quality and limitations](#data-quality-and-limitations)
10. [Data source and licence](#data-source-and-licence)

---

## Key features

- **50 indicators** with a documented definition, unit and "better direction" (higher, lower or neutral) for each one.
- **Sidebar filters on every page:** province, survey (province and year), urban or rural, sex, wealth quintile, district,
  "compare charts by", minimum group size, 95% confidence intervals and reset.
- **Equity analysis:** wealth-quintile gradients, urban-rural gaps, slope index and concentration index of inequality,
  and district rankings with confidence intervals.
- **Statistical comparison:** a two-group comparison page with difference, confidence interval, p-value and a
  plain-language verdict.
- **Population-weighted Pakistan estimate:** an optional toggle that turns the five provincial surveys into one
  census-weighted view (province populations are set in `POP` in `common.py`).
- **Province map** of any indicator, using the latest survey of each province.
- **KPI scorecard:** first-versus-last survey change for each province, with a flag for real change versus change within
  the margin of error.
- **Shareable views:** filters are stored in the page address, so a view can be sent as a link.
- **Exports:** the camera icon on any chart saves a high-resolution PNG, every table has a CSV download, and the browser's
  Print > Save as PDF gives a page report.

## Dashboard pages

| Group | Pages |
|---|---|
| Start | Home, Overview |
| Living conditions | Households and housing, Water, sanitation and hygiene, Assets and connectivity |
| Equity | Wealth and equity, Inequality and districts |
| Women and newborns | Maternal and newborn health, Fertility and marriage |
| Children | Child immunisation, Child nutrition, Child mortality and siblings, Child illness and care |
| Education and gender | Education, gender and children 5-17, Women vs men |
| Analysis tools | Compare and data explorer, Compare two groups, KPI scorecard |
| Reference | Research graphics, Concept maps, Data notes (methods, indicator definitions, survey coverage) |

## Data coverage

Each survey is one province in one year. Comparisons over time are valid only within a province.

| Province | Surveys |
|---|---|
| Punjab | 2011, 2014, 2017 |
| Sindh | 2014, 2018 |
| Khyber Pakhtunkhwa | 2016, 2019 |
| Balochistan | 2010, 2019 |
| Gilgit-Baltistan | 2016 |

Records per table (all surveys combined):

| Table | Records | Surveys with data |
|---|---|---|
| Households | 305,642 | all 10 |
| Women 15-49 | 464,668 | all 10 |
| Children under 5 | 255,425 | all 10 |
| Men 15-49 | 80,194 | 4 (Punjab 2017, Sindh 2018, KP 2019, Balochistan 2019) |
| Birth history | 401,088 | same 4 |
| Sibling history | 878,606 | same 4 |
| Children 5-17 | 86,447 | same 4 |
| Mosquito nets | 27,741 | Balochistan 2010 and 2019, Sindh 2014 and 2018 |
| Household members | 2,076,887 | all 10 |

Questions that a survey did not ask are left out, never shown as zero.

## Methodology

- **Weighted percentages** use the sample weight of each table. Groups smaller than the minimum group size (sidebar) are hidden.
- **No mixing of survey years:** KPI cards, the Home hexagons and every chart that is not split by survey use the **latest survey
  of each province** (Punjab 2017, Sindh 2018, KP 2019, Balochistan 2019, GB 2016). Trend and by-survey charts use all 10 surveys.
  Picking surveys in the sidebar overrides this.
- **Population-weighted by default:** each survey is weighted to its province's 2023 census population (`POP` in `common.py`),
  so a value over several provinces reads as a Pakistan estimate for about 2017-2019. Single-province values are not affected.
- **Water and sanitation use the JMP 2017 / MICS6 definitions:** tanker-truck and cart with small tank are improved water
  sources, pond / toba is surface water, and a flush toilet to an unknown place is improved sanitation.
- **Confidence intervals** are approximate (based on effective sample size, without clustering), so they are slightly optimistic.
- **Two-group tests** use a two-sided normal test on the difference between two weighted shares.
- **Inequality indices:** the slope index of inequality (SII) is the weighted regression slope of the indicator on the
  fractional wealth rank; the relative index (RII) is the ratio of fitted values for richest and poorest; the concentration
  index is computed from the weighted covariance of the indicator and the wealth rank.
- **Child mortality** is crude (not an official life-table rate): neonatal and infant deaths use births in the 10 years before
  the survey, and under-5 deaths use births 5-9 years before the survey.
- **Vaccination** shows children aged 12-35 months who received **at least one dose** by card or mother's report. This is
  higher than official full-course coverage.
- **Pakistan estimates** cover the four provinces and GB only (no Islamabad, AJK or ex-FATA before 2018) and combine
  surveys from 2016-2019.

## Quick start

Requirements: Python 3.11 or newer.

```bash
git clone https://github.com/GallupPakistan/MICS-Pakistan-Insights-Dashboard.git
cd MICS-Pakistan-Insights-Dashboard

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

The `data` folder already holds the cleaned tables, so the app starts straight away. The first page load reads all tables
and can take up to a minute; later pages use the cache.

To use data stored elsewhere, set the environment variable `MICS_DASH_DATA` to the folder that contains `hh.parquet`.

## Rebuilding the data

Only needed if you add or replace source files. Place the source `MICS_*.parquet` files in one folder and run:

```bash
python prepare_data.py "path/to/parquet" "data"
```

`prepare_data.py` is the harmonisation layer. It:

- unifies labels (for example `Rural`, `RURAL` and `2.0` become `Rural`);
- merges the same concept stored in several columns (weights, wealth quintile, area, age) into one;
- copies household facts (area, wealth quintile) onto every person-level table;
- computes indicators as 0/1 flags;
- keeps only completed interviews with a sample weight above zero;
- writes the clean tables, `coverage.csv` and `prep_log.txt` (what was mapped, and the share of records with a value per survey).

The original files are never changed.

## Project structure

```
app.py                   Entry point: layout, navigation and sidebar filters
common.py                Data loading, filters, weighted statistics, indicator registry, charts, KPI cards
extras.py                Shared deep-dive charts used on several pages
prepare_data.py          Builds the clean tables from the raw MICS parquet files
views/                   One module per dashboard page
data/                    Clean parquet tables, coverage.csv and prep_log.txt
assets/                  Logo
pakistan_provinces.geojson   Province boundaries for the map
.streamlit/config.toml   Theme and server settings
.github/workflows/       Scheduled job that keeps the hosted app awake
```

## Deployment

The app is hosted on Streamlit Community Cloud. The workflow in `.github/workflows/keep_alive.yml` visits the app every
6 hours and wakes it if it has gone to sleep.

All tables are held in memory (about 330 MB), plus temporary copies while filters run. If the hosted app is slow to load or
restarts, the memory limit of the free tier is the first thing to check.

## Data quality and limitations

Key indicators (water, sanitation, electricity, female-headed households, stunting, wasting, underweight, diarrhoea,
women's schooling, contraception, skilled birth attendance, facility delivery, 4+ antenatal visits, children ever born,
age at marriage) were recomputed independently from the original SPSS files and match the dashboard values. The checks
below are things to keep in mind when using the numbers.

- **Drinking water:** with the JMP 2017 definition Punjab 2017 is 98.3% improved (94.4% → 98.7% → 98.3% over the three
  Punjab rounds). About 15% of Punjab 2017 and Balochistan 2019 households rely on tanker / cart water, which is improved
  but not piped; the water-source chart shows this split.
- **Punjab 2017 siblings who died** is 9.7%, against about 3-4% in the other three sibling-history surveys. The pooled
  figure is driven by this survey.
- **Survey weights** are normalised within each survey, so pooled values mix surveys by sample size.
- **Not included:** official life-table mortality rates (they need interview-month dates that are not in the tables) and a
  district boundary map (it needs a district boundary file).

## Data source and licence

The data come from the Multiple Indicator Cluster Surveys (MICS) of Pakistan's provincial governments, supported by UNICEF.
MICS microdata are shared under UNICEF's terms of use. Check those terms before redistributing the data files, and cite MICS
and the relevant provincial Bureau of Statistics when you publish results from this dashboard.

Add a `LICENSE` file to state the licence for the code in this repository.
