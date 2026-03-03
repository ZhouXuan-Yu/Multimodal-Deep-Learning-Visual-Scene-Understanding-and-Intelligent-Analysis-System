<template>
  <div class="dual-video-uploader">
    <div class="uploader-container">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- 可见光视频上传 -->
        <div class="uploader-box">
          <div class="uploader-header">
            <h3 class="text-lg font-medium text-gray-700">可见光视频</h3>
            <p class="text-sm text-gray-500">支持MP4、AVI格式，100MB以内</p>
          </div>
          <div 
            class="uploader-area"
            :class="{ 'upload-active': isRGBDragActive }"
            @dragover.prevent="isRGBDragActive = true"
            @dragleave.prevent="isRGBDragActive = false"
            @drop.prevent="handleRGBDrop"
          >
            <div v-if="!rgbVideoUrl" class="upload-placeholder">
              <div class="icon-container">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-10 h-10">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <p class="mt-2 text-sm text-gray-600">拖放视频至此处或</p>
              <label for="rgb-video-upload" class="select-file-btn">
                选择文件
                <input 
                  id="rgb-video-upload" 
                  type="file" 
                  accept="video/*" 
                  class="hidden" 
                  @change="handleRGBVideoChange"
                />
              </label>
            </div>
            <div v-else class="uploaded-video-container">
              <video :src="rgbVideoUrl" class="uploaded-video" controls></video>
              <button @click="removeRGBVideo" class="remove-btn">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- 热成像视频上传 -->
        <div class="uploader-box">
          <div class="uploader-header">
            <h3 class="text-lg font-medium text-gray-700">热成像视频 (可选)</h3>
            <p class="text-sm text-gray-500">支持MP4、AVI格式，100MB以内</p>
          </div>
          <div 
            class="uploader-area"
            :class="{ 'upload-active': isThermalDragActive }"
            @dragover.prevent="isThermalDragActive = true"
            @dragleave.prevent="isThermalDragActive = false"
            @drop.prevent="handleThermalDrop"
          >
            <div v-if="!thermalVideoUrl" class="upload-placeholder">
              <div class="icon-container">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-10 h-10">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <p class="mt-2 text-sm text-gray-600">拖放视频至此处或</p>
              <label for="thermal-video-upload" class="select-file-btn">
                选择文件
                <input 
                  id="thermal-video-upload" 
                  type="file" 
                  accept="video/*" 
                  class="hidden" 
                  @change="handleThermalVideoChange"
                />
              </label>
            </div>
            <div v-else class="uploaded-video-container">
              <video :src="thermalVideoUrl" class="uploaded-video" controls></video>
              <button @click="removeThermalVideo" class="remove-btn">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 控制按钮 -->
      <div class="controls-container" v-if="rgbVideoUrl || thermalVideoUrl">
        <button 
          @click="clearVideos" 
          class="clear-btn"
        >
          清除视频
        </button>
        <button 
          @click="processVideos" 
          class="process-btn"
          :class="{ 'processing': isProcessing }"
          :disabled="!canProcess || isProcessing"
        >
          {{ isProcessing ? '处理中...' : '开始处理' }}
          <div v-if="isProcessing" class="spinner"></div>
        </button>
      </div>

      <!-- 处理进度 -->
      <div v-if="isProcessing || processingStatus" class="progress-container">
        <div class="progress-card">
          <div class="progress-header">
            <h4 class="progress-title">处理状态: {{ getStatusText }}</h4>
          </div>
          <div class="progress-bar-container">
            <div class="progress-bar" :style="{ width: `${processingProgress}%` }"></div>
          </div>
          <div class="progress-info">{{ processingProgress }}% {{ processingStatus }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

// 属性定义
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
    type: String,
    default: ''
  }
});

// 事件定义
const emit = defineEmits([
  'file-change', 
  'remove-video', 
  'process-videos', 
  'clear-videos',
  'retry',
  'error'
]);

// 状态变量
const rgbVideoFile = ref(null);
const rgbVideoUrl = ref('');
const thermalVideoFile = ref(null);
const thermalVideoUrl = ref('');
const isRGBDragActive = ref(false);
const isThermalDragActive = ref(false);

// 计算属性
const canProcess = computed(() => {
  return rgbVideoFile.value; // 仅要求RGB视频，热成像视频可选
});

const getStatusText = computed(() => {
  if (props.processingStatus === 'completed') return '已完成';
  if (props.processingStatus === 'failed') return '处理失败';
  return '处理中';
});

// 处理可见光视频变更
const handleRGBVideoChange = (event) => {
  const file = event.target.files[0];
  if (file) {
    processRGBFile(file);
  }
};

// 处理热成像视频变更
const handleThermalVideoChange = (event) => {
  const file = event.target.files[0];
  if (file) {
    processThermalFile(file);
  }
};

// 处理可见光拖放
const handleRGBDrop = (event) => {
  isRGBDragActive.value = false;
  const file = event.dataTransfer.files[0];
  if (file && file.type.startsWith('video/')) {
    processRGBFile(file);
  } else {
    emit('error', '请上传有效的视频文件');
  }
};

// 处理热成像拖放
const handleThermalDrop = (event) => {
  isThermalDragActive.value = false;
  const file = event.dataTransfer.files[0];
  if (file && file.type.startsWith('video/')) {
    processThermalFile(file);
  } else {
    emit('error', '请上传有效的视频文件');
  }
};

// 处理RGB文件
const processRGBFile = (file) => {
  // 验证文件类型
  if (!file.type.match('video.*')) {
    emit('error', '请上传有效的视频文件');
    return;
  }

  // 验证文件大小 (小于100MB)
  if (file.size > 100 * 1024 * 1024) {
    emit('error', '视频文件过大，请上传小于100MB的文件');
    return;
  }

  rgbVideoFile.value = file;
  rgbVideoUrl.value = URL.createObjectURL(file);
  emit('file-change', { type: 'rgb', file });
};

// 处理热成像文件
const processThermalFile = (file) => {
  // 验证文件类型
  if (!file.type.match('video.*')) {
    emit('error', '请上传有效的视频文件');
    return;
  }

  // 验证文件大小 (小于100MB)
  if (file.size > 100 * 1024 * 1024) {
    emit('error', '视频文件过大，请上传小于100MB的文件');
    return;
  }

  thermalVideoFile.value = file;
  thermalVideoUrl.value = URL.createObjectURL(file);
  emit('file-change', { type: 'thermal', file });
};

// 移除可见光视频
const removeRGBVideo = () => {
  if (rgbVideoUrl.value) {
    URL.revokeObjectURL(rgbVideoUrl.value);
  }
  rgbVideoFile.value = null;
  rgbVideoUrl.value = '';
  emit('remove-video', 'rgb');
};

// 移除热成像视频
const removeThermalVideo = () => {
  if (thermalVideoUrl.value) {
    URL.revokeObjectURL(thermalVideoUrl.value);
  }
  thermalVideoFile.value = null;
  thermalVideoUrl.value = '';
  emit('remove-video', 'thermal');
};

// 清除所有视频
const clearVideos = () => {
  removeRGBVideo();
  removeThermalVideo();
  emit('clear-videos');
};

// 开始处理视频
const processVideos = () => {
  if (!canProcess.value) {
    emit('error', '请至少上传可见光视频');
    return;
  }

  const formData = new FormData();
  formData.append('rgb_video', rgbVideoFile.value);
  
  if (thermalVideoFile.value) {
    formData.append('thermal_video', thermalVideoFile.value);
  }
  
  emit('process-videos', formData);
};

// 在组件销毁时释放URL对象
watch(() => props.isProcessing, (newVal, oldVal) => {
  if (oldVal && !newVal && props.processingStatus === 'failed') {
    // 处理失败时可能需要重试
  }
});
</script>

<style scoped>
.dual-video-uploader {
  width: 100%;
}

.uploader-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.uploader-box {
  border-radius: 0.5rem;
  overflow: hidden;
  background-color: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.uploader-header {
  padding: 1rem;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.uploader-area {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 240px;
  border: 2px dashed #cbd5e1;
  border-radius: 0.375rem;
  transition: all 0.2s;
  cursor: pointer;
  position: relative;
}

.uploader-area:hover {
  border-color: #94a3b8;
}

.upload-active {
  border-color: #4f46e5;
  background-color: rgba(79, 70, 229, 0.05);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.icon-container {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 9999px;
  background-color: #f1f5f9;
  color: #64748b;
}

.select-file-btn {
  margin-top: 0.5rem;
  padding: 0.375rem 0.75rem;
  background-color: #f1f5f9;
  color: #1e293b;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.select-file-btn:hover {
  background-color: #e2e8f0;
}

.uploaded-video-container {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.uploaded-video {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.remove-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  width: 2rem;
  height: 2rem;
  border-radius: 9999px;
  background-color: rgba(15, 23, 42, 0.7);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.remove-btn:hover {
  background-color: rgba(15, 23, 42, 0.9);
}

.controls-container {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-top: 1rem;
}

.clear-btn {
  padding: 0.625rem 1.25rem;
  background-color: #ef4444;
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-btn:hover {
  background-color: #dc2626;
}

.process-btn {
  padding: 0.625rem 1.25rem;
  background-color: #4f46e5;
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.process-btn:hover:not(:disabled) {
  background-color: #4338ca;
}

.process-btn:disabled {
  background-color: #a5b4fc;
  cursor: not-allowed;
}

.processing {
  position: relative;
}

.spinner {
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 0.8s linear infinite;
}

.progress-container {
  margin-top: 1.5rem;
}

.progress-card {
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.25rem;
}

.progress-header {
  margin-bottom: 1rem;
}

.progress-title {
  font-size: 1rem;
  font-weight: 500;
  color: #334155;
}

.progress-bar-container {
  height: 0.75rem;
  background-color: #f1f5f9;
  border-radius: 9999px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-bar {
  height: 100%;
  background-color: #4f46e5;
  border-radius: 9999px;
  transition: width 0.5s ease;
}

.progress-info {
  font-size: 0.875rem;
  color: #64748b;
  text-align: right;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
