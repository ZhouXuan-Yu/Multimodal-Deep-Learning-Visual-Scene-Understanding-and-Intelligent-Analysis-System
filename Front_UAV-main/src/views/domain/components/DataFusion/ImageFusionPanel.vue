<template>
  <div class="image-fusion-panel">
    <div class="panel-container">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- 可见光图像上传 -->
        <div class="uploader-box">
          <div class="uploader-header">
            <h3 class="text-lg font-medium text-gray-700">可见光图像</h3>
            <p class="text-sm text-gray-500">支持JPG、PNG格式图像</p>
          </div>
          <div 
            class="uploader-area"
            :class="{ 'upload-active': isRGBDragActive }"
            @dragover.prevent="isRGBDragActive = true"
            @dragleave.prevent="isRGBDragActive = false"
            @drop.prevent="handleRGBDrop"
          >
            <div v-if="!rgbImageUrl" class="upload-placeholder">
              <div class="icon-container">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-10 h-10">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <p class="mt-2 text-sm text-gray-600">拖放图像至此处或</p>
              <label for="rgb-file-upload" class="select-file-btn">
                选择文件
                <input 
                  id="rgb-file-upload" 
                  type="file" 
                  accept="image/*" 
                  class="hidden" 
                  @change="handleRGBImageChange"
                />
              </label>
            </div>
            <div v-else class="uploaded-image-container">
              <img :src="rgbImageUrl" class="uploaded-image" alt="可见光图像" />
              <button @click="removeRGBImage" class="remove-btn">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- 热成像图像上传 -->
        <div class="uploader-box">
          <div class="uploader-header">
            <h3 class="text-lg font-medium text-gray-700">热成像图像</h3>
            <p class="text-sm text-gray-500">支持JPG、PNG格式图像</p>
          </div>
          <div 
            class="uploader-area"
            :class="{ 'upload-active': isThermalDragActive }"
            @dragover.prevent="isThermalDragActive = true"
            @dragleave.prevent="isThermalDragActive = false"
            @drop.prevent="handleThermalDrop"
          >
            <div v-if="!thermalImageUrl" class="upload-placeholder">
              <div class="icon-container">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-10 h-10">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <p class="mt-2 text-sm text-gray-600">拖放图像至此处或</p>
              <label for="thermal-file-upload" class="select-file-btn">
                选择文件
                <input 
                  id="thermal-file-upload" 
                  type="file" 
                  accept="image/*" 
                  class="hidden" 
                  @change="handleThermalImageChange"
                />
              </label>
            </div>
            <div v-else class="uploaded-image-container">
              <img :src="thermalImageUrl" class="uploaded-image" alt="热成像图像" />
              <button @click="removeThermalImage" class="remove-btn">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 融合参数设置 -->
      <div class="parameters-container">
        <div class="parameters-header">
          <h3 class="parameters-title">融合参数</h3>
        </div>
        <div class="parameters-content">
          <div class="parameter-row">
            <div class="parameter-label">RGB权重:</div>
            <div class="parameter-control">
              <input 
                type="range" 
                min="0" 
                max="100" 
                step="5" 
                v-model="rgbWeight" 
                class="parameter-slider"
              />
              <div class="parameter-value">{{ rgbWeight }}%</div>
            </div>
          </div>
          <div class="parameter-row">
            <div class="parameter-label">热成像权重:</div>
            <div class="parameter-control">
              <input 
                type="range" 
                min="0" 
                max="100" 
                step="5" 
                v-model="thermalWeight" 
                class="parameter-slider"
              />
              <div class="parameter-value">{{ thermalWeight }}%</div>
            </div>
          </div>
          <div class="parameter-row">
            <div class="parameter-label">增强等级:</div>
            <div class="parameter-control enhancement-buttons">
              <button 
                v-for="level in enhancementLevels" 
                :key="level.value"
                @click="selectedEnhancement = level.value"
                :class="{ 'selected': selectedEnhancement === level.value }"
                class="enhancement-button"
              >
                {{ level.label }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 进度条 -->
      <div v-if="isProcessing" class="progress-container">
        <div class="progress-info">{{ processingProgress }}% 处理中...</div>
        <div class="progress-bar-container">
          <div class="progress-bar" :style="{ width: `${processingProgress}%` }"></div>
        </div>
      </div>

      <!-- 控制按钮 -->
      <div class="controls-container" v-if="rgbImageUrl || thermalImageUrl">
        <button 
          @click="clearImages" 
          class="clear-btn"
        >
          清除图片
        </button>
        <button 
          @click="processFusion" 
          class="process-btn"
          :class="{ 'processing': isProcessing }"
          :disabled="!canProcess || isProcessing"
        >
          {{ isProcessing ? '处理中...' : '开始融合' }}
          <div v-if="isProcessing" class="spinner"></div>
        </button>
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
  }
});

// 事件定义
const emit = defineEmits([
  'process-fusion',
  'error'
]);

// 状态变量
const rgbImageFile = ref(null);
const rgbImageUrl = ref('');
const thermalImageFile = ref(null);
const thermalImageUrl = ref('');
const isRGBDragActive = ref(false);
const isThermalDragActive = ref(false);

// 融合参数
const rgbWeight = ref(50);
const thermalWeight = ref(50);
const enhancementLevels = [
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' }
];
const selectedEnhancement = ref('medium');

// 计算是否可以处理
const canProcess = computed(() => {
  return rgbImageFile.value && thermalImageFile.value;
});

// 处理可见光图像变更
const handleRGBImageChange = (event) => {
  const file = event.target.files[0];
  if (file) {
    processRGBFile(file);
  }
};

// 处理热成像图像变更
const handleThermalImageChange = (event) => {
  const file = event.target.files[0];
  if (file) {
    processThermalFile(file);
  }
};

// 处理可见光拖放
const handleRGBDrop = (event) => {
  isRGBDragActive.value = false;
  const file = event.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) {
    processRGBFile(file);
  } else {
    emit('error', '请上传有效的图像文件');
  }
};

// 处理热成像拖放
const handleThermalDrop = (event) => {
  isThermalDragActive.value = false;
  const file = event.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) {
    processThermalFile(file);
  } else {
    emit('error', '请上传有效的图像文件');
  }
};

// 处理RGB文件
const processRGBFile = (file) => {
  // 验证文件类型
  if (!file.type.match('image.*')) {
    emit('error', '请上传有效的图像文件');
    return;
  }

  // 验证文件大小 (小于20MB)
  if (file.size > 20 * 1024 * 1024) {
    emit('error', '图像文件过大，请上传小于20MB的文件');
    return;
  }

  rgbImageFile.value = file;
  rgbImageUrl.value = URL.createObjectURL(file);
};

// 处理热成像文件
const processThermalFile = (file) => {
  // 验证文件类型
  if (!file.type.match('image.*')) {
    emit('error', '请上传有效的图像文件');
    return;
  }

  // 验证文件大小 (小于20MB)
  if (file.size > 20 * 1024 * 1024) {
    emit('error', '图像文件过大，请上传小于20MB的文件');
    return;
  }

  thermalImageFile.value = file;
  thermalImageUrl.value = URL.createObjectURL(file);
};

// 移除可见光图像
const removeRGBImage = () => {
  if (rgbImageUrl.value) {
    URL.revokeObjectURL(rgbImageUrl.value);
  }
  rgbImageFile.value = null;
  rgbImageUrl.value = '';
};

// 移除热成像图像
const removeThermalImage = () => {
  if (thermalImageUrl.value) {
    URL.revokeObjectURL(thermalImageUrl.value);
  }
  thermalImageFile.value = null;
  thermalImageUrl.value = '';
};

// 清除所有图像
const clearImages = () => {
  removeRGBImage();
  removeThermalImage();
};

// 处理融合
const processFusion = () => {
  if (!canProcess.value) {
    emit('error', '请上传可见光和热成像图像');
    return;
  }

  const formData = new FormData();
  formData.append('rgb_image', rgbImageFile.value);
  formData.append('thermal_image', thermalImageFile.value);
  formData.append('rgb_weight', rgbWeight.value);
  formData.append('thermal_weight', thermalWeight.value);
  formData.append('enhancement_level', selectedEnhancement.value);
  
  emit('process-fusion', {
    formData,
    rgbFile: rgbImageFile.value,
    thermalFile: thermalImageFile.value,
    parameters: {
      rgbWeight: rgbWeight.value,
      thermalWeight: thermalWeight.value,
      enhancementLevel: selectedEnhancement.value
    }
  });
};

// 监听RGB权重改变，自动更新热成像权重
watch(rgbWeight, (newValue) => {
  thermalWeight.value = 100 - newValue;
});

// 监听热成像权重改变，自动更新RGB权重
watch(thermalWeight, (newValue) => {
  rgbWeight.value = 100 - newValue;
});
</script>

<style scoped>
.image-fusion-panel {
  width: 100%;
}

.panel-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
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

.uploaded-image-container {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.uploaded-image {
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

.parameters-container {
  background-color: white;
  border-radius: 0.5rem;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.parameters-header {
  padding: 1rem;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.parameters-title {
  font-size: 1.125rem;
  font-weight: 500;
  color: #334155;
}

.parameters-content {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.parameter-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.parameter-label {
  width: 6rem;
  font-weight: 500;
  color: #334155;
}

.parameter-control {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.parameter-slider {
  flex: 1;
  height: 0.5rem;
  background-color: #e2e8f0;
  border-radius: 9999px;
  -webkit-appearance: none;
  appearance: none;
  outline: none;
}

.parameter-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 50%;
  background: #4f46e5;
  cursor: pointer;
}

.parameter-slider::-moz-range-thumb {
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 50%;
  background: #4f46e5;
  cursor: pointer;
  border: none;
}

.parameter-value {
  width: 3.5rem;
  text-align: right;
  font-weight: 500;
  color: #4b5563;
}

.enhancement-buttons {
  display: flex;
  gap: 0.5rem;
}

.enhancement-button {
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  border: 1px solid #e2e8f0;
  background-color: white;
  color: #4b5563;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.enhancement-button:hover {
  background-color: #f8fafc;
}

.enhancement-button.selected {
  background-color: #4f46e5;
  color: white;
  border-color: #4f46e5;
}

.progress-container {
  margin-top: 1rem;
}

.progress-info {
  font-size: 0.875rem;
  font-weight: 500;
  color: #4b5563;
  margin-bottom: 0.5rem;
}

.progress-bar-container {
  height: 0.5rem;
  background-color: #e2e8f0;
  border-radius: 9999px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: #4f46e5;
  border-radius: 9999px;
  transition: width 0.3s ease;
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

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
