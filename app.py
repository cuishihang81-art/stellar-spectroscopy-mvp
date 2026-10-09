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

GLOSSARY = {
    "CCD": ("Charge-Coupled Device，电荷耦合器件", "把落到望远镜里的光变成数字的感光芯片，类似科研相机的眼睛。"),
    "FITS": ("Flexible Image Transport System", "天文学常用的数据文件；不只保存图像，还保存曝光时间、仪器设置等信息。"),
    "Overscan": ("过扫描区", "CCD 上不接收光的一小块读出区域，用来估计这一次读出的电子学零点。"),
    "Bias": ("偏置", "相机没有见光也会记录的底数，像空电子秤仍显示几克。"),
    "Flat": ("平场", "校正不同像素灵敏度不一致，像把一排明暗不均的眼睛调到同一标准。"),
    "Cosmic ray": ("宇宙线", "高能粒子撞进探测器留下的一次性亮点或短划痕，不是目标恒星的光。"),
    "Echelle": ("阶梯光栅光谱", "把很长的高分辨率彩虹折成许多条，排在同一张 CCD 上。"),
    "Blaze": ("闪耀响应", "同一条光谱阶次中央通常亮、两端暗的仪器效率包络。"),
    "S/N": ("Signal-to-Noise Ratio，信噪比", "有用信号相对于随机噪声的强弱；越高通常越可靠。"),
    "RV": ("Radial Velocity，视向速度", "天体沿着我们视线方向靠近或远离的速度。"),
    "Å": ("Ångström，埃", "常用波长单位；1 Å 等于一亿分之一厘米。"),
}

st.set_page_config(page_title="光谱侦探：从 CCD 到恒星速度", page_icon="🔭", layout="wide")
st.markdown("""
<style>
.block-container{max-width:1180px;padding-top:1.5rem}.hero{padding:1.5rem 2rem;border-radius:24px;background:radial-gradient(circle at 90% 20%,#155e75,#071b33 58%);color:white}.eyebrow{letter-spacing:.12em;color:#7dd3fc;font-size:.8rem}.step{padding:.85rem;border:1px solid #dbeafe;border-radius:14px;background:#f8fbff;min-height:105px}.big-result{font-size:2.2rem;font-weight:760;color:#075985}.fine{color:#64748b;font-size:.88rem}.mission{padding:.9rem 1.1rem;border-radius:14px;background:#eff6ff;border-left:5px solid #0ea5e9}.sim{padding:.7rem 1rem;border-radius:12px;background:#fff7ed;border-left:5px solid #f97316}.done{color:#15803d;font-weight:700}.learn{padding:1rem;border-radius:14px;background:#f0fdfa;border:1px solid #99f6e4;min-height:125px}.term{color:#075985;font-weight:750}.question{padding:1rem;border-radius:14px;background:#fefce8;border:1px solid #fde68a}.emoji{font-size:2rem;line-height:1.1}.mode{padding:.8rem 1rem;border-radius:14px;background:#eef2ff;border-left:5px solid #6366f1}
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
    # Large Plotly heatmaps dominate browser transfer and redraw time. Keep the
    # scientific array untouched, but send a display-resolution view.
    sy = max(1, int(np.ceil(arr.shape[0] / 330)))
    sx = max(1, int(np.ceil(arr.shape[1] / 520)))
    shown = arr[::sy, ::sx]
    x_axis = np.arange(arr.shape[1])[::sx]
    y_axis = np.arange(arr.shape[0])[::sy]
    lo, hi = np.nanpercentile(arr, [3, zmax_percentile])
    fig = go.Figure(go.Heatmap(x=x_axis, y=y_axis, z=shown, colorscale=cmap, zmin=lo, zmax=hi, showscale=False, hovertemplate="x=%{x}<br>y=%{y}<br>计数=%{z:.0f}<extra></extra>"))
    if markers:
        fig.add_trace(go.Scatter(x=[p[1] for p in markers], y=[p[0] for p in markers], mode="markers", marker=dict(symbol="circle-open", size=17, color="#ef4444", line=dict(width=2)), name="候选宇宙线"))
    fig.update_yaxes(autorange="reversed", title="CCD 空间方向")
    fig.update_xaxes(title="色散方向")
    fig.update_layout(title=title, height=430, margin=dict(l=10, r=10, t=48, b=10), legend=dict(orientation="h"))
    return fig


mode = st.radio("选择你的体验方式", ["🌱 第一次接触（推荐）", "🔬 科研体验"], horizontal=True)
beginner = mode.startswith("🌱")
st.markdown(
    '<div class="mode"><b>零基础模式：</b>先看图和动手，再认识术语；专业细节按需展开。</div>'
    if beginner else
    '<div class="mode"><b>科研体验模式：</b>保留数据身份、处理参数、误差与质量控制细节。</div>',
    unsafe_allow_html=True,
)
with st.expander("🛟 术语急救箱：看不懂的英文都在这里"):
    glossary_cols = st.columns(2)
    for idx, (term, (full, plain)) in enumerate(GLOSSARY.items()):
        glossary_cols[idx % 2].markdown(f"**{term}｜{full}**  \n{plain}")

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

pages = ["1 · 看懂相机数据", "2 · 清除相机痕迹", "3 · 找出宇宙线", "4 · 收集多阶光谱", "5 · 拼成完整光谱", "6 · 测量恒星速度", "📖 处理手册"]
page = st.radio("选择当前任务（每次只加载一页，切换会更快）", pages, horizontal=True, label_visibility="collapsed")

if page == pages[0]:
    st.markdown("### 先看见，再学习名字")
    st.write("这不是一张漂亮星空照，而是天文相机交给研究者的数字底片。先认出三类东西，不需要任何前置知识。")
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="learn"><div class="emoji">🌟</div><b>横向亮带</b><br>恒星的光被仪器按颜色展开，是我们真正想测的信号。</div>', unsafe_allow_html=True)
    c2.markdown('<div class="learn"><div class="emoji">📷</div><b>整幅底色与接缝</b><br>相机电子元件也会留下痕迹，不能误认为都是星光。</div>', unsafe_allow_html=True)
    c3.markdown('<div class="learn"><div class="emoji">⚡</div><b>孤立的尖亮点</b><br>可能是高能粒子的一次撞击，需要后续检查。</div>', unsafe_allow_html=True)
    st.caption("专业名字稍后再出现：现在只要记住，一张原始底片里混着‘目标、相机、偶发事件’。")
    stretch = st.slider("显示对比度（越高越容易看见微弱结构）", 97.0, 99.9, 99.5, 0.1)
    raw = load_image("01_overscan_corrected_raw.fits")
    st.plotly_chart(image_figure(raw, "真实 GMOS 原始科学曝光：J2145+0031", zmax_percentile=stretch), width="stretch")
    with st.expander("刚才出现的两个专业名词"):
        st.markdown("**CCD（电荷耦合器件）**：把光变成数字的感光芯片。  \n**FITS（Flexible Image Transport System）**：天文数据文件，除了像素还保存曝光时间和仪器设置。")
    st.markdown('<div class="question"><b>小挑战：</b>根据上面的三张提示卡，这张原始底片里有什么？</div>', unsafe_allow_html=True)
    clue = st.radio("选择你的观察结论", ["只有恒星发来的光", "恒星信号、相机痕迹和粒子事件混在一起", "它只是一张普通照片，没有其他信息"], index=None)
    if st.button("提交勘察记录", key="raw_submit"):
        if clue == "恒星信号、相机痕迹和粒子事件混在一起":
            finish("raw"); st.success("正确：观测到的数值不等于纯天体信号。FITS 还保存仪器与观测元数据。")
        else:
            st.info("看看上面的三张提示卡：研究者必须先把三类来源分开，才能测量恒星。再试一次吧。")

if page == pages[1]:
    st.markdown("### 先做三个视觉实验，再安排顺序")
    st.write("暂时不背单词。想象你在使用一台科研相机，它可能有下面三个问题：")
    b1, b2, b3 = st.columns(3)
    b1.markdown('<div class="learn"><div class="emoji">⚖️</div><b>空秤不归零</b><br>没有光时仍记录底数。减掉它叫 <span class="term">Bias（偏置）</span>。</div>', unsafe_allow_html=True)
    b2.markdown('<div class="learn"><div class="emoji">🎛️</div><b>本次零点漂移</b><br>每次读出的零点略不同。用无光读出区估计，叫 <span class="term">Overscan（过扫描）</span>。</div>', unsafe_allow_html=True)
    b3.markdown('<div class="learn"><div class="emoji">🟫</div><b>像素有明有暗</b><br>同样的光得到不同数字。校平它叫 <span class="term">Flat（平场）</span>。</div>', unsafe_allow_html=True)
    st.caption("下面切换三种校正，并把细微变化故意放大。先用眼睛看，再做最后的路线题。")
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
    diff_fig = go.Figure(go.Heatmap(z=delta[::2, ::2], colorscale="RdBu", zmid=0, zmin=-scale, zmax=scale, colorbar=dict(title="改变的计数")))
    diff_fig.update_layout(title=f"机器真正减掉/修正了什么：{identity}",height=300,margin=dict(l=10,r=10,t=45,b=10)); diff_fig.update_xaxes(title="色散方向"); diff_fig.update_yaxes(title="空间方向",autorange="reversed")
    st.plotly_chart(diff_fig,width="stretch"); st.info(plain)
    with st.expander("打开 CuAr 弧灯：给像素装一把波长尺"):
        st.plotly_chart(image_figure(load_image("arc_mosaic.fits"), "CuAr 波长定标灯", "Turbo"), width="stretch")
        st.write("管线将亮线与实验室线表匹配，拟合像素位置到波长的函数，并检查残差。")
    st.markdown('<div class="question"><b>现在再做路线题：</b>既然原始数字混有相机底数和像素差异，应该先校正，还是先急着提取最终光谱？</div>', unsafe_allow_html=True)
    routes = ["A　先校正相机底数与像素差异，再检查异常、定标和提取", "B　先提取最终光谱，之后再考虑相机问题", "C　不做校正，直接寻找最低点"]
    route = st.radio("选择一条本次教学路线", routes, index=None)
    if st.button("让值班科学家审阅", key="cal_submit"):
        if route == routes[0]:
            finish("cal"); st.success("正确。先把测量工具自身的偏差处理清楚，再从数据中提取恒星信号。")
        elif route:
            st.info("如果先把混合数据压成最终曲线，相机痕迹也会一起被加进去。回看三个视觉实验，再试一次。")
        else:
            st.warning("请先选择一条路线。")

if page == pages[2]:
    st.markdown("### ⚡ 找出只出现一次的异常亮点")
    if beginner:
        v1, v2, v3 = st.columns(3)
        v1.markdown('<div class="learn"><div class="emoji">🌌</div><b>恒星光</b><br>沿着光谱方向形成连续结构，是真正要保留的信息。</div>', unsafe_allow_html=True)
        v2.markdown('<div class="learn"><div class="emoji">⚡</div><b>宇宙线</b><br>高能粒子撞到相机，突然留下尖亮点；它不是恒星发来的光。</div>', unsafe_allow_html=True)
        v3.markdown('<div class="learn"><div class="emoji">🩹</div><b>处理原则</b><br>标记异常位置，再参考邻居或其他曝光估计；不能随便擦除所有亮点。</div>', unsafe_allow_html=True)
        st.write("拖动下面的阈值：数值越低，红圈越多；数值越高，算法越谨慎。直接看图比背定义更重要。")
    else:
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
    st.markdown('<div class="question"><b>情境挑战：</b>先看“有几张照片、亮点落在哪里、之前是否已处理”，再决定。答案就在情境和选项中，不需要额外知识。</div>', unsafe_allow_html=True)
    situations = ["只有 1 张长曝光，而且尖亮点正压在恒星光谱上", "有 8 张重复曝光，可以比较并在合并时排除只出现一次的亮点", "可靠管线已经标记并处理，人工复核也没有问题"]
    decisions = ["必须检测、标记并处理这个亮点", "单张可以不先替换，但合并时必须拒绝异常", "不用重复处理，但继续保留质量标记"]
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

if page == pages[3]:
    st.markdown("### 🌈 把一条很长的彩虹折进相机")
    st.markdown('<div class="sim"><b>数据身份：</b>当前 Gemini B600 数据是普通长缝光谱，并非 echelle。下图是用其真实一维谱构造的教学模拟，用来展示“阶次—提取—blaze—合并”的数学关系。</div>', unsafe_allow_html=True)
    if beginner:
        st.write("如果把一条很长、很精细的彩虹直接排成一行，相机可能装不下。阶梯光谱仪把它分成许多有重叠的短段，像把长纸条折成多行。每条弯曲亮带叫一个“阶次”。")
    else:
        st.write("Echelle 光栅在高衍射级工作，交叉色散器把互相重叠的波长段分开，CCD 上于是出现许多阶次。高分辨率恒星光谱常用这种设计，但不能说所有或大多数望远镜都只使用 echelle。")
    e_clean = load_image("echelle_cosmic_cleaned.fits")
    order_no = st.slider("选择并追踪一条彩虹带（专业名：阶次）", 1, 9, 5)
    fig = image_figure(e_clean, "去除宇宙线后的模拟 echellogram", "Viridis", zmax_percentile=99.7)
    xx = np.arange(e_clean.shape[1]); xn = (xx-(len(xx)-1)/2)/((len(xx)-1)/2)
    yy = 34 + (order_no-1)*44 + ((order_no-1)-4)*0.8*xn + 5.5*xn**2
    aperture = st.slider("光子收集网的半宽（专业名：提取孔径，单位为像素）", 2, 10, 5)
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

if page == pages[4]:
    st.markdown("### 🧩 把重叠的彩虹短段拼成一条")
    if beginner:
        st.write("每一段的中央通常清楚、两端较暗。先把这种明暗包络校平，再让清楚的部分拥有更大投票权，像拼接几张有重叠的全景照片。")
    wavelength, reference_flux = load_spectrum()
    ow, oflux, blaze = load_orders()
    chosen = st.slider("检查阶次编号", 1, len(ow), 5, key="extract_order") - 1
    blaze_correct = st.toggle("把‘中间亮、两端暗’的仪器效果校平（Blaze 校正）", value=False)
    shown = oflux[chosen] if blaze_correct else oflux[chosen] * blaze[chosen]
    fig = go.Figure(go.Scatter(x=ow[chosen], y=shown, mode="lines", line=dict(color="#0369a1", width=2)))
    fig.update_xaxes(title="波长（Å）"); fig.update_yaxes(title="相对流量" if blaze_correct else "CCD 计数（含 blaze）")
    fig.update_layout(height=360, margin=dict(l=10,r=10,t=20,b=10)); st.plotly_chart(fig, width="stretch")
    if not blaze_correct:
        st.warning("阶次中央效率高、两端低。现在直接拼接会出现波浪和台阶；先打开 blaze 校正。")
    else:
        st.success("校正后相邻阶次的重叠区可以互相核对。科研处理中还要处理通量定标、连续谱与误差。")
    st.markdown("#### 合并实验：重叠区由谁说了算？")
    exponent = st.slider("让清晰区域拥有更大投票权（专业名：按 Blaze / 信噪比加权）", 0.0, 4.0, 2.0, 0.5)
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

if page == pages[5]:
    st.markdown("### 🚑 最后一关：像听救护车一样测恒星")
    st.write("救护车靠近时声音变尖、远离时变低；光也会发生类似的多普勒位移。吸收谷向更长波长移动叫红移，表示远离；向更短波长移动叫蓝移，表示靠近。")
    d1, d2 = st.columns(2)
    d1.markdown('<div class="learn"><div class="emoji">🔵 ←</div><b>蓝移</b><br>谱线跑向较短波长：目标朝我们靠近。</div>', unsafe_allow_html=True)
    d2.markdown('<div class="learn"><div class="emoji">→ 🔴</div><b>红移</b><br>谱线跑向较长波长：目标正在远离。</div>', unsafe_allow_html=True)
    wavelength, reference_flux = load_spectrum()
    rest = 4471.48; window = (wavelength>4435)&(wavelength<4510); local_w, local_f = wavelength[window], reference_flux[window]
    core = (local_w>4460)&(local_w<4485); suggested = float(local_w[core][np.nanargmin(local_f[core])])
    observed = st.slider("拖动绿色标尺，对准最低的吸收谷（λobs 是‘看到的波长’，单位 Å）", float(local_w.min()), float(local_w.max()), suggested, 0.05)
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

if page == pages[6]:
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
