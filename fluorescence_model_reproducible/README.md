# 荧光信号解混模型：可复现代码包

队伍：ShanghaiTech-China，iGEM 2026。此包用于复现 Model 中的酶标仪信号解混分析，并供 Wiki 负责人接收源码；不需要修改 Wiki 配置或申请 Software。

## 文件

- `data/`：原始 Excel 数据。解析器读取两次测量，模型拟合使用 20260921 数据。
- `src/`：数据解析、M1–M7 模型比较、绘图与 M3 预测脚本。
- `reference/`：原始数值结果，用于检查复现结果是否一致。
- `figures/`：三张最终图的 PNG、SVG 文件。
- `run_all.py`：按顺序运行解析、模型评估及绘图。
- `requirements.txt`：验证时使用的 Python 依赖版本。
- `tests/check_regression.py`：核对模型指标、M3 参数、数据划分及预测函数。
- `web/`：可在本地使用的英文工作台，含第三方库及许可证。
- `docs/`、`LICENSE`：来源说明、第三方库校验信息及许可证。

模型主体、数据划分、系数和计算结果沿用原始分析；绘图样式与文件命名进行了整理。

## 复现步骤（Windows）

验证使用 Python 3.10.20。先安装 Python 3.10，在本文件所在目录打开终端，然后执行：

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_all.py
.\.venv\Scripts\python.exe tests/check_regression.py
```

无需激活虚拟环境。如果系统没有 `py` 命令，用实际 Python 3.10 可执行文件替换第一行的 `py -3.10`。

首次安装依赖需要联网。后续解析、拟合、绘图和数值检查使用本地文件，不需要网络。

## 运行结果

中间数据和结果写入 `output/`，最终三张图同时写入 `figures/`：

```text
figure2-1_model_comparison.png / .svg
figure2-2_best_model_diagnostics.png / .svg
figure2-3_calibration_curve.png / .svg
```

`output/model_comparison.csv` 为七个模型的评估结果；`output/final_model_summary.json` 为 M3 的参数及指标。

检查脚本应输出 `PASS`。它核对 63 个拟合点、21 个比例水平、8 个留出测试点，以及七个模型的指标和 M3 参数与原始参考值一致。浮点比较使用容差，不要求不同环境下图像文件的字节完全一致。

复现结果中的 M3 留出测试 R² 约为 0.9098、RMSE 约为 0.0582。M3 是按交叉验证表现和线性形式选用的校准模型，并非所有指标均最优。

图 2-1 延用原图的 R² 显示下限 −0.3：更低的柱形被截断，实际数值应查结果表；RMSE 轴为对数坐标。

## 本地体验工作台（可选）

用浏览器打开 `web/index.html`。点击 **Load example layout**，上传 `web/SIMULATED_workbench_demo.csv`，再点击 **Start analysis**。

预期结果为 88 个测试孔、8 个空白孔，预测比例均值约 0.507，无超出校准范围标记。此 CSV 是合成演示数据，不是实验结果，也不用于拟合或生物学验证。计算和结果下载在浏览器本地完成。

## 交付方式

将整个代码包交给 Wiki 负责人，或提交到队伍 Wiki 仓库的 `models/fluorescence/`。此路径是建议的组织方式，不是官方强制目录。不要上传 `.venv/`、`__pycache__/`、生成的 `output/` 等环境与缓存文件。

在线工作台和 Model 页面接入由 Wiki 负责人处理。本代码包不包含 Wiki 页面模板、部署配置或 CI 修改。

队伍应按实际贡献记录补全 `docs/ATTRIBUTIONS.md` 中的作者信息；第三方 SheetJS 的 Apache 2.0 许可证保存在 `web/vendor/`，应保留。
