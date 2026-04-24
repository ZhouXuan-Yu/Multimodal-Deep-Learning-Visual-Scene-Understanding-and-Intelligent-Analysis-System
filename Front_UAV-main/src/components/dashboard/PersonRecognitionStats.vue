<template>
  <div class="person-stats">
    <!-- KPI Row -->
    <div class="kpi-row">
      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #8FB87A, #6B9B5A);">
          <el-icon><User /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ personStats.total }}</div>
          <div class="kpi-label">累计识别人次</div>
          <div class="kpi-sub">最近7天</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #7BA7C2, #5A8BA6);">
          <el-icon><Odometer /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ (personStats.avgConfidence * 100).toFixed(1) }}%</div>
          <div class="kpi-label">平均置信度</div>
          <div class="kpi-sub">总体识别质量</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #E8834A, #C4703A);">
          <el-icon><Clock /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ personStats.avgProcessingTime }}s</div>
          <div class="kpi-label">平均处理耗时</div>
          <div class="kpi-sub">单次识别</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #D4A843, #B08830);">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ personRecords.length }}</div>
          <div class="kpi-label">识别记录数</div>
          <div class="kpi-sub">本地存储</div>
        </div>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="charts-grid">
      <!-- Gender Pie -->
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #E8834A, #C4703A);">
              <el-icon><User /></el-icon>
            </div>
            <div>
              <div class="chart-name">性别分布</div>
              <div class="chart-desc">识别人员性别统计</div>
            </div>
          </div>
        </div>
        <div id="gender-chart" class="chart-canvas"></div>
      </div>

      <!-- Color Bar -->
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #8FB87A, #6B9B5A);">
              <el-icon><Brush /></el-icon>
            </div>
            <div>
              <div class="chart-name">上装颜色分布</div>
              <div class="chart-desc">识别人员服装颜色TOP</div>
            </div>
          </div>
        </div>
        <div id="color-chart" class="chart-canvas"></div>
      </div>

      <!-- Age Bar -->
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #7BA7C2, #5A8BA6);">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <div>
              <div class="chart-name">年龄分布</div>
              <div class="chart-desc">识别人员年龄段统计</div>
            </div>
          </div>
        </div>
        <div id="age-chart" class="chart-canvas"></div>
      </div>

      <!-- Trend -->
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #D4A843, #B08830);">
              <el-icon><DataAnalysis /></el-icon>
            </div>
            <div>
              <div class="chart-name">日识别趋势</div>
              <div class="chart-desc">最近7天每日识别量</div>
            </div>
          </div>
        </div>
        <div id="trend-chart" class="chart-canvas"></div>
      </div>
    </div>

    <!-- Recent Records -->
    <div class="records-section premium-glass animate-glass-restore">
      <div class="records-header">
        <div class="records-title">
          <el-icon><Clock /></el-icon>
          <span>最近识别记录</span>
        </div>
        <span class="records-count">{{ personRecords.length }} 条记录</span>
      </div>
      <div class="records-table">
        <div class="record-row header">
          <span>时间</span><span>性别</span><span>年龄段</span><span>上装颜色</span><span>下装颜色</span><span>置信度</span><span>处理耗时</span><span>详情</span>
        </div>
        <template
          v-for="(record, idx) in personRecords.slice(-15).reverse()"
          :key="record.id"
        >
          <div
            class="record-row"
            :class="{ expanded: expandedId === record.id }"
            :style="{ animationDelay: `${idx * 0.03}s` }"
            @click="toggleExpand(record.id)"
          >
            <span>{{ formatTime(record.timestamp) }}</span>
            <span>
              <span class="gender-tag" :class="record.gender === '男' ? 'tag-male' : record.gender === '女' ? 'tag-female' : 'tag-unknown'">
                {{ record.gender }}
              </span>
            </span>
            <span>{{ record.age }}</span>
            <span><span class="color-dot" :style="{ background: colorNameToHex(record.upperColor) }"></span>{{ record.upperColor }}</span>
            <span><span class="color-dot" :style="{ background: colorNameToHex(record.lowerColor) }"></span>{{ record.lowerColor }}</span>
            <span>
              <span class="conf-badge" :class="record.confidence >= 0.85 ? 'conf-high' : record.confidence >= 0.7 ? 'conf-mid' : 'conf-low'">
                {{ (record.confidence * 100).toFixed(0) }}%
              </span>
            </span>
            <span>{{ record.processingTime }}s</span>
            <span class="expand-toggle">
              <el-icon><component :is="expandedId === record.id ? 'CaretTop' : 'CaretBottom'" /></el-icon>
              {{ expandedId === record.id ? '收起' : '查看' }}
            </span>
          </div>

          <!-- Expanded Detail -->
          <div v-if="expandedId === record.id" class="detail-row">
            <div class="detail-grid">
              <div class="detail-item">
                <div class="detail-label">性别</div>
                <div class="detail-value">{{ record.gender }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">年龄段</div>
                <div class="detail-value">{{ record.age }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">上装颜色</div>
                <div class="detail-value">
                  <span class="color-dot-lg" :style="{ background: colorNameToHex(record.upperColor) }"></span>
                  {{ record.upperColor }}
                </div>
              </div>
              <div class="detail-item">
                <div class="detail-label">下装颜色</div>
                <div class="detail-value">
                  <span class="color-dot-lg" :style="{ background: colorNameToHex(record.lowerColor) }"></span>
                  {{ record.lowerColor }}
                </div>
              </div>
              <div class="detail-item">
                <div class="detail-label">置信度</div>
                <div class="detail-value">{{ (record.confidence * 100).toFixed(1) }}%</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">处理耗时</div>
                <div class="detail-value">{{ record.processingTime }}s</div>
              </div>
            </div>
            <div v-if="record.imageUrl" class="detail-image">
              <div class="detail-label">识别图片</div>
              <img :src="record.imageUrl" class="recog-img" alt="识别图片" />
            </div>
          </div>
        </template>
        <div v-if="personRecords.length === 0" class="records-empty">
          <el-icon><User /></el-icon>
          <span>暂无识别记录，请先在智眸千析模块进行人物识别</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, watch, ref } from 'vue';
import * as echarts from 'echarts';
import { User, Odometer, Clock, TrendCharts, DataAnalysis, Brush, CaretTop, CaretBottom } from '@element-plus/icons-vue';
import { useDashboardStore } from '@/stores/dashboardStore';

const store = useDashboardStore();
const personStats = computed(() => store.personStats);
const personRecords = computed(() => store.personRecords);
const expandedId = ref<string | null>(null);

const toggleExpand = (id: string) => {
  expandedId.value = expandedId.value === id ? null : id;
};

let genderChart: any = null;
let colorChart: any = null;
let ageChart: any = null;
let trendChart: any = null;

const COLORS = { primary: '#E8834A', gold: '#D4A843', coral: '#E8906A', blue: '#7BA7C2', green: '#8FB87A', purple: '#B094BE', text: '#7A6552' };

const COLOR_MAP: Record<string, string> = {
  '黑色': '#1a1a1a', '白色': '#f0f0f0', '蓝色': '#3b82f6', '红色': '#ef4444',
  '灰色': '#9ca3af', '绿色': '#22c55e', '黄色': '#eab308', '紫色': '#a855f7',
  '棕色': '#92400e', '粉色': '#ec4899', '未知': '#d1d5db',
};

const colorNameToHex = (name: string) => COLOR_MAP[name] || '#9ca3af';

const formatTime = (ts: number) => {
  const d = new Date(ts);
  return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${d.getMinutes().toString().padStart(2,'0')}`;
};

const initCharts = () => {
  const gDom = document.getElementById('gender-chart');
  const cDom = document.getElementById('color-chart');
  const aDom = document.getElementById('age-chart');
  const tDom = document.getElementById('trend-chart');
  if (gDom) genderChart = echarts.init(gDom);
  if (cDom) colorChart = echarts.init(cDom);
  if (aDom) ageChart = echarts.init(aDom);
  if (tDom) trendChart = echarts.init(tDom);
  updateCharts();
};

const updateCharts = () => {
  const { genderDist, ageDist, colorDist } = personStats.value;
  const total = personStats.value.total || 1;

  // Gender Pie
  if (genderChart) {
    const pieData = Object.entries(genderDist).map(([name, value]) => ({ name, value }));
    genderChart.setOption({
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

  // Color Bar
  if (colorChart) {
    const sortedColors = Object.entries(colorDist).sort(([,a], [,b]) => b - a).slice(0, 8);
    colorChart.setOption({
      grid: { top: 10, left: 10, right: 10, bottom: 30, containLabel: true },
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.97)', borderColor: 'rgba(200,160,100,0.25)', borderRadius: 12, padding: [10,14], textStyle: { fontFamily: 'Inter', color: '#3D2E1E' } },
      xAxis: { type: 'value', axisLabel: { color: COLORS.text, fontFamily: 'Inter' }, splitLine: { lineStyle: { color: 'rgba(200,160,100,0.08)' } } },
      yAxis: { type: 'category', data: sortedColors.map(([k]) => k), axisLabel: { color: COLORS.text, fontFamily: 'Inter', fontSize: 11 }, axisLine: { lineStyle: { color: 'rgba(200,160,100,0.20)' } } },
      series: [{
        type: 'bar',
        data: sortedColors.map(([k, v]) => ({ value: v, itemStyle: { color: colorNameToHex(k), borderRadius: [0, 4, 4, 0] } })),
        barMaxWidth: 24,
        animationDuration: 1200,
      }],
    });
  }

  // Age Bar
  if (ageChart) {
    const ageOrder = ['3-12', '13-17', '18-25', '26-35', '36-45', '46-55', '56-65', '65+'];
    const ageData = ageOrder.map(k => ({ name: k, value: ageDist[k] || 0 }));
    ageChart.setOption({
      grid: { top: 10, left: 10, right: 10, bottom: 10, containLabel: true },
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.97)', borderColor: 'rgba(200,160,100,0.25)', borderRadius: 12, padding: [10,14], textStyle: { fontFamily: 'Inter', color: '#3D2E1E' } },
      xAxis: { type: 'category', data: ageOrder, axisLabel: { color: COLORS.text, fontFamily: 'Inter', fontSize: 10 }, axisLine: { lineStyle: { color: 'rgba(200,160,100,0.20)' } } },
      yAxis: { type: 'value', axisLabel: { color: COLORS.text, fontFamily: 'Inter' }, splitLine: { lineStyle: { color: 'rgba(200,160,100,0.08)' } } },
      series: [{
        type: 'bar',
        data: ageData.map(d => ({ value: d.value, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: COLORS.blue }, { offset: 1, color: `${COLORS.blue}60` }]), borderRadius: [4, 4, 0, 0] } })),
        barMaxWidth: 40,
        animationDuration: 1200,
      }],
    });
  }

  // Trend (last 7 days)
  if (trendChart) {
    const dayCount: Record<string, number> = {};
    const now = Date.now();
    for (let d = 6; d >= 0; d--) {
      const day = new Date(now - d * 86400000);
      dayCount[`${day.getMonth()+1}/${day.getDate()}`] = 0;
    }
    personRecords.value.forEach(r => {
      const d = new Date(r.timestamp);
      const key = `${d.getMonth()+1}/${d.getDate()}`;
      if (key in dayCount) dayCount[key]++;
    });
    const days = Object.keys(dayCount);
    const counts = Object.values(dayCount);
    trendChart.setOption({
      grid: { top: 10, left: 10, right: 10, bottom: 10, containLabel: true },
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.97)', borderColor: 'rgba(200,160,100,0.25)', borderRadius: 12, padding: [10,14], textStyle: { fontFamily: 'Inter', color: '#3D2E1E' } },
      xAxis: { type: 'category', data: days, axisLabel: { color: COLORS.text, fontFamily: 'Inter', fontSize: 10 }, axisLine: { lineStyle: { color: 'rgba(200,160,100,0.20)' } } },
      yAxis: { type: 'value', axisLabel: { color: COLORS.text, fontFamily: 'Inter' }, splitLine: { lineStyle: { color: 'rgba(200,160,100,0.08)' } } },
      series: [{
        type: 'line', data: counts, smooth: 0.4,
        lineStyle: { width: 3, color: COLORS.gold },
        itemStyle: { color: COLORS.gold, borderColor: 'white', borderWidth: 2 },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: `${COLORS.gold}40` }, { offset: 1, color: `${COLORS.gold}00` }]) },
        animationDuration: 1200,
      }],
    });
  }
};

const handleResize = () => {
  [genderChart, colorChart, ageChart, trendChart].forEach(c => c?.resize());
};

watch(() => personStats.value, updateCharts, { deep: true });

onMounted(() => { setTimeout(() => { initCharts(); window.addEventListener('resize', handleResize); }, 100); });
onBeforeUnmount(() => { window.removeEventListener('resize', handleResize); [genderChart, colorChart, ageChart, trendChart].forEach(c => c?.dispose()); });
</script>

<style scoped>
.person-stats { display: flex; flex-direction: column; gap: 20px; }

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
.records-table { display: flex; flex-direction: column; gap: 2px; }
.record-row { display: grid; grid-template-columns: 2fr 1fr 1fr 1.5fr 1.5fr 1.5fr 1.5fr 1.5fr; gap: 8px; padding: 9px 10px; border-radius: 8px; font-family: 'Inter',system-ui; font-size: 0.8rem; align-items: center; color: var(--text-primary); }
.record-row.header { background: rgba(200,160,100,0.06); color: var(--text-tertiary); font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.record-row:not(.header):hover { background: rgba(255,255,255,0.45); }
.record-row:not(.header) { animation: fadeSlideUp 0.3s ease both; }
.record-row.expanded { background: rgba(232,131,74,0.06); }
.expand-toggle { display: inline-flex; align-items: center; gap: 4px; color: var(--accent-primary); font-size: 0.75rem; font-weight: 500; cursor: pointer; }

.detail-row { padding: 16px 20px; background: rgba(253,251,247,0.8); border-bottom: 1px solid rgba(200,160,100,0.12); animation: fadeSlideUp 0.25s ease both; }
.detail-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-bottom: 12px; }
.detail-item { display: flex; flex-direction: column; gap: 3px; }
.detail-label { font-family: 'Inter',system-ui; font-size: 0.68rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; }
.detail-value { font-family: 'Inter',system-ui; font-size: 0.8rem; color: var(--text-primary); display: flex; align-items: center; gap: 5px; }
.color-dot-lg { display: inline-block; width: 12px; height: 12px; border-radius: 50%; border: 1px solid rgba(0,0,0,0.1); }
.detail-image { margin-top: 8px; }
.detail-image .detail-label { margin-bottom: 6px; }
.recog-img { max-width: 200px; max-height: 150px; border-radius: 8px; object-fit: cover; border: 1px solid rgba(200,160,100,0.2); }

.gender-tag { padding: 2px 8px; border-radius: 8px; font-size: 0.72rem; font-weight: 600; }
.tag-male { background: rgba(59,130,246,0.12); color: #3b82f6; }
.tag-female { background: rgba(236,72,153,0.12); color: #ec4899; }
.tag-unknown { background: rgba(156,163,175,0.12); color: #9ca3af; }

.color-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }

.conf-badge { padding: 2px 8px; border-radius: 8px; font-size: 0.72rem; font-weight: 600; }
.conf-high { background: rgba(139,184,122,0.12); color: #6B9B5A; }
.conf-mid { background: rgba(232,176,96,0.12); color: #C48A30; }
.conf-low { background: rgba(196,80,64,0.12); color: #C45040; }

.records-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 32px; color: var(--text-tertiary); font-family: 'Inter',system-ui; font-size: 0.85rem; }

@keyframes fadeSlideUp { 0% { opacity: 0; transform: translateY(4px); } 100% { opacity: 1; transform: translateY(0); } }

@media (max-width: 1400px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 1100px) { .charts-grid { grid-template-columns: 1fr; } .record-row { grid-template-columns: 2fr 1fr 1fr 1fr 1fr; } }
@media (max-width: 768px) { .kpi-row { grid-template-columns: 1fr; } }
</style>
