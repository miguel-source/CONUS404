"""Interannual variability and delete-one jackknife estimators."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import numpy as np
import xarray as xr

from accuracy_assessment import write_raster


def common_valid_stacks(
    stacks: Mapping[str, xr.DataArray],
    positive_only: bool = True,
) -> dict[str, xr.DataArray]:
    """Apply one common cell-year mask to every dataset stack."""
    if not stacks:
        raise ValueError("At least one data stack is required")
    valid = None
    for stack in stacks.values():
        current = np.isfinite(stack)
        if positive_only:
            current &= stack > 0
        valid = current if valid is None else valid & current
    return {name: stack.where(valid) for name, stack in stacks.items()}


def variability_metrics(stack: xr.DataArray, dim: str = "year") -> dict[str, xr.DataArray]:
    """Calculate mean, interannual variance, jackknife variance, SE, and RU."""
    count = stack.count(dim)
    mean = stack.mean(dim, skipna=True)
    interannual_variance = stack.var(dim, skipna=True, ddof=1)
    variance_of_mean = xr.where(count > 1, interannual_variance / count, np.nan)
    standard_error = np.sqrt(variance_of_mean)
    relative_uncertainty_fraction = xr.where(
        (count > 1) & (mean > 0), standard_error / mean, np.nan
    )
    return {
        "n_valid": count.astype("float32"),
        "multiannual_mean": mean,
        "interannual_variance": interannual_variance,
        "jackknife_variance_of_mean": variance_of_mean,
        "standard_error_of_mean": standard_error,
        "relative_uncertainty_fraction": relative_uncertainty_fraction,
        "relative_uncertainty_percent": 100.0 * relative_uncertainty_fraction,
    }


def write_variability_set(
    metrics: Mapping[str, xr.DataArray], directory: str | Path
) -> dict[str, Path]:
    """Write a complete interannual-variability raster set."""
    directory = Path(directory)
    outputs = {}
    for name, data in metrics.items():
        path = directory / f"{name}.tif"
        write_raster(data, path)
        outputs[name] = path
    return outputs
