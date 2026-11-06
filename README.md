# CO₂ Emissions and Economic Development

An exploratory data analysis proposal examining how national carbon dioxide emissions relate to income and economic structure. This repository contains the preliminary profiling evidence, reproducible acquisition and figure scripts, an executed notebook, the report draft, and figure designs. It is a proposal and profiling project; the four dashboard wireframes are explicitly mock-ups, not results.

## Project contents

```text
data/
  processed/profiling/       Small profiling tables and JSON summary
  raw/                       Downloaded source data (created when the script runs; ignored by Git)
figures/                     Profiling charts, workflow diagrams, timeline, and wireframes
notebooks/                   Preliminary profiling notebook
report/                      Proposal draft and author notes
src/                         Data profiling and figure-generation scripts
requirements.txt
```

The tracked profiling tables and figures are snapshots from the preliminary run. The raw OWID and World Bank source files are not included; the profiling script downloads them when needed. Some counts can change when the sources are refreshed.

## Data sources

- [Our World in Data CO₂ and GHG emissions](https://github.com/owid/co2-data)
- [World Bank Indicators API v2](https://api.worldbank.org/v2/) — GDP per capita, PPP GDP per capita, population, urban population share, and industry share of GDP

Review the source terms before redistributing data. The report discusses attribution and source limitations.

## Set up

Python 3.11 or newer is recommended (the source bundle was developed with Python 3.13).

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux:        source .venv/bin/activate
pip install -r requirements.txt
```

## Reproduce

Run commands from the repository root:

```bash
python src/profile_data.py
python src/make_figures.py
```

The first command downloads the OWID CSV and World Bank indicator data into `data/raw/`, then writes profiling tables and charts. Add `--refresh` to fetch current source data instead of using cached downloads. The second command regenerates the workflow, cleaning, timeline, and wireframe figures from the profiling summary. The notebook is available at `notebooks/01_preliminary_profiling.ipynb`.

## Preliminary profile

The supplied snapshot reports 36 OWID non-country entities and 44 World Bank aggregates, no duplicate country-year keys in either source, and 206 ISO3 matches across the two sources. In the 1990–2022 study window, 1.61% of OWID CO₂ values are missing. The report frames the 2022 GDP–CO₂-per-capita correlation as a smoke test (197 countries; Spearman 0.86), not a final finding or causal claim. See `report/report_content.md` and `data/processed/profiling/profiling_summary.json` for context and methodology.

## Notes

- `report/report_notes.md` records author checks and limitations; verify its references and personal submission details before using the report academically.
- Figures prefixed `fig_wireframe_` contain fabricated placeholder marks for layout discussion.
- Raw data and the large joined preview are excluded from Git by `.gitignore`.
