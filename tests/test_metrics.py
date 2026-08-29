import numpy as np
import xarray as xr

from accuracy_assessment import compute_metrics, paired_valid


def test_nmae_uses_model_multiannual_mean():
    model = xr.DataArray(
        np.array([10.0, 20.0]).reshape(2, 1, 1),
        dims=("year", "y", "x"),
        coords={"year": [2000, 2001], "y": [0], "x": [0]},
    )
    reference = xr.DataArray(
        np.array([8.0, 18.0]).reshape(2, 1, 1),
        dims=("year", "y", "x"),
        coords=model.coords,
    )
    paired_model, paired_reference = paired_valid(model, reference)
    metrics = compute_metrics(paired_model, paired_reference, model)

    assert np.isclose(metrics["mae"].item(), 2.0)
    assert np.isclose(metrics["model_mean"].item(), 15.0)
    assert np.isclose(metrics["nmae_percent"].item(), 100.0 * 2.0 / 15.0)
    assert np.isclose(metrics["pbias"].item(), 100.0 * 4.0 / 26.0)


def test_zero_mae_remains_zero():
    model = xr.DataArray([10.0, 10.0], dims="year")
    metrics = compute_metrics(model, model, model)

    assert metrics["nmae_percent"].item() == 0.0
