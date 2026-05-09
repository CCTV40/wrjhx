import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import time
import json
import math
from datetime import timedelta
import random

st.set_page_config(page_title="无人机智能避障航线规划", layout="wide")

# ========================== 记忆存储 ==========================
if "obstacles" not in st.session_state:
    st.session_state.obstacles = json.loads(st.session_state.get("saved_obstacles", "[]"))
if "waypoints" not in st.session_state:
    st.session_state.waypoints = json.loads(st.session_state.get("saved_waypoints", "[]"))
if "safe_radius" not in st.session_state:
    st.session_state.safe_radius = 15

def save_data():
    st.session_state["saved_obstacles"] = json.dumps(st.session_state.obstacles)
    st.session_state["saved_waypoints"] = json.dumps(st.session_state.waypoints)

# ========================== 飞行状态 ==========================
if "flying" not in st.session_state:
    st.session_state.flying = False
if "current_wp_idx" not in st.session_state:
    st.session_state.current_wp_idx = 0
if "fly_time" not in st.session_state:
    st.session_state.fly_time = 0

# 学校坐标
NPI_LAT = 32.2341
NPI_LON = 118.7494
FLY_SPEED = 8.0

# ========================== 核心算法 ==========================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def point_in_obstacle(lat, lon, obstacles, safe_m):
    for obs in obstacles:
        for (olat, olon) in obs:
            if haversine(lat, lon, olat, olon) < safe_m:
                return True
    return False

def is_segment_safe(p1, p2, obstacles, safe_m):
    lat1, lon1 = p1
    lat2, lon2 = p2
    steps = 20
    for i in range(steps+1):
        t = i/steps
        lat = lat1 + t*(lat2-lat1)
        lon = lon1 + t*(lon2-lon1)
        if point_in_obstacle(lat, lon, obstacles, safe_m):
            return False
    return True

def find_safe_route(start, end, obstacles, safe_m):
    path = [start]
    current = start
    for _ in range(8):
        if is_segment_safe(current, end, obstacles, safe_m):
            path.append(end)
            break
        for __ in range(20):
            dx = random.uniform(-0.0003, 0.0003)
            dy = random.uniform(-0.0003, 0.0003)
            new_p = (current[0]+dx, current[1]+dy)
            if not point_in_obstacle(new_p[0], new_p[1], obstacles, safe_m):
                if is_segment_safe(current, new_p, obstacles, safe_m):
                    current = new_p
                    path.append(current)
                    break
    return path

def calc_remain(waypts, idx):
    d = 0
    for i in range(idx, len(waypts)-1):
        d += haversine(waypts[i][0], waypts[i][1], waypts[i+1][0], waypts[i+1][1])
    return round(d,1)

# ========================== 界面 ==========================
st.title("🛰️ 无人机智能避障航线规划｜自动绕开障碍物")

safe_radius = st.slider("安全半径（米）", 5, 50, st.session_state.safe_radius)
st.session_state.safe_radius = safe_radius

c1,c2,c3,c4 = st.columns(4)
with c1:
    if st.button("🧹 清空障碍物"):
        st.session_state.obstacles = []
        save_data()
with c2:
    if st.button("🧹 清空航点"):
        st.session_state.waypoints = []
        save_data()
with c3:
    if st.button("🛣️ 自动规划避障航线"):
        if len(st.session_state.waypoints) >= 2:
            start = st.session_state.waypoints[0]
            end = st.session_state.waypoints[-1]
            st.session_state.waypoints = find_safe_route(start, end, st.session_state.obstacles, safe_radius)
            save_data()
        else:
            st.warning("请先添加起点和终点！")
with c4:
    if st.button("🚀 开始飞行"):
        st.session_state.current_wp_idx = 0
        st.session_state.fly_time = 0
        st.session_state.flying = True

st.subheader("📊 飞行实时监控")
idx = st.session_state.current_wp_idx
remain = calc_remain(st.session_state.waypoints, idx)
eta = int(remain/FLY_SPEED) if remain>0 else 0
bat = max(5, 100 - idx*5)

m1,m2,m3,m4,m5,m6 = st.columns(6)
m1.metric("当前航点", f"{idx+1}/{len(st.session_state.waypoints)}")
m2.metric("飞行速度", f"{FLY_SPEED} m/s")
m3.metric("已用时间", str(timedelta(seconds=st.session_state.fly_time)))
m4.metric("剩余距离", f"{remain} m")
m5.metric("预计到达", str(timedelta(seconds=eta)))
m6.metric("剩余电量", f"{bat} %")

# ========================== 地图 ==========================
st.subheader("🗺️ 地图操作：画障碍物 → 加航点 → 自动避障规划航线")
m = folium.Map(location=[NPI_LAT, NPI_LON], zoom_start=17, tiles="Esri WorldImagery")

Draw(export=False,
     draw_options={
         "marker":True,
         "polygon":True,
         "rectangle":True,
         "polyline":False,
         "circle":False
     }).add_to(m)

# 绘制障碍物
for obs in st.session_state.obstacles:
    folium.Polygon(locations=obs, color='red', fill=True, fill_opacity=0.4).add_to(m)

# 绘制航线
if len(st.session_state.waypoints) >= 2:
    folium.PolyLine(
        st.session_state.waypoints, color="blue", weight=5
    ).add_to(m)

# 绘制航点
for i, wp in enumerate(st.session_state.waypoints):
    color = "yellow" if i == idx else "blue"
    folium.CircleMarker(wp, radius=7, color=color, fill=True, popup=f"航点{i+1}").add_to(m)

data = st_folium(m, width=1200, height=600)

# ========================== 【核心修复：追加模式，不覆盖】 ==========================
try:
    if data and "all_drawings" in data and data["all_drawings"]:
        for o in data["all_drawings"]:
            geo = o["geometry"]
            # 航点：追加，不覆盖
            if geo["type"] == "Point":
                lat = round(geo["coordinates"][1], 6)
                lng = round(geo["coordinates"][0], 6)
                point = (lat, lng)
                if point not in st.session_state.waypoints:
                    st.session_state.waypoints.append(point)
                    save_data()
            # 障碍物：追加，不覆盖
            if geo["type"] in ["Polygon", "Rectangle"]:
                pts = [(round(p[1],6), round(p[0],6)) for p in geo["coordinates"][0]]
                if pts not in st.session_state.obstacles and len(pts) > 3:
                    st.session_state.obstacles.append(pts)
                    save_data()
except:
    pass

# ========================== 飞行模拟 ==========================
if st.session_state.flying and idx < len(st.session_state.waypoints)-1:
    st.session_state.current_wp_idx += 1
    st.session_state.fly_time += 1
    time.sleep(0.9)
    st.rerun()

if idx >= len(st.session_state.waypoints)-1 and len(st.session_state.waypoints)>=2:
    st.success("✅ 飞行任务完成！")
    st.session_state.flying = False

st.success(f"✅ 障碍物：{len(st.session_state.obstacles)} 个｜ 航点：{len(st.session_state.waypoints)} 个｜ 安全半径：{safe_radius}米")
