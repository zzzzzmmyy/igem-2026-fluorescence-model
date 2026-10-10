"""Compare reproduced metrics with the supplied, unchanged reference results."""
from pathlib import Path
import importlib.util
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
actual = pd.read_csv(ROOT / "output" / "model_comparison.csv")
expected = pd.read_csv(ROOT / "reference" / "model_comparison.csv")
assert actual["model"].tolist() == expected["model"].tolist()
np.testing.assert_allclose(actual.iloc[:, 1:], expected.iloc[:, 1:], rtol=1e-9, atol=1e-12)
actual_summary = json.loads((ROOT / "output" / "final_model_summary.json").read_text())
expected_summary = json.loads((ROOT / "reference" / "final_model_summary.json").read_text())
assert actual_summary.keys() == expected_summary.keys()
for key in actual_summary:
    np.testing.assert_allclose(actual_summary[key], expected_summary[key], rtol=1e-9, atol=1e-12)

spec = importlib.util.spec_from_file_location("predict_gfp_fraction", ROOT / "src" / "predict_gfp_fraction.py")
predictor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(predictor)
train = pd.read_pickle(ROOT / "output" / "train_921.pkl")
assert len(train) == 63 and train["fraction"].nunique() == 21
test = pd.read_pickle(ROOT / "output" / "test_921.pkl")
assert len(test) == 8
np.testing.assert_allclose(sorted(test["fraction"].unique()), [0.075, 0.275, 0.575])
demo = pd.read_csv(ROOT / "web" / "SIMULATED_workbench_demo.csv")
blank = demo[demo["Well"].str.endswith("12")]
samples = demo[~demo["Well"].str.endswith("12")]
result = predictor.predict_fraction(samples["GFP_raw"], samples["mCherry_raw"], blank["GFP_raw"], blank["mCherry_raw"])
assert len(result) == 88
assert not result["out_of_calibration_range"].any()
np.testing.assert_allclose(result["fraction"].mean(), 0.5073613706420455, rtol=1e-10)
print("PASS: all seven models, M3 parameters/metrics, dataset split and predictor unchanged.")
