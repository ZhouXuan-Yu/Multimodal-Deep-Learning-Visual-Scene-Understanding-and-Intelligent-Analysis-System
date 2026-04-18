<template>
  <div class="processing-results">
    <!-- 图像处理结果 -->
    <div v-if="resultType === 'image' && imageResults" class="image-results">
      <h3 class="results-title">图像处理结果</h3>
      
      <div class="comparison-container">
        <div class="comparison-item">
          <div class="image-label">原始图像</div>
          <div class="image-wrapper">
            <img :src="imageResults.originalUrl" alt="原始图像" class="result-image" />
          </div>
        </div>
        
        <div class="comparison-item">
          <div class="image-label">
            增强后的图像
            <span class="processing-time" v-if="imageResults.processingTime">
              (处理时间: {{ formatTime(imageResults.processingTime) }})
            </span>
          </div>
          <div class="image-wrapper">
            <img :src="imageResults.enhancedUrl" alt="增强图像" class="result-image" />
          </div>
        </div>
        
        <div class="comparison-item" v-if="imageResults.detectionUrl">
          <div class="image-label">目标检测结果</div>
          <div class="image-wrapper">
            <img :src="imageResults.detectionUrl" alt="检测结果" class="result-image" />
          </div>
        </div>
      </div>
      
      <!-- 检测结果信息 -->
      <div class="detection-info" v-if="imageResults.detections && imageResults.detections.length > 0">
        <h4 class="info-title">检测到的目标</h4>
        <div class="detections-list">
          <div 
            v-for="(detection, index) in imageResults.detections" 
            :key="index"
            class="detection-item"
          >
            <div class="detection-type">
              <span :style="{ backgroundColor: getColorForClass(detection.class) }" class="type-indicator"></span>
              {{ translateClass(detection.class) }}
            </div>
            <div class="detection-confidence">
              置信度: {{ (detection.confidence * 100).toFixed(1) }}%
            </div>
          </div>
        </div>
      </div>
      
      <div class="actions-container">
        <button class="action-button restart-button" @click="restartProcessing">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          重新处理
        </button>
        <button class="action-button download-button" @click="downloadResults">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          下载结果
        </button>
      </div>
    </div>
    
    <!-- 视频处理结果 -->
    <div v-if="resultType === 'video' && videoResults" class="video-results">
      <h3 class="results-title">视频处理结果</h3>
      
      <div class="comparison-container">
        <div class="comparison-item">
          <div class="video-label">原始视频</div>
          <div class="video-wrapper">
            <video 
              :src="videoResults.originalUrl" 
              controls 
              class="result-video"
              @error="handleVideoError('original')"
            ></video>
            <div v-if="videoErrors.original" class="video-error">
              无法加载原始视频，请检查文件格式
            </div>
          </div>
        </div>
        
        <div class="comparison-item">
          <div class="video-label">
            处理后的视频
            <span class="processing-time" v-if="videoResults.processingTime">
              (处理时间: {{ formatTime(videoResults.processingTime, true) }})
            </span>
          </div>
          <div class="video-wrapper">
            <video 
              :src="videoResults.processedUrl" 
              controls 
              class="result-video"
              @error="handleVideoError('processed')"
            ></video>
            <div v-if="videoErrors.processed" class="video-error">
              无法加载处理后的视频，请尝试下载后查看
            </div>
          </div>
        </div>
      </div>
      
      <!-- 检测结果摘要 -->
      <div class="detection-summary" v-if="videoResults.detectionSummary">
        <h4 class="summary-title">检测摘要</h4>
        <div class="summary-content">
          <div class="summary-stat">
            <div class="stat-value">{{ videoResults.detectionSummary.totalFrames || 0 }}</div>
            <div class="stat-label">处理帧数</div>
          </div>
          <div class="summary-stat">
            <div class="stat-value">{{ videoResults.detectionSummary.totalDetections || 0 }}</div>
            <div class="stat-label">检测目标数</div>
          </div>
          <div class="summary-stat">
            <div class="stat-value">{{ videoResults.detectionSummary.averageEnhancement || '0%' }}</div>
            <div class="stat-label">平均增强度</div>
          </div>
        </div>
      </div>
      
      <div class="actions-container">
        <button class="action-button restart-button" @click="restartProcessing">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          重新处理
        </button>
        <button class="action-button download-button" @click="downloadResults">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          下载结果
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  resultType: {
    type: String,
    default: 'image',
    validator: (value) => ['image', 'video'].includes(value)
  },
  imageResults: {
    type: Object,
    default: null
  },
  videoResults: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['restart', 'download']);

// 视频错误状态
const videoErrors = ref({
  original: false,
  processed: false
});

// 处理视频错误
const handleVideoError = (videoType) => {
  videoErrors.value[videoType] = true;
};

// 重新开始处理
const restartProcessing = () => {
  emit('restart');
};

// 下载结果
const downloadResults = () => {
  const resultsData = props.resultType === 'image' ? props.imageResults : props.videoResults;
  emit('download', {
    type: props.resultType,
    data: resultsData
  });
};

// 格式化处理时间
const formatTime = (ms, isLong = false) => {
  if (!ms && ms !== 0) return '--';
  
  if (ms < 1000) {
    return `${ms.toFixed(0)}毫秒`;
  }
  
  const seconds = ms / 1000;
  
  if (seconds < 60 || !isLong) {
    return `${seconds.toFixed(1)}秒`;
  }
  
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  
  return `${minutes}分${remainingSeconds.toFixed(0)}秒`;
};

// 获取目标类别对应的颜色
const getColorForClass = (className) => {
  const colorMap = {
    'person': '#4f46e5',
    'car': '#f59e0b',
    'truck': '#d97706',
    'bicycle': '#10b981',
    'motorcycle': '#059669',
    'bus': '#7c3aed',
    'animal': '#8b5cf6',
    'traffic_light': '#ef4444',
    'stop_sign': '#b91c1c',
    'face': '#ec4899'
  };
  
  return colorMap[className] || '#6b7280';
};

// 翻译目标类别
const translateClass = (className) => {
  const classMap = {
    'person': '人',
    'car': '汽车',
    'truck': '卡车',
    'bicycle': '自行车',
    'motorcycle': '摩托车',
    'bus': '公交车',
    'animal': '动物',
    'traffic_light': '红绿灯',
    'stop_sign': '停止标志',
    'face': '人脸'
  };
  
  return classMap[className] || className;
};
</script>

<style scoped>
.processing-results {
  width: 100%;
  background-color: white;
  border-radius: 0.5rem;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.results-title {
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 1.5rem;
  font-size: 1.25rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #e2e8f0;
}

.comparison-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.comparison-item {
  display: flex;
  flex-direction: column;
}

.image-label,
.video-label {
  font-weight: 500;
  color: #334155;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
}

.processing-time {
  font-weight: normal;
  color: #64748b;
  margin-left: 0.5rem;
  font-size: 0.75rem;
}

.image-wrapper,
.video-wrapper {
  position: relative;
  width: 100%;
  border-radius: 0.25rem;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  background-color: #f8fafc;
}

.result-image,
.result-video {
  width: 100%;
  object-fit: contain;
  max-height: 300px;
}

.video-error {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 0.5rem;
  background-color: rgba(239, 68, 68, 0.9);
  color: white;
  font-size: 0.75rem;
  text-align: center;
}

.detection-info,
.detection-summary {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 0.375rem;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.info-title,
.summary-title {
  font-weight: 600;
  color: #334155;
  margin-bottom: 0.75rem;
  font-size: 1rem;
}

.detections-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}

.detection-item {
  display: flex;
  flex-direction: column;
  padding: 0.75rem;
  background-color: white;
  border-radius: 0.25rem;
  border: 1px solid #e2e8f0;
}

.detection-type {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  color: #334155;
  margin-bottom: 0.25rem;
}

.type-indicator {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 50%;
}

.detection-confidence {
  font-size: 0.75rem;
  color: #64748b;
}

.summary-content {
  display: flex;
  justify-content: space-around;
}

.summary-stat {
  text-align: center;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: #4f46e5;
}

.stat-label {
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.25rem;
}

.actions-container {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1rem;
}

.action-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  border: none;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.restart-button {
  background-color: #f1f5f9;
  color: #334155;
}

.restart-button:hover {
  background-color: #e2e8f0;
  color: #1e293b;
}

.download-button {
  background-color: #4f46e5;
  color: white;
}

.download-button:hover {
  background-color: #4338ca;
}
</style>
