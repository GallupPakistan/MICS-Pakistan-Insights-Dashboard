# Pakistan MICS dashboard (Streamlit)

12 pages: Overview (KPIs + province map) | Households & housing | Water, sanitation & hygiene | Wealth & equity |
Maternal & newborn health | Child immunisation | Child nutrition | Child mortality & siblings |
Education, gender & children 5-17 | Compare & data explorer | Compare two groups | Inequality & districts.

Sidebar filters (work on every page): province, survey (province + year), area, sex, wealth quintile, district,
"compare charts by", minimum group size, 95% confidence intervals, reset.

## Run it (Windows, Python 3.13 virtual environment)

    cd dashboard
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app.py

The folder `data` already contains the cleaned tables built from your 8 parquet files, so it starts immediately.

## Rebuild the data (after you replace the Punjab files, add the 32 MB HouseholdMembers file, etc.)

    python prepare_data.py "C:\Users\DELL\Desktop\MICS\parquet" "data"

`prepare_data.py` reads MICS_Households / Women / Men / Children_U5 / BirthHistory / SiblingHistory / MosquitoNets /
Children_5to17 (+ MICS_HouseholdMembers if present, which switches on the population pyramid) and writes the small clean
tables into `data`. It also writes `data\prep_log.txt` (what was mapped, share of records with a value per survey).

Original files are never changed.

## Advanced features
* Population-weighted Pakistan estimate (sidebar toggle; province populations are in `POP` in common.py - edit if you prefer other figures)
* Compare two groups with significance tests (page 11)
* Wealth inequality indices (slope index, concentration index) and district rankings with confidence intervals (page 12)
* Explorer with small-multiple panels; ready-made views; shareable web address that stores the filters
* Camera icon on every chart downloads a sharp PNG; every table has a CSV download; use the browser Print > Save as PDF for a page report

Not included: official life-table mortality rates (needs interview-month dates that are not in the data tables) and a district
boundary map (needs a district boundary file).

## Population pyramid
The Education page has a 'Population structure' tab (pyramid, median age, under-15 / 65+ shares, dependency ratio). It covers all 10 surveys (all provinces). Add the other provinces' household-member rows as MICS_HouseholdMembers.parquet and re-run prepare_data.py to extend it.

## New in v5: 3 more pages (15 pages in total)
* Assets & connectivity: television, refrigerator, mobile phone, motorcycle, bank account (by province, wealth ladder, urban/rural, male/female-headed, head's education, renting)
* Child illness & care: diarrhoea, fever, ORS, vitamin A (by age, wealth, mother's education, sanitation vs diarrhoea, illness overlap)
* Fertility & marriage: children ever born, completed fertility, age at first marriage, marriage before 18
Re-run prepare_data.py after adding new files: it now also reads these columns.
