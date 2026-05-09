import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import numpy as np
import time

st.set_page_config(page_title="无人机航线规划", layout="wide")

# 初始化session状态
if "obstacles" not in st.session_state:
    st.session_state.obstacles = []
if "waypoints" not in st.session_state:
    st.session_state.waypoints = []
if "flying" not in st.session_state:
    st.session_state.flying = False
if "current_wp_idx" not in st.session_state:
    st.session_state.current_wp_idx = 0
if "fly_time" not in st.session_state:
    st.session_state.fly_time = 0

# 配置参数
SAFE_RADIUS = 10  # 安全半径（米）
FLY_SPEED = 8.0   # 飞行速度（m/s）
# 南京科技职业学院坐标
NPI_LAT = 32.2341
NPI_LON = 118.7494

# 标题与控制按钮
st.title("📡 无人机航线规划与安全监控 Demo（南京科技职业学院）")
col_btn = st.columns(4)
with col_btn[0]:
    if st.button("🖌️ 绘制障碍物"):
        st.info("在地图上使用Draw工具绘制多边形障碍物")
with col_btn[1]:
    if st.button("📍 重置航点"):
        st.session_state.waypoints = []
with col_btn[2]:
    if st.button("🚀 开始模拟飞行"):
        if len(st.session_state.waypoints) >= 2:
            st.session_state.flying = True
            st.session_state.current_wp_idx = 0
            st.session_state.fly_time = 0
        else:
            st.warning("请先在地图上添加至少2个航点！")
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

# 创建地图（定位在南京科技职业学院）
st.subheader("🗺️ 飞行区域 - 南京科技职业学院")
m = folium.Map(
    location=[NPI_LAT, NPI_LON],
    zoom_start=16,
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles &copy; Esri"
)

# 添加绘制控件（障碍区圈选）
draw = Draw(
    draw_options={
        "polygon": True,
        "rectangle": True,
        "polyline": False,
        "circle": False,
        "marker": True,
        "circlemarker": False
    },
    edit_options={"edit": True, "remove": True}
)
draw.add_to(m)

# 添加已有的障碍物和航点
for obs in st.session_state.obstacles:
    folium.Polygon(obs, color="red", fill=True, fill_opacity=0.2).add_to(m)

for i, wp in enumerate(st.session_state.waypoints):
    folium.Marker(wp, tooltip=f"航点{i+1}").add_to(m)

# 显示地图并获取用户绘制结果
map_data = st_folium(m, width=1200, height=600)

# 处理用户绘制的元素
if map_data and "all_drawings" in map_data:
    drawings = map_data["all_drawings"]
    new_obstacles = []
    new_waypoints = []

    for d in drawings:
        if d["geometry"]["type"] in ["Polygon", "Rectangle"]:
            coords = d["geometry"]["coordinates"][0]
            latlngs = [(coord[1], coord[0]) for coord in coords]
            new_obstacles.append(latlngs)
        elif d["geometry"]["type"] == "Point":
            latlng = (d["geometry"]["coordinates"][1], d["geometry"]["coordinates"][0])
            new_waypoints.append(latlng)

    # 安全距离检测（简化版）
    st.session_state.obstacles = new_obstacles
    st.session_state.waypoints = new_waypoints

    st.success(f"✅ 障碍物：{len(new_obstacles)} 个 | ✅ 航点：{len(new_waypoints)} 个")

# 飞行模拟逻辑
if st.session_state.flying and st.session_state.current_wp_idx < len(st.session_state.waypoints):
    st.session_state.current_wp_idx += 1
    st.session_state.fly_time += 1
    time.sleep(1)
    st.experimental_rerun()

if st.session_state.current_wp_idx >= len(st.session_state.waypoints) and len(st.session_state.waypoints) > 0:
    st.success("🎉 飞行任务已完成！")
    st.session_state.flying = False
