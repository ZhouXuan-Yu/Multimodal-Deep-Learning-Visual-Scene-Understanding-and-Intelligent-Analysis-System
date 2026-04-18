<template>
  <div class="camera-detection-container">
    <div class="camera-controls">
      <h3 class="section-title">实时火灾检测</h3>
      <div class="camera-buttons">
        <button 
          v-if="!isActive" 
          @click="startCameraDetection" 
          class="start-camera-btn"
          :disabled="loading"
        >
          <span v-if="!loading">开启摄像头</span>
          <span v-else class="loading-text">
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            正在准备...
          </span>
        </button>
        <button 
          v-else 
          @click="stopCameraDetection" 
          class="stop-camera-btn"
        >
          停止检测
        </button>
      </div>
    </div>
    
    <div class="camera-view-area" :class="{ 'detection-active': isActive }">
      <div class="video-container">
        <video 
          ref="cameraVideo" 
          class="camera-video" 
          autoplay 
          muted 
          playsinline
        ></video>
        <canvas 
          ref="cameraCanvas" 
          class="detection-canvas" 
          v-show="isActive"
        ></canvas>
        <div class="overlay-message" v-if="!isActive && !loading">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="message-icon">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <p>点击"开启摄像头"按钮开始实时火灾检测</p>
        </div>
        <div class="overlay-message" v-if="loading">
          <svg class="animate-spin message-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p>正在初始化摄像头...</p>
        </div>
        <div class="fire-alert" v-if="isActive && fireDetected">
          <div class="alert-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-8 h-8">
              <path fill-rule="evenodd" d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z" clip-rule="evenodd" />
            </svg>
          </div>
          <div class="alert-text">火灾警告!</div>
        </div>
      </div>
    </div>
    
    <div class="detection-results" v-if="isActive">
      <div class="result-card">
        <div class="result-header">
          <h4 class="result-title">检测状态</h4>
          <div class="update-time">最后更新: {{ formattedLastUpdateTime }}</div>
        </div>
        
        <div class="status-metrics">
          <div class="metric-item">
            <div class="metric-label">检测帧率</div>
            <div class="metric-value">{{ fps.toFixed(1) }} FPS</div>
          </div>
          <div class="metric-item">
            <div class="metric-label">处理时间</div>
            <div class="metric-value">{{ processingTime.toFixed(0) }} ms</div>
          </div>
          <div class="metric-item" :class="{ 'fire-detected': fireDetected }">
            <div class="metric-label">检测状态</div>
            <div class="metric-value status-value">
              {{ fireDetected ? '火灾警告!' : '安全' }}
            </div>
          </div>
        </div>
        
        <div class="confidence-bar-container">
          <div class="confidence-label">火灾可能性: {{ (confidence * 100).toFixed(1) }}%</div>
          <div class="confidence-bar-bg">
            <div 
              class="confidence-bar" 
              :style="{ width: `${confidence * 100}%` }"
              :class="{ 'high-confidence': confidence > 0.7 }"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import disasterDetectionService from '../../services/disasterDetectionService';

// 状态变量
const cameraVideo = ref(null);
const cameraCanvas = ref(null);
const isActive = ref(false);
const loading = ref(false);
const fireDetected = ref(false);
const confidence = ref(0);
const fps = ref(0);
const processingTime = ref(0);
const lastUpdateTime = ref(null);
const animationFrameId = ref(null);
const processingTimeHistory = ref([]);
const cameraStream = ref(null);

// 计算属性
const formattedLastUpdateTime = computed(() => {
  if (!lastUpdateTime.value) return '无数据';
  return new Date(lastUpdateTime.value).toLocaleTimeString();
});

// 启动摄像头检测
const startCameraDetection = async () => {
  loading.value = true;
  
  try {
    // 请求摄像头权限
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' },
      audio: false
    });
    
    cameraStream.value = stream;
    cameraVideo.value.srcObject = stream;
    
    // 确保视频元素已加载
    await new Promise(resolve => {
      cameraVideo.value.onloadedmetadata = () => {
        resolve();
      };
    });
    
    // 开始播放视频
    await cameraVideo.value.play();
    
    // 设置canvas大小
    const videoWidth = cameraVideo.value.videoWidth;
    const videoHeight = cameraVideo.value.videoHeight;
    
    cameraCanvas.value.width = videoWidth;
    cameraCanvas.value.height = videoHeight;
    
    // 激活检测
    isActive.value = true;
    loading.value = false;
    
    // 开始检测循环
    startCameraDetectionLoop();
  } catch (error) {
    console.error('摄像头访问失败:', error);
    alert(`无法访问摄像头: ${error.message}`);
    loading.value = false;
  }
};

// 停止摄像头检测
const stopCameraDetection = () => {
  isActive.value = false;
  
  // 停止检测循环
  if (animationFrameId.value) {
    cancelAnimationFrame(animationFrameId.value);
    animationFrameId.value = null;
  }
  
  // 停止视频流
  if (cameraStream.value) {
    cameraStream.value.getTracks().forEach(track => track.stop());
    cameraStream.value = null;
  }
  
  // 清除视频源
  if (cameraVideo.value) {
    cameraVideo.value.srcObject = null;
  }
  
  // 重置状态
  fireDetected.value = false;
  confidence.value = 0;
  fps.value = 0;
  processingTime.value = 0;
  processingTimeHistory.value = [];
  lastUpdateTime.value = null;
};

// 开始检测循环
const startCameraDetectionLoop = () => {
  let lastFrameTime = performance.now();
  let frameCount = 0;
  let fpsUpdateTime = lastFrameTime;
  
  const detectFrame = async () => {
    if (!isActive.value) return;
    
    const now = performance.now();
    frameCount++;
    
    // 每秒更新FPS
    if (now - fpsUpdateTime > 1000) {
      fps.value = frameCount / ((now - fpsUpdateTime) / 1000);
      frameCount = 0;
      fpsUpdateTime = now;
    }
    
    // 捕获并处理帧
    await processCameraFrame();
    
    // 请求下一帧
    animationFrameId.value = requestAnimationFrame(detectFrame);
  };
  
  detectFrame();
};

// 处理摄像头帧
const processCameraFrame = async () => {
  if (!cameraVideo.value || !cameraCanvas.value || !isActive.value) return;
  
  const startTime = performance.now();
  
  try {
    // 绘制当前帧到Canvas
    const ctx = cameraCanvas.value.getContext('2d');
    ctx.drawImage(
      cameraVideo.value, 
      0, 0, 
      cameraCanvas.value.width, 
      cameraCanvas.value.height
    );
    
    // 获取canvas数据
    const imageData = ctx.getImageData(
      0, 0, 
      cameraCanvas.value.width, 
      cameraCanvas.value.height
    );
    
    // 将图像数据转换为blob
    const canvas = document.createElement('canvas');
    canvas.width = cameraCanvas.value.width;
    canvas.height = cameraCanvas.value.height;
    const tempCtx = canvas.getContext('2d');
    tempCtx.putImageData(imageData, 0, 0);
    
    const blob = await new Promise(resolve => {
      canvas.toBlob(blob => resolve(blob), 'image/jpeg', 0.8);
    });
    
    // 发送帧进行处理
    const formData = new FormData();
    formData.append('frame', blob);
    
    const response = await disasterDetectionService.processCameraFrame(formData);
    
    // 更新检测结果
    if (response.data) {
      fireDetected.value = response.data.fire_detected;
      confidence.value = response.data.confidence || 0;
      
      // 如果返回了检测框，绘制它们
      if (response.data.bounding_boxes && response.data.bounding_boxes.length > 0) {
        drawDetectionBoxes(response.data.bounding_boxes);
      }
      
      // 更新时间和性能指标
      lastUpdateTime.value = new Date();
      const endTime = performance.now();
      const currentProcessingTime = endTime - startTime;
      
      // 保留最近10次的处理时间计算平均值
      processingTimeHistory.value.push(currentProcessingTime);
      if (processingTimeHistory.value.length > 10) {
        processingTimeHistory.value.shift();
      }
      
      processingTime.value = processingTimeHistory.value.reduce((sum, time) => sum + time, 0) / 
                            processingTimeHistory.value.length;
    }
  } catch (error) {
    console.error('帧处理失败:', error);
    // 不弹出错误，只记录日志，避免太多错误通知
  }
};

// 绘制检测框
const drawDetectionBoxes = (boxes) => {
  if (!cameraCanvas.value) return;
  
  const ctx = cameraCanvas.value.getContext('2d');
  const width = cameraCanvas.value.width;
  const height = cameraCanvas.value.height;
  
  // 绘制之前保存当前帧，以便在其上绘制
  const frameData = ctx.getImageData(0, 0, width, height);
  
  // 在当前帧上绘制检测框
  ctx.lineWidth = 3;
  ctx.strokeStyle = 'rgba(255, 0, 0, 0.8)';
  ctx.fillStyle = 'rgba(255, 0, 0, 0.3)';
  ctx.font = '16px Arial';
  
  boxes.forEach(box => {
    const x = box.x * width;
    const y = box.y * height;
    const w = box.width * width;
    const h = box.height * height;
    
    // 绘制填充矩形
    ctx.fillRect(x, y, w, h);
    
    // 绘制边框
    ctx.strokeRect(x, y, w, h);
    
    // 绘制标签
    ctx.fillStyle = 'rgba(255, 0, 0, 1)';
    ctx.fillText(`火灾: ${(box.confidence * 100).toFixed(0)}%`, x, y - 5);
    ctx.fillStyle = 'rgba(255, 0, 0, 0.3)';
  });
};

// 组件卸载时清理资源
onBeforeUnmount(() => {
  stopCameraDetection();
});
</script>

<style scoped>
.camera-detection-container {
  width: 100%;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 1rem;
}

.camera-controls {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

@media (min-width: 640px) {
  .camera-controls {
    flex-direction: row;
    align-items: center;
  }
}

.camera-buttons {
  margin-top: 0.5rem;
}

@media (min-width: 640px) {
  .camera-buttons {
    margin-top: 0;
  }
}

.start-camera-btn {
  padding-left: 1.5rem;
  padding-right: 1.5rem;
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
  background-color: #3b82f6;
  color: white;
  border-radius: 0.375rem;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 140px;
}

.start-camera-btn:hover {
  background-color: #2563eb;
}

.start-camera-btn:focus {
  outline: none;
  box-shadow: 0 0 0 2px #3b82f6, 0 0 0 4px rgba(59, 130, 246, 0.5);
}

.start-camera-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.stop-camera-btn {
  padding-left: 1.5rem;
  padding-right: 1.5rem;
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
  background-color: #ef4444;
  color: white;
  border-radius: 0.375rem;
}

.stop-camera-btn:hover {
  background-color: #dc2626;
}

.stop-camera-btn:focus {
  outline: none;
  box-shadow: 0 0 0 2px #ef4444, 0 0 0 4px rgba(239, 68, 68, 0.5);
}

.loading-text {
  display: flex;
  align-items: center;
}

.camera-view-area {
  margin-bottom: 1.5rem;
  background-color: #1f2937;
  border-radius: 0.5rem;
  overflow: hidden;
  height: 400px;
}

.camera-view-area.detection-active {
  border: 2px solid #3b82f6;
}

.video-container {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.camera-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.detection-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.overlay-message {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  text-align: center;
  padding: 1rem;
}

.message-icon {
  width: 4rem;
  height: 4rem;
  margin-bottom: 1rem;
  color: white;
}

.fire-alert {
  position: absolute;
  top: 1rem;
  left: 1rem;
  display: flex;
  align-items: center;
  padding: 0.75rem;
  background-color: #dc2626;
  color: white;
  border-radius: 0.375rem;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.alert-icon {
  margin-right: 0.5rem;
}

.alert-text {
  font-weight: 700;
  font-size: 1.125rem;
}

.detection-results {
  width: 100%;
}

.result-card {
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
  padding: 1rem;
  border: 1px solid #e5e7eb;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.result-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
}

.update-time {
  font-size: 0.875rem;
  color: #6b7280;
}

.status-metrics {
  display: grid;
  grid-template-columns: repeat(1, minmax(0, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

@media (min-width: 640px) {
  .status-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.metric-item {
  background-color: #f9fafb;
  padding: 0.75rem;
  border-radius: 0.5rem;
}

.metric-item.fire-detected .metric-value {
  color: #dc2626;
}

.metric-label {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.25rem;
}

.metric-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
}

.status-value {
  font-weight: 700;
}

.confidence-bar-container {
  margin-top: 1rem;
}

.confidence-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.25rem;
}

.confidence-bar-bg {
  background-color: #e5e7eb;
  border-radius: 9999px;
  height: 0.75rem;
  overflow: hidden;
}

.confidence-bar {
  height: 100%;
  background-color: #10b981;
  border-radius: 9999px;
  transition: all 300ms;
}

.confidence-bar.high-confidence {
  background-color: #ef4444;
}
</style>
