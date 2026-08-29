"""Annual basin-scale runoff accuracy assessment."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Mapping

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    import geopandas as gpd


def compute_basin_metrics(
    data: pd.DataFrame,
    columns: Mapping[str, str],
    start_year: int,
    end_year: int,
    minimum_years: int = 3,
) -> pd.DataFrame:
    """Calculate annual accuracy metrics independently for every basin."""
    basin = columns["basin_id"]
    year = columns["year"]
    observed = columns["observed"]
    modeled = columns["modeled"]
    required = {basin, year, observed, modeled}
    missing = sorted(required.difference(data.columns))
    if missing:
        raise KeyError(f"Runoff table is missing columns: {missing}")

    frame = data.loc[:, [basin, year, observed, modeled]].copy()
    original_year = frame[year].copy()
    numeric_year = pd.to_numeric(original_year, errors="coerce")
    parsed_year = pd.to_datetime(original_year, errors="coerce").dt.year
    frame[year] = numeric_year.where(numeric_year.notna(), parsed_year)
    frame[observed] = pd.to_numeric(frame[observed], errors="coerce")
    frame[modeled] = pd.to_numeric(frame[modeled], errors="coerce")
    frame = frame.loc[frame[year].between(start_year, end_year)]
    frame = frame.loc[
        np.isfinite(frame[observed])
        & np.isfinite(frame[modeled])
        & (frame[observed] > 0)
        & (frame[modeled] > 0)
    ]

    rows = []
    for basin_id, group in frame.groupby(basin, sort=True):
        obs = group[observed].to_numpy(dtype="float64")
        sim = group[modeled].to_numpy(dtype="float64")
        n = obs.size
        difference = sim - obs
        model_mean = np.mean(sim) if n else np.nan
        reference_sum = np.sum(obs) if n else np.nan
        mae = np.mean(np.abs(difference)) if n else np.nan
        valid = n >= minimum_years and model_mean > 0 and reference_sum > 0
        rows.append(
            {
                "basin_id": basin_id,
                "n_years": n,
                "mbe_mm": np.mean(difference) if valid else np.nan,
                "mae_mm": mae if valid else np.nan,
                "rmse_mm": np.sqrt(np.mean(difference**2)) if valid else np.nan,
                "pbias_percent": 100.0 * np.sum(difference) / reference_sum if valid else np.nan,
                "model_multiannual_mean_mm": model_mean if valid else np.nan,
                "nmae_fraction": mae / model_mean if valid else np.nan,
                "nmae_percent": 100.0 * mae / model_mean if valid else np.nan,
            }
        )
    return pd.DataFrame(rows)


def assign_climate_regions(
    metrics: pd.DataFrame,
    gage_points_file: str | Path,
    gage_id_field: str,
    regions: "gpd.GeoDataFrame",
    region_name_field: str,
    region_code_field: str,
) -> pd.DataFrame:
    """Assign each gage point to one climate region and merge basin metrics."""
    import geopandas as gpd

    gages = gpd.read_file(gage_points_file)[[gage_id_field, "geometry"]].copy()
    selected_regions = regions[
        [region_name_field, region_code_field, "geometry"]
    ].copy()
    gages = gages.to_crs(selected_regions.crs)
    joined = gpd.sjoin(gages, selected_regions, how="left", predicate="within")
    joined = joined.drop_duplicates(subset=[gage_id_field])
    metrics = metrics.copy()
    metrics["basin_id"] = metrics["basin_id"].astype(str)
    joined[gage_id_field] = joined[gage_id_field].astype(str)
    return metrics.merge(
        joined[[gage_id_field, region_name_field, region_code_field]],
        left_on="basin_id",
        right_on=gage_id_field,
        how="left",
    )
