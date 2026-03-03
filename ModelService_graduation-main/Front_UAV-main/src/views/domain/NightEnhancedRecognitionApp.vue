<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import BasePage from './templates/BasePage.vue';

// 直接导入前端项目2的组件和API
import NightDetectionView from './src/views/NightDetectionView.vue';
import { nightDetectionApi } from './src/api/nightDetection';
import request from './src/utils/request';

// 页面标题
const title = '夜间增强识别';

// 调试信息记录器
const apiLogs = ref([]);
const isDebugMode = ref(process.env.NODE_ENV === 'development');

// 记录API调用日志的函数
const logApiCall = (direction, data) => {
  if (isDebugMode.value) {
    apiLogs.value.push({
      timestamp: new Date().toISOString(),
      direction,
      data
    });
    console.log(`[API ${direction}]`, data);
  }
};

// 挂载API请求拦截器，用于记录请求和响应
onMounted(() => {
  // 确保端口配置正确 - 统一使用8081端口
  if (request.defaults && request.defaults.baseURL) {
    console.log('当前API基础URL:', request.defaults.baseURL);
    // 确保baseURL使用正确的端口
    if (!request.defaults.baseURL.includes('8081')) {
      console.warn('API基础URL可能配置错误，当前值:', request.defaults.baseURL);
    }
  }
  
  // 添加请求拦截器
  if (request.interceptors) {
    const reqInterceptor = request.interceptors.request.use(
      config => {
        logApiCall('请求', {
          url: config.url,
          method: config.method?.toUpperCase(),
          data: config.data,
          params: config.params
        });
        return config;
      },
      error => {
        logApiCall('请求错误', error);
        return Promise.reject(error);
      }
    );
    
    // 添加响应拦截器
    const resInterceptor = request.interceptors.response.use(
      response => {
        logApiCall('响应', {
          status: response.status,
          data: response.data,
          headers: response.headers
        });
        return response;
      },
      error => {
        logApiCall('响应错误', {
          message: error.message,
          status: error.response?.status,
          data: error.response?.data
        });
        return Promise.reject(error);
      }
    );
  }
});

// 清理资源
onUnmounted(() => {
  // 清理拦截器和其他资源如果需要
});
</script>

<template>
  <BasePage :title="title">
    <div class="night-enhanced-container">
      <!-- 应用介绍 -->
      <section class="app-intro">
        <div class="intro-content">
          <h2 class="intro-title">夜间增强识别功能</h2>
          <p class="intro-text">结合了先进的光学成像和人工智能算法，使无人机能够在低光环境下进行高精度的目标识别和跟踪，提高夜间监控的效果和精度。</p>
        </div>
      </section>

      <!-- 直接使用前端项目2的夜间增强检测组件 -->
      <div class="detection-wrapper">
        <NightDetectionView />
      </div>
      
      <!-- 调试面板 - 只在开发模式下显示 -->
      <div v-if="isDebugMode" class="debug-panel">
        <details>
          <summary>调试信息面板</summary>
          <div class="debug-content">
            <h4>API 通信日志</h4>
            <div v-if="apiLogs.length > 0" class="api-logs">
              <div v-for="(log, index) in apiLogs" :key="index" class="log-entry">
                <span class="log-time">{{ new Date(log.timestamp).toLocaleTimeString() }}</span>
                <span :class="['log-type', `log-${log.direction}`]">{{ log.direction }}</span>
                <pre class="log-data">{{ JSON.stringify(log.data, null, 2) }}</pre>
          </div>
        </div>
            <div v-else class="no-logs">暂无API通信日志</div>
          </div>
        </details>
      </div>
    </div>
  </BasePage>
</template>

<style scoped>
.night-enhanced-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding-top: 1.5rem; /* 添加顶部边距，避免被导航栏遮挡 */
}

.app-intro {
  position: relative;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(8px);
  border-radius: 1rem;
  overflow: hidden;
  margin-bottom: 1.5rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.intro-content {
  position: relative;
  padding: 2rem;
  z-index: 2;
}

.app-intro::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.15), rgba(0, 210, 170, 0.15));
  z-index: 1;
}

.intro-title {
  font-size: 1.75rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 1rem;
  background: linear-gradient(90deg, #4f46e5, #00d2aa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.intro-text {
  color: #4b5563;
  line-height: 1.6;
  font-size: 1.1rem;
}

.detection-wrapper {
  position: relative;
  flex-grow: 1;
  overflow: hidden;
  border-radius: 1rem;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.detection-wrapper:hover {
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
  transform: translateY(-3px);
}

/* 保持NightDetectionView原有样式不受影响 */
:deep(.night-detection-view) {
  height: auto !important;
  min-height: 600px;
  flex-grow: 1;
  background: transparent !important;
}

:deep(.el-container) {
  background: transparent !important;
}

:deep(.upload-area) {
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.05);
  border: 2px dashed rgba(79, 70, 229, 0.3);
}

:deep(.upload-area:hover) {
  background: rgba(79, 70, 229, 0.08);
  border-color: #4f46e5;
  transform: scale(1.01);
}

:deep(.el-button) {
  transition: all 0.3s ease;
}

:deep(.el-button:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* 调试面板样式 */
.debug-panel {
  position: fixed;
  bottom: 0;
  right: 0;
  z-index: 9999;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  border-top-left-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  max-width: 500px;
  max-height: 300px;
  overflow: auto;
  font-size: 12px;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.1);
}

.debug-panel summary {
  padding: 10px 14px;
  cursor: pointer;
  background: rgba(240, 240, 240, 0.8);
  font-weight: bold;
  user-select: none;
  border-top-left-radius: 12px;
}

.debug-content {
  padding: 12px;
}

.api-logs {
  max-height: 250px;
  overflow-y: auto;
}

.log-entry {
  margin-bottom: 10px;
  border-bottom: 1px dashed #eee;
  padding-bottom: 10px;
}

.log-time {
  color: #888;
  margin-right: 8px;
}

.log-type {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  margin-right: 8px;
  font-weight: 500;
}

.log-请求 {
  background: #e6f7ff;
  color: #1890ff;
}

.log-响应 {
  background: #f6ffed;
  color: #52c41a;
}

.log-请求错误, .log-响应错误 {
  background: #fff2f0;
  color: #ff4d4f;
}

.log-data {
  margin-top: 6px;
  white-space: pre-wrap;
  word-break: break-word;
  background: #f5f5f5;
  padding: 8px;
  border-radius: 6px;
  max-height: 150px;
  overflow: auto;
  font-family: monospace;
}

.no-logs {
  color: #999;
  font-style: italic;
}

/* 添加响应式适配 */
@media (max-width: 768px) {
  .night-enhanced-container {
    padding: 1rem;
    padding-top: 1.5rem;
  }
  
  .intro-title {
    font-size: 1.4rem;
  }
  
  .intro-text {
    font-size: 1rem;
  }
  
  .debug-panel {
    max-width: 100%;
    right: 0;
    left: 0;
    border-radius: 0;
  }
}
</style>