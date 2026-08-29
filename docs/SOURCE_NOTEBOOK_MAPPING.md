# Source-notebook consolidation

The repository consolidates the exploratory notebooks into an ordered manuscript workflow. It retains the substantive calculations and removes duplicated imports, hard-coded machine paths, repeated plotting cells, and temporary dataset aliases.

| Exploratory notebook | Compiled location | Method retained |
|---|---|---|
| `CONUS404_Annual_Precipitation.ipynb` | Notebook 00 and notebook 01 | Native annual precipitation acquisition and water-year aggregation |
| `CONUS404_Annual_AET_data.ipynb` | Notebook 00 and notebooks 03, 04, and 08 | AET component sum, annual/seasonal inputs, accuracy metrics, and annual variability |
| `CONUS404_Annual_Runoff.ipynb` | Notebook 00 and notebook 05 | `ACRUNSF + ACQRF` total runoff and annual runoff assessment |
| `CONUS404_Seasonal_RAIN_data.ipynb` | Notebook 00 and notebook 02 | Native seasonal precipitation and season-ending labels |
| `CONUS404_Seasonal_RAIN_data-BA.ipynb` | Notebook 00 and notebook 02 | Bias-adjusted `RAIN` seasonal precipitation |
| `CONUS404_Monthly_Precipitation.ipynb` | Notebook 00 | Monthly-resampling logic replaced by direct daily-to-paper-period aggregation |
| `CONUS404BA_Monthly_Precipitation.ipynb` | Notebook 00 | Bias-adjusted monthly intermediate replaced by direct daily-to-paper-period aggregation |
| `Statistical_Analysis_Precipitation.ipynb` | Notebooks 01, 02, 06, and 07 | PBIAS, MAE, RMSE, model-normalized MAE, regional distributions, correlation input, and precipitation variability |
| `Statistical_Analysis_Precipitation-BA.ipynb` | Notebooks 01, 02, and 07 | Bias-adjusted precipitation comparisons and variability |
| `Statistical_Analysis_Evapotranspiration.ipynb` | Notebooks 03, 04, 06, and 08 | Sanford and MODIS comparisons, seasonal assessment, annual PBIAS series, and ET variability |
| `Sanford_Basins_Runoff-Annual.ipynb` | Notebooks 05 and 05a | HyTEST runoff construction, NLDI basin retrieval, grid-polygon overlay, sparse area-weighted basin aggregation, NWIS discharge conversion, annual alignment, metrics, regression scatter plots, basin-area analysis, climate-region assignment, and basin distributions |
| `Pearson_Correlation_P-AET.ipynb` | Notebook 06 | Pixelwise temporal Pearson correlation between precipitation and ET PBIAS errors |
| `Python Code for Seasonal Jackknife Variance Estimation_Precipitation.ipynb` | Notebook 07 | Annual sample variance, jackknife variance of the mean, standard error, and relative uncertainty for precipitation |
| `Python Code for Seasonal Jackknife Variance Estimation.ipynb_Evapotranspiration.ipynb` | Notebook 08 | Annual sample variance, jackknife variance of the mean, standard error, and relative uncertainty for ET |

## Reconciled implementation details

The repository replaces Python ranges whose comments and endpoints disagreed with explicit inclusive `start_year` and `end_year` values in `config.yml`.

The repository replaces the temporary ET aliases `PRISM`, `DAYMET`, and `CONUS404BA` with the actual dataset identities Sanford WBET, MOD16A2GF.061, and CONUS404.

The workflow preserves the paper nMAE definition by dividing MAE by the corresponding modeled multiannual mean. The repository renames the runoff denominator accordingly; the exploratory column named `USGSmean` actually contained the modeled CONUS404 mean.

The workflow retains missing raster values as nodata instead of writing them as zero. The workflow also retains true zero MAE, PBIAS, and Pearson correlation as valid calculated values.

The analysis calculates the P–ET error correlation from the original annual model/reference rasters over a dedicated common period. This separates the Sanford correlation record from the shorter MODIS overlap used in the ET accuracy assessment.

The workflow applies a common cell-year mask across datasets in each interannual-variability assessment, so every dataset comparison at a cell uses the same annual observations.
