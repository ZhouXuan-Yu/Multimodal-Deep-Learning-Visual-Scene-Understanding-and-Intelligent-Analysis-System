<template>
  <div class="video-upload-section">
    <h2>火灾检测 - 视频分析</h2>
    <p class="description">选择并上传视频文件进行火灾检测分析。支持MP4、AVI等常见格式。</p>
    
    <div class="upload-box" :class="{ 'has-video': modelValue }">
      <div v-if="!modelValue" class="upload-placeholder">
        <el-icon class="upload-icon"><Upload /></el-icon>
        <p>选择或拖拽视频文件</p>
        <p class="upload-hint">支持MP4、AVI等常见格式，最大100MB</p>
        <input
          type="file"
          id="videoFileInput"
          accept="video/*"
          @change="handleFileChange"
          class="file-input"
        />
      </div>
      
      <div v-else class="video-preview">
        <div class="video-info">
          <p class="video-name">文件名: {{ modelValue.name }}</p>
          <p class="video-size">大小: {{ formatSize(modelValue.size) }}</p>
          <p class="video-type">类型: {{ modelValue.type }}</p>
        </div>
        
        <div class="settings-area">
          <h4>处理选项</h4>
          <div class="option-group">
            <el-checkbox v-model="saveFrames" label="保存关键帧" />
            <el-tooltip content="保存检测到火灾的帧以便详细分析">
              <el-icon class="info-icon"><InfoFilled /></el-icon>
            </el-tooltip>
          </div>
          

          
          <div v-if="enableAlarm" class="email-input">
            <el-input v-model="email" placeholder="接收提醒的邮箱地址" />
          </div>
          
          <div class="option-group frame-skip-option">
            <label>帧间隔 (每N帧处理1帧):</label>
            <el-select v-model="frameSkip" placeholder="选择">
              <el-option :value="1" label="1 (处理每一帧)" />
              <el-option :value="2" label="2 (跳过1帧)" />
              <el-option :value="3" label="3 (跳过2帧)" />
              <el-option :value="5" label="5 (跳过4帧)" />
              <el-option :value="10" label="10 (跳过9帧)" />
              <el-option :value="15" label="15 (跳过14帧)" />
              <el-option :value="30" label="30 (跳过29帧)" />
            </el-select>
            <p class="option-hint">值越高处理越快，但可能会错过短暂事件</p>
          </div>
        </div>
        
        <div class="video-actions">
          <el-button type="danger" @click="clearVideo" class="action-btn">
            <el-icon><Delete /></el-icon> 清除视频
          </el-button>
          <el-button 
            type="primary" 
            @click="processVideo" 
            :disabled="isProcessing"
            :loading="isProcessing"
            class="action-btn"
          >
            <el-icon><VideoPlay /></el-icon> 开始处理
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { Delete, Upload, InfoFilled, VideoPlay } from '@element-plus/icons-vue';

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
    required: true
  }
});

// 定义emit函数，用于事件发射
const emit = defineEmits(['update:modelValue', 'clear', 'process']);

// Form state
const saveFrames = ref(true);
const enableAlarm = ref(false);
const email = ref('');
const frameSkip = ref(5); // Default to 5 (process 1 frame every 5 frames)

// File change handler
function handleFileChange(e) {
  const files = e.target.files || e.dataTransfer.files;
  if (!files.length) return;
  
  emit('update:modelValue', files[0]);
}

// Clear video
function clearVideo() {
  emit('clear');
}

// Process video
function processVideo() {
  const formData = {
    file: props.modelValue,
    save_frames: saveFrames.value,
    enable_alarm: enableAlarm.value,
    email: enableAlarm.value ? email.value : '',
    frame_skip: frameSkip.value
  };
  
  emit('process', formData);
}

// Format file size
function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}
</script>

<style scoped>
.video-upload-section {
  margin-bottom: 2rem;
}

h2 {
  font-size: 1.8rem;
  color: #333;
  margin-bottom: 0.5rem;
  font-weight: 600;
  background: linear-gradient(45deg, #4f46e5, #00d2aa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.description {
  font-size: 1rem;
  color: #606266;
  margin-bottom: 1.5rem;
  line-height: 1.5;
}

.upload-box {
  border: 2px dashed #dcdfe6;
  border-radius: 12px;
  padding: 30px;
  text-align: center;
  background-color: rgba(255, 255, 255, 0.8);
  transition: all 0.3s ease;
  position: relative;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.upload-box:hover {
  background-color: rgba(255, 255, 255, 1);
  border-color: #4f46e5;
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.upload-icon {
  font-size: 3rem;
  color: #4f46e5;
  margin-bottom: 1rem;
}

.upload-hint {
  font-size: 0.9rem;
  color: #909399;
  margin-top: 1rem;
}

.file-input {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.video-preview {
  text-align: left;
}

.video-info {
  margin-bottom: 1.5rem;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.video-name, .video-size, .video-type {
  margin: 8px 0;
  font-size: 0.95rem;
  color: #606266;
}

.settings-area {
  margin-bottom: 1.5rem;
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.settings-area h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.1rem;
  color: #333;
  font-weight: 600;
}

.option-group {
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
}

.info-icon {
  margin-left: 8px;
  color: #4f46e5;
  cursor: pointer;
}

.email-input {
  margin-bottom: 1rem;
}

.frame-skip-option {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.frame-skip-option label {
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #606266;
}

.option-hint {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: #909399;
}

.video-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  border-radius: 8px;
  padding: 10px 16px;
  transition: all 0.3s;
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

:deep(.el-button.el-button--primary) {
  background: linear-gradient(45deg, #4f46e5, #00d2aa);
  border: none;
}

:deep(.el-select) {
  width: 100%;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.video-preview, .upload-placeholder {
  animation: fadeIn 0.3s ease;
}

@media (max-width: 768px) {
  .video-actions {
    flex-direction: column;
  }
  
  .upload-box {
    padding: 20px;
  }
}
</style> 