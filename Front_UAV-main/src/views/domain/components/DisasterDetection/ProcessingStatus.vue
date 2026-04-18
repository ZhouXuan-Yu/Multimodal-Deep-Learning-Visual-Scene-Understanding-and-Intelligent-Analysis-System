<template>
  <div class="processing-status-container">
    <div class="status-card">
      <div class="status-header">
        <h3 class="status-title">正在处理视频</h3>
        <span class="process-id">任务ID: {{ processId }}</span>
      </div>
      
      <div class="progress-container">
        <div class="progress-bar-container">
          <div class="progress-bar" :style="{ width: `${progress}%` }"></div>
        </div>
        <div class="progress-text">{{ progress }}%</div>
      </div>
      
      <div class="status-info">
        <div class="status-message">{{ message || '正在处理中...' }}</div>
        <div class="elapsed-time">
          <span>已用时间: {{ formatTime(elapsedTime) }}</span>
        </div>
      </div>
      
      <div v-if="error" class="error-container">
        <div class="error-message">{{ error }}</div>
        <button @click="$emit('error', error)" class="retry-button">
          重试
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  processId: {
    type: String,
    required: true
  },
  progress: {
    type: Number,
    default: 0
  },
  message: {
    type: String,
    default: ''
  },
  elapsedTime: {
    type: Number,
    default: 0
  },
  error: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['complete', 'error']);

const formatTime = (seconds) => {
  if (!seconds) return '0:00';
  
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};
</script>

<style scoped>
.processing-status-container {
  @apply w-full p-4;
}

.status-card {
  @apply bg-white rounded-lg shadow-md p-6 border border-gray-200;
}

.status-header {
  @apply flex justify-between items-center mb-4;
}

.status-title {
  @apply text-xl font-semibold text-gray-800;
}

.process-id {
  @apply text-sm text-gray-500;
}

.progress-container {
  @apply flex items-center mb-6;
}

.progress-bar-container {
  @apply flex-1 bg-gray-200 rounded-full h-2.5 mr-2;
  overflow: hidden;
}

.progress-bar {
  @apply bg-blue-500 h-full rounded-full transition-all duration-300 ease-out;
}

.progress-text {
  @apply text-sm font-medium text-gray-700 w-12 text-right;
}

.status-info {
  @apply mb-4;
}

.status-message {
  @apply text-gray-700 mb-2;
}

.elapsed-time {
  @apply text-sm text-gray-500;
}

.error-container {
  @apply bg-red-50 border border-red-200 rounded-md p-3 mt-4;
}

.error-message {
  @apply text-red-600 mb-2;
}

.retry-button {
  @apply px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50;
}
</style>
