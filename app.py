import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import time
import json
import math
from datetime import timedelta

st.set_page_config(page_title="无人机航线规划-飞行监控", layout="wide")

# ====================== 记忆功能 ======================
if "waypoints" not in st.session_state:
    st.session_state.waypoints = json.loads(st.session_state.get("saved_waypoints", "[]"))
if "obstacles" not in st.session_state:
    st.session_state.obstacles = json.loads(st.session_state.get("saved_obstacles", "[]"))
if "safe_radius" not in st.session_state:
    st.session_state.safe_radius = 15

def save_data():
    st.session_state["saved_waypoints"] = json.dumps(st.session_state.waypoints)
    st.session_state["saved_obstacles"] = json.dumps(st.session_state.obstacles)

# 飞行状态
if "flying" not in st.session_state:
    st.session_state.flying = False
if "current_wp_idx" not in st.session_state:
    st.session_state.current_wp_idx = 0
if "fly_time" not in st.session_state:
    st.session_state.fly_time = 0

# 南京科技职业学院
NPI_LAT = 32.2341
NPI_LON = 118.7494
FLY_SPEED = 8.0

# ====================== 核心算法：距离 & 避障 ======================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def point_in_polygon(lat, lon, polygon):
    x = lon
    y = lat
    inside = False
    for i in range(len(polygon)):
        j = (i + 1) % len(polygon)
        xi, yi = polygon[i][1], polygon[i][0]
        xj, yj = polygon[j][1], polygon[j][0]
        if ((yi > y) != (yj > y)):
            x_intersect = (y - yi) * (xj - xi) / (yj - yi) + xi
            if x < x_intersect:
                inside = not inside
    return inside

def is_route_unsafe(waypts, obstacles, safe_m):
    for i in range(len(waypts)-1):
        lat1, lon1 = waypts[i]
        lat2, lon2 = waypts[i+1]
        steps = 20
        for s in range(steps+1):
            t = s/steps
            lat = lat1 + t*(lat2-lat1)
            lon = lon1 + t*(lon2-lon1)
            
            for obs in obstacles:
                if point_in_polygon(lat, lon, obs):
                    return True
                for (olat, olon) in obs:
                    d = haversine(lat, lon, olat, olon)
                    if d < safe_m:
                        return True
    return False

def calc_remain(waypts, idx):
    total = 0
    for i in range(idx, len(waypts)-1):
        total += haversine(waypts[i][0], waypts[i][1], waypts[i+1][0], waypts[i+1][1])
    return round(total,1)

# ====================== 界面 ======================
st.title("🛰️ 无人机航线规划与实时飞行监控｜南京科技职业学院")

safe_radius = st.slider("🔧 安全半径（米）",5,50,st.session_state.safe_radius)
st.session_state.safe_radius = safe_radius

c1,c2,c3,c4 = st.columns(4)
with c1:
    if st.button("🧹 清空航点"):
        st.session_state.waypoints=[]
        save_data()
with c2:
    if st.button("🧹 清空障碍物"):
        st.session_state.obstacles=[]
        save_data()
with c3:
    if st.button("🚀 开始飞行"):
        if len(st.session_state.waypoints)>=2:
            st.session_state.flying=True
            st.session_state.current_wp_idx=0
            st.session_state.fly_time=0
with c4:
    if st.button("⏹ 停止飞行"):
        st.session_state.flying=False

# ====================== 飞行监控面板 ======================
st.subheader("📊 飞行实时画面 - 任务执行监控")
idx = st.session_state.current_wp_idx
remain_d = calc_remain(st.session_state.waypoints, idx)
eta = int(remain_d/FLY_SPEED) if FLY_SPEED>0 else 0
bat = max(5, 100 - idx*6)

m1,m2,m3,m4,m5,m6 = st.columns(6)
m1.metric("当前航点",f"{idx+1}/{len(st.session_state.waypoints)}")
m2.metric("飞行速度",f"{FLY_SPEED} m/s")
m3.metric("已用时间",str(timedelta(seconds=st.session_state.fly_time)))
m4.metric("剩余距离",f"{remain_d} m")
m5.metric("预计到达",str(timedelta(seconds=eta)))
m6.metric("剩余电量",f"{bat} %")

# 安全检测
danger = is_route_unsafe(st.session_state.waypoints, st.session_state.obstacles, safe_radius)
if len(st.session_state.waypoints)>=2:
    if danger:
        st.error("❌ 警告：航线穿过障碍物或安全区！")
    else:
        st.success("✅ 航线安全，可正常飞行")
else:
    st.info("📍 左侧点标记工具添加航点")

# ====================== 地图 ======================
st.subheader("🗺️ 地图：画障碍物 → 规划航线 → 自动避障")
m = folium.Map(location=[NPI_LAT,NPI_LON],zoom_start=17,tiles="Esri WorldImagery")

Draw(export=False,
     draw_options={"marker":True,"polygon":True,"rectangle":True,"polyline":False,"circle":False}
).add_to(m)

# 画障碍物
for obs in st.session_state.obstacles:
    folium.Polygon(locations=obs, color='red', fill=True, fill_opacity=0.4).add_to(m)

# 画航线
if len(st.session_state.waypoints)>=2:
    col = "red" if danger else "blue"
    folium.PolyLine(st.session_state.waypoints, color=col, weight=5).add_to(m)

# 画航点（当前飞行点黄色高亮）
for i,wp in enumerate(st.session_state.waypoints):
    color = "yellow" if i==idx else "blue"
    folium.CircleMarker(wp, radius=7, color=color, fill=True, popup=f"航点{i+1}").add_to(m)

data = st_folium(m, width=1200, height=600)

# ====================== 【修复】正确读取障碍物 ======================
try:
    if data and "all_drawings" in data and data["all_drawings"]:
        temp_obs = []
        temp_wp = []
        for o in data["all_drawings"]:
            geo = o["geometry"]
            if geo["type"] == "Point":
                lat = geo["coordinates"][1]
                lng = geo["coordinates"][0]
                temp_wp.append( (lat,lng) )
            if geo["type"] in ["Polygon","Rectangle"]:
                pts = [ (p[1],p[0]) for p in geo["coordinates"][0] ]
                temp_obs.append(pts)
        
        st.session_state.waypoints = temp_wp
        st.session_state.obstacles = temp_obs
        save_data()
except:
    pass

# ====================== 飞行模拟 ======================
if st.session_state.flying and idx < len(st.session_state.waypoints)-1:
    st.session_state.current_wp_idx +=1
    st.session_state.fly_time +=1
    time.sleep(0.9)
    st.rerun()

if idx >= len(st.session_state.waypoints)-1 and len(st.session_state.waypoints)>=2:
    st.success("🎉 飞行任务完成！")
    st.session_state.flying = False

st.info(f"✅ 障碍物：{len(st.session_state.obstacles)} 个 ｜ 航点：{len(st.session_state.waypoints)} 个")
