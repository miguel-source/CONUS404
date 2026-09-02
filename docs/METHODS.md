# Methods implemented in the repository

## CONUS404 water-balance preparation

The workflow reads the native `conus404-daily-osn` product and, when enabled in the configuration, the `conus404-daily-ba-osn` precipitation product through the HyTEST intake catalog. It processes one requested period at a time and writes float32, DEFLATE-compressed GeoTIFFs in EPSG:5070.

For native precipitation, the workflow retains two explicit constructions from the source notebooks. The annual source exported `PREC_ACC_NC`, whereas the seasonal source calculated `ACRAINLSM + ACSNOWLSM`. The workflow therefore configures `PREC_ACC_NC` as the default and retains the land-surface component sum as an alternative. Bias-adjusted precipitation is represented by `RAIN`.

The workflow reproduces the source AET construction as:

$$
ET=\mathrm{ACEDIR}+\mathrm{ACETRAN}+\mathrm{ACECAN}.
$$

The workflow retains `ACETLSM` as an alternative and calculates a sparse diagnostic difference between `ACETLSM` and the component sum. It does not automatically clip negative net AET.

The analysis calculates total CONUS404 runoff as:

$$
Q=\mathrm{ACRUNSF}+\mathrm{ACQRF},
$$

where the two fields represent accumulated surface and subsurface runoff components in the supplied runoff workflow.

The analysis calculates annual products as October–September water-year sums. It calculates Fall from October–December, Winter from January–March, Spring from April–June, and Summer from July–September. The workflow uses calendar-year seasonal labels and water-year annual labels. It aggregates the daily cloud product directly and does not retain the exploratory monthly NetCDF files as required intermediates.

## 3.1 Accuracy statistical assessment

### Spatial pairing

For precipitation and ET, the workflow opens one modeled and one reference raster for each time interval. It reprojects the reference raster to the modeled grid with the configured resampling method. The pairwise validity mask requires finite modeled and reference values; the configured paper workflow also requires both values to be positive. The same mask is applied to both arrays.

The workflow retains invalid cells as nodata. The workflow does not replace missing values with zero because zero is a physical value for the water-balance variables and a mathematical value for unbiased error.

### Metrics

For modeled values (S_t), reference values (O_t), and (n) valid paired intervals, the analysis calculates:

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
\mathrm{PBIAS}=100\frac{\sum_t(S_t-O_t)}{\sum_tO_t}.
$$

Positive PBIAS represents model overestimation and negative PBIAS represents model underestimation.

The analysis normalizes MAE by the multiannual modeled mean:

$$
\mathrm{nMAE}=100\frac{\mathrm{MAE}}{\overline{S}}.
$$

This denominator reproduces the paper definition. The workflow uses the relevant CONUS404 or CONUS404BA precipitation mean for precipitation, the CONUS404 ET mean for ET, and the CONUS404 basin runoff mean for runoff. At the seasonal scale, the analysis calculates a separate modeled denominator for each season.

The workflow retains a true MAE of zero as nMAE equal to zero. This corrects the exploratory behavior that converted exact zero error to nodata.

### Precipitation

The analysis evaluates native and bias-adjusted CONUS404 precipitation against the enabled DAYMET and PRISM products. It calculates annual and seasonal metrics separately and writes annual per-pixel PBIAS rasters for the later correlation analysis.

### Evapotranspiration

The analysis evaluates CONUS404 ET against Sanford WBET and MOD16A2GF.061. The workflow uses the same gridded alignment, masking, and metric definitions as the precipitation assessment. The workflow keeps the Sanford and MODIS identities explicit rather than retaining the `PRISM` and `DAYMET` temporary variable names present in the exploratory ET notebook.

### Runoff

The analysis evaluates runoff at the basin scale. The aligned table contains basin ID, year, observed USGS runoff depth, and modeled CONUS404 runoff depth. The workflow filters the configured inclusive study period, retains finite positive annual pairs, and calculates one metric set per basin. It requires at least the configured number of valid annual pairs.

The workflow spatially joins gage points to climate-region polygons and attaches the climate-region code and name to each basin metric. The runoff violin plots therefore represent between-basin distributions within each climate region.

#### Standalone HyTEST–NLDI–NWIS runoff construction

Notebook `05a_runoff_hytest_nldi_end_to_end.ipynb` reconstructs the aligned annual runoff table without external local scientific inputs or `config.yml`. The complete CAMELS gage list from the source notebook is embedded in the notebook. A demonstration run selects the first eight identifiers, and `RUN_FULL_GAGE_SET = True` selects the complete list.

The notebook opens `conus404-daily-osn` through the public HyTEST intake catalog, validates `ACRUNSF` and `ACQRF`, and forms daily total runoff as their sum. Daily depths are aggregated with October-start water-year bins:

$$
Q_{CONUS404,\,WY}=\sum_{d\in WY}(\mathrm{ACRUNSF}_d+\mathrm{ACQRF}_d).
$$

NLDI supplies the contributing-basin polygon and `nwissite` point for each selected USGS identifier. Basin areas are calculated in EPSG:5070. Basin polygons are also projected to the native CONUS404 grid, and their combined bounding box limits the gridded calculation.

The x- and y-coordinate bounds define a polygon for every retained CONUS404 grid cell. An intersection overlay between those grid polygons and the NLDI basins produces the area of every basin–cell fragment. For basin (b) and grid cell (j), the spatial weight is:

$$
w_{jb}=\frac{A_{jb}}{\sum_j A_{jb}},\qquad \sum_jw_{jb}=1.
$$

The overlay table is converted to a sparse matrix indexed by y, x, and gage. Sparse matrix multiplication calculates the area-weighted modeled basin runoff:

$$
S_{b,t}=\sum_j w_{jb}Q_{j,t}.
$$

NWIS daily values supply mean discharge for parameter `00060` and statistic `00003`. Discharge is converted from cubic feet per second to cubic meters per second. For basin area (A_b), daily discharge (q_d), and each water year, observed runoff depth is:

$$
O_{b,\,WY}(\mathrm{mm})=
\frac{\sum_{d\in WY}q_d\,86400}{A_b}\,1000.
$$

An observed water year is retained only when its daily-value coverage meets the configured 90% threshold. Modeled and observed annual depths are joined by gage identifier and ending water year. The aligned table feeds MBE, MAE, RMSE, PBIAS, model-mean nMAE, individual linear-regression scatter plots, a filtered multi-basin scatter grid, and the MAE-versus-basin-area analysis. The notebook writes the NLDI vectors, daily NWIS values, coverage, aligned annual records, metrics, regression coefficients, and figures below `results/runoff_hytest_nldi/`.

### Regional distributions

For gridded P and ET results, the workflow extracts raster cells inside each climate-region polygon. For runoff, the analysis groups basin metrics by the assigned climate region. Each violin represents the retained distribution. The workflow plots the median as a circle, the mean as an ×, and the mean ± one sample standard deviation as an error bar.

The workflow applies each configured figure interval before calculating the displayed mean, median, standard deviation, and sample size. Therefore, every exported regional-statistics table describes the same values displayed in its corresponding figure.

## 3.2 Correlation of water-balance component-wise PBIAS errors

The workflow constructs annual PBIAS stacks from:

1. CONUS404 precipitation relative to PRISM;
2. CONUS404 ET relative to Sanford WBET.

The workflow uses inclusive start and end years, aligns the precipitation PBIAS raster to the corresponding ET PBIAS grid, and forms a paired finite-value mask at every cell. For the paired annual series (x_t) and (y_t), the analysis calculates:

$$
r=\frac{\sum_t(x_t-\overline{x})(y_t-\overline{y})}{\sqrt{\sum_t(x_t-\overline{x})^2}\sqrt{\sum_t(y_t-\overline{y})^2}}.
$$

The workflow restricts the spatial domain with the CONUS404-versus-Sanford ET nMAE raster. It retains cells from 0% through 300% nMAE by default, matching the mask applied in the source correlation notebook. The configuration preserves both thresholds so that the documented analysis domain and the executed analysis domain remain identical. This domain mask does not enter the Pearson equation.

The workflow retains (r) only where the number of paired years meets the configured minimum. It writes both the Pearson coefficient and valid-year count. Positive correlation describes errors that vary in the same temporal direction, negative correlation describes opposing behavior, and zero describes no linear association. The statistic does not establish a causal relation between precipitation and ET errors.

## 3.3 Interannual variability statistical assessment

The analysis conducts separate annual assessments for precipitation and ET. The workflow aligns all enabled datasets in a component to one configured target grid and applies one common finite and positive cell-year mask. This gives every dataset the same valid annual sample at a cell.

For annual values (X_t), the analysis calculates the multiannual mean and sample interannual variance:

$$
\overline{X}=\frac{1}{n}\sum_tX_t
$$

$$
s^2=\frac{1}{n-1}\sum_t(X_t-\overline{X})^2.
$$

For the sample mean, the delete-one jackknife variance is:

$$
\widehat{\mathrm{Var}}_{JK}(\overline{X})=\frac{n-1}{n}\sum_{i=1}^{n}(\overline{X}_{(-i)}-\overline{X}_{JK})^2=\frac{s^2}{n}.
$$

The analysis then calculates:

$$
SE=\sqrt{\widehat{\mathrm{Var}}_{JK}(\overline{X})}
$$

and

$$
RU=100\frac{SE}{\overline{X}}.
$$

RU is reported as a percentage. The multiannual mean and standard error have units of millimeters, both variance quantities have units of square millimeters, and relative uncertainty is dimensionless before conversion to percent. The workflow masks variance-derived quantities when fewer than two valid annual values are present and masks relative uncertainty when the multiannual mean is not positive.

For every dataset, the workflow writes valid-year count, multiannual mean, interannual variance, jackknife variance of the mean, standard error of the mean, relative-uncertainty fraction, and relative-uncertainty percent. The analysis summarizes multiannual mean, standard error, and relative uncertainty by climate region with the same violin and statistics convention used in the accuracy assessment.

