# Fluorescence Unmixing Model

Team: ShanghaiTech-China, iGEM 2026. This package supports the plate-reader signal unmixing analysis described in the Model section.

## Files

- `data/`: Original Excel data. The parser reads measurements from both dates; model fitting uses the 20260921 data.
- `src/`: Scripts for data parsing, M1–M7 model comparison, plotting, and M3 prediction.
- `reference/`: Original numerical results used to check reproducibility.
- `figures/`: PNG and SVG files for the three final figures.
- `run_all.py`: Runs data parsing, model evaluation, and plotting in sequence.
- `requirements.txt`: Python dependency versions used for verification.
- `tests/check_regression.py`: Checks model metrics, M3 parameters, data splits, and the prediction function.
- `web/`: English workbench for local use, including the third-party library and its license.
- `docs/` and `LICENSE`: Provenance documentation, third-party library verification information, and licenses.

The model logic, data splits, coefficients, and numerical results are preserved from the original analysis. Figure styling and file naming have been updated.

## Reproduction Steps (Windows)

Verification was performed using Python 3.10.20. Install Python 3.10, open a terminal in the directory containing this file, and run:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_all.py
.\.venv\Scripts\python.exe tests/check_regression.py
```

Activating the virtual environment is unnecessary. If the `py` command is unavailable, replace `py -3.10` in the first line with the path to your Python 3.10 executable.

An internet connection is required for the initial dependency installation. Subsequent data parsing, model fitting, plotting, and numerical checks use local files and require no network connection.

## Outputs

Intermediate data and results are saved to `output/`. The three final figures are also saved to `figures/`:

```text
figure2-1_model_comparison.png / .svg
figure2-2_best_model_diagnostics.png / .svg
figure2-3_calibration_curve.png / .svg
```

`output/model_comparison.csv` contains the evaluation results for all seven models; `output/final_model_summary.json` contains the M3 parameters and metrics.

The check script should output `PASS`. It verifies the 63 fitting points, 21 fraction levels, and 8 held-out test points, and confirms that the metrics for all seven models and the M3 parameters match the original reference results. Floating-point comparisons use tolerances; image files are not required to be byte-identical across environments.

The reproduced M3 held-out test R² is approximately 0.9098, and its RMSE is approximately 0.0582. M3 was selected as the calibration model based on its cross-validation performance and linear form; it does not achieve the best result for every metric.

Figure 2-1 retains the original R² display lower limit of −0.3: bars below this limit are truncated, and their actual values should be checked in the results table. The RMSE axis uses a logarithmic scale.

## Try the Workbench Locally (Optional)

Open `web/index.html` in a browser. Click **Load example layout**, upload `web/SIMULATED_workbench_demo.csv`, and then click **Start analysis**.

The expected result is 88 test wells and 8 blank wells, with a mean predicted fraction of approximately 0.507 and no out-of-calibration-range flags. This CSV contains synthetic demonstration data, not experimental results, and is not used for model fitting or biological validation. Calculations and result downloads run locally in the browser.
