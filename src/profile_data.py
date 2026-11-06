"""Preliminary profiling for the CO2-and-economy EDA proposal.

What this script does (all of it is real, nothing is hard-coded):
  1. Downloads the two public datasets into data/raw/ (cached; use --refresh to re-download)
       - Our World in Data (OWID) CO2 & GHG dataset (one CSV)
       - World Bank Open Data indicators via the public v2 API (JSON, no key)
  2. Profiles both: shape, dtypes, missing values, duplicates, year/entity coverage,
     outliers and impossible values, aggregate rows, cross-source key matching.
  3. Writes tables to data/processed/profiling/ and a machine-readable
     profiling_summary.json; writes three figures to figures/.

Usage (from the project root):
    python src/profile_data.py            # use cached raw files if present
    python src/profile_data.py --refresh  # force a fresh download
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib.pyplot as plt  # noqa: E402
import style  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
PROF = PROC / "profiling"

OWID_URL = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"
WB_BASE = "https://api.worldbank.org/v2"
WB_INDICATORS = {
    "NY.GDP.PCAP.KD": "gdp_per_capita_const2015usd",
    "NY.GDP.PCAP.PP.KD": "gdp_per_capita_ppp_const2021intl",
    "SP.POP.TOTL": "population_wb",
    "SP.URB.TOTL.IN.ZS": "urban_pop_pct",
    "NV.IND.TOTL.ZS": "industry_value_added_pct_gdp",
}
KEY_OWID_COLS = [
    "population", "gdp", "co2", "co2_per_capita", "co2_per_gdp", "co2_including_luc",
    "coal_co2", "oil_co2", "gas_co2", "cement_co2", "flaring_co2", "land_use_change_co2",
    "methane", "nitrous_oxide", "total_ghg", "consumption_co2", "trade_co2",
    "primary_energy_consumption", "energy_per_capita", "energy_per_gdp",
    "temperature_change_from_ghg", "share_global_co2", "cumulative_co2",
]


# --------------------------------------------------------------------------- acquisition
def download_owid(refresh: bool) -> Path:
    path = RAW / "owid-co2-data.csv"
    if refresh or not path.exists():
        r = requests.get(OWID_URL, timeout=120)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path


def _wb_get(url: str, params: dict) -> list:
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=90)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))


def download_worldbank(refresh: bool) -> tuple[Path, Path]:
    long_path = RAW / "worldbank_indicators_long.csv"
    meta_path = RAW / "worldbank_country_metadata.csv"
    if not refresh and long_path.exists() and meta_path.exists():
        return long_path, meta_path

    frames = []
    for code, name in WB_INDICATORS.items():
        payload = _wb_get(f"{WB_BASE}/country/all/indicator/{code}",
                          {"format": "json", "per_page": 20000, "date": "1960:2025"})
        header, rows = payload[0], payload[1]
        if header["pages"] != 1:
            raise RuntimeError(f"{code}: expected 1 page, got {header['pages']}")
        (RAW / f"wb_{code}.json").write_text(json.dumps(payload), encoding="utf-8")
        df = pd.DataFrame({
            "country_name": [x["country"]["value"] for x in rows],
            "wb_country_id": [x["country"]["id"] for x in rows],
            "iso3": [x["countryiso3code"] for x in rows],
            "year": [int(x["date"]) for x in rows],
            "indicator": name,
            "value": [x["value"] for x in rows],
        })
        df["source_last_updated"] = header.get("lastupdated")
        frames.append(df)
    pd.concat(frames, ignore_index=True).to_csv(long_path, index=False)

    meta = _wb_get(f"{WB_BASE}/country", {"format": "json", "per_page": 1000})[1]
    pd.DataFrame({
        "iso3": [m["id"] for m in meta],
        "name": [m["name"] for m in meta],
        "region": [m["region"]["value"] for m in meta],
        "income_level": [m["incomeLevel"]["value"] for m in meta],
    }).to_csv(meta_path, index=False)
    return long_path, meta_path


# --------------------------------------------------------------------------- helpers
def missing_table(df: pd.DataFrame) -> pd.DataFrame:
    t = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "n_missing": df.isna().sum(),
        "pct_missing": (df.isna().mean() * 100).round(2),
        "n_unique": df.nunique(),
    })
    return t.sort_values("pct_missing", ascending=False)


def iqr_outliers(s: pd.Series, log: bool = False) -> dict:
    s = s.dropna()
    s = s[s > 0] if log else s
    x = np.log10(s) if log else s
    q1, q3 = x.quantile([0.25, 0.75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mask = (x < lo) | (x > hi)
    return {"n": int(len(s)), "n_outliers": int(mask.sum()),
            "pct_outliers": round(100 * mask.mean(), 2), "log10_scale": log}


# --------------------------------------------------------------------------- profiling
def main(refresh: bool = False) -> dict:
    PROF.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    style.apply_style()
    S: dict = {}  # summary

    owid_path = download_owid(refresh)
    wb_path, meta_path = download_worldbank(refresh)
    owid = pd.read_csv(owid_path)
    wb = pd.read_csv(wb_path, keep_default_na=False, na_values=[""])
    meta = pd.read_csv(meta_path, keep_default_na=False, na_values=[""])

    # ---------------- OWID
    o = {}
    o["file_size_mb"] = round(owid_path.stat().st_size / 1e6, 2)
    o["shape"] = list(owid.shape)
    o["year_min"], o["year_max"] = int(owid.year.min()), int(owid.year.max())
    o["n_entities"] = int(owid.country.nunique())
    o["dtype_counts"] = owid.dtypes.astype(str).value_counts().to_dict()
    o["duplicate_full_rows"] = int(owid.duplicated().sum())
    o["duplicate_country_year"] = int(owid.duplicated(["country", "year"]).sum())
    o["memory_mb"] = round(owid.memory_usage(deep=True).sum() / 1e6, 2)

    mt = missing_table(owid)
    mt.to_csv(PROF / "owid_missing_by_column.csv")
    o["n_cols_over_50pct_missing"] = int((mt.pct_missing > 50).sum())
    o["n_cols_over_20pct_missing"] = int((mt.pct_missing > 20).sum())
    o["median_pct_missing_across_cols"] = round(float(mt.pct_missing.median()), 2)
    o["pct_missing_selected"] = mt.loc[
        [c for c in ["population", "gdp", "co2", "co2_per_capita", "energy_per_capita",
                     "consumption_co2", "trade_co2", "methane", "total_ghg",
                     "primary_energy_consumption", "land_use_change_co2", "iso_code"] if c in mt.index],
        "pct_missing"].to_dict()

    # Non-country entities (aggregates): iso_code missing or OWID_ prefix
    is_agg = owid.iso_code.isna() | owid.iso_code.astype(str).str.startswith("OWID_")
    agg_ents = (owid[is_agg].groupby("country").agg(rows=("year", "size"), first=("year", "min"),
                                                      last=("year", "max"),
                                                      iso=("iso_code", "first")).reset_index())
    agg_ents.to_csv(PROF / "owid_non_country_entities.csv", index=False)
    o["n_non_country_entities"] = int(len(agg_ents))
    o["n_non_country_rows"] = int(is_agg.sum())
    o["pct_rows_non_country"] = round(100 * is_agg.mean(), 2)
    o["non_country_examples"] = agg_ents.country.head(12).tolist()
    o["owid_prefixed_iso_codes"] = sorted(owid.loc[owid.iso_code.astype(str).str.startswith("OWID_"),
                                                   "iso_code"].unique().tolist())
    o["iso_missing_entities"] = int(owid.loc[owid.iso_code.isna(), "country"].nunique())
    countries = owid[~is_agg].copy()
    o["n_countries_proper"] = int(countries.country.nunique())
    o["bad_iso_length"] = int((countries.iso_code.str.len() != 3).sum())

    # Coverage
    key_cov = {}
    for c in ["co2", "co2_per_capita", "gdp", "population", "primary_energy_consumption",
              "consumption_co2", "methane"]:
        sub = countries[countries[c].notna()]
        key_cov[c] = {"first_year": int(sub.year.min()), "last_year": int(sub.year.max()),
                      "n_countries": int(sub.country.nunique())}
    o["coverage_countries_only"] = key_cov
    cov_by_year = (countries.groupby("year")[["co2", "gdp", "population", "primary_energy_consumption",
                                              "consumption_co2"]].count())
    cov_by_year.to_csv(PROF / "owid_coverage_by_year.csv")
    last = o["year_max"]
    o["rows_in_last_year"] = int((countries.year == last).sum())
    o["co2_nonnull_in_last_year"] = int(countries.loc[countries.year == last, "co2"].notna().sum())
    o["gdp_nonnull_in_last_year"] = int(countries.loc[countries.year == last, "gdp"].notna().sum())
    o["last_year_with_gdp"] = int(countries.loc[countries.gdp.notna(), "year"].max())
    o["gdp_nonnull_in_last_gdp_year"] = int(countries.loc[countries.year == o["last_year_with_gdp"], "gdp"].notna().sum())

    # Study window used throughout the proposal
    W0, W1 = 1990, 2022
    win = countries[(countries.year >= W0) & (countries.year <= W1)]
    o["window"] = [W0, W1]
    o["window_rows"] = int(len(win))
    o["window_co2_pct_missing"] = round(float(win.co2.isna().mean() * 100), 2)
    o["window_gdp_pct_missing"] = round(float(win.gdp.isna().mean() * 100), 2)
    o["window_pop_pct_missing"] = round(float(win.population.isna().mean() * 100), 2)
    o["window_co2_pc_pct_missing"] = round(float(win.co2_per_capita.isna().mean() * 100), 2)

    # Impossible / suspicious values
    num = owid.select_dtypes("number")
    neg_ok = {"land_use_change_co2", "co2_including_luc", "trade_co2", "co2_growth_abs", "co2_growth_prct",
              "co2_including_luc_growth_abs", "co2_including_luc_growth_prct",
              "co2_including_luc_per_capita", "co2_including_luc_per_gdp", "co2_including_luc_per_unit_energy",
              "land_use_change_co2_per_capita", "cumulative_luc_co2", "cumulative_co2_including_luc",
              "share_global_luc_co2", "share_global_co2_including_luc",
              "share_global_cumulative_luc_co2", "share_global_cumulative_co2_including_luc",
              "ghg_per_capita", "total_ghg", "nitrous_oxide", "temperature_change_from_ghg"}
    neg_counts = {c: int((num[c] < 0).sum()) for c in num.columns if (num[c] < 0).any()}
    o["negative_values_by_column"] = neg_counts
    o["unexpected_negative_columns"] = {c: n for c, n in neg_counts.items()
                                         if c in ("co2", "population", "gdp", "co2_per_capita",
                                                  "coal_co2", "oil_co2", "gas_co2", "cement_co2",
                                                  "primary_energy_consumption")}
    o["zero_co2_rows_countries"] = int((countries.co2 == 0).sum())
    o["share_gt_100"] = int((owid.filter(like="share_global_") > 100).sum().sum())
    o["trade_co2_negative_rows"] = int((owid.trade_co2 < 0).sum())

    # Outliers in the last full year (countries only)
    y = countries[countries.year == W1]
    o["outliers_co2_per_capita_2022"] = iqr_outliers(y.co2_per_capita)
    o["outliers_co2_per_capita_2022_log"] = iqr_outliers(y.co2_per_capita, log=True)
    o["outliers_co2_2022_log"] = iqr_outliers(y.co2, log=True)
    top = y.nlargest(10, "co2_per_capita")[["country", "iso_code", "population", "co2_per_capita"]]
    top.to_csv(PROF / "owid_top10_co2_per_capita_2022.csv", index=False)
    o["top5_co2_per_capita_2022"] = top.head(5)[["country", "co2_per_capita"]].round(2).to_dict("records")
    o["top5_pop_of_top_per_capita"] = top.head(5)[["country", "population"]].to_dict("records")
    o["co2_per_capita_2022_median"] = round(float(y.co2_per_capita.median()), 2)
    o["co2_per_capita_2022_max_over_median"] = round(float(y.co2_per_capita.max() / y.co2_per_capita.median()), 1)
    o["skew_co2_pc_2022"] = round(float(y.co2_per_capita.skew()), 2)
    o["skew_log_co2_pc_2022"] = round(float(np.log10(y.co2_per_capita[y.co2_per_capita > 0]).skew()), 2)
    # small-population effect
    small = y[y.population < 1e6]
    o["n_countries_pop_lt_1m_2022"] = int(len(small))
    o["n_small_in_top20_pc"] = int(y.nlargest(20, "co2_per_capita").population.lt(1e6).sum())

    # ---------------- World Bank
    w = {}
    w["file_size_mb"] = round(wb_path.stat().st_size / 1e6, 2)
    w["shape_long"] = list(wb.shape)
    w["indicators"] = WB_INDICATORS
    w["source_last_updated"] = str(wb.source_last_updated.dropna().unique().tolist())
    wb = wb.merge(meta[["iso3", "region"]], on="iso3", how="left")
    wb["is_aggregate"] = wb.region.eq("Aggregates")
    w["n_entities"] = int(wb.country_name.nunique())
    w["n_aggregates"] = int(wb[wb.is_aggregate].country_name.nunique())
    w["n_without_metadata_match"] = int(wb[wb.region.isna()].country_name.nunique())
    w["unmatched_metadata_examples"] = wb[wb.region.isna()].country_name.unique()[:5].tolist()
    w["year_min"], w["year_max"] = int(wb.year.min()), int(wb.year.max())
    w["duplicate_rows_entity_year_indicator"] = int(wb.duplicated(["wb_country_id", "year", "indicator"]).sum())
    w["rows_with_blank_iso3"] = int(wb.iso3.isna().sum())
    w["entities_with_blank_iso3"] = sorted(wb.loc[wb.iso3.isna(), "country_name"].unique().tolist())
    wb["value"] = pd.to_numeric(wb["value"], errors="coerce")

    wide = (wb[~wb.is_aggregate & wb.region.notna()]
            .pivot(index=["iso3", "country_name", "year"], columns="indicator", values="value")
            .reset_index())
    wide.columns.name = None
    wide.to_csv(PROC / "worldbank_wide_countries_preview.csv", index=False)
    w["n_country_rows_wide"] = int(len(wide))
    w["n_countries"] = int(wide.iso3.nunique())
    wmt = missing_table(wide[list(WB_INDICATORS.values())])
    wmt.to_csv(PROF / "worldbank_missing_by_indicator.csv")
    w["pct_missing_by_indicator"] = wmt.pct_missing.to_dict()
    wwin = wide[(wide.year >= W0) & (wide.year <= W1)]
    w["window_pct_missing_by_indicator"] = {c: round(float(wwin[c].isna().mean() * 100), 2)
                                            for c in WB_INDICATORS.values()}
    w["last_year_any_gdp"] = int(wide.loc[wide.gdp_per_capita_const2015usd.notna(), "year"].max())
    ly = w["last_year_any_gdp"]
    w["gdp_countries_in_last_gdp_year"] = int(wide.loc[wide.year == ly, "gdp_per_capita_const2015usd"].notna().sum())
    w["gdp_countries_2022"] = int(wide.loc[wide.year == 2022, "gdp_per_capita_const2015usd"].notna().sum())
    w["gdp_countries_2023"] = int(wide.loc[wide.year == 2023, "gdp_per_capita_const2015usd"].notna().sum())
    w["gdp_countries_2024"] = int(wide.loc[wide.year == 2024, "gdp_per_capita_const2015usd"].notna().sum())
    w["industry_countries_2022"] = int(wide.loc[wide.year == 2022, "industry_value_added_pct_gdp"].notna().sum())
    w["ppp_first_year"] = int(wide.loc[wide.gdp_per_capita_ppp_const2021intl.notna(), "year"].min())
    wnum = wide[list(WB_INDICATORS.values())]
    w["nonpositive_gdp_or_pop"] = int(((wnum.gdp_per_capita_const2015usd <= 0) |
                                       (wnum.population_wb <= 0)).sum())
    w["pct_outside_0_100_urban_industry"] = int(((wnum.urban_pop_pct < 0) | (wnum.urban_pop_pct > 100) |
                                                  (wnum.industry_value_added_pct_gdp < 0) |
                                                  (wnum.industry_value_added_pct_gdp > 100)).sum())
    w["negative_industry_share_rows"] = int((wnum.industry_value_added_pct_gdp < 0).sum())
    wy = wide[wide.year == W1]
    w["outliers_gdp_pc_2022_log"] = iqr_outliers(wy.gdp_per_capita_const2015usd, log=True)
    w["gdp_pc_2022_median"] = round(float(wy.gdp_per_capita_const2015usd.median()), 0)
    w["gdp_pc_2022_max_over_min"] = round(float(wy.gdp_per_capita_const2015usd.max() /
                                                wy.gdp_per_capita_const2015usd.min()), 0)
    topg = wy.nlargest(5, "gdp_per_capita_const2015usd")[["country_name", "gdp_per_capita_const2015usd"]]
    w["top5_gdp_pc_2022"] = topg.round(0).to_dict("records")
    w["skew_gdp_pc_2022"] = round(float(wy.gdp_per_capita_const2015usd.skew()), 2)
    w["skew_log_gdp_pc_2022"] = round(float(np.log10(wy.gdp_per_capita_const2015usd.dropna()).skew()), 2)

    # ---------------- Key matching
    km = {}
    owid_c = countries[["country", "iso_code"]].drop_duplicates()
    wb_c = wide[["iso3", "country_name"]].drop_duplicates()
    km["owid_country_iso_pairs"] = int(len(owid_c))
    km["wb_country_iso_pairs"] = int(len(wb_c))
    iso_match = set(owid_c.iso_code) & set(wb_c.iso3)
    km["iso3_matched"] = len(iso_match)
    km["owid_unmatched_iso"] = owid_c[~owid_c.iso_code.isin(wb_c.iso3)].sort_values("country")
    km["wb_unmatched_iso"] = wb_c[~wb_c.iso3.isin(owid_c.iso_code)].sort_values("country_name")
    km["owid_unmatched_iso"].to_csv(PROF / "key_match_owid_not_in_worldbank.csv", index=False)
    km["wb_unmatched_iso"].to_csv(PROF / "key_match_worldbank_not_in_owid.csv", index=False)
    # Name-based join for comparison
    name_match = set(owid_c.country) & set(wb_c.country_name)
    km["name_matched"] = len(name_match)
    both = owid_c.merge(wb_c, left_on="iso_code", right_on="iso3")
    both["name_equal"] = both.country == both.country_name
    mism = both[~both.name_equal][["iso_code", "country", "country_name"]].sort_values("iso_code")
    mism.to_csv(PROF / "key_match_name_mismatches_for_matched_iso.csv", index=False)
    km["iso_matched_but_name_differs"] = int(len(mism))
    km["name_mismatch_examples"] = mism.head(8).to_dict("records")
    km["owid_unmatched_n"] = int(len(km["owid_unmatched_iso"]))
    km["wb_unmatched_n"] = int(len(km["wb_unmatched_iso"]))
    km["owid_unmatched_names"] = km["owid_unmatched_iso"].country.tolist()
    km["wb_unmatched_names"] = km["wb_unmatched_iso"].country_name.tolist()
    for k in ("owid_unmatched_iso", "wb_unmatched_iso"):
        km.pop(k)

    # Joined frame
    j = countries.merge(wide, left_on=["iso_code", "year"], right_on=["iso3", "year"], how="inner")
    jw = j[(j.year >= W0) & (j.year <= W1)]
    km["joined_rows_all_years"] = int(len(j))
    km["joined_rows_window"] = int(len(jw))
    km["joined_countries_window"] = int(jw.iso_code.nunique())
    both_gdp = jw.dropna(subset=["co2_per_capita", "gdp_per_capita_const2015usd"])
    km["complete_pairs_co2pc_gdppc_window"] = int(len(both_gdp))
    km["complete_pair_countries_window"] = int(both_gdp.iso_code.nunique())
    km["pct_window_rows_complete_pairs"] = round(100 * len(both_gdp) / len(jw), 1)
    full33 = both_gdp.groupby("iso_code").size()
    km["countries_with_all_33_years_complete"] = int((full33 == (W1 - W0 + 1)).sum())
    km["countries_with_ge_25_years_complete"] = int((full33 >= 25).sum())
    c2022 = j[(j.year == W1)].dropna(subset=["co2_per_capita", "gdp_per_capita_const2015usd"])
    km["countries_complete_pair_2022"] = int(len(c2022))
    # Cross-source validation: population
    pj = jw.dropna(subset=["population", "population_wb"])
    rel = ((pj.population - pj.population_wb).abs() / pj.population_wb)
    km["population_rel_diff_median_pct"] = round(float(rel.median() * 100), 3)
    km["population_rel_diff_p99_pct"] = round(float(rel.quantile(0.99) * 100), 2)
    km["population_rel_diff_gt5pct_rows"] = int((rel > 0.05).sum())
    km["population_rel_diff_gt5pct_countries"] = pj.loc[rel > 0.05, "iso_code"].nunique()
    km["population_rel_diff_gt5pct_examples"] = pj.loc[rel > 0.05, "country"].value_counts().head(5).to_dict()
    # GDP cross-check: OWID gdp (total, 2011 int-$) / pop vs WB PPP per capita (different base year)
    gj = jw.dropna(subset=["gdp", "population", "gdp_per_capita_ppp_const2021intl"])
    ratio = (gj.gdp / gj.population) / gj.gdp_per_capita_ppp_const2021intl
    km["owid_gdp_pc_vs_wb_ppp_ratio_median"] = round(float(ratio.median()), 3)
    km["owid_gdp_pc_vs_wb_ppp_ratio_iqr"] = [round(float(ratio.quantile(.25)), 3), round(float(ratio.quantile(.75)), 3)]
    gl = j.dropna(subset=["gdp"]).year.max()
    km["owid_gdp_last_year_in_join"] = int(gl)
    # Pearson / Spearman preview (log-log, 2022) - a preview only, not a result of the final analysis
    if len(c2022) > 10:
        lx, ly_ = np.log10(c2022.gdp_per_capita_const2015usd), np.log10(c2022.co2_per_capita.clip(lower=1e-3))
        km["preview_log_pearson_2022"] = round(float(lx.corr(ly_)), 3)
        km["preview_spearman_2022"] = round(float(c2022.gdp_per_capita_const2015usd.corr(
            c2022.co2_per_capita, method="spearman")), 3)
        km["preview_raw_pearson_2022"] = round(float(c2022.gdp_per_capita_const2015usd.corr(c2022.co2_per_capita)), 3)
    j.to_csv(PROC / "joined_preview_owid_worldbank.csv", index=False)

    S["owid"], S["worldbank"], S["join"] = o, w, km

    # ---------------- Figures
    # 1) Missing-value heatmap: share missing by decade, key OWID columns, countries only
    cols = [c for c in KEY_OWID_COLS if c in countries.columns]
    dec = (countries.assign(decade=(countries.year // 10) * 10)
           .query("decade >= 1850")
           .groupby("decade")[cols].agg(lambda s: s.isna().mean() * 100).T)
    dec = dec.loc[dec.mean(axis=1).sort_values().index]
    fig, ax = plt.subplots(figsize=(9, 7.2))
    im = ax.imshow(dec.values, aspect="auto", cmap=style_cmap(), vmin=0, vmax=100)
    ax.set_xticks(range(len(dec.columns)), [f"{d}s" for d in dec.columns], rotation=60, fontsize=8)
    ax.set_yticks(range(len(dec.index)), dec.index, fontsize=8.5)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("% of country-year rows missing")
    ax.set_title("OWID CO2 dataset: missingness is driven by time, not by column alone")
    ax.set_xlabel("Countries only (aggregates removed), 1850 onwards. Darker = more missing.",
                  fontsize=8.5, labelpad=8)
    style.save(fig, "fig_profile_missing_heatmap.png")

    # 2) Coverage by year
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.4), gridspec_kw={"width_ratios": [1.15, 1]})
    cy = cov_by_year.loc[1900:]
    for col, colr, lab in [("co2", style.BLUE, "CO2 (OWID)"), ("population", style.ORANGE, "Population (OWID)"),
                           ("gdp", style.AQUA, "GDP (OWID)"),
                           ("primary_energy_consumption", style.MAGENTA, "Primary energy (OWID)")]:
        axs[0].plot(cy.index, cy[col], color=colr, lw=2, label=lab)
    wcov = wide.groupby("year").gdp_per_capita_const2015usd.count()
    axs[0].plot(wcov.index, wcov.values, color=style.INK2, lw=2, ls="--", label="GDP per capita (World Bank)")
    axs[0].set_title("Countries reporting each variable, by year")
    axs[0].set_ylabel("number of countries")
    axs[0].axvspan(W0, W1, color=style.SEQ[0], alpha=0.45, lw=0)
    axs[0].text(W0 + 1, 8, "study window\n1990-2022", fontsize=8, color=style.INK2)
    axs[0].legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    axs[0].set_xlim(1900, last)
    # right: per-country # complete years in window
    cnt = both_gdp.groupby("iso_code").size()
    axs[1].hist(cnt, bins=np.arange(0.5, 34.5, 1), color=style.BLUE, edgecolor="white", lw=0.6)
    axs[1].set_title("Complete CO2 + GDP-per-capita years per country")
    axs[1].set_xlabel("years with both values present (of 33, 1990-2022)")
    axs[1].set_ylabel("number of countries")
    style.save(fig, "fig_profile_coverage_by_year.png")

    # 3) Distributions / outliers
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 4.2))
    v = y.co2_per_capita.dropna()
    axs[0].hist(v, bins=40, color=style.BLUE, edgecolor="white", lw=0.5)
    axs[0].set_title("CO2 per capita, 2022 (raw)")
    axs[0].set_xlabel("tonnes per person")
    axs[0].set_ylabel("countries")
    axs[0].text(0.97, 0.9, f"skew = {o['skew_co2_pc_2022']}", transform=axs[0].transAxes, ha="right", fontsize=9)
    axs[1].hist(np.log10(v[v > 0]), bins=40, color=style.AQUA, edgecolor="white", lw=0.5)
    axs[1].set_title("CO2 per capita, 2022 (log10)")
    axs[1].set_xlabel("log10(tonnes per person)")
    axs[1].text(0.97, 0.9, f"skew = {o['skew_log_co2_pc_2022']}", transform=axs[1].transAxes, ha="right", fontsize=9)
    g = wy.gdp_per_capita_const2015usd.dropna()
    axs[2].scatter(c2022.gdp_per_capita_const2015usd, c2022.co2_per_capita, s=22, color=style.BLUE,
                   edgecolor="white", lw=0.6, alpha=0.9)
    axs[2].set_xscale("log"); axs[2].set_yscale("log")
    axs[2].set_title("Joined preview, 2022 (log-log)")
    axs[2].set_xlabel("GDP per capita (const. 2015 US$)")
    axs[2].set_ylabel("CO2 per capita (t)")
    for _, r in c2022.nlargest(1, "co2_per_capita").iterrows():
        axs[2].annotate(r["country"], (r.gdp_per_capita_const2015usd, r.co2_per_capita), fontsize=8,
                        xytext=(4, 3), textcoords="offset points", color=style.INK2)
    fig.suptitle("Skewed distributions justify log scales and rank-based statistics",
                 x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    style.save(fig, "fig_profile_distributions.png")

    (PROF / "profiling_summary.json").write_text(json.dumps(S, indent=2, default=str), encoding="utf-8")
    return S


def style_cmap():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("seq_blue", ["#ffffff"] + style.SEQ[1:])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-download raw data")
    args = ap.parse_args()
    summary = main(args.refresh)
    print(json.dumps(summary, indent=2, default=str))
