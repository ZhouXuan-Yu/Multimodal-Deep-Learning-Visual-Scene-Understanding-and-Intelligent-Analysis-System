<script setup>
import { ref, reactive, onMounted, watch, onUnmounted } from 'vue';
import BasePage from './templates/BasePage.vue';
import DualImageUploader from './components/LongRangeIdentification/DualImageUploader.vue';
import DualVideoUploader from './components/LongRangeIdentification/DualVideoUploader.vue';
import DetectionResults from './components/LongRangeIdentification/DetectionResults.vue';
import rgbtDetectionService from './services/rgbtDetectionService';

// 直接导入前端项目2的组件
import RGBTDetectionView from './src/views/RGBTDetectionView.vue';
import request from './src/utils/request';
// 导入API
import { rgbtDetectionApi } from './src/api/rgbtDetection';

// 页面标题
const title = '远距离目标识别';

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

// 修改RGBTDetectionView中的getFullImageUrl函数
const modifyRGBTDetectionView = () => {
  // 检查是否存在getFullImageUrl函数
  if (!RGBTDetectionView.setup) {
    console.warn('无法修改RGBTDetectionView组件，setup函数不存在');
    return;
  }
  
  // 尝试注入函数
  try {
    // 确保组件中有处理静态资源的函数
    const backendPort = import.meta.env.VITE_BACKEND_PORT || 8081;
    
    // 添加到全局范围以便组件使用
    window.getFullImageUrl = (relativePath) => {
      if (!relativePath) return '';
      
      let fullUrl;
      const backendUrl = `http://localhost:${backendPort}`;
      
      if (relativePath.startsWith('blob:')) {
        // 如果是Blob URL，直接返回
        fullUrl = relativePath;
      } else if (relativePath.startsWith('/static/')) {
        // 静态资源路径，添加完整的后端服务器地址
        fullUrl = `${backendUrl}${relativePath}`;
        
        // 添加时间戳防止缓存
        fullUrl = `${fullUrl}?t=${Date.now()}`;
      } else if (relativePath.startsWith('/')) {
        // 其他带前导斜杠的路径
        fullUrl = `${backendUrl}/api${relativePath}`;
      } else {
        // 无前导斜杠的路径
        fullUrl = `${backendUrl}/api/${relativePath}`;
      }
      
      console.log('图像完整URL:', fullUrl);
      return fullUrl;
    };
    
    console.log('已全局注入getFullImageUrl函数');
  } catch (error) {
    console.error('修改RGBTDetectionView组件失败:', error);
  }
};

// 挂载API请求拦截器，用于记录请求和响应
onMounted(() => {
  // 修改组件中的URL处理方法
  modifyRGBTDetectionView();
  
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
        // 检查并修正URL路径
        if (config.url && config.url.includes('/api/api/')) {
          config.url = config.url.replace('/api/api/', '/api/');
          console.log('修正重复API路径:', config.url);
        }
        
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
  if (window.getFullImageUrl) {
    delete window.getFullImageUrl;
  }
});

// 处理模式 (image/video)
const processingMode = ref('image');

// 通知状态
const notification = reactive({
  show: false,
  message: '',
  type: 'info', // info, success, error
  timeout: null
});

// 图像处理状态
const isImageProcessing = ref(false);
const imageProcessingProgress = ref(0);
const rgbImageFile = ref(null);
const thermalImageFile = ref(null);
const imageResults = ref(null);

// 视频处理状态
const isVideoProcessing = ref(false);
const videoProcessingProgress = ref(0);
const videoProcessingStatus = ref('');
const rgbVideoFile = ref(null);
const thermalVideoFile = ref(null);
const videoTaskId = ref(null);
const videoResults = ref(null);

// 显示通知
const showNotification = (message, type = 'info', duration = 5000) => {
  // 清除之前的超时
  if (notification.timeout) {
    clearTimeout(notification.timeout);
  }
  
  // 设置通知内容
  notification.message = message;
  notification.type = type;
  notification.show = true;
  
  // 设置自动关闭
  notification.timeout = setTimeout(() => {
    notification.show = false;
  }, duration);
};

// 关闭通知
const closeNotification = () => {
  notification.show = false;
  if (notification.timeout) {
    clearTimeout(notification.timeout);
    notification.timeout = null;
  }
};

// 处理错误
const handleError = (message) => {
  showNotification(message, 'error');
};

// 模拟进度更新
const simulateProgress = (progressRef, isProcessingRef, callback) => {
  let progress = 0;
  progressRef.value = progress;
  
  const interval = setInterval(() => {
    if (progress >= 90) {
      clearInterval(interval);
      return;
    }
    
    // 不均匀增加进度，模拟真实处理过程
    const increment = Math.random() * 5 + (progress < 30 ? 5 : (progress < 60 ? 3 : 1));
    progress = Math.min(90, progress + increment);
    progressRef.value = Math.floor(progress);
    
    if (!isProcessingRef.value) {
      clearInterval(interval);
      
      // 如果处理完成，直接设为100%
      if (callback && typeof callback === 'function') {
        progressRef.value = 100;
        callback();
      }
    }
  }, 800);
  
  return interval;
};

// 处理图像文件变更
const handleImageChange = ({ type, file }) => {
  if (type === 'rgb') {
    rgbImageFile.value = file;
  } else if (type === 'thermal') {
    thermalImageFile.value = file;
  }
};

// 移除图像
const handleRemoveImage = (type) => {
  if (type === 'rgb') {
    rgbImageFile.value = null;
  } else if (type === 'thermal') {
    thermalImageFile.value = null;
  }
};

// 清除图像
const handleClearImages = () => {
  rgbImageFile.value = null;
  thermalImageFile.value = null;
};

// 处理图像分析
const handleProcessImages = async (formData) => {
  if (isImageProcessing.value) return;
  
  try {
    isImageProcessing.value = true;
    imageProcessingProgress.value = 0;
    
    // 模拟进度更新
    const progressInterval = simulateProgress(imageProcessingProgress, isImageProcessing, null);
    
    // 调用API处理图像 - 替换为实际的API调用
    // 注意：在实际项目中需要连接到后端API，这里使用模拟数据进行演示
    // const response = await rgbtDetectionService.processImages(formData);
    
    // 模拟网络延迟
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // 模拟API返回结果
    const response = rgbtDetectionService.mockDetectionResult('image');
    
    // 处理完成
    clearInterval(progressInterval);
    imageProcessingProgress.value = 100;
    
    // 保存结果
    imageResults.value = {
      rgb_image: {
        original: URL.createObjectURL(rgbImageFile.value),
        processed: response.rgb_image.processed,
        detections: response.rgb_image.detections
      },
      thermal_image: {
        original: URL.createObjectURL(thermalImageFile.value),
        processed: response.thermal_image.processed,
        detections: response.thermal_image.detections
      }
    };
    
    showNotification('图像处理成功！', 'success');
  } catch (error) {
    console.error('处理图像时出错:', error);
    handleError('处理图像时出错，请稍后重试');
  } finally {
    isImageProcessing.value = false;
  }
};

// 处理视频文件变更
const handleVideoChange = ({ type, file }) => {
  if (type === 'rgb') {
    rgbVideoFile.value = file;
  } else if (type === 'thermal') {
    thermalVideoFile.value = file;
  }
};

// 移除视频
const handleRemoveVideo = (type) => {
  if (type === 'rgb') {
    rgbVideoFile.value = null;
  } else if (type === 'thermal') {
    thermalVideoFile.value = null;
  }
};

// 清除视频
const handleClearVideos = () => {
  rgbVideoFile.value = null;
  thermalVideoFile.value = null;
  videoTaskId.value = null;
  videoProcessingStatus.value = '';
};

// 检查视频处理状态
const checkVideoTaskStatus = async () => {
  if (!videoTaskId.value) return;
  
  try {
    // 替换为实际的API调用
    // const response = await rgbtDetectionService.checkVideoTaskStatus(videoTaskId.value);
    
    // 模拟API返回结果
    const response = {
      status: videoProcessingProgress.value >= 95 ? 'completed' : 'processing',
      progress: videoProcessingProgress.value,
      result: videoProcessingProgress.value >= 95 ? rgbtDetectionService.mockDetectionResult('video') : null
    };
    
    videoProcessingStatus.value = response.status;
    
    if (response.progress) {
      videoProcessingProgress.value = response.progress;
    }
    
    if (response.status === 'completed' && response.result) {
      // 处理完成，保存结果
      videoResults.value = {
        rgb_video: {
          original: URL.createObjectURL(rgbVideoFile.value),
          processed: response.result.rgb_video.processed
        },
        thermal_video: thermalVideoFile.value ? {
          original: URL.createObjectURL(thermalVideoFile.value),
          processed: response.result.thermal_video?.processed
        } : null
      };
      
      isVideoProcessing.value = false;
      showNotification('视频处理完成！', 'success');
    } else if (response.status === 'failed') {
      // 处理失败
      handleError('视频处理失败，请检查视频文件并重试');
      isVideoProcessing.value = false;
    } else {
      // 继续轮询
      setTimeout(checkVideoTaskStatus, 2000);
    }
  } catch (error) {
    console.error('检查视频任务状态时出错:', error);
    handleError('检查处理状态时出错');
  }
};

// 处理视频
const handleProcessVideos = async (formData) => {
  if (isVideoProcessing.value) return;
  
  try {
    isVideoProcessing.value = true;
    videoProcessingProgress.value = 0;
    videoProcessingStatus.value = 'processing';
    videoResults.value = null;
    
    // 模拟进度更新
    simulateProgress(videoProcessingProgress, isVideoProcessing, null);
    
    // 调用API处理视频 - 替换为实际的API调用
    // const response = await rgbtDetectionService.processVideos(formData);
    
    // 模拟网络延迟和任务ID
    await new Promise(resolve => setTimeout(resolve, 2000));
    const response = { task_id: 'mock-task-' + Date.now() };
    
    videoTaskId.value = response.task_id;
    
    // 轮询检查状态
    setTimeout(checkVideoTaskStatus, 1000);
    
    showNotification('视频处理已开始，请稍候...', 'info');
  } catch (error) {
    console.error('处理视频时出错:', error);
    isVideoProcessing.value = false;
    handleError('处理视频时出错，请稍后重试');
  }
};

// 重新开始处理
const handleRestart = () => {
  imageResults.value = null;
  videoResults.value = null;
  videoTaskId.value = null;
  videoProcessingStatus.value = '';
  imageProcessingProgress.value = 0;
  videoProcessingProgress.value = 0;
};

// 监视模式变化，重置状态
watch(processingMode, (newMode) => {
  handleRestart();
});

// LogRequestAndResponse函数，用于调试API请求和响应
const logRequestAndResponse = (endpoint, req, res) => {
  // 记录请求
  console.log('[API 请求]', {
    url: endpoint,
    method: req.method,
    data: req.data,
    params: req.params
  });
  
  // 记录响应
  if (res) {
    console.log('[API 响应]', {
      data: res,  // 记录完整响应
      status: res.status,
      headers: res.headers
    });
  }
};
</script>

<template>
  <BasePage :title="title">
    <div class="rgbt-detection-container">
      <!-- 应用介绍 -->
      <section class="app-intro">
        <div class="intro-content">
          <h2 class="intro-title">远距离目标识别系统</h2>
          <p class="intro-text">基于特殊图像增强处理，实现全天候、远距离的小目标检测与识别，大幅提升复杂环境下的目标识别率，适用于边境巡逻、海上搜救等场景。</p>
        </div>
      </section>

      <!-- 直接使用前端项目2的可见光-热红外检测组件 -->
      <div class="detection-wrapper">
        <RGBTDetectionView />
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
.rgbt-detection-container {
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

/* 保持RGBTDetectionView原有样式不受影响 */
:deep(.rgbt-detection-view) {
  height: auto !important;
  min-height: 600px;
  flex-grow: 1;
  background: transparent !important;
}

:deep(.el-container) {
  background: transparent !important;
}

/* 修复可能的元素样式冲突 */
:deep(.el-upload) {
  width: 100%;
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

:deep(.assistant-panel) {
  background-color: rgba(250, 250, 252, 0.95) !important; /* 浅色背景替换黑色 */
  border-left: 1px solid rgba(79, 70, 229, 0.2) !important;
  box-shadow: -5px 0 15px rgba(0, 0, 0, 0.05) !important;
}

:deep(.assistant-header) {
  background: linear-gradient(45deg, rgba(79, 70, 229, 0.1), rgba(0, 210, 170, 0.1)) !important;
  border-bottom: 1px solid rgba(79, 70, 229, 0.2) !important;
}

:deep(.assistant-header h3) {
  color: #4f46e5 !important;
  background: linear-gradient(45deg, #4f46e5, #00d2aa) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
}

:deep(.detection-assistant) {
  color: #333 !important; /* 深色文字，适应浅色背景 */
}

:deep(.stat-item) {
  background: rgba(255, 255, 255, 0.7) !important;
  border-radius: 12px !important;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05) !important;
  border: 1px solid rgba(79, 70, 229, 0.2) !important;
}

:deep(.stat-value) {
  background: linear-gradient(45deg, #4f46e5, #00d2aa) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
}

:deep(.stat-label) {
  color: #666 !important;
}

:deep(.objects-list), :deep(.analysis-summary) {
  background: rgba(255, 255, 255, 0.7) !important;
  border-radius: 12px !important;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05) !important;
  border: 1px solid rgba(79, 70, 229, 0.1) !important;
}

:deep(.splitter) {
  background: linear-gradient(to bottom, rgba(79, 70, 229, 0.2), rgba(0, 210, 170, 0.2)) !important;
}

:deep(.splitter-handle) {
  background-color: rgba(79, 70, 229, 0.4) !important;
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
  .rgbt-detection-container {
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

/* 动画效果 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.app-intro, .detection-wrapper {
  animation: fadeIn 0.5s ease-out;
}
</style>