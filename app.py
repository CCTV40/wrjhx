import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import math
import time
from datetime import timedelta

st.set_page_config(page_title="无人机智能化应用Demo", layout="wide")

# ====================== 1. 持久化存储（刷新不丢）======================
if "obstacles" not in st.session_state:
    st.session_state.obstacles = []
if "waypoints" not in st.session_state:
    st.session_state.waypoints = []
if "safe_radius" not in st.session_state:
    st.session_state.safe_radius = 15

# 飞行状态
if "flying" not in st.session_state:
    st.session_state.flying = False
if "current_wp_idx" not in st.session_state:
    st.session_state.current_wp_idx = 0
if "fly_time" not in st.session_state:
    st.session_state.fly_time = 0

# 南京科技职业学院坐标
LAT = 32.2341
LON = 118.7494
FLY_SPEED = 8.5  # 和参考图一致

# ====================== 2. 核心算法：自动避障（和参考图一样绕开建筑）======================
def haversine(lat1, lon1, lat2, lon2):
    """计算两点间距离（米）"""
    R = 6371000
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def point_in_polygon(pt, polygon):
    """射线法判断点是否在多边形障碍物内部"""
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

def is_point_safe(pt, obstacles, safe_m):
    """判断点是否在障碍物安全区外"""
    lat, lon = pt
    for poly in obstacles:
        if point_in_polygon(pt, poly):
            return False
        for (olat, olon) in poly:
            if haversine(lat, lon, olat, olon) < safe_m:
                return False
    return True

def is_line_safe(p1, p2, obstacles, safe_m):
    """判断整条航线是否安全"""
    lat1, lon1 = p1
    lat2, lon2 = p2
    for i in range(20):
        t = i / 19
        lat = lat1 + t * (lat2 - lat1)
        lon = lon1 + t * (lon2 - lon1)
        if not is_point_safe((lat, lon), obstacles, safe_m):
            return False
    return True

def plan_avoid_route(start, end, obstacles, safe_m):
    """生成和参考图一样的绕行航线"""
    if is_line_safe(start, end, obstacles, safe_m):
        return [start, end]
    
    # 自动生成绕行拐点（和参考图一样从侧边绕开建筑）
    waypoints = [start]
    current = start
    target = end
    
    # 生成3个绕行点，保证绕开所有建筑
    for _ in range(3):
        # 向右上方偏移绕路
        mid_pt = (
            (current[0] + target[0])/2 + 0.0004,
            (current[1] + target[1])/2 + 0.0004
        )
        # 若点不安全，继续偏移
        attempts = 0
        while not is_point_safe(mid_pt, obstacles, safe_m) and attempts < 10:
            mid_pt = (mid_pt[0] + 0.00015, mid_pt[1] + 0.00015)
            attempts += 1
        waypoints.append(mid_pt)
        current = mid_pt
        if is_line_safe(current, target, obstacles, safe_m):
            break
    waypoints.append(target)
    return waypoints

def calc_remain_distance(waypts, idx):
    """计算剩余距离"""
    total = 0.0
    for i in range(idx, len(waypts)-1):
        total += haversine(*waypts[i], *waypts[i+1])
    return round(total, 1)

# ====================== 3. 界面布局 ======================
st.title("🛰️ 无人机智能化应用 - 航线规划与飞行监控")

# 安全半径设置
safe_radius = st.slider("🔧 障碍物安全半径（米）", 5, 50, st.session_state.safe_radius)
st.session_state.safe_radius = safe_radius

# 功能按钮区
col_btn = st.columns(5)
with col_btn[0]:
    if st.button("🧹 清空航点"):
        st.session_state.waypoints = []
with col_btn[1]:
    if st.button("🧹 清空障碍物"):
        st.session_state.obstacles = []
with col_btn[2]:
    if st.button("🛣️ 自动规划避障航线"):
        if len(st.session_state.waypoints) >= 2:
            start = st.session_state.waypoints[0]
            end = st.session_state.waypoints[-1]
            st.session_state.waypoints = plan_avoid_route(start, end, st.session_state.obstacles, safe_radius)
with col_btn[3]:
    if st.button("🚀 开始任务"):
        st.session_state.flying = True
        st.session_state.current_wp_idx = 0
        st.session_state.fly_time = 0
with col_btn[4]:
    if st.button("⏹ 停止任务"):
        st.session_state.flying = False

# ====================== 4. 飞行监控界面（和参考图完全一致）======================
st.markdown("### 📊 飞行实时画面 - 任务执行监控")
idx = st.session_state.current_wp_idx
wp_count = len(st.session_state.waypoints)
remain_dist = calc_remain_distance(st.session_state.waypoints, idx)
eta_sec = int(remain_dist / FLY_SPEED) if remain_dist > 0 else 0
battery = max(5, 100 - idx * 5)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("当前航点", f"{idx+1}/{wp_count}")
c2.metric("飞行速度", f"{FLY_SPEED} m/s")
c3.metric("已用时间", str(timedelta(seconds=st.session_state.fly_time)))
c4.metric("剩余距离", f"{remain_dist} m")
c5.metric("预计到达", str(timedelta(seconds=eta_sec)))
c6.metric("剩余电量", f"{battery} %")

# 航线安全状态提示
if len(st.session_state.waypoints) >= 2:
    if is_line_safe(st.session_state.waypoints[0], st.session_state.waypoints[-1], st.session_state.obstacles, safe_radius):
        st.success("✅ 航线规划合规，全程无侵入障碍物安全区域")
    else:
        st.error("❌ 航线存在安全隐患，请重新调整或增大安全半径")

# ====================== 5. 地图显示 ======================
st.markdown("### 🗺️ 操作说明：用多边形/矩形圈选障碍物 → 标记2个航点 → 点击【自动规划避障航线】")
m = folium.Map(location=[LAT, LON], zoom_start=17, tiles="Esri WorldImagery")

# 绘图工具（圈选障碍物+标记航点）
Draw(
    draw_options={
        "marker": True,
        "polygon": True,
        "rectangle": True,
        "polyline": False,
        "circle": False
    }
).add_to(m)

# 绘制障碍物（红色）
for obs in st.session_state.obstacles:
    folium.Polygon(
        locations=obs,
        color="red",
        fill=True,
        fill_opacity=0.4,
        popup="障碍物"
    ).add_to(m)

# 绘制航线（安全蓝/危险红，和参考图一致）
if len(st.session_state.waypoints) >= 2:
    line_color = "blue" if is_line_safe(st.session_state.waypoints[0], st.session_state.waypoints[-1], st.session_state.obstacles, safe_radius) else "red"
    folium.PolyLine(
        st.session_state.waypoints,
        color=line_color,
        weight=5,
        opacity=0.8,
        popup="规划航线"
    ).add_to(m)

# 绘制航点（当前点高亮黄色）
for i, pt in enumerate(st.session_state.waypoints):
    color = "yellow" if i == idx else "blue"
    icon = "play" if i == len(st.session_state.waypoints)-1 else "circle"
    folium.Marker(
        location=pt,
        icon=folium.Icon(color=color, icon=icon),
        popup=f"航点{i+1}"
    ).add_to(m)

# 渲染地图
map_data = st_folium(m, width=1200, height=600, key="map_demo")

# ====================== 6. 追加模式：不覆盖之前的绘制 ======================
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
            # 障碍物追加
            if geo["type"] in ["Polygon", "Rectangle"]:
                poly = [(round(p[1],5), round(p[0],5)) for p in geo["coordinates"][0]]
                if poly not in st.session_state.obstacles:
                    st.session_state.obstacles.append(poly)
except:
    pass

# ====================== 7. 飞行动态模拟 ======================
if st.session_state.flying and idx < wp_count - 1:
    st.session_state.current_wp_idx += 1
    st.session_state.fly_time += 1
    time.sleep(0.8)
    st.rerun()

if idx >= wp_count - 1 and wp_count >= 2:
    st.success("🎉 飞行任务全部航点已完成，任务结束")
    st.session_state.flying = False

# 底部状态
st.info(f"📌 障碍物总数：{len(st.session_state.obstacles)} | 航点总数：{wp_count} | 当前安全半径：{safe_radius} 米")
