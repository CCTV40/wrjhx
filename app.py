import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import time

st.set_page_config(page_title="无人机航线规划", layout="wide")

# 初始化状态
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
if "selected_obs" not in st.session_state:
    st.session_state.selected_obs = []

# 南京科技职业学院
NPI_LAT = 32.2341
NPI_LON = 118.7494
FLY_SPEED = 8.0

# 界面
st.title("📡 无人机航线规划（南京科技职业学院）")
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🧹 清空所有航点"):
        st.session_state.waypoints = []
with col2:
    if st.button("🧹 清空所有障碍物"):
        st.session_state.obstacles = []
        st.session_state.selected_obs = []
with col3:
    if st.button("🚀 开始飞行"):
        if len(st.session_state.waypoints) >=2:
            st.session_state.flying = True
            st.session_state.current_wp_idx = 0
            st.session_state.fly_time = 0
        else:
            st.warning("至少2个航点！")
with col4:
    if st.button("⏹ 停止飞行"):
        st.session_state.flying = False

# 监控面板
st.subheader("📊 飞行监控")
c1,c2,c3,c4 = st.columns(4)
c1.metric("当前航点", f"{st.session_state.current_wp_idx+1}/{len(st.session_state.waypoints)}")
c2.metric("飞行速度", f"{FLY_SPEED} m/s")
c3.metric("已用时间", f"{st.session_state.fly_time}s")
battery = max(0, 100 - st.session_state.current_wp_idx * 5)
c4.metric("电量", f"{battery}%")

# 地图
st.subheader("🗺️ 操作说明：左侧点 📍 标记 添加航点 | 多边形画障碍物")
m = folium.Map(
    location=[NPI_LAT, NPI_LON],
    zoom_start=17,
    tiles="Esri WorldImagery"
)

# 开启绘图工具
Draw(
    export=False,
    draw_options={
        "marker": True,    # 航点
        "polygon": True,   # 障碍物
        "rectangle": True, # 圈选
        "polyline": False,
        "circle": False
    }
).add_to(m)

# 画障碍物
for idx, obs in enumerate(st.session_state.obstacles):
    col = "#ff0000" if idx in st.session_state.selected_obs else "#ff8888"
    folium.Polygon(
        locations=obs,
        color=col,
        fill=True,
        fill_opacity=0.3
    ).add_to(m)

# 画航点 + 航线
if len(st.session_state.waypoints) >=2:
    folium.PolyLine(
        st.session_state.waypoints,
        color="blue", weight=4
    ).add_to(m)

for i, wp in enumerate(st.session_state.waypoints):
    folium.CircleMarker(
        wp, radius=5, color="blue", fill=True, popup=f"航点{i+1}"
    ).add_to(m)

# 显示地图
data = st_folium(m, width=1200, height=600, key="map")

# ---------------------- 【修复：航点秒响应】----------------------
try:
    if data and data.get("all_drawings"):
        for obj in data["all_drawings"]:
            geo = obj["geometry"]
            if geo["type"] == "Point":
                lat = geo["coordinates"][1]
                lng = geo["coordinates"][0]
                point = (lat, lng)
                if point not in st.session_state.waypoints:
                    st.session_state.waypoints.append(point)

            if geo["type"] == "Polygon":
                pts = [(p[1], p[0]) for p in geo["coordinates"][0]]
                if pts not in st.session_state.obstacles and len(pts) > 3:
                    st.session_state.obstacles.append(pts)
except:
    pass

# 飞行模拟
if st.session_state.flying and st.session_state.current_wp_idx < len(st.session_state.waypoints)-1:
    st.session_state.current_wp_idx +=1
    st.session_state.fly_time +=1
    time.sleep(0.9)
    st.rerun()

if st.session_state.current_wp_idx >= len(st.session_state.waypoints)-1 and len(st.session_state.waypoints)>=2:
    st.success("✅ 飞行完成！")
    st.session_state.flying = False

st.success(f"✅ 航点：{len(st.session_state.waypoints)} ｜ 障碍物：{len(st.session_state.obstacles)}")
