<template>
  <div class="module-overview">
    <div class="module-grid">
      <div class="module-card premium-glass animate-glass-restore" @click="$emit('navigate', 'geo')">
        <div class="module-icon" style="background: linear-gradient(135deg, #7BA7C2 0%, #5A8BA6 100%);">
          <el-icon><Location /></el-icon>
        </div>
        <div class="module-info">
          <div class="module-name">地理服务API</div>
          <div class="module-desc">POI搜索、路径规划与地理数据可视化</div>
          <div class="module-stats">
            <span class="stat-item">
              <span class="stat-dot dot-blue"></span>
              高德地图集成
            </span>
            <span class="stat-item">
              <span class="stat-dot dot-green"></span>
              实时地理分析
            </span>
          </div>
        </div>
        <div class="module-arrow">
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>

      <div class="module-card premium-glass animate-glass-restore" @click="$emit('navigate', 'person')">
        <div class="module-icon" style="background: linear-gradient(135deg, #8FB87A 0%, #6B9B5A 100%);">
          <el-icon><User /></el-icon>
        </div>
        <div class="module-info">
          <div class="module-name">智眸千析</div>
          <div class="module-desc">多维人物属性识别与统计分析</div>
          <div class="module-stats">
            <span class="stat-item">
              <span class="stat-dot dot-green"></span>
              累计识别 {{ personStats.total }} 人
            </span>
            <span class="stat-item">
              <span class="stat-dot dot-blue"></span>
              平均置信度 {{ (personStats.avgConfidence * 100).toFixed(1) }}%
            </span>
          </div>
        </div>
        <div class="module-arrow">
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>

      <div class="module-card premium-glass animate-glass-restore" @click="$emit('navigate', 'route')">
        <div class="module-icon" style="background: linear-gradient(135deg, #E8834A 0%, #C4703A 100%);">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="module-info">
          <div class="module-name">智程导航</div>
          <div class="module-desc">自然语言驱动的智能路径规划</div>
          <div class="module-stats">
            <span class="stat-item">
              <span class="stat-dot dot-green"></span>
              总路线数 {{ routeStats.total }} 条
            </span>
            <span class="stat-item">
              <span class="stat-dot dot-amber"></span>
              总里程 {{ routeStats.totalDistance }} km
            </span>
          </div>
        </div>
        <div class="module-arrow">
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>

      <div class="module-card premium-glass animate-glass-restore" @click="$emit('navigate', 'consultation')">
        <div class="module-icon" style="background: linear-gradient(135deg, #D4A843 0%, #B08830 100%);">
          <el-icon><ChatDotRound /></el-icon>
        </div>
        <div class="module-info">
          <div class="module-name">联系我们</div>
          <div class="module-desc">AI驱动的需求分析与自动邮件</div>
          <div class="module-stats">
            <span class="stat-item">
              <span class="stat-dot dot-green"></span>
              累计咨询 {{ consultationStats.total }} 条
            </span>
            <span class="stat-item">
              <span class="stat-dot dot-amber"></span>
              今日 {{ consultationStats.today }} 条
            </span>
          </div>
        </div>
        <div class="module-arrow">
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <div class="quick-actions premium-glass animate-glass-restore">
      <div class="quick-header">
        <el-icon><Connection /></el-icon>
        <span>快捷功能入口</span>
      </div>
      <div class="quick-links">
        <button class="quick-link" @click="goTo('/path-planning')">
          <el-icon><TrendCharts /></el-icon>
          路径规划
        </button>
        <button class="quick-link" @click="goTo('/person-recognition')">
          <el-icon><User /></el-icon>
          人物识别
        </button>
        <button class="quick-link" @click="goToGeoApi">
          <el-icon><Location /></el-icon>
          地理服务API
        </button>
        <button class="quick-link" @click="goTo('/contact')">
          <el-icon><ChatDotRound /></el-icon>
          联系我们
        </button>
      </div>
    </div>

    <div class="recent-activity premium-glass animate-glass-restore">
      <div class="activity-header">
        <el-icon><Clock /></el-icon>
        <span>最新操作记录</span>
      </div>
      <div class="activity-list">
        <div
          v-for="(item, idx) in recentActivity"
          :key="idx"
          class="activity-item"
          :style="{ animationDelay: (idx * 0.05) + 's' }"
        >
          <div class="activity-icon" :class="'activity-' + item.type">
            <el-icon><component :is="getActivityIcon(item.type)" /></el-icon>
          </div>
          <div class="activity-content">
            <div class="activity-text">{{ item.text }}</div>
            <div class="activity-time">{{ formatTime(item.timestamp) }}</div>
          </div>
        </div>
        <div v-if="recentActivity.length === 0" class="activity-empty">
          <el-icon><Clock /></el-icon>
          <span>暂无操作记录</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { Compass, User, TrendCharts, ChatDotRound, ArrowRight, Connection, Clock, Location } from '@element-plus/icons-vue';
import { useDashboardStore } from '@/stores/dashboardStore';

const router = useRouter();
const store = useDashboardStore();

defineEmits(['navigate']);

const personStats = computed(() => store.personStats);
const routeStats = computed(() => store.routeStats);
const consultationStats = computed(() => store.consultationStats);

const recentActivity = computed(() => {
  const activities: { type: string; text: string; timestamp: number }[] = [];

  store.routeRecords.slice(-3).forEach(r => {
    activities.push({
      type: 'route',
      text: '路径规划: ' + r.startPoint + ' -> ' + r.endPoint + ' (' + r.distance + 'km)',
      timestamp: r.timestamp,
    });
  });

  const recentPersons = store.personRecords.slice(-5);
  if (recentPersons.length > 0) {
    activities.push({
      type: 'person',
      text: '人物识别: 检测到 ' + recentPersons.length + ' 人次',
      timestamp: recentPersons[recentPersons.length - 1].timestamp,
    });
  }

  store.consultationRecords.slice(-3).forEach(c => {
    activities.push({
      type: 'consultation',
      text: '联系我们: ' + c.interestLabel + ' (' + c.name + ')',
      timestamp: c.timestamp,
    });
  });

  return activities.sort((a, b) => b.timestamp - a.timestamp).slice(0, 8);
});

const getActivityIcon = (type: string) => {
  const map: Record<string, any> = {
    route: TrendCharts,
    person: User,
    consultation: ChatDotRound,
    geo: Location,
  };
  return map[type] || Compass;
};

const formatTime = (ts: number) => {
  const diff = Date.now() - ts;
  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
  return new Date(ts).toLocaleDateString('zh-CN');
};

const goTo = (path: string) => {
  router.push(path);
};

const goToGeoApi = () => {
  router.push('/data-dashboard-detail');
};
</script>

<style scoped>
.module-overview { display: flex; flex-direction: column; gap: 20px; }

.module-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }

.module-card {
  padding: 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25,0.1,0.25,1);
  position: relative;
  overflow: hidden;
}

.module-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-gold));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.module-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 36px rgba(180, 120, 60, 0.12);
  background: rgba(255,255,255,0.65);
}

.module-card:hover::before { opacity: 1; }

.module-icon {
  width: 52px; height: 52px;
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.module-icon .el-icon { font-size: 24px; color: white; }

.module-info { flex: 1; min-width: 0; }

.module-name {
  font-family: 'Inter',system-ui; font-size: 1rem; font-weight: 700;
  color: var(--text-primary); margin-bottom: 2px;
}

.module-desc {
  font-family: 'Inter',system-ui; font-size: 0.75rem;
  color: var(--text-tertiary); margin-bottom: 8px;
}

.module-stats { display: flex; gap: 12px; flex-wrap: wrap; }

.stat-item {
  display: inline-flex; align-items: center; gap: 5px;
  font-family: 'Inter',system-ui; font-size: 0.78rem; color: var(--text-secondary);
}

.stat-dot { width: 7px; height: 7px; border-radius: 50%; }
.dot-green { background: #6B9B5A; }
.dot-amber { background: #E8B060; }
.dot-blue { background: #7BA7C2; }

.module-arrow { color: var(--text-tertiary); transition: transform 0.3s ease; }
.module-card:hover .module-arrow { transform: translateX(4px); color: var(--accent-primary); }

.quick-actions { padding: 20px 24px; }
.quick-header { display: flex; align-items: center; gap: 8px; font-family: 'Inter',system-ui; font-weight: 600; font-size: 0.9rem; color: var(--text-primary); margin-bottom: 14px; }
.quick-links { display: flex; gap: 10px; flex-wrap: wrap; }

.quick-link {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 10px 18px;
  background: rgba(255,255,255,0.45);
  border: 1px solid rgba(200,160,100,0.15);
  border-radius: 12px;
  font-family: 'Inter',system-ui; font-size: 0.85rem; font-weight: 500;
  color: var(--text-secondary); cursor: pointer;
  transition: all 0.3s ease;
}
.quick-link:hover { background: rgba(255,255,255,0.70); color: var(--accent-primary); border-color: rgba(200,160,100,0.30); transform: translateY(-1px); }

.recent-activity { padding: 20px 24px; }
.activity-header { display: flex; align-items: center; gap: 8px; font-family: 'Inter',system-ui; font-weight: 600; font-size: 0.9rem; color: var(--text-primary); margin-bottom: 14px; }
.activity-list { display: flex; flex-direction: column; gap: 10px; }

.activity-item {
  display: flex; align-items: center; gap: 12px;
  animation: fadeSlideUp 0.4s ease both;
}

.activity-icon {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.activity-icon .el-icon { font-size: 16px; color: white; }
.activity-route { background: linear-gradient(135deg, #E8834A, #C4703A); }
.activity-person { background: linear-gradient(135deg, #8FB87A, #6B9B5A); }
.activity-consultation { background: linear-gradient(135deg, #D4A843, #B08830); }
.activity-geo { background: linear-gradient(135deg, #7BA7C2, #5A8BA6); }

.activity-content { flex: 1; }
.activity-text { font-family: 'Inter',system-ui; font-size: 0.85rem; color: var(--text-primary); }
.activity-time { font-family: 'Inter',system-ui; font-size: 0.72rem; color: var(--text-tertiary); margin-top: 2px; }

.activity-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 32px; color: var(--text-tertiary); font-family: 'Inter',system-ui; font-size: 0.85rem; }

@keyframes fadeSlideUp { 0% { opacity: 0; transform: translateY(8px); } 100% { opacity: 1; transform: translateY(0); } }

@media (max-width: 900px) { .module-grid { grid-template-columns: 1fr; } }
</style>
