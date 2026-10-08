# 光谱侦探：天文科研科普 MVP

一个可本地运行的中文 Streamlit 展项，完整走通：

**原始 CCD → 偏置/平场 → 宇宙线决策 → 多阶定位 → 提取与 blaze 校正 → 阶次合并 → 谱线 → 视向速度**

新版采用任务制：参与者选择岗位、提交判断、调节检测阈值与提取孔径、追踪阶次、决定合并权重，并签署自己的 RV 观测日志。页面会记录 6 项任务的完成进度。

面向零基础参与者，参数反馈采用“真实数据 + 教学增强”双层表达：Bias/Flat/Overscan 提供差值放大镜；宇宙线阈值实时改变红圈掩膜、局部修复三联图；提取孔径直接覆盖在阶次和横截面上，并显示收光率与背景宽度；合并权重同时展示等权结果、当前结果、重叠区放大和差值曲线；RV 误差预算用“尺子精度”类比解释并动态换算为速度不确定度。

## 演示视频

`demo/天文科研科普MVP演示.gif` 是初版四阶段界面的约 23 秒无声演示；新版已经扩展为六项互动任务。

## 一页式科研故事

你是今天的值班天文学家。Gemini South 望远镜把白矮星候选体 J2145+0031 的光送入 GMOS 光谱仪。CCD 给你的不是彩色星空，而是被展开的光、电子学基线、像素响应差异和天空背景的叠加。

1. 打开原始 FITS，辨认恒星的二维光谱和探测器结构。
2. 用 bias 认识电子学零点，用 flat 认识像素响应；用 CuAr 弧灯理解波长尺。
3. 判断宇宙线何时必须处理、何时可交给多曝光稳健合并，并检查数据质量掩膜。
4. 在明确标注的 echelle 教学模拟中追踪弯曲阶次、选择提取孔径、校正 blaze，并按信噪比合并重叠区。
5. 最后才对准 He I 4471.48 Å 吸收谷，用 `v = c(λobs-λ0)/λ0` 得到视向速度估计。

```text
望远镜
  ↓
原始科学帧 ──→ Bias / Flat 校正 ──→ 校正后的二维光谱
                        ↑
                  CuAr 弧灯定标
                        ↓
           宇宙线检查 / 掩膜 / 稳健合并
                        ↓
             阶次追踪 → 提取 → blaze 校正
                        ↓
                 重采样与阶次合并
                        ↓
                  最终一维光谱
                        ↓
          He I 实验室波长 ↔ 观测中心
                        ↓
                    视向速度
```

## 运行

建议使用 Python 3.11 或 3.12：

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

应用启动后会显示本地网址，通常是 `http://localhost:8501`。

## 分享到互联网并保留可编辑性

推荐使用 **GitHub + Streamlit Community Cloud**：朋友通过固定网址直接体验，你继续在本地或 GitHub 编辑；推送到 GitHub 后，网页会自动重新部署。完整操作、公开/私有选择和协作方式见 [DEPLOY.md](DEPLOY.md)。

## 项目结构

```text
stellar-spectroscopy-mvp/
├── app.py                         # Streamlit 展项
├── requirements.txt
├── README.md
├── DEPLOY.md                       # GitHub + Streamlit 云端发布指南
├── DATA_SOURCES.md                # 候选比较、来源、公开状态与引用
├── source_data/                   # 4 个真实 GMOS 原始 FITS（bzip2 压缩）
│   ├── S20171022S0087.fits.bz2    # science: J2145+0031
│   ├── S20171021S0265.fits.bz2    # bias
│   ├── S20171022S0088.fits.bz2    # flat
│   └── S20171022S0092.fits.bz2    # CuAr arc
├── data/                          # GMOS 中间产品、echelle 模拟和参考一维谱
└── scripts/prepare_data.py        # 从源数据重建 data/
```

## 重建教学产品

仓库已经包含生成后的 `data/`。需要重建时：

```bash
python scripts/prepare_data.py
```

脚本会完成逐放大器 overscan 估计、拼接、代表性 bias 相减、教学版 flat 校正、固定窗口提取和局部连续谱归一化。它还会从真实一维谱确定性地构造九阶 echelle 教学数据，注入可验证的宇宙线事件，并输出去宇宙线图与逐阶波长、流量和 blaze 响应。显示用二维产品做了合并以减小体积。

## 科学边界（必须保留）

这是“研究流程体验”，不是发表级数据产品：

- 为便携和可解释性，只使用一帧 science、一个代表性 bias、一个 flat 和一个 arc；官方科研流程使用多帧 master bias、仪器坏像素掩膜、完整序列与标准星。
- 校正和提取是通用教学近似，不包含 GMOS 全部仪器模型、畸变/QE/通量定标。
- 一维谱的波长轴按 B600、2×2 binning 和 515 nm 中心波长构造近似线性尺。CuAr 帧用于展示真实定标证据，但 MVP 没有自动拟合弧灯线表。
- RV 未做日心/重心改正，谱线中心为手动估计。界面结果只能用于科普。
- 原始 Gemini B600 观测是普通长缝光谱，不是 echelle。多阶 CCD、宇宙线位置和逐阶产品是基于真实 J2145+0031 一维谱的教学模拟，界面和 FITS 头均明确标注，不能冒充真实 echelle 观测。

若要升级到科研级版本，应按官方教程用 DRAGONS 处理完整 Example 1 数据包，并把其 `*_2D.fits`、`*_1D.fits` 和 wavelength solution 替换进应用。

## 数据与致谢

数据来自 International Gemini Observatory / NSF NOIRLab 的官方 GMOS long-slit DRAGONS tutorial Example 1，程序 GS-2017B-Q-72。详细链接和公开状态见 [DATA_SOURCES.md](DATA_SOURCES.md)。

推荐致谢：

> Based on observations obtained at the international Gemini Observatory, a program of NSF NOIRLab, acquired through the Gemini Observatory Archive and used here via the official GMOS Longslit DRAGONS tutorial dataset.

代码可按 MIT 方式复用；原始观测数据仍遵循 Gemini Archive 的数据政策和致谢要求，本项目不对数据重新授权。
