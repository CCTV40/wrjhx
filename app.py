import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import math
import time
from datetime import timedelta

# ----------------- 基础配置 -----------------
st.set_page_config(page_title="无人机自动避障", layout="wide")

# 永久存储（不覆盖、不丢失）
if "waypoints" not in st.session_state:
    st.session_state.waypoints = []
if "obstacles" not in st.session_state:
    st.session_state.obstacles = []

# 飞行状态
if "flying" not in st.session_state:
    st.session_state.flying = False
if "wp_idx" not in st.session_state:
    st.session_state.wp_idx = 0
if "fly_time" not in st.session_state:
    st.session_state.fly_time = 0

# 南京科技职业学院
LAT = 32.2341
LON = 118.7494
SPEED = 8
SAFE_DISTANCE = 15  # 安全距离


# ----------------- 核心：自动避障路线生成 -----------------
def get_safe_route(start, end, obstacles, safe_dist):
    route = [start]
    current = start

    for _ in range(10):
        clear = True

        # 检查当前到终点是否安全
        for i in range(10):
            t = i / 9
            lat = current[0] + t * (end[0] - current[0])
            lng = current[1] + t * (end[1] - current[1])
            for obs in obstacles:
                for (olat, olng) in obs:
                    d = math.hypot(lat - olat, lng - olng) * 111000
                    if d < safe_dist:
                        clear = False
                        break
                if not clear:
                    break

        if clear:
            route.append(end)
            break

        # 不安全 → 自动往右绕路
        current = (current[0] + 0.00015, current[1] + 0.00015)
        route.append(current)

    return route


# ----------------- 界面 -----------------
st.title("🛰️ 南京科技职业学院 - 无人机自动避障航线规划")

col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🧹 清空航点"):
        st.session_state.waypoints = []
with col2:
    if st.button("🧹 清空障碍物"):
        st.session_state.obstacles = []
with col3:
    if st.button("🛣️ 自动避障规划"):
        if len(st.session_state.waypoints) >= 2:
            s = st.session_state.waypoints[0]
            e = st.session_state.waypoints[-1]
            st.session_state.waypoints = get_safe_route(
                s, e, st.session_state.obstacles, SAFE_DISTANCE
            )
with col4:
    if st.button("🚀 开始飞行"):
        st.session_state.flying = True
        st.session_state.wp_idx = 0
        st.session_state.fly_time = 0

# ----------------- 飞行监控面板 -----------------
st.subheader("📊 飞行实时监控")
idx = st.session_state.wp_idx
wp_count = len(st.session_state.waypoints)

remain = 0
for i in range(idx, wp_count - 1):
    remain += math.hypot(
        st.session_state.waypoints[i][0]-st.session_state.waypoints[i+1][0],
        st.session_state.waypoints[i][1]-st.session_state.waypoints[i+1][1]
    ) * 111000
remain = round(remain, 1)
eta = int(remain / SPEED) if remain > 0 else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("当前航点", f"{idx+1}/{wp_count}")
c2.metric("飞行速度", f"{SPEED} m/s")
c3.metric("已用时间", str(timedelta(seconds=st.session_state.fly_time)))
c4.metric("剩余距离", f"{remain} m")
c5.metric("预计到达", str(timedelta(seconds=eta)))
c6.metric("剩余电量", f"{max(10, 100-idx*5)} %")

# ----------------- 地图 -----------------
m = folium.Map(location=[LAT, LON], zoom_start=17, tiles="Esri WorldImagery")
Draw(
    draw_options={
        "marker": True,
        "polygon": True,
        "rectangle": True,
        "polyline": False, "circle": False
    }
).add_to(m)

# 画障碍物
for obs in st.session_state.obstacles:
    folium.Polygon(obs, color="red", fill=True, fill_opacity=0.4).add_to(m)

# 画航线
if len(st.session_state.waypoints) >= 2:
    folium.PolyLine(
        st.session_state.waypoints, color="blue", weight=5
    ).add_to(m)

# 画航点
for i, p in enumerate(st.session_state.waypoints):
    color = "yellow" if i == idx else "blue"
    folium.CircleMarker(p, radius=6, color=color, fill=True).add_to(m)

map_data = st_folium(m, width=1200, height=550, key="map")

# ----------------- 【稳定不覆盖】读取数据 -----------------
try:
    if map_data and "all_drawings" in map_data:
        for item in map_data["all_drawings"]:
            geo = item["geometry"]

            # 航点 追加不覆盖
            if geo["type"] == "Point":
                lat = geo["coordinates"][1]
                lng = geo["coordinates"][0]
                p = (round(lat, 5), round(lng, 5))
                if p not in st.session_state.waypoints:
                    st.session_state.waypoints.append(p)

            # 障碍物 追加不覆盖
            if geo["type"] in ["Polygon", "Rectangle"]:
                pts = [(round(p[1],5), round(p[0],5)) for p in geo["coordinates"][0]]
                if pts not in st.session_state.obstacles:
                    st.session_state.obstacles.append(pts)
except:
    pass

# ----------------- 自动飞行 -----------------
if st.session_state.flying and idx < wp_count - 1:
    st.session_state.wp_idx += 1
    st.session_state.fly_time += 1
    time.sleep(0.8)
    st.rerun()

st.success(f"✅ 航点：{wp_count} ｜ 障碍物：{len(st.session_state.obstacles)}")
