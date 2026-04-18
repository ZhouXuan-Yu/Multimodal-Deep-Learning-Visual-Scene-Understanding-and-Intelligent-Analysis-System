<script setup>
// 导入所需的组件和库
import BasePage from './templates/BasePage.vue';
import RoutePlanningView from './src/views/RoutePlanningView.vue';
import { ref, onMounted } from 'vue';
import { useMainStore } from './src/stores';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Delete, Clock } from '@element-plus/icons-vue';

// 页面标题
const title = '路径规划';

// 获取store实例
const store = useMainStore();

// 路线历史记录
const routeHistory = ref([]);
const showHistoryPanel = ref(false);
const selectedRoute = ref(null);

// 在组件挂载时加载历史记录
onMounted(() => {
  loadRouteHistory();
});

// 加载路线历史记录
const loadRouteHistory = () => {
  routeHistory.value = store.getRouteRecords() || [];
};

// 查看历史记录详情
const viewRouteDetails = (route) => {
  selectedRoute.value = route;
};

// 加载选中的路线
const loadSelectedRoute = (route) => {
  store.setSelectedRouteRecord(route);
  // 关闭历史面板
  showHistoryPanel.value = false;
  // 重定向到带有加载记录标识的路径规划页面
  ElMessage.success('正在加载路线记录...');
  // 由于是在同一组件内，我们使用事件通知子组件加载记录
  store.loadSelectedRecord = true;
  selectedRoute.value = null;
};

// 删除路线记录
const deleteRoute = (route) => {
  ElMessageBox.confirm(
    '确定要删除这条路线记录吗？此操作不可恢复。',
    '删除确认',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    store.deleteRouteRecord(route.id);
    loadRouteHistory();
    ElMessage.success('路线记录已删除');
    if (selectedRoute.value && selectedRoute.value.id === route.id) {
      selectedRoute.value = null;
    }
  }).catch(() => {
    // 取消删除，不做任何操作
  });
};

// 格式化日期时间
const formatDateTime = (timestamp) => {
  if (!timestamp) return '未知时间';
  const date = new Date(timestamp);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// 切换历史面板显示
const toggleHistoryPanel = () => {
  showHistoryPanel.value = !showHistoryPanel.value;
  if (showHistoryPanel.value) {
    loadRouteHistory();
  }
};
</script>

<template>
  <BasePage :title="title">
    <div class="route-planning-page">
      <!-- 历史记录按钮 -->
      <div class="history-button-container">
        <el-button 
          type="primary" 
          class="history-button"
          @click="toggleHistoryPanel"
          :icon="Clock"
        >
          {{ showHistoryPanel ? '关闭历史' : '路线历史' }}
        </el-button>
      </div>

      <!-- 历史记录面板 -->
      <div class="history-panel" v-if="showHistoryPanel">
        <div class="history-panel-header">
          <h3>路线规划历史记录</h3>
        </div>
        <div class="history-panel-content">
          <div class="history-list">
            <div v-if="routeHistory.length === 0" class="no-history">
              <p>暂无历史记录</p>
            </div>
            <div 
              v-for="route in routeHistory" 
              :key="route.id"
              class="history-item"
              :class="{ 'selected': selectedRoute && selectedRoute.id === route.id }"
              @click="viewRouteDetails(route)"
            >
              <div class="history-item-info">
                <div class="route-name">{{ route.routeInfo.start_point }} → {{ route.routeInfo.end_point }}</div>
                <div class="route-time">{{ formatDateTime(route.timestamp) }}</div>
                <div class="route-stats">
                  <span>{{ route.routeInfo.distance }}公里</span>
                  <span>{{ route.routeInfo.duration }}分钟</span>
                </div>
              </div>
              <div class="history-item-actions">
                <el-button 
                  type="danger" 
                  size="small" 
                  :icon="Delete"
                  @click.stop="deleteRoute(route)"
                  circle
                ></el-button>
              </div>
            </div>
          </div>
          
          <div class="history-details" v-if="selectedRoute">
            <h4>路线详情</h4>
            <div class="detail-item">
              <span class="label">起点:</span>
              <span class="value">{{ selectedRoute.routeInfo.start_point }}</span>
            </div>
            <div class="detail-item">
              <span class="label">终点:</span>
              <span class="value">{{ selectedRoute.routeInfo.end_point }}</span>
            </div>
            <div class="detail-item">
              <span class="label">距离:</span>
              <span class="value">{{ selectedRoute.routeInfo.distance }}公里</span>
            </div>
            <div class="detail-item">
              <span class="label">时间:</span>
              <span class="value">{{ selectedRoute.routeInfo.duration }}分钟</span>
            </div>
            <div class="detail-item">
              <span class="label">过路费:</span>
              <span class="value">{{ selectedRoute.routeInfo.toll || '0' }}元</span>
            </div>
            <div v-if="selectedRoute.routeInfo.waypoints && selectedRoute.routeInfo.waypoints.length" class="detail-item">
              <span class="label">途经点:</span>
              <span class="value">{{ selectedRoute.routeInfo.waypoints.join(' → ') }}</span>
            </div>
            <div class="detail-actions">
              <el-button type="primary" @click="loadSelectedRoute(selectedRoute)">加载此路线</el-button>
            </div>
          </div>
        </div>
      </div>

      <div class="route-planning-container" :class="{ 'with-history': showHistoryPanel }">
        <!-- 集成RoutePlanningView组件 -->
        <RoutePlanningView />
      </div>
    </div>
  </BasePage>
</template>

<style scoped>
.route-planning-page {
  position: relative;
  width: 100%;
  margin-top: 30px; /* 添加顶部边距，避免被导航栏遮挡 */
}

.route-planning-container {
  width: 100%;
  height: calc(100vh - 80px); /* 进一步增加高度 */
  min-height: 800px; /* 增加最小高度 */
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: width 0.3s ease;
}

.route-planning-container.with-history {
  width: calc(100% - 350px);
  margin-left: 350px;
}

.history-button-container {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1000;
}

.history-panel {
  position: absolute;
  top: 0;
  left: 0;
  width: 330px;
  height: calc(100vh - 80px); /* 调整历史面板的高度 */
  background-color: #f5f7fa;
  border-right: 1px solid #e4e7ed;
  border-radius: 12px 0 0 12px;
  overflow: hidden;
  z-index: 10;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.history-panel-header {
  padding: 15px;
  background-color: #ecf5ff;
  border-bottom: 1px solid #d9ecff;
}

.history-panel-header h3 {
  margin: 0;
  color: #409eff;
  font-weight: 600;
}

.history-panel-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.history-list {
  width: 50%;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
  max-height: 100%;
}

.history-item {
  padding: 12px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: background-color 0.3s;
  display: flex;
  justify-content: space-between;
}

.history-item:hover {
  background-color: #f5f7fa;
}

.history-item.selected {
  background-color: #ecf5ff;
}

.route-name {
  font-weight: 500;
  margin-bottom: 5px;
}

.route-time {
  font-size: 12px;
  color: #909399;
  margin-bottom: 5px;
}

.route-stats {
  font-size: 12px;
  color: #606266;
  display: flex;
  gap: 10px;
}

.history-details {
  width: 50%;
  padding: 15px;
  overflow-y: auto;
}

.history-details h4 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #303133;
}

.detail-item {
  margin-bottom: 10px;
  display: flex;
  flex-direction: column;
}

.label {
  font-weight: 500;
  color: #606266;
  margin-bottom: 5px;
}

.value {
  color: #303133;
}

.detail-actions {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.no-history {
  padding: 20px;
  text-align: center;
  color: #909399;
}
</style>