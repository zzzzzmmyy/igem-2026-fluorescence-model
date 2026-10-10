#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
predict_gfp_fraction.py
========================
独立打包的最终标定模型 -- 输入空白孔(背景)读数 + 待测孔的 GFP/mCherry 荧光读数,
输出该孔中 GFP 阳性细胞所占比例(fraction, 0~1)。

模型来源
--------
本脚本封装的是 20260921 数据集回归建模中最终选定的模型:
    M3 -- 双通道线性回归(two-channel linear regression)
    fraction = a * GFPc + b * mCherryc + c
其中 GFPc / mCherryc 是背景校正后的信号:
    GFPc     = GFP_raw     - blank_GFP_mean
    mCherryc = mCherry_raw - blank_mCherry_mean

系数、截距、残差标准差均取自 model_0921.py + plot_model.py 的输出
(output/final_model_summary.json),对应结果:
    训练集 LOGO 交叉验证 R² = 0.9956, RMSE = 0.0201, MAE = 0.0149
    外部测试集(0.075/0.275/0.575) R² = 0.9098, RMSE = 0.0582, MAE = 0.0413
详见分析报告第 3、5 节。本脚本只负责"应用模型",不重新训练模型;
如果以后有新一批数据、想重新拟合系数,应回到 model_0921.py 重新跑一遍,
而不是手改本文件里的常数。

标定范围(重要)
----------------
模型是在下表范围的数据上训练出来的,超出这个范围的读数属于"外推"
(extrapolation),模型给出的结果可信度没有保证,函数会自动给出警告:
    GFPc     训练范围: 7.5e+03  ~ 3.10e+06
    mCherryc 训练范围: 2.1e+02  ~ 4.03e+04
    fraction 训练范围: 0.00     ~ 1.00

用法一:作为 Python 模块导入
----------------------------
    from predict_gfp_fraction import predict_fraction

    # 单个孔,空白孔只测了一次
    result = predict_fraction(
        gfp_raw=1250000, mcherry_raw=15000,
        blank_gfp_raw=-48944, blank_mcherry_raw=931,
    )
    print(result["fraction"])          # 点估计
    print(result["ci_low"], result["ci_high"])   # 95% 置信区间

    # 空白孔测了多次(比如 6 个复孔),直接把读数列表传进去,函数会自动取均值
    result = predict_fraction(
        gfp_raw=1250000, mcherry_raw=15000,
        blank_gfp_raw=[-48800, -49100, -48950, -49200, -48700, -48900],
        blank_mcherry_raw=[905, 940, 920, 950, 960, 913],
    )

    # 批量多个孔一起算(gfp_raw / mcherry_raw 传数组或列表即可)
    import pandas as pd
    df = predict_fraction(
        gfp_raw=[300000, 1250000, 2700000],
        mcherry_raw=[32000, 15000, 3500],
        blank_gfp_raw=-48944, blank_mcherry_raw=931,
    )
    print(df)   # 返回一个 pandas DataFrame,每行一个孔

用法二:命令行直接跑
----------------------
    # 单孔,空白孔已经算好均值
    python3 predict_gfp_fraction.py --gfp 1250000 --mcherry 15000 \\
        --blank-gfp -48944 --blank-mcherry 931

    # 空白孔给多个复孔读数,自动取均值
    python3 predict_gfp_fraction.py --gfp 1250000 --mcherry 15000 \\
        --blank-gfp -48800 -49100 -48950 -49200 -48700 -48900 \\
        --blank-mcherry 905 940 920 950 960 913

    # 批量:一个 CSV(需要 GFP_raw / mCherry_raw 两列),用同一批空白孔校正
    python3 predict_gfp_fraction.py --csv wells.csv \\
        --blank-gfp -48800 -49100 -48950 --blank-mcherry 905 940 920 \\
        --output result.csv
"""

import argparse
import sys
import numpy as np

# ============================================================
# 1. 模型参数(来自 output/final_model_summary.json, M3 模型)
# ============================================================
COEF_GFPC = 2.6363458858137393e-07
COEF_MCHERRYC = -5.50412798458503e-06
INTERCEPT = 0.19327294046955756

# 训练集 LOGO 交叉验证残差的标准差,用来给预测值配一个 95% 置信区间
# (来自 plot_model.py 里 fig9/fig10 的 resid_train.std(ddof=1))
CV_RESIDUAL_SD = 0.020230368391386134
CI_MULTIPLIER = 1.96  # 95% 置信区间对应的正态分布倍数

# 训练数据实际覆盖的范围,用于判断新孔是不是在"标定范围之外"(外推)
TRAIN_RANGE_GFPC = (7547.666666666664, 3100443.6666666665)
TRAIN_RANGE_MCHERRYC = (208.66666666666663, 40345.666666666664)

# 模型整体表现,写在这里方便调用方查阅/打印,不参与计算
MODEL_PERFORMANCE = {
    "cv_R2": 0.9956024724100442,
    "cv_RMSE": 0.020077517170854372,
    "cv_MAE": 0.014860733265170002,
    "test_R2": 0.909783983617622,
    "test_RMSE": 0.0581644273962976,
    "test_MAE": 0.04129825148110456,
}


def _mean_of(x):
    """把标量或者一组读数统一处理成一个均值(标量原样返回,数组取均值)。"""
    arr = np.atleast_1d(np.asarray(x, dtype=float))
    return float(arr.mean())


def predict_fraction(gfp_raw, mcherry_raw, blank_gfp_raw, blank_mcherry_raw, clip=True):
    """
    根据某个孔(或一批孔)的原始 GFP / mCherry 荧光读数,以及空白孔(培养基空白)
    的读数,预测这个孔里 GFP 阳性细胞所占的比例(fraction)。

    参数
    ----
    gfp_raw, mcherry_raw : float 或者 一维数组/列表
        待测孔的原始荧光读数(未做任何背景校正)。可以是单个孔(标量),
        也可以是多个孔(数组/列表,一次性批量预测,两者长度要一致)。
    blank_gfp_raw, blank_mcherry_raw : float 或者 一维数组/列表
        空白孔(培养基空白,不含细胞)的原始读数,用来算背景基线。
        - 传单个数值:表示这个值已经是空白孔的均值,直接用。
        - 传多个数值(比如 6 个复孔的读数):函数会自动取均值再使用,
          和 model_0921.py 里对空白孔取均值背景校正的做法完全一致。
    clip : bool, 默认 True
        细胞比例在生物学意义上只能落在 [0, 1] 之间。线性模型本身不知道
        这个约束,极端情况下可能给出 <0 或 >1 的预测值。clip=True 时,
        会在结果里额外给出裁剪到 [0,1] 之后的 fraction_clipped 字段;
        原始的、未裁剪的线性预测值仍然保留在 fraction 字段里,方便判断
        模型是不是明显跑飞了。

    返回
    ----
    - 如果 gfp_raw / mcherry_raw 是单个数值:返回一个 dict。
    - 如果 gfp_raw / mcherry_raw 是数组/列表(多个孔):返回一个 pandas
      DataFrame,每一行对应一个孔。
    两种情况下都包含以下字段:
        GFPc, mCherryc        背景校正后的信号
        fraction              模型的原始线性预测值(可能小于0或大于1)
        fraction_clipped      裁剪到 [0,1] 之后的预测值(clip=True 才有)
        ci_low, ci_high       以 fraction(未裁剪值)为中心的 95% 置信区间
        out_of_calibration_range   True/False,是否超出了训练数据覆盖的范围
                              (超出时,预测结果的可信度没有保证)
    """
    blank_gfp_mean = _mean_of(blank_gfp_raw)
    blank_mch_mean = _mean_of(blank_mcherry_raw)

    is_scalar = np.isscalar(gfp_raw) or (np.ndim(gfp_raw) == 0)
    gfp_arr = np.atleast_1d(np.asarray(gfp_raw, dtype=float))
    mch_arr = np.atleast_1d(np.asarray(mcherry_raw, dtype=float))
    if gfp_arr.shape != mch_arr.shape:
        raise ValueError("gfp_raw 和 mcherry_raw 的长度必须一致(一一对应同一批孔)。")

    gfpc = gfp_arr - blank_gfp_mean
    mchc = mch_arr - blank_mch_mean

    pred = COEF_GFPC * gfpc + COEF_MCHERRYC * mchc + INTERCEPT
    ci_low = pred - CI_MULTIPLIER * CV_RESIDUAL_SD
    ci_high = pred + CI_MULTIPLIER * CV_RESIDUAL_SD

    out_of_range = (
        (gfpc < TRAIN_RANGE_GFPC[0]) | (gfpc > TRAIN_RANGE_GFPC[1]) |
        (mchc < TRAIN_RANGE_MCHERRYC[0]) | (mchc > TRAIN_RANGE_MCHERRYC[1])
    )

    result = {
        "GFP_raw": gfp_arr,
        "mCherry_raw": mch_arr,
        "GFPc": gfpc,
        "mCherryc": mchc,
        "fraction": pred,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "out_of_calibration_range": out_of_range,
    }
    if clip:
        result["fraction_clipped"] = np.clip(pred, 0.0, 1.0)

    if is_scalar:
        return {k: (v[0] if isinstance(v, np.ndarray) else v) for k, v in result.items()}

    import pandas as pd
    return pd.DataFrame(result)


# ============================================================
# 命令行入口
# ============================================================
def _build_arg_parser():
    p = argparse.ArgumentParser(
        description="用最终标定模型(M3双通道线性回归),从 GFP/mCherry 荧光读数预测 GFP 细胞比例。"
    )
    p.add_argument("--gfp", type=float, nargs="+",
                    help="单孔或多孔的 GFP 通道原始读数(可给多个值,和 --mcherry 一一对应)")
    p.add_argument("--mcherry", type=float, nargs="+",
                    help="单孔或多孔的 mCherry 通道原始读数(数量需和 --gfp 一致)")
    p.add_argument("--csv", type=str,
                    help="批量模式:一个 CSV 文件路径,需包含 GFP_raw 和 mCherry_raw 两列")
    p.add_argument("--blank-gfp", type=float, nargs="+", required=True,
                    help="空白孔 GFP 通道读数,可给一个均值,也可给多个复孔读数(自动取均值)")
    p.add_argument("--blank-mcherry", type=float, nargs="+", required=True,
                    help="空白孔 mCherry 通道读数,可给一个均值,也可给多个复孔读数(自动取均值)")
    p.add_argument("--no-clip", action="store_true",
                    help="不输出裁剪到 [0,1] 之后的 fraction_clipped 列")
    p.add_argument("--output", type=str, default=None,
                    help="把结果另存为一个 CSV 文件(不指定则只打印到终端)")
    return p


def main():
    args = _build_arg_parser().parse_args()

    if args.csv:
        import pandas as pd
        wells = pd.read_csv(args.csv)
        for col in ("GFP_raw", "mCherry_raw"):
            if col not in wells.columns:
                sys.exit(f"[错误] --csv 指定的文件里没有找到列 '{col}'")
        gfp_vals = wells["GFP_raw"].values
        mch_vals = wells["mCherry_raw"].values
    elif args.gfp is not None and args.mcherry is not None:
        if len(args.gfp) != len(args.mcherry):
            sys.exit("[错误] --gfp 和 --mcherry 给出的数值个数必须相同。")
        gfp_vals = args.gfp
        mch_vals = args.mcherry
    else:
        sys.exit("[错误] 请用 --gfp/--mcherry 指定读数,或用 --csv 指定批量文件。")

    out = predict_fraction(
        gfp_raw=gfp_vals,
        mcherry_raw=mch_vals,
        blank_gfp_raw=args.blank_gfp,
        blank_mcherry_raw=args.blank_mcherry,
        clip=not args.no_clip,
    )

    import pandas as pd
    if isinstance(out, dict):
        out = pd.DataFrame([out])

    pd.set_option("display.float_format", lambda x: f"{x:.6g}")
    print(out.to_string(index=False))

    n_bad = int(out["out_of_calibration_range"].sum())
    if n_bad > 0:
        print(f"\n[警告] 有 {n_bad} 个孔的背景校正信号超出了模型训练时覆盖的范围"
              f"(GFPc: {TRAIN_RANGE_GFPC[0]:.3g}~{TRAIN_RANGE_GFPC[1]:.3g}, "
              f"mCherryc: {TRAIN_RANGE_MCHERRYC[0]:.3g}~{TRAIN_RANGE_MCHERRYC[1]:.3g}),"
              f" 这些孔的预测结果属于外推,可信度没有保证。")

    if args.output:
        out.to_csv(args.output, index=False)
        print(f"\n结果已保存到 {args.output}")


if __name__ == "__main__":
    main()
