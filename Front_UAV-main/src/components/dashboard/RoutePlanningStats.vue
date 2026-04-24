<template>
  <div class="route-stats">
    <!-- KPI Row -->
    <div class="kpi-row">
      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #E8834A, #C4703A);">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ routeStats.total }}</div>
          <div class="kpi-label">总路线数</div>
          <div class="kpi-sub">历史累计</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #8FB87A, #6B9B5A);">
          <el-icon><MapLocation /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ routeStats.totalDistance }} km</div>
          <div class="kpi-label">总行驶里程</div>
          <div class="kpi-sub">全部路线</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #7BA7C2, #5A8BA6);">
          <el-icon><Clock /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ formatDuration(routeStats.totalDuration) }}</div>
          <div class="kpi-label">总行驶时长</div>
          <div class="kpi-sub">全部路线</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #D4A843, #B08830);">
          <el-icon><Money /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ totalToll }} 元</div>
          <div class="kpi-label">预估总费用</div>
          <div class="kpi-sub">含高速费</div>
        </div>
      </div>
    </div>

    <!-- Charts Grid -->
    <div class="charts-grid">
      <!-- Strategy Pie -->
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #E8834A, #C4703A);">
              <el-icon><DataAnalysis /></el-icon>
            </div>
            <div>
              <div class="chart-name">路线策略分布</div>
              <div class="chart-desc">按策略类型分组统计</div>
            </div>
          </div>
        </div>
        <div id="strategy-chart" class="chart-canvas"></div>
      </div>

      <!-- City Bar -->
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #7BA7C2, #5A8BA6);">
              <el-icon><MapLocation /></el-icon>
            </div>
            <div>
              <div class="chart-name">城市热度 TOP10</div>
              <div class="chart-desc">途经城市出现频次</div>
            </div>
          </div>
        </div>
        <div id="city-chart" class="chart-canvas"></div>
      </div>
    </div>

    <!-- Route Records -->
    <div class="records-section premium-glass animate-glass-restore">
      <div class="records-header">
        <div class="records-title">
          <el-icon><Clock /></el-icon>
          <span>路线规划历史</span>
        </div>
        <span class="records-count">{{ routeRecords.length }} 条记录</span>
      </div>
      <div class="records-table">
        <div class="record-row header">
          <span>时间</span><span>起点</span><span>终点</span><span>途经城市</span><span>策略</span><span>距离</span><span>耗时</span><span>详情</span>
        </div>
        <template
          v-for="(record, idx) in routeRecords.slice(-15).reverse()"
          :key="record.id"
        >
          <div
            class="record-row"
            :class="{ expanded: expandedId === record.id }"
            :style="{ animationDelay: `${idx * 0.03}s` }"
            @click="toggleExpand(record.id)"
          >
            <span>{{ formatDate(record.timestamp) }}</span>
            <span class="city-tag">{{ record.startPoint }}</span>
            <span class="city-tag">{{ record.endPoint }}</span>
            <span class="cities-text">{{ record.cities }}</span>
            <span>
              <span class="strategy-badge" :class="`strategy-${record.strategy}`">
                {{ strategyLabels[record.strategy] }}
              </span>
            </span>
            <span>{{ record.distance }} km</span>
            <span>{{ formatDuration(record.duration) }}</span>
            <span class="expand-toggle">
              <el-icon><component :is="expandedId === record.id ? 'CaretTop' : 'CaretBottom'" /></el-icon>
              {{ expandedId === record.id ? '收起' : '查看' }}
            </span>
          </div>

          <!-- Expanded Detail -->
          <div v-if="expandedId === record.id" class="detail-row">
            <div class="detail-grid">
              <div class="detail-item">
                <div class="detail-label">起点</div>
                <div class="detail-value">{{ record.startPoint }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">终点</div>
                <div class="detail-value">{{ record.endPoint }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">途经城市</div>
                <div class="detail-value">{{ record.cities }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">规划策略</div>
                <div class="detail-value">{{ strategyLabels[record.strategy] }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">总距离</div>
                <div class="detail-value">{{ record.distance }} km</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">总耗时</div>
                <div class="detail-value">{{ formatDuration(record.duration) }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">预估费用</div>
                <div class="detail-value">{{ record.toll }} 元</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">限行路段</div>
                <div class="detail-value">{{ record.hasRestriction ? '有' : '无' }}</div>
              </div>
            </div>
          </div>
        </template>
        <div v-if="routeRecords.length === 0" class="records-empty">
          <el-icon><TrendCharts /></el-icon>
          <span>暂无路线规划记录，请先在智程导航模块进行路径规划</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, watch, ref } from 'vue';
import * as echarts from 'echarts';
import { TrendCharts, MapLocation, Clock, Money, DataAnalysis, CaretTop, CaretBottom } from '@element-plus/icons-vue';
import { useDashboardStore } from '@/stores/dashboardStore';

const store = useDashboardStore();
const routeStats = computed(() => store.routeStats);
const routeRecords = computed(() => store.routeRecords);
const expandedId = ref<string | null>(null);

const toggleExpand = (id: string) => {
  expandedId.value = expandedId.value === id ? null : id;
};

const strategyLabels: Record<string, string> = {
  fastest: '最快路线', economic: '最经济路线', shortest: '最短距离',
};

const STRATEGY_COLORS: Record<string, string> = {
  fastest: '#E8834A', economic: '#8FB87A', shortest: '#7BA7C2',
};

const formatDate = (ts: number) => {
  const d = new Date(ts);
  return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${d.getMinutes().toString().padStart(2,'0')}`;
};

const formatDuration = (mins: number) => {
  if (!mins) return '—';
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h > 0 ? `${h}h${m}m` : `${m}min`;
};

const totalToll = computed(() => {
  return routeRecords.value.reduce((s, r) => s + (r.toll || 0), 0);
});

let strategyChart: any = null;
let cityChart: any = null;

const COLORS = { text: '#7A6552', grid: 'rgba(200,160,100,0.12)' };

const initCharts = () => {
  const sDom = document.getElementById('strategy-chart');
  const cDom = document.getElementById('city-chart');
  if (sDom) strategyChart = echarts.init(sDom);
  if (cDom) cityChart = echarts.init(cDom);
  updateCharts();
};

const updateCharts = () => {
  const { strategyDist, cityFrequency } = routeStats.value;

  if (strategyChart) {
    const pieData = Object.entries(strategyDist)
      .filter(([, v]) => v > 0)
      .map(([name, value]) => ({
        name,
        value,
        itemStyle: { color: STRATEGY_COLORS[Object.keys(strategyLabels).find(k => strategyLabels[k] === name) || ''] || '#E8834A' }
      }));
    strategyChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)', backgroundColor: 'rgba(255,255,255,0.97)', borderColor: 'rgba(200,160,100,0.25)', borderRadius: 12, padding: [10,14], textStyle: { fontFamily: 'Inter', color: '#3D2E1E' } },
      legend: { orient: 'horizontal', bottom: 0, left: 'center', textStyle: { color: COLORS.text, fontFamily: 'Inter', fontSize: 11 }, icon: 'circle' },
      series: [{
        type: 'pie', radius: ['30%', '62%'], center: ['50%', '45%'],
        itemStyle: { borderColor: 'rgba(255,255,255,0.8)', borderWidth: 2, borderRadius: 6 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold', color: '#3D2E1E', fontFamily: 'Inter' } },
        data: pieData.length > 0 ? pieData : [{ name: '暂无数据', value: 1 }],
        animationType: 'expansion', animationDuration: 1200,
      }],
    });
  }

  if (cityChart) {
    const sorted = Object.entries(cityFrequency).sort(([,a], [,b]) => b - a).slice(0, 10);
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
              { offset: 0, color: ['#E8834A','#8FB87A','#7BA7C2','#D4A843'][i % 4] },
              { offset: 1, color: `${['#E8834A','#8FB87A','#7BA7C2','#D4A843'][i % 4]}60` }
            ]),
            borderRadius: [0, 4, 4, 0]
          }
        })),
        barMaxWidth: 28,
        animationDuration: 1200,
      }],
    });
  }
};

const handleResize = () => { strategyChart?.resize(); cityChart?.resize(); };
watch(() => routeStats.value, updateCharts, { deep: true });
onMounted(() => { setTimeout(() => { initCharts(); window.addEventListener('resize', handleResize); }, 100); });
onBeforeUnmount(() => { window.removeEventListener('resize', handleResize); strategyChart?.dispose(); cityChart?.dispose(); });
</script>

<style scoped>
.route-stats { display: flex; flex-direction: column; gap: 20px; }

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
.chart-canvas { flex: 1; min-height: 200px; }

/* Records */
.records-section { padding: 20px 24px; }
.records-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid rgba(200,160,100,0.12); }
.records-title { display: flex; align-items: center; gap: 8px; font-family: 'Inter',system-ui; font-weight: 600; font-size: 0.9rem; color: var(--text-primary); }
.records-count { font-family: 'Inter',system-ui; font-size: 0.8rem; color: var(--text-tertiary); }
.records-table { display: flex; flex-direction: column; gap: 2px; overflow-x: auto; }
.record-row { display: grid; grid-template-columns: 2fr 1.5fr 1.5fr 2.5fr 1.5fr 1fr 1fr 1.5fr; gap: 8px; padding: 9px 10px; border-radius: 8px; font-family: 'Inter',system-ui; font-size: 0.8rem; align-items: center; color: var(--text-primary); white-space: nowrap; }
.record-row.header { background: rgba(200,160,100,0.06); color: var(--text-tertiary); font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.record-row:not(.header):hover { background: rgba(255,255,255,0.45); }
.record-row:not(.header) { animation: fadeSlideUp 0.3s ease both; }
.record-row.expanded { background: rgba(232,131,74,0.06); }
.expand-toggle { display: inline-flex; align-items: center; gap: 4px; color: var(--accent-primary); font-size: 0.75rem; font-weight: 500; cursor: pointer; }

.detail-row { padding: 16px 20px; background: rgba(253,251,247,0.8); border-bottom: 1px solid rgba(200,160,100,0.12); animation: fadeSlideUp 0.25s ease both; }
.detail-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.detail-item { display: flex; flex-direction: column; gap: 3px; }
.detail-label { font-family: 'Inter',system-ui; font-size: 0.68rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; }
.detail-value { font-family: 'Inter',system-ui; font-size: 0.8rem; color: var(--text-primary); }

.city-tag { color: var(--accent-primary); font-weight: 600; }
.cities-text { color: var(--text-secondary); font-size: 0.75rem; overflow: hidden; text-overflow: ellipsis; }
.strategy-badge { padding: 2px 8px; border-radius: 8px; font-size: 0.72rem; font-weight: 600; }
.strategy-fastest { background: rgba(232,131,74,0.12); color: #C4703A; }
.strategy-economic { background: rgba(143,184,122,0.12); color: #6B9B5A; }
.strategy-shortest { background: rgba(123,167,194,0.12); color: #5A8BA6; }

.records-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 32px; color: var(--text-tertiary); font-family: 'Inter',system-ui; font-size: 0.85rem; }

@keyframes fadeSlideUp { 0% { opacity: 0; transform: translateY(4px); } 100% { opacity: 1; transform: translateY(0); } }

@media (max-width: 1400px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 1100px) { .charts-grid { grid-template-columns: 1fr; } }
@media (max-width: 768px) { .kpi-row { grid-template-columns: 1fr; } .record-row { grid-template-columns: 1fr 1fr 1fr; } }
</style>
