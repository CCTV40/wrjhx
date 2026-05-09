import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import math
import random
import time
from datetime import timedelta

st.set_page_config(page_title="无人机自动避障航线规划", layout="wide")

# -------------------------- 持久化存储 --------------------------
if "waypoints" not in st.session_state:
    st.session_state.waypoints = []
if "obstacles" not in st.session_state:
    st.session_state.obstacles = []
if "flying" not in st.session_state:
    st.session_state.flying = False
if "current_wp_idx" not in st.session_state:
    st.session_state.current_wp_idx = 0
if "fly_time" not in st.session_state:
    st.session_state.fly_time = 0

# -------------------------- 配置参数 --------------------------
NPI_LAT = 32.2341
NPI_LON = 118.7494
FLY_SPEED = 8.0
SAFE_RADIUS = 20  # 障碍物安全距离（米）

# -------------------------- 工具函数 --------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def is_point_safe(lat, lon, obstacles, safe_m):
    """判断一个点是否在障碍物安全区外"""
    for obs in obstacles:
        for (olat, olon) in obs:
            if haversine(lat, lon, olat, olon) < safe_m:
                return False
    return True

def get_safe_route(start, end, obstacles, safe_m):
    """真正的自动避障算法：如果直连不安全，就自动绕路"""
    if is_point_safe(start[0], start[1], obstacles, safe_m) and is_point_safe(end[0], end[1], obstacles, safe_m):
        # 先检查直连是否安全
        clear = True
        for i in range(15):
            t = i / 14
            lat = start[0] + t * (end[0] - start[0])
            lon = start[1] + t * (end[1] - start[1])
            if not is_point_safe(lat, lon, obstacles, safe_m):
                clear = False
                break
        if clear:
            return [start, end]
    
    # 直连不安全，生成绕路航线
    route = [start]
    current = start
    target = end
    attempts = 0
    
    while attempts < 20:
        attempts += 1
        # 尝试向右绕路（可以改成向左，看障碍物位置）
        step_lat = 0.0002 * random.choice([-1, 1])
        step_lon = 0.0002
        
        new_point = (current[0] + step_lat, current[1] + step_lon)
        if is_point_safe(new_point[0], new_point[1], obstacles, safe_m):
            # 检查新点到终点是否安全
            final_clear = True
            for i in range(10):
                t = i / 9
                lat = new_point[0] + t * (target[0] - new_point[0])
                lon = new_point[1] + t * (target[1] - new_point[1])
                if not is_point_safe(lat, lon, obstacles, safe_m):
                    final_clear = False
                    break
            if final_clear:
                route.append(new_point)
                route.append(target)
                break
            else:
                route.append(new_point)
                current = new_point
    return route

def calc_remain(waypts, idx):
    d = 0
    for i in range(idx, len(waypts)-1):
        d += haversine(*waypts[i], *waypts[i+1])
    return round(d,1)

# -------------------------- 界面 --------------------------
st.title("🛰️ 无人机自动避障航线规划｜南京科技职业学院")

col_btn = st.columns(5)
with col_btn[0]:
    if st.button("🧹 清空航点"):
        st.session_state.waypoints = []
with col_btn[1]:
    if st.button("🧹 清空障碍物"):
        st.session_state.obstacles = []
with col_btn[2]:
    if st.button("🛣️ 生成避障航线"):
        if len(st.session_state.waypoints) >= 2:
            start = st.session_state.waypoints[0]
            end = st.session_state.waypoints[-1]
            st.session_state.waypoints = get_safe_route(start, end, st.session_state.obstacles, SAFE_RADIUS)
with col_btn[3]:
    if st.button("🚀 开始飞行"):
        st.session_state.flying = True
        st.session_state.current_wp_idx = 0
        st.session_state.fly_time = 0
with col_btn[4]:
    if st.button("⏹ 停止飞行"):
        st.session_state.flying = False

# -------------------------- 飞行监控面板 --------------------------
st.subheader("📊 飞行实时监控")
idx = st.session_state.current_wp_idx
wp_count = len(st.session_state.waypoints)
remain = calc_remain(st.session_state.waypoints, idx)
eta = int(remain / FLY_SPEED) if remain > 0 else 0
battery = max(5, 100 - idx * 5)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("当前航点", f"{idx+1}/{wp_count}")
c2.metric("飞行速度", f"{FLY_SPEED} m/s")
c3.metric("已用时间", str(timedelta(seconds=st.session_state.fly_time)))
c4.metric("剩余距离", f"{remain} m")
c5.metric("预计到达", str(timedelta(seconds=eta)))
c6.metric("剩余电量", f"{battery} %")

# -------------------------- 地图 --------------------------
st.subheader("🗺️ 操作：画红色障碍物 → 加2个航点 → 点【生成避障航线】")
m = folium.Map(location=[NPI_LAT, NPI_LON], zoom_start=17, tiles="Esri WorldImagery")
Draw(draw_options={"marker": True, "polygon": True, "rectangle": True, "polyline": False, "circle": False}).add_to(m)

# 画障碍物
for obs in st.session_state.obstacles:
    folium.Polygon(obs, color="red", fill=True, fill_opacity=0.4).add_to(m)

# 画航线
if len(st.session_state.waypoints) >= 2:
    # 自动判断是否安全
    route_safe = True
    for i in range(len(st.session_state.waypoints)-1):
        lat1, lon1 = st.session_state.waypoints[i]
        lat2, lon2 = st.session_state.waypoints[i+1]
        for step in range(10):
            t = step/9
            lat = lat1 + t*(lat2-lat1)
            lon = lon1 + t*(lon2-lon1)
            if not is_point_safe(lat, lon, st.session_state.obstacles, SAFE_RADIUS):
                route_safe = False
                break
    line_color = "blue" if route_safe else "red"
    folium.PolyLine(st.session_state.waypoints, color=line_color, weight=5).add_to(m)

# 画航点
for i, p in enumerate(st.session_state.waypoints):
    color = "yellow" if i == idx else "blue"
    folium.CircleMarker(p, radius=7, color=color, fill=True, popup=f"航点{i+1}").add_to(m)

map_data = st_folium(m, width=1200, height=600, key="map")

# -------------------------- 读取地图数据（不覆盖） --------------------------
try:
    if map_data and "all_drawings" in map_data:
        for item in map_data["all_drawings"]:
            geo = item["geometry"]
            if geo["type"] == "Point":
                lat = round(geo["coordinates"][1], 5)
                lng = round(geo["coordinates"][0], 5)
                p = (lat, lng)
                if p not in st.session_state.waypoints:
                    st.session_state.waypoints.append(p)
            if geo["type"] in ["Polygon", "Rectangle"]:
                pts = [(round(p[1],5), round(p[0],5)) for p in geo["coordinates"][0]]
                if pts not in st.session_state.obstacles:
                    st.session_state.obstacles.append(pts)
except:
    pass

# -------------------------- 飞行模拟 --------------------------
if st.session_state.flying and idx < wp_count - 1:
    st.session_state.current_wp_idx += 1
    st.session_state.fly_time += 1
    time.sleep(0.8)
    st.rerun()

st.info(f"📌 障碍物：{len(st.session_state.obstacles)} 个｜航点：{wp_count} 个｜安全半径：{SAFE_RADIUS} 米")
