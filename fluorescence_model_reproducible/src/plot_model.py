import os
import json
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import r2_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "white"

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "output")

C_TRAIN = "#2a78d6"
C_TEST = "#eb6834"

results_df = pd.read_pickle(os.path.join(OUT, "results_df.pkl"))
train = pd.read_pickle(os.path.join(OUT, "train_921.pkl"))
test = pd.read_pickle(os.path.join(OUT, "test_921.pkl"))


PAPER_STYLE = {
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 12,
    "axes.linewidth": 0.8,
    "figure.facecolor": "#000000",
    "axes.facecolor": "#000000",
    "savefig.facecolor": "#000000",
    "axes.edgecolor": "#9CA3AF",
    "text.color": "#F3F4F6",
    "axes.labelcolor": "#E5E7EB",
    "xtick.color": "#D1D5DB",
    "ytick.color": "#D1D5DB",
    "svg.fonttype": "none",
}
MODEL_COLORS = ("#56B4E9", "#CC79A7")

# ============ model comparison ============
name_short = {
    "M1_GFP_only_linear": "M1\nGFP\nlinear",
    "M2_mCherry_only_linear": "M2\nmCherry\nlinear",
    "M3_two_channel_linear": "M3\nTwo-channel\nlinear",
    "M4_ratio_linear": "M4\nRatio\nlinear",
    "M5_ratio_quadratic": "M5\nRatio\nquadratic",
    "M6_GFP_quadratic": "M6\nGFP\nquadratic",
    "M7_random_forest_two_channel": "M7\nRandom forest\n(two-channel)",
}
results_df["short"] = results_df["model"].map(name_short)

# Apply the shared paper style locally to each figure.
with plt.rc_context(PAPER_STYLE):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
    # Sky blue and reddish purple from the Okabe-Ito scientific palette.
    colors = MODEL_COLORS
    x = np.arange(len(results_df))
    w = 0.34

    for ax in axes:
        ax.set_axisbelow(True)
        ax.grid(axis="y", color="#FFFFFF", alpha=0.12, linewidth=0.65)
        ax.set_xticks(x)
        ax.set_xticklabels(results_df["short"], fontsize=7.5)
        ax.tick_params(axis="x", length=0, pad=9)
        ax.tick_params(axis="y", labelsize=9, width=0.7, length=3)
        ax.set_xlim(-0.65, len(results_df) - 0.35)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    ax = axes[0]
    r2_cv_clipped = results_df["R2_CV"].clip(lower=-0.3)
    r2_test_clipped = results_df["R2_test"].clip(lower=-0.3)
    ax.bar(x - w/2, r2_cv_clipped, width=w, color=colors[0], label="Cross-validation (LOGO)")
    ax.bar(x + w/2, r2_test_clipped, width=w, color=colors[1], label="External test")
    ax.axhline(0, color="#9CA3AF", lw=0.8)
    ax.axhline(1, color="#9CA3AF", lw=0.8, ls=(0, (3, 3)))
    ax.set_ylabel("R²")
    ax.set_ylim(-0.4, 1.08)
    ax.set_yticks([-0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_title("(A) R²", loc="left", fontweight="bold", pad=12)

    ax = axes[1]
    ax.bar(x - w/2, results_df["RMSE_CV"], width=w, color=colors[0])
    ax.bar(x + w/2, results_df["RMSE_test"], width=w, color=colors[1])
    # A log axis reveals small errors while retaining every original RMSE value.
    ax.set_yscale("log")
    ax.set_ylim(0.01, 15)
    ax.set_yticks([0.01, 0.1, 1, 10], labels=["0.01", "0.1", "1", "10"])
    ax.tick_params(axis="y", which="minor", length=0)
    ax.set_ylabel("RMSE (log scale)")
    ax.set_title("(B) RMSE", loc="left", fontweight="bold", pad=12)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.suptitle("Model comparison", fontsize=15, fontweight="bold", y=0.985)
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.915),
               ncol=2, frameon=False, fontsize=10, handlelength=1.4, columnspacing=2.5)
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.16, top=0.76, wspace=0.22)
    for extension in ("png", "svg"):
        filename = f"figure2-1_model_comparison.{extension}"
        fig.savefig(os.path.join(OUT, filename), dpi=300, bbox_inches="tight")
    plt.close(fig)
print("saved figure2-1_model_comparison (PNG + SVG)")
print(results_df[["model", "R2_CV", "RMSE_CV", "R2_test", "RMSE_test"]].to_string(index=False))

# ============ Recompute best-model (M3) OOF + test predictions for diagnostics ============
Xtrain = train[["GFPc", "mCherryc"]].values
ytrain = train["fraction"].values
groups = train["fraction"].values
Xtest = test[["GFPc", "mCherryc"]].values
ytest = test["fraction"].values

logo = LeaveOneGroupOut()
oof_pred_m3 = np.zeros(len(ytrain))
for tr_idx, va_idx in logo.split(Xtrain, ytrain, groups):
    m = LinearRegression()
    m.fit(Xtrain[tr_idx], ytrain[tr_idx])
    oof_pred_m3[va_idx] = m.predict(Xtrain[va_idx])

m3_full = LinearRegression().fit(Xtrain, ytrain)
pred_test_m3 = m3_full.predict(Xtest)
print(f"\nM3 two-channel linear regression coefficients: GFPc={m3_full.coef_[0]:.6e}, "
      f"mCherryc={m3_full.coef_[1]:.6e}, intercept={m3_full.intercept_:.4f}")

# ============ best-model diagnostics ============
resid_train = oof_pred_m3 - ytrain
resid_test = pred_test_m3 - ytest
band = np.std(resid_train)

with plt.rc_context(PAPER_STYLE):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
    colors = MODEL_COLORS

    for ax in axes:
        ax.set_axisbelow(True)
        ax.grid(color="#FFFFFF", alpha=0.12, linewidth=0.65)
        ax.tick_params(labelsize=9, width=0.7, length=3)
        ax.set_xlabel("True GFP fraction")
        ax.set_xlim(-0.08, 1.08)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    ax = axes[0]
    ideal, = ax.plot([0, 1], [0, 1], color="#9CA3AF", lw=1,
                    ls=(0, (4, 4)), zorder=1, label="Ideal prediction")
    cv_points = ax.scatter(ytrain, oof_pred_m3, color=colors[0], s=38, alpha=0.85,
                           zorder=3, edgecolor="#000000", linewidth=0.4,
                           label="Cross-validation (LOGO)")
    test_points = ax.scatter(ytest, pred_test_m3, color=colors[1], s=70, marker="^",
                             zorder=4, edgecolor="#000000", linewidth=0.5,
                             label="External test")
    ax.set_ylabel("Predicted GFP fraction")
    ax.set_ylim(-0.08, 1.08)
    ax.set_title("(A) Predicted vs. true", loc="left", fontweight="bold", pad=12)
    ax.legend(handles=[ideal], frameon=False, fontsize=9, loc="upper left")

    ax = axes[1]
    ax.axhline(0, color="#9CA3AF", lw=1, ls=(0, (4, 4)), zorder=2)
    ax.scatter(ytrain, resid_train, color=colors[0], s=38, alpha=0.85,
               zorder=3, edgecolor="#000000", linewidth=0.4)
    ax.scatter(ytest, resid_test, color=colors[1], s=70, marker="^",
               zorder=4, edgecolor="#000000", linewidth=0.5)
    ax.axhspan(-band, band, color=colors[0], alpha=0.14, zorder=0, label="CV ±1 SD")
    ax.set_ylabel("Residual (predicted − true)")
    ax.set_title("(B) Residuals", loc="left", fontweight="bold", pad=12)
    ax.legend(frameon=False, fontsize=9, loc="upper right")

    fig.suptitle("Best-model diagnostics (M3)", fontsize=15, fontweight="bold", y=0.985)
    fig.legend(handles=[cv_points, test_points], loc="upper center",
               bbox_to_anchor=(0.5, 0.915), ncol=2, frameon=False,
               fontsize=10, handlelength=1.4, columnspacing=2.5)
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.16, top=0.76, wspace=0.25)
    for extension in ("png", "svg"):
        filename = f"figure2-2_best_model_diagnostics.{extension}"
        fig.savefig(os.path.join(OUT, filename), dpi=300, bbox_inches="tight")
    plt.close(fig)
print("saved figure2-2_best_model_diagnostics (PNG + SVG)")
print(f"train residual: mean={resid_train.mean():.4f} sd={resid_train.std(ddof=1):.4f}")
print(f"test residual: mean={resid_test.mean():.4f} sd={resid_test.std(ddof=1):.4f}")

# ============ calibration curve ============
resid_sd = resid_train.std(ddof=1)
xs = np.linspace(0, 1, 100)
rmse_all_test = np.sqrt(np.mean((pred_test_m3 - ytest) ** 2))
mae_all_test = np.mean(np.abs(pred_test_m3 - ytest))

with plt.rc_context(PAPER_STYLE):
    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    colors = MODEL_COLORS
    ideal, = ax.plot([0, 1], [0, 1], color="#9CA3AF", lw=1,
                    ls=(0, (4, 4)), label="Ideal calibration", zorder=1)
    cv_points = ax.scatter(ytrain, oof_pred_m3, color=colors[0], s=38, alpha=0.85,
                           zorder=3, edgecolor="#000000", linewidth=0.4,
                           label="Cross-validation (LOGO)")
    test_points = ax.scatter(ytest, pred_test_m3, color=colors[1], s=70, marker="^",
                             zorder=4, edgecolor="#000000", linewidth=0.5,
                             label="External test")
    residual_band = ax.fill_between(xs, xs - 1.96 * resid_sd, xs + 1.96 * resid_sd,
                                    color=colors[0], alpha=0.14,
                                    label="CV ±1.96 SD", zorder=0)
    ax.set_xlabel("True GFP fraction")
    ax.set_ylabel("Predicted GFP fraction")
    ax.set_axisbelow(True)
    ax.grid(color="#FFFFFF", alpha=0.12, linewidth=0.65)
    ax.tick_params(labelsize=9, width=0.7, length=3)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.1, 1.1)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(handles=[ideal, residual_band], fontsize=9, frameon=False, loc="lower right")
    fig.suptitle("Calibration curve (M3)", fontsize=15, fontweight="bold", y=0.985)
    fig.legend(handles=[cv_points, test_points], loc="upper center",
               bbox_to_anchor=(0.5, 0.915), ncol=2, frameon=False,
               fontsize=10, handlelength=1.4, columnspacing=2)
    fig.subplots_adjust(left=0.12, right=0.975, bottom=0.12, top=0.79)
    for extension in ("png", "svg"):
        filename = f"figure2-3_calibration_curve.{extension}"
        fig.savefig(os.path.join(OUT, filename), dpi=300, bbox_inches="tight")
    plt.close(fig)
print("saved figure2-3_calibration_curve (PNG + SVG)")

with open(os.path.join(OUT, "model_blank_baseline.json")) as f:
    baseline = json.load(f)

summary = {
    "blank_baseline_GFP": baseline["blank_gfp"],
    "blank_baseline_mCherry": baseline["blank_mch"],
    "M3_coef_GFPc": float(m3_full.coef_[0]),
    "M3_coef_mCherryc": float(m3_full.coef_[1]),
    "M3_intercept": float(m3_full.intercept_),
    "M3_train_cv_R2": float(r2_score(ytrain, oof_pred_m3)),
    "M3_test_R2": float(r2_score(ytest, pred_test_m3)),
    "M3_test_RMSE": float(rmse_all_test),
    "M3_test_MAE": float(mae_all_test),
}
with open(os.path.join(OUT, "final_model_summary.json"), "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
