<template>
  <!-- Premium Background -->
  <div class="premium-page-bg"></div>

  <div class="premium-page premium-mt-nav">
    <!-- ================================================
         NAVBAR
         ================================================ -->
    <nav class="premium-navbar">
      <div class="navbar-inner">
        <div class="navbar-brand">
          <div class="navbar-logo">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <circle cx="16" cy="16" r="14" stroke="url(#logoGrad)" stroke-width="2" fill="none"/>
              <path d="M10 16L16 10L22 16L16 22L10 16Z" fill="url(#logoGrad)" opacity="0.8"/>
              <circle cx="16" cy="16" r="3" fill="url(#logoGrad)"/>
              <defs>
                <linearGradient id="logoGrad" x1="0" y1="0" x2="32" y2="32">
                  <stop offset="0%" stop-color="#E8834A"/>
                  <stop offset="100%" stop-color="#D4A843"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div class="navbar-titles">
            <span class="navbar-title">监控数据大屏</span>
            <span class="navbar-subtitle">智程导航 · 智眸千析 · 智航监控 · 智能咨询</span>
          </div>
        </div>

        <div class="navbar-center">
          <div class="premium-tabs">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              class="premium-tab"
              :class="{ active: activeTab === tab.key }"
              @click="switchTab(tab.key)"
            >
              <el-icon><component :is="tab.icon" /></el-icon>
              {{ tab.label }}
            </button>
          </div>
        </div>

        <div class="navbar-actions">
          <button class="premium-btn-glass" @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
            刷新
          </button>
        </div>
      </div>
    </nav>

    <!-- ================================================
         MAIN CONTENT
         ================================================ -->
    <main class="premium-main">
      <div v-if="loading" class="premium-loading">
        <div class="loading-orb"></div>
        <p class="loading-text">正在加载数据...</p>
      </div>

      <div v-else class="tab-content">
        <ModuleOverview v-if="activeTab === 'overview'" @navigate="switchTab" />

        <!-- 地理服务API：支持两种视图 -->
        <div v-else-if="activeTab === 'geo'" class="geo-wrapper">
          <div class="geo-view-toggle">
            <button
              class="toggle-btn"
              :class="{ active: geoViewMode === 'dashboard' }"
              @click="geoViewMode = 'dashboard'"
            >
              <el-icon><DataAnalysis /></el-icon>
              功能操作台
            </button>
            <button
              class="toggle-btn"
              :class="{ active: geoViewMode === 'stats' }"
              @click="geoViewMode = 'stats'"
            >
              <el-icon><Histogram /></el-icon>
              数据分析报告
            </button>
          </div>
          <GeoApiDashboard v-if="geoViewMode === 'dashboard'" @goto-stats="jumpToGeoStats" />
          <GeoApiStats v-else />
        </div>

        <PersonRecognitionStats v-else-if="activeTab === 'person'" />
        <RoutePlanningStats v-else-if="activeTab === 'route'" />
        <AnomalyDetectionComponent v-else-if="activeTab === 'ai'" />
        <ConsultationStats v-else-if="activeTab === 'consultation'" />
      </div>
    </main>

    <!-- ================================================
         FOOTER
         ================================================ -->
    <footer class="premium-footer premium-glass">
      <div class="footer-inner">
        <div class="footer-brand">
          <svg width="20" height="20" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="14" stroke="url(#footerGrad)" stroke-width="2" fill="none"/>
            <circle cx="16" cy="16" r="3" fill="url(#footerGrad)"/>
            <defs>
              <linearGradient id="footerGrad" x1="0" y1="0" x2="32" y2="32">
                <stop offset="0%" stop-color="#E8834A"/>
                <stop offset="100%" stop-color="#D4A843"/>
              </linearGradient>
            </defs>
          </svg>
          <span>空融智链 · 数据分析大屏</span>
        </div>
        <div class="footer-meta">
          <span class="footer-update">
            <span class="footer-dot"></span>
            系统在线 · 数据更新: {{ lastUpdateStr }}
          </span>
          <span style="color:var(--text-tertiary)">空融智链 · ModelService</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import {
  Refresh, DataAnalysis, Compass, Sunny, Odometer,
  Connection, User, ChatDotRound, TrendCharts, Warning, Location, Histogram
} from '@element-plus/icons-vue';
import { useDashboardStore } from '@/stores/dashboardStore';

// Tab components
import ModuleOverview from '@/components/dashboard/ModuleOverview.vue';
import GeoApiDashboard from '@/components/dashboard/GeoApiDashboard.vue';
import GeoApiStats from '@/components/dashboard/GeoApiStats.vue';
import PersonRecognitionStats from '@/components/dashboard/PersonRecognitionStats.vue';
import RoutePlanningStats from '@/components/dashboard/RoutePlanningStats.vue';
import AnomalyDetectionComponent from '@/components/dashboard/AnomalyDetectionComponent.vue';
import ConsultationStats from '@/components/dashboard/ConsultationStats.vue';

const store = useDashboardStore();
const route = useRoute();
const loading = ref(true);
const activeTab = ref('overview');
const geoViewMode = ref<'dashboard' | 'stats'>('dashboard');

const tabs = [
  { key: 'overview',       label: '模块总览',      icon: Connection },
  { key: 'geo',            label: '地理服务API',    icon: Location },
  { key: 'person',         label: '智眸千析',       icon: User },
  { key: 'route',          label: '智程导航',       icon: TrendCharts },
  { key: 'ai',             label: 'AI数据分析',    icon: DataAnalysis },
  { key: 'consultation',    label: '联系我们',       icon: ChatDotRound },
];

const lastUpdateStr = computed(() => {
  if (!store.lastUpdate) return '—';
  return new Date(store.lastUpdate).toLocaleString('zh-CN');
});

const switchTab = (key: string) => {
  activeTab.value = key;
  if (key !== 'geo') geoViewMode.value = 'dashboard';
};

const jumpToGeoStats = () => {
  geoViewMode.value = 'stats';
  activeTab.value = 'geo';
};

const handleRefresh = () => {
  store.refresh();
  ElMessage({ message: '数据已刷新', type: 'success' });
};

onMounted(() => {
  store.init();
  if (route.query.geoView === 'stats') geoViewMode.value = 'stats';
  setTimeout(() => { loading.value = false; }, 800);
});

onBeforeUnmount(() => {
  store.destroy();
});
</script>

<style scoped>
/* ── Page Layout ── */
.premium-page {
  min-height: 100vh;
  padding-bottom: 32px;
  animation: pageFadeIn 0.6s ease both;
}
@keyframes pageFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.premium-main { max-width: 1920px; margin: 0 auto; padding: 0 28px; }

/* ── Navbar ── */
.navbar-inner { display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.navbar-brand { display: flex; align-items: center; gap: 14px; flex-shrink: 0; }
.navbar-logo {
  display: flex; align-items: center; justify-content: center;
  width: 44px; height: 44px;
  background: rgba(255,255,255,0.6);
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.4);
  box-shadow: 0 2px 12px rgba(232,131,74,0.15);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.navbar-logo:hover { transform: scale(1.08) rotate(5deg); box-shadow: 0 4px 20px rgba(232,131,74,0.30); }
.navbar-titles { display: flex; flex-direction: column; gap: 2px; }
.navbar-title { font-family: 'Inter','SF Pro Display',system-ui; font-weight: 700; font-size: 1.05rem; color: var(--text-primary); letter-spacing: -0.02em; white-space: nowrap; }
.navbar-subtitle { font-family: 'Inter',system-ui; font-size: 0.72rem; color: var(--text-tertiary); letter-spacing: 0.02em; }
.navbar-center { flex: 1; display: flex; justify-content: center; }
.navbar-actions { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

/* ── Tabs ── */
.premium-tabs { display: inline-flex; gap: 4px; background: rgba(255,255,255,0.40); backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px); border: 1px solid var(--glass-border); border-radius: 20px; padding: 5px; }
.premium-tab { display: inline-flex; align-items: center; gap: 7px; padding: 9px 18px; background: transparent; border: none; border-radius: 14px; font-family: 'Inter',system-ui; font-weight: 500; font-size: 0.88rem; color: var(--text-secondary); cursor: pointer; transition: all 0.35s cubic-bezier(0.25,0.1,0.25,1); white-space: nowrap; position: relative; }
.premium-tab:hover { color: var(--text-primary); background: rgba(255,255,255,0.50); transform: translateY(-1px); }
.premium-tab.active {
  background: white;
  color: var(--text-primary);
  font-weight: 600;
  box-shadow: 0 3px 14px rgba(180,120,60,0.14), 0 0 0 1px rgba(232,131,74,0.15);
}
.premium-tab.active::after {
  content: '';
  position: absolute;
  bottom: 4px; left: 50%;
  transform: translateX(-50%);
  width: 20px; height: 3px;
  background: linear-gradient(90deg, #E8834A, #D4A843);
  border-radius: 2px;
}
.premium-tab .el-icon { font-size: 15px; }

/* ── Buttons ── */
.premium-btn-glass { display: inline-flex; align-items: center; gap: 7px; padding: 9px 18px; background: rgba(255,255,255,0.45); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid var(--glass-border); border-radius: 14px; font-family: 'Inter',system-ui; font-weight: 500; font-size: 0.85rem; color: var(--text-secondary); cursor: pointer; transition: all 0.3s ease; }
.premium-btn-glass:hover { background: rgba(255,255,255,0.70); color: var(--text-primary); border-color: rgba(200,160,100,0.35); transform: translateY(-1px); }
.premium-btn-primary { display: inline-flex; align-items: center; gap: 7px; padding: 9px 18px; background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-gold) 100%); border: none; border-radius: 14px; font-family: 'Inter',system-ui; font-weight: 600; font-size: 0.85rem; color: white; cursor: pointer; box-shadow: 0 4px 16px rgba(232,131,74,0.30); transition: all 0.3s ease; }
.premium-btn-primary:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(232,131,74,0.40); }

/* ── Loading ── */
.premium-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: calc(100vh - 120px); gap: 24px; }
.loading-orb { width: 56px; height: 56px; border-radius: 50%; background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-gold) 100%); box-shadow: 0 8px 32px rgba(232,131,74,0.35); animation: orbPulse 1.8s ease-in-out infinite; }
@keyframes orbPulse { 0%,100% { transform: scale(1); box-shadow: 0 8px 32px rgba(232,131,74,0.35); } 50% { transform: scale(1.12); box-shadow: 0 16px 48px rgba(232,131,74,0.50); } }
.loading-text { font-family: 'Inter',system-ui; font-size: 0.95rem; color: var(--text-secondary); margin: 0; animation: textFade 1.5s ease-in-out infinite alternate; }
@keyframes textFade { from { opacity: 0.5; } to { opacity: 1; } }

/* ── Tab Content ── */
.tab-content { margin-top: 24px; }

/* ── Geo Sub-View Toggle ── */
.geo-wrapper { display: flex; flex-direction: column; gap: 16px; }
.geo-view-toggle { display: flex; gap: 6px; padding: 5px; background: rgba(255,255,255,0.40); backdrop-filter: blur(15px); border: 1px solid var(--glass-border); border-radius: 16px; width: fit-content; }
.toggle-btn { display: inline-flex; align-items: center; gap: 7px; padding: 8px 20px; background: transparent; border: none; border-radius: 11px; font-family: 'Inter',system-ui; font-weight: 500; font-size: 0.85rem; color: var(--text-secondary); cursor: pointer; transition: all 0.3s ease; }
.toggle-btn:hover { color: var(--text-primary); background: rgba(255,255,255,0.50); transform: translateY(-1px); }
.toggle-btn.active { background: white; color: var(--text-primary); font-weight: 600; box-shadow: 0 2px 10px rgba(180,120,60,0.10); }
.toggle-btn .el-icon { font-size: 15px; }

/* ── Footer ── */
.premium-footer { margin: 32px 28px 0; border-radius: 24px; padding: 18px 28px; }
.footer-inner { display: flex; justify-content: space-between; align-items: center; }
.footer-brand { display: flex; align-items: center; gap: 10px; font-family: 'Inter',system-ui; font-size: 0.85rem; color: var(--text-secondary); }
.footer-meta { font-family: 'Inter',system-ui; font-size: 0.82rem; color: var(--text-tertiary); display: flex; gap: 20px; align-items: center; }
.footer-update { display: inline-flex; align-items: center; gap: 6px; }
.footer-dot { width: 8px; height: 8px; border-radius: 50%; background: #52c41a; display: inline-block; animation: dotPulse 2s ease-in-out infinite; }
@keyframes dotPulse { 0%,100% { opacity: 1; box-shadow: 0 0 0 0 rgba(82,196,26,0.4); } 50% { opacity: 0.7; box-shadow: 0 0 0 4px rgba(82,196,26,0); } }

/* ── Responsive ── */
@media (max-width: 1400px) { .premium-tabs { flex-wrap: wrap; max-width: 600px; } }
@media (max-width: 1100px) { .navbar-center { display: none; } .navbar-inner { justify-content: space-between; } }
@media (max-width: 768px) { .premium-main { padding: 0 16px; } .premium-footer { margin: 24px 16px 0; } .footer-inner { flex-direction: column; gap: 8px; text-align: center; } }
</style>
