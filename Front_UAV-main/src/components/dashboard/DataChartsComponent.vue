/**
 * 文件名: DataChartsComponent.vue
 * 描述: 数据图表可视化组件 — Premium Edition
 * 在项目中的作用:
 * - 使用ECharts提供多种数据图表展示
 * - 可视化展示无人机的电量、信号、速度等核心指标
 * - 提供实时数据更新和历史数据趋势分析
 * - 支持多种图表类型和交互方式
 */

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, reactive, watch } from 'vue';
import * as echarts from 'echarts';
import { ElMessage } from 'element-plus';
import { Filter } from '@element-plus/icons-vue';

type ChartType = 'battery' | 'signal' | 'speed' | 'person' | 'personActivity' | 'vehicle' | 'task' | 'risk' | 'heatmap' | 'all';

const props = defineProps({
  chartType: {
    type: String as () => ChartType,
    default: 'all'
  },
  updateInterval: {
    type: Number,
    default: 30000
  }
});

let batteryChart: any = null;
let signalChart: any = null;
let speedChart: any = null;
let recognitionChart: any = null;
let personActivityChart: any = null;
let riskChart: any = null;
let updateTimer: number | null = null;

const chartsLoading = reactive({
  battery: false, signal: false, speed: false,
  recognition: false, person: false, personActivity: false,
  vehicle: false, task: false, risk: false, heatmap: false, comparison: false
});

const dateRange = ref<[Date, Date]>([
  new Date(new Date().setDate(new Date().getDate() - 7)),
  new Date()
]);

const regions = ref([
  { value: 'north', label: '北部区域' },
  { value: 'south', label: '南部区域' },
  { value: 'east', label: '东部区域' },
  { value: 'west', label: '西部区域' },
  { value: 'central', label: '中心区域' }
]);
const selectedRegions = ref(['central']);

const dataTypeOptions = ref([
  { value: 'person', label: '人流量' },
  { value: 'vehicle', label: '车流量' },
  { value: 'risk', label: '风险事件' },
  { value: 'drone', label: '无人机状态' }
]);
const selectedDataTypes = ref(['person', 'vehicle', 'risk']);
const showFilterPanel = ref(false);

// === Warm Color Palette for ECharts ===
const CHART_COLORS = {
  primary: '#E8834A',
  gold: '#D4A843',
  coral: '#E8906A',
  peach: '#F5C9A0',
  amber: '#E8B060',
  deep: '#C4703A',
  cream: '#F5E6D0',
  warmBlue: '#7BA7C2',
  warmGreen: '#8FB87A',
  warmPurple: '#B094BE',
  warmRed: '#C45040',
  text: '#7A6552',
  textLight: '#A89480',
  grid: 'rgba(200, 160, 100, 0.12)',
  splitLine: 'rgba(200, 160, 100, 0.08)',
};

// Shared tooltip/axis config
const makeTooltip = (formatter?: string) => ({
  trigger: 'axis' as const,
  backgroundColor: 'rgba(255, 255, 255, 0.97)',
  borderColor: 'rgba(200, 160, 100, 0.25)',
  borderWidth: 1,
  borderRadius: 12,
  padding: [10, 14],
  textStyle: {
    fontFamily: 'Inter, system-ui',
    color: '#3D2E1E',
    fontSize: 12,
  },
  axisPointer: {
    type: 'line' as const,
    lineStyle: {
      color: 'rgba(232, 131, 74, 0.35)',
      width: 2,
    },
  },
});

const makeAxis = (labelColor = CHART_COLORS.textLight) => ({
  axisLabel: {
    color: labelColor,
    fontSize: 11,
    fontFamily: 'Inter, system-ui',
  },
  axisLine: { lineStyle: { color: 'rgba(200, 160, 100, 0.20)' } },
  axisTick: { lineStyle: { color: 'rgba(200, 160, 100, 0.20)' } },
  splitLine: { lineStyle: { color: CHART_COLORS.splitLine, type: 'dashed' as const } },
});

const makeGrid = () => ({
  top: 20, left: 12, right: 16, bottom: 12, containLabel: true,
});

// Battery data
const batteryData = ref<number[]>([85, 84, 83, 82, 80, 79, 78, 77, 76, 75]);
const signalData = ref<number[]>([92, 94, 90, 88, 85, 87, 91, 89, 90, 88]);
const speedData = ref<number[]>([8.4, 12.1, 10.5, 9.2, 11.8, 13.2, 12.4, 10.8, 9.6, 11.2]);
const timePoints = ref<string[]>([]);

const historyBatteryData = ref<number[]>([88, 86, 85, 84, 82, 81, 80, 79, 77, 76]);
const historySignalData = ref<number[]>([95, 93, 92, 90, 88, 89, 93, 91, 88, 87]);
const historySpeedData = ref<number[]>([7.8, 11.3, 9.8, 8.7, 10.9, 12.4, 11.8, 10.2, 9.1, 10.5]);

const useDataFiltering = ref(true);
const filterStrength = ref(3);

const applyDataFilter = (data: number[], newValue: number): number => {
  if (!useDataFiltering.value || data.length === 0) return newValue;
  const lastValue = data[data.length - 1];
  const filtered = lastValue + (newValue - lastValue) / filterStrength.value;
  return Number(filtered.toFixed(1));
};

const recognitionData = ref([
  { name: '成年男性', value: 42 },
  { name: '成年女性', value: 38 },
  { name: '老年人', value: 15 },
  { name: '儿童', value: 5 }
]);

const personActivityData = ref([
  { date: '7:00', active: 32, stationary: 18, entering: 8, leaving: 5 },
  { date: '8:00', active: 48, stationary: 25, entering: 15, leaving: 7 },
  { date: '9:00', active: 65, stationary: 30, entering: 18, leaving: 12 },
  { date: '10:00', active: 72, stationary: 35, entering: 20, leaving: 15 },
  { date: '11:00', active: 80, stationary: 45, entering: 15, leaving: 18 },
  { date: '12:00', active: 95, stationary: 52, entering: 10, leaving: 25 },
  { date: '13:00', active: 85, stationary: 45, entering: 12, leaving: 20 }
]);

const taskData = ref([
  { name: '人物识别', value: 32 },
  { name: '车辆监控', value: 28 },
  { name: '灾害检测', value: 15 },
  { name: '车牌识别', value: 18 },
  { name: '其他任务', value: 7 }
]);

const riskData = ref([
  { date: '6/1', level1: 2, level2: 5, level3: 1 },
  { date: '6/2', level1: 3, level2: 4, level3: 0 },
  { date: '6/3', level1: 5, level2: 6, level3: 2 },
  { date: '6/4', level1: 4, level2: 7, level3: 1 },
  { date: '6/5', level1: 6, level2: 5, level3: 2 },
  { date: '6/6', level1: 2, level2: 3, level3: 0 },
  { date: '6/7', level1: 3, level2: 4, level3: 1 }
]);

const droneList = ref([
  { id: 1, name: '无人机#01', type: '侦察型', battery: 85, signal: 92, speed: 8.4, status: '巡航中' },
  { id: 2, name: '无人机#02', type: '夜视型', battery: 78, signal: 88, speed: 10.2, status: '巡航中' },
  { id: 3, name: '无人机#03', type: '高速型', battery: 92, signal: 95, speed: 14.5, status: '待命中' },
  { id: 4, name: '无人机#04', type: '侦察型', battery: 65, signal: 83, speed: 9.1, status: '巡航中' },
  { id: 5, name: '无人机#05', type: '夜视型', battery: 72, signal: 90, speed: 7.8, status: '返航中' },
]);

const selectedDroneId = ref(1);
const selectedDrone = () => droneList.value.find(d => d.id === selectedDroneId.value) || droneList.value[0];

const generateTimePoints = () => {
  const now = new Date();
  const points = [];
  for (let i = 9; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 60000);
    points.push(`${time.getHours()}:${time.getMinutes().toString().padStart(2, '0')}`);
  }
  timePoints.value = points;
};

const shouldShowChart = (type: ChartType): boolean => {
  return props.chartType === 'all' || props.chartType === type;
};

const makeLineGradient = (color1: string, color2: string) =>
  new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: color1 },
    { offset: 1, color: color2 },
  ]);

const makeAreaGradient = (color: string) =>
  new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: `${color}40` },
    { offset: 1, color: `${color}00` },
  ]);

// ── Battery Chart ──
const initBatteryChart = () => {
  const chartDom = document.getElementById('battery-chart');
  if (!chartDom) return;
  batteryChart = echarts.init(chartDom);
  chartsLoading.battery = true;
  setTimeout(() => {
    batteryChart.setOption({
      grid: makeGrid(),
      tooltip: { ...makeTooltip('{b}<br/>{a}: {c}%'), formatter: '{b}<br/>{a}: {c}%' },
      xAxis: { type: 'category', data: timePoints.value, ...makeAxis() },
      yAxis: { type: 'value', min: 50, max: 100, ...makeAxis(), axisLabel: { formatter: '{value}%', color: CHART_COLORS.textLight, fontFamily: 'Inter' } },
      series: [{
        name: '电池电量',
        type: 'line', data: batteryData.value, smooth: 0.4,
        symbol: 'circle', symbolSize: 6, showSymbol: false,
        lineStyle: { width: 3, color: CHART_COLORS.warmGreen },
        itemStyle: { color: CHART_COLORS.warmGreen, borderColor: 'white', borderWidth: 2 },
        areaStyle: { color: makeAreaGradient(CHART_COLORS.warmGreen) },
        emphasis: { focus: 'series', itemStyle: { shadowBlur: 12, shadowColor: `${CHART_COLORS.warmGreen}80` } },
        animationDuration: 1800, animationEasing: 'cubicOut',
      }],
    });
    chartsLoading.battery = false;
  }, 200);
};

// ── Signal Chart ──
const initSignalChart = () => {
  const chartDom = document.getElementById('signal-chart');
  if (!chartDom) return;
  signalChart = echarts.init(chartDom);
  chartsLoading.signal = true;
  setTimeout(() => {
    signalChart.setOption({
      grid: makeGrid(),
      tooltip: { ...makeTooltip(), formatter: '{b}<br/>{a}: {c}%' },
      xAxis: { type: 'category', data: timePoints.value, ...makeAxis() },
      yAxis: { type: 'value', min: 50, max: 100, ...makeAxis(), axisLabel: { formatter: '{value}%', color: CHART_COLORS.textLight, fontFamily: 'Inter' } },
      series: [{
        name: '信号强度',
        type: 'line', data: signalData.value, smooth: 0.4,
        symbol: 'circle', symbolSize: 6, showSymbol: false,
        lineStyle: { width: 3, color: CHART_COLORS.warmBlue },
        itemStyle: { color: CHART_COLORS.warmBlue, borderColor: 'white', borderWidth: 2 },
        areaStyle: { color: makeAreaGradient(CHART_COLORS.warmBlue) },
        emphasis: { focus: 'series', itemStyle: { shadowBlur: 12, shadowColor: `${CHART_COLORS.warmBlue}80` } },
        animationDuration: 1800, animationEasing: 'cubicOut',
      }],
    });
    chartsLoading.signal = false;
  }, 200);
};

// ── Speed Chart ──
const initSpeedChart = () => {
  const chartDom = document.getElementById('speed-chart');
  if (!chartDom) return;
  speedChart = echarts.init(chartDom);
  chartsLoading.speed = true;
  setTimeout(() => {
    speedChart.setOption({
      grid: makeGrid(),
      tooltip: { ...makeTooltip(), formatter: '{b}<br/>{a}: {c} m/s' },
      visualMap: { show: false, dimension: 1, pieces: [
        { lte: 5, color: CHART_COLORS.warmGreen },
        { gt: 5, lte: 10, color: CHART_COLORS.amber },
        { gt: 10, color: CHART_COLORS.primary },
      ]},
      xAxis: { type: 'category', data: timePoints.value, ...makeAxis() },
      yAxis: { type: 'value', min: 0, max: 20, ...makeAxis(), axisLabel: { formatter: '{value}', color: CHART_COLORS.textLight, fontFamily: 'Inter' } },
      series: [{
        name: '飞行速度',
        type: 'line', data: speedData.value, smooth: 0.4,
        symbol: 'circle', symbolSize: 6, showSymbol: false,
        lineStyle: { width: 3, color: CHART_COLORS.primary },
        itemStyle: { color: CHART_COLORS.primary, borderColor: 'white', borderWidth: 2 },
        areaStyle: { color: makeAreaGradient(CHART_COLORS.primary) },
        markPoint: {
          symbol: 'circle', symbolSize: 36,
          data: [{ type: 'max', name: '最高速度' }],
          label: { formatter: '{b}: {c}', fontFamily: 'Inter', fontSize: 11 },
          itemStyle: { color: CHART_COLORS.coral },
        },
        animationDuration: 1800, animationEasing: 'cubicOut',
      }],
    });
    chartsLoading.speed = false;
  }, 200);
};

// ── Person Activity Chart ──
const initPersonActivityChart = () => {
  const chartDom = document.getElementById('person-activity-chart');
  if (!chartDom) return;
  personActivityChart = echarts.init(chartDom);
  chartsLoading.personActivity = true;
  setTimeout(() => {
    personActivityChart.setOption({
      grid: { top: 36, left: 10, right: 10, bottom: 10, containLabel: true },
      tooltip: { ...makeTooltip(), trigger: 'axis' },
      legend: {
        data: ['活跃人员', '静止人员', '进入区域', '离开区域'],
        textStyle: { color: CHART_COLORS.text, fontFamily: 'Inter', fontSize: 11 },
        top: 4, itemGap: 14,
      },
      xAxis: { type: 'category', data: personActivityData.value.map(i => i.date), ...makeAxis() },
      yAxis: { type: 'value', ...makeAxis() },
      series: [
        { name: '活跃人员', type: 'line', smooth: 0.4, data: personActivityData.value.map(i => i.active), lineStyle: { width: 2.5, color: CHART_COLORS.warmGreen }, itemStyle: { color: CHART_COLORS.warmGreen }, animationDuration: 1400 },
        { name: '静止人员', type: 'line', smooth: 0.4, data: personActivityData.value.map(i => i.stationary), lineStyle: { width: 2.5, color: CHART_COLORS.warmBlue }, itemStyle: { color: CHART_COLORS.warmBlue }, animationDuration: 1400 },
        { name: '进入区域', type: 'bar', data: personActivityData.value.map(i => i.entering), itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: CHART_COLORS.gold }, { offset: 1, color: `${CHART_COLORS.gold}60` }]), borderRadius: [4, 4, 0, 0] }, animationDuration: 1200 },
        { name: '离开区域', type: 'bar', data: personActivityData.value.map(i => i.leaving), itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: CHART_COLORS.coral }, { offset: 1, color: `${CHART_COLORS.coral}60` }]), borderRadius: [4, 4, 0, 0] }, animationDuration: 1200 },
      ],
    });
    chartsLoading.personActivity = false;
  }, 200);
};

// ── Recognition Pie Chart ──
const initRecognitionChart = () => {
  const chartDom = document.getElementById('recognition-chart');
  if (!chartDom) return;
  recognitionChart = echarts.init(chartDom);
  chartsLoading.recognition = true;
  const pieColors = [CHART_COLORS.primary, CHART_COLORS.gold, CHART_COLORS.warmBlue, CHART_COLORS.coral];
  setTimeout(() => {
    recognitionChart.setOption({
      tooltip: { ...makeTooltip(), trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: {
        orient: 'horizontal', bottom: 0, left: 'center',
        textStyle: { color: CHART_COLORS.text, fontFamily: 'Inter', fontSize: 11 },
        icon: 'circle', itemWidth: 10, itemHeight: 10, itemGap: 14,
      },
      series: [{
        type: 'pie',
        radius: ['30%', '62%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: 'rgba(255,255,255,0.8)', borderWidth: 2, borderRadius: 6 },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 13, fontWeight: 'bold', color: '#3D2E1E', fontFamily: 'Inter' },
          itemStyle: { shadowBlur: 16, shadowColor: `${CHART_COLORS.primary}40` },
        },
        labelLine: { show: false },
        data: recognitionData.value.map((d, i) => ({ ...d, itemStyle: { color: pieColors[i] } })),
        animationType: 'expansion', animationDuration: 1400,
      }],
    });
    chartsLoading.recognition = false;
  }, 200);
};

// ── Task Rose Chart ──
const initTaskChart = () => {
  const chartDom = document.getElementById('task-chart');
  if (!chartDom) return;
  const taskChart = echarts.init(chartDom);
  chartsLoading.task = true;
  const taskColors = [CHART_COLORS.warmGreen, CHART_COLORS.warmBlue, CHART_COLORS.warmRed, CHART_COLORS.gold, CHART_COLORS.warmPurple];
  setTimeout(() => {
    taskChart.setOption({
      tooltip: { ...makeTooltip(), trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: {
        orient: 'horizontal', bottom: 0, left: 'center',
        textStyle: { color: CHART_COLORS.text, fontFamily: 'Inter', fontSize: 11 },
        icon: 'rect', itemWidth: 10, itemHeight: 10, itemGap: 10,
      },
      series: [{
        type: 'pie', radius: ['0%', '68%'], center: ['50%', '45%'],
        roseType: 'radius',
        itemStyle: { borderRadius: 6, borderColor: 'rgba(255,255,255,0.8)', borderWidth: 2 },
        label: { show: false },
        emphasis: {
          label: { show: true, formatter: '{b}: {c}', color: '#3D2E1E', fontFamily: 'Inter', fontSize: 12 },
          itemStyle: { shadowBlur: 16, shadowColor: `${CHART_COLORS.gold}40` },
        },
        data: taskData.value.map((d, i) => ({ ...d, itemStyle: { color: taskColors[i] } })),
        animationType: 'expansion', animationDuration: 1400,
      }],
    });
    chartsLoading.task = false;
  }, 200);
};

// ── Risk Stacked Bar Chart ──
const initRiskChart = () => {
  const chartDom = document.getElementById('risk-chart');
  if (!chartDom) return;
  riskChart = echarts.init(chartDom);
  chartsLoading.risk = true;
  setTimeout(() => {
    riskChart.setOption({
      grid: { top: 36, left: 8, right: 8, bottom: 8, containLabel: true },
      tooltip: { ...makeTooltip(), trigger: 'axis' },
      legend: {
        data: ['低风险', '中风险', '高风险'],
        textStyle: { color: CHART_COLORS.text, fontFamily: 'Inter', fontSize: 11 },
        top: 4,
      },
      xAxis: { type: 'category', data: riskData.value.map(i => i.date), ...makeAxis() },
      yAxis: { type: 'value', ...makeAxis() },
      series: [
        { name: '低风险', type: 'bar', stack: 'total', data: riskData.value.map(i => i.level1), itemStyle: { color: CHART_COLORS.warmGreen, borderRadius: [0, 0, 0, 0] }, animationDuration: 1200 },
        { name: '中风险', type: 'bar', stack: 'total', data: riskData.value.map(i => i.level2), itemStyle: { color: CHART_COLORS.amber, borderRadius: [0, 0, 0, 0] }, animationDuration: 1200 },
        { name: '高风险', type: 'bar', stack: 'total', data: riskData.value.map(i => i.level3), itemStyle: { color: CHART_COLORS.warmRed, borderRadius: [4, 4, 0, 0] }, animationDuration: 1200 },
      ],
    });
    chartsLoading.risk = false;
  }, 200);
};

const updateChartData = () => {
  generateTimePoints();
  const drone = selectedDrone();
  const newBattery = Math.max(50, Math.min(100, drone.battery + (Math.random() * 2 - 1)));
  const newSignal = Math.max(70, Math.min(100, drone.signal + (Math.random() * 4 - 2)));
  const newSpeed = Math.max(5, Math.min(20, drone.speed + (Math.random() * 2 - 1)));
  const fb = applyDataFilter(batteryData.value, newBattery);
  const fs = applyDataFilter(signalData.value, newSignal);
  const fv = applyDataFilter(speedData.value, newSpeed);
  drone.battery = parseFloat(fb.toFixed(1));
  drone.signal = parseFloat(fs.toFixed(1));
  drone.speed = parseFloat(fv.toFixed(1));
  batteryData.value.shift(); batteryData.value.push(parseFloat(fb.toFixed(1)));
  signalData.value.shift(); signalData.value.push(parseFloat(fs.toFixed(1)));
  speedData.value.shift(); speedData.value.push(parseFloat(fv.toFixed(1)));

  if (batteryChart) batteryChart.setOption({ xAxis: { data: timePoints.value }, series: [{ data: batteryData.value }] });
  if (signalChart) signalChart.setOption({ xAxis: { data: timePoints.value }, series: [{ data: signalData.value }] });
  if (speedChart) speedChart.setOption({ xAxis: { data: timePoints.value }, series: [{ data: speedData.value }] });
};

const disposeCharts = () => {
  [batteryChart, signalChart, speedChart, recognitionChart, personActivityChart, riskChart].forEach(c => { if (c) { c.dispose(); } });
  batteryChart = signalChart = speedChart = recognitionChart = personActivityChart = riskChart = null;
};

const handleResize = () => {
  setTimeout(() => {
    [batteryChart, signalChart, speedChart, recognitionChart, personActivityChart, riskChart].forEach(c => { if (c) c.resize(); });
  }, 200);
};

onMounted(() => {
  generateTimePoints();
  if (shouldShowChart('battery')) initBatteryChart();
  if (shouldShowChart('signal')) initSignalChart();
  if (shouldShowChart('speed')) initSpeedChart();
  if (shouldShowChart('person')) initRecognitionChart();
  if (shouldShowChart('personActivity')) initPersonActivityChart();
  if (shouldShowChart('task')) initTaskChart();
  if (shouldShowChart('risk')) initRiskChart();
  if (props.chartType === 'all') {
    setTimeout(() => {
      initBatteryChart(); initSignalChart(); initSpeedChart();
      initRecognitionChart(); initPersonActivityChart(); initTaskChart(); initRiskChart();
    }, 200);
  }
  updateTimer = window.setInterval(updateChartData, props.updateInterval);
  window.addEventListener('resize', handleResize);
});

watch(() => props.chartType, () => {
  disposeCharts();
  setTimeout(() => {
    if (shouldShowChart('battery')) initBatteryChart();
    if (shouldShowChart('signal')) initSignalChart();
    if (shouldShowChart('speed')) initSpeedChart();
    if (shouldShowChart('person')) initRecognitionChart();
    if (shouldShowChart('personActivity')) initPersonActivityChart();
    if (shouldShowChart('task')) initTaskChart();
    if (shouldShowChart('risk')) initRiskChart();
  }, 100);
});

onBeforeUnmount(() => {
  if (updateTimer) clearInterval(updateTimer);
  window.removeEventListener('resize', handleResize);
  disposeCharts();
});
</script>

<template>
  <div class="premium-charts-root">
    <!-- Drone Selector Bar -->
    <div v-if="shouldShowChart('battery') || shouldShowChart('signal') || shouldShowChart('speed')" class="drone-selector-bar">
      <div class="selector-label">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <circle cx="7" cy="7" r="5" stroke="currentColor" stroke-width="1.5"/>
          <path d="M7 4v3l2 1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        监测设备
      </div>
      <el-select v-model="selectedDroneId" size="small" style="width: 140px;">
        <el-option
          v-for="drone in droneList"
          :key="drone.id"
          :label="drone.name"
          :value="drone.id"
        >
          <div class="drone-option-inner">
            <span>{{ drone.name }}</span>
            <span class="drone-type-tag">{{ drone.type }}</span>
          </div>
        </el-option>
      </el-select>
    </div>

    <!-- Charts Grid -->
    <template v-if="props.chartType !== 'all'">
      <div v-if="shouldShowChart('battery')" class="chart-unit">
        <div id="battery-chart" class="chart-canvas"></div>
        <div v-if="chartsLoading.battery" class="chart-skeleton">
          <div class="premium-skeleton" style="height: 100%;"></div>
        </div>
      </div>
      <div v-if="shouldShowChart('signal')" class="chart-unit">
        <div id="signal-chart" class="chart-canvas"></div>
        <div v-if="chartsLoading.signal" class="chart-skeleton">
          <div class="premium-skeleton" style="height: 100%;"></div>
        </div>
      </div>
      <div v-if="shouldShowChart('speed')" class="chart-unit">
        <div id="speed-chart" class="chart-canvas"></div>
        <div v-if="chartsLoading.speed" class="chart-skeleton">
          <div class="premium-skeleton" style="height: 100%;"></div>
        </div>
      </div>
      <div v-if="shouldShowChart('person')" class="chart-unit">
        <div id="recognition-chart" class="chart-canvas"></div>
        <div v-if="chartsLoading.recognition" class="chart-skeleton">
          <div class="premium-skeleton" style="height: 100%;"></div>
        </div>
      </div>
      <div v-if="shouldShowChart('personActivity')" class="chart-unit">
        <div id="person-activity-chart" class="chart-canvas"></div>
        <div v-if="chartsLoading.personActivity" class="chart-skeleton">
          <div class="premium-skeleton" style="height: 100%;"></div>
        </div>
      </div>
      <div v-if="shouldShowChart('task')" class="chart-unit">
        <div id="task-chart" class="chart-canvas"></div>
        <div v-if="chartsLoading.task" class="chart-skeleton">
          <div class="premium-skeleton" style="height: 100%;"></div>
        </div>
      </div>
      <div v-if="shouldShowChart('risk')" class="chart-unit">
        <div id="risk-chart" class="chart-canvas"></div>
        <div v-if="chartsLoading.risk" class="chart-skeleton">
          <div class="premium-skeleton" style="height: 100%;"></div>
        </div>
      </div>
    </template>

    <!-- Full Dashboard Mode -->
    <template v-else>
      <div class="charts-grid-premium">
        <div class="grid-item-premium">
          <div id="battery-chart" class="chart-canvas-full"></div>
          <div v-if="chartsLoading.battery" class="chart-skeleton"><div class="premium-skeleton" style="height: 100%;"></div></div>
        </div>
        <div class="grid-item-premium">
          <div id="signal-chart" class="chart-canvas-full"></div>
          <div v-if="chartsLoading.signal" class="chart-skeleton"><div class="premium-skeleton" style="height: 100%;"></div></div>
        </div>
        <div class="grid-item-premium">
          <div id="speed-chart" class="chart-canvas-full"></div>
          <div v-if="chartsLoading.speed" class="chart-skeleton"><div class="premium-skeleton" style="height: 100%;"></div></div>
        </div>
        <div class="grid-item-premium">
          <div id="recognition-chart" class="chart-canvas-full"></div>
          <div v-if="chartsLoading.recognition" class="chart-skeleton"><div class="premium-skeleton" style="height: 100%;"></div></div>
        </div>
        <div class="grid-item-premium">
          <div id="risk-chart" class="chart-canvas-full"></div>
          <div v-if="chartsLoading.risk" class="chart-skeleton"><div class="premium-skeleton" style="height: 100%;"></div></div>
        </div>
        <div class="grid-item-premium">
          <div id="task-chart" class="chart-canvas-full"></div>
          <div v-if="chartsLoading.task" class="chart-skeleton"><div class="premium-skeleton" style="height: 100%;"></div></div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.premium-charts-root {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Drone Selector */
.drone-selector-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.35);
  border-radius: 12px;
  border: 1px solid rgba(200, 160, 100, 0.15);
}

.selector-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-family: 'Inter', sans-serif;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.selector-label svg {
  color: var(--accent-primary);
}

.drone-option-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.drone-type-tag {
  font-size: 0.7rem;
  color: var(--text-tertiary);
  background: rgba(200, 160, 100, 0.12);
  padding: 1px 6px;
  border-radius: 6px;
}

/* Chart Units */
.chart-unit {
  width: 100%;
  height: 100%;
  position: relative;
  min-height: 280px;
}

.chart-canvas {
  width: 100%;
  height: 100%;
  min-height: 280px;
}

/* Full Dashboard Grid */
.charts-grid-premium {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 16px;
  width: 100%;
  flex: 1;
  min-height: 500px;
}

.grid-item-premium {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  min-height: 220px;
}

.chart-canvas-full {
  width: 100%;
  height: 100%;
  min-height: 220px;
}

.chart-skeleton {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  overflow: hidden;
}

/* Responsive */
@media (max-width: 1200px) {
  .charts-grid-premium { grid-template-columns: repeat(2, 1fr); grid-auto-rows: minmax(220px, auto); }
}

@media (max-width: 768px) {
  .charts-grid-premium { grid-template-columns: 1fr; }
  .chart-canvas { min-height: 220px; }
}

/* Element Plus override for select in this component */
:deep(.el-select) {
  --el-select-border-color-hover: var(--accent-primary) !important;
}

:deep(.el-select__wrapper) {
  background: rgba(255, 255, 255, 0.50) !important;
  border-radius: 10px !important;
  min-height: 30px !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.82rem !important;
  box-shadow: none !important;
}

:deep(.el-select__wrapper:hover) {
  background: rgba(255, 255, 255, 0.70) !important;
}

:deep(.el-select-dropdown__item) {
  font-family: 'Inter', sans-serif !important;
  font-size: 0.85rem !important;
}
</style>
