import streamlit as st
import numpy as np

st.set_page_config(page_title="无人机航线规划", layout="wide")

# 初始化状态
if "obstacles" not in st.session_state:
    st.session_state.obstacles = []  # 障碍物点集
if "waypoints" not in st.session_state:
    st.session_state.waypoints = []  # 航点
if "mode" not in st.session_state:
    st.session_state.mode = "添加航点"
if "fly_time" not in st.session_state:
    st.session_state.fly_time = 0
if "flying" not in st.session_state:
    st.session_state.flying = False

SAFE_RADIUS = 30

# 界面
st.title("📡 无人机航线规划与安全监控 Demo")

col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🖌️ 绘制障碍物"):
        st.session_state.mode = "绘制障碍物"
with col2:
    if st.button("📍 添加航点"):
        st.session_state.mode = "添加航点"
with col3:
    if st.button("🚀 开始模拟飞行"):
        st.session_state.flying = True
with col4:
    if st.button("🧹 清空全部"):
        st.session_state.obstacles = []
        st.session_state.waypoints = []
        st.session_state.flying = False

# 监控面板
st.subheader("📊 飞行监控")
c1, c2, c3, c4 = st.columns(4)
c1.metric("当前航点", f"{len(st.session_state.waypoints)}/{len(st.session_state.waypoints)}")
c2.metric("飞行速度", "8.0 m/s")
c3.metric("已用时间", f"{st.session_state.fly_time} s")
c4.metric("电量", "100 %")

# 画布（Streamlit 专用）
st.subheader("🗺️ 飞行区域")
canvas_result = st_canvas(
    fill_color="#eee",
    stroke_width=2,
    stroke_color="red" if st.session_state.mode == "绘制障碍物" else "blue",
    background_color="#e8f4f8",
    width=1200,
    height=500,
    drawing_mode="polygon" if st.session_state.mode == "绘制障碍物" else "point",
    key="canvas",
)

# 处理障碍物
if canvas_result.json_data is not None:
    objects = canvas_result.json_data["objects"]
    
    # 清空旧数据，避免重复
    st.session_state.obstacles = []
    st.session_state.waypoints = []

    for o in objects:
        if o["type"] == "polygon":
            points = [
                (p[0], p[1]) for p in zip(o["path"][::2], o["path"][1::2])
            ]
            st.session_state.obstacles.append(points)
        
        if o["type"] == "point":
            x, y = o["left"], o["top"]
            st.session_state.waypoints.append((x, y))

st.success(f"✅ 障碍物：{len(st.session_state.obstacles)} 个")
st.success(f"✅ 航点：{len(st.session_state.waypoints)} 个")
