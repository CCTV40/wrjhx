import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import time
import json
import math

st.set_page_config(page_title="无人机航线规划", layout="wide")

# ====================== 记忆持久化 ======================
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

# 学校固定坐标
NPI_LAT = 32.2341
NPI_LON = 118.7494
FLY_SPEED = 8.0

# ====================== 距离与避障算法 ======================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

def is_point_near_obstacle(lat, lon, obs_list, safe_m):
    for obs in obs_list:
        for (olat, olon) in obs:
            dist = haversine(lat, lon, olat, olon)
            if dist < safe_m:
                return True
    return False

def is_route_safe(waypts, obs_list, safe_m):
    for i in range(len(waypts)-1):
        lat1, lon1 = waypts[i]
        lat2, lon2 = waypts[i+1]
        steps = 10
        for s in range(steps+1):
            t = s / steps
            lat = lat1 + t * (lat2 - lat1)
            lon = lon1 + t * (lon2 - lon1)
            if is_point_near_obstacle(lat, lon, obs_list, safe_m):
                return False
    return True

# ====================== 页面布局 ======================
st.title("📡 无人机智能航线规划｜南京科技职业学院")

# 安全半径滑块（可调节+记忆）
safe_radius = st.slider(
    "🔧 障碍物安全半径（米）",
    min_value=5,
    max_value=50,
    value=st.session_state.safe_radius,
    step=1
)
st.session_state.safe_radius = safe_radius

# 功能按钮
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🧹 清空航点"):
        st.session_state.waypoints = []
        save_data()
with col2:
    if st.button("🧹 清空障碍物"):
        st.session_state.obstacles = []
        save_data()
with col3:
    if st.button("🚀 开始飞行"):
        if len(st.session_state.waypoints) >= 2:
            st.session_state.flying = True
            st.session_state.current_wp_idx = 0
            st.session_state.fly_time = 0
        else:
            st.warning("至少添加2个航点！")
with col4:
    if st.button("⏹ 停止飞行"):
        st.session_state.flying = False

# 飞行监控面板
st.subheader("📊 飞行监控")
c1, c2, c3, c4 = st.columns(4)
c1.metric("当前航点", f"{st.session_state.current_wp_idx+1}/{len(st.session_state.waypoints)}")
c2.metric("飞行速度", f"{FLY_SPEED} m/s")
c3.metric("已用时间", f"{st.session_state.fly_time}s")
battery = max(0, 100 - st.session_state.current_wp_idx * 5)
c4.metric("电量", f"{battery}%")

# 航线安全检测
route_ok = is_route_safe(st.session_state.waypoints, st.session_state.obstacles, safe_radius)
if len(st.session_state.waypoints) >= 2:
    if route_ok:
        st.success("✅ 航线安全，未侵入障碍物安全范围")
    else:
        st.error("❌ 航线侵入障碍物安全区，请调整航点或调大安全半径")
else:
    st.info("ℹ️ 请在地图添加至少2个航点，自动规划航线")

# ====================== 地图绘制 ======================
st.subheader("🗺️ 操作：左侧标记📍加航点 | 多边形画障碍物 | 自动规划航线")
m = folium.Map(
    location=[NPI_LAT, NPI_LON],
    zoom_start=17,
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri WorldImagery"
)

Draw(
    export=False,
    draw_options={
        "marker": True,
        "polygon": True,
        "rectangle": True,
        "polyline": False,
        "circle": False
    }
).add_to(m)

# 绘制障碍物
for obs in st.session_state.obstacles:
    folium.Polygon(
        locations=obs, color="red", fill=True, fill_opacity=0.3
    ).add_to(m)

# 自动规划航线：安全蓝 / 危险红
if len(st.session_state.waypoints) >= 2:
    line_color = "blue" if route_ok else "red"
    folium.PolyLine(
        st.session_state.waypoints,
        color=line_color, weight=5, opacity=0.8
    ).add_to(m)

# 绘制航点
for i, (lat, lon) in enumerate(st.session_state.waypoints):
    folium.CircleMarker(
        location=(lat, lon), radius=6, color="blue", fill=True,
        popup=f"航点{i+1}"
    ).add_to(m)

# 渲染地图
data = st_folium(m, width=1200, height=600, key="map")

# ====================== 解析地图绘制内容 ======================
try:
    if data and data.get("all_drawings"):
        for obj in data["all_drawings"]:
            geo = obj["geometry"]
            # 添加航点
            if geo["type"] == "Point":
                lat = geo["coordinates"][1]
                lon = geo["coordinates"][0]
                pt = [round(lat,6), round(lon,6)]
                if pt not in st.session_state.waypoints:
                    st.session_state.waypoints.append(pt)
                    save_data()
            # 添加障碍物
            if geo["type"] == "Polygon":
                pts = [(round(p[1],6), round(p[0],6)) for p in geo["coordinates"][0]]
                if pts not in st.session_state.obstacles and len(pts) > 3:
                    st.session_state.obstacles.append(pts)
                    save_data()
except:
    pass

# ====================== 飞行模拟逻辑 ======================
if st.session_state.flying and st.session_state.current_wp_idx < len(st.session_state.waypoints)-1:
    st.session_state.current_wp_idx += 1
    st.session_state.fly_time += 1
    time.sleep(0.9)
    st.rerun()

if st.session_state.current_wp_idx >= len(st.session_state.waypoints)-1 and len(st.session_state.waypoints)>=2:
    st.success("✅ 飞行任务完成")
    st.session_state.flying = False

# 底部状态
st.info(f"📌 航点：{len(st.session_state.waypoints)} ｜ 障碍物：{len(st.session_state.obstacles)} ｜ 当前安全半径：{safe_radius} 米")
