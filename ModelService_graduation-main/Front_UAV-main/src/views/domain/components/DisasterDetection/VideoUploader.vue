<template>
  <div class="video-uploader-container">
    <div v-if="!modelValue" class="upload-area">
      <div class="upload-prompt">
        <div class="upload-icon">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-12 h-12">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <h3 class="upload-title">上传视频文件</h3>
        <p class="upload-description">拖拽视频到此处或点击上传</p>
        <p class="upload-formats">支持格式: MP4, AVI, MOV (最大100MB)</p>
      </div>
      <input 
        type="file" 
        ref="fileInput" 
        class="file-input" 
        accept="video/mp4,video/avi,video/quicktime"
        @change="handleFileChange" 
      />
    </div>
    
    <div v-else class="selected-video-container">
      <div class="video-preview">
        <video 
          ref="videoPreview" 
          class="preview-video" 
          controls 
          :src="videoPreviewUrl"
        ></video>
      </div>
      <div class="video-info">
        <div class="file-details">
          <span class="file-name">{{ modelValue.name }}</span>
          <span class="file-size">{{ formatFileSize(modelValue.size) }}</span>
        </div>
        <div class="action-buttons">
          <button @click="onProcess" class="process-btn" :disabled="isProcessing">
            {{ isProcessing ? '处理中...' : '开始检测' }}
          </button>
          <button @click="onClear" class="clear-btn">清除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

// Props
const props = defineProps({
  modelValue: {
    type: Object,
    default: null
  },
  isProcessing: {
    type: Boolean,
    default: false
  },
  getApiUrl: {
    type: Function,
    default: (path) => path
  }
});

// Emits
const emit = defineEmits(['update:modelValue', 'process', 'clear']);

// Refs
const fileInput = ref(null);
const videoPreview = ref(null);

// Computed
const videoPreviewUrl = computed(() => {
  if (!props.modelValue) return '';
  return URL.createObjectURL(props.modelValue);
});

// Methods
const handleFileChange = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  // Check file size (100MB limit)
  if (file.size > 100 * 1024 * 1024) {
    alert('文件大小不能超过100MB');
    event.target.value = '';
    return;
  }
  
  // Check file type
  const validTypes = ['video/mp4', 'video/avi', 'video/quicktime'];
  if (!validTypes.includes(file.type)) {
    alert('请上传MP4、AVI或MOV格式的视频');
    event.target.value = '';
    return;
  }
  
  emit('update:modelValue', file);
};

const onProcess = () => {
  if (!props.modelValue) return;
  emit('process', { file: props.modelValue });
};

const onClear = () => {
  if (fileInput.value) {
    fileInput.value.value = '';
  }
  emit('update:modelValue', null);
  emit('clear');
};

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};
</script>

<style scoped>
.video-uploader-container {
  @apply w-full bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 transition-all duration-300;
}

.video-uploader-container:hover {
  @apply border-blue-400 bg-blue-50;
}

.upload-area {
  @apply flex items-center justify-center p-8 relative cursor-pointer;
  min-height: 240px;
}

.upload-prompt {
  @apply flex flex-col items-center text-center p-4;
}

.upload-icon {
  @apply text-blue-500 mb-4;
}

.upload-title {
  @apply text-xl font-semibold text-gray-800 mb-2;
}

.upload-description {
  @apply text-gray-600 mb-1;
}

.upload-formats {
  @apply text-sm text-gray-500;
}

.file-input {
  @apply absolute inset-0 w-full h-full opacity-0 cursor-pointer;
}

.selected-video-container {
  @apply p-4;
}

.video-preview {
  @apply mb-4 bg-black rounded-lg overflow-hidden;
  height: 240px;
}

.preview-video {
  @apply w-full h-full object-contain;
}

.video-info {
  @apply flex justify-between items-center;
}

.file-details {
  @apply flex flex-col;
}

.file-name {
  @apply font-medium text-gray-800 truncate;
  max-width: 240px;
}

.file-size {
  @apply text-sm text-gray-500;
}

.action-buttons {
  @apply flex space-x-2;
}

.process-btn {
  @apply px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed;
}

.clear-btn {
  @apply px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-opacity-50;
}
</style>
