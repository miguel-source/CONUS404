# CONUS404 water-balance statistical assessment

The repository contains code for evaluating precipitation, actual evapotranspiration (ET), and runoff. Its structure follows the methodology described in detail in the manuscript, “Assessing Accuracy and Variability of CONUS404 and Related Datasets for Water Resources Planning.” It includes Python and Jupyter Notebook workflows for manipulating the CONUS404 dataset and performing statistical analyses. The repository also contains notebooks demonstrating how to access and spatially process CONUS404 data using xarray. For more information about any workflow, please contact the authors. The [methods document](docs/METHODS.md) records the equations and processing definitions.

## Manuscript organization

| Paper component | Scale and comparison | Notebook |
|---|---|---|
| 3.1 Accuracy statistical assessment — precipitation | Annual CONUS404/CONUS404BA versus DAYMET/PRISM | `01_accuracy_precipitation_annual.ipynb` |
| 3.1 Accuracy statistical assessment — precipitation | Seasonal CONUS404/CONUS404BA versus DAYMET/PRISM | `02_accuracy_precipitation_seasonal.ipynb` |
| 3.1 Accuracy statistical assessment — evapotranspiration | Annual CONUS404 versus Sanford WBET and MOD16A2GF.061 | `03_accuracy_evapotranspiration_annual.ipynb` |
| 3.1 Accuracy statistical assessment — evapotranspiration | Seasonal CONUS404 versus Sanford WBET and MOD16A2GF.061 | `04_accuracy_evapotranspiration_seasonal.ipynb` |
| 3.1 Accuracy statistical assessment — runoff | Annual CONUS404 versus USGS at Sanford/CAMELS basins | `05_accuracy_runoff_annual.ipynb` |
| Standalone runoff data and analysis workflow | HyTEST CONUS404 + NLDI basins + NWIS discharge, including basin aggregation and regression figures | `05a_runoff_hytest_nldi_end_to_end.ipynb` |
| 3.2 Correlation of component-wise PBIAS errors | Annual CONUS404–PRISM precipitation PBIAS versus CONUS404–Sanford ET PBIAS | `06_correlation_pbias_precipitation_evapotranspiration.ipynb` |
| 3.3 Interannual variability statistical assessment | Annual precipitation | `07_interannual_variability_precipitation.ipynb` |
| 3.3 Interannual variability statistical assessment | Annual evapotranspiration | `08_interannual_variability_evapotranspiration.ipynb` |

The preparation notebook produces the CONUS404 precipitation, ET, and runoff rasters in `00_prepare_conus404_water_balance_data.ipynb`. It aggregates the daily cloud product directly, so the monthly precipitation files created in the exploratory notebooks are not required as intermediate paper inputs.

The standalone runoff notebook reproduces the full cloud-to-basin sequence from `Sanford_Basins_Runoff-Annual.ipynb`. It does not read `config.yml` or require a prepared local input dataset. The complete CAMELS gage list is embedded in the notebook; HyTEST supplies CONUS404, NLDI supplies basin polygons and gage points, and NWIS supplies daily discharge. The default run processes eight gages, while `RUN_FULL_GAGE_SET = True` activates the complete embedded list.

## Accuracy assessment

For modeled values (S_t) and reference values (O_t), the analysis calculates:

$$
\mathrm{MBE}=\frac{1}{n}\sum_t(S_t-O_t)
$$

$$
\mathrm{MAE}=\frac{1}{n}\sum_t|S_t-O_t|
$$

$$
\mathrm{RMSE}=\sqrt{\frac{1}{n}\sum_t(S_t-O_t)^2}
$$

$$
\mathrm{PBIAS}=100\frac{\sum_t(S_t-O_t)}{\sum_tO_t}
$$

The workflow preserves the paper's model-based nMAE denominator:

$$
\mathrm{nMAE}=100\frac{\mathrm{MAE}}{\overline{S}}.
$$

Thus, the analysis normalizes precipitation MAE by the corresponding CONUS404 or CONUS404BA mean, ET MAE by the CONUS404 ET mean, and runoff MAE by the CONUS404 basin runoff mean. The workflow retains a true MAE or PBIAS value of zero as a valid result rather than converting it to nodata.

For gridded comparisons, the workflow aligns every reference raster to the corresponding modeled grid, forms a pairwise finite and positive mask, and retains missing values as nodata. The analysis calculates annual and seasonal metrics separately. The workflow defines Fall as October–December, Winter as January–March, Spring as April–June, and Summer as July–September.

For runoff, the analysis calculates the metrics independently for each gage basin from aligned annual USGS and CONUS404 runoff depths. The workflow assigns gage points to climate regions with a spatial within-join before constructing the regional figures.

## Component-wise PBIAS correlation

The analysis calculates a Pearson correlation coefficient through time at every cell using two annual PBIAS series:

- precipitation: CONUS404 relative to PRISM;
- ET: CONUS404 relative to Sanford WBET.

The workflow aligns precipitation PBIAS to the ET PBIAS grid, uses only paired finite annual values, records the number of valid years, and masks coefficients with fewer than the configured minimum. It also applies the CONUS404-versus-Sanford ET nMAE raster as the spatial-domain mask and retains nMAE values from 0% through 300% by default. This mask defines the analysis domain but does not change the Pearson equation. Exact zero correlation remains valid. The resulting raster represents temporal association between component errors, not causation.

## Interannual variability

For each annual dataset stack, the analysis calculates the multiannual mean, sample interannual variance, delete-one jackknife variance of the mean, standard error, and relative uncertainty:

$$
s^2=\frac{1}{n-1}\sum_t(X_t-\overline{X})^2
$$

$$
\widehat{\mathrm{Var}}_{JK}(\overline{X})=\frac{s^2}{n},\qquad
SE=\sqrt{\frac{s^2}{n}},\qquad
RU=100\frac{SE}{\overline{X}}.
$$

The workflow uses one common finite and positive cell-year mask across the enabled datasets within each component. This keeps the valid years identical for precipitation-dataset and ET-dataset comparisons.

## Repository structure

```text
.
├── notebooks/
│   ├── 00_prepare_conus404_water_balance_data.ipynb
│   ├── 01_accuracy_precipitation_annual.ipynb
│   ├── 02_accuracy_precipitation_seasonal.ipynb
│   ├── 03_accuracy_evapotranspiration_annual.ipynb
│   ├── 04_accuracy_evapotranspiration_seasonal.ipynb
│   ├── 05_accuracy_runoff_annual.ipynb
│   ├── 05a_runoff_hytest_nldi_end_to_end.ipynb
│   ├── 06_correlation_pbias_precipitation_evapotranspiration.ipynb
│   ├── 07_interannual_variability_precipitation.ipynb
│   └── 08_interannual_variability_evapotranspiration.ipynb
├── src/
│   ├── correlation_analysis.py
│   ├── interannual_variability.py
│   ├── accuracy_assessment.py
│   ├── regional_plots.py
│   └── runoff_assessment.py
├── tests/
├── docs/
│   ├── METHODS.md
├── config.example.yml
├── environment.yml
└── README.md
```

## Software environment and execution

The workflow defines the complete Conda environment in `environment.yml`:

```bash
conda env create -f environment.yml
conda activate conus404-water-balance
```

The repository stores machine-specific paths and study periods outside the notebooks:

```powershell
Copy-Item config.example.yml config.yml
jupyter lab
```

`config.yml` is the repository's machine-specific analysis configuration, not the HyTEST catalog. It maps dataset names to local PRISM, DAYMET, Sanford, MODIS, boundary, and result paths and stores study periods and plotting parameters. The public HyTEST intake catalog already exists online and is opened directly by notebooks `00` and `05a`; it is not created locally.

The configured notebooks import reusable functions from `src/`. Those modules implement raster validation and alignment, statistical metrics, regional extraction, violin plots, PBIAS correlation, interannual variability, and runoff assessment. Notebook `05a` is intentionally self-contained: its HyTEST, NLDI, NWIS, spatial-overlay, sparse aggregation, metrics, and regression operations remain visible inside the notebook and do not depend on `config.yml`.

The configured manuscript notebooks execute in numerical order except for the runoff pair: notebook `05a` executes before notebook `05`. Notebook `05a` is independent of the YAML configuration and generates `results/runoff_hytest_nldi/aligned_annual_runoff.csv` and `results/runoff_hytest_nldi/nldi_gage_points.gpkg`; those outputs are the default runoff inputs referenced by `config.example.yml`. Notebook `05` then adds the manuscript climate-region violin analysis. The correlation notebook recalculates the two annual component PBIAS series over its own common period, allowing the Sanford comparison to extend beyond the MODIS-limited ET accuracy period. The two interannual-variability notebooks operate directly on annual accumulated input rasters.

## Required local inputs

The CONUS404 preparation notebook reads the public HyTEST OSN catalog. The standalone runoff notebook retrieves all of its scientific inputs remotely and requires only internet access and the declared software environment. The remaining manuscript products use configurable local filename templates:

- annual and seasonal DAYMET precipitation;
- annual and seasonal PRISM precipitation;
- annual and seasonal Sanford WBET evapotranspiration;
- annual and seasonal MOD16A2GF.061 evapotranspiration;
- climate-region polygons.

The aligned runoff CSV and gage-point layer are generated by notebook `05a`; they are outputs rather than external local inputs.

The repository excludes large rasters, generated results, and the machine-specific `config.yml` from Git.

## Outputs

The workflow writes paper outputs below `results/`:

```text
results/
├── runoff_hytest_nldi/
├── accuracy/
│   ├── precipitation/
│   ├── evapotranspiration/
│   └── runoff/
├── correlation/
└── interannual_variability/
    ├── precipitation/
    └── evapotranspiration/
```

Each gridded accuracy comparison contains model mean, MBE, MAE, RMSE, PBIAS, nMAE fraction, nMAE percent, and annual PBIAS rasters. The standalone runoff directory contains NLDI vectors, NWIS observations and coverage, aligned annual runoff, basin metrics, regression coefficients, individual scatter plots, a filtered scatter grid, and basin-area figures. The correlation directory contains Pearson (r), valid-year count, regional statistics, and the correlation violin plot. Each variability dataset contains valid-year count, multiannual mean, interannual variance, jackknife variance of the mean, standard error, and relative uncertainty.

## CONUS404 source

The repository identifies CONUS404 with DOI [10.5065/ZYY0-Y036](https://doi.org/10.5065/ZYY0-Y036) and uses the public products described by the [HyTEST CONUS404 access guide](https://hytest-org.github.io/hytest/dataset_access/CONUS404_ACCESS.html). The acquisition notebooks record the selected variable construction and catalog metadata used in each run.

**Funding**

This research was funded by the United States Geological Survey through the Water Resources Research Act Program National Competitive Grants Program (104g), grant work GR-028464-00001 Cruse-Multi-scale spatio-temporal analysis of the U.S. water budget using CONUS404.

**Acknowledgement:**

The authors would like to thank the United States Geological Survey – USGS, Iowa State University, the National Center for Atmospheric Research, and the Iowa Water Center, for providing and supporting the access to hydroclimate data repositories, reviewing and guiding the project through interinstitutional collaboration.   

1. Rasmussen, R.M., F. Chen, C.H. Liu, K. Ikeda, A. Prein, J. Kim, T. Schneider, A. Dai, D. Gochis, A. Dugger, Y. Zhang, A. Jaye, J. Dudhia, C. He, M. Harrold, L. Xue, S. Chen, A. Newman, E. Dougherty, R. Abolafia-Rozenzweig, N. Lybarger, R. Viger, D. Lesmes, K. Skalak, J. Brakebill, D. Cline, K. Dunne, K. Rasmussen, G. Miguez-Macho, 2023: CONUS404: The NCAR/USGS 4-km long-term regional hydroclimate reanalysis over the CONUS. Bulletin American Meteorological Society, 01 August 2023, Pages: E1382 to E1408, DOI: https://doi.org/10.1175/BAMS-D-21-0326.1.
2. Rasmussen, R.M., Chen, F., Liu, C., Ikeda, K., Prein, A., Kim, J., Schneider, T., Dai, A., Gochis, D., Dugger, A., Zhang, Y., Jaye, A., Dudhia, J., He, C., Harrold, M., Xue, L., Chen, S., Newman, A., Dougherty, E., Abolafia-Rozenzweig, R., Lybarger, N., R. Viger, Dunne, K., Rasmussen, K., Miguez-Macho, G., 2023, Four-kilometer long-term regional hydroclimate reanalysis over the conterminous United States (CONUS), 1979-2020: U.S. Geological Survey data release, https://doi.org/10.5066/P9PHPK4F.


## Citation

If you use this repository, please cite:

Diaz, M. A., & Arenas, A. (2026). *CONUS404 water-balance statistical assessment* [Computer software]. GitHub. https://github.com/miguel-source/CONUS404




