<template>
  <div class="route-records">
    <div class="records-header">
      <h2 class="title">我的路线记录</h2>
      <el-button @click="$emit('switch-tab', 'planning')" type="primary" size="small">
        <el-icon><ArrowLeft /></el-icon>
        返回规划
      </el-button>
    </div>
    
    <!-- 空状态 -->
    <el-empty v-if="!records || records.length === 0" description="暂无路线记录">
      <el-button type="primary" @click="$emit('switch-tab', 'planning')">开始规划路线</el-button>
    </el-empty>
    
    <!-- 记录列表 -->
    <div v-else class="records-list">
      <el-collapse v-model="activeGroups">
        <el-collapse-item 
          v-for="(group, groupIndex) in records" 
          :key="groupIndex"
          :name="groupIndex.toString()"
        >
          <template #title>
            <div class="group-header">
              <span><el-icon><Calendar /></el-icon> {{ formatDate(group.timestamp) }}</span>
              <el-tag size="small" type="info">{{ group.routes.length }}条路线</el-tag>
            </div>
          </template>
          
          <div class="group-content">
            <el-card
              v-for="(record, index) in group.routes"
              :key="index"
              class="record-card"
              shadow="hover"
            >
              <div class="record-header">
                <div class="record-title">
                  <h3>
                    {{ record.routeInfo.start_point ? record.routeInfo.start_point.name || record.routeInfo.start_point : '起点' }}
                    <span class="text-gray-400 mx-2">→</span>
                    {{ record.routeInfo.end_point ? record.routeInfo.end_point.name || record.routeInfo.end_point : '终点' }}
                  </h3>
                  <span class="record-time">{{ formatTime(record.timestamp) }}</span>
                </div>
              </div>
              
              <div class="record-details">
                <div class="detail-item">
                  <el-icon><Timer /></el-icon>
                  <span>{{ record.routeInfo.duration || '--' }} 分钟</span>
                </div>
                <div class="detail-item">
                  <el-icon><Location /></el-icon>
                  <span>{{ record.routeInfo.distance || '--' }} 公里</span>
                </div>
              </div>
              
              <div v-if="record.routeInfo.waypoints && record.routeInfo.waypoints.length > 0" class="waypoints">
                <div class="waypoints-label">途经点:</div>
                <div class="waypoints-content">
                  <el-tag 
                    v-for="(point, i) in record.routeInfo.waypoints" 
                    :key="i"
                    size="small"
                    class="waypoint-tag"
                  >
                    {{ point.name || point }}
                  </el-tag>
                </div>
              </div>
              
              <div class="record-actions">
                <el-button 
                  type="primary" 
                  size="small"
                  @click="loadRoute(group, record)"
                >
                  <el-icon><StarFilled /></el-icon>
                  加载此路线
                </el-button>
                <el-button 
                  type="danger" 
                  size="small"
                  @click="deleteRoute(groupIndex, index)"
                >
                  <el-icon><Delete /></el-icon>
                  删除记录
                </el-button>
              </div>
            </el-card>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { Calendar, Location, Timer, Delete, StarFilled, ArrowLeft } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';

// 定义组件事件
const emit = defineEmits(['switch-tab', 'load-route']);

// 记录数据和活跃分组
const records = ref([]);
const activeGroups = ref(['0']); // 默认展开第一组

// 格式化日期：YYYY年MM月DD日
const formatDate = (timestamp) => {
  const date = new Date(timestamp);
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
};

// 格式化时间：HH:MM
const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

// 加载路线记录
const loadRecords = () => {
  try {
    const savedRecords = localStorage.getItem('routeRecords');
    if (savedRecords) {
      records.value = JSON.parse(savedRecords);
  } else {
      records.value = [];
  }
  } catch (error) {
    console.error('加载路线记录失败:', error);
    ElMessage.error('加载路线记录失败');
    records.value = [];
  }
};

// 加载已选择的路线
const loadRoute = (group, record) => {
  try {
    emit('load-route', { group, route: record });
  } catch (error) {
    console.error('加载路线失败:', error);
    ElMessage.error('加载路线失败');
  }
};

// 删除路线记录
const deleteRoute = (groupIndex, recordIndex) => {
  ElMessageBox.confirm('确定要删除此路线记录吗？此操作不可恢复', '删除确认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    try {
      // 删除指定记录
      records.value[groupIndex].routes.splice(recordIndex, 1);
    
      // 如果组中没有更多记录，删除整个组
      if (records.value[groupIndex].routes.length === 0) {
        records.value.splice(groupIndex, 1);
    }
    
      // 更新本地存储
      localStorage.setItem('routeRecords', JSON.stringify(records.value));
      
      ElMessage.success('路线记录已删除');
    } catch (error) {
      console.error('删除路线记录失败:', error);
      ElMessage.error('删除路线记录失败');
    }
  }).catch(() => {
    // 用户取消删除，不做任何操作
  });
};

// 组件挂载时加载记录
onMounted(() => {
  loadRecords();
});

// 暴露给父组件的方法
defineExpose({
  loadRecords
});
</script>

<style scoped>
.route-records {
  padding: 1rem;
}

.records-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.records-list {
  margin-top: 1rem;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.group-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.5rem 0;
}

.record-card {
  border: 1px solid #eaeaea;
  border-radius: 8px;
  transition: all 0.2s;
}

.record-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.record-header {
  margin-bottom: 0.75rem;
}

.record-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.record-title h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #333;
}

.record-time {
  font-size: 0.875rem;
  color: #666;
}

.record-details {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 0.75rem;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: #666;
}

.waypoints {
  margin-bottom: 0.75rem;
}

.waypoints-label {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.waypoints-content {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.waypoint-tag {
  margin-right: 0.25rem;
}

.record-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
</style>
