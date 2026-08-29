"""Gridded accuracy-assessment utilities for water-balance components."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import rioxarray
import xarray as xr
from rasterio.enums import Resampling


def load_config(path: str | Path) -> dict:
    """Load YAML configuration and resolve repository-relative paths."""
    import yaml

    path = Path(path).resolve()
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    base = path.parent

    path_keys = {
        "file",
        "input_csv",
        "gage_points_file",
        "output_dir",
        "domain_mask",
    }

    def resolve(value, key: str | None = None):
        if isinstance(value, dict):
            return {child_key: resolve(child, child_key) for child_key, child in value.items()}
        if isinstance(value, list):
            return [resolve(child) for child in value]
        if isinstance(value, str) and (key in path_keys or (key and key.endswith("_dir"))):
            if value == "":
                return None
            candidate = Path(value)
            return candidate if candidate.is_absolute() else base / candidate
        return value

    config = resolve(config)
    return config


def enabled_items(config: dict, collection: str) -> dict:
    """Return enabled entries from a configured collection."""
    return {
        key: value
        for key, value in config[collection].items()
        if value.get("enabled", True)
    }


def years_for(
    config: dict,
    scale: str,
    component: str | None = None,
    assessment: str = "accuracy",
) -> list[int]:
    if component is None:
        period = config["study"][scale]
    else:
        period = config["study"][assessment][component][scale]
    return list(range(int(period["start_year"]), int(period["end_year"]) + 1))


def raster_path(dataset: Mapping, scale: str, year: int, season: str | None = None, suffix: str | None = None) -> Path:
    values = {"year": year, "season": season, "suffix": suffix}
    return Path(dataset[f"{scale}_dir"]) / dataset[f"{scale}_pattern"].format(**values)


def validate_inputs(
    config: dict,
    scale: str,
    years: Iterable[int],
    seasons: Mapping[str, Mapping] | None = None,
    component_config: Mapping | None = None,
) -> None:
    """Validate configured rasters and the climate-region layer."""
    years = list(years)
    missing: list[Path] = []
    source = config if component_config is None else component_config
    datasets = {**enabled_items(source, "models"), **enabled_items(source, "references")}
    season_items = seasons.items() if seasons else [(None, {})]
    for dataset in datasets.values():
        for season, details in season_items:
            for year in years:
                candidate = raster_path(dataset, scale, year, season, details.get("suffix"))
                if not candidate.is_file():
                    missing.append(candidate)
    region_file = Path(config["regions"]["file"])
    if not region_file.is_file():
        missing.append(region_file)
    if missing:
        preview = "\n".join(f"- {item}" for item in missing[:20])
        rest = f"\n... and {len(missing) - 20} more" if len(missing) > 20 else ""
        raise FileNotFoundError(f"Missing {len(missing)} required input(s):\n{preview}{rest}")


def open_raster(path: str | Path) -> xr.DataArray:
    """Open a single-band raster as a two-dimensional float array."""
    data = rioxarray.open_rasterio(path, masked=True).squeeze(drop=True)
    if data.ndim != 2:
        raise ValueError(f"Expected one 2-D raster band in {path}; got {data.dims}")
    if data.rio.crs is None:
        raise ValueError(f"Raster has no CRS: {path}")
    return data.astype("float32")


def load_stack(
    dataset: Mapping,
    scale: str,
    years: Iterable[int],
    season: str | None = None,
    suffix: str | None = None,
    match: list[xr.DataArray] | None = None,
    resampling: str = "bilinear",
) -> xr.DataArray:
    """Load a time stack and align every raster when a target grid is supplied."""
    years = list(years)
    method = getattr(Resampling, resampling)
    layers = []
    for index, year in enumerate(years):
        layer = open_raster(raster_path(dataset, scale, year, season, suffix))
        if match is not None:
            layer = layer.rio.reproject_match(match[index], resampling=method)
        layers.append(layer.expand_dims(year=[year]))
    return xr.concat(layers, dim="year")


def load_comparison(
    model: Mapping,
    reference: Mapping,
    scale: str,
    years: Iterable[int],
    season: str | None = None,
    suffix: str | None = None,
    resampling: str = "bilinear",
) -> tuple[xr.DataArray, xr.DataArray]:
    """Load a model stack and align the reference to each model-year grid."""
    years = list(years)
    model_layers = [
        open_raster(raster_path(model, scale, year, season, suffix)) for year in years
    ]
    model_stack = xr.concat(
        [layer.expand_dims(year=[year]) for layer, year in zip(model_layers, years)],
        dim="year",
    )
    reference_stack = load_stack(
        reference,
        scale,
        years,
        season=season,
        suffix=suffix,
        match=model_layers,
        resampling=resampling,
    )
    return model_stack, reference_stack


def paired_valid(
    model: xr.DataArray,
    reference: xr.DataArray,
    positive_only: bool = True,
) -> tuple[xr.DataArray, xr.DataArray]:
    """Apply the same finite-value mask to modeled and reference arrays."""
    valid = np.isfinite(model) & np.isfinite(reference)
    if positive_only:
        valid &= (model > 0) & (reference > 0)
    return model.where(valid), reference.where(valid)


def compute_metrics(
    model: xr.DataArray,
    reference: xr.DataArray,
    model_for_denominator: xr.DataArray | None = None,
) -> dict[str, xr.DataArray]:
    """Calculate MBE, MAE, RMSE, PBIAS, and model-normalized MAE."""
    difference = model - reference
    mbe = difference.mean("year", skipna=True)
    mae = abs(difference).mean("year", skipna=True)
    rmse = np.sqrt((difference**2).mean("year", skipna=True))
    reference_sum = reference.sum("year", skipna=True, min_count=1)
    pbias = xr.where(
        reference_sum > 0,
        100.0 * difference.sum("year", skipna=True, min_count=1) / reference_sum,
        np.nan,
    )
    denominator_stack = model if model_for_denominator is None else model_for_denominator
    model_mean = denominator_stack.where(denominator_stack > 0).mean("year", skipna=True)
    nmae_fraction = xr.where(model_mean > 0, mae / model_mean, np.nan)
    nmae_percent = 100.0 * nmae_fraction
    return {
        "model_mean": model_mean,
        "mbe": mbe,
        "mae": mae,
        "rmse": rmse,
        "pbias": pbias,
        "nmae_fraction": nmae_fraction,
        "nmae_percent": nmae_percent,
    }


def annual_pbias(model: xr.DataArray, reference: xr.DataArray) -> xr.DataArray:
    """Calculate per-year PBIAS for every raster cell."""
    return xr.where(reference > 0, 100.0 * (model - reference) / reference, np.nan)


def write_raster(data: xr.DataArray, path: str | Path) -> None:
    """Write a compressed float32 GeoTIFF and preserve missing pixels as nodata."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data.astype("float32").rio.write_nodata(np.nan).rio.to_raster(path, compress="deflate")


def write_metric_set(metrics: Mapping[str, xr.DataArray], directory: str | Path) -> dict[str, Path]:
    """Write every metric raster and return its output path."""
    directory = Path(directory)
    outputs = {}
    for name, data in metrics.items():
        path = directory / f"{name}.tif"
        write_raster(data, path)
        outputs[name] = path
    return outputs
