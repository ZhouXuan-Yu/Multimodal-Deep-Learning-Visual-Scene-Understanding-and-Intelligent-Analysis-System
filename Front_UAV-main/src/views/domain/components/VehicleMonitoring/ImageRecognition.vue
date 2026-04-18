<script setup>
import { ref, reactive } from 'vue';
import vehicleMonitoringService from '../../services/vehicleMonitoringService';

const emit = defineEmits(['recognition-result', 'error', 'loading-change']);

const isLoading = ref(false);
const acceptedImageTypes = '.jpg,.jpeg,.png';

// 上传前检查图片
const beforeUpload = (file) => {
  // 检查文件类型
  const isImage = file.type.startsWith('image/');
  if (!isImage) {
    emit('error', '请上传图片文件，支持 JPG, JPEG, PNG 格式');
    return false;
  }
  
  // 检查文件大小（限制为 10MB）
  const isLessThan10M = file.size / 1024 / 1024 < 10;
  if (!isLessThan10M) {
    emit('error', '图片大小不能超过 10MB');
    return false;
  }
  
  return true;
};

// 处理图片上传
const handleUpload = async (event) => {
  const files = event.target.files || event.dataTransfer.files;
  if (!files || files.length === 0) return;
  
  const file = files[0];
  if (!beforeUpload(file)) return;

  // 创建FormData对象
  const formData = new FormData();
  formData.append('image', file);

  // 设置加载状态
  isLoading.value = true;
  emit('loading-change', true);
  
  try {
    // 调用API发送请求
    const response = await vehicleMonitoringService.uploadImage(formData);
    
    // 处理响应
    if (response.data && response.data.success) {
      emit('recognition-result', {
        plates: response.data.plates || [],
        imageUrl: response.data.image_url,
        timestamp: new Date().toLocaleString()
      });
    } else {
      emit('error', response.data?.message || '识别失败，请重试');
    }
  } catch (error) {
    console.error('图片上传识别失败:', error);
    emit('error', '图片上传识别失败，请检查网络连接后重试');
  } finally {
    isLoading.value = false;
    emit('loading-change', false);
    
    // 清空文件输入，允许重复选择相同文件
    const fileInput = document.getElementById('image-upload');
    if (fileInput) fileInput.value = '';
  }
};

// 模拟点击文件输入框
const triggerFileInput = () => {
  document.getElementById('image-upload').click();
};

// 处理拖放图片
const handleDrop = (event) => {
  event.preventDefault();
  event.stopPropagation();
  
  // 检查是否还在加载中
  if (isLoading.value) return;
  
  handleUpload(event);
};

// 允许拖放
const handleDragOver = (event) => {
  event.preventDefault();
  event.stopPropagation();
};
</script>

<template>
  <div 
    class="image-recognition-container"
    @drop="handleDrop"
    @dragover="handleDragOver"
  >
    <input
      id="image-upload"
      type="file"
      :accept="acceptedImageTypes"
      @change="handleUpload"
      class="hidden-input"
    />
    
    <div class="upload-area" @click="triggerFileInput">
      <div class="upload-icon">
        <svg v-if="!isLoading" xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        <div v-else class="loading-spinner"></div>
      </div>
      
      <div class="upload-text" v-if="!isLoading">
        <h3>上传图片进行车牌识别</h3>
        <p>点击此处或拖放图片文件</p>
        <p class="upload-formats">支持格式: JPG, JPEG, PNG</p>
      </div>
      <div class="upload-text" v-else>
        <h3>正在识别...</h3>
        <p>正在处理您的图片，请稍候</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.image-recognition-container {
  width: 100%;
  padding: 1.5rem;
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.hidden-input {
  display: none;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px dashed #e5e7eb;
  border-radius: 0.5rem;
  padding: 2rem;
  cursor: pointer;
  transition: all 0.2s ease-in-out;
}

.upload-area:hover {
  border-color: #4f46e5;
  background-color: rgba(79, 70, 229, 0.05);
}

.upload-icon {
  color: #6b7280;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
}

.upload-text {
  text-align: center;
}

.upload-text h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 0.5rem;
}

.upload-text p {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0.25rem 0;
}

.upload-formats {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #9ca3af;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(79, 70, 229, 0.1);
  border-radius: 50%;
  border-top-color: #4f46e5;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
