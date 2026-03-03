<template>
  <div class="video-upload-section">
    <h2>Fire Detection - Video Analysis</h2>
    <p class="description">Select and upload a video file for fire detection analysis. Supports MP4, AVI and other common formats.</p>
    
    <div class="upload-box" :class="{ 'has-video': modelValue }">
      <div v-if="!modelValue" class="upload-placeholder">
        <el-icon><Upload /></el-icon>
        <p>Select or drag video file</p>
        <p class="upload-hint">Supports MP4, AVI and other common formats, max size 100MB</p>
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
          <p class="video-name">File name: {{ modelValue.name }}</p>
          <p class="video-size">Size: {{ formatSize(modelValue.size) }}</p>
          <p class="video-type">Type: {{ modelValue.type }}</p>
        </div>
        
        <div class="settings-area">
          <h4>Processing Options</h4>
          <div class="option-group">
            <el-checkbox v-model="saveFrames" label="Save key frames" />
            <el-tooltip content="Save detected fire frames for detailed analysis">
              <el-icon class="info-icon"><InfoFilled /></el-icon>
            </el-tooltip>
          </div>
          
          <div class="option-group">
            <el-checkbox v-model="enableAlarm" label="Enable email alerts" />
            <el-tooltip content="Send email notification when fire is detected">
              <el-icon class="info-icon"><InfoFilled /></el-icon>
            </el-tooltip>
          </div>
          
          <div v-if="enableAlarm" class="email-input">
            <el-input v-model="email" placeholder="Email address for alerts" />
          </div>
          
          <div class="option-group frame-skip-option">
            <label>Frame Skip (Process 1 frame every N frames):</label>
            <el-select v-model="frameSkip" placeholder="Select">
              <el-option :value="1" label="1 (Process every frame)" />
              <el-option :value="2" label="2 (Skip 1 frame)" />
              <el-option :value="3" label="3 (Skip 2 frames)" />
              <el-option :value="5" label="5 (Skip 4 frames)" />
              <el-option :value="10" label="10 (Skip 9 frames)" />
              <el-option :value="15" label="15 (Skip 14 frames)" />
              <el-option :value="30" label="30 (Skip 29 frames)" />
            </el-select>
            <p class="option-hint">Higher values process faster but may miss quick events</p>
          </div>
        </div>
        
        <div class="video-actions">
          <el-button type="danger" @click="clearVideo">
            <el-icon><Delete /></el-icon> Clear video
          </el-button>
          <el-button 
            type="primary" 
            @click="processVideo" 
            :disabled="isProcessing"
            :loading="isProcessing"
          >
            <el-icon><VideoPlay /></el-icon> Start Processing
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

.upload-box {
  border: 2px dashed #d63031;
  border-radius: 10px;
  padding: 30px;
  text-align: center;
  background-color: rgba(255, 255, 255, 0.8);
  transition: all 0.3s ease;
}

.upload-box:hover {
  background-color: rgba(255, 255, 255, 1);
  border-color: #e17055;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.upload-hint {
  font-size: 0.9rem;
  color: #7f8c8d;
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
}

.settings-area {
  margin-bottom: 1.5rem;
  background-color: #f1f2f6;
  padding: 15px;
  border-radius: 8px;
}

.option-group {
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
}

.info-icon {
  margin-left: 8px;
  color: #3498db;
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
}

.option-hint {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: #7f8c8d;
}

.video-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.description {
  color: #2c3e50;
  margin-bottom: 1.5rem;
}
</style> 