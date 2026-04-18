<template>
  <div class="result-display-container">
    <div class="result-header">
      <h3 class="result-title">检测结果</h3>
      <div class="result-stats">
        <div class="stat-item">
          <span class="stat-label">处理时间:</span>
          <span class="stat-value">{{ processingTime }}秒</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">FPS:</span>
          <span class="stat-value">{{ fps }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">跳帧率:</span>
          <span class="stat-value">{{ frameSkip }}</span>
        </div>
      </div>
    </div>

    <div class="videos-container">
      <div class="video-column">
        <h4 class="video-label">原始视频</h4>
        <div class="video-wrapper">
          <video 
            controls 
            class="video-player" 
            :src="originalVideoUrl"
            @error="handleVideoError('original')"
          ></video>
          <div v-if="videoErrors.original" class="video-error">
            <p>视频加载失败</p>
          </div>
        </div>
      </div>
      
      <div class="video-column">
        <h4 class="video-label">检测结果</h4>
        <div class="video-wrapper">
          <video 
            controls 
            class="video-player" 
            :src="getProcessedVideoUrl"
            @error="handleVideoError('processed')"
          ></video>
          <div v-if="videoErrors.processed" class="video-error">
            <p>视频加载失败，请刷新页面或重新处理</p>
          </div>
        </div>
      </div>
    </div>

    <div class="detection-summary">
      <h4 class="summary-title">检测统计</h4>
      <div class="frames-container">
        <div v-if="frames && frames.length > 0" class="frames-grid">
          <div 
            v-for="(frame, index) in frames" 
            :key="index"
            class="frame-card"
            :class="{ 'fire-detected': frame.fire_detected }"
          >
            <div class="frame-number">帧 {{ frame.frame_number }}</div>
            <div class="frame-status">
              <span v-if="frame.fire_detected" class="status-warning">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
                  <path fill-rule="evenodd" d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z" clip-rule="evenodd" />
                </svg>
                火灾警告
              </span>
              <span v-else class="status-safe">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
                  <path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm13.36-1.814a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clip-rule="evenodd" />
                </svg>
                安全
              </span>
            </div>
            <div class="frame-confidence">
              可信度: {{ (frame.confidence * 100).toFixed(2) }}%
            </div>
          </div>
        </div>
        <div v-else class="no-frames">
          <p>没有可用的帧数据</p>
        </div>
      </div>
    </div>

    <div class="result-actions">
      <button @click="$emit('restart')" class="restart-btn">重新检测</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  processId: {
    type: String,
    required: true
  },
  frames: {
    type: Array,
    default: () => []
  },
  processingTime: {
    type: Number,
    default: 0
  },
  fps: {
    type: Number,
    default: 0
  },
  frameSkip: {
    type: Number,
    default: 0
  },
  getApiUrl: {
    type: Function,
    default: (path) => path
  },
  originalVideoUrl: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['restart']);

const videoErrors = ref({
  original: false,
  processed: false
});

const handleVideoError = (type) => {
  videoErrors.value[type] = true;
};

const getProcessedVideoUrl = computed(() => {
  if (!props.processId) return '';
  return props.getApiUrl(`/results/${props.processId}/video`);
});
</script>

<style scoped>
.result-display-container {
  @apply w-full bg-white rounded-lg shadow-md p-6;
}

.result-header {
  @apply flex flex-col md:flex-row justify-between items-start md:items-center mb-6 pb-4 border-b border-gray-200;
}

.result-title {
  @apply text-xl font-bold text-gray-800 mb-2 md:mb-0;
}

.result-stats {
  @apply flex flex-wrap gap-3;
}

.stat-item {
  @apply bg-gray-100 px-3 py-1 rounded text-sm;
}

.stat-label {
  @apply font-medium text-gray-600 mr-1;
}

.stat-value {
  @apply text-gray-800;
}

.videos-container {
  @apply grid grid-cols-1 md:grid-cols-2 gap-4 mb-8;
}

.video-column {
  @apply flex flex-col;
}

.video-label {
  @apply text-lg font-medium mb-2 text-gray-700;
}

.video-wrapper {
  @apply relative bg-black rounded-lg overflow-hidden;
  aspect-ratio: 16/9;
}

.video-player {
  @apply w-full h-full object-contain;
}

.video-error {
  @apply absolute inset-0 flex items-center justify-center bg-black bg-opacity-70 text-white p-4 text-center;
}

.detection-summary {
  @apply mb-6;
}

.summary-title {
  @apply text-lg font-medium mb-3 text-gray-700;
}

.frames-container {
  @apply bg-gray-50 rounded-lg p-4;
  max-height: 300px;
  overflow-y: auto;
}

.frames-grid {
  @apply grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3;
}

.frame-card {
  @apply bg-white p-3 rounded shadow-sm border border-gray-200;
}

.frame-card.fire-detected {
  @apply bg-red-50 border-red-300;
}

.frame-number {
  @apply text-sm font-medium text-gray-700 mb-1;
}

.frame-status {
  @apply mb-1;
}

.status-warning {
  @apply flex items-center text-red-600 font-medium;
}

.status-safe {
  @apply flex items-center text-green-600 font-medium;
}

.frame-confidence {
  @apply text-xs text-gray-600;
}

.no-frames {
  @apply text-center py-6 text-gray-500;
}

.result-actions {
  @apply flex justify-center mt-4;
}

.restart-btn {
  @apply px-6 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition-colors;
}
</style>
