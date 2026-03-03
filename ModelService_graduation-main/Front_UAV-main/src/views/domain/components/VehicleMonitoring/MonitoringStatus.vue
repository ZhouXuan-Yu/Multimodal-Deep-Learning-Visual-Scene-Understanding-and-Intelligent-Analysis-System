<script setup>
import { computed } from 'vue';

const props = defineProps({
  status: {
    type: Object,
    default: () => ({
      status: 'idle',
      progress: 0,
      message: '',
      processId: null
    })
  }
});

// 计算进度百分比
const progressPercent = computed(() => {
  return Math.round(props.status.progress * 100);
});

// 判断是否处于活动状态
const isActive = computed(() => {
  return ['uploading', 'queued', 'processing'].includes(props.status.status);
});

// 状态类
const statusClass = computed(() => {
  switch (props.status.status) {
    case 'completed':
      return 'status-success';
    case 'failed':
    case 'cancelled':
      return 'status-error';
    case 'uploading':
    case 'queued':
    case 'processing':
      return 'status-active';
    default:
      return '';
  }
});
</script>

<template>
  <div class="monitoring-status" v-if="status.status !== 'idle'">
    <div class="status-header">
      <div class="status-title" :class="statusClass">
        <svg v-if="status.status === 'completed'" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
        <svg v-else-if="status.status === 'failed' || status.status === 'cancelled'" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="15" y1="9" x2="9" y2="15"></line>
          <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>
        <svg v-else class="animate-spin" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
        </svg>
        <span class="status-text">{{ status.message }}</span>
      </div>
      <div v-if="status.processId" class="process-id">
        处理ID: {{ status.processId }}
      </div>
    </div>
    
    <div v-if="isActive" class="progress-container">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
      </div>
      <div class="progress-text">{{ progressPercent }}%</div>
    </div>
  </div>
</template>

<style scoped>
.monitoring-status {
  width: 100%;
  padding: 1.25rem;
  background-color: #f9fafb;
  border-radius: 0.5rem;
  margin-bottom: 1.5rem;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.status-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  color: #4b5563;
}

.status-success {
  color: #16a34a;
}

.status-error {
  color: #dc2626;
}

.status-active {
  color: #4f46e5;
}

.process-id {
  font-size: 0.75rem;
  color: #6b7280;
}

.progress-container {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.progress-bar {
  flex-grow: 1;
  height: 0.5rem;
  background-color: #e5e7eb;
  border-radius: 0.25rem;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: #4f46e5;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.875rem;
  color: #4b5563;
  font-weight: 500;
  min-width: 3rem;
  text-align: right;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
