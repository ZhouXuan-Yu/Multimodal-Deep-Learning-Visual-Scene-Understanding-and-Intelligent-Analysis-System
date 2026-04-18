<template>
  <div class="image-detection-container">
    <div class="image-upload-area" v-if="!imageResult">
      <h3 class="section-title">上传图像进行火灾检测</h3>
      
      <div class="image-uploader">
        <div 
          class="uploader-area" 
          :class="{ 'has-image': imageUrl }"
          @click="triggerFileInput"
          @dragover.prevent
          @drop.prevent="handleFileDrop"
        >
          <img v-if="imageUrl" :src="imageUrl" class="preview-image" />
          <div v-else class="upload-placeholder">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="upload-icon">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <div class="upload-text">点击或拖拽上传图像</div>
          </div>
        </div>
        <input 
          type="file" 
          ref="fileInput" 
          class="file-input-hidden" 
          accept="image/jpeg,image/png,image/gif"
          @change="handleImageChange"
        />
      </div>
      
      <div class="image-actions">
        <button 
          class="detect-btn" 
          @click="uploadImageForDetection" 
          :disabled="!imageFile || processing"
          :class="{ 'loading': processing }"
        >
          <span v-if="!processing">检测火灾</span>
          <span v-else class="loading-text">
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            处理中...
          </span>
        </button>
        <button 
          class="reset-btn" 
          @click="resetImageDetection" 
          :disabled="!imageFile && !imageResult"
        >
          重置
        </button>
      </div>
    </div>
    
    <div v-if="imageResult" class="image-result-area">
      <div class="result-header">
        <h3 class="result-title">检测结果</h3>
        <div 
          class="result-status" 
          :class="{ 'fire-detected': imageResult.fire_detected }"
        >
          <svg v-if="imageResult.fire_detected" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="status-icon">
            <path fill-rule="evenodd" d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z" clip-rule="evenodd" />
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="status-icon">
            <path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm13.36-1.814a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clip-rule="evenodd" />
          </svg>
          {{ imageResult.fire_detected ? '火灾警告!' : '未检测到火灾' }}
        </div>
      </div>
      
      <div class="result-images">
        <div class="image-comparison">
          <div class="original-image">
            <h4 class="image-label">原始图像</h4>
            <div class="image-container">
              <img :src="imageUrl" class="result-img" />
            </div>
          </div>
          
          <div class="detected-image">
            <h4 class="image-label">检测结果</h4>
            <div class="image-container">
              <img 
                :src="imageResult.result_image_url" 
                class="result-img" 
                @error="handleResultImageError" 
                @load="resultImageError = false"
              />
            </div>
          </div>
        </div>
      </div>
      
      <div class="detection-details">
        <div class="detail-item">
          <span class="detail-label">检测时间:</span>
          <span class="detail-value">{{ imageResult.processing_time.toFixed(2) }}秒</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">火灾可能性:</span>
          <span class="detail-value">{{ (imageResult.confidence * 100).toFixed(2) }}%</span>
        </div>
        <div class="detail-item" v-if="imageResult.affected_area_percentage">
          <span class="detail-label">影响区域:</span>
          <span class="detail-value">{{ (imageResult.affected_area_percentage * 100).toFixed(2) }}% 的图像区域</span>
        </div>
      </div>
      
      <div class="result-actions">
        <button class="new-detection-btn" @click="resetImageDetection">新的检测</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import disasterDetectionService from '../../services/disasterDetectionService';

const emit = defineEmits(['detection-complete']);

// 状态变量
const imageFile = ref(null);
const imageUrl = ref('');
const processing = ref(false);
const imageResult = ref(null);
const resultImageError = ref(false);
const fileInput = ref(null);

// 处理图片上传
const handleImageChange = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = (e) => {
    imageUrl.value = e.target.result;
    imageFile.value = file;
  };
  reader.readAsDataURL(file);
};

// 处理文件拖放
const handleFileDrop = (event) => {
  const file = event.dataTransfer.files[0];
  if (!file || !file.type.startsWith('image/')) return;
  
  const reader = new FileReader();
  reader.onload = (e) => {
    imageUrl.value = e.target.result;
    imageFile.value = file;
  };
  reader.readAsDataURL(file);
};

// 触发文件输入
const triggerFileInput = () => {
  fileInput.value.click();
};

// 上传图片进行检测
const uploadImageForDetection = async () => {
  if (!imageFile.value) return;
  
  processing.value = true;
  resultImageError.value = false;
  
  try {
    const formData = new FormData();
    formData.append('image', imageFile.value);
    
    const response = await disasterDetectionService.uploadImageForDetection(formData);
    
    if (response.data) {
      imageResult.value = {
        ...response.data,
        result_image_url: disasterDetectionService.getApiUrl(`/results/${response.data.id}/image`)
      };
      
      emit('detection-complete', imageResult.value);
    }
  } catch (error) {
    console.error('火灾检测失败:', error);
    alert(`检测失败: ${error.response?.data?.message || error.message || '未知错误'}`);
  } finally {
    processing.value = false;
  }
};

// 重置图像检测
const resetImageDetection = () => {
  imageFile.value = null;
  imageUrl.value = '';
  imageResult.value = null;
  resultImageError.value = false;
  if (fileInput.value) {
    fileInput.value.value = '';
  }
};

// 处理结果图像加载错误
const handleResultImageError = () => {
  resultImageError.value = true;
};
</script>

<style scoped>
.image-detection-container {
  @apply w-full;
}

.section-title {
  @apply text-xl font-semibold text-gray-800 mb-4;
}

.image-upload-area {
  @apply mb-8;
}

.image-uploader {
  @apply mb-4;
}

.uploader-area {
  @apply bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer overflow-hidden transition-all duration-300;
  height: 300px;
}

.uploader-area:hover {
  @apply border-blue-400 bg-blue-50;
}

.uploader-area.has-image {
  @apply border-solid border-gray-300;
}

.preview-image {
  @apply w-full h-full object-contain;
}

.upload-placeholder {
  @apply flex flex-col items-center justify-center h-full p-6;
}

.upload-icon {
  @apply w-16 h-16 text-blue-500 mb-4;
}

.upload-text {
  @apply text-gray-500 text-center;
}

.file-input-hidden {
  @apply hidden;
}

.image-actions {
  @apply flex space-x-3;
}

.detect-btn {
  @apply px-6 py-3 bg-blue-500 text-white rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center;
  min-width: 120px;
}

.detect-btn.loading {
  @apply bg-blue-600;
}

.loading-text {
  @apply flex items-center;
}

.reset-btn {
  @apply px-6 py-3 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed;
}

.image-result-area {
  @apply bg-white rounded-lg;
}

.result-header {
  @apply flex justify-between items-center mb-6;
}

.result-title {
  @apply text-xl font-semibold text-gray-800;
}

.result-status {
  @apply flex items-center px-4 py-2 rounded font-medium text-green-700 bg-green-100;
}

.result-status.fire-detected {
  @apply text-red-700 bg-red-100;
}

.status-icon {
  @apply w-5 h-5 mr-2;
}

.result-images {
  @apply mb-6;
}

.image-comparison {
  @apply grid grid-cols-1 md:grid-cols-2 gap-4;
}

.original-image, .detected-image {
  @apply flex flex-col;
}

.image-label {
  @apply text-lg font-medium mb-2 text-gray-700;
}

.image-container {
  @apply bg-black rounded-lg overflow-hidden relative;
  height: 300px;
}

.result-img {
  @apply w-full h-full object-contain;
}

.image-error-overlay {
  @apply absolute inset-0 flex items-center justify-center bg-black bg-opacity-70 text-white;
}

.detection-details {
  @apply grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg mb-6;
}

.detail-item {
  @apply flex flex-col;
}

.detail-label {
  @apply text-sm text-gray-500 mb-1;
}

.detail-value {
  @apply font-medium text-gray-800;
}

.result-actions {
  @apply flex justify-center;
}

.new-detection-btn {
  @apply px-6 py-3 bg-blue-500 text-white rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50;
}
</style>
