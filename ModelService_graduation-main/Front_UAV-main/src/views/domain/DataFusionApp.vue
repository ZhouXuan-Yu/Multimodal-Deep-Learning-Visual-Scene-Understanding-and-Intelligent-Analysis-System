<script setup>
import { ref, reactive, onMounted } from 'vue';
import BasePage from './templates/BasePage.vue';
import ImageFusionPanel from './components/DataFusion/ImageFusionPanel.vue';
import VideoFusionPanel from './components/DataFusion/VideoFusionPanel.vue';
import FusionResultDisplay from './components/DataFusion/FusionResultDisplay.vue';
import dataFusionService from './services/dataFusionService';

// 页面标题
const title = '多状态数据融合';

// 处理模式 (image/video)
const processingMode = ref('image');

// 通知状态
const notification = reactive({
  show: false,
  message: '',
  type: 'info', // info, success, error
  timeout: null
});

// 图像融合状态
const isImageProcessing = ref(false);
const imageFusionProgress = ref(0);
const fusionImageResult = ref(null);
const fusionMethods = ref([
  { value: 'wavelet', label: '小波变换' },
  { value: 'deeplearning', label: '深度学习融合' },
  { value: 'laplacian', label: '拉普拉斯金字塔' }
]);
const selectedFusionMethod = ref('deeplearning');

// 视频融合状态
const isVideoProcessing = ref(false);
const videoFusionProgress = ref(0);
const videoFusionStatus = ref('');
const videoTaskId = ref(null);
const videoFusionResult = ref(null);

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

// 处理图像融合
const handleImageFusion = async (data) => {
  if (isImageProcessing.value) return;
  
  try {
    isImageProcessing.value = true;
    imageFusionProgress.value = 0;
    fusionImageResult.value = null;
    
    // 模拟进度更新
    const progressInterval = simulateProgress(imageFusionProgress, isImageProcessing, null);
    
    // 添加选择的融合方法
    const formData = data.formData;
    formData.append('fusion_method', selectedFusionMethod.value);
    
    // 调用API进行图像融合 - 替换为实际的API调用
    // const response = await dataFusionService.processImageFusion(formData);
    
    // 模拟网络延迟
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // 模拟API返回结果
    const response = {
      data: dataFusionService.mockFusionResult()
    };
    
    // 处理完成
    clearInterval(progressInterval);
    imageFusionProgress.value = 100;
    
    // 保存结果
    fusionImageResult.value = {
      rgbImageUrl: URL.createObjectURL(data.rgbFile),
      thermalImageUrl: URL.createObjectURL(data.thermalFile),
      fusionImageUrl: response.data.fusionImageUrl,
      metadata: response.data.metadata
    };
    
    showNotification('图像融合成功！', 'success');
  } catch (error) {
    console.error('图像融合失败:', error);
    handleError('图像融合处理时出错，请稍后重试');
  } finally {
    isImageProcessing.value = false;
  }
};

// 处理视频融合
const handleVideoFusion = async (data) => {
  if (isVideoProcessing.value) return;
  
  try {
    isVideoProcessing.value = true;
    videoFusionProgress.value = 0;
    videoFusionStatus.value = 'processing';
    videoFusionResult.value = null;
    
    // 模拟进度更新
    simulateProgress(videoFusionProgress, isVideoProcessing, null);
    
    // 添加选择的融合方法
    const formData = data.formData;
    formData.append('fusion_method', selectedFusionMethod.value);
    
    // 调用API进行视频融合 - 替换为实际的API调用
    // const response = await dataFusionService.processVideoFusion(formData);
    
    // 模拟网络延迟和任务ID
    await new Promise(resolve => setTimeout(resolve, 2000));
    const response = { data: { task_id: 'mock-task-' + Date.now() } };
    
    videoTaskId.value = response.data.task_id;
    
    // 轮询检查状态
    setTimeout(checkVideoFusionStatus, 1000);
    
    showNotification('视频融合处理已开始，请稍候...', 'info');
  } catch (error) {
    console.error('视频融合处理失败:', error);
    isVideoProcessing.value = false;
    handleError('视频融合处理时出错，请稍后重试');
  }
};

// 检查视频融合状态
const checkVideoFusionStatus = async () => {
  if (!videoTaskId.value) return;
  
  try {
    // 替换为实际的API调用
    // const response = await dataFusionService.getVideoFusionStatus(videoTaskId.value);
    
    // 模拟API返回结果
    const response = {
      data: {
        status: videoFusionProgress.value >= 95 ? 'completed' : 'processing',
        progress: videoFusionProgress.value,
        result: videoFusionProgress.value >= 95 ? {
          rgbVideoUrl: '/mock/original_rgb_video.mp4',
          thermalVideoUrl: '/mock/original_thermal_video.mp4',
          fusionVideoUrl: '/mock/fusion_result_video.mp4',
          metadata: {
            fusionMethod: '深度学习融合',
            processingTime: 35.7,
            enhancementLevel: '高',
            resolution: '1280x720'
          }
        } : null
      }
    };
    
    videoFusionStatus.value = response.data.status;
    
    if (response.data.progress) {
      videoFusionProgress.value = response.data.progress;
    }
    
    if (response.data.status === 'completed' && response.data.result) {
      // 处理完成，保存结果
      videoFusionResult.value = response.data.result;
      
      isVideoProcessing.value = false;
      showNotification('视频融合处理完成！', 'success');
    } else if (response.data.status === 'failed') {
      // 处理失败
      handleError('视频融合处理失败，请检查视频文件并重试');
      isVideoProcessing.value = false;
    } else {
      // 继续轮询
      setTimeout(checkVideoFusionStatus, 2000);
    }
  } catch (error) {
    console.error('检查视频融合状态时出错:', error);
    handleError('检查处理状态时出错');
  }
};

// 重新开始处理
const handleRestart = () => {
  fusionImageResult.value = null;
  videoFusionResult.value = null;
  videoTaskId.value = null;
  videoFusionStatus.value = '';
  imageFusionProgress.value = 0;
  videoFusionProgress.value = 0;
};

// 加载融合方法列表
const loadFusionMethods = async () => {
  try {
    // 替换为实际API调用
    // const response = await dataFusionService.getFusionMethods();
    // fusionMethods.value = response.data;
    
    // 已有默认融合方法，所以此处不做操作
  } catch (error) {
    console.error('加载融合方法失败:', error);
  }
};

// 组件挂载时加载融合方法
onMounted(() => {
  loadFusionMethods();
});
</script>

<template>
  <BasePage :title="title">
    <div class="app-container">
      <!-- 应用介绍 -->
      <section class="app-intro">
        <h2 class="intro-title">多状态数据融合系统</h2>
        <p class="intro-text">结合可见光与热红外数据，利用先进的融合算法，提供增强的目标识别与场景理解能力，实现全天候、全天时的监控与检测。</p>
      </section>

      <!-- 通知提示 -->
      <transition name="fade">
        <div 
          v-if="notification.show" 
          class="notification" 
          :class="`notification-${notification.type}`"
        >
          <div class="notification-content">
            {{ notification.message }}
          </div>
          <button class="notification-close" @click="closeNotification">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </transition>

      <!-- 处理模式选择 -->
      <div class="mode-selection">
        <button 
          class="mode-button" 
          :class="{ active: processingMode === 'image' }" 
          @click="processingMode = 'image'"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          图像融合
        </button>
        <button 
          class="mode-button" 
          :class="{ active: processingMode === 'video' }" 
          @click="processingMode = 'video'"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          视频融合
        </button>
      </div>

      <!-- 融合方法选择 -->
      <div class="fusion-method-selection">
        <label class="method-label">融合方法：</label>
        <div class="method-options">
          <label 
            v-for="method in fusionMethods" 
            :key="method.value" 
            class="method-option"
            :class="{ active: selectedFusionMethod === method.value }"
          >
            <input 
              type="radio" 
              :value="method.value" 
              v-model="selectedFusionMethod" 
              class="method-radio"
            />
            <span class="method-name">{{ method.label }}</span>
          </label>
        </div>
      </div>

      <!-- 主功能区域 -->
      <div class="processing-container">
        <!-- 图像融合 -->
        <div v-if="processingMode === 'image'" class="processor-section">
          <!-- 图像上传和处理 -->
          <div v-if="!fusionImageResult" class="upload-section">
            <ImageFusionPanel 
              :is-processing="isImageProcessing" 
              :processing-progress="imageFusionProgress"
              @process-fusion="handleImageFusion"
              @error="handleError"
            />
          </div>
          
          <!-- 图像融合结果 -->
          <div v-else class="results-section">
            <FusionResultDisplay 
              result-type="image"
              :fusion-result="fusionImageResult"
              @restart="handleRestart"
              @error="handleError"
            />
          </div>
        </div>
        
        <!-- 视频融合 -->
        <div v-if="processingMode === 'video'" class="processor-section">
          <!-- 视频上传和处理 -->
          <div v-if="!videoFusionResult" class="upload-section">
            <VideoFusionPanel 
              :is-processing="isVideoProcessing" 
              :processing-progress="videoFusionProgress"
              :processing-status="videoFusionStatus"
              @process-fusion="handleVideoFusion"
              @error="handleError"
            />
          </div>
          
          <!-- 视频融合结果 -->
          <div v-else class="results-section">
            <FusionResultDisplay 
              result-type="video"
              :fusion-result="videoFusionResult"
              @restart="handleRestart"
              @error="handleError"
            />
          </div>
        </div>
      </div>
    </div>
  </BasePage>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 1.5rem;
}

.app-intro {
  background-color: #f8fafc;
  border-radius: 0.5rem;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border-left: 4px solid #4f46e5;
}

.intro-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 0.75rem;
}

.intro-text {
  color: #4b5563;
  line-height: 1.6;
}

.notification {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  max-width: 24rem;
}

.notification-info {
  background-color: #3b82f6;
  color: white;
  border-left: 4px solid #1d4ed8;
}

.notification-success {
  background-color: #10b981;
  color: white;
  border-left: 4px solid #047857;
}

.notification-error {
  background-color: #ef4444;
  color: white;
  border-left: 4px solid #b91c1c;
}

.notification-content {
  flex-grow: 1;
  margin-right: 0.75rem;
}

.notification-close {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: color 0.2s;
}

.notification-close:hover {
  color: white;
}

.mode-selection {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.mode-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  font-weight: 500;
  border-radius: 0.375rem;
  background-color: #f1f5f9;
  color: #64748b;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-button:hover {
  background-color: #e2e8f0;
  color: #334155;
}

.mode-button.active {
  background-color: #4f46e5;
  color: white;
}

.fusion-method-selection {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background-color: #f8fafc;
  border-radius: 0.5rem;
}

.method-label {
  font-weight: 500;
  color: #334155;
}

.method-options {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.method-option {
  display: flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background-color: #f1f5f9;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.2s;
}

.method-option:hover {
  background-color: #e2e8f0;
}

.method-option.active {
  background-color: #4f46e5;
  color: white;
}

.method-radio {
  display: none;
}

.method-name {
  font-size: 0.875rem;
  font-weight: 500;
}

.processing-container {
  width: 100%;
}

.processor-section,
.upload-section,
.results-section {
  width: 100%;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-1rem);
}
</style>
