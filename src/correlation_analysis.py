"""Pixelwise Pearson correlation of component PBIAS time series."""

from __future__ import annotations

import numpy as np
import xarray as xr


def pearson_correlation(
    first: xr.DataArray,
    second: xr.DataArray,
    dim: str = "year",
    min_valid: int = 3,
) -> dict[str, xr.DataArray]:
    """Calculate paired Pearson r and the number of valid observations."""
    valid = np.isfinite(first) & np.isfinite(second)
    first_paired = first.where(valid)
    second_paired = second.where(valid)
    n_valid = valid.sum(dim)
    correlation = xr.corr(first_paired, second_paired, dim=dim).where(
        n_valid >= min_valid
    )
    return {
        "pearson_r": correlation,
        "n_valid": n_valid.astype("float32"),
    }
