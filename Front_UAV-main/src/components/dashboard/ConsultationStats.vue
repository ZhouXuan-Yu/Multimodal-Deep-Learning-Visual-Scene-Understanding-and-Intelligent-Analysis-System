<template>
  <div class="consultation-stats">
    <!-- KPI Row -->
    <div class="kpi-row">
      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #D4A843, #B08830);">
          <el-icon><ChatDotRound /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ consultationStats.total }}</div>
          <div class="kpi-label">累计咨询</div>
          <div class="kpi-sub">全部历史</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #8FB87A, #6B9B5A);">
          <el-icon><Sunny /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ consultationStats.today }}</div>
          <div class="kpi-label">今日咨询</div>
          <div class="kpi-sub">当日提交</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #7BA7C2, #5A8BA6);">
          <el-icon><Odometer /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ consultationStats.avgProcessingTime }}s</div>
          <div class="kpi-label">平均处理</div>
          <div class="kpi-sub">AI分析耗时</div>
        </div>
      </div>

      <div class="kpi-card premium-glass animate-glass-restore">
        <div class="kpi-icon" style="background: linear-gradient(135deg, #E8834A, #C4703A);">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ consultationStats.statusDist?.failed || 0 }}</div>
          <div class="kpi-label">失败重试</div>
          <div class="kpi-sub">邮件发送失败</div>
        </div>
      </div>
    </div>

    <!-- Charts -->
    <div class="charts-grid">
      <!-- Type Pie -->
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #D4A843, #B08830);">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <div>
              <div class="chart-name">咨询类型分布</div>
              <div class="chart-desc">按功能模块分组统计</div>
            </div>
          </div>
        </div>
        <div id="type-chart" class="chart-canvas"></div>
      </div>

      <!-- Status Bar -->
      <div class="chart-card premium-glass animate-glass-restore">
        <div class="chart-header">
          <div class="chart-title">
            <div class="chart-icon" style="background: linear-gradient(135deg, #E8834A, #C4703A);">
              <el-icon><DataAnalysis /></el-icon>
            </div>
            <div>
              <div class="chart-name">处理状态统计</div>
              <div class="chart-desc">邮件发送状态分布</div>
            </div>
          </div>
        </div>
        <div id="status-chart" class="chart-canvas"></div>
      </div>
    </div>

    <!-- Records -->
    <div class="records-section premium-glass animate-glass-restore">
      <div class="records-header">
        <div class="records-title">
          <el-icon><Clock /></el-icon>
          <span>咨询记录</span>
        </div>
        <span class="records-count">{{ consultationRecords.length }} 条记录</span>
      </div>
      <div class="records-table">
        <div class="record-row header">
          <span>时间</span><span>姓名</span><span>咨询类型</span><span>状态</span><span>详情</span>
        </div>
        <template
          v-for="(record, idx) in consultationRecords.slice(-15).reverse()"
          :key="record.id"
        >
          <div
            class="record-row"
            :class="{ expanded: expandedId === record.id }"
            :style="{ animationDelay: `${idx * 0.03}s` }"
            @click="toggleExpand(record.id)"
          >
            <span>{{ formatTime(record.timestamp) }}</span>
            <span>{{ record.name }}</span>
            <span>
              <span class="type-badge">
                {{ record.interestLabel }}
              </span>
            </span>
            <span>
              <span class="status-badge" :class="`status-${record.status}`">
                {{ statusLabels[record.status] }}
              </span>
            </span>
            <span class="expand-toggle">
              <el-icon><component :is="expandedId === record.id ? 'CaretTop' : 'CaretBottom'" /></el-icon>
              {{ expandedId === record.id ? '收起' : '查看' }}
            </span>
          </div>

          <!-- Expanded Detail -->
          <div v-if="expandedId === record.id" class="detail-row">
            <div class="detail-grid">
              <div class="detail-item">
                <div class="detail-label">用户邮箱</div>
                <div class="detail-value">{{ record.email || '未提供' }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">咨询类型</div>
                <div class="detail-value">{{ record.interestLabel }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">处理耗时</div>
                <div class="detail-value">{{ record.processingTime ? `${record.processingTime}s` : '—' }}</div>
              </div>
            </div>
            <div class="detail-section">
              <div class="detail-label">用户提问</div>
              <div class="detail-message user-msg">{{ record.message }}</div>
            </div>
            <div v-if="record.aiReply" class="detail-section">
              <div class="detail-label">AI 分析回复</div>
              <div class="detail-message ai-msg">{{ record.aiReply }}</div>
            </div>
          </div>
        </template>
        <div v-if="consultationRecords.length === 0" class="records-empty">
          <el-icon><ChatDotRound /></el-icon>
          <span>暂无咨询记录，请先在联系我们页面提交咨询</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, watch, ref } from 'vue';
import * as echarts from 'echarts';
import { ChatDotRound, Sunny, Odometer, Warning, DataAnalysis, Clock, CaretTop, CaretBottom } from '@element-plus/icons-vue';
import { useDashboardStore } from '@/stores/dashboardStore';

const store = useDashboardStore();
const consultationStats = computed(() => store.consultationStats);
const consultationRecords = computed(() => store.consultationRecords);
const expandedId = ref<string | null>(null);

const toggleExpand = (id: string) => {
  expandedId.value = expandedId.value === id ? null : id;
};

const statusLabels: Record<string, string> = {
  sent: '已发送', processing: '处理中', failed: '失败重试',
};

let typeChart: any = null;
let statusChart: any = null;

const COLORS = { text: '#7A6552', gold: '#D4A843', coral: '#E8906A', green: '#8FB87A', blue: '#7BA7C2', purple: '#B094BE' };

const formatTime = (ts: number) => {
  const d = new Date(ts);
  return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${d.getMinutes().toString().padStart(2,'0')}`;
};

const TYPE_COLORS = ['#E8834A', '#8FB87A', '#7BA7C2', '#D4A843', '#B094BE', '#E8906A'];

const initCharts = () => {
  const tDom = document.getElementById('type-chart');
  const sDom = document.getElementById('status-chart');
  if (tDom) typeChart = echarts.init(tDom);
  if (sDom) statusChart = echarts.init(sDom);
  updateCharts();
};

const updateCharts = () => {
  const { typeDist, statusDist } = consultationStats.value;
  const total = Object.values(typeDist).reduce((s: number, v) => s + (v as number), 0) || 1;

  if (typeChart) {
    const pieData = Object.entries(typeDist)
      .filter(([, v]) => (v as number) > 0)
      .map(([name, value], i) => ({ name, value, itemStyle: { color: TYPE_COLORS[i % TYPE_COLORS.length] } }));
    typeChart.setOption({
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

  if (statusChart) {
    const statusData = [
      { name: '已发送', value: statusDist?.sent || 0, color: '#8FB87A' },
      { name: '处理中', value: statusDist?.processing || 0, color: '#7BA7C2' },
      { name: '失败重试', value: statusDist?.failed || 0, color: '#E8906A' },
    ];
    statusChart.setOption({
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.97)', borderColor: 'rgba(200,160,100,0.25)', borderRadius: 12, padding: [10,14], textStyle: { fontFamily: 'Inter', color: '#3D2E1E' } },
      grid: { top: 10, left: 10, right: 10, bottom: 30, containLabel: true },
      xAxis: { type: 'category', data: statusData.map(d => d.name), axisLabel: { color: COLORS.text, fontFamily: 'Inter' }, axisLine: { lineStyle: { color: 'rgba(200,160,100,0.20)' } } },
      yAxis: { type: 'value', axisLabel: { color: COLORS.text, fontFamily: 'Inter' }, splitLine: { lineStyle: { color: 'rgba(200,160,100,0.08)' } } },
      series: [{
        type: 'bar',
        data: statusData.map(d => ({ value: d.value, itemStyle: { color: d.color, borderRadius: [4, 4, 0, 0] } })),
        barMaxWidth: 60,
        animationDuration: 1200,
      }],
    });
  }
};

const handleResize = () => { typeChart?.resize(); statusChart?.resize(); };
watch(() => consultationStats.value, updateCharts, { deep: true });
onMounted(() => { setTimeout(() => { initCharts(); window.addEventListener('resize', handleResize); }, 100); });
onBeforeUnmount(() => { window.removeEventListener('resize', handleResize); typeChart?.dispose(); statusChart?.dispose(); });
</script>

<style scoped>
.consultation-stats { display: flex; flex-direction: column; gap: 20px; }

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
.record-row { display: grid; grid-template-columns: 2fr 1.5fr 2fr 1.5fr 1.5fr; gap: 8px; padding: 9px 10px; border-radius: 8px; font-family: 'Inter',system-ui; font-size: 0.8rem; align-items: center; color: var(--text-primary); }
.record-row.header { background: rgba(200,160,100,0.06); color: var(--text-tertiary); font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.record-row:not(.header):hover { background: rgba(255,255,255,0.45); }
.record-row:not(.header) { animation: fadeSlideUp 0.3s ease both; }

.email-text { color: var(--text-secondary); font-size: 0.75rem; overflow: hidden; text-overflow: ellipsis; }
.type-badge { padding: 2px 8px; background: rgba(232,131,74,0.10); color: #C4703A; border: 1px solid rgba(232,131,74,0.20); border-radius: 8px; font-size: 0.72rem; font-weight: 600; }
.status-badge { padding: 2px 8px; border-radius: 8px; font-size: 0.72rem; font-weight: 600; }
.status-sent { background: rgba(143,184,122,0.12); color: #6B9B5A; }
.status-processing { background: rgba(232,176,96,0.12); color: #C48A30; }
.status-failed { background: rgba(196,80,64,0.12); color: #C45040; }

.records-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 32px; color: var(--text-tertiary); font-family: 'Inter',system-ui; font-size: 0.85rem; }

.record-row { cursor: pointer; }
.record-row.expanded { background: rgba(232,131,74,0.06); }
.expand-toggle { display: inline-flex; align-items: center; gap: 4px; color: var(--accent-primary); font-size: 0.75rem; font-weight: 500; }

.detail-row { padding: 16px 20px; background: rgba(253,251,247,0.8); border-bottom: 1px solid rgba(200,160,100,0.12); animation: fadeSlideUp 0.25s ease both; }
.detail-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 14px; }
.detail-item { display: flex; flex-direction: column; gap: 3px; }
.detail-label { font-family: 'Inter',system-ui; font-size: 0.68rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; }
.detail-value { font-family: 'Inter',system-ui; font-size: 0.8rem; color: var(--text-primary); }
.detail-section { margin-bottom: 10px; }
.detail-section:last-child { margin-bottom: 0; }
.detail-message { padding: 10px 12px; border-radius: 10px; font-family: 'Inter',system-ui; font-size: 0.8rem; line-height: 1.5; white-space: pre-wrap; word-break: break-word; max-height: 200px; overflow-y: auto; }
.user-msg { background: rgba(123,167,194,0.10); border-left: 3px solid #7BA7C2; color: var(--text-secondary); }
.ai-msg { background: rgba(232,131,74,0.08); border-left: 3px solid #E8834A; color: var(--text-secondary); }

@keyframes fadeSlideUp { 0% { opacity: 0; transform: translateY(4px); } 100% { opacity: 1; transform: translateY(0); } }

@media (max-width: 1400px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 1100px) { .charts-grid { grid-template-columns: 1fr; } }
@media (max-width: 768px) { .kpi-row { grid-template-columns: 1fr; } .record-row { grid-template-columns: 1fr 1fr 1fr; } }
</style>
