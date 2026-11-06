# Report notes (for you, not for submission)

## 1. Figures and where they belong

| File | Section in `report_content.md` | What it is |
|---|---|---|
| `fig_profile_missing_heatmap.png` | 2.2 (Fig 2.1) | Real: share missing by variable and decade, OWID |
| `fig_profile_coverage_by_year.png` | 2.5 (Fig 2.2) | Real: countries reporting per year; complete years per country |
| `fig_cleaning_flowchart.png` | 4 (Fig 4.1) | Decision flowchart; the "Found:" notes are read from the profiling JSON |
| `fig_wireframe_1.png` to `fig_wireframe_4.png` | 7.4 (Figs 7.1-7.4) | Mock-ups only; all lines, bars and dots are made up on purpose |
| `fig_profile_distributions.png` | 7.5 (Fig 7.5) | Real: 2022 distributions and a joined log-log preview |
| `fig_workflow_flowchart.png` | 8 (Fig 8.1) | End-to-end pipeline |
| `fig_timeline_gantt.png` | 9 (Fig 9.1) | 32 hours, eight phases, four milestones |

All PNGs are 200 dpi. When you paste into Word, keep the captions from the markdown and renumber if you add or remove figures.

## 2. URLs checked, failures, substitutions

- **No URL failed and no substitution was needed.**
- OWID CSV: `https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv` returned HTTP 200 (14.4 MB).
- World Bank API v2 (`api.worldbank.org/v2/...`) returned JSON for all five indicators plus the country metadata endpoint, with no key.
- Licence and documentation pages were also fetched: the OWID GitHub README, the OWID topic page `ourworldindata.org/co2-and-greenhouse-gas-emissions`, the World Bank public-licences page and the Indicators API documentation page. The OWID codebook (`owid-co2-codebook.csv`) was used to confirm units and sources.
- The raw data was downloaded on 2026-11-05. The World Bank snapshot reports `lastupdated = 2026-10-08`. Re-running with `--refresh` can change counts slightly.

## 3. Things to double-check before you submit

1. **Add your own details.** Name, student ID, course, date and any required cover page are not in `report_content.md`.
2. **Reference details.** I confirmed by fetching: the OWID topic page (authors, year, title), the OWID GitHub repository, the World Bank licences page and the World Bank API documentation page. The journal and book entries (Anscombe, Efron, Grossman & Krueger, Harrower & Brewer, Harris et al., Hunter, McKinney, Peters et al., Stern, Virtanen et al., Waskom, Wilkinson et al.) are written from memory and were **not** fetched here. They are standard, real publications, but check volume and page numbers on Google Scholar before submitting.
3. **Colour-blind check not run.** The report says the palette "will be checked with a colour-vision-deficiency simulator during the visualization phase". That is true as a plan; it has not been done.
4. **Numbers are a snapshot.** Every figure and statistic in the report comes from `data/processed/profiling/profiling_summary.json` produced by `src/profile_data.py`. If you re-download, re-run the script and update the numbers.
5. **The 0.86 correlation is a smoke test.** The report calls it a hint, not a finding. Keep that wording; the assignment is about the plan, not the result.
6. **Two statements are general knowledge, not measured:** that 1990 is a conventional baseline year for climate comparisons, and that the newest years of a release are the most likely to be revised. Soften them if your marker wants a citation.
7. **Length.** The body (excluding references) is about 5,000 words counting tables. If your college counts only prose, it is about 2,400.
8. **Gantt assumption.** The chart assumes about 8 working hours per week over four weeks. Change the wording if your schedule differs; the 32-hour total is what matters.
9. **Wireframes are not results.** The captions and the "WIREFRAME - not real data" banner say so. Do not describe them as findings.
10. **Pandas 3 shows `str` as the text dtype.** If your marker runs older pandas, they will see `object`. This is cosmetic.

## 4. Likely viva / interview questions

**Q1. Why did you join the datasets on ISO3 codes instead of country names?**
Because names differ between sources: in the profiling run 206 countries matched on ISO3 but only 177 matched on exact name, so a name join would silently drop 29 (for example `Egypt` against `Egypt, Arab Rep.`). ISO3 is stable, and I log every entity that fails to match.

**Q2. Why not fill in the missing GDP or CO2 values?**
They are the outcome and the key predictor. Imputing them would partly manufacture the relationship I am trying to study. I drop incomplete rows from paired analyses only and report the sample size. I allow short interpolation (three years or fewer) only for secondary covariates such as industry share, and I flag those cells so I can re-run without them.

**Q3. Why 1990-2022 rather than all available years?**
CO2 and population are almost complete from 1990 (1.6% and 0.9% missing in the window), the World Bank PPP series and OWID consumption-based CO2 start in 1990, and OWID's GDP column ends in 2022. Earlier years are mostly missing: 62% of OWID rows are before 1950.

**Q4. Why log scales and Spearman correlation?**
Per-capita CO2 and GDP are strongly right-skewed (skew 2.53 and 3.25 in 2022), so raw Pearson correlation is dominated by a few extreme countries. In the preview, Pearson on raw values was 0.51, while log-log Pearson was 0.85 and Spearman 0.86. Logs make the relationship closer to linear and ranks remove sensitivity to extremes.

**Q5. Does your analysis show that wealth causes emissions?**
No, and the plan says so. It is a descriptive, country-level exploration. Associations across countries can reflect confounders (energy resources, climate, trade), and countries are not people. The sensitivity analysis (Q10) tests whether the patterns survive different data choices, but it still does not establish causation.
