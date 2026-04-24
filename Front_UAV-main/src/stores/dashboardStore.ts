/**
 * 文件名: dashboardStore.ts
 * 描述: 数据大屏统一状态管理
 * 作用:
 * - 聚合智眸千析、智程导航、联系我们三模块数据
 * - 提供计算属性生成 ECharts 所需格式
 * - 与 DashboardService 配合完成数据持久化
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import DashboardService, {
  type PersonRecord,
  type RouteRecord,
  type ConsultationRecord,
} from '@/services/DashboardService';

// ============================================================
//  Anomaly Result
// ============================================================
export interface AnomalyResult {
  id: string;
  source: 'recognition' | 'route';
  metric: string;
  value: number;
  threshold: number;
  severity: 'low' | 'medium' | 'high';
  description: string;
  timestamp: number;
}

// ============================================================
//  Dashboard Store
// ============================================================
export const useDashboardStore = defineStore('dashboard', () => {
  // ── 初始化标志 ──
  const initialized = ref(false);

  // ── 人物识别数据 ──
  const personRecords = ref<PersonRecord[]>([]);
  const personStats = computed(() => DashboardService.computePersonStats(personRecords.value));

  // ── 路径规划数据 ──
  const routeRecords = ref<RouteRecord[]>([]);
  const routeStats = computed(() => DashboardService.computeRouteStats(routeRecords.value));

  // ── 咨询数据 ──
  const consultationRecords = ref<ConsultationRecord[]>([]);
  const consultationStats = computed(() =>
    DashboardService.computeConsultationStats(consultationRecords.value)
  );

  // ── 数据分析结果 ──
  const anomalies = ref<AnomalyResult[]>([]);

  // ── AI洞察 ──
  const insights = ref<any[]>([]);

  // ── 最近更新时间 ──
  const lastUpdate = ref<number | null>(null);

  // ============================================================
  //  初始化
  // ============================================================
  function init() {
    if (initialized.value) return;

    // 初始化模拟数据（首次加载时）
    DashboardService.initializeSimulatedData();

    // 从 localStorage 加载数据
    personRecords.value = DashboardService.getPersonRecords();
    routeRecords.value = DashboardService.getRouteRecords();
    consultationRecords.value = DashboardService.getConsultationRecords();

    // 执行初始数据分析
    runAnomalyDetection();

    initialized.value = true;
    lastUpdate.value = Date.now();
  }

  // ============================================================
  //  人物识别
  // ============================================================
  function addPersonRecord(
    record: Omit<PersonRecord, 'id' | 'timestamp'>
  ): PersonRecord {
    const full = DashboardService.addPersonRecord(record);
    personRecords.value = DashboardService.getPersonRecords();
    runAnomalyDetection();
    lastUpdate.value = Date.now();
    return full;
  }

  // ============================================================
  //  路径规划
  // ============================================================
  function addRouteRecord(
    record: Omit<RouteRecord, 'id' | 'timestamp'>
  ): RouteRecord {
    const full = DashboardService.addRouteRecord(record);
    routeRecords.value = DashboardService.getRouteRecords();
    lastUpdate.value = Date.now();
    return full;
  }

  // ============================================================
  //  智能咨询
  // ============================================================
  function addConsultationRecord(
    record: Omit<ConsultationRecord, 'id' | 'timestamp'>
  ): ConsultationRecord {
    const full = DashboardService.addConsultationRecord(record);
    consultationRecords.value = DashboardService.getConsultationRecords();
    lastUpdate.value = Date.now();
    return full;
  }

  // ============================================================
  //  数据分析
  // ============================================================
  function runAnomalyDetection() {
    const results: AnomalyResult[] = [];
    const now = Date.now();

    // 识别置信度异常（近1小时）
    const recentPersons = personRecords.value.filter(
      r => now - r.timestamp < 3600 * 1000
    );
    if (recentPersons.length > 0) {
      const avgConf = recentPersons.reduce((s, r) => s + r.confidence, 0) / recentPersons.length;
      if (avgConf < 0.7) {
        results.push({
          id: `recognition-conf-${now}`,
          source: 'recognition',
          metric: 'confidence',
          value: avgConf,
          threshold: 0.7,
          severity: avgConf < 0.6 ? 'high' : 'medium',
          description: `近期识别平均置信度过低 (${(avgConf * 100).toFixed(1)}%)`,
          timestamp: now,
        });
      }
    }

    // 路线规划异常检测（耗时超过2小时且距离<50km可能异常）
    const recentRoutes = routeRecords.value.filter(
      r => now - r.timestamp < 24 * 3600 * 1000
    );
    recentRoutes.forEach(r => {
      if (r.duration > 120 && parseFloat(r.distance) < 50) {
        results.push({
          id: `route-duration-${r.id}`,
          source: 'route',
          metric: 'duration',
          value: r.duration,
          threshold: 120,
          severity: 'low',
          description: `路线 ${r.startPoint} → ${r.endPoint} 耗时异常 (${r.duration}min, 距离${r.distance}km)`,
          timestamp: r.timestamp,
        });
      }
    });

    anomalies.value = results;
    return results;
  }

  // ============================================================
  //  全量刷新
  // ============================================================
  function refresh() {
    personRecords.value = DashboardService.getPersonRecords();
    routeRecords.value = DashboardService.getRouteRecords();
    consultationRecords.value = DashboardService.getConsultationRecords();
    runAnomalyDetection();
    lastUpdate.value = Date.now();
  }

  // ============================================================
  //  销毁
  // ============================================================
  function destroy() {
    initialized.value = false;
  }

  return {
    // State
    personRecords,
    routeRecords,
    consultationRecords,
    anomalies,
    insights,
    lastUpdate,
    // Computed stats
    personStats,
    routeStats,
    consultationStats,
    // Actions
    init,
    refresh,
    addPersonRecord,
    addRouteRecord,
    addConsultationRecord,
    runAnomalyDetection,
    destroy,
  };
});
