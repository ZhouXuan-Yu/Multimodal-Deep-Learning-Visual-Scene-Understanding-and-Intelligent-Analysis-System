/**
 * 文件名: AnomalyDetectionComponent.vue
 * 描述: AI异常检测组件 — Premium Edition
 * 作用:
 * - 展示无人机、人物识别、路径规划各模块的异常检测结果
 * - 对真实数据进行 Z-Score 异常检测
 * - 集成 DeepSeek API 生成智能分析报告
 * - 可视化异常趋势与告警分布
 */

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import * as echarts from 'echarts';
import { ElMessage, ElLoading } from 'element-plus';
import { ArrowLeft, RefreshRight, Download, Histogram, Warning, CircleCheck, TrendCharts, DataAnalysis, PieChart } from '@element-plus/icons-vue';
import AnomalyDetectionService from '@/services/AnomalyDetectionService';
import DeepSeekService from '@/services/DeepSeekService';
import MarkdownRenderer from '@/components/common/MarkdownRenderer.vue';
import { useDashboardStore } from '@/stores/dashboardStore';

const store = useDashboardStore();

const loading = ref(false);
const analyzing = ref(false);
const analysisResult = ref('');
let trendChart: any = null;
let sourceChart: any = null;

const CHART_COLORS = {
  primary: '#E8834A', gold: '#D4A843', coral: '#E8906A',
  warmBlue: '#7BA7C2', warmGreen: '#8FB87A', warmRed: '#C45040',
  amber: '#E8B060', text: '#7A6552', textLight: '#A89480',
  grid: 'rgba(200, 160, 100, 0.12)',
};

const anomalies = computed(() => store.anomalies);

const highCount = computed(() => anomalies.value.filter(a => a.severity === 'high').length);
const mediumCount = computed(() => anomalies.value.filter(a => a.severity === 'medium').length);
const lowCount = computed(() => anomalies.value.filter(a => a.severity === 'low').length);

const bySource = computed(() => {
  const counts: Record<string, number> = { recognition: 0, route: 0 };
  anomalies.value.forEach(a => {
    if (a.source in counts) counts[a.source]++;
  });
  return counts;
});

const getSeverityClass = (severity: string) => {
  const map: Record<string, string> = { high: 'severity-high', medium: 'severity-medium', low: 'severity-low' };
  return map[severity] || '';
};

const getSeverityLabel = (severity: string) => {
  const map: Record<string, string> = { high: '高风险', medium: '中风险', low: '低风险' };
  return map[severity] || severity;
};

const getSourceLabel = (source: string) => {
  const map: Record<string, string> = { recognition: '智眸千析', route: '智程导航' };
  return map[source] || source;
};

const getSeverityIcon = (severity: string) => {
  if (severity === 'low') return CircleCheck;
  return Warning;
};

const formatTime = (ts: number) => {
  const diff = Date.now() - ts;
  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
  return new Date(ts).toLocaleDateString('zh-CN');
};

const rerunDetection = () => {
  loading.value = true;
  setTimeout(() => {
    store.runAnomalyDetection();
    loading.value = false;
    updateCharts();
    ElMessage({ message: '异常检测已完成', type: 'success' });
  }, 800);
};

const analyzeWithDeepSeek = async () => {
  if (anomalies.value.length === 0) {
    ElMessage({ message: '暂无异常数据，请先执行异常检测', type: 'warning' });
    return;
  }
  analyzing.value = true;
  analysisResult.value = '';
  const loadingInstance = ElLoading.service({ lock: true, text: '正在进行智能分析...', background: 'rgba(253,251,247,0.90)' });

  const recognitionCount = bySource.value.recognition;
  const routeCount = bySource.value.route;

  const prompt = `作为数据分析系统的智能分析师，请对以下数据进行深入分析：

【系统概览】
- 智眸千析：累计识别 ${store.personStats.total} 人次，平均置信度 ${(store.personStats.avgConfidence * 100).toFixed(1)}%
- 智程导航：累计规划 ${store.routeStats.total} 条路线

【数据统计结果】
- 高风险: ${highCount.value} 条
- 中风险: ${mediumCount.value} 条
- 低风险: ${lowCount.value} 条
- 来源分布: 智眸千析 ${recognitionCount} 条, 智程导航 ${routeCount} 条

【详情】
${anomalies.value.slice(0, 10).map((a, i) => `${i + 1}. [${getSeverityLabel(a.severity)}] ${a.description} (${getSourceLabel(a.source)}, ${formatTime(a.timestamp)})`).join('\n')}

请提供：
1. 数据质量分析
2. 系统健康状况评估
3. 优化建议`;

  try {
    const result = await DeepSeekService.generateWeatherAnalysis(prompt);
    analysisResult.value = result;
    loadingInstance.close();
  } catch (error) {
    console.error('DeepSeek API 调用失败:', error);
    loadingInstance.close();
    ElMessage({ message: '智能分析服务暂时不可用', type: 'error' });
  } finally {
    analyzing.value = false;
  }
};

const exportData = () => {
  if (anomalies.value.length === 0) {
    ElMessage({ message: '暂无异常数据', type: 'warning' });
    return;
  }
  const json = JSON.stringify(anomalies.value, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `异常检测_${new Date().toISOString().split('T')[0]}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  ElMessage({ message: '导出成功', type: 'success' });
};

// ── Charts ──
const initCharts = () => {
  const trendDom = document.getElementById('anomaly-trend-chart');
  const sourceDom = document.getElementById('anomaly-source-chart');
  if (trendDom) trendChart = echarts.init(trendDom);
  if (sourceDom) sourceChart = echarts.init(sourceDom);
  updateCharts();
};

const updateCharts = () => {
  // Trend: mock last 7 days
  if (trendChart) {
    const days = 7;
    const today = new Date();
    const labels = Array.from({ length: days }, (_, i) => {
      const d = new Date(today.getTime() - (days - 1 - i) * 86400000);
      return `${d.getMonth() + 1}/${d.getDate()}`;
    });
    const highData = Array.from({ length: days }, (_, i) =>
      i === days - 1 ? highCount.value : Math.floor(Math.random() * Math.max(1, highCount.value))
    );
    const mediumData = Array.from({ length: days }, () => Math.floor(Math.random() * 5));
    trendChart.setOption({
      grid: { top: 20, left: 10, right: 10, bottom: 10, containLabel: true },
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.97)', borderColor: 'rgba(200,160,100,0.25)', borderRadius: 12, padding: [10,14], textStyle: { fontFamily: 'Inter', color: '#3D2E1E' } },
      legend: { data: ['高风险', '中风险'], textStyle: { color: CHART_COLORS.text, fontFamily: 'Inter', fontSize: 11 }, top: 4 },
      xAxis: { type: 'category', data: labels, axisLabel: { color: CHART_COLORS.textLight, fontFamily: 'Inter', fontSize: 11 }, axisLine: { lineStyle: { color: 'rgba(200,160,100,0.20)' } } },
      yAxis: { type: 'value', axisLabel: { color: CHART_COLORS.textLight, fontFamily: 'Inter' }, splitLine: { lineStyle: { color: 'rgba(200,160,100,0.08)', type: 'dashed' } } },
      series: [
        { name: '高风险', type: 'bar', data: highData, itemStyle: { color: CHART_COLORS.warmRed, borderRadius: [4,4,0,0] }, barMaxWidth: 32, animationDuration: 1200 },
        { name: '中风险', type: 'bar', data: mediumData, itemStyle: { color: CHART_COLORS.amber, borderRadius: [4,4,0,0] }, barMaxWidth: 32, animationDuration: 1200 },
      ],
    });
  }

  // Source Pie
  if (sourceChart) {
    const data = [
      { name: '智眸千析', value: bySource.value.recognition, color: CHART_COLORS.warmGreen },
      { name: '智程导航', value: bySource.value.route, color: CHART_COLORS.primary },
    ].filter(d => d.value > 0);
    sourceChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)', backgroundColor: 'rgba(255,255,255,0.97)', borderColor: 'rgba(200,160,100,0.25)', borderRadius: 12, padding: [10,14], textStyle: { fontFamily: 'Inter', color: '#3D2E1E' } },
      legend: { orient: 'horizontal', bottom: 0, left: 'center', textStyle: { color: CHART_COLORS.text, fontFamily: 'Inter', fontSize: 11 }, icon: 'circle' },
      series: [{
        type: 'pie', radius: ['30%', '62%'], center: ['50%', '45%'],
        itemStyle: { borderColor: 'rgba(255,255,255,0.8)', borderWidth: 2, borderRadius: 6 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold', color: '#3D2E1E', fontFamily: 'Inter' } },
        data: data.length > 0 ? data.map(d => ({ ...d, itemStyle: { color: d.color } })) : [{ name: '暂无异常', value: 1 }],
        animationType: 'expansion', animationDuration: 1200,
      }],
    });
  }
};

const handleResize = () => { trendChart?.resize(); sourceChart?.resize(); };

watch(() => anomalies.value, () => { updateCharts(); }, { deep: true });

onMounted(() => {
  setTimeout(() => {
    initCharts();
    window.addEventListener('resize', handleResize);
  }, 100);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  trendChart?.dispose();
  sourceChart?.dispose();
});
</script>

<template>
  <div class="anomaly-root">
    <!-- Header -->
    <div class="anomaly-header premium-glass animate-glass-restore">
      <div class="header-left">
        <div class="header-title">
          <div class="title-icon">
            <el-icon><Warning /></el-icon>
          </div>
          <div>
            <h2 class="title-main">AI 数据分析</h2>
            <p class="title-sub">多模块联合数据监测 · 实时统计分析</p>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <button class="premium-btn-glass" @click="rerunDetection" :disabled="loading">
          <el-icon><RefreshRight /></el-icon>
          {{ loading ? '检测中...' : '重新检测' }}
        </button>
        <button class="premium-btn-glass" @click="exportData" :disabled="anomalies.length === 0">
          <el-icon><Download /></el-icon>
          导出
        </button>
        <button class="premium-btn-primary" @click="analyzeWithDeepSeek" :disabled="analyzing || anomalies.length === 0">
          <el-icon><Histogram /></el-icon>
          {{ analyzing ? '分析中...' : 'AI智能分析' }}
        </button>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="stats-row">
      <div class="stat-card premium-glass animate-glass-restore">
        <div class="stat-icon stat-total"><el-icon><Warning /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value">{{ anomalies.length }}</div>
          <div class="stat-label">异常总数</div>
        </div>
      </div>
      <div class="stat-card premium-glass animate-glass-restore">
        <div class="stat-icon stat-high"><el-icon><Warning /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value">{{ highCount }}</div>
          <div class="stat-label">高风险</div>
        </div>
      </div>
      <div class="stat-card premium-glass animate-glass-restore">
        <div class="stat-icon stat-medium"><el-icon><Warning /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value">{{ mediumCount }}</div>
          <div class="stat-label">中风险</div>
        </div>
      </div>
      <div class="stat-card premium-glass animate-glass-restore">
        <div class="stat-icon stat-low"><el-icon><CircleCheck /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value">{{ lowCount }}</div>
          <div class="stat-label">低风险</div>
        </div>
      </div>
    </div>

    <!-- Charts -->
    <div class="charts-row">
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #E8834A, #C4703A);">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <div>
              <div class="chart-name">异常趋势</div>
              <div class="chart-desc">最近7天风险等级分布</div>
            </div>
          </div>
        </div>
        <div id="anomaly-trend-chart" class="chart-canvas"></div>
      </div>

      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #D4A843, #B08830);">
              <el-icon><PieChart /></el-icon>
            </div>
            <div>
              <div class="chart-name">异常来源分布</div>
              <div class="chart-desc">按模块分组统计</div>
            </div>
          </div>
        </div>
        <div id="anomaly-source-chart" class="chart-canvas"></div>
      </div>
    </div>

    <!-- Anomaly List -->
    <div class="anomaly-list premium-glass animate-glass-restore">
      <div class="list-header">
        <div class="list-title">
          <div class="list-icon"><el-icon><Warning /></el-icon></div>
          <h3>检测到的异常</h3>
          <span class="anomaly-count">{{ anomalies.length }}</span>
        </div>
        <button class="premium-btn-primary" size="small" @click="analyzeWithDeepSeek" :disabled="analyzing || anomalies.length === 0">
          <el-icon><Histogram /></el-icon>
          AI分析
        </button>
      </div>

      <div v-if="anomalies.length === 0" class="empty-state">
        <div class="empty-icon"><el-icon><CircleCheck /></el-icon></div>
        <p class="empty-title">系统运行正常</p>
        <p class="empty-sub">当前未检测到显著异常，所有指标处于正常范围</p>
      </div>

      <div v-else class="anomaly-grid">
        <div
          v-for="(anomaly, idx) in anomalies"
          :key="anomaly.id"
          class="anomaly-card"
          :class="getSeverityClass(anomaly.severity)"
          :style="{ animationDelay: `${idx * 0.05}s` }"
        >
          <div class="card-header">
            <div class="source-badge">{{ getSourceLabel(anomaly.source) }}</div>
            <span class="severity-badge" :class="`badge-${anomaly.severity}`">
              {{ getSeverityLabel(anomaly.severity) }}
            </span>
          </div>
          <div class="card-body">
            <div class="card-desc">{{ anomaly.description }}</div>
            <div class="card-meta">
              <span>指标: {{ anomaly.metric }}</span>
              <span>当前值: {{ typeof anomaly.value === 'number' ? anomaly.value.toFixed(1) : anomaly.value }}</span>
              <span>阈值: {{ anomaly.threshold }}</span>
              <span>{{ formatTime(anomaly.timestamp) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI Analysis Result -->
    <div v-if="analysisResult" class="analysis-result premium-glass animate-glass-restore">
      <div class="result-header">
        <div class="result-icon">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="10" r="8" stroke="url(#aiGrad)" stroke-width="1.5"/>
            <path d="M7 10L9 12L13 8" stroke="url(#aiGrad)" stroke-width="1.5" stroke-linecap="round"/>
            <defs><linearGradient id="aiGrad" x1="0" y1="0" x2="20" y2="20"><stop offset="0%" stop-color="#E8834A"/><stop offset="100%" stop-color="#D4A843"/></linearGradient></defs>
          </svg>
        </div>
        <h3>DeepSeek 智能分析报告</h3>
      </div>
      <div class="result-body">
        <MarkdownRenderer :content="analysisResult" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.anomaly-root { display: flex; flex-direction: column; gap: 20px; }

/* Header */
.anomaly-header { padding: 20px 24px; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.header-left { display: flex; align-items: center; gap: 16px; }
.header-title { display: flex; align-items: center; gap: 14px; }
.title-icon { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, var(--accent-primary), var(--accent-gold)); box-shadow: 0 4px 14px rgba(232,131,74,0.30); }
.title-icon .el-icon { font-size: 20px; color: white; }
.title-main { font-family: 'Inter',system-ui; font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin: 0 0 3px; }
.title-sub { font-family: 'Inter',system-ui; font-size: 0.78rem; color: var(--text-tertiary); margin: 0; }
.header-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

/* Stats */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat-card { padding: 16px 20px; display: flex; align-items: center; gap: 14px; }
.stat-icon { width: 40px; height: 40px; border-radius: 11px; display: flex; align-items: center; justify-content: center; }
.stat-icon .el-icon { font-size: 18px; color: white; }
.stat-total { background: linear-gradient(135deg, #E8906A, #C4703A); }
.stat-high { background: linear-gradient(135deg, #C45040, #A03020); }
.stat-medium { background: linear-gradient(135deg, #E8B060, #C08830); }
.stat-low { background: linear-gradient(135deg, #8FB87A, #6B9B5A); }
.stat-value { font-family: 'Inter','SF Pro Display',system-ui; font-size: 1.5rem; font-weight: 700; color: var(--text-primary); letter-spacing: -0.03em; line-height: 1; }
.stat-label { font-family: 'Inter',system-ui; font-size: 0.75rem; font-weight: 500; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }

/* Charts */
.charts-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }
.chart-card { padding: 20px; display: flex; flex-direction: column; gap: 14px; min-height: 280px; }
.chart-header { display: flex; align-items: center; }
.chart-title { display: flex; align-items: center; gap: 12px; }
.chart-icon { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.chart-icon .el-icon { font-size: 18px; color: white; }
.chart-name { font-family: 'Inter',system-ui; font-weight: 600; font-size: 0.9rem; color: var(--text-primary); }
.chart-desc { font-family: 'Inter',system-ui; font-size: 0.72rem; color: var(--text-tertiary); }
.chart-canvas { flex: 1; min-height: 200px; }

/* Anomaly List */
.anomaly-list { padding: 24px; }
.list-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; padding-bottom: 14px; border-bottom: 1px solid rgba(200,160,100,0.15); }
.list-title { display: flex; align-items: center; gap: 10px; }
.list-icon { width: 32px; height: 32px; border-radius: 9px; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #E8906A, #C4703A); }
.list-icon .el-icon { font-size: 16px; color: white; }
.list-title h3 { font-family: 'Inter',system-ui; font-size: 0.95rem; font-weight: 600; color: var(--text-primary); margin: 0; }
.anomaly-count { display: inline-flex; align-items: center; justify-content: center; min-width: 22px; height: 22px; padding: 0 7px; background: linear-gradient(135deg, var(--accent-primary), var(--accent-gold)); color: white; border-radius: 11px; font-family: 'Inter',system-ui; font-size: 0.72rem; font-weight: 700; }

/* Empty */
.empty-state { display: flex; flex-direction: column; align-items: center; padding: 48px 20px; text-align: center; }
.empty-icon { width: 56px; height: 56px; border-radius: 50%; background: rgba(143,184,122,0.15); display: flex; align-items: center; justify-content: center; margin-bottom: 16px; }
.empty-icon .el-icon { font-size: 26px; color: #6B9B5A; }
.empty-title { font-family: 'Inter',system-ui; font-size: 1rem; font-weight: 600; color: var(--text-primary); margin: 0 0 6px; }
.empty-sub { font-family: 'Inter',system-ui; font-size: 0.85rem; color: var(--text-tertiary); margin: 0; }

/* Anomaly Grid */
.anomaly-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.anomaly-card { background: rgba(255,255,255,0.45); border-radius: 16px; padding: 16px; border: 1px solid rgba(200,160,100,0.15); position: relative; overflow: hidden; transition: all 0.3s ease; animation: fadeSlideUp 0.5s ease both; opacity: 0; }
.anomaly-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; border-radius: 16px 16px 0 0; }
.severity-high::before { background: linear-gradient(90deg, #C45040, #E8906A); }
.severity-medium::before { background: linear-gradient(90deg, #E8B060, #E8B060); }
.severity-low::before { background: linear-gradient(90deg, #8FB87A, #8FB87A); }
.anomaly-card:hover { transform: translateY(-3px); box-shadow: 0 12px 36px rgba(180,120,60,0.12); background: rgba(255,255,255,0.65); }
.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.source-badge { padding: 2px 8px; background: rgba(200,160,100,0.10); color: var(--text-secondary); border-radius: 8px; font-family: 'Inter',system-ui; font-size: 0.72rem; font-weight: 600; }
.severity-badge { padding: 2px 9px; border-radius: 10px; font-family: 'Inter',system-ui; font-size: 0.72rem; font-weight: 700; }
.badge-high { background: rgba(196,80,64,0.14); color: #C45040; border: 1px solid rgba(196,80,64,0.25); }
.badge-medium { background: rgba(232,176,96,0.16); color: #C48A30; border: 1px solid rgba(232,176,96,0.28); }
.badge-low { background: rgba(143,184,122,0.16); color: #6B9B5A; border: 1px solid rgba(143,184,122,0.28); }
.card-desc { font-family: 'Inter',system-ui; font-size: 0.82rem; color: var(--text-primary); line-height: 1.5; margin-bottom: 8px; }
.card-meta { display: flex; gap: 8px; flex-wrap: wrap; font-family: 'Inter',system-ui; font-size: 0.72rem; color: var(--text-tertiary); }
.card-meta span { background: rgba(200,160,100,0.08); padding: 2px 6px; border-radius: 6px; }

/* Analysis Result */
.analysis-result { padding: 24px; }
.result-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding-bottom: 14px; border-bottom: 1px solid rgba(200,160,100,0.15); }
.result-icon { display: flex; align-items: center; justify-content: center; }
.result-header h3 { font-family: 'Inter',system-ui; font-size: 0.95rem; font-weight: 600; color: var(--text-primary); margin: 0; }
.result-body { background: rgba(255,255,255,0.40); border-radius: 14px; padding: 20px; border: 1px solid rgba(200,160,100,0.12); max-height: 500px; overflow-y: auto; }

/* Buttons */
.premium-btn-glass { display: inline-flex; align-items: center; gap: 7px; padding: 9px 18px; background: rgba(255,255,255,0.45); backdrop-filter: blur(12px); border: 1px solid rgba(200,160,100,0.15); border-radius: 14px; font-family: 'Inter',system-ui; font-weight: 500; font-size: 0.85rem; color: var(--text-secondary); cursor: pointer; transition: all 0.3s ease; }
.premium-btn-glass:hover:not(:disabled) { background: rgba(255,255,255,0.70); color: var(--text-primary); border-color: rgba(200,160,100,0.35); }
.premium-btn-glass:disabled { opacity: 0.5; cursor: not-allowed; }
.premium-btn-primary { display: inline-flex; align-items: center; gap: 7px; padding: 9px 18px; background: linear-gradient(135deg, var(--accent-primary), var(--accent-gold)); border: none; border-radius: 14px; font-family: 'Inter',system-ui; font-weight: 600; font-size: 0.85rem; color: white; cursor: pointer; box-shadow: 0 4px 16px rgba(232,131,74,0.30); transition: all 0.3s ease; }
.premium-btn-primary:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(232,131,74,0.40); }
.premium-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

@keyframes fadeSlideUp { 0% { opacity: 0; transform: translateY(12px); } 100% { opacity: 1; transform: translateY(0); } }

@media (max-width: 1100px) { .stats-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 768px) { .stats-row { grid-template-columns: 1fr; } .charts-row { grid-template-columns: 1fr; } .anomaly-grid { grid-template-columns: 1fr; } .anomaly-header { flex-direction: column; align-items: flex-start; } }
</style>
