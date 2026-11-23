# Review changes (November 2026)

The dashboard was reviewed page by page and its numbers were checked against the original SPSS files.

## What was checked
- The `data` tables were rebuilt from the cleaned CSV files. They were identical to the old tables (difference 0.0 on every indicator).
- 15 key indicators were recomputed independently from the original SPSS files using raw codes and standard MICS
  definitions: water, sanitation, electricity, female-headed households, stunting, wasting, underweight, diarrhoea,
  women's schooling, contraception, skilled birth attendance, facility delivery, 4+ antenatal visits, children ever born
  and age at marriage. They match. The only gaps are skilled birth attendance (within 1 point) and Balochistan 2010
  wasting (0.7 points, a difference in how flagged z-scores are handled).
- All 21 pages were run and every page loads without errors.

## Fixed: numbers
| Issue | Before | After |
|---|---|---|
| Improved drinking water used the old definition, with tanker and cart counted as unimproved. JMP 2017 / MICS6 count them as improved. | Punjab 2017 83.7%, Balochistan 2019 71.7% | Punjab 2017 98.3%, Balochistan 2019 85.9% (matches SPSS) |
| A flush toilet to an unknown place was counted as unimproved. JMP counts it as improved. | Balochistan 2010 63.5% | 66.0% |
| Fertility page: Punjab was missing because the wrong column was read. Now uses CEB and WAGEM. | No Punjab data; marriage age missing for 4 surveys | All 10 surveys |
| Refrigerator for Punjab 2011 was shown as "not asked", but the question was asked. | n/a | 44.3% |
| Motorcycle for Sindh 2014 was shown as "not asked", but the question was asked. | n/a | 39.3% |
| Vitamin A for Punjab 2011 was shown as "not asked", but the question was asked. | n/a | 65.5% |
| Children 5-17, Sindh 2018: sex was empty (stored as HL4). | No boys/girls split | Fixed |

## Fixed: analysis method
- **No more mixing survey years.** KPI cards, the Home hexagons and province, area and wealth charts used to combine
  2010-2019 rounds; for example, "Punjab" was Punjab 2011 + 2014 + 2017 together. They now use the latest survey of each
  province. Trend charts still show every survey, and picking surveys in the sidebar overrides the rule.
- **Population weighting is now on by default.** Values over several provinces are now a Pakistan estimate weighted by
  the 2023 census, instead of a mix driven by sample sizes. The weighting is now applied per survey.
- **Scorecard heatmaps** were coloured by raw value, so high stunting looked "good". Colours are now green for better and
  red for worse within each row, and lower-is-better rows are flipped.
- **KPI scorecard targets** used to be an arbitrary 90% / 20% for every indicator. Targets are now filled in only where
  an international benchmark exists (SDG 6/7, Immunization Agenda 2030, WHA wasting below 5%).
- **Chart order:** mother's age at birth, birth interval and birth order now run in their natural order.
- **Trend charts:** the percentage axis no longer runs to 120%.

## Second pass: visual analysis of every page
- **School attendance (children 5-17) was overstated.** It was calculated only among children who had ever been to school.
  It is now out of all children 5-17, and matches SPSS exactly.
  Before → after: Balochistan 2019 75.6% → **30.9%**, KP 2019 87.8% → **63.9%**, Punjab 2017 86.3% → **76.7%**, Sindh 2018 85.6% → **52.8%**.
- **Line charts by age or wealth** joined points in alphabetical order ("0-5 m, 12-23 m, ..., 6-11 m"), so the lines
  zig-zagged and one province looked like two lines. The points are now joined in the right order (diarrhoea and
  stunting by age, the asset ladder).
- **Mosquito nets:** the "age of the net" chart was wrong. Most MICS6 answers are 0 or "more than 36 months", and the
  second group was being dropped, so Balochistan 2019 showed "100% under 1 year". The chart is removed. "Nets per
  household" was removed too, because the table has one row per net, not per household. It is replaced by the share
  of nets slept under last night.
- **Gap charts (wealth / urban-rural)** painted a big gap favouring the rich in "good" green. Bars now use one colour per
  direction, and the bar length shows the size of the inequality.
- **Scorecard heatmaps:** context indicators (female-headed households, rented dwelling, caesarean) are now shown
  neutral instead of good or bad.
- **Inequality page:** the KPI cards averaged the slope and concentration indices over 2010-2019. They now use the
  latest surveys.
- **Compare two groups:** removed "trace 0" from the legend.

## Removed (extras)
- Duplicate "Deep dive" charts: the immunisation scorecard and province chart (already at the top of the page), the
  province comparison on Assets and Equity, and the automatic drill-down chart (it repeated each page's main chart).
- Explorer: the "indicators across surveys" line (it joined different provinces into one line), the province bar
  chart with 10 indicators (unreadable) and the two-indicator scatter.
- Compare two groups: the evidence-strength, relative-difference, verdict-count and record-count charts, which
  repeated the KPI cards.
- Child illness: the sanitation vs diarrhoea scatter (10 dots, no pattern, implies a cause). It is replaced by urban vs
  rural.
- Child nutrition: the "early learning" KPI card (not a nutrition indicator; still available in the scorecard and
  explorer).
- "Deep dive" blocks on the Fertility and Inequality pages. They showed indicators unrelated to the page, such as
  caesarean and contraception on Fertility.
- Concept maps: the technical "how the tables link" diagram and the how-to cards, which repeated the Home page.

## Still worth knowing
- Vaccination counts **any dose**, so it is higher than official full-course coverage. The official "fully vaccinated"
  indicator (BCG, Polio3, Penta3, Measles by 12-23 months) is not in the dashboard.
- Mortality rates are crude, not official life-table rates.
- Punjab 2017 sibling deaths are 9.7%, against 3-4% in the other three surveys. This is in the source data.
- The Pakistan estimate covers the four provinces and GB only (no Islamabad or AJK), using surveys from 2016-2019.
