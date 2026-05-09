import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import math
import time

# ====================== 全局状态（永不覆盖） ======================
st.set_page_config(page_title="无人机自动避障", layout="wide")

if "waypoints" not in st.session_state:
    st.session_state.waypoints = []
if "obstacles" not in st.session_state:
    st.session_state.obstacles = []
if "flying" not in st.session_state:
    st.session_state.flying = False
if "wp_index" not in st.session_state:
    st.session_state.wp_index = 0
if "fly_time" not in st.session_state:
    st.session_state.fly_time = 0

# 学校坐标
LAT = 32.2341
LON = 118.7494
SPEED = 8
SAFE_METER = 20

# ====================== 核心：避障检测 ======================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dLat = math.radians(lat2-lat1)
    dLon = math.radians(lon2-lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def is_safe_point(lat, lon, obstacles, safe_m):
    for obs in obstacles:
        for (olat, olon) in obs:
            if haversine(lat, lon, olat, olon) < safe_m:
                return False
    return True

def is_safe_line(p1, p2, obstacles, safe_m):
    lat1, lon1 = p1
    lat2, lon2 = p2
    for i in range(12):
        t = i / 11
        lat = lat1 + t*(lat2-lat1)
        lon = lon1 + t*(lon2-lon1)
        if not is_safe_point(lat, lon, obstacles, safe_m):
            return False
    return True

def auto_avoid_path(start, end, obstacles, safe_m):
    path = [start]
    current = start

    # 能直飞就直飞
    if is_safe_line(current, end, obstacles, safe_m):
        return [start, end]

    # 不能直飞 → 自动向右绕开障碍
    for _ in range(6):
        candidate = (current[0] + 0.00018, current[1] + 0.00018)
        if is_safe_point(candidate[0], candidate[1], obstacles, safe_m):
            path.append(candidate)
            current = candidate
            if is_safe_line(current, end, obstacles, safe_m):
                break

    path.append(end)
    return path

# ====================== 界面 ======================
st.title("🛰️ 南京科技职业学院 - 无人机自动避障航线规划")

col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🧹 清空航点"):
        st.session_state.waypoints = []
with col2:
    if st.button("🧹 清空障碍物"):
        st.session_state.obstacles = []
with col3:
    if st.button("✅ 自动避障规划"):
        if len(st.session_state.waypoints) >= 2:
            s = st.session_state.waypoints[0]
            e = st.session_state.waypoints[-1]
            st.session_state.waypoints = auto_avoid_path(s, e, st.session_state.obstacles, SAFE_METER)
with col4:
    if st.button("🚀 开始飞行"):
        st.session_state.flying = True
        st.session_state.wp_index = 0
        st.session_state.fly_time = 0

# ====================== 飞行监控 ======================
st.subheader("📊 飞行实时监控")
idx = st.session_state.wp_index
total_wp = len(st.session_state.waypoints)

remain = 0
for i in range(idx, total_wp-1):
    remain += haversine(*st.session_state.waypoints[i], *st.session_state.waypoints[i+1])
remain = round(remain,1)

c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("当前航点", f"{idx+1}/{total_wp}")
c2.metric("飞行速度", "8 m/s")
c3.metric("已用时间", f"{st.session_state.fly_time}s")
c4.metric("剩余距离", f"{remain}m")
c5.metric("预计到达", f"{int(remain/8)}s" if remain>0 else "0s")
c6.metric("剩余电量", f"{max(10, 100-idx*6)}%")

# ====================== 地图 ======================
m = folium.Map(location=[LAT, LON], zoom_start=17, tiles="Esri WorldImagery")
Draw(
    draw_options={
        "marker": True,
        "polygon": True,
        "rectangle": True,
        "polyline": False,
        "circle": False
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
    folium.CircleMarker(p, radius=7, color=color, fill=True).add_to(m)

data = st_folium(m, width=1200, height=550)

# ====================== 永久追加，不覆盖 ======================
try:
    if data and "all_drawings" in data:
        for item in data["all_drawings"]:
            geo = item["geometry"]
            # 航点
            if geo["type"] == "Point":
                lat = round(geo["coordinates"][1],5)
                lng = round(geo["coordinates"][0],5)
                p = (lat, lng)
                if p not in st.session_state.waypoints:
                    st.session_state.waypoints.append(p)
            # 障碍物
            if geo["type"] in ["Polygon","Rectangle"]:
                pts = [(round(p[1],5), round(p[0],5)) for p in geo["coordinates"][0]]
                if pts not in st.session_state.obstacles:
                    st.session_state.obstacles.append(pts)
except:
    pass

# ====================== 飞行模拟 ======================
if st.session_state.flying and idx < total_wp -1:
    st.session_state.wp_index +=1
    st.session_state.fly_time +=1
    time.sleep(0.8)
    st.rerun()

st.success(f"✅ 航点：{total_wp} ｜ 障碍物：{len(st.session_state.obstacles)}")
