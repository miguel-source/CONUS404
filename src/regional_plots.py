"""Regional extraction, summary, and violin-plot utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MultipleLocator
from rasterio.mask import mask


def wrap_region_name(name: object) -> str:
    return (
        str(name)
        .replace("Northern Great Plains", "Northern Great\nPlains")
        .replace("Southern Great Plains", "Southern Great\nPlains")
    )


def extract_distributions(
    raster_path: str | Path,
    regions: gpd.GeoDataFrame,
    name_field: str,
    code_field: str,
    value_range: tuple[float, float] | None = None,
    exclude_zero: bool = True,
) -> tuple[list[np.ndarray], list[str]]:
    """Extract raster pixels within each region, ordered by region code."""
    for field in (name_field, code_field):
        if field not in regions.columns:
            raise KeyError(f"Region field {field!r} was not found")
    distributions, labels = [], []
    with rasterio.open(raster_path) as source:
        projected = regions.to_crs(source.crs).sort_values(code_field)
        for _, region in projected.iterrows():
            image, _ = mask(source, [region.geometry], crop=True, filled=False)
            values = image[0].compressed().astype("float64")
            values = values[np.isfinite(values)]
            if exclude_zero:
                values = values[values != 0]
            if value_range is not None:
                values = values[(values >= value_range[0]) & (values <= value_range[1])]
            distributions.append(values)
            code = region[code_field]
            is_integer = isinstance(code, (int, float, np.number)) and float(code).is_integer()
            code_label = str(int(code)) if is_integer else str(code)
            labels.append(f"{code_label}.\n{wrap_region_name(region[name_field])}")
    return distributions, labels


def distribution_statistics(
    series: Mapping[str, Sequence[np.ndarray]], labels: Sequence[str]
) -> pd.DataFrame:
    """Return n, mean, median, and sample standard deviation for every group."""
    rows = []
    for series_label, distributions in series.items():
        for region_label, values in zip(labels, distributions):
            rows.append(
                {
                    "series": series_label.replace("\n", " "),
                    "region": region_label.replace("\n", " "),
                    "n_pixels": values.size,
                    "mean": np.mean(values) if values.size else np.nan,
                    "median": np.median(values) if values.size else np.nan,
                    "sigma": np.std(values, ddof=1) if values.size > 1 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def plot_grouped_violins(
    raster_series: Sequence[tuple[str, str | Path]],
    regions: gpd.GeoDataFrame,
    name_field: str,
    code_field: str,
    output_png: str | Path,
    output_csv: str | Path,
    ylabel: str,
    value_range: tuple[float, float],
    colors: Sequence[str],
    dpi: int = 1200,
    exclude_zero: bool = True,
) -> pd.DataFrame:
    """Create grouped regional violins with median and mean ± 1 sigma."""
    if len(raster_series) != len(colors):
        raise ValueError("Provide exactly one color for each raster series")
    extracted: dict[str, list[np.ndarray]] = {}
    labels = None
    for series_label, raster_path in raster_series:
        values, current_labels = extract_distributions(
            raster_path,
            regions,
            name_field,
            code_field,
            value_range=value_range,
            exclude_zero=exclude_zero,
        )
        too_small = [label for label, array in zip(current_labels, values) if array.size < 2]
        if too_small:
            raise ValueError(
                f"Series {series_label!r} has fewer than two values after filtering in: "
                + ", ".join(too_small)
            )
        extracted[series_label] = values
        labels = current_labels if labels is None else labels

    stats = distribution_statistics(extracted, labels)
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    stats.to_csv(output_csv, index=False)

    plt.rcParams.update(
        {
            "font.size": 14,
            "axes.labelsize": 18,
            "xtick.labelsize": 18,
            "ytick.labelsize": 18,
            "legend.fontsize": 12,
        }
    )
    fig, axis = plt.subplots(figsize=(16, 6), dpi=dpi)
    positions = np.arange(1, len(labels) + 1)
    count = len(raster_series)
    offsets = np.linspace(-0.27, 0.27, count) if count > 1 else np.array([0.0])
    width = min(0.50, 0.64 / count)

    for (series_label, _), color, offset in zip(raster_series, colors, offsets):
        values = extracted[series_label]
        violin = axis.violinplot(
            values,
            positions=positions + offset,
            widths=width,
            showmeans=False,
            showmedians=False,
            showextrema=False,
        )
        for body in violin["bodies"]:
            body.set_facecolor(color)
            body.set_edgecolor("black")
            body.set_alpha(0.85)
        medians = np.array([np.median(item) for item in values])
        means = np.array([np.mean(item) for item in values])
        sigmas = np.array([np.std(item, ddof=1) for item in values])
        axis.scatter(positions + offset, medians, color="black", marker="o", s=28, zorder=4)
        axis.errorbar(
            positions + offset,
            means,
            yerr=sigmas,
            fmt="x",
            color="black",
            ecolor="black",
            markersize=8,
            markeredgewidth=2,
            elinewidth=2,
            capsize=4,
            linestyle="none",
            zorder=5,
        )

    axis.set_xticks(positions)
    axis.set_xticklabels(labels, ha="center")
    axis.tick_params(axis="x", pad=10)
    axis.set_ylabel(ylabel)
    axis.set_ylim(*value_range)
    axis.grid(False)
    if value_range[0] < 0 < value_range[1]:
        axis.axhline(0, color="black", linewidth=1.5)
    span = value_range[1] - value_range[0]
    major = 10 if span <= 100 else 20
    axis.yaxis.set_major_locator(MultipleLocator(major))
    axis.yaxis.set_minor_locator(MultipleLocator(5))

    handles = [
        Patch(facecolor=color, edgecolor="black", label=label.replace("\n", " "))
        for (label, _), color in zip(raster_series, colors)
    ]
    handles.extend(
        [
            Line2D([0], [0], marker="o", color="black", linestyle="None", label="Median"),
            Line2D([0], [0], marker="x", color="black", linestyle="None", label="Mean"),
            Line2D([0], [0], color="black", linewidth=2, label="± 1σ (Std. dev.)"),
        ]
    )
    axis.legend(
        handles=handles,
        ncol=4,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.18),
        frameon=False,
    )
    fig.subplots_adjust(top=0.78)
    fig.tight_layout()
    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return stats


def plot_table_violins(
    table: pd.DataFrame,
    value_series: Sequence[tuple[str, str]],
    region_name_field: str,
    region_code_field: str,
    output_png: str | Path,
    output_csv: str | Path,
    ylabel: str,
    value_range: tuple[float, float],
    colors: Sequence[str],
    dpi: int = 1200,
) -> pd.DataFrame:
    """Create grouped violins from basin metrics assigned to climate regions."""
    if len(value_series) != len(colors):
        raise ValueError("The number of series and colors must match")
    for field in (region_name_field, region_code_field):
        if field not in table.columns:
            raise KeyError(f"Region field {field!r} was not found")

    region_table = (
        table[[region_code_field, region_name_field]]
        .dropna()
        .drop_duplicates()
        .sort_values(region_code_field)
    )
    labels = []
    for code, name in region_table.itertuples(index=False, name=None):
        try:
            numeric_code = float(code)
            code_label = str(int(numeric_code)) if numeric_code.is_integer() else str(code)
        except (TypeError, ValueError):
            code_label = str(code)
        labels.append(f"{code_label}.\n{wrap_region_name(name)}")
    codes = region_table[region_code_field].tolist()
    extracted: dict[str, list[np.ndarray]] = {}
    for label, column in value_series:
        if column not in table.columns:
            raise KeyError(f"Value column {column!r} was not found")
        distributions = []
        for code in codes:
            values = pd.to_numeric(
                table.loc[table[region_code_field] == code, column], errors="coerce"
            ).to_numpy(dtype="float64")
            values = values[np.isfinite(values)]
            values = values[(values >= value_range[0]) & (values <= value_range[1])]
            if values.size < 2:
                raise ValueError(
                    f"Series {label!r} has fewer than two values in climate region {code}"
                )
            distributions.append(values)
        extracted[label] = distributions

    stats = distribution_statistics(extracted, labels)
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    stats.to_csv(output_csv, index=False)

    fig, axis = plt.subplots(figsize=(16, 6), dpi=dpi)
    positions = np.arange(1, len(labels) + 1)
    count = len(value_series)
    offsets = np.linspace(-0.27, 0.27, count) if count > 1 else np.array([0.0])
    width = min(0.50, 0.64 / count)
    for (label, _), color, offset in zip(value_series, colors, offsets):
        values = extracted[label]
        violin = axis.violinplot(
            values,
            positions=positions + offset,
            widths=width,
            showmeans=False,
            showmedians=False,
            showextrema=False,
        )
        for body in violin["bodies"]:
            body.set_facecolor(color)
            body.set_edgecolor("black")
            body.set_alpha(0.85)
        medians = np.array([np.median(item) for item in values])
        means = np.array([np.mean(item) for item in values])
        sigmas = np.array([np.std(item, ddof=1) for item in values])
        axis.scatter(positions + offset, medians, color="black", marker="o", s=28)
        axis.errorbar(
            positions + offset,
            means,
            yerr=sigmas,
            fmt="x",
            color="black",
            ecolor="black",
            markersize=8,
            markeredgewidth=2,
            elinewidth=2,
            capsize=4,
            linestyle="none",
        )

    axis.set_xticks(positions)
    axis.set_xticklabels(labels, ha="center")
    axis.set_ylabel(ylabel)
    axis.set_ylim(*value_range)
    axis.grid(False)
    if value_range[0] < 0 < value_range[1]:
        axis.axhline(0, color="black", linewidth=1.5)
    handles = [
        Patch(facecolor=color, edgecolor="black", label=label)
        for (label, _), color in zip(value_series, colors)
    ]
    handles.extend(
        [
            Line2D([0], [0], marker="o", color="black", linestyle="None", label="Median"),
            Line2D([0], [0], marker="x", color="black", linestyle="None", label="Mean"),
            Line2D([0], [0], color="black", linewidth=2, label="± 1σ (Std. dev.)"),
        ]
    )
    axis.legend(
        handles=handles,
        ncol=4,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.18),
        frameon=False,
    )
    fig.subplots_adjust(top=0.78)
    fig.tight_layout()
    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return stats
