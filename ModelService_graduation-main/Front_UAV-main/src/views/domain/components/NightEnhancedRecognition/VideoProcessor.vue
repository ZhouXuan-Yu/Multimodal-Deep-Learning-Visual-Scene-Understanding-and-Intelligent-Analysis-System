<template>
  <div class="video-processor">
    <div class="upload-container" v-if="!videoUrl">
      <input 
        type="file" 
        ref="fileInput" 
        accept="video/*" 
        class="file-input" 
        @change="handleFileChange"
      />
      <div class="upload-area" @click="triggerFileInput">
        <div class="upload-icon">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-12 h-12">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        </div>
        <div class="upload-text">
          <p class="primary-text">点击或拖拽上传夜间或低光视频</p>
          <p class="secondary-text">支持 MP4, AVI 等常见视频格式</p>
        </div>
      </div>
    </div>
    
    <div v-if="videoUrl" class="preview-container">
      <video :src="videoUrl" controls class="preview-video"></video>
      <div class="video-controls">
        <button @click="removeVideo" class="control-button remove-button">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
          删除视频
        </button>
        <button @click="processVideo" class="control-button process-button" :disabled="isProcessing">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ isProcessing ? '处理中...' : '开始处理' }}
        </button>
      </div>
    </div>
    
    <!-- 增强处理选项 -->
    <div class="enhancement-options" v-if="videoUrl">
      <h3 class="options-title">增强选项</h3>
      <div class="options-grid">
        <label class="option-item">
          <input type="checkbox" v-model="options.enhanceContrast" />
          <span class="option-text">对比度增强</span>
        </label>
        <label class="option-item">
          <input type="checkbox" v-model="options.reduceLowLight" />
          <span class="option-text">低光照降噪</span>
        </label>
        <label class="option-item">
          <input type="checkbox" v-model="options.detectObjects" />
          <span class="option-text">目标检测</span>
        </label>
        <label class="option-item">
          <input type="checkbox" v-model="options.sharpening" />
          <span class="option-text">细节锐化</span>
        </label>
      </div>
    </div>
    
    <!-- 处理状态 -->
    <div v-if="processingStatus && processingStatus.status !== 'idle'" class="status-container">
      <div class="status-header">
        <div 
          class="status-badge" 
          :class="{
            'status-queued': processingStatus.status === 'queued',
            'status-processing': processingStatus.status === 'processing',
            'status-completed': processingStatus.status === 'completed',
            'status-failed': processingStatus.status === 'failed'
          }"
        >
          {{ getStatusText(processingStatus.status) }}
        </div>
        <div class="status-timestamp" v-if="processingStatus.updated_at">
          {{ formatTime(processingStatus.updated_at) }}
        </div>
      </div>
      
      <!-- 进度条 -->
      <div class="progress-container" v-if="['queued', 'processing'].includes(processingStatus.status)">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${processingProgress}%` }"></div>
        </div>
        <div class="progress-text">{{ processingStatus.message || processingProgressText }}</div>
      </div>
      
      <!-- 处理失败 -->
      <div class="error-container" v-if="processingStatus.status === 'failed'">
        <div class="error-message">{{ processingStatus.error || '处理失败，请重试' }}</div>
        <button @click="retryProcessing" class="retry-button">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          重试
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  isProcessing: {
    type: Boolean,
    default: false
  },
  processingProgress: {
    type: Number,
    default: 0
  },
  processingStatus: {
    type: Object,
    default: () => ({
      status: 'idle',
      message: '',
      error: null,
      processId: null,
      updated_at: null
    })
  }
});

const emit = defineEmits(['file-change', 'remove-video', 'process-video', 'error', 'retry']);

const fileInput = ref(null);
const videoUrl = ref(null);
const videoFile = ref(null);

// 增强选项
const options = ref({
  enhanceContrast: true,
  reduceLowLight: true,
  detectObjects: true,
  sharpening: false
});

// 计算进度文本
const processingProgressText = computed(() => {
  const progress = props.processingProgress;
  
  if (progress < 20) {
    return '正在准备视频...';
  } else if (progress < 40) {
    return '正在处理视频帧...';
  } else if (progress < 60) {
    return '正在应用图像增强...';
  } else if (progress < 80) {
    return '正在检测目标...';
  } else {
    return '正在合成结果视频...';
  }
});

// 触发文件选择
const triggerFileInput = () => {
  fileInput.value.click();
};

// 处理文件选择
const handleFileChange = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  // 验证文件类型
  if (!file.type.includes('video/')) {
    emit('error', '请上传视频文件');
    return;
  }
  
  // 验证文件大小 (最大100MB)
  if (file.size > 100 * 1024 * 1024) {
    emit('error', '视频大小不能超过100MB');
    return;
  }
  
  videoFile.value = file;
  videoUrl.value = URL.createObjectURL(file);
  
  emit('file-change', {
    file: videoFile.value,
    url: videoUrl.value,
    name: file.name
  });
};

// 删除视频
const removeVideo = () => {
  if (videoUrl.value) {
    URL.revokeObjectURL(videoUrl.value);
  }
  
  videoUrl.value = null;
  videoFile.value = null;
  
  // 重置文件输入框，确保可以重新选择同一文件
  if (fileInput.value) {
    fileInput.value.value = '';
  }
  
  emit('remove-video');
};

// 处理视频
const processVideo = () => {
  if (!videoFile.value || props.isProcessing) return;
  
  emit('process-video', {
    file: videoFile.value,
    options: options.value,
    fileName: videoFile.value.name
  });
};

// 重试处理
const retryProcessing = () => {
  emit('retry');
};

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    'idle': '等待开始',
    'queued': '队列中',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '处理失败'
  };
  
  return statusMap[status] || status;
};

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '';
  
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit'
  });
};
</script>

<style scoped>
.video-processor {
  width: 100%;
  background-color: white;
  border-radius: 0.5rem;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.upload-container {
  width: 100%;
}

.file-input {
  display: none;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  border: 2px dashed #e2e8f0;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-area:hover {
  border-color: #4f46e5;
  background-color: rgba(79, 70, 229, 0.05);
}

.upload-icon {
  color: #4f46e5;
  margin-bottom: 1rem;
}

.upload-text {
  text-align: center;
}

.primary-text {
  font-size: 1.125rem;
  font-weight: 500;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.secondary-text {
  font-size: 0.875rem;
  color: #64748b;
}

.preview-container {
  position: relative;
  width: 100%;
}

.preview-video {
  width: 100%;
  max-height: 400px;
  border-radius: 0.5rem 0.5rem 0 0;
}

.video-controls {
  display: flex;
  justify-content: space-between;
  padding: 1rem;
  background-color: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

.control-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  border: none;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.remove-button {
  background-color: #f1f5f9;
  color: #64748b;
}

.remove-button:hover {
  background-color: #e2e8f0;
  color: #334155;
}

.process-button {
  background-color: #4f46e5;
  color: white;
}

.process-button:hover:not(:disabled) {
  background-color: #4338ca;
}

.process-button:disabled {
  background-color: #c7d2fe;
  cursor: not-allowed;
}

.enhancement-options {
  padding: 1rem;
  background-color: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

.options-title {
  font-weight: 600;
  color: #334155;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
}

.options-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.option-text {
  font-size: 0.875rem;
  color: #334155;
}

.status-container {
  padding: 1rem;
  background-color: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.status-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.status-queued {
  background-color: #dbeafe;
  color: #1e40af;
}

.status-processing {
  background-color: #fef3c7;
  color: #92400e;
}

.status-completed {
  background-color: #dcfce7;
  color: #166534;
}

.status-failed {
  background-color: #fee2e2;
  color: #b91c1c;
}

.status-timestamp {
  font-size: 0.75rem;
  color: #64748b;
}

.progress-container {
  margin-top: 0.75rem;
}

.progress-bar {
  height: 0.5rem;
  background-color: #e2e8f0;
  border-radius: 0.25rem;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background-color: #4f46e5;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.875rem;
  color: #64748b;
  text-align: center;
}

.error-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.75rem;
  padding: 0.75rem;
  background-color: #fee2e2;
  border-radius: 0.25rem;
}

.error-message {
  color: #b91c1c;
  font-size: 0.875rem;
}

.retry-button {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
  border-radius: 0.25rem;
  background-color: #b91c1c;
  color: white;
  font-size: 0.75rem;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-button:hover {
  background-color: #991b1b;
}
</style>
