<template>
  <div class="fire-detection-container">
    <div class="page-header">
      <h1>Fire Detection System</h1>
      <p>Advanced fire detection with YOLOv8 AI model</p>
    </div>

    <!-- Tabs for different detection modes -->
    <el-tabs v-model="activeTab" class="detection-tabs">
      <el-tab-pane label="Video Detection" name="video">
        <VideoUploader 
          v-if="!processing && !processId" 
          v-model="videoFile"
          :is-processing="isUploading"
          @process="processVideo"
          @clear="clearVideo"
          :get-api-url="getApiUrl"
        />
        
        <ProcessingStatus 
          v-if="processing" 
          :processId="processId"
          :progress="progressPercent" 
          :message="progressMessage"
          :elapsedTime="elapsedTime"
          :error="processingError"
          @complete="onProcessingComplete"
          @error="onProcessingError"
        />
        
        <ResultDisplay 
          v-if="!processing && processId"
          :process-id="processId" 
          :frames="frames"
          :processing-time="processingTime"
          :fps="fps"
          :frame-skip="frameSkip"
          :get-api-url="getApiUrl"
          :original-video-url="originalVideoUrl"
          @restart="resetProcessing"
        />
      </el-tab-pane>
            
      <el-tab-pane label="Image Detection" name="image">
        <div class="image-detection-container">
          <div class="image-upload-area">
            <h3>Upload Image for Fire Detection</h3>
            
            <el-upload
              class="image-uploader"
              action="#"
              :auto-upload="false"
              :on-change="handleImageChange"
              :show-file-list="false"
              accept="image/jpeg,image/png,image/gif"
            >
              <img v-if="imageUrl" :src="imageUrl" class="preview-image" />
              <div v-else class="upload-placeholder">
                <el-icon><Plus /></el-icon>
                <div class="upload-text">Click to upload image</div>
              </div>
            </el-upload>
              
            <div class="image-actions">
                <el-button 
                  type="primary" 
                @click="uploadImageForDetection" 
                :disabled="!imageFile || imageProcessing"
                :loading="imageProcessing"
                >
                Detect Fire
              </el-button>
              <el-button 
                @click="resetImageDetection" 
                :disabled="!imageFile && !imageResult"
              >
                Reset
                </el-button>
            </div>
          </div>
          
          <div v-if="imageResult" class="image-result-area">
            <div class="result-header">
              <h3>Detection Result</h3>
              <div 
                class="result-status" 
                :class="{ 'fire-detected': imageResult.fire_detected }"
              >
                <el-icon v-if="imageResult.fire_detected">
                  <WarningFilled />
                </el-icon>
                <el-icon v-else>
                  <SuccessFilled />
                </el-icon>
                {{ imageResult.fire_detected ? 'FIRE DETECTED!' : 'No Fire Detected' }}
        </div>
      </div>
      
            <div class="result-images">
              <div class="original-image">
                <h4>Original Image</h4>
                <img :src="imageResult.original_image_url" alt="Original image" />
          </div>
              <div class="processed-image">
                <h4>Processed Image</h4>
                <img :src="imageResult.processed_image_url" alt="Processed image with detection" />
          </div>
        </div>
        
            <div class="result-details">
              <h4>Detection Details</h4>
              <ul>
                <li><strong>Confidence:</strong> {{ (imageResult.confidence * 100).toFixed(2) }}%</li>
                <li><strong>Fire Area:</strong> {{ (imageResult.fire_area_percentage * 100).toFixed(2) }}%</li>
                <li v-if="imageResult.smoke_detected"><strong>Smoke Area:</strong> {{ (imageResult.smoke_area_percentage * 100).toFixed(2) }}%</li>
                <li><strong>Method:</strong> {{ imageResult.method }}</li>
                <li><strong>Processing Time:</strong> {{ imageResult.processing_time.toFixed(2) }}s</li>
              </ul>
            </div>
            </div>
          </div>
      </el-tab-pane>
      
      <el-tab-pane label="Camera Detection" name="camera">
        <div class="camera-detection-container">
          <div class="camera-controls">
            <h3>Real-time Fire Detection with Camera</h3>
            <div class="camera-buttons">
              <el-button 
                type="primary" 
                @click="startCameraDetection" 
                :disabled="isCameraActive"
              >
                Start Camera
            </el-button>
              <el-button 
                type="danger" 
                @click="stopCameraDetection" 
                :disabled="!isCameraActive"
              >
                Stop Camera
            </el-button>
              <el-select 
                v-model="cameraSettings.detectionInterval" 
                placeholder="Detection Interval"
                :disabled="isCameraActive"
              >
                <el-option label="Fast (200ms)" :value="200" />
                <el-option label="Normal (500ms)" :value="500" />
                <el-option label="Slow (1000ms)" :value="1000" />
              </el-select>
          </div>
        </div>
        
          <div class="camera-view">
            <div class="camera-feed">
              <h4>Camera Feed</h4>
              <video 
                ref="cameraVideo" 
                autoplay 
                playsinline 
                muted
                :width="cameraSettings.width"
                :height="cameraSettings.height"
              ></video>
              <canvas
                ref="cameraCanvas"
                style="display: none;"
                :width="cameraSettings.width"
                :height="cameraSettings.height"
              ></canvas>
          </div>
          
            <div v-if="cameraResult" class="camera-result">
              <h4>Detection Result</h4>
              <div class="camera-status" :class="{ 'fire-detected': cameraResult.fire_detected }">
                <el-icon v-if="cameraResult.fire_detected">
                  <WarningFilled />
                </el-icon>
                <el-icon v-else>
                  <SuccessFilled />
                </el-icon>
                {{ cameraResult.fire_detected ? 'FIRE DETECTED!' : 'No Fire Detected' }}
            </div>
              <img 
                v-if="cameraResult.processed_image_url" 
                :src="cameraResult.processed_image_url" 
                alt="Processed camera frame" 
                class="processed-frame" 
              />
              <div class="camera-result-details">
                <p><strong>Confidence:</strong> {{ (cameraResult.confidence * 100).toFixed(2) }}%</p>
                <p><strong>Fire Area:</strong> {{ (cameraResult.fire_area_percentage * 100).toFixed(2) }}%</p>
                <p><strong>Method:</strong> {{ cameraResult.method }}</p>
                <p><strong>Processing Time:</strong> {{ (cameraResult.processing_time * 1000).toFixed(0) }}ms</p>
                <p><strong>Timestamp:</strong> {{ new Date().toLocaleTimeString() }}</p>
          </div>
          </div>
        </div>
      </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { ElMessage } from 'element-plus';
import { WarningFilled, SuccessFilled, Plus } from '@element-plus/icons-vue';
import VideoUploader from '@/components/fire_detection/VideoUploader.vue';
import ProcessingStatus from '@/components/fire_detection/ProcessingStatus.vue';
import ResultDisplay from '@/components/fire_detection/ResultDisplay.vue';

// Backend URL (from environment or default)
const backendUrl = ref(import.meta.env.VITE_API_BASE_URL || '');

// 辅助函数，用于构建统一的API URL
function getApiUrl(path) {
  // 确保路径以/开头
  const apiPath = path.startsWith('/') ? path : `/${path}`;
  
  // 添加/api前缀（后端需要）
  // 添加额外检查，确保能正确处理路由
  const fullUrl = `/api${apiPath}`;
  console.log(`构建API URL: 原始路径=${path}, 处理后=${fullUrl}`);
  return fullUrl;
}

// Active tab state
const activeTab = ref('video');

// ------- Video Detection State -------
const processing = ref(false);
const processId = ref('');
const frames = ref([]);
const processingTime = ref(0);
const fps = ref(0);
const frameSkip = ref(5);
const videoFile = ref(null);
// 保存原始视频URL
const originalVideoUrl = ref('');
const isUploading = ref(false);
const progressPercent = ref(0);
const progressMessage = ref('处理中...');
const elapsedTime = ref(0);
const processingError = ref(null);
const processingStartTime = ref(0);
const processingTimer = ref(null);

// Process video by uploading it to backend
async function processVideo(data) {
  try {
    isUploading.value = true;
    
    // 保存原始视频的URL - 创建本地Blob URL
    if (data.file) {
      originalVideoUrl.value = URL.createObjectURL(data.file);
      console.log('保存原始视频URL:', originalVideoUrl.value);
    }
    
    // Create form data
    const formData = new FormData();
    formData.append('file', data.file);
    formData.append('save_frames', data.save_frames);
    formData.append('enable_alarm', data.enable_alarm);
    if (data.enable_alarm && data.email) {
      formData.append('email', data.email);
    }
    formData.append('frame_skip', data.frame_skip);
    
    // 显示上传开始消息
    ElMessage.info('正在上传视频，请稍候...');
    
    // 发送到后端，使用正确的路由路径
    const response = await fetch(getApiUrl('fire_detection_direct/upload-video'), {
      method: 'POST',
      body: formData
    });
    
    // 先检查HTTP状态码
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: `服务器错误 (${response.status})` }));
      throw new Error(errorData.detail || `上传失败: 服务器返回状态码 ${response.status}`);
    }
    
    // 解析JSON响应
    let result;
    try {
      result = await response.json();
    } catch (jsonError) {
      throw new Error(`解析服务器响应失败: ${jsonError.message}`);
    }
    
    console.log('Video upload result:', result);
    
    // 检查服务器返回结果是否包含process_id
    if (!result.process_id) {
      throw new Error('服务器返回无效的响应，缺少process_id');
    }
    
    // 开始处理视频
    processId.value = result.process_id;
    processing.value = true;
    frameSkip.value = data.frame_skip || 5;
    ElMessage.success('视频上传成功，开始处理');
    
    // 重置进度状态并开始计时
    progressPercent.value = 0;
    progressMessage.value = '处理中...';
    processingError.value = null;
    processingStartTime.value = Date.now();
    
    // 开始计时
    startProcessingTimer();
    
    // 检查处理状态的函数
    const checkProcessingStatus = async () => {
      try {
        const statusResponse = await fetch(getApiUrl(`fire_detection_direct/video-status/${result.process_id}`));
        
        if (!statusResponse.ok) {
          throw new Error(`获取处理状态失败: ${statusResponse.status}`);
        }
        
        const statusData = await statusResponse.json();
        console.log('Processing status:', statusData);
        
        // 更新进度
        progressPercent.value = statusData.progress || 0;
        progressMessage.value = statusData.message || '处理中...';
        
        // 检查处理是否完成或失败
        if (statusData.status === 'completed') {
          // 处理完成
          progressPercent.value = 100;
          progressMessage.value = '处理完成';
          
          // 获取结果
          const resultResponse = await fetch(getApiUrl(`fire_detection_direct/detection-results/${result.process_id}`));
          if (resultResponse.ok) {
            const resultData = await resultResponse.json();
            onProcessingComplete(resultData);
          } else {
            onProcessingComplete({
              status: 'completed',
              message: '处理已完成',
              key_frames: statusData.key_frames || [],
              processing_time: statusData.processing_time || (Date.now() - processingStartTime.value) / 1000,
              frame_skip: frameSkip.value
            });
          }
          return true; // 停止轮询
        } else if (statusData.status === 'failed') {
          // 处理失败
          onProcessingError(statusData.message || '处理失败');
          return true; // 停止轮询
        }
        
        return false; // 继续轮询
      } catch (error) {
        console.error('获取处理状态出错:', error);
        // 如果连续多次获取状态失败，可以考虑停止轮询
        return false; // 暂时继续轮询
      }
    };
    
    // 开始轮询检查状态（每3秒一次）
    const statusInterval = 3000; // 3秒
    const maxPollingTime = 600000; // 10分钟
    const startTime = Date.now();
    
    const pollStatus = async () => {
      // 检查是否超过最大轮询时间
      if (Date.now() - startTime > maxPollingTime) {
        onProcessingError('处理超时，请稍后检查结果');
        return;
      }
      
      // 检查状态
      const shouldStop = await checkProcessingStatus();
      if (!shouldStop) {
        // 继续轮询
        setTimeout(pollStatus, statusInterval);
      }
    };
    
    // 开始轮询
    setTimeout(pollStatus, statusInterval);
      
  } catch (error) {
    console.error('Error uploading video:', error);
    ElMessage.error(`上传视频失败: ${error.message}`);
    processingError.value = error.message;
  } finally {
    isUploading.value = false;
  }
}

// Clear video
function clearVideo() {
  videoFile.value = null;
}

// Start video processing (legacy method - keeping for compatibility)
function startProcessing(data) {
  processId.value = data.processId;
  processing.value = true;
      }

// Handle processing complete
function onProcessingComplete(data) {
  console.log('Video processing completed:', data);
  processing.value = false;
  frames.value = data.key_frames || [];
  processingTime.value = data.processing_time || 0;
  fps.value = data.frames_per_second || 0;
  frameSkip.value = data.frame_skip || 5;
  
  // 停止计时器
  stopProcessingTimer();
  
  // 通知用户处理完成
  ElMessage.success('视频处理完成!');
  
  // 尝试获取模型检测结果
  loadDetectionResults(processId.value);
}

// Handle processing error
function onProcessingError(error) {
  console.error('Video processing error:', error);
  processing.value = false;
  processingError.value = error;
  
  // 停止计时器
  stopProcessingTimer();
  
  // 通知用户错误
  ElMessage.error(`视频处理失败: ${error}`);
}

// Reset processing state
function resetProcessing() {
  processing.value = false;
  processId.value = '';
  frames.value = [];
}

// ------- Image Detection State -------
const imageFile = ref(null);
const imageUrl = ref('');
const imageProcessing = ref(false);
const imageResult = ref(null);

// Handle image upload
function handleImageChange(file) {
  imageFile.value = file.raw;
  imageUrl.value = URL.createObjectURL(file.raw);
}

// Upload and process image
async function uploadImageForDetection() {
  if (!imageFile.value) {
    ElMessage.warning('请先选择一张图片');
    return;
  }
  
  imageProcessing.value = true;
  
  try {
    // 显示上传开始消息
    ElMessage.info('正在处理图像，请稍候...');
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', imageFile.value);
    formData.append('threshold', 0.5);
    
    // 发送请求，使用正确的路由路径
    const response = await fetch(getApiUrl('fire_detection_direct/detect-image'), {
      method: 'POST',
      body: formData
    });
    
    // 先检查HTTP状态码
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: `服务器错误 (${response.status})` }));
      throw new Error(errorData.detail || `处理失败: 服务器返回状态码 ${response.status}`);
    }
    
    // 解析JSON响应
    let result;
    try {
      result = await response.json();
    } catch (jsonError) {
      throw new Error(`解析服务器响应失败: ${jsonError.message}`);
    }
    
    console.log('Image detection result:', result);
    
    // 检查是否包含必要的结果字段
    if (!result.original_image || !result.processed_image) {
      throw new Error('服务器返回的结果数据不完整');
    }
    
    // Add image URLs - 使用统一的API路径处理
    const originalImagePath = result.original_image.startsWith('/') 
      ? result.original_image.substring(1) 
      : result.original_image;
    
    const processedImagePath = result.processed_image.startsWith('/') 
      ? result.processed_image.substring(1) 
      : result.processed_image;
    
    result.original_image_url = getApiUrl(originalImagePath);
    result.processed_image_url = getApiUrl(processedImagePath);
    
    // Update state
    imageResult.value = result;
    
    // 显示处理结果消息
    const fireMsg = result.fire_detected 
      ? '警告：检测到火灾！' 
      : '未检测到火灾';
    const confidence = (result.confidence * 100).toFixed(1);
    ElMessage[result.fire_detected ? 'error' : 'success'](`${fireMsg} (置信度: ${confidence}%)`);
    
  } catch (error) {
    console.error('Error detecting fire in image:', error);
    ElMessage.error(`图像处理失败: ${error.message}`);
    imageResult.value = null;
  } finally {
    imageProcessing.value = false;
  }
}

// Reset image detection
function resetImageDetection() {
  imageFile.value = null;
  imageUrl.value = '';
  imageResult.value = null;
}

// ------- Camera Detection State -------
const cameraVideo = ref(null);
const cameraCanvas = ref(null);
const isCameraActive = ref(false);
const cameraStream = ref(null);
const cameraResult = ref(null);
const cameraDetectionTimer = ref(null);
const cameraSessionId = ref('');

// Camera settings
const cameraSettings = ref({
  width: 640,
  height: 480,
  detectionInterval: 500, // milliseconds
  facingMode: 'environment' // Use back camera on mobile if available
});

// Start camera detection
async function startCameraDetection() {
  try {
    // Generate a new session ID
    cameraSessionId.value = crypto.randomUUID();
    
    // Get camera access
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: cameraSettings.value.width },
        height: { ideal: cameraSettings.value.height },
        facingMode: cameraSettings.value.facingMode
      },
      audio: false
    });
    
    // Store stream and attach to video element
    cameraStream.value = stream;
    cameraVideo.value.srcObject = stream;
    isCameraActive.value = true;
    
    // Wait for video to be playing
    await new Promise(resolve => {
      cameraVideo.value.onloadedmetadata = () => {
        cameraVideo.value.play();
        resolve();
      };
    });
    
    ElMessage.success('Camera started successfully');
    
    // Start detection loop
    startCameraDetectionLoop();
    
  } catch (error) {
    console.error('Error accessing camera:', error);
    ElMessage.error(`Failed to access camera: ${error.message}`);
    stopCameraDetection();
  }
}

// Start detection loop
function startCameraDetectionLoop() {
  // Clear any existing timer
  if (cameraDetectionTimer.value) {
    clearInterval(cameraDetectionTimer.value);
  }
  
  // Create new timer for periodic detection
  cameraDetectionTimer.value = setInterval(processCameraFrame, cameraSettings.value.detectionInterval);
  }
  
// Process a single camera frame
async function processCameraFrame() {
  if (!isCameraActive.value || !cameraVideo.value || !cameraCanvas.value) return;
  
  try {
    // Draw current video frame to canvas
    const context = cameraCanvas.value.getContext('2d');
    context.drawImage(
      cameraVideo.value, 
      0, 0, 
      cameraSettings.value.width, 
      cameraSettings.value.height
    );
    
    // Convert canvas to blob
    const blob = await new Promise(resolve => {
      cameraCanvas.value.toBlob(resolve, 'image/jpeg', 0.9);
    });
    
    if (!blob) {
      console.error('无法从画布创建图像数据');
      return;
    }
    
    // Create file from blob
    const file = new File([blob], 'camera_frame.jpg', { type: 'image/jpeg' });
  
    // Create form data
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', cameraSessionId.value);
    formData.append('threshold', 0.5);
    
    // 发送到API，使用正确的路由路径
    const response = await fetch(getApiUrl('fire_detection_direct/detect-camera'), {
      method: 'POST',
      body: formData
    });
    
    // 检查响应状态
    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      console.error('摄像头帧处理失败:', errorData?.detail || response.statusText);
      return;
    }
    
    // Process result
    const result = await response.json();
    
    // Add image URLs - 使用统一的API路径处理
    if (result.original_image && result.processed_image) {
      const originalImagePath = result.original_image.startsWith('/') 
        ? result.original_image.substring(1) 
        : result.original_image;
      
      const processedImagePath = result.processed_image.startsWith('/') 
        ? result.processed_image.substring(1) 
        : result.processed_image;
      
      result.original_image_url = getApiUrl(originalImagePath);
      result.processed_image_url = getApiUrl(processedImagePath);
      
      // Update state
      cameraResult.value = result;
      
      // Show alert if fire detected
      if (result.fire_detected && result.confidence > 0.7) {
        // 只在高置信度火灾且上一次提醒超过3秒时显示提醒
        const now = Date.now();
        if (!window.lastFireAlert || now - window.lastFireAlert > 3000) {
          window.lastFireAlert = now;
          ElMessage({
            message: '警告！检测到火灾！置信度高。',
            type: 'error',
            duration: 3000
          });
        }
      }
    } else {
      console.warn('服务器响应缺少图像路径信息');
    }
    
  } catch (error) {
    console.error('处理摄像头帧时出错:', error);
    // 不显示错误消息给用户，避免过多干扰
    
    // 检测错误次数，如果持续出错可能需要停止检测
    window.cameraErrorCount = (window.cameraErrorCount || 0) + 1;
    if (window.cameraErrorCount > 10) {
      ElMessage.error('摄像头检测连续出错，即将停止检测');
      setTimeout(() => {
        stopCameraDetection();
        window.cameraErrorCount = 0;
      }, 2000);
    }
  }
}

// Stop camera detection
function stopCameraDetection() {
  // Clear detection timer
  if (cameraDetectionTimer.value) {
    clearInterval(cameraDetectionTimer.value);
    cameraDetectionTimer.value = null;
}

  // Stop camera stream
  if (cameraStream.value) {
    cameraStream.value.getTracks().forEach(track => track.stop());
    cameraStream.value = null;
  }
  
  // Reset video element
  if (cameraVideo.value) {
    cameraVideo.value.srcObject = null;
  }
  
  // Update state
  isCameraActive.value = false;
  cameraResult.value = null;
  cameraSessionId.value = '';
  
  ElMessage.info('Camera detection stopped');
}

// Cleanup on component unmount
onBeforeUnmount(() => {
  stopCameraDetection();
});

// 添加计时器函数
function startProcessingTimer() {
  // 清除之前的计时器（如果存在）
  if (processingTimer.value) {
    clearInterval(processingTimer.value);
  }
  
  // 创建新的计时器，每秒更新一次经过时间
  processingTimer.value = setInterval(() => {
    if (processing.value) {
      const now = Date.now();
      elapsedTime.value = Math.floor((now - processingStartTime.value) / 1000);
    }
  }, 1000);
}

function stopProcessingTimer() {
  if (processingTimer.value) {
    clearInterval(processingTimer.value);
    processingTimer.value = null;
  }
}

// 添加加载检测结果的函数

async function loadDetectionResults(pid) {
  if (!pid) return;
  
  try {
    const response = await fetch(getApiUrl(`fire_detection_direct/detection-results/${pid}`));
    
    if (!response.ok) {
      throw new Error(`Error: ${response.status} ${response.statusText}`);
    }
    
    const result = await response.json();
    // 更新帧数据
    if (result.frames && result.frames.length > 0) {
      frames.value = result.frames;
    }
    // 更新处理时间
    if (result.processing_time) {
      processingTime.value = result.processing_time;
    }
  } catch (error) {
    console.error('获取检测结果出错:', error);
  }
}
</script>

<style scoped>
  .fire-detection-container {
  max-width: 1200px;
    margin: 0 auto;
  padding: 20px;
  color: #2c3e50;
  }

.page-header {
    text-align: center;
    margin-bottom: 30px;
}

.page-header h1 {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 10px;
  }

.page-header p {
  font-size: 1.2rem;
  color: #7f8c8d;
  }

.detection-tabs {
  background: white;
    border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 20px;
  }

/* Image Detection Styles */
.image-detection-container {
    display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 992px) {
  .image-detection-container {
    grid-template-columns: 1fr;
  }
}

.image-upload-area {
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.image-upload-area h3 {
    margin-bottom: 20px;
  color: #2c3e50;
}

.image-uploader {
  width: 100%;
  max-width: 400px;
  margin-bottom: 20px;
  }

.preview-image {
    width: 100%;
  max-height: 300px;
  object-fit: contain;
  border-radius: 8px;
}

.upload-placeholder {
    display: flex;
    flex-direction: column;
    justify-content: center;
  align-items: center;
  width: 100%;
  height: 300px;
  border: 2px dashed #dcdfe6;
    border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.3s;
  }

.upload-placeholder:hover {
  border-color: #409eff;
}

.upload-placeholder .el-icon {
  font-size: 48px;
  color: #909399;
}

.upload-text {
  margin-top: 10px;
  font-size: 16px;
  color: #909399;
  }

.image-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  }

.image-result-area {
  background-color: #f8f9fa;
    padding: 20px;
    border-radius: 10px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.result-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: bold;
  background-color: #52c41a;
  color: white;
}

.result-status.fire-detected {
  background-color: #f5222d;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(245, 34, 45, 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(245, 34, 45, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(245, 34, 45, 0);
  }
}

.result-images {
    display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 20px;
  }

.original-image,
.processed-image {
  display: flex;
  flex-direction: column;
}

.original-image h4,
.processed-image h4 {
  margin-bottom: 10px;
  text-align: center;
  }

.original-image img,
.processed-image img {
    width: 100%;
  max-height: 250px;
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid #dcdfe6;
}

.result-details {
  background-color: white;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  }

.result-details h4 {
  margin-bottom: 10px;
  color: #2c3e50;
}

.result-details ul {
  list-style: none;
  padding: 0;
    margin: 0;
  }

.result-details li {
  padding: 5px 0;
  border-bottom: 1px dashed #ebeef5;
  }

.result-details li:last-child {
  border-bottom: none;
}

/* Camera Detection Styles */
.camera-detection-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  }

.camera-controls {
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
    display: flex;
  flex-direction: column;
    gap: 15px;
}

.camera-controls h3 {
  margin: 0;
  color: #2c3e50;
  }

.camera-buttons {
    display: flex;
    gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.camera-view {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 992px) {
  .camera-view {
    grid-template-columns: 1fr;
  }
  }

.camera-feed {
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  }

.camera-feed h4 {
  margin-bottom: 10px;
  color: #2c3e50;
    }

.camera-feed video {
  width: 100%;
  max-height: 360px;
    border-radius: 8px;
  background-color: #000;
  object-fit: contain;
  }

.camera-result {
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.camera-result h4 {
  margin-bottom: 10px;
    color: #2c3e50;
  align-self: flex-start;
}

.camera-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: bold;
  background-color: #52c41a;
  color: white;
  margin-bottom: 15px;
  align-self: flex-start;
}

.camera-status.fire-detected {
  background-color: #f5222d;
  animation: pulse 2s infinite;
}

.processed-frame {
  width: 100%;
  max-height: 300px;
  object-fit: contain;
    border-radius: 8px;
  margin-bottom: 15px;
  border: 1px solid #dcdfe6;
}

.camera-result-details {
  background-color: white;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  width: 100%;
  }

.camera-result-details p {
  margin: 5px 0;
  padding: 5px 0;
  border-bottom: 1px dashed #ebeef5;
}

.camera-result-details p:last-child {
  border-bottom: none;
  }
</style>
