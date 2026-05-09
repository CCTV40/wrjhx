import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import time

st.set_page_config(page_title="无人机航线规划", layout="wide")

# ========== 初始化状态 ==========
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
# 圈选矩形
if "select_rect" not in st.session_state:
    st.session_state.select_rect = None
# 选中的障碍物下标
if "selected_obs_idx" not in st.session_state:
    st.session_state.selected_obs_idx = []

# ========== 学校坐标 ==========
NPI_LAT = 32.2341
NPI_LON = 118.7494
FLY_SPEED = 8.0

# ========== 界面按钮 ==========
st.title("📡 无人机航线规划 - 南京科技职业学院（支持圈选障碍物）")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.info("左侧工具栏：画多边形/矩形 = 障碍物")
with col2:
    if st.button("🧹 清空航点"):
        st.session_state.waypoints = []
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
with col5:
    if st.button("❌ 删除圈选中的障碍物"):
        # 反向删除，避免下标错乱
        for idx in sorted(st.session_state.selected_obs_idx, reverse=True):
            if 0 <= idx < len(st.session_state.obstacles):
                del st.session_state.obstacles[idx]
        st.session_state.selected_obs_idx = []

# ========== 飞行监控面板 ==========
st.subheader("📊 飞行监控")
m1, m2, m3, m4 = st.columns(4)
m1.metric("当前航点", f"{st.session_state.current_wp_idx+1}/{len(st.session_state.waypoints)}")
m2.metric("速度", f"{FLY_SPEED} m/s")
m3.metric("已用时间", f"{st.session_state.fly_time}s")
battery = max(0, 100 - st.session_state.current_wp_idx * 6)
m4.metric("电量", f"{battery}%")

# ========== 创建地图 ==========
st.subheader("🗺️ 卫星地图 - 可圈选障碍物")
m = folium.Map(
    location=[NPI_LAT, NPI_LON],
    zoom_start=17,
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles &copy; Esri"
)

# 绘图工具：开启矩形用于圈选
draw = Draw(
    draw_options={
        "polygon": True,
        "rectangle": True,
        "polyline": False,
        "circle": False,
        "marker": True,
        "circlemarker": False
    },
    edit_options={"edit": True, "remove": True}
)
draw.add_to(m)

# ========== 绘制所有障碍物（选中变红，未选中浅红） ==========
for idx, obs in enumerate(st.session_state.obstacles):
    color = "#ff0000" if idx in st.session_state.selected_obs_idx else "#ff6666"
    fill_op = 0.4 if idx in st.session_state.selected_obs_idx else 0.2
    folium.Polygon(obs, color=color, fill=True, fill_opacity=fill_op).add_to(m)

# ========== 绘制航点+航线 ==========
if len(st.session_state.waypoints) >= 2:
    folium.PolyLine(st.session_state.waypoints, color="blue", weight=5, opacity=0.8).add_to(m)
for i, wp in enumerate(st.session_state.waypoints):
    folium.CircleMarker(wp, radius=6, color="blue", fill=True, popup=f"航点{i+1}").add_to(m)

# ========== 显示地图并处理圈选逻辑 ==========
map_data = st_folium(m, width=1200, height=600)

# 解析绘制的图形
if map_data and "all_drawings" in map_data and map_data["all_drawings"] is not None:
    drawings = map_data["all_drawings"]
    for item in drawings:
        geo_type = item["geometry"]["type"]
        coords = item["geometry"]["coordinates"][0]

        # 普通障碍物多边形保存
        if geo_type in ["Polygon"] and len(coords) > 3:
            latlngs = [(c[1], c[0]) for c in coords]
            if latlngs not in st.session_state.obstacles:
                st.session_state.obstacles.append(latlngs)

        # 矩形 = 圈选框
        if geo_type == "Rectangle":
            # 取圈选框范围
            lons = [p[0] for p in coords]
            lats = [p[1] for p in coords]
            min_lon, max_lon = min(lons), max(lons)
            min_lat, max_lat = min(lats), max(lats)

            # 匹配范围内的障碍物
            selected = []
            for idx, obs in enumerate(st.session_state.obstacles):
                # 取障碍物中心点
                obs_lats = [p[0] for p in obs]
                obs_lons = [p[1] for p in obs]
                cen_lat = sum(obs_lats)/len(obs_lats)
                cen_lon = sum(obs_lons)/len(obs_lons)
                # 判断是否在圈选矩形内
                if min_lat <= cen_lat <= max_lat and min_lon <= cen_lon <= max_lon:
                    selected.append(idx)
            st.session_state.selected_obs_idx = selected

# ========== 飞行模拟 ==========
if st.session_state.flying and st.session_state.current_wp_idx < len(st.session_state.waypoints)-1:
    st.session_state.current_wp_idx += 1
    st.session_state.fly_time += 1
    time.sleep(0.8)
    st.rerun()

if st.session_state.current_wp_idx >= len(st.session_state.waypoints)-1 and len(st.session_state.waypoints) >= 2:
    st.success("✅ 飞行任务完成！")
    st.session_state.flying = False

# 状态提示
st.success(f"✅ 障碍物总数：{len(st.session_state.obstacles)} | 已圈选选中：{len(st.session_state.selected_obs_idx)} 个 | 航点：{len(st.session_state.waypoints)}")
