# 数据来源、核验与选型记录

核验日期：2026-09-02。

## 最终选择

选择 **Gemini/NOIRLab GMOS Longslit DRAGONS Tutorial，Example 1: Dithered Point Source**。

它是本次检索中最接近“一整套、标准、可下载、可复现、适合公众教学”的数据：官方教程提供独立打包下载，并逐项列出 science、两组 bias、随科学观测取得的 spectroscopic flat、CuAr arc、光谱流量标准星和 BPM。目标 J2145+0031 是 DB 白矮星候选体，He I 吸收线适合做谱线选择体验。

- 教程总览：<https://dragons.readthedocs.io/projects/gmosls-drtutorial/en/stable/01_overview.html>
- 数据包下载页：<https://dragons.readthedocs.io/projects/gmosls-drtutorial/en/stable/02_datasets.html>
- Example 1 文件清单：<https://dragons.readthedocs.io/projects/gmosls-drtutorial/en/stable/ex1_gmosls_dithered_dataset.html>
- 官方 reduction walkthrough：<https://dragons.readthedocs.io/projects/gmosls-drtutorial/en/stable/ex1_gmosls_dithered_cmdline.html>
- 原始包：<https://www.gemini.edu/sciops/data/software/datapkgs/gmosls_tutorial_datapkg-dithered-v1.tar>

本项目携带的文件均直接从上述官方包提取，未更改压缩文件内容：

| 教学角色 | Gemini 文件 | 头信息核验 |
|---|---|---|
| raw science | `S20171022S0087.fits.bz2` | OBJECT=J2145+0031, OBSTYPE=OBJECT, 1050 s |
| bias | `S20171021S0265.fits.bz2` | OBJECT=Bias, OBSTYPE=BIAS, 0 s |
| flat | `S20171022S0088.fits.bz2` | OBJECT=GCALflat, OBSTYPE=FLAT, 3 s |
| arc | `S20171022S0092.fits.bz2` | OBJECT=CuAr, OBSTYPE=ARC, 20 s |
| reference spectrum | `data/reference_spectrum.fits` | 由本项目脚本从上述 science/calibration 帧生成的教学产品 |

官方完整包还包含另外 3 帧 science、另一中心波长的 flat/arc、10 个 full-frame bias、标准星及其校准帧和 BPM。本 MVP 仅内置最小子集；文件名和完整清单保留在官方教程中。

## 公开状态与使用条件

- 该数据由 Gemini 官方主动放入无需登录即可下载的教程包；同一页面说明原始数据也可从 Gemini Observatory Archive 获取，因此可核验为公开教学数据。
- 观测日期为 2017 年，早已超过通常的 proprietary period；Gemini Archive 对 proprietary data 与 public release 作区分。
- Gemini 页面要求在包含 Gemini 数据的科学论文中使用相应 acknowledgement。公开可下载不等于以 CC0 或 MIT 重新授权；因此本项目保留来源和致谢，不宣称拥有或重新许可原始 FITS。
- Archive 与致谢说明：<https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/gemini/>

## 候选比较

| 来源 | 完整度 | 下载/教程状态 | 本 MVP 判断 |
|---|---|---|---|
| Gemini GMOS DRAGONS Example 1 | science + bias + flat + arc + standard + BPM；明确产出 2D/1D | 官方小型分包、无需登录、逐步 Python/CLI 教程 | **最佳**：真实、完整、对象有明显恒星吸收线 |
| ESO EFOSC/FORS Reflex demos | 通常含完整 calibration cascade 和 pipeline 产品 | 官方教程成熟，但示例包约 99–483 MB 或更大，工作流较重 | 很强的备选，更适合完整 workshop 而非轻量展项 |
| NOIRLab/IRAF slit-spectra guides | reduction 文档经典，涵盖 CCD/长缝光谱方法 | 多为说明书；统一、现代、可直接下载的一整套示例数据不如 Gemini 明确 | 用作方法背景，不作为数据源 |
| STScI HST/STIS/COS | raw、reference files、pipeline output 体系完整 | 数据结构和空间望远镜管线较复杂，bias/flat/arc 不以公众直观的独立帧呈现 | 不利于“一帧一作用”的展项叙事 |
| AAVSO/高校练习 | 往往适合课堂，解释友好 | 常偏成品一维谱或自制数据，校准帧/许可/长期下载一致性不一 | 可作为课程补充，不优先于官方完整包 |

相关官方背景：

- NOIRLab IRAF documentation（含 CCD reductions 与 reducing slit spectra guides）：<https://iraf.noirlab.edu/docs.html>
- ESO EFOSC demo index：<https://ftp.eso.org/pub/dfs/pipelines/efosc/>
- ESO EFOSC spectroscopy tutorial：<https://ftp.eso.org/pub/dfs/pipelines/instruments/efosc/efosc-mos-reflex-tutorial-2.3.10.pdf>
- HST/STIS pipeline overview：<https://hst-docs.stsci.edu/stisihb/chapter-15-overview-of-pipeline-calibration/15-1-pipeline-processing-overview>

## 完整性说明

没有找到一套同时满足“体积很小、单一下载、完整 raw calibrations、预先生成的科研级 1D、目标又是易讲的恒星吸收谱”的完美数据集。Gemini 包满足前四项中的前三项，并提供清晰教程说明科研级 2D/1D 输出如何生成；但下载包本身主要是原始输入，不附完整 reduction outputs。

因此本项目采用官方 raw + calibration 子集，并以可重现脚本补齐教学中间产品。所有近似均在界面和 README 中显式标注，避免把教学结果伪装成科研级数据。

## Echelle 与宇宙线教学模拟

Gemini Example 1 使用 GMOS B600 普通长缝模式，原始帧不是 echelle 多阶光谱。为展示高分辨率恒星光谱常见的阶次处理链，本项目由 `scripts/prepare_data.py` 使用真实 J2145+0031 一维谱确定性地生成九个有重叠波段和 blaze 响应的弯曲阶次，并注入已知位置的粒子事件。相关 FITS 头包含 `TEACHING=True`、`DATATYPE=SIMULATED ECHELLE` 和 `BASEDON=J2145+0031 1D`。

这些模拟产品只用于理解宇宙线检测、阶次追踪、提取、blaze 校正、重采样与加权合并，不应被引用为 Gemini 的真实 echelle 观测。若升级为真实高分辨率版本，建议另选带完整 bias/flat/order-flat/arc 和 pipeline product 的公开 UVES、HARPS、ESPRESSO 或 GHOST 教学数据，并重新核验其数据政策。
