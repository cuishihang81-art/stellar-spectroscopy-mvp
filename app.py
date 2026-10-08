from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from astropy.io import fits
from scipy.ndimage import median_filter
from scipy.special import erf

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
C_KMS = 299_792.458
TASKS = {"raw": "检查原始 CCD", "cal": "制定校正顺序", "cosmic": "作出宇宙线决策", "trace": "追踪阶次", "merge": "合并阶次", "rv": "提交 RV 结论"}

st.set_page_config(page_title="光谱侦探：从 CCD 到恒星速度", page_icon="🔭", layout="wide")
st.markdown("""
<style>
.block-container{max-width:1180px;padding-top:1.5rem}.hero{padding:1.5rem 2rem;border-radius:24px;background:radial-gradient(circle at 90% 20%,#155e75,#071b33 58%);color:white}.eyebrow{letter-spacing:.12em;color:#7dd3fc;font-size:.8rem}.step{padding:.85rem;border:1px solid #dbeafe;border-radius:14px;background:#f8fbff;min-height:105px}.big-result{font-size:2.2rem;font-weight:760;color:#075985}.fine{color:#64748b;font-size:.88rem}.mission{padding:.9rem 1.1rem;border-radius:14px;background:#eff6ff;border-left:5px solid #0ea5e9}.sim{padding:.7rem 1rem;border-radius:12px;background:#fff7ed;border-left:5px solid #f97316}.done{color:#15803d;font-weight:700}
</style>
<div class="hero"><div class="eyebrow">互动科研任务 · 约 20 分钟</div><h1>光谱侦探：从 CCD 到恒星速度</h1><p>你是今晚的数据负责人。每一步都要作出选择：什么是仪器痕迹？宇宙线要不要去？多阶光谱怎样变成一条可测量的曲线？</p></div>
""", unsafe_allow_html=True)

if "done" not in st.session_state:
    st.session_state.done = []


def finish(key):
    if key not in st.session_state.done:
        st.session_state.done.append(key)


@st.cache_data
def load_image(name):
    return np.asarray(fits.getdata(DATA / name), dtype=float)


@st.cache_data
def load_spectrum():
    with fits.open(DATA / "reference_spectrum.fits") as hdul:
        t = hdul["SPECTRUM"].data
        return np.array(t["wavelength"]), np.array(t["normalized_flux"])


@st.cache_data
def load_orders():
    with fits.open(DATA / "echelle_extracted_orders.fits") as hdul:
        return tuple(np.asarray(hdul[n].data, dtype=float) for n in ["WAVELENGTH", "ORDER_FLUX", "BLAZE"])


def image_figure(arr, title, cmap="gray", markers=None, zmax_percentile=99.5):
    lo, hi = np.nanpercentile(arr, [3, zmax_percentile])
    fig = go.Figure(go.Heatmap(z=arr, colorscale=cmap, zmin=lo, zmax=hi, showscale=False, hovertemplate="x=%{x}<br>y=%{y}<br>计数=%{z:.0f}<extra></extra>"))
    if markers:
        fig.add_trace(go.Scatter(x=[p[1] for p in markers], y=[p[0] for p in markers], mode="markers", marker=dict(symbol="circle-open", size=17, color="#ef4444", line=dict(width=2)), name="候选宇宙线"))
    fig.update_yaxes(autorange="reversed", title="CCD 空间方向")
    fig.update_xaxes(title="色散方向")
    fig.update_layout(title=title, height=430, margin=dict(l=10, r=10, t=48, b=10), legend=dict(orientation="h"))
    return fig


name_col, role_col = st.columns([1, 1])
observer = name_col.text_input("观测员代号", "小小天文学家")
role = role_col.selectbox("本次岗位", ["数据处理员", "宇宙线猎手", "光谱分析员"])
score = len(st.session_state.done)
st.progress(score / len(TASKS), text=f"{observer} · {role}　任务进度 {score}/{len(TASKS)}")
if score:
    st.caption("已完成：" + "、".join(TASKS[k] for k in st.session_state.done))

st.subheader("今晚的处理链")
labels = [("01", "读懂 CCD", "先观察，不急着按按钮。"), ("02", "校正与宇宙线", "判断哪些信号不来自恒星。"), ("03", "追踪与提取", "沿弯曲阶次收集光子。"), ("04", "合并与测量", "最后才得到一维谱和 RV。")]
for col, (n, title, desc) in zip(st.columns(4), labels):
    col.markdown(f'<div class="step"><b>{n} · {title}</b><br><span class="fine">{desc}</span></div>', unsafe_allow_html=True)
st.caption("原始 FITS → overscan/bias/flat → 宇宙线判断 → 阶次定位 → 背景扣除与提取 → blaze 校正 → 重采样与合并 → 谱线中心 → RV")

tabs = st.tabs(["任务 1 · 勘察", "任务 2 · 校正", "任务 3 · 宇宙线", "任务 4 · 多阶光谱", "任务 5 · 提取合并", "任务 6 · 测 RV", "处理手册"])
wavelength, reference_flux = load_spectrum()

with tabs[0]:
    st.markdown("### 先找证据，再处理")
    st.write("下面是真实的 Gemini South / GMOS 长缝光谱帧。移动鼠标读取像素，放大寻找亮带、放大器接缝和异常亮点。")
    stretch = st.slider("显示对比度（越高越容易看见微弱结构）", 97.0, 99.9, 99.5, 0.1)
    raw = load_image("01_overscan_corrected_raw.fits")
    st.plotly_chart(image_figure(raw, "真实 GMOS 原始科学曝光：J2145+0031", zmax_percentile=stretch), width="stretch")
    clue = st.radio("哪一个判断最科学？", ["最亮的像素一定来自恒星", "原始帧混合了天体、仪器和粒子信号", "FITS 只是一种图片格式"], index=None)
    if st.button("提交勘察记录", key="raw_submit"):
        if clue == "原始帧混合了天体、仪器和粒子信号":
            finish("raw"); st.success("正确：观测到的数值不等于纯天体信号。FITS 还保存仪器与观测元数据。")
        else:
            st.error("再想想：亮点可能是恒星、弧灯线、热像素，也可能是宇宙线。")

with tabs[1]:
    st.markdown("### 你来安排校正顺序")
    st.write("先选一条处理路线。真实管线还包含坏像素掩膜、增益、畸变和误差传播；不同仪器的具体先后可能不同。")
    routes = ["A　减 Bias → Flat → 检查宇宙线 → 波长定标 → 提取", "B　提取 → Flat → 减 Bias → 波长定标 → 去宇宙线", "C　波长定标 → 提取 → 减 Bias → Flat → 去宇宙线"]
    route = st.radio("哪条路线最适合作为本次教学流程？", routes, index=None)
    if st.button("让值班科学家审阅", key="cal_submit"):
        if route == routes[0]:
            finish("cal"); st.success("这是一条合理的教学顺序。实际先后会随仪器和算法改变，但提取前必须掌握校正与质量标记。")
        else:
            st.info("提示：先认识并校正电子学基线与响应，再处理异常/定标，最后提取。")
    st.markdown("#### 为什么肉眼常常看不出校正差别？")
    st.write("真实校正通常只改变总计数的一小部分，却会系统性地影响精密测量。下面同时给出真实数据和“教学放大镜”：放大的是两阶段之差，不是伪造新的科学结果。")
    stage = st.radio("选择一项校正", ["Overscan：每次读出时的电子学零点", "Bias：零秒曝光记录的固定底纹", "Flat：不同像素灵敏度不一样"], horizontal=True)
    over = load_image("01_overscan_corrected_raw.fits"); bias_after = load_image("02_bias_subtracted.fits"); flat_after = load_image("03_flat_corrected.fits")
    if stage.startswith("Overscan"):
        rows, cols = over.shape
        teaching_pattern = 8*np.sin(np.linspace(0,5*np.pi,rows))[:,None] + 5*((np.arange(cols)//64)%2)[None,:]
        before, after = over + teaching_pattern, over
        plain = "把相机读出时附加的、随行或放大器变化的零点估出来并减掉。这里的“校正前”是明确标注的教学增强重建。"
        identity = "教学增强示意"
    elif stage.startswith("Bias"):
        before, after = over, bias_after; plain = "像给空秤去皮：即使没有曝光，CCD 也有固定电子学底数。"; identity = "真实阶段差"
    else:
        before, after = bias_after, flat_after; plain = "像校正一排亮暗不均的眼睛：同样多的光，每个像素反应并不完全相同。"; identity = "真实阶段差"
    boost = st.slider("教学放大镜：把变化放大多少倍", 1, 30, 12)
    delta = after-before
    enhanced_after = before + boost*delta
    left, right = st.columns(2)
    left.plotly_chart(image_figure(before, "校正前", zmax_percentile=99.5), width="stretch")
    right.plotly_chart(image_figure(enhanced_after, f"校正后变化 ×{boost}（教学增强）", zmax_percentile=99.5), width="stretch")
    scale = max(float(np.nanpercentile(np.abs(delta),99)), 1e-6)
    diff_fig = go.Figure(go.Heatmap(z=delta, colorscale="RdBu", zmid=0, zmin=-scale, zmax=scale, colorbar=dict(title="改变的计数")))
    diff_fig.update_layout(title=f"机器真正减掉/修正了什么：{identity}",height=300,margin=dict(l=10,r=10,t=45,b=10)); diff_fig.update_xaxes(title="色散方向"); diff_fig.update_yaxes(title="空间方向",autorange="reversed")
    st.plotly_chart(diff_fig,width="stretch"); st.info(plain)
    with st.expander("打开 CuAr 弧灯：给像素装一把波长尺"):
        st.plotly_chart(image_figure(load_image("arc_mosaic.fits"), "CuAr 波长定标灯", "Turbo"), width="stretch")
        st.write("管线将亮线与实验室线表匹配，拟合像素位置到波长的函数，并检查残差。")

with tabs[2]:
    st.markdown("### 宇宙线不是“宇宙中的星光”")
    st.markdown("""
高能粒子穿过 CCD 时会在很少几个像素里突然释放大量电荷，留下尖点或短轨迹。它不携带目标恒星的光谱信息，却可能：

- 假装成窄发射线，制造不存在的元素；
- 落进吸收线，推偏线心和视向速度；
- 在一维提取时被加总，污染通量和误差。

去除的本质不是“把难看的点擦掉”，而是**检测异常、用邻域/模型估计替代，并保存掩膜和不确定度**。过度清理会误删真正的窄谱线。
""")
    e_raw = load_image("echelle_raw_simulated.fits")
    e_clean = load_image("echelle_cosmic_cleaned.fits")
    threshold = st.slider("候选阈值：高于局部噪声多少 σ？", 4.0, 12.0, 7.0, 0.5)
    # In this simulation we know the clean model, so the threshold experiment
    # can isolate particle hits without teaching that every sharp feature is bad.
    residual = e_raw-e_clean
    detected = residual > threshold*np.sqrt(np.maximum(e_clean,1))
    dynamic_clean = e_raw.copy(); dynamic_clean[detected] = e_clean[detected]
    coords = np.argwhere(detected)
    if len(coords) > 700:
        coords = coords[np.linspace(0,len(coords)-1,700,dtype=int)]
    m1,m2,m3 = st.columns(3)
    m1.metric("红圈候选像素",f"{detected.sum():,}")
    m2.metric("被替换的图像面积",f"{100*detected.mean():.3f}%")
    m3.metric("规则",f"> {threshold:.1f}σ")
    st.write("拖动阈值时，红圈和右侧修复结果会立即改变。阈值低：抓得多，也更容易误伤；阈值高：更谨慎，也可能漏掉较弱事件。本模拟知道无宇宙线真值；真实数据只能用邻域、多帧和物理模型估计。")
    left,right = st.columns(2)
    left.plotly_chart(image_figure(e_raw,"检测结果：红圈随阈值变化","Cividis",[tuple(p) for p in coords],99.7),width="stretch")
    right.plotly_chart(image_figure(dynamic_clean,"按当前阈值替换后的图像","Cividis",None,99.7),width="stretch")
    st.markdown("#### 放大一个命中阶次的现场")
    cy,cx,radius = 267,347,30
    crop_raw = e_raw[cy-radius:cy+radius,cx-radius:cx+radius]
    crop_clean = dynamic_clean[cy-radius:cy+radius,cx-radius:cx+radius]
    crop_mask = detected[cy-radius:cy+radius,cx-radius:cx+radius]
    z1,z2,z3 = st.columns(3)
    z1.plotly_chart(image_figure(crop_raw,"① 原始局部","Magma",None,99.9),width="stretch")
    z2.plotly_chart(image_figure(crop_mask.astype(float),"② 当前算法的红色掩膜","Reds",None,100),width="stretch")
    z3.plotly_chart(image_figure(crop_clean,"③ 替换后局部","Magma",None,99.9),width="stretch")
    st.caption("橙色提示：这是基于真实 GMOS 一维谱构造的 echelle 教学模拟；宇宙线位置是可验证的人工注入，不冒充真实事件。")
    situations = ["单张 30 分钟曝光，宇宙线压在目标阶次上", "8 张重复曝光，准备做带掩膜的 sigma-clipped 合并", "管线成品已有数据质量掩膜，且原始帧复核通过"]
    decisions = ["必须单独检测并处理", "可以不在单帧上替换，但必须在合并/掩膜中拒绝", "无需重复处理，但仍保留并检查质量标记"]
    scenario = st.selectbox("值班情境", situations)
    decision = st.radio("你的决定", decisions, index=None)
    if st.button("提交宇宙线处置单", key="cosmic_submit"):
        if decision and decisions.index(decision) == situations.index(scenario):
            finish("cosmic"); st.success("判断正确。关键不是每张图都必须运行同一个算法，而是最终分析必须拒绝污染并传播质量信息。")
        else:
            st.error("这项选择会留下污染或重复破坏数据。结合曝光数量、命中位置和已有掩膜再判断。")
    with st.expander("什么时候必须做？什么时候可以不单独做？", expanded=True):
        st.markdown("""
**必须检测并处理/屏蔽：** 单张或少量长曝光；命中目标孔径或关键谱线；需要精确通量、线宽或 RV；没有可靠质量掩膜。

**可以不对单帧另跑替换算法：** 有足够多的重复曝光，后续使用带掩膜的中位数或 sigma-clipped 合并；标准管线已经可靠标记并处理；某次命中确定在提取孔径外。即使如此仍应目视检查掩膜和合并残差。

**不应盲目处理：** 单帧中的真实窄发射线、坏列和热像素与宇宙线外形可能相似。应结合多帧重复性、二维形态、平场/BPM 和谱线物理判断。
""")

with tabs[3]:
    st.markdown("### 高分辨率光谱为什么像许多条弯曲彩带？")
    st.markdown('<div class="sim"><b>数据身份：</b>当前 Gemini B600 数据是普通长缝光谱，并非 echelle。下图是用其真实一维谱构造的教学模拟，用来展示“阶次—提取—blaze—合并”的数学关系。</div>', unsafe_allow_html=True)
    st.write("echelle 光栅在高衍射级工作，交叉色散器把互相重叠的波长段分开，CCD 上于是出现许多阶次。高分辨率恒星光谱常用这种设计，但不能说所有或大多数望远镜都只使用 echelle。")
    order_no = st.slider("选择并追踪一个阶次", 1, 9, 5)
    fig = image_figure(e_clean, "去除宇宙线后的模拟 echellogram", "Viridis", zmax_percentile=99.7)
    xx = np.arange(e_clean.shape[1]); xn = (xx-(len(xx)-1)/2)/((len(xx)-1)/2)
    yy = 34 + (order_no-1)*44 + ((order_no-1)-4)*0.8*xn + 5.5*xn**2
    aperture = st.slider("提取孔径半宽（像素）", 2, 10, 5)
    fig.add_trace(go.Scatter(x=xx,y=yy-aperture,mode="lines",line=dict(color="rgba(251,113,133,.7)",width=1),name="孔径上边界"))
    fig.add_trace(go.Scatter(x=xx,y=yy+aperture,mode="lines",line=dict(color="rgba(251,113,133,.7)",width=1),fill="tonexty",fillcolor="rgba(251,113,133,.25)",name="你收集的区域"))
    fig.add_trace(go.Scatter(x=xx, y=yy, mode="lines", line=dict(color="#facc15", width=3), name=f"阶次 {order_no} 中心"))
    st.plotly_chart(fig, width="stretch")
    cross_x = np.linspace(-15,15,301); profile = np.exp(-.5*(cross_x/2.1)**2)
    cross = go.Figure(go.Scatter(x=cross_x,y=profile,mode="lines",line=dict(color="#0369a1",width=3),name="恒星光"))
    cross.add_vrect(x0=-aperture,x1=aperture,fillcolor="#fb7185",opacity=.25,line_width=0,annotation_text="你的提取孔径")
    cross.update_layout(title="横切一刀：阴影区域会被加进一维光谱",height=300,margin=dict(l=10,r=10,t=45,b=10)); cross.update_xaxes(title="离阶次中心的距离（像素）"); cross.update_yaxes(title="相对亮度",range=[0,1.08])
    st.plotly_chart(cross,width="stretch")
    captured = 100*erf(aperture/(np.sqrt(2)*2.1)); background = 2*aperture+1
    a1,a2 = st.columns(2); a1.metric("理论上收集到的恒星光",f"{captured:.1f}%"); a2.metric("同时加进来的背景宽度",f"{background} 行像素")
    if aperture <= 3:
        st.warning("孔径偏窄：背景少，但恒星光稍有漂移就容易跑到阴影外。")
    elif aperture >= 8:
        st.warning("孔径偏宽：几乎不丢星光，但会加进更多天空噪声，甚至邻近阶次。")
    else:
        st.success("这是一个折中区域：保留大部分恒星光，同时不过度扩大背景。")
    if st.button("保存阶次轨迹", key="trace_submit"):
        finish("trace"); st.success("轨迹已写入观测日志。真实管线会沿色散方向拟合中心位置，并同时估计天空背景与方差。")

with tabs[4]:
    st.markdown("### 先看每个阶次，再决定怎样合并")
    ow, oflux, blaze = load_orders()
    chosen = st.slider("检查阶次编号", 1, len(ow), 5, key="extract_order") - 1
    blaze_correct = st.toggle("执行 blaze/阶次响应校正", value=False)
    shown = oflux[chosen] if blaze_correct else oflux[chosen] * blaze[chosen]
    fig = go.Figure(go.Scatter(x=ow[chosen], y=shown, mode="lines", line=dict(color="#0369a1", width=2)))
    fig.update_xaxes(title="波长（Å）"); fig.update_yaxes(title="相对流量" if blaze_correct else "CCD 计数（含 blaze）")
    fig.update_layout(height=360, margin=dict(l=10,r=10,t=20,b=10)); st.plotly_chart(fig, width="stretch")
    if not blaze_correct:
        st.warning("阶次中央效率高、两端低。现在直接拼接会出现波浪和台阶；先打开 blaze 校正。")
    else:
        st.success("校正后相邻阶次的重叠区可以互相核对。科研处理中还要处理通量定标、连续谱与误差。")
    st.markdown("#### 合并实验：重叠区由谁说了算？")
    exponent = st.slider("按 blaze / 信噪比加权的强度", 0.0, 4.0, 2.0, 0.5)
    grid = np.arange(3780.0,6330.0,0.9)
    def combine(power):
        numerator=np.zeros_like(grid); denominator=np.zeros_like(grid)
        for w,f,b in zip(ow,oflux,blaze):
            inside=(grid>=w.min())&(grid<=w.max()); fi=np.interp(grid[inside],w,f); bi=np.interp(grid[inside],w,b)
            weight=np.ones_like(bi) if power==0 else bi**power
            numerator[inside]+=fi*weight; denominator[inside]+=weight
        return np.divide(numerator,denominator,out=np.full_like(grid,np.nan),where=denominator>0)
    equal_merge = combine(0); merged = combine(exponent)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grid,y=equal_merge,mode="lines",line=dict(color="#94a3b8",width=1),name="灰：完全等权"))
    fig.add_trace(go.Scatter(x=grid,y=merged,mode="lines",line=dict(color="#0f766e",width=1.7),name=f"绿：当前权重 {exponent:.1f}"))
    fig.update_xaxes(title="波长（Å）",range=[3900,6200]); fig.update_yaxes(title="合并后归一化流量",range=[0.55,1.18]); fig.update_layout(title="全波段结果：两条线重合处说明选择影响很小",height=390,margin=dict(l=10,r=10,t=45,b=10)); st.plotly_chart(fig,width="stretch")
    st.markdown("##### 放大重叠区，直接看参数影响")
    zoom = (grid>4680)&(grid<4810)
    zfig = go.Figure()
    zfig.add_trace(go.Scatter(x=grid[zoom],y=equal_merge[zoom],mode="lines",line=dict(color="#94a3b8",width=2),name="等权"))
    zfig.add_trace(go.Scatter(x=grid[zoom],y=merged[zoom],mode="lines",line=dict(color="#0f766e",width=2.5),name="当前权重"))
    zfig.update_layout(height=330,margin=dict(l=10,r=10,t=15,b=10)); zfig.update_xaxes(title="重叠区波长（Å）"); zfig.update_yaxes(title="流量")
    st.plotly_chart(zfig,width="stretch")
    difference = 100*(merged-equal_merge)
    dfig=go.Figure(go.Scatter(x=grid[zoom],y=difference[zoom],mode="lines",fill="tozeroy",line=dict(color="#e11d48",width=2)))
    dfig.add_hline(y=0,line_color="#64748b"); dfig.update_layout(title="参数造成的直接变化（百分点）：0 表示与等权完全相同",height=250,margin=dict(l=10,r=10,t=45,b=10)); dfig.update_xaxes(title="波长（Å）"); dfig.update_yaxes(title="当前 − 等权")
    st.plotly_chart(dfig,width="stretch")
    truth=median_filter(np.interp(grid,wavelength,reference_flux),size=11); valid=np.isfinite(merged)&np.isfinite(equal_merge)&(truth>.7)&(truth<1.3)
    equal_err=100*np.median(np.abs(equal_merge[valid]-truth[valid])); current_err=100*np.median(np.abs(merged[valid]-truth[valid]))
    q1,q2=st.columns(2); q1.metric("等权合并的稳健误差分数",f"{equal_err:.2f}"); q2.metric("当前权重的稳健误差分数",f"{current_err:.2f}",delta=f"{equal_err-current_err:+.2f}（正数表示改善）")
    if exponent==0:
        st.info("现在每个像素投票权一样。阶次边缘很暗、噪声更大，却仍与阶次中央拥有同样权重。")
    else:
        st.info("增大参数后，阶次中央的高响应/高信噪比区域票数更多，边缘票数更少。参数不是越大越好，应以误差和接缝检查决定。")
    if st.button("接受合并谱并写入 FITS", key="merge_submit"):
        if blaze_correct:
            finish("merge"); st.success("合并完成：重叠区使用响应权重，阶次边缘的低信噪比数据贡献较小。现在才得到可用于测线的一维谱。")
        else:
            st.error("值班科学家拒绝了产品：请先检查并执行 blaze 校正。")

with tabs[5]:
    st.markdown("### 最后一关：亲手测一条吸收线")
    rest = 4471.48; window = (wavelength>4435)&(wavelength<4510); local_w, local_f = wavelength[window], reference_flux[window]
    core = (local_w>4460)&(local_w<4485); suggested = float(local_w[core][np.nanargmin(local_f[core])])
    observed = st.slider("拖动 λobs 标尺，对准 He I 吸收谷（Å）", float(local_w.min()), float(local_w.max()), suggested, 0.05)
    fig = go.Figure(go.Scatter(x=local_w, y=local_f, mode="lines", line=dict(color="#075985", width=2))); fig.add_vline(x=rest,line_dash="dot",line_color="#f97316",annotation_text="实验室 λ₀"); fig.add_vline(x=observed,line_color="#16a34a",annotation_text="你的 λobs")
    fig.update_xaxes(title="波长（Å）"); fig.update_yaxes(title="归一化流量",range=[0.82,1.12]); fig.update_layout(height=380,margin=dict(l=10,r=10,t=35,b=10)); st.plotly_chart(fig,width="stretch")
    velocity = C_KMS*(observed-rest)/rest
    a,b,c = st.columns([1,1.5,1]); a.metric("实验室波长",f"{rest:.2f} Å"); b.markdown(f'<div class="big-result">{velocity:+.0f} km/s</div><div class="fine">视向速度估计</div>',unsafe_allow_html=True); c.metric("Δλ",f"{observed-rest:+.2f} Å")
    direction = "远离我们（红移）" if velocity>0 else "朝向我们（蓝移）"; confidence = st.select_slider("你对线心选择的信心",["低","中","高"],value="中")
    note = st.text_area("写一句观测日志",f"He I 4471 Å 显示目标{direction}；线心为手动估计。")
    with st.expander("建立一个最小误差预算：为什么做、怎样做？",expanded=True):
        st.write("报出一个速度而不报‘大概能差多少’，就像说桌子长 100 cm，却不说尺子只能读到 1 cm 还是 0.01 cm。最小预算先数清两个最直观的随机来源：")
        st.markdown("**① 线心不确定度：** 吸收谷有宽度和噪声，你每次放标尺的位置会略有不同。  \n**② 波长尺不确定度：** 弧灯拟合也有残差，相当于尺子的刻度略有偏差。")
        line_sigma = st.slider("线心选择不确定度（Å）",0.05,1.00,0.25,0.05)
        wave_sigma = st.slider("波长定标不确定度（Å）",0.05,1.00,0.20,0.05)
        total_wave_sigma = np.hypot(line_sigma,wave_sigma); sigma_v = C_KMS*total_wave_sigma/rest
        budget = go.Figure(go.Bar(x=[line_sigma,wave_sigma,total_wave_sigma],y=["线心","波长尺","合成"],orientation="h",marker_color=["#38bdf8","#fb923c","#0f766e"],text=[f"{line_sigma:.2f} Å",f"{wave_sigma:.2f} Å",f"{total_wave_sigma:.2f} Å"],textposition="auto"))
        budget.update_layout(height=230,margin=dict(l=10,r=10,t=15,b=30),xaxis_title="波长不确定度（Å）",showlegend=False); st.plotly_chart(budget,width="stretch")
        c1,c2=st.columns(2); c1.metric("合成波长不确定度",f"±{total_wave_sigma:.2f} Å"); c2.metric("换算成速度",f"±{sigma_v:.0f} km/s")
        st.latex(r"\sigma_\lambda=\sqrt{\sigma_{line}^2+\sigma_{cal}^2},\qquad \sigma_v\approx \frac{c}{\lambda_0}\sigma_\lambda")
        st.caption("平方后相加，是因为这里把两项当作彼此独立的随机误差；已知的系统偏差应该先改正，不能只塞进这个平方根。")
        bary = st.checkbox("已执行观测者运动的日心/重心改正")
        if not bary:
            st.warning("尚未改正：地球公转和自转会造成系统性速度偏移。它不是‘多测几次就平均掉’的普通噪声，必须根据观测时间、位置和目标方向计算并改正。")
    if st.button("签署并提交 RV 结果",type="primary",key="rv_submit"):
        finish("rv"); st.success(f"任务完成：{observer} 测得 {velocity:+.0f} km/s，信心“{confidence}”。科学记录已包含方法限制。")
    log_text = f"""光谱侦探观测日志
观测员：{observer}
岗位：{role}
目标：J2145+0031
谱线：He I 4471.48 Å
观测线心：{observed:.2f} Å
教学 RV：{velocity:+.0f} km/s
信心：{confidence}
记录：{note}
限制：近似线性波长尺；未传播完整误差；日心/重心改正状态需由分析者核实。
"""
    st.download_button("下载我的观测日志",log_text,file_name="J2145+0031_观测日志.txt",mime="text/plain")
    st.latex(r"v=c\,\frac{\lambda_{obs}-\lambda_0}{\lambda_0}"); st.warning("教学结果：当前波长轴为近似线性尺，未做日心/重心改正，也未传播完整误差，不能作为发表级 RV。")

with tabs[6]:
    st.markdown("### 为什么处理不是固定按钮清单？")
    st.write("不同探测器、光谱仪和科学目标需要不同策略。可靠流程必须保存原始数据、校准来源、参数、掩膜、误差和日志，使每一步都能回退和复现。")
    st.markdown("""
| 决策点 | 你要问的问题 | 常见陷阱 |
|---|---|---|
| Bias / overscan | 基线是否随放大器和时间变化？ | 把结构性偏置当作天体背景 |
| Flat / blaze | 校正的是像素响应还是光谱仪效率包络？ | 将两者混为一个除法 |
| 宇宙线 | 有几帧？命中哪里？已有 DQ mask 吗？ | 误删真实窄线或不传播掩膜 |
| 阶次提取 | 轨迹、孔径、天空背景是否稳定？ | 孔径太宽引入相邻阶次 |
| 阶次合并 | 重叠区的波长与通量尺度一致吗？ | 等权使用低信噪比阶次边缘 |
| RV | 线心、波长解、重心改正和误差可靠吗？ | 把教学公式结果当发表值 |
""")
    st.info("下一版可增加：多曝光 sigma-clipping 动画、真正公开 UVES/HARPS echelle 原始帧、弧灯线匹配小游戏、误差预算、双星多历元 RV 与轨道拟合。")

st.divider()
if len(st.session_state.done) == len(TASKS):
    st.balloons(); st.markdown(f'<div class="mission"><span class="done">任务完成：</span>{observer} 已从原始 CCD 走到可解释的 RV 结论，并留下质量控制记录。</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="mission">还有 <b>{len(TASKS)-len(st.session_state.done)}</b> 项任务未签署。可以自由探索，但科学结论必须能追溯到每一步证据。</div>', unsafe_allow_html=True)
st.caption("真实数据：Gemini South / GMOS 官方 DRAGONS 教程 Example 1。Echelle 与宇宙线场景为明确标注的教学模拟，基于真实 J2145+0031 一维谱构造。")
