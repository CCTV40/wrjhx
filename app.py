import streamlit as st
from streamlit_drawable_canvas import st_canvas
import numpy as np
import time

st.set_page_config(page_title="无人机航线规划", layout="wide")

# 初始化session状态
if "obstacles" not in st.session_state:
    st.session_state.obstacles = []
if "waypoints" not in st.session_state:
    st.session_state.waypoints = []
if "mode" not in st.session_state:
    st.session_state.mode = "添加航点"
if "flying" not in st.session_state:
    st.session_state.flying = False
if "current_wp_idx" not in st.session_state:
    st.session_state.current_wp_idx = 0
if "fly_time" not in st.session_state:
    st.session_state.fly_time = 0

SAFE_RADIUS = 30  # 安全半径（像素）
FLY_SPEED = 8.0   # 飞行速度（m/s）

# 标题与控制按钮
st.title("📡 无人机航线规划与安全监控 Demo")
col_btn = st.columns(4)
with col_btn[0]:
    if st.button("🖌️ 绘制障碍物"):
        st.session_state.mode = "绘制障碍物"
with col_btn[1]:
    if st.button("📍 添加航点"):
        st.session_state.mode = "添加航点"
with col_btn[2]:
    if st.button("🚀 开始模拟飞行"):
        if len(st.session_state.waypoints) >= 2:
            st.session_state.flying = True
            st.session_state.current_wp_idx = 0
            st.session_state.fly_time = 0
        else:
            st.warning("请先添加至少2个航点！")
with col_btn[3]:
    if st.button("🧹 清空全部"):
        st.session_state.obstacles = []
        st.session_state.waypoints = []
        st.session_state.flying = False
        st.session_state.current_wp_idx = 0
        st.session_state.fly_time = 0

# 飞行监控面板
st.subheader("📊 飞行监控")
col_monitor = st.columns(4)
with col_monitor[0]:
    st.metric("当前航点", f"{st.session_state.current_wp_idx+1}/{len(st.session_state.waypoints)}")
with col_monitor[1]:
    st.metric("飞行速度", f"{FLY_SPEED} m/s")
with col_monitor[2]:
    st.metric("已用时间", f"{st.session_state.fly_time} s")
with col_monitor[3]:
    battery = max(0, 100 - st.session_state.current_wp_idx * 5)
    st.metric("电量", f"{battery} %")

# 画布设置
st.subheader("🗺️ 飞行区域")
drawing_mode = "polygon" if st.session_state.mode == "绘制障碍物" else "point"
stroke_color = "#ff0000" if st.session_state.mode == "绘制障碍物" else "#0000ff"

canvas_result = st_canvas(
    fill_color="rgba(255, 100, 100, 0.2)",  # 障碍物填充色（带透明度）
    stroke_width=2,
    stroke_color=stroke_color,
    background_color="#e8f4f8",
    width=1200,
    height=500,
    drawing_mode=drawing_mode,
    key="drone_canvas"
)

# 处理画布输入
if canvas_result.json_data is not None:
    objects = canvas_result.json_data["objects"]
    new_obstacles = []
    new_waypoints = []

    for obj in objects:
        if obj["type"] == "polygon":
            # 提取障碍物多边形顶点
            path = obj["path"]
            poly_points = [(path[i], path[i+1]) for i in range(0, len(path), 2)]
            new_obstacles.append(poly_points)
        elif obj["type"] == "point":
            # 提取航点坐标
            x, y = obj["left"], obj["top"]
            new_waypoints.append((x, y))

    # 安全距离检测：过滤掉障碍物安全区内的航点
    safe_waypoints = []
    for wp in new_waypoints:
        is_safe = True
        for obs in new_obstacles:
            for p in obs:
                dist = np.hypot(wp[0] - p[0], wp[1] - p[1])
                if dist < SAFE_RADIUS:
                    is_safe = False
                    break
            if not is_safe:
                break
        if is_safe:
            safe_waypoints.append(wp)

    st.session_state.obstacles = new_obstacles
    st.session_state.waypoints = safe_waypoints

    st.success(f"✅ 障碍物：{len(new_obstacles)} 个 | ✅ 安全航点：{len(safe_waypoints)} 个")

# 飞行模拟逻辑
if st.session_state.flying and st.session_state.current_wp_idx < len(st.session_state.waypoints):
    # 更新飞行状态
    st.session_state.current_wp_idx += 1
    st.session_state.fly_time += 1
    # 模拟延迟，控制飞行速度
    time.sleep(1)
    # 强制刷新页面
    st.experimental_rerun()

# 任务完成判断
if st.session_state.current_wp_idx >= len(st.session_state.waypoints) and len(st.session_state.waypoints) > 0:
    st.success("🎉 飞行任务已完成！")
    st.session_state.flying = False
