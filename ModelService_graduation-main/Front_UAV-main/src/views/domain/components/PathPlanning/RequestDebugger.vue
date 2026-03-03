<template>
  <div class="request-debugger" :style="showDebugger ? 'display: block' : 'display: none'">
    <div class="debugger-header">
      <h3>API请求调试</h3>
      <el-button type="primary" size="small" @click="toggleDebugger">
        {{ expanded ? '收起' : '展开' }}
      </el-button>
    </div>
    
    <div class="debugger-content" v-if="expanded">
      <!-- 系统信息面板 -->
      <div class="system-info">
        <h4>系统状态</h4>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">高德地图API:</span>
            <span class="info-value" :class="mapApiStatus ? 'success' : 'error'">
              {{ mapApiStatus ? '已加载' : '未加载' }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">API状态:</span>
            <span class="info-value" :class="apiStatus">{{ apiStatusText }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">最近请求:</span>
            <span class="info-value">{{ lastRequestTime || '无' }}</span>
          </div>
        </div>
        
        <!-- 快速操作区 -->
        <div class="quick-actions">
          <el-button size="small" type="primary" @click="checkMapApi">
            检查地图API
          </el-button>
          <el-button size="small" type="success" @click="testConnection">
            测试API连接
          </el-button>
          <el-button size="small" type="danger" @click="clearLogs">
            清除日志
          </el-button>
        </div>
      </div>
      
      <!-- 日志区域 -->
      <div class="request-logs">
        <h4>请求日志 <span class="log-count">({{ logs.length }})</span></h4>
        <div 
          v-for="(log, index) in logs.slice().reverse()" 
          :key="index" 
          class="log-item"
          :class="{ 'request': log.type === 'request', 'response': log.type === 'response', 'error': log.type === 'error', 'info': log.type === 'info' }"
        >
          <div class="log-header">
            <span class="log-type">{{ getLogTypeText(log.type) }}</span>
            <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          </div>
          <div class="log-body">
            <pre>{{ formatLogContent(log) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouteStore } from '../../stores/routeStore'
import { get } from '../../api/request'

const props = defineProps({
  showDebugger: {
    type: Boolean,
    default: false
  }
})

// 组件状态
const expanded = ref(false)
const logs = ref([])
const mapApiStatus = ref(false)
const apiStatus = ref('idle')
const lastRequestTime = ref('')

// 引入store
const routeStore = useRouteStore()

// 计算状态文本
const apiStatusText = computed(() => {
  switch (apiStatus.value) {
    case 'idle': return '空闲'
    case 'loading': return '加载中'
    case 'success': return '成功'
    case 'error': return '错误'
    default: return '未知'
  }
})

// 展开/收起调试面板
const toggleDebugger = () => {
  expanded.value = !expanded.value
}

// 清除日志
const clearLogs = () => {
  logs.value = []
  addInfoLog('日志已清除')
}

// 检查高德地图API
const checkMapApi = () => {
  try {
    if (window.AMap) {
      mapApiStatus.value = true
      
      // 获取API版本和插件信息
      let plugins = []
      if (window.AMap.Driving) plugins.push('Driving')
      if (window.AMap.Geocoder) plugins.push('Geocoder')
      if (window.AMap.TileLayer && window.AMap.TileLayer.Traffic) plugins.push('TileLayer.Traffic')
      if (window.AMap.TileLayer && window.AMap.TileLayer.Satellite) plugins.push('TileLayer.Satellite')
      if (window.AMap.Buildings) plugins.push('Buildings')
      
      addInfoLog(`高德地图API已加载: 版本=${window.AMap.version || '未知'}, 插件=[${plugins.join(', ')}]`)
      ElMessage.success('高德地图API加载正常')
    } else {
      mapApiStatus.value = false
      addErrorLog('高德地图API未加载，请检查网络连接或API密钥配置')
      ElMessage.error('高德地图API未加载')
    }
  } catch (error) {
    mapApiStatus.value = false
    addErrorLog(`检查高德地图API失败: ${error.message || String(error)}`)
    ElMessage.error('检查API失败')
  }
}

// 测试API连接
const testConnection = async () => {
  apiStatus.value = 'loading'
  addInfoLog('测试与后端API的连接...')
  
  try {
    const testRequest = {
      url: 'health',
      method: 'GET'
    }
    
    addRequestLog(testRequest)
    
    const response = await get('health')
    
    apiStatus.value = 'success'
    addResponseLog(response)
    
    ElMessage.success('API连接正常')
  } catch (error) {
    apiStatus.value = 'error'
    addErrorLog(`API连接测试失败: ${error.message}`)
    
    ElMessage.error('API连接失败')
  }
}

// 获取日志类型文本
const getLogTypeText = (type) => {
  switch (type) {
    case 'request': return '请求'
    case 'response': return '响应'
    case 'error': return '错误'
    case 'info': return '信息'
    default: return '日志'
  }
}

// 格式化时间
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}.${date.getMilliseconds().toString().padStart(3, '0')}`
}

// 格式化日志内容
const formatLogContent = (log) => {
  if (typeof log.content === 'string') {
    return log.content
  }
  
  try {
    return JSON.stringify(log.content, null, 2)
  } catch (_) {
    return String(log.content)
  }
}

// 添加请求日志
const addRequestLog = (content) => {
  logs.value.push({
    type: 'request',
    content,
    timestamp: Date.now()
  })
  
  lastRequestTime.value = formatTime(Date.now())
  apiStatus.value = 'loading'
}

// 添加响应日志
const addResponseLog = (content) => {
  logs.value.push({
    type: 'response',
    content,
    timestamp: Date.now()
  })
  
  apiStatus.value = 'success'
}

// 添加错误日志
const addErrorLog = (content) => {
  logs.value.push({
    type: 'error',
    content,
    timestamp: Date.now()
  })
  
  apiStatus.value = 'error'
}

// 添加信息日志
const addInfoLog = (content) => {
  logs.value.push({
    type: 'info',
    content,
    timestamp: Date.now()
  })
}

// 监听调试器显示状态
watch(() => props.showDebugger, (newValue) => {
  if (newValue && !expanded.value) {
    expanded.value = true
  }
})

// 组件挂载
onMounted(() => {
  // 检查高德地图API状态
  if (window.AMap) {
    mapApiStatus.value = true
    addInfoLog('高德地图API已加载')
  } else {
    addInfoLog('等待高德地图API加载...')
    
    // 等待地图API加载
    const checkInterval = setInterval(() => {
      if (window.AMap) {
        mapApiStatus.value = true
        addInfoLog('高德地图API已成功加载')
        clearInterval(checkInterval)
      }
    }, 1000)
    
    // 10秒后如果还未加载则停止检查
    setTimeout(() => {
      if (!mapApiStatus.value) {
        clearInterval(checkInterval)
        addErrorLog('高德地图API加载超时')
      }
    }, 10000)
  }
  
  // 添加初始化日志
  addInfoLog('请求调试器已初始化')
})

// 对外暴露方法
defineExpose({
  addRequestLog,
  addResponseLog,
  addErrorLog,
  addInfoLog,
  clearLogs
})
</script>

<style scoped>
.request-debugger {
  position: fixed;
  bottom: 80px;
  right: 20px;
  width: 420px;
  max-width: 90vw;
  background: var(--el-bg-color-overlay);
  border-radius: 8px;
  box-shadow: var(--el-box-shadow-light);
  z-index: 9999;
  backdrop-filter: blur(10px);
  overflow: hidden;
  border: 1px solid var(--el-border-color);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.debugger-header {
  padding: 10px 16px;
  background: var(--el-color-primary-light-9);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--el-border-color);
}

.debugger-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.debugger-content {
  padding: 16px;
  max-height: calc(80vh - 50px);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.system-info {
  background: var(--el-bg-color);
  border-radius: 4px;
  padding: 12px;
  box-shadow: var(--el-box-shadow-lighter);
}

h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.info-label {
  color: var(--el-text-color-secondary);
}

.info-value {
  font-weight: 500;
}

.info-value.success {
  color: var(--el-color-success);
}

.info-value.error {
  color: var(--el-color-danger);
}

.info-value.loading {
  color: var(--el-color-warning);
}

.info-value.idle {
  color: var(--el-text-color-secondary);
}

.quick-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.request-logs {
  flex: 1;
  min-height: 200px;
  overflow-y: auto;
}

.log-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-weight: normal;
}

.log-item {
  margin-bottom: 12px;
  background: var(--el-bg-color);
  border-radius: 4px;
  overflow: hidden;
  box-shadow: var(--el-box-shadow-lighter);
}

.log-header {
  display: flex;
  justify-content: space-between;
  padding: 6px 12px;
  font-size: 12px;
  color: white;
}

.log-item.request .log-header {
  background-color: var(--el-color-primary);
}

.log-item.response .log-header {
  background-color: var(--el-color-success);
}

.log-item.error .log-header {
  background-color: var(--el-color-danger);
}

.log-item.info .log-header {
  background-color: var(--el-color-info);
}

.log-body {
  padding: 8px 12px;
  font-size: 12px;
  max-height: 300px;
  overflow-y: auto;
  color: var(--el-text-color-regular);
}

.log-body pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
</style> 