import numpy as np
import pandas as pd
import xarray as xr

from correlation_analysis import pearson_correlation
from interannual_variability import common_valid_stacks, variability_metrics
from runoff_assessment import compute_basin_metrics


def test_pixelwise_pearson_correlation_and_valid_count():
    first = xr.DataArray([1.0, 2.0, 3.0], dims="year")
    second = xr.DataArray([2.0, 4.0, 6.0], dims="year")
    metrics = pearson_correlation(first, second, min_valid=3)

    assert np.isclose(metrics["pearson_r"].item(), 1.0)
    assert metrics["n_valid"].item() == 3


def test_jackknife_variance_of_mean_equals_sample_variance_over_n():
    stack = xr.DataArray([1.0, 2.0, 3.0], dims="year")
    metrics = variability_metrics(stack)

    assert np.isclose(metrics["multiannual_mean"].item(), 2.0)
    assert np.isclose(metrics["interannual_variance"].item(), 1.0)
    assert np.isclose(metrics["jackknife_variance_of_mean"].item(), 1.0 / 3.0)
    assert np.isclose(metrics["standard_error_of_mean"].item(), np.sqrt(1.0 / 3.0))


def test_common_mask_is_applied_to_every_stack():
    stacks = {
        "first": xr.DataArray([1.0, np.nan, 3.0], dims="year"),
        "second": xr.DataArray([4.0, 5.0, 6.0], dims="year"),
    }
    masked = common_valid_stacks(stacks)

    assert np.isnan(masked["first"].values[1])
    assert np.isnan(masked["second"].values[1])


def test_runoff_metrics_use_modeled_multiannual_mean_for_nmae():
    data = pd.DataFrame(
        {
            "Gage_ID": ["A", "A", "A"],
            "Year": [2001, 2002, 2003],
            "Runoff_Annual": [1.0, 2.0, 3.0],
            "Runoff_Squaw": [2.0, 3.0, 4.0],
        }
    )
    metrics = compute_basin_metrics(
        data,
        {
            "basin_id": "Gage_ID",
            "year": "Year",
            "observed": "Runoff_Annual",
            "modeled": "Runoff_Squaw",
        },
        2001,
        2003,
        minimum_years=3,
    ).iloc[0]

    assert np.isclose(metrics["mbe_mm"], 1.0)
    assert np.isclose(metrics["mae_mm"], 1.0)
    assert np.isclose(metrics["rmse_mm"], 1.0)
    assert np.isclose(metrics["pbias_percent"], 50.0)
    assert np.isclose(metrics["model_multiannual_mean_mm"], 3.0)
    assert np.isclose(metrics["nmae_percent"], 100.0 / 3.0)
