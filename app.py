import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import time
import json
import math
from datetime import timedelta

st.set_page_config(page_title="无人机航线规划-飞行监控", layout="wide")

# ====================== 持久化记忆 ======================
if "waypoints" not in st.session_state:
    st.session_state.waypoints = json.loads(st.session_state.get("saved_waypoints", "[]"))
if "obstacles" not in st.session_state:
    st.session_state.obstacles = json.loads(st.session_state.get("saved_obstacles", "[]"))
if "safe_radius" not in st.session_state:
    st.session_state.safe_radius = 15

def save_data():
    st.session_state["saved_waypoints"] = json.dumps(st.session_state.waypoints)
    st.session_state["saved_obstacles"] = json.dumps(st.session_state.obstacles)

# 飞行全局状态
if "flying" not in st.session_state:
    st.session_state.flying = False
if "current_wp_idx" not in st.session_state:
    st.session_state.current_wp_idx = 0
if "fly_time" not in st.session_state:
    st.session_state.fly_time = 0

# 基础配置
NPI_LAT = 32.2341
NPI_LON = 118.7494
FLY_SPEED = 8.0

# ====================== 距离计算 / 避障检测 ======================
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
            lat = lat1 + t*(lat2-lat1)
            lon = lon1 + t*(lon2-lon1)
            if is_point_near_obstacle(lat, lon, obs_list, safe_m):
                return False
    return True

# 计算整条航线剩余总距离
def calc_remain_distance(waypts, now_idx):
    total = 0.0
    for i in range(now_idx, len(waypts)-1):
        lat1, lon1 = waypts[i]
        lat2, lon2 = waypts[i+1]
        total += haversine(lat1, lon1, lat2, lon2)
    return round(total, 1)

# ====================== 页面标题与参数调节 ======================
st.title("🛰️ 无人机航线规划与飞行任务实时监控｜南京科技职业学院")
safe_radius = st.slider("🔧 障碍物安全半径（米）", 5, 50, st.session_state.safe_radius, 1)
st.session_state.safe_radius = safe_radius

# 功能按钮区
col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
with col_btn1:
    if st.button("🧹 清空航点"):
        st.session_state.waypoints = []
        save_data()
with col_btn2:
    if st.button("🧹 清空障碍物"):
        st.session_state.obstacles = []
        save_data()
with col_btn3:
    if st.button("🚀 开始任务飞行"):
        if len(st.session_state.waypoints) >= 2:
            st.session_state.flying = True
            st.session_state.current_wp_idx = 0
            st.session_state.fly_time = 0
        else:
            st.warning("⚠️ 请至少添加2个航点进行航线规划")
with col_btn4:
    if st.button("⏹ 终止飞行任务"):
        st.session_state.flying = False

# ====================== 专业飞行任务监控界面 ======================
st.markdown("## 📊 飞行实时画面 - 任务执行监控")
c1, c2, c3, c4, c5, c6 = st.columns(6)

# 计算监控指标
now_idx = st.session_state.current_wp_idx
remain_dist = calc_remain_distance(st.session_state.waypoints, now_idx)
eta_sec = int(remain_dist / FLY_SPEED) if FLY_SPEED>0 else 0
battery = max(5, round(100 - now_idx * 6))

with c1:
    st.metric("当前航点", f"{now_idx+1}/{len(st.session_state.waypoints)}")
with c2:
    st.metric("飞行速度", f"{FLY_SPEED} m/s")
with c3:
    st.metric("已用时间", str(timedelta(seconds=st.session_state.fly_time)))
with c4:
    st.metric("剩余距离", f"{remain_dist} m")
with c5:
    st.metric("预计到达", str(timedelta(seconds=eta_sec)))
with c6:
    st.metric("剩余电量", f"{battery} %")

# 航线安全状态提示
route_ok = is_route_safe(st.session_state.waypoints, st.session_state.obstacles, safe_radius)
if len(st.session_state.waypoints) >= 2:
    if route_ok:
        st.success("✅ 航线规划合规 | 无侵入障碍物安全区域，可正常执行飞行任务")
    else:
        st.error("❌ 航线侵入障碍物安全区，请调整航点或增大安全半径")
else:
    st.info("ℹ️ 在地图左侧选择标记工具，点击添加航点，自动生成规划航线")

# ====================== 卫星地图 + 航线绘制 ======================
st.markdown("## 🗺️ 航线规划飞行地图（南京科技职业学院）")
m = folium.Map(
    location=[NPI_LAT, NPI_LON],
    zoom_start=17,
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri WorldImagery"
)

# 绘图工具
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
    folium.Polygon(locations=obs, color="red", fill=True, fill_opacity=0.3).add_to(m)

# 规划航线：安全蓝 / 危险红
if len(st.session_state.waypoints) >= 2:
    line_color = "blue" if route_ok else "red"
    folium.PolyLine(st.session_state.waypoints, color=line_color, weight=5, opacity=0.8).add_to(m)

# 绘制航点
for i, (lat, lon) in enumerate(st.session_state.waypoints):
    # 当前飞行航点高亮黄色
    color = "#ffcc00" if i == now_idx else "blue"
    folium.CircleMarker(
        location=(lat, lon), radius=7, color=color, fill=True,
        popup=f"航点{i+1}"
    ).add_to(m)

# 渲染地图
data = st_folium(m, width=1200, height=600, key="map")

# ====================== 解析地图绘制：航点/障碍物保存 ======================
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

# ====================== 飞行实时动态巡航 ======================
if st.session_state.flying and now_idx < len(st.session_state.waypoints)-1:
    st.session_state.current_wp_idx += 1
    st.session_state.fly_time += 1
    time.sleep(0.85)
    st.rerun()

if now_idx >= len(st.session_state.waypoints)-1 and len(st.session_state.waypoints)>=2:
    st.success("🎉 飞行任务全部航点已完成，任务结束")
    st.session_state.flying = False

# 底部状态信息
st.info(f"📌 航点总数：{len(st.session_state.waypoints)} ｜ 障碍物总数：{len(st.session_state.obstacles)} ｜ 当前安全半径：{safe_radius} 米")
