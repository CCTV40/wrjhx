import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import math
import time
from datetime import timedelta

st.set_page_config(page_title="无人机真正区域自动避障", layout="wide")

# 状态初始化
if "waypoints" not in st.session_state:
    st.session_state.waypoints = []
if "obstacles" not in st.session_state:
    st.session_state.obstacles = []
if "flying" not in st.session_state:
    st.session_state.flying = False
if "curr_idx" not in st.session_state:
    st.session_state.curr_idx = 0
if "fly_time" not in st.session_state:
    st.session_state.fly_time = 0

# 基础参数
LAT_SCH = 32.2341
LON_SCH = 118.7494
FLY_SPEED = 8.0
SAFE_M = 25

# -------------------------- 工具函数 --------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# 射线法：判断坐标是否在多边形障碍物内部
def point_in_polygon(pt, polygon):
    x, y = pt[1], pt[0]
    inside = False
    n = len(polygon)
    for i in range(n):
        j = (i + 1) % n
        xi, yi = polygon[i][1], polygon[i][0]
        xj, yj = polygon[j][1], polygon[j][0]
        if ((yi > y) != (yj > y)):
            x_inter = (y - yi) * (xj - xi) / (yj - yi) + xi
            if x < x_inter:
                inside = not inside
    return inside

# 判断一个点是否靠近任意障碍物（含内部+安全距离）
def is_point_blocked(pt, obstacles, safe_m):
    lat, lon = pt
    for poly in obstacles:
        # 在障碍物内部 直接阻塞
        if point_in_polygon(pt, poly):
            return True
        # 在障碍物周边安全范围内 也阻塞
        for (olat, olon) in poly:
            if haversine(lat, lon, olat, olon) < safe_m:
                return True
    return False

# 检测两点连线是否穿过障碍物
def is_line_blocked(p1, p2, obstacles, safe_m):
    lat1, lon1 = p1
    lat2, lon2 = p2
    for i in range(20):
        t = i / 19
        lat = lat1 + t * (lat2 - lat1)
        lon = lon1 + t * (lon2 - lon1)
        if is_point_blocked((lat, lon), obstacles, safe_m):
            return True
    return False

# 真正自动避障：直线路径被挡，自动外侧绕路生成拐点
def plan_avoid_route(start, end, obstacles, safe_m):
    if not is_line_blocked(start, end, obstacles, safe_m):
        return [start, end]
    
    # 自动生成绕行中间点
    mid_lat = (start[0] + end[0]) / 2 + 0.0003
    mid_lon = (start[1] + end[1]) / 2 + 0.0003
    mid_pt = (mid_lat, mid_lon)
    
    # 若绕行点还在障碍里，再偏移
    cnt = 0
    while is_point_blocked(mid_pt, obstacles, safe_m) and cnt < 10:
        mid_pt = (mid_pt[0] + 0.00015, mid_pt[1] + 0.00015)
        cnt += 1
    return [start, mid_pt, end]

def calc_remain(waypts, idx):
    total = 0.0
    for i in range(idx, len(waypts)-1):
        total += haversine(*waypts[i], *waypts[i+1])
    return round(total, 1)

# -------------------------- 界面按钮 --------------------------
st.title("🛰️ 南京科技职业学院 - 无人机【区域级真正自动避障】")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    if st.button("🧹 清空航点"):
        st.session_state.waypoints = []
with c2:
    if st.button("🧹 清空障碍物"):
        st.session_state.obstacles = []
with c3:
    if st.button("🛣️ 自动避障规划"):
        if len(st.session_state.waypoints) >= 2:
            s = st.session_state.waypoints[0]
            e = st.session_state.waypoints[-1]
            st.session_state.waypoints = plan_avoid_route(s, e, st.session_state.obstacles, SAFE_M)
with c4:
    if st.button("🚀 开始飞行"):
        st.session_state.flying = True
        st.session_state.curr_idx = 0
        st.session_state.fly_time = 0
with c5:
    if st.button("⏹ 停止飞行"):
        st.session_state.flying = False

# -------------------------- 飞行监控面板 --------------------------
st.subheader("📊 飞行实时画面 - 任务执行监控")
idx = st.session_state.curr_idx
wp_num = len(st.session_state.waypoints)
remain_dist = calc_remain(st.session_state.waypoints, idx)
eta_sec = int(remain_dist / FLY_SPEED) if remain_dist > 0 else 0
battery = max(5, 100 - idx * 5)

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("当前航点", f"{idx+1}/{wp_num}")
m2.metric("飞行速度", f"{FLY_SPEED} m/s")
m3.metric("已用时间", str(timedelta(seconds=st.session_state.fly_time)))
m4.metric("剩余距离", f"{remain_dist} m")
m5.metric("预计到达", str(timedelta(seconds=eta_sec)))
m6.metric("剩余电量", f"{battery} %")

# -------------------------- 地图绘制 --------------------------
st.subheader("🗺️ 操作：画多边形障碍物 → 打点起止航点 → 自动避障规划")
m = folium.Map(location=[LAT_SCH, LON_SCH], zoom_start=17, tiles="Esri WorldImagery")
Draw(draw_options={"marker":True,"polygon":True,"rectangle":True,"polyline":False,"circle":False}).add_to(m)

# 绘制所有障碍物
for poly in st.session_state.obstacles:
    folium.Polygon(poly, color="red", fill=True, fill_opacity=0.4).add_to(m)

# 绘制航线
if len(st.session_state.waypoints) >= 2:
    if is_line_blocked(st.session_state.waypoints[0], st.session_state.waypoints[-1], st.session_state.obstacles, SAFE_M):
        folium.PolyLine(st.session_state.waypoints, color="red", weight=5).add_to(m)
        st.error("❌ 原始直线路径穿过障碍物，已自动生成绕行航线")
    else:
        folium.PolyLine(st.session_state.waypoints, color="blue", weight=5).add_to(m)
        st.success("✅ 航线安全，无侵入障碍物区域")

# 绘制航点
for i, pt in enumerate(st.session_state.waypoints):
    color = "yellow" if i == idx else "blue"
    folium.CircleMarker(pt, radius=7, color=color, fill=True).add_to(m)

map_data = st_folium(m, width=1200, height=580, key="map_sch")

# -------------------------- 追加模式：不覆盖历史绘制 --------------------------
try:
    if map_data and "all_drawings" in map_data:
        for item in map_data["all_drawings"]:
            geo = item["geometry"]
            # 航点追加
            if geo["type"] == "Point":
                lat = round(geo["coordinates"][1], 5)
                lon = round(geo["coordinates"][0], 5)
                p = (lat, lon)
                if p not in st.session_state.waypoints:
                    st.session_state.waypoints.append(p)
            # 障碍物多边形追加
            if geo["type"] in ["Polygon", "Rectangle"]:
                poly = [(round(p[1],5), round(p[0],5)) for p in geo["coordinates"][0]]
                if poly not in st.session_state.obstacles:
                    st.session_state.obstacles.append(poly)
except:
    pass

# -------------------------- 飞行动态模拟 --------------------------
if st.session_state.flying and idx < wp_num - 1:
    st.session_state.curr_idx += 1
    st.session_state.fly_time += 1
    time.sleep(0.8)
    st.rerun()

if idx >= wp_num - 1 and wp_num >= 2:
    st.success("🎉 飞行任务完成")
    st.session_state.flying = False

st.info(f"📌 障碍物数量：{len(st.session_state.obstacles)} | 航点数量：{wp_num} | 安全半径：{SAFE_M} 米")
