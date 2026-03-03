<template>
  <div class="image-uploader">
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
          <p class="primary-text">点击或拖拽上传图片</p>
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
        <button @click="analyzeImage" class="control-button analyze-button" :disabled="isAnalyzing">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          {{ isAnalyzing ? '分析中...' : '开始分析' }}
        </button>
      </div>
    </div>
    
    <!-- 分析模式选择 -->
    <div class="analysis-mode-container">
      <div class="mode-label">分析模式:</div>
      <div class="mode-options">
        <label class="mode-option">
          <input type="radio" v-model="analysisMode" value="normal" />
          <span class="mode-text">普通分析</span>
          <span class="mode-description">仅使用本地模型，速度更快</span>
        </label>
        <label class="mode-option">
          <input type="radio" v-model="analysisMode" value="enhanced" />
          <span class="mode-text">增强分析</span>
          <span class="mode-description">使用多模型综合分析，精度更高</span>
        </label>
      </div>
    </div>
    
    <!-- 分析进度 -->
    <div v-if="isAnalyzing" class="progress-container">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${analysisProgress}%` }"></div>
      </div>
      <div class="progress-text">{{ progressText }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import personRecognitionService from '../../services/personRecognitionService';

const props = defineProps({
  isAnalyzing: {
    type: Boolean,
    default: false
  },
  analysisProgress: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits(['file-change', 'remove-image', 'analyze', 'error']);

const fileInput = ref(null);
const imageUrl = ref(null);
const imageFile = ref(null);
const analysisMode = ref('normal');

// 计算进度文本
const progressText = computed(() => {
  if (props.analysisProgress < 25) {
    return '正在加载图片...';
  } else if (props.analysisProgress < 50) {
    return '正在检测人物...';
  } else if (props.analysisProgress < 75) {
    return '正在分析特征...';
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

// 分析图片
const analyzeImage = async () => {
  if (!imageFile.value) return;
  
  // 准备分析数据
  const analysisData = {
    file: imageFile.value,
    mode: analysisMode.value
  };
  
  try {
    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', imageFile.value);
    formData.append('mode', analysisMode.value);
    
    // 检查健康状态（可选）
    try {
      await personRecognitionService.healthCheck();
    } catch (healthError) {
      console.warn('健康检查失败，但仍将尝试进行分析:', healthError);
    }
    
    // 直接使用父组件的事件处理
    emit('analyze', analysisData);
    
  } catch (error) {
    console.error('分析处理错误:', error);
    emit('error', '图像分析失败: ' + error.message);
  }
};
</script>

<style scoped>
.image-uploader {
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
  max-height: 500px;
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

.analyze-button {
  background-color: #4f46e5;
  color: white;
}

.analyze-button:hover:not(:disabled) {
  background-color: #4338ca;
}

.analyze-button:disabled {
  background-color: #c7d2fe;
  cursor: not-allowed;
}

.analysis-mode-container {
  padding: 1rem;
  background-color: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

.mode-label {
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: #334155;
}

.mode-options {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.mode-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.mode-option:hover {
  background-color: #f1f5f9;
}

.mode-text {
  font-weight: 500;
  color: #334155;
}

.mode-description {
  font-size: 0.75rem;
  color: #64748b;
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
