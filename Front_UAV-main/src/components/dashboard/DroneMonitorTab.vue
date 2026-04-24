<template>
  <div class="drone-monitor">
    <!-- KPI Row -->
    <div class="kpi-row">
      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #7BA7C2, #5A8BA6);">
          <el-icon><Compass /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ onlineDrones }}/{{ store.droneList.length }}</div>
          <div class="kpi-label">在线无人机</div>
          <div class="kpi-sub">{{ warningDrones }} 架告警中</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #8FB87A, #6B9B5A);">
          <el-icon><Odometer /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ avgBattery }}%</div>
          <div class="kpi-label">平均电量</div>
          <div class="kpi-sub">{{ lowBatteryCount }} 架需充电</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #E8834A, #C4703A);">
          <el-icon><Connection /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ avgSignal }}%</div>
          <div class="kpi-label">平均信号强度</div>
          <div class="kpi-sub">最低 {{ minSignal }}%</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #D4A843, #B08830);">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ avgSpeed }} m/s</div>
          <div class="kpi-label">平均飞行速度</div>
          <div class="kpi-sub">最高 {{ maxSpeed }} m/s</div>
        </div>
      </div>
    </div>

    <!-- Charts Grid -->
    <div class="charts-grid">
      <!-- Battery Trend -->
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #8FB87A, #6B9B5A);">
              <el-icon><Odometer /></el-icon>
            </div>
            <div>
              <div class="chart-name">电量趋势</div>
              <div class="chart-desc">全机队平均电量 · 最近60分钟</div>
            </div>
          </div>
          <div class="chart-badge">实时</div>
        </div>
        <div id="drone-battery-chart" class="chart-canvas"></div>
      </div>

      <!-- Signal Strength -->
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #7BA7C2, #5A8BA6);">
              <el-icon><Connection /></el-icon>
            </div>
            <div>
              <div class="chart-name">信号强度</div>
              <div class="chart-desc">全机队平均信号 · 最近60分钟</div>
            </div>
          </div>
        </div>
        <div id="drone-signal-chart" class="chart-canvas"></div>
      </div>

      <!-- Temperature Panel -->
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #E8906A, #C4703A);">
              <el-icon><Sunny /></el-icon>
            </div>
            <div>
              <div class="chart-name">温度监控</div>
              <div class="chart-desc">电池 / 电机 / CPU 温度</div>
            </div>
          </div>
        </div>
        <div class="temp-grid">
          <div class="temp-item" v-for="drone in store.droneList.slice(0, 5)" :key="drone.id">
            <div class="temp-name">{{ drone.name }}</div>
            <div class="temp-bars">
              <div class="temp-bar-wrap">
                <span class="temp-label">电池</span>
                <div class="temp-bar-bg">
                  <div class="temp-bar-fill" :style="{ width: `${getTemp(drone, 'battery')}%`, background: getTempColor(getTemp(drone, 'battery')) }"></div>
                </div>
                <span class="temp-val">{{ getTemp(drone, 'battery') }}°C</span>
              </div>
              <div class="temp-bar-wrap">
                <span class="temp-label">电机</span>
                <div class="temp-bar-bg">
                  <div class="temp-bar-fill" :style="{ width: `${getTemp(drone, 'motors')}%`, background: getTempColor(getTemp(drone, 'motors')) }"></div>
                </div>
                <span class="temp-val">{{ getTemp(drone, 'motors') }}°C</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Drone List -->
      <div class="chart-card premium-glass animate-glass-restore drone-list-card">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #E8834A, #C4703A);">
              <el-icon><Compass /></el-icon>
            </div>
            <div>
              <div class="chart-name">无人机列表</div>
              <div class="chart-desc">{{ store.droneList.length }} 架无人机</div>
            </div>
          </div>
        </div>
        <div class="drone-table">
          <div class="drone-row header-row">
            <span>名称</span><span>状态</span><span>电量</span><span>信号</span><span>速度</span><span>高度</span>
          </div>
          <div
            class="drone-row"
            v-for="drone in store.droneList"
            :key="drone.id"
            :class="`status-${drone.status}`"
          >
            <span>{{ drone.name }}</span>
            <span>
              <span class="status-badge" :class="`badge-${drone.status}`">
                {{ statusLabels[drone.status] }}
              </span>
            </span>
            <span>
              <div class="mini-bar-wrap">
                <div class="mini-bar-bg">
                  <div class="mini-bar-fill" :style="{ width: `${drone.batteryLevel}%`, background: drone.batteryLevel < 20 ? '#C45040' : drone.batteryLevel < 50 ? '#E8B060' : '#8FB87A' }"></div>
                </div>
                <span>{{ drone.batteryLevel.toFixed(0) }}%</span>
              </div>
            </span>
            <span>
              <div class="mini-bar-wrap">
                <div class="mini-bar-bg">
                  <div class="mini-bar-fill" :style="{ width: `${drone.signalStrength}%`, background: drone.signalStrength < 50 ? '#C45040' : '#7BA7C2' }"></div>
                </div>
                <span>{{ drone.signalStrength.toFixed(0) }}%</span>
              </div>
            </span>
            <span>{{ drone.speed.toFixed(1) }} m/s</span>
            <span>{{ drone.altitude.toFixed(0) }} m</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import * as echarts from 'echarts';
import { Compass, Odometer, Connection, TrendCharts, Sunny } from '@element-plus/icons-vue';
import { useDashboardStore } from '@/stores/dashboardStore';
import DroneService from '@/services/DroneService';

const store = useDashboardStore();

let batteryChart: any = null;
let signalChart: any = null;
let updateTimer: number | null = null;

const statusLabels: Record<string, string> = {
  mission: '巡航中', idle: '待命', returning: '返航中',
  warning: '告警', offline: '离线',
};

const onlineDrones = computed(() => store.droneList.filter(d => d.status !== 'offline').length);
const warningDrones = computed(() => store.droneList.filter(d => d.status === 'warning' || d.batteryLevel < 20).length);
const avgBattery = computed(() => {
  if (!store.droneList.length) return '0.0';
  return (store.droneList.reduce((s, d) => s + d.batteryLevel, 0) / store.droneList.length).toFixed(1);
});
const avgSignal = computed(() => {
  if (!store.droneList.length) return '0.0';
  return (store.droneList.reduce((s, d) => s + d.signalStrength, 0) / store.droneList.length).toFixed(1);
});
const minSignal = computed(() => {
  if (!store.droneList.length) return '0';
  return Math.min(...store.droneList.map(d => d.signalStrength)).toFixed(0);
});
const avgSpeed = computed(() => {
  const flying = store.droneList.filter(d => d.status === 'mission' || d.status === 'returning');
  if (!flying.length) return '0.0';
  return (flying.reduce((s, d) => s + d.speed, 0) / flying.length).toFixed(1);
});
const maxSpeed = computed(() => {
  const flying = store.droneList.filter(d => d.status === 'mission' || d.status === 'returning');
  if (!flying.length) return '0.0';
  return Math.max(...flying.map(d => d.speed)).toFixed(1);
});
const lowBatteryCount = computed(() => store.droneList.filter(d => d.batteryLevel < 20).length);

const getTemp = (drone: any, key: 'battery' | 'motors') => {
  const t = DroneService.getTelemetry(drone.id);
  if (!t) return 25;
  return Math.round(t.temperature[key]);
};

const getTempColor = (temp: number) => {
  if (temp > 55) return '#C45040';
  if (temp > 45) return '#E8B060';
  return '#8FB87A';
};

const COLORS = { green: '#8FB87A', blue: '#7BA7C2', amber: '#E8B060', coral: '#E8906A', text: '#7A6552' };

const makeTooltip = (formatter: string) => ({
  trigger: 'axis' as const,
  backgroundColor: 'rgba(255,255,255,0.97)',
  borderColor: 'rgba(200,160,100,0.25)', borderWidth: 1, borderRadius: 12, padding: [10, 14],
  textStyle: { fontFamily: 'Inter,system-ui', color: '#3D2E1E', fontSize: 12 },
  axisPointer: { type: 'line' as const, lineStyle: { color: 'rgba(232,131,74,0.35)', width: 2 } },
  formatter,
});

const initCharts = () => {
  const batteryDom = document.getElementById('drone-battery-chart');
  const signalDom = document.getElementById('drone-signal-chart');
  if (!batteryDom || !signalDom) return;

  batteryChart = echarts.init(batteryDom);
  signalChart = echarts.init(signalDom);
  updateCharts();
};

const buildTimeline = (minutes: number) => {
  const now = Date.now();
  return Array.from({ length: minutes }, (_, i) => {
    const t = new Date(now - (minutes - 1 - i) * 60 * 1000);
    return `${t.getHours()}:${t.getMinutes().toString().padStart(2, '0')}`;
  });
};

const updateCharts = () => {
  const snapshots = store.getRecentDroneSnapshots(60);
  const timeline = buildTimeline(Math.max(12, snapshots.length));
  const batteryData = snapshots.length > 0
    ? snapshots.map(s => s.battery)
    : Array(timeline.length).fill(parseFloat(avgBattery.value));
  const signalData = snapshots.length > 0
    ? snapshots.map(s => s.signal)
    : Array(timeline.length).fill(parseFloat(avgSignal.value));

  if (batteryChart) {
    batteryChart.setOption({
      grid: { top: 20, left: 12, right: 16, bottom: 12, containLabel: true },
      tooltip: makeTooltip('{b}<br/>{a}: {c}%'),
      xAxis: { type: 'category', data: timeline, axisLabel: { color: COLORS.text, fontSize: 11, fontFamily: 'Inter' }, axisLine: { lineStyle: { color: 'rgba(200,160,100,0.20)' } }, splitLine: { show: false } },
      yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%', color: COLORS.text, fontFamily: 'Inter' }, splitLine: { lineStyle: { color: 'rgba(200,160,100,0.08)', type: 'dashed' as const } } },
      series: [{
        name: '平均电量', type: 'line', data: batteryData, smooth: 0.4,
        symbol: 'circle', symbolSize: 5, showSymbol: false,
        lineStyle: { width: 3, color: COLORS.green },
        itemStyle: { color: COLORS.green, borderColor: 'white', borderWidth: 2 },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: `${COLORS.green}40` }, { offset: 1, color: `${COLORS.green}00` }]) },
        animationDuration: 1200,
      }],
    });
  }

  if (signalChart) {
    signalChart.setOption({
      grid: { top: 20, left: 12, right: 16, bottom: 12, containLabel: true },
      tooltip: makeTooltip('{b}<br/>{a}: {c}%'),
      xAxis: { type: 'category', data: timeline, axisLabel: { color: COLORS.text, fontSize: 11, fontFamily: 'Inter' }, axisLine: { lineStyle: { color: 'rgba(200,160,100,0.20)' } }, splitLine: { show: false } },
      yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%', color: COLORS.text, fontFamily: 'Inter' }, splitLine: { lineStyle: { color: 'rgba(200,160,100,0.08)', type: 'dashed' as const } } },
      series: [{
        name: '信号强度', type: 'line', data: signalData, smooth: 0.4,
        symbol: 'circle', symbolSize: 5, showSymbol: false,
        lineStyle: { width: 3, color: COLORS.blue },
        itemStyle: { color: COLORS.blue, borderColor: 'white', borderWidth: 2 },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: `${COLORS.blue}40` }, { offset: 1, color: `${COLORS.blue}00` }]) },
        animationDuration: 1200,
      }],
    });
  }
};

const handleResize = () => {
  batteryChart?.resize();
  signalChart?.resize();
};

onMounted(() => {
  setTimeout(() => {
    initCharts();
    updateTimer = window.setInterval(() => {
      store.refreshDroneList();
      updateCharts();
    }, 5000);
    window.addEventListener('resize', handleResize);
  }, 100);
});

onBeforeUnmount(() => {
  if (updateTimer) clearInterval(updateTimer);
  window.removeEventListener('resize', handleResize);
  batteryChart?.dispose();
  signalChart?.dispose();
});
</script>

<style scoped>
.drone-monitor { display: flex; flex-direction: column; gap: 20px; }

/* KPI */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
.kpi-card { padding: 20px 22px; display: flex; align-items: center; gap: 16px; }
.kpi-icon { width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.kpi-icon .el-icon { font-size: 22px; color: white; }
.kpi-value { font-family: 'Inter','SF Pro Display',system-ui; font-weight: 700; font-size: 1.6rem; color: var(--text-primary); letter-spacing: -0.03em; line-height: 1.1; }
.kpi-label { font-family: 'Inter',system-ui; font-size: 0.75rem; font-weight: 500; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin: 3px 0; }
.kpi-sub { font-family: 'Inter',system-ui; font-size: 0.72rem; color: var(--text-secondary); }

/* Charts */
.charts-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }
.chart-card { padding: 20px; display: flex; flex-direction: column; gap: 14px; min-height: 280px; }
.chart-header { display: flex; align-items: center; justify-content: space-between; }
.chart-title { display: flex; align-items: center; gap: 12px; }
.chart-icon { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.chart-icon .el-icon { font-size: 18px; color: white; }
.chart-name { font-family: 'Inter',system-ui; font-weight: 600; font-size: 0.9rem; color: var(--text-primary); }
.chart-desc { font-family: 'Inter',system-ui; font-size: 0.72rem; color: var(--text-tertiary); }
.chart-badge { padding: 3px 10px; background: rgba(139,184,122,0.15); color: #6B9B5A; border: 1px solid rgba(139,184,122,0.25); border-radius: 8px; font-family: 'Inter',system-ui; font-size: 0.72rem; font-weight: 600; }
.chart-canvas { flex: 1; min-height: 200px; }

/* Temperature */
.temp-grid { display: flex; flex-direction: column; gap: 10px; flex: 1; }
.temp-item { display: flex; align-items: center; gap: 12px; }
.temp-name { font-family: 'Inter',system-ui; font-size: 0.8rem; color: var(--text-secondary); width: 70px; flex-shrink: 0; }
.temp-bars { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.temp-bar-wrap { display: flex; align-items: center; gap: 6px; }
.temp-label { font-family: 'Inter',system-ui; font-size: 0.68rem; color: var(--text-tertiary); width: 26px; flex-shrink: 0; }
.temp-bar-bg { flex: 1; height: 6px; background: rgba(200,160,100,0.12); border-radius: 3px; overflow: hidden; }
.temp-bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s ease; }
.temp-val { font-family: 'Inter',system-ui; font-size: 0.68rem; color: var(--text-secondary); width: 32px; text-align: right; }

/* Drone List */
.drone-list-card { min-height: 320px; }
.drone-table { display: flex; flex-direction: column; gap: 4px; flex: 1; overflow: auto; }
.drone-row { display: grid; grid-template-columns: 1.5fr 1fr 1.5fr 1.5fr 1fr 1fr; gap: 8px; padding: 8px 10px; border-radius: 8px; font-family: 'Inter',system-ui; font-size: 0.8rem; align-items: center; transition: background 0.2s; }
.drone-row.header-row { background: rgba(200,160,100,0.06); color: var(--text-tertiary); font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.drone-row:not(.header-row):hover { background: rgba(255,255,255,0.45); }
.drone-row:not(.header-row) { color: var(--text-primary); }

.status-badge { padding: 2px 8px; border-radius: 8px; font-size: 0.72rem; font-weight: 600; }
.badge-mission { background: rgba(143,184,122,0.15); color: #6B9B5A; }
.badge-idle { background: rgba(123,167,194,0.15); color: #5A8BA6; }
.badge-returning { background: rgba(232,176,96,0.15); color: #C48A30; }
.badge-warning { background: rgba(196,80,64,0.15); color: #C45040; }
.badge-offline { background: rgba(168,148,128,0.15); color: var(--text-tertiary); }

.mini-bar-wrap { display: flex; align-items: center; gap: 5px; }
.mini-bar-bg { width: 50px; height: 5px; background: rgba(200,160,100,0.12); border-radius: 3px; overflow: hidden; }
.mini-bar-fill { height: 100%; border-radius: 3px; }

@media (max-width: 1400px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 1100px) { .charts-grid { grid-template-columns: 1fr; } }
@media (max-width: 768px) { .kpi-row { grid-template-columns: 1fr; } }
</style>
