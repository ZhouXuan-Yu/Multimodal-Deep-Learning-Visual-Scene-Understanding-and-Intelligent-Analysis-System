<template>
  <div class="route-records">
    <h1 class="page-title">我的路线记录</h1>
    
    <el-empty v-if="routeRecords.length === 0" description="暂无路线记录">
      <el-button type="primary" @click="navigateToRoutePlanning">去规划路线</el-button>
    </el-empty>
    
    <div v-else class="records-container">
      <el-collapse v-model="activeNames">
        <el-collapse-item 
          v-for="(recordGroup, groupIndex) in routeRecords" 
          :key="groupIndex"
          :name="groupIndex.toString()"
        >
          <template #title>
            <div class="record-group-title">
              <span class="group-date">{{ formatDate(recordGroup.timestamp) }}</span>
              <el-tag size="small" type="info">{{ recordGroup && recordGroup.routes && recordGroup.routes.length || 0 }}条路线</el-tag>
            </div>
          </template>
          
          <div class="record-list">
            <el-card 
              v-for="(record, index) in recordGroup.routes" 
              :key="index"
              class="record-card"
              shadow="hover"
            >
              <div class="record-header">
                <h3 class="record-title">
                  {{ record.routeInfo.start_point }} → {{ record.routeInfo.end_point }}
                </h3>
                <div class="record-time">{{ formatTime(record.timestamp) }}</div>
              </div>
              
              <div class="record-details">
                <div class="detail-item">
                  <el-icon><Timer /></el-icon>
                  <span>{{ record.routeInfo.duration || '--' }}分钟</span>
                </div>
                <div class="detail-item">
                  <el-icon><Place /></el-icon>
                  <span>{{ record.routeInfo.distance || '--' }}公里</span>
                </div>
                <div class="detail-item" v-if="record.routeInfo.toll">
                  <el-icon><Money /></el-icon>
                  <span>{{ record.routeInfo.toll || '0' }}元</span>
                </div>
              </div>
              
              <div class="waypoints" v-if="record.routeInfo.waypoints && record.routeInfo.waypoints.length > 0">
                <div class="waypoints-title">途经点：</div>
                <div class="waypoints-list">
                  {{ record.routeInfo.waypoints.join(' → ') }}
                </div>
              </div>
              
              <div class="chat-preview">
                <div class="preview-title">对话记录：</div>
                <el-scrollbar max-height="150px">
                  <div 
                    v-for="(message, msgIndex) in record.chatHistory" 
                    :key="msgIndex"
                    :class="['chat-message', message.role]"
                  >
                    <div class="message-content">{{ truncateText(message.content, 100) }}</div>
                  </div>
                </el-scrollbar>
              </div>
              
              <div class="record-actions">
                <el-button 
                  type="primary" 
                  size="small"
                  @click="viewRouteDetails(record)"
                >
                  查看详情
                </el-button>
                <el-button 
                  type="danger" 
                  size="small"
                  @click="deleteRecord(groupIndex, index)"
                >
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMainStore } from '@/stores'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Timer, Place, Money } from '@element-plus/icons-vue'

const router = useRouter()
const store = useMainStore()
const routeRecords = ref([])
const activeNames = ref(['0']) // 默认展开第一组

// 从本地存储加载路线记录
const loadRouteRecords = () => {
  try {
    const records = localStorage.getItem('routeRecords')
    if (records) {
      const parsedRecords = JSON.parse(records)
      
      // 验证解析出的数据是否有效
      if (Array.isArray(parsedRecords)) {
        // 过滤不符合数据结构的记录
        routeRecords.value = parsedRecords.filter(group => {
          // 检查组是否有效且包含routes数组
          if (!group || typeof group !== 'object' || !Array.isArray(group.routes)) {
            return false
          }
          
          // 检查每个路线是否有效
          group.routes = group.routes.filter(route => 
            route && typeof route === 'object' && route.routeInfo
          )
          
          // 只保留有路线的组
          return group.routes.length > 0
        })
        
      // 确保按时间倒序排列
      routeRecords.value.sort((a, b) => b.timestamp - a.timestamp)
      } else {
        console.error('路线记录格式无效')
        routeRecords.value = []
        // 清除无效数据
        localStorage.removeItem('routeRecords')
      }
    } else {
      routeRecords.value = []
    }
  } catch (error) {
    console.error('加载路线记录失败:', error)
    ElMessage.error('加载路线记录失败')
    routeRecords.value = []
    // 清除可能损坏的数据
    localStorage.removeItem('routeRecords')
  }
}

// 格式化日期 (YYYY-MM-DD)
const formatDate = (timestamp) => {
  const date = new Date(timestamp)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

// 格式化时间 (HH:MM:SS)
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

// 截断文本
const truncateText = (text, maxLength) => {
  if (!text) return ''
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
}

// 查看路线详情
const viewRouteDetails = (record) => {
  // 将选中的记录保存到store中
  store.setSelectedRouteRecord(record)
  // 导航到路径规划页面并加载该记录
  router.push('/route-planning?loadRecord=true')
}

// 删除记录
const deleteRecord = (groupIndex, recordIndex) => {
  ElMessageBox.confirm('确定要删除这条路线记录吗？', '删除确认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    // 检查路线记录和组是否存在
    if (!routeRecords.value || routeRecords.value.length <= groupIndex) {
      ElMessage.error('路线记录不存在')
      return
    }
    
    const group = routeRecords.value[groupIndex]
    if (!group || !group.routes || group.routes.length <= recordIndex) {
      ElMessage.error('路线记录不存在')
      return
    }
    
    // 删除指定记录
    group.routes.splice(recordIndex, 1)
    
    // 如果组内没有路线了，删除整个组
    if (group.routes.length === 0) {
      routeRecords.value.splice(groupIndex, 1)
    }
    
    // 更新本地存储
    localStorage.setItem('routeRecords', JSON.stringify(routeRecords.value))
    ElMessage.success('删除成功')
  }).catch(() => {
    // 取消删除
  })
}

// 导航到路径规划页面
const navigateToRoutePlanning = () => {
  router.push('/route-planning')
}

onMounted(() => {
  loadRouteRecords()
})
</script>

<style scoped>
.route-records {
  padding: 20px;
}

.page-title {
  margin-bottom: 24px;
  color: var(--el-color-primary);
}

.records-container {
  max-width: 1200px;
}

.record-group-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.group-date {
  font-weight: 500;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.record-card {
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
}

.record-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.record-title {
  margin: 0;
  font-size: 16px;
  color: var(--el-color-primary);
}

.record-time {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.record-details {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--el-text-color-regular);
}

.waypoints {
  margin-bottom: 16px;
}

.waypoints-title {
  font-weight: 500;
  margin-bottom: 4px;
  color: var(--el-text-color-regular);
}

.waypoints-list {
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.chat-preview {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 16px;
}

.preview-title {
  font-weight: 500;
  margin-bottom: 8px;
  color: var(--el-text-color-regular);
}

.chat-message {
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.chat-message:last-child {
  border-bottom: none;
}

.chat-message.user {
  text-align: right;
  color: var(--el-color-primary);
}

.chat-message.assistant {
  color: var(--el-text-color-primary);
}

.record-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>