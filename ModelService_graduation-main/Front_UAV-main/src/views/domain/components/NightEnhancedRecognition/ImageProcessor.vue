<template>
  <div class="image-processor">
    <div class="upload-container" v-if="!imageUrl">
      <input 
        type="file" 
        ref="fileInput" 
        accept="image/*" 
        class="file-input" 
        @change="handleFileChange"
      />
      <div class="upload-area" @click="triggerFileInput">
        <div class="upload-icon">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-12 h-12">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <div class="upload-text">
          <p class="primary-text">点击或拖拽上传夜间或低光图片</p>
          <p class="secondary-text">支持 JPG, PNG 等常见图片格式</p>
        </div>
      </div>
    </div>
    
    <div v-if="imageUrl" class="preview-container">
      <img :src="imageUrl" alt="上传预览" class="preview-image" />
      <div class="image-controls">
        <button @click="removeImage" class="control-button remove-button">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
          删除图片
        </button>
        <button @click="processImage" class="control-button process-button" :disabled="isProcessing">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ isProcessing ? '处理中...' : '开始处理' }}
        </button>
      </div>
    </div>
    
    <!-- 增强处理选项 -->
    <div class="enhancement-options" v-if="imageUrl">
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
    
    <!-- 处理进度 -->
    <div v-if="isProcessing" class="progress-container">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${processingProgress}%` }"></div>
      </div>
      <div class="progress-text">{{ processingProgressText }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import nightEnhancementService from '../../services/nightEnhancementService';

const props = defineProps({
  isProcessing: {
    type: Boolean,
    default: false
  },
  processingProgress: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits(['file-change', 'remove-image', 'process-image', 'error']);

const fileInput = ref(null);
const imageUrl = ref(null);
const imageFile = ref(null);

// 增强选项
const options = ref({
  enhanceContrast: true,
  reduceLowLight: true,
  detectObjects: true,
  sharpening: false
});

// 计算进度文本
const processingProgressText = computed(() => {
  if (props.processingProgress < 25) {
    return '正在加载图片...';
  } else if (props.processingProgress < 50) {
    return '正在增强图像...';
  } else if (props.processingProgress < 75) {
    return '正在检测目标...';
  } else {
    return '正在生成结果...';
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
  if (!file.type.includes('image/')) {
    emit('error', '请上传图片文件');
    return;
  }
  
  // 验证文件大小 (最大10MB)
  if (file.size > 10 * 1024 * 1024) {
    emit('error', '图片大小不能超过10MB');
    return;
  }
  
  imageFile.value = file;
  const reader = new FileReader();
  
  reader.onload = (e) => {
    imageUrl.value = e.target.result;
    emit('file-change', {
      file: imageFile.value,
      url: imageUrl.value
    });
  };
  
  reader.readAsDataURL(file);
};

// 删除图片
const removeImage = () => {
  imageUrl.value = null;
  imageFile.value = null;
  
  // 重置文件输入框，确保可以重新选择同一文件
  if (fileInput.value) {
    fileInput.value.value = '';
  }
  
  emit('remove-image');
};

// 处理图片
const processImage = () => {
  if (!imageFile.value || props.isProcessing) return;
  
  emit('process-image', {
    file: imageFile.value,
    options: options.value
  });
};
</script>

<style scoped>
.image-processor {
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

.preview-image {
  width: 100%;
  max-height: 400px;
  object-fit: contain;
  border-radius: 0.5rem 0.5rem 0 0;
}

.image-controls {
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

.progress-container {
  padding: 1rem;
  background-color: #f8fafc;
  border-top: 1px solid #e2e8f0;
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
</style>
