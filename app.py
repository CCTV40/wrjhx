import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import time

st.set_page_config(page_title="无人机航线规划", layout="wide")

# 初始化状态（确保不会清空历史航点）
if "obstacles" not in st.session_state:
    st.session_state.obstacles = []
if "waypoints" not in st.session_state:
    st.session_state.waypoints = []  # 多个航点列表
if "flying" not in st.session_state:
    st.session_state.flying = False
if "current_wp_idx" not in st.session_state:
    st.session_state.current_wp_idx = 0
if "fly_time" not in st.session_state:
    st.session_state.fly_time = 0

# 南京科技职业学院坐标
NPI_LAT = 32.2341
NPI_LON = 118.7494
FLY_SPEED = 8.0

# 界面
st.title("📡 无人机航线规划（南京科技职业学院）")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.info("左侧工具栏点 📍 标记添加航点")
with col2:
    if st.button("🧹 清空航点"):
        st.session_state.waypoints = []
with col3:
    if st.button("🚀 开始飞行"):
        if len(st.session_state.waypoints) >= 2:
            st.session_state.flying = True
            st.session_state.current_wp_idx = 0
            st.session_state.fly_time = 0
        else:
            st.warning("至少需要2个航点！")
with col4:
    if st.button("⏹ 停止飞行"):
        st.session_state.flying = False

# 监控面板
st.subheader("📊 飞行监控")
m1, m2, m3, m4 = st.columns(4)
m1.metric("当前航点", f"{st.session_state.current_wp_idx+1}/{len(st.session_state.waypoints)}")
m2.metric("速度", f"{FLY_SPEED} m/s")
m3.metric("已用时间", f"{st.session_state.fly_time}s")
battery = max(0, 100 - st.session_state.current_wp_idx * 6)
m4.metric("电量", f"{battery}%")

# 地图
st.subheader("🗺️ 地图")
m = folium.Map(location=[NPI_LAT, NPI_LON], zoom_start=17, tiles="Esri WorldImagery")
Draw(export=True).add_to(m)

# 绘制所有航点 + 航线
if len(st.session_state.waypoints) >= 2:
    folium.PolyLine(
        st.session_state.waypoints,
        color="blue", weight=5, opacity=0.8
    ).add_to(m)

for i, wp in enumerate(st.session_state.waypoints):
    folium.CircleMarker(
        location=wp, radius=6, color="blue", fill=True, popup=f"航点{i+1}"
    ).add_to(m)

# 显示地图
map_data = st_folium(m, width=1200, height=600)

# --------------- 关键修复：追加航点，不覆盖 ---------------
if map_data and "all_drawings" in map_data and map_data["all_drawings"] is not None:
    for item in map_data["all_drawings"]:
        if item["geometry"]["type"] == "Point":
            lat = item["geometry"]["coordinates"][1]
            lng = item["geometry"]["coordinates"][0]
            point = (lat, lng)

            # 不重复添加
            if point not in st.session_state.waypoints:
                st.session_state.waypoints.append(point)

# 飞行模拟
if st.session_state.flying and st.session_state.current_wp_idx < len(st.session_state.waypoints)-1:
    st.session_state.current_wp_idx += 1
    st.session_state.fly_time += 1
    time.sleep(0.8)
    st.rerun()

if st.session_state.current_wp_idx >= len(st.session_state.waypoints)-1 and len(st.session_state.waypoints) >= 2:
    st.success("✅ 飞行任务完成！")
    st.session_state.flying = False

st.success(f"✅ 当前航点数量：{len(st.session_state.waypoints)}")
