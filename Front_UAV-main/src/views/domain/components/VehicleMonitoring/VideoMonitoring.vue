<script setup>
import { ref, watch } from 'vue';
import vehicleMonitoringService from '../../services/vehicleMonitoringService';

const props = defineProps({
  targetPlate: {
    type: Object,
    default: () => null
  },
  disabled: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['monitoring-result', 'status-update', 'error', 'loading-change']);

const isUploading = ref(false);
const acceptedVideoTypes = '.mp4,.avi,.mov';
const progressCheckInterval = ref(null);
const processId = ref(null);

// 监视目标车牌变化
watch(() => props.targetPlate, (newValue) => {
  // 如果目标车牌被清除，同时有正在进行的进度检查，则停止
  if (!newValue && progressCheckInterval.value) {
    clearInterval(progressCheckInterval.value);
    progressCheckInterval.value = null;
  }
}, { deep: true });

// 上传前检查视频
const beforeUpload = (file) => {
  // 检查是否有目标车牌
  if (!props.targetPlate || !props.targetPlate.plate_no) {
    emit('error', '请先设置目标车牌');
    return false;
  }
  
  // 检查文件类型
  const isVideo = file.type.startsWith('video/');
  if (!isVideo) {
    emit('error', '请上传视频文件，支持 MP4, AVI, MOV 格式');
    return false;
  }
  
  // 检查文件大小（限制为 100MB）
  const isLessThan100M = file.size / 1024 / 1024 < 100;
  if (!isLessThan100M) {
    emit('error', '视频大小不能超过 100MB');
    return false;
  }
  
  return true;
};

// 处理视频上传
const handleUpload = async (event) => {
  const files = event.target.files || event.dataTransfer.files;
  if (!files || files.length === 0) return;
  
  const file = files[0];
  if (!beforeUpload(file)) return;

  // 创建FormData对象
  const formData = new FormData();
  formData.append('video', file);
  formData.append('target_plate', props.targetPlate.plate_no);
  if (props.targetPlate.plate_color) {
    formData.append('plate_color', props.targetPlate.plate_color);
  }

  // 设置加载状态
  isUploading.value = true;
  emit('loading-change', true);
  emit('status-update', { 
    status: 'uploading', 
    progress: 0, 
    message: '正在上传视频...'
  });
  
  try {
    // 调用API发送请求
    const response = await vehicleMonitoringService.uploadMonitorVideo(formData);
    
    // 处理响应
    if (response.data && response.data.success) {
      processId.value = response.data.process_id;
      
      emit('status-update', { 
        status: 'processing', 
        progress: 0, 
        message: '视频已上传，开始分析...',
        processId: processId.value
      });
      
      // 开始检查进度
      startProgressCheck();
    } else {
      emit('error', response.data?.message || '上传失败，请重试');
      isUploading.value = false;
      emit('loading-change', false);
    }
  } catch (error) {
    console.error('视频上传失败:', error);
    emit('error', '视频上传失败，请检查网络连接后重试');
    isUploading.value = false;
    emit('loading-change', false);
  } finally {
    // 清空文件输入，允许重复选择相同文件
    const fileInput = document.getElementById('video-upload');
    if (fileInput) fileInput.value = '';
  }
};

// 开始检查进度
const startProgressCheck = () => {
  // 先清除可能存在的旧计时器
  if (progressCheckInterval.value) {
    clearInterval(progressCheckInterval.value);
  }
  
  // 设置新的计时器，每3秒检查一次进度
  progressCheckInterval.value = setInterval(checkProgress, 3000);
  
  // 立即执行一次检查
  checkProgress();
};

// 检查处理进度
const checkProgress = async () => {
  if (!processId.value) return;
  
  try {
    const response = await vehicleMonitoringService.getMonitorStatus(processId.value);
    
    if (response.data && response.data.success) {
      const status = response.data.status;
      const progress = response.data.progress || 0;
      
      // 更新状态
      emit('status-update', {
        status: status,
        progress: progress,
        message: getStatusMessage(status, progress),
        processId: processId.value
      });
      
      // 如果处理完成或失败，获取结果并停止检查
      if (status === 'completed') {
        clearInterval(progressCheckInterval.value);
        progressCheckInterval.value = null;
        
        // 获取结果
        const resultsResponse = await vehicleMonitoringService.getMonitorResults(processId.value);
        
        if (resultsResponse.data && resultsResponse.data.success) {
          // 发送结果
          emit('monitoring-result', resultsResponse.data);
        } else {
          emit('error', '获取监控结果失败');
        }
        
        isUploading.value = false;
        emit('loading-change', false);
      } else if (status === 'failed') {
        clearInterval(progressCheckInterval.value);
        progressCheckInterval.value = null;
        emit('error', '视频处理失败: ' + (response.data.message || '未知错误'));
        isUploading.value = false;
        emit('loading-change', false);
      }
    }
  } catch (error) {
    console.error('检查进度失败:', error);
    emit('status-update', {
      status: 'unknown',
      progress: 0,
      message: '检查进度失败，重试中...',
      processId: processId.value
    });
  }
};

// 根据状态获取消息
const getStatusMessage = (status, progress) => {
  switch (status) {
    case 'uploading':
      return '正在上传视频...';
    case 'queued':
      return '视频已上传，等待处理...';
    case 'processing':
      return `正在处理视频 (${Math.round(progress * 100)}%)`;
    case 'completed':
      return '处理完成';
    case 'failed':
      return '处理失败';
    default:
      return '未知状态';
  }
};

// 取消上传/处理
const cancelProcessing = () => {
  if (progressCheckInterval.value) {
    clearInterval(progressCheckInterval.value);
    progressCheckInterval.value = null;
  }
  
  isUploading.value = false;
  emit('loading-change', false);
  emit('status-update', {
    status: 'cancelled',
    progress: 0,
    message: '操作已取消'
  });
};

// 模拟点击文件输入框
const triggerFileInput = () => {
  if (props.disabled || isUploading.value) return;
  document.getElementById('video-upload').click();
};

// 处理拖放视频
const handleDrop = (event) => {
  event.preventDefault();
  event.stopPropagation();
  
  // 检查是否禁用或正在上传
  if (props.disabled || isUploading.value) return;
  
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
    class="video-monitoring-container"
    :class="{ 'is-disabled': disabled }"
    @drop="handleDrop"
    @dragover="handleDragOver"
  >
    <input
      id="video-upload"
      type="file"
      :accept="acceptedVideoTypes"
      @change="handleUpload"
      class="hidden-input"
      :disabled="disabled || isUploading"
    />
    
    <div class="upload-area" @click="triggerFileInput">
      <div class="upload-icon">
        <svg v-if="!isUploading" xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="23 7 16 12 23 17 23 7"></polygon>
          <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
        </svg>
        <div v-else class="loading-spinner"></div>
      </div>
      
      <div class="upload-text" v-if="!isUploading">
        <h3>上传视频进行车牌监控</h3>
        <p v-if="!disabled">点击此处或拖放视频文件</p>
        <p v-else class="disabled-text">请先设置目标车牌</p>
        <p class="upload-formats">支持格式: MP4, AVI, MOV</p>
      </div>
      <div class="upload-text" v-else>
        <h3>正在处理...</h3>
        <p>您的视频正在处理中，请稍候</p>
        <button class="cancel-button" @click="cancelProcessing">
          取消
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.video-monitoring-container {
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

.upload-area:hover:not(.is-disabled) {
  border-color: #4f46e5;
  background-color: rgba(79, 70, 229, 0.05);
}

.is-disabled .upload-area {
  opacity: 0.7;
  cursor: not-allowed;
  background-color: #f9fafb;
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

.disabled-text {
  color: #ef4444;
  font-weight: 500;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(79, 70, 229, 0.1);
  border-radius: 50%;
  border-top-color: #4f46e5;
  animation: spin 1s linear infinite;
}

.cancel-button {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background-color: #ef4444;
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.cancel-button:hover {
  background-color: #dc2626;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
