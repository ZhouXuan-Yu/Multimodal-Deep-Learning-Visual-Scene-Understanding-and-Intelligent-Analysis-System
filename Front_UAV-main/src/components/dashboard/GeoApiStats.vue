/**
 * 文件名: GeoApiStats.vue
 * 描述: 地理服务API数据展示组件
 * 作用: 在数据分析大屏中展示地理API服务的使用统计
 */

<template>
  <div class="geo-stats">
    <!-- KPI Row -->
    <div class="kpi-row">
      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #7BA7C2, #5A8BA6);">
          <el-icon><Location /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ geoStats.totalSearches }}</div>
          <div class="kpi-label">累计搜索次数</div>
          <div class="kpi-sub">POI + 路线</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #E8834A, #C4703A);">
          <el-icon><Compass /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ geoStats.poiSearches }}</div>
          <div class="kpi-label">POI搜索次数</div>
          <div class="kpi-sub">兴趣点查询</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #8FB87A, #6B9B5A);">
          <el-icon><MapLocation /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ geoStats.routeSearches }}</div>
          <div class="kpi-label">路线规划次数</div>
          <div class="kpi-sub">智能路径规划</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #D4A843, #B08830);">
          <el-icon><Odometer /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ geoStats.cityCount }}</div>
          <div class="kpi-label">涉及城市数</div>
          <div class="kpi-sub">全国覆盖</div>
        </div>
      </div>
    </div>

    <!-- Charts Grid -->
    <div class="charts-grid">
      <!-- Search Type Distribution -->
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #7BA7C2, #5A8BA6);">
              <el-icon><PieChart /></el-icon>
            </div>
            <div>
              <div class="chart-name">搜索类型分布</div>
              <div class="chart-desc">POI搜索 vs 路线规划占比</div>
            </div>
          </div>
        </div>
        <div id="geo-type-chart" class="chart-canvas"></div>
      </div>

      <!-- City Heatmap -->
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #E8834A, #C4703A);">
              <el-icon><MapLocation /></el-icon>
            </div>
            <div>
              <div class="chart-name">城市热度 TOP10</div>
              <div class="chart-desc">搜索热度最高城市排行</div>
            </div>
          </div>
        </div>
        <div id="geo-city-chart" class="chart-canvas"></div>
      </div>
    </div>

    <!-- Search Records -->
    <div class="records-section premium-glass animate-glass-restore">
      <div class="records-header">
        <div class="records-title">
          <el-icon><Clock /></el-icon>
          <span>地理服务使用记录</span>
        </div>
        <div class="records-actions">
          <button class="premium-btn-glass" @click="goToGeoApi">
            <el-icon><TrendCharts /></el-icon>
            打开地理服务
          </button>
          <span class="records-count">{{ geoRecords.length }} 条记录</span>
        </div>
      </div>
      <div class="records-table">
        <div class="record-row header">
          <span>时间</span><span>类型</span><span>关键词/路线</span><span>城市</span><span>结果数</span>
        </div>
        <div
          class="record-row"
          v-for="(record, idx) in geoRecords.slice(-15).reverse()"
          :key="record.id"
          :style="{ animationDelay: `${idx * 0.03}s` }"
        >
          <span>{{ formatTime(record.timestamp) }}</span>
          <span>
            <span class="type-badge" :class="`type-${record.type}`">
              {{ record.type === 'poi' ? 'POI搜索' : '路线规划' }}
            </span>
          </span>
          <span class="keyword-text">{{ record.keyword }}</span>
          <span>{{ record.city || '—' }}</span>
          <span>{{ record.resultCount }} 条</span>
        </div>
        <div v-if="geoRecords.length === 0" class="records-empty">
          <el-icon><Location /></el-icon>
          <span>暂无地理服务使用记录，请先在地理服务API模块进行搜索</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue';
import * as echarts from 'echarts';
import { useRouter } from 'vue-router';
import { Location, Compass, MapLocation, Odometer, Clock, PieChart, TrendCharts } from '@element-plus/icons-vue';

const router = useRouter();

interface GeoRecord {
  id: string;
  timestamp: number;
  type: 'poi' | 'route';
  keyword: string;
  city: string;
  resultCount: number;
}

const geoRecords = ref<GeoRecord[]>([]);

const geoStats = computed(() => {
  const records = geoRecords.value;
  const poiCount = records.filter(r => r.type === 'poi').length;
  const routeCount = records.filter(r => r.type === 'route').length;
  const cities = new Set(records.map(r => r.city).filter(Boolean));
  return {
    totalSearches: records.length,
    poiSearches: poiCount,
    routeSearches: routeCount,
    cityCount: cities.size,
  };
});

const CITIES_MAP: Record<string, number> = {
  '北京': 42, '上海': 38, '深圳': 31, '广州': 27, '成都': 22,
  '杭州': 19, '武汉': 15, '西安': 14, '重庆': 13, '南京': 12,
};

const formatTime = (ts: number) => {
  const d = new Date(ts);
  return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${d.getMinutes().toString().padStart(2,'0')}`;
};

let typeChart: any = null;
let cityChart: any = null;

const COLORS = { primary: '#E8834A', gold: '#D4A843', blue: '#7BA7C2', green: '#8FB87A', text: '#7A6552' };

const initCharts = () => {
  const tDom = document.getElementById('geo-type-chart');
  const cDom = document.getElementById('geo-city-chart');
  if (tDom) typeChart = echarts.init(tDom);
  if (cDom) cityChart = echarts.init(cDom);
  updateCharts();
};

const updateCharts = () => {
  const { poiSearches, routeSearches } = geoStats.value;

  if (typeChart) {
    const data = [
      { name: 'POI搜索', value: poiSearches, color: COLORS.blue },
      { name: '路线规划', value: routeSearches, color: COLORS.primary },
    ];
    const total = data.reduce((s, d) => s + d.value, 0);
    typeChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)', backgroundColor: 'rgba(255,255,255,0.97)', borderColor: 'rgba(200,160,100,0.25)', borderRadius: 12, padding: [10,14], textStyle: { fontFamily: 'Inter', color: '#3D2E1E' } },
      legend: { orient: 'horizontal', bottom: 0, left: 'center', textStyle: { color: COLORS.text, fontFamily: 'Inter', fontSize: 11 }, icon: 'circle' },
      series: [{
        type: 'pie', radius: ['30%', '62%'], center: ['50%', '45%'],
        itemStyle: { borderColor: 'rgba(255,255,255,0.8)', borderWidth: 2, borderRadius: 6 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold', color: '#3D2E1E', fontFamily: 'Inter' } },
        data: total > 0 ? data : [{ name: '暂无数据', value: 1, color: '#e0e0e0' }],
        animationType: 'expansion', animationDuration: 1200,
      }],
    });
  }

  if (cityChart) {
    const sorted = Object.entries(CITIES_MAP).sort(([,a], [,b]) => b - a).slice(0, 10);
    cityChart.setOption({
      grid: { top: 10, left: 10, right: 10, bottom: 30, containLabel: true },
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.97)', borderColor: 'rgba(200,160,100,0.25)', borderRadius: 12, padding: [10,14], textStyle: { fontFamily: 'Inter', color: '#3D2E1E' } },
      xAxis: { type: 'value', axisLabel: { color: COLORS.text, fontFamily: 'Inter' }, splitLine: { lineStyle: { color: 'rgba(200,160,100,0.08)' } } },
      yAxis: { type: 'category', data: sorted.map(([k]) => k), axisLabel: { color: COLORS.text, fontFamily: 'Inter', fontSize: 11 }, axisLine: { lineStyle: { color: 'rgba(200,160,100,0.20)' } } },
      series: [{
        type: 'bar',
        data: sorted.map(([k, v], i) => ({
          value: v,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: [COLORS.primary, COLORS.gold, COLORS.blue, COLORS.green][i % 4] },
              { offset: 1, color: `${[COLORS.primary, COLORS.gold, COLORS.blue, COLORS.green][i % 4]}60` },
            ]),
            borderRadius: [0, 4, 4, 0],
          },
        })),
        barMaxWidth: 24,
        animationDuration: 1200,
      }],
    });
  }
};

const handleResize = () => { typeChart?.resize(); cityChart?.resize(); };

const goToGeoApi = () => {
  router.push('/data-dashboard-detail');
};

onMounted(() => {
  loadRecords();
  setTimeout(() => { initCharts(); window.addEventListener('resize', handleResize); }, 100);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  typeChart?.dispose();
  cityChart?.dispose();
});

function loadRecords() {
  try {
    const raw = localStorage.getItem('dashboard_geo_records');
    if (raw) geoRecords.value = JSON.parse(raw);
  } catch { geoRecords.value = []; }
}
</script>

<style scoped>
.geo-stats { display: flex; flex-direction: column; gap: 20px; }

.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
.kpi-card { padding: 20px 22px; display: flex; align-items: center; gap: 16px; }
.kpi-icon { width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.kpi-icon .el-icon { font-size: 22px; color: white; }
.kpi-value { font-family: 'Inter','SF Pro Display',system-ui; font-weight: 700; font-size: 1.6rem; color: var(--text-primary); letter-spacing: -0.03em; line-height: 1.1; }
.kpi-label { font-family: 'Inter',system-ui; font-size: 0.75rem; font-weight: 500; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin: 3px 0; }
.kpi-sub { font-family: 'Inter',system-ui; font-size: 0.72rem; color: var(--text-secondary); }

.charts-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }
.chart-card { padding: 20px; display: flex; flex-direction: column; gap: 14px; min-height: 280px; }
.chart-header { display: flex; align-items: center; justify-content: space-between; }
.chart-title { display: flex; align-items: center; gap: 12px; }
.chart-icon { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.chart-icon .el-icon { font-size: 18px; color: white; }
.chart-name { font-family: 'Inter',system-ui; font-weight: 600; font-size: 0.9rem; color: var(--text-primary); }
.chart-desc { font-family: 'Inter',system-ui; font-size: 0.72rem; color: var(--text-tertiary); }
.chart-canvas { flex: 1; min-height: 200px; }

.records-section { padding: 20px 24px; }
.records-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid rgba(200,160,100,0.12); }
.records-title { display: flex; align-items: center; gap: 8px; font-family: 'Inter',system-ui; font-weight: 600; font-size: 0.9rem; color: var(--text-primary); }
.records-count { font-family: 'Inter',system-ui; font-size: 0.8rem; color: var(--text-tertiary); }
.records-actions { display: flex; align-items: center; gap: 10px; }
.records-table { display: flex; flex-direction: column; gap: 2px; }
.record-row { display: grid; grid-template-columns: 2fr 1.5fr 3fr 1.5fr 1fr; gap: 8px; padding: 9px 10px; border-radius: 8px; font-family: 'Inter',system-ui; font-size: 0.8rem; align-items: center; color: var(--text-primary); }
.record-row.header { background: rgba(200,160,100,0.06); color: var(--text-tertiary); font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.record-row:not(.header):hover { background: rgba(255,255,255,0.45); }
.record-row:not(.header) { animation: fadeSlideUp 0.3s ease both; }

.type-badge { padding: 2px 8px; border-radius: 8px; font-size: 0.72rem; font-weight: 600; }
.type-poi { background: rgba(123,167,194,0.12); color: #5A8BA6; }
.type-route { background: rgba(232,131,74,0.12); color: #C4703A; }

.keyword-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-secondary); }

.records-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 32px; color: var(--text-tertiary); font-family: 'Inter',system-ui; font-size: 0.85rem; }

.premium-btn-glass { display: inline-flex; align-items: center; gap: 7px; padding: 7px 14px; background: rgba(255,255,255,0.45); backdrop-filter: blur(12px); border: 1px solid rgba(200,160,100,0.15); border-radius: 12px; font-family: 'Inter',system-ui; font-weight: 500; font-size: 0.82rem; color: var(--text-secondary); cursor: pointer; transition: all 0.3s ease; }
.premium-btn-glass:hover { background: rgba(255,255,255,0.70); color: var(--text-primary); border-color: rgba(200,160,100,0.30); }

@keyframes fadeSlideUp { 0% { opacity: 0; transform: translateY(4px); } 100% { opacity: 1; transform: translateY(0); } }

@media (max-width: 1400px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 1100px) { .charts-grid { grid-template-columns: 1fr; } }
@media (max-width: 768px) { .kpi-row { grid-template-columns: 1fr; } }
</style>
