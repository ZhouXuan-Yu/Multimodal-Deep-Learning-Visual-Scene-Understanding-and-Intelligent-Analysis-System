<template>
  <div class="result-area">
    <h2>Fire Detection Results</h2>
    
    <div class="result-summary">
      <div class="detection-status" :class="{ 'fire-detected': hasFireFrames }">
        <el-icon v-if="hasFireFrames"><WarningFilled /></el-icon>
        <el-icon v-else><SuccessFilled /></el-icon>
        <span>{{ hasFireFrames ? 'FIRE DETECTED' : 'NO FIRE DETECTED' }}</span>
      </div>
      
      <div class="detection-info">
        <p v-if="hasFireFrames">Highest fire confidence: {{ (frames[0].confidence * 100).toFixed(2) }}%</p>
        <p v-else>No fire detected</p>
      </div>
    </div>
    
    <div class="videos-container">
      <!-- Grid layout for original and processed videos -->
      <div class="video-grid">
        <!-- Original video -->
        <div class="original-video">
          <h3>Original Video</h3>
          <video 
            v-if="processId && !usingFramePlayerOriginal" 
            ref="originalVideo"
            controls 
            class="video-player" 
            :src="getOriginalVideoURL()"
            @error="handleVideoError($event, 'original')"
            @loadeddata="videoLoaded('original')"
            @waiting="handleVideoWaiting('original')"
            @stalled="handleVideoStalled('original')"
            crossorigin="anonymous"
            preload="auto"
          ></video>
          <div v-else-if="!processId" class="video-placeholder">原始视频将在处理后显示</div>
          <!-- 原始视频帧播放器 -->
          <div v-else-if="usingFramePlayerOriginal" class="frame-player-container">
            <div class="frame-player">
              <div class="frame-display-area">
                <div v-if="originalFrames.length === 0" class="frame-loading">
                  <el-progress type="circle" :percentage="loadingProgress" :status="loadingStatus"></el-progress>
                  <p>{{ loadingMessage }}</p>
                </div>
                <img :src="currentOriginalFrame" class="frame-image" v-else-if="currentOriginalFrame" 
                     :class="{'frame-transition': useFrameTransition}"
                     @load="handleFrameLoad('original')" />
                <div v-else class="frame-error">
                  <el-icon><WarningFilled /></el-icon>
                  <p>无法加载视频帧</p>
                </div>
              </div>
              <div class="frame-progress-bar">
                <el-slider 
                  v-model="currentFrameIndexOriginal" 
                  :min="0" 
                  :max="originalFrames.length - 1"
                  :show-tooltip="false"
                  :disabled="originalFrames.length === 0"
                  @change="handleSeek('original')"
                ></el-slider>
                <span class="frame-time">{{ formatTime(originalFrameTime) }}</span>
              </div>
              <div class="frame-controls">
                <el-button type="primary" size="small" @click="toggleFramePlayback('original')"
                          :disabled="originalFrames.length === 0">
                  <el-icon v-if="!isFramePlayingOriginal"><VideoPlay /></el-icon>
                  <span v-else class="pause-icon">■</span>
                  {{ isFramePlayingOriginal ? '暂停' : '播放' }}
                </el-button>
                <el-slider v-model="frameSpeedOriginal" :min="1" :max="30" :step="1" 
                          :format-tooltip="val => `${val} 帧/秒`" style="width: 120px; margin: 0 10px;" />
                <span class="frame-info">{{ currentFrameIndexOriginal + 1 }}/{{ originalFrames.length }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Processed video -->
        <div class="processed-video">
          <h3>Processed Video with Fire Detection</h3>
          <video 
            v-if="processId && !usingFramePlayerProcessed" 
            ref="processedVideo"
            controls 
            class="video-player" 
            :src="getProcessedVideoURL()"
            @error="handleVideoError($event, 'processed')"
            @loadeddata="videoLoaded('processed')"
            @waiting="handleVideoWaiting('processed')"
            @stalled="handleVideoStalled('processed')"
            crossorigin="anonymous"
            preload="auto"
          ></video>
          <div v-else-if="!processId" class="video-placeholder">处理后的视频将在处理后显示</div>
          <!-- 处理后视频帧播放器 -->
          <div v-else-if="usingFramePlayerProcessed" class="frame-player-container">
            <div class="frame-player">
              <div class="frame-display-area">
                <div v-if="processedFrames.length === 0" class="frame-loading">
                  <el-progress type="circle" :percentage="loadingProgress" :status="loadingStatus"></el-progress>
                  <p>{{ loadingMessage }}</p>
                </div>
                <img :src="currentProcessedFrame" class="frame-image" v-else-if="currentProcessedFrame" 
                     :class="{'frame-transition': useFrameTransition}"
                     @load="handleFrameLoad('processed')" />
                <div v-else class="frame-error">
                  <el-icon><WarningFilled /></el-icon>
                  <p>无法加载视频帧</p>
                </div>
              </div>
              <div class="frame-progress-bar">
                <el-slider 
                  v-model="currentFrameIndexProcessed" 
                  :min="0" 
                  :max="processedFrames.length - 1"
                  :show-tooltip="false"
                  :disabled="processedFrames.length === 0"
                  @change="handleSeek('processed')"
                ></el-slider>
                <span class="frame-time">{{ formatTime(currentFrameTime) }}</span>
              </div>
              <div class="frame-controls">
                <el-button type="primary" size="small" @click="toggleFramePlayback('processed')"
                          :disabled="processedFrames.length === 0">
                  <el-icon v-if="!isFramePlayingProcessed"><VideoPlay /></el-icon>
                  <span v-else class="pause-icon">■</span>
                  {{ isFramePlayingProcessed ? '暂停' : '播放' }}
                </el-button>
                <el-slider v-model="frameSpeedProcessed" :min="1" :max="30" :step="1" 
                          :format-tooltip="val => `${val} 帧/秒`" style="width: 120px; margin: 0 10px;" />
                <span class="frame-info">{{ currentFrameIndexProcessed + 1 }}/{{ processedFrames.length }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="processing-details">
        <h3>Processing Details</h3>
        <table class="details-table">
          <tbody>
            <tr>
              <td><strong>Frame Skip:</strong></td>
              <td>{{ frameSkip }} (Processed 1 frame every {{ frameSkip }} frames)</td>
            </tr>
            <tr v-if="frames">
              <td><strong>Fire Frames:</strong></td>
              <td>{{ frames.length }}</td>
            </tr>
            <tr v-if="processingTime !== undefined">
              <td><strong>Processing Time:</strong></td>
              <td>{{ processingTime.toFixed(2) }} seconds</td>
            </tr>
            <tr v-if="fps !== undefined">
              <td><strong>Processing Speed:</strong></td>
              <td>{{ fps.toFixed(1) }} frames per second</td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <div class="video-actions">
        <el-button type="primary" @click="downloadProcessedVideo">
          <el-icon><Download /></el-icon> Download Processed Video
        </el-button>
        <el-button type="success" @click="downloadOriginalVideo">
          <el-icon><Download /></el-icon> Download Original Video
        </el-button>
        <el-button @click="emit('restart')">
          <el-icon><RefreshRight /></el-icon> New Detection
        </el-button>
      </div>
    </div>
    
    <div v-if="hasFireFrames" class="fire-frames">
      <h3>Fire Key Frames</h3>
      
      <!-- Selected key frame detail view -->
      <div v-if="selectedFrame" class="selected-frame-container">
        <div class="selected-frame-header">
          <h4>Key Frame #{{ selectedFrame.frame }} Details</h4>
          <el-button type="default" size="small" @click="selectedFrame = null">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
        <div class="selected-frame-image">
          <img :src="getApiUrl(`fire_detection_direct/frame/${processId}/${selectedFrame.name}`)" />
        </div>
        <div class="selected-frame-info">
          <p><strong>Frame Number:</strong> {{ selectedFrame.frame }}</p>
          <p><strong>Confidence:</strong> {{ (selectedFrame.confidence * 100).toFixed(2) }}%</p>
          <p><strong>File name:</strong> {{ selectedFrame.name }}</p>
          <a :href="getApiUrl(`fire_detection_direct/frame/${processId}/${selectedFrame.name}`)" target="_blank" download>
            <el-button type="primary" size="small">Download original image</el-button>
          </a>
        </div>
      </div>
      
      <!-- Frame grid -->
      <div v-if="frames && frames.length > 0" class="frames-grid">
        <div v-for="(frame, index) in frames" :key="index" class="frame-item">
          <img :src="getApiUrl(`fire_detection_direct/frame/${processId}/${frame.name}`)" @click="viewFrame(frame)" />
          <p class="frame-info">Frame #{{ frame.frame }} | Confidence: {{ (frame.confidence * 100).toFixed(2) }}%</p>
        </div>
      </div>
      <div v-else class="no-frames-message">
        <p>No fire key frames detected</p>
        <p>Try uploading a video containing fire to see key frames</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import { Download, RefreshRight, Close, WarningFilled, SuccessFilled, VideoPlay } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

// 定义emit函数，用于事件发射
const emit = defineEmits(['restart']);

const props = defineProps({
  processId: {
    type: String,
    default: ''
  },
  frames: {
    type: Array,
    default: () => []
  },
  processingTime: Number,
  fps: Number,
  frameSkip: {
    type: Number,
    default: 5
  },
  backendUrl: {
    type: String,
    default: 'http://localhost:8081'
  },
  getApiUrl: {
    type: Function,
    required: true
  },
  originalVideoUrl: {
    type: String,
    default: ''
  }
});

// UI State
const selectedFrame = ref(null);

// 帧播放器状态
const usingFramePlayerOriginal = ref(false);
const usingFramePlayerProcessed = ref(false);
const originalFrames = ref([]);
const processedFrames = ref([]);
const currentFrameIndexOriginal = ref(0);
const currentFrameIndexProcessed = ref(0);
const isFramePlayingOriginal = ref(false);
const isFramePlayingProcessed = ref(false);
const frameSpeedOriginal = ref(10); // 默认10帧/秒
const frameSpeedProcessed = ref(10); // 默认10帧/秒
const frameTimerOriginal = ref(null);
const frameTimerProcessed = ref(null);
const retryCount = ref(0);
const maxRetries = 3;

// 添加加载状态相关变量
const loadingProgress = ref(0);
const loadingStatus = ref('');
const loadingMessage = ref('正在加载帧序列...');
const useFrameTransition = ref(true);
const framePreloadQueue = ref([]); // 预加载队列
const preloadedFrames = ref(new Set()); // 已预加载的帧
const currentFrameTime = ref(0);
const originalFrameTime = ref(0);
const videoInfo = ref({
  fps: 24,
  duration: 0,
  total_frames: 0
});

// 计算当前显示的帧
const currentOriginalFrame = computed(() => {
  if (originalFrames.value.length === 0 || currentFrameIndexOriginal.value >= originalFrames.value.length) {
    return null;
  }
  return originalFrames.value[currentFrameIndexOriginal.value];
});

const currentProcessedFrame = computed(() => {
  if (processedFrames.value.length === 0 || currentFrameIndexProcessed.value >= processedFrames.value.length) {
    return null;
  }
  return processedFrames.value[currentFrameIndexProcessed.value];
});

// Computed properties
const hasFireFrames = computed(() => props.frames && props.frames.length > 0);

// 监听processId变化，重置帧播放器状态
watch(() => props.processId, (newId, oldId) => {
  if (newId && newId !== oldId) {
    resetFramePlayers();
  }
});

// 监听帧播放速度变化
watch(frameSpeedOriginal, () => {
  if (isFramePlayingOriginal.value) {
    // 重新启动计时器
    stopFramePlayback('original');
    startFramePlayback('original');
  }
});

watch(frameSpeedProcessed, () => {
  if (isFramePlayingProcessed.value) {
    // 重新启动计时器
    stopFramePlayback('processed');
    startFramePlayback('processed');
  }
});

// 组件挂载时
onMounted(() => {
  // 如果已有processId，初始化帧播放器
  if (props.processId) {
    initFramePlayers();
  }
});

// 组件卸载前清除计时器
onBeforeUnmount(() => {
  stopFramePlayback('original');
  stopFramePlayback('processed');
});

// 初始化帧播放器
function initFramePlayers() {
  if (!props.processId) return;
  
  // 重置状态
  resetFramePlayers();
  
  // 加载帧序列
  fetchVideoFrames();
}

// 重置帧播放器状态
function resetFramePlayers() {
  usingFramePlayerOriginal.value = false;
  usingFramePlayerProcessed.value = false;
  originalFrames.value = [];
  processedFrames.value = [];
  currentFrameIndexOriginal.value = 0;
  currentFrameIndexProcessed.value = 0;
  isFramePlayingOriginal.value = false;
  isFramePlayingProcessed.value = false;
  stopFramePlayback('original');
  stopFramePlayback('processed');
  retryCount.value = 0;
}

// 获取视频帧序列
async function fetchVideoFrames() {
  if (!props.processId) return;
  
  try {
    loadingProgress.value = 10;
    loadingMessage.value = '正在请求视频帧...';
    loadingStatus.value = '';
    
    // 加载原始视频的帧
    loadingMessage.value = '正在提取原始视频帧...';
    const originalResponse = await fetch(props.getApiUrl(`fire_detection_direct/extract-frames/${props.processId}?type=original`));
    if (!originalResponse.ok) {
      throw new Error(`获取原始视频帧失败: ${originalResponse.status}`);
    }
    loadingProgress.value = 40;
    
    const originalData = await originalResponse.json();
    originalFrames.value = originalData.frames.map(frame => frame.url);
    
    // 保存视频信息
    if (originalData.video_info) {
      videoInfo.value = originalData.video_info;
    }
    
    loadingProgress.value = 60;
    loadingMessage.value = '正在提取处理后视频帧...';
    
    // 加载处理后视频的帧
    const processedResponse = await fetch(props.getApiUrl(`fire_detection_direct/extract-frames/${props.processId}?type=processed`));
    if (!processedResponse.ok) {
      throw new Error(`获取处理后视频帧失败: ${processedResponse.status}`);
    }
    loadingProgress.value = 80;
    
    const processedData = await processedResponse.json();
    processedFrames.value = processedData.frames.map(frame => frame.url);
    
    loadingProgress.value = 100;
    loadingMessage.value = '加载完成';
    loadingStatus.value = 'success';
    
    // 如果有帧，自动开始播放处理后视频的帧
    if (processedFrames.value.length > 0) {
      // 预加载前几帧
      preloadFrames(processedFrames.value, 0);
      
      // 更新初始帧时间
      updateCurrentFrameTime();
      updateOriginalFrameTime();
      
      // 开始播放
      isFramePlayingProcessed.value = true;
      startFramePlayback('processed');
    }
    
    console.log(`已加载 ${originalFrames.value.length} 帧原始视频和 ${processedFrames.value.length} 帧处理后视频`);
  } catch (error) {
    console.error('获取视频帧序列失败:', error);
    loadingStatus.value = 'exception';
    loadingMessage.value = '加载失败: ' + error.message;
    ElMessage.error('无法加载视频帧序列，请稍后再试');
  }
}

// 切换帧播放状态
function toggleFramePlayback(type) {
  if (type === 'original') {
    if (isFramePlayingOriginal.value) {
      stopFramePlayback(type);
    } else {
      startFramePlayback(type);
    }
    isFramePlayingOriginal.value = !isFramePlayingOriginal.value;
  } else {
    if (isFramePlayingProcessed.value) {
      stopFramePlayback(type);
    } else {
      startFramePlayback(type);
    }
    isFramePlayingProcessed.value = !isFramePlayingProcessed.value;
  }
}

// 开始帧播放
function startFramePlayback(type) {
  if (type === 'original') {
    if (frameTimerOriginal.value) clearInterval(frameTimerOriginal.value);
    frameTimerOriginal.value = setInterval(() => {
      // 循环播放
      if (currentFrameIndexOriginal.value >= originalFrames.value.length - 1) {
        currentFrameIndexOriginal.value = 0;
      } else {
        currentFrameIndexOriginal.value++;
      }
      // 更新时间
      updateOriginalFrameTime();
      // 预加载下一批帧
      preloadNextFrames('original');
    }, 1000 / frameSpeedOriginal.value);
  } else {
    if (frameTimerProcessed.value) clearInterval(frameTimerProcessed.value);
    frameTimerProcessed.value = setInterval(() => {
      // 循环播放
      if (currentFrameIndexProcessed.value >= processedFrames.value.length - 1) {
        currentFrameIndexProcessed.value = 0;
      } else {
        currentFrameIndexProcessed.value++;
      }
      // 更新时间
      updateCurrentFrameTime();
      // 预加载下一批帧
      preloadNextFrames('processed');
    }, 1000 / frameSpeedProcessed.value);
  }
}

// 停止帧播放
function stopFramePlayback(type) {
  if (type === 'original') {
    if (frameTimerOriginal.value) {
      clearInterval(frameTimerOriginal.value);
      frameTimerOriginal.value = null;
    }
  } else {
    if (frameTimerProcessed.value) {
      clearInterval(frameTimerProcessed.value);
      frameTimerProcessed.value = null;
    }
  }
}

// Get processed video URL with cache-busting
function getProcessedVideoURL() {
  if (!props.processId) return '';
  const timestamp = new Date().getTime();
  const randomParam = Math.floor(Math.random() * 1000000); // Add randomness
  
  // 尝试获取多种格式，让浏览器自动选择兼容的格式
  return props.getApiUrl(`fire_detection_direct/result-video/${props.processId}?t=${timestamp}&r=${randomParam}`);
}

// Get original video URL with cache-busting
function getOriginalVideoURL() {
  // 优先使用从父组件传入的原始视频URL
  if (props.originalVideoUrl) {
    console.log('使用本地原始视频URL:', props.originalVideoUrl);
    return props.originalVideoUrl;
  }
  
  // 后备方案：尝试从服务器获取
  if (!props.processId) return '';
  const timestamp = new Date().getTime();
  const randomParam = Math.floor(Math.random() * 1000000); // Add randomness
  return props.getApiUrl(`fire_detection_direct/original-video/${props.processId}?t=${timestamp}&r=${randomParam}`);
}

// Video error handling with improved fallback mechanism
function handleVideoError(event, type) {
  console.error(`${type} video loading error:`, event);
  
  // Log detailed error info
  const videoUrl = type === 'original' ? getOriginalVideoURL() : getProcessedVideoURL();
  console.log({
    type: `${type} video loading error`,
    url: videoUrl,
    processId: props.processId,
    error: event.target?.error || event,
    errorCode: event.target?.error?.code,
    networkState: event.target?.networkState,
    readyState: event.target?.readyState
  });
  
  // 如果重试次数低于最大值，尝试不同的方法播放视频
  if (retryCount.value < maxRetries) {
    retryCount.value++;
    
    // 处理后视频加载失败时尝试其他格式
    if (type === 'processed') {
      tryAlternativeFormat(event.target);
    } else {
      // 对于原始视频，尝试简单的重载
      setTimeout(() => reloadVideo(type), 2000);
    }
    
    // 显示提示消息
    const typeText = type === 'original' ? '原始' : '处理后';
    ElMessage({
      message: `${typeText}视频加载失败，正在尝试其他格式...（尝试 ${retryCount.value}/${maxRetries}）`,
      type: 'warning',
      duration: 3000
    });
  } else {
    // 超过最大重试次数，切换到帧轮询模式
    if (type === 'original') {
      usingFramePlayerOriginal.value = true;
      
      // 如果帧还没有加载，加载它们
      if (originalFrames.value.length === 0) {
        fetchVideoFrames();
      }
      
      ElMessage({
        message: '原始视频无法播放，已切换到帧序列模式',
        type: 'info',
        duration: 5000
      });
    } else {
      usingFramePlayerProcessed.value = true;
      
      // 如果帧还没有加载，加载它们
      if (processedFrames.value.length === 0) {
        fetchVideoFrames();
      }
      
      ElMessage({
        message: '处理后视频无法播放，已切换到帧序列模式',
        type: 'info',
        duration: 5000
      });
    }
  }
}

// 尝试加载不同格式的处理后视频
function tryAlternativeFormat(videoElement) {
  if (!videoElement || !props.processId) return;
  
  // 记录当前视频URL和状态
  const currentSrc = videoElement.src;
  const wasPlaying = !videoElement.paused;
  const currentTime = videoElement.currentTime;
  
  // 尝试三种常见的视频格式
  const formats = ['mp4', 'avi', 'webm'];
  const currentFormat = currentSrc.includes('.avi') ? 'avi' : 
                       currentSrc.includes('.webm') ? 'webm' : 'mp4';
  
  // 找到当前格式在数组中的位置，然后选择下一个格式
  const currentIndex = formats.indexOf(currentFormat);
  const nextFormat = formats[(currentIndex + 1) % formats.length];
  
  console.log(`尝试切换到${nextFormat}格式，当前格式为${currentFormat}`);
  
  // 生成新的视频URL，指定格式
  const timestamp = new Date().getTime();
  const randomParam = Math.floor(Math.random() * 1000000);
  const newSrc = props.getApiUrl(`fire_detection_direct/result-video/${props.processId}?format=${nextFormat}&t=${timestamp}&r=${randomParam}`);
  
  // 设置新的视频源
  videoElement.src = newSrc;
  
  // 添加事件监听器，在视频可以播放时恢复播放位置
  videoElement.oncanplay = () => {
    videoElement.currentTime = currentTime;
    if (wasPlaying) videoElement.play();
    videoElement.oncanplay = null;
  };
  
  // 加载新视频
  videoElement.load();
  console.log(`尝试加载新格式: ${nextFormat}, URL: ${newSrc}`);
}

// Reload video with better error recovery
function reloadVideo(type) {
  if (!props.processId) return;
  
  const videoSelector = type === 'processed' ? '.processed-video video' : '.original-video video';
  const video = document.querySelector(videoSelector);
  
  if (video) {
    // Save current position
    const currentTime = video.currentTime;
    const wasPlaying = !video.paused;
    
    // Set new source with cache-busting
    const timestamp = new Date().getTime();
    const randomParam = Math.floor(Math.random() * 1000000);
    video.src = type === 'processed' ? 
      props.getApiUrl(`fire_detection_direct/result-video/${props.processId}?nocache=${timestamp}&r=${randomParam}`) : 
      props.getApiUrl(`fire_detection_direct/original-video/${props.processId}?nocache=${timestamp}&r=${randomParam}`);
    
    // Add event listener to restore position
    video.oncanplay = () => {
      video.currentTime = currentTime;
      if (wasPlaying) video.play();
      video.oncanplay = null; // Remove handler
    };
    
    video.load();
    console.log(`尝试重新加载${type === 'processed' ? '处理后' : '原始'}视频`);
  }
}

// Video loaded callback
function videoLoaded(type) {
  console.log(`${type}视频加载成功`);
  ElMessage.success(`${type === 'original' ? '原始' : '处理后'}视频加载成功`);
  
  // 重置重试计数
  retryCount.value = 0;
}

// Video waiting callback
function handleVideoWaiting(type) {
  console.log(`${type}视频加载中...`);
}

// Video stalled callback
function handleVideoStalled(type) {
  console.log(`${type}视频加载停滞，尝试恢复...`);
  setTimeout(() => reloadVideo(type), 1500);
}

// Download processed video
async function downloadProcessedVideo() {
  if (!props.processId) {
    ElMessage.warning('视频尚未处理');
    return;
  }
  
  try {
    const response = await fetch(props.getApiUrl(`fire_detection_direct/result-video/${props.processId}`));
    if (!response.ok) {
      throw new Error(`服务器错误: ${response.status} ${response.statusText}`);
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fire_detection_processed_${new Date().getTime()}.mp4`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    ElMessage.success('处理后视频下载已开始');
  } catch (error) {
    console.error('下载处理后视频出错:', error);
    ElMessage.error('视频下载失败，请稍后再试');
  }
}

// Download original video
async function downloadOriginalVideo() {
  if (!props.processId) {
    ElMessage.warning('视频尚未处理');
    return;
  }
  
  try {
    const response = await fetch(props.getApiUrl(`fire_detection_direct/original-video/${props.processId}`));
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fire_detection_original_${new Date().getTime()}.mp4`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    ElMessage.success('原始视频下载已开始');
  } catch (error) {
    console.error('下载原始视频出错:', error);
    ElMessage.error('视频下载失败，请稍后再试');
  }
}

// View frame details
function viewFrame(frame) {
  selectedFrame.value = frame;
}

// 处理帧加载完成事件
function handleFrameLoad(type) {
  // 在帧加载完成后，开始预加载后续帧
  preloadNextFrames(type);
}

// 预加载后续帧
function preloadNextFrames(type) {
  if (type === 'original') {
    preloadFrames(originalFrames.value, currentFrameIndexOriginal.value);
  } else {
    preloadFrames(processedFrames.value, currentFrameIndexProcessed.value);
  }
}

// 预加载帧列表中的指定数量的帧
function preloadFrames(frames, currentIndex, count = 5) {
  // 清空之前的预加载队列
  while (framePreloadQueue.value.length > 0) {
    const img = framePreloadQueue.value.pop();
    img.src = '';
  }
  
  // 添加新的预加载任务
  for (let i = 1; i <= count; i++) {
    const nextIndex = currentIndex + i;
    if (nextIndex < frames.length && !preloadedFrames.value.has(frames[nextIndex])) {
      const img = new Image();
      img.src = frames[nextIndex];
      img.onload = () => {
        preloadedFrames.value.add(frames[nextIndex]);
      };
      framePreloadQueue.value.push(img);
    }
  }
}

// 处理进度条拖动事件
function handleSeek(type) {
  if (type === 'original') {
    updateOriginalFrameTime();
    preloadFrames(originalFrames.value, currentFrameIndexOriginal.value);
  } else {
    updateCurrentFrameTime();
    preloadFrames(processedFrames.value, currentFrameIndexProcessed.value);
  }
}

// 更新当前帧时间
function updateCurrentFrameTime() {
  if (videoInfo.value.fps > 0 && processedFrames.value.length > 0) {
    // 根据帧索引和帧率计算当前时间点
    currentFrameTime.value = currentFrameIndexProcessed.value / videoInfo.value.fps;
  }
}

// 更新原始视频帧时间
function updateOriginalFrameTime() {
  if (videoInfo.value.fps > 0 && originalFrames.value.length > 0) {
    // 根据帧索引和帧率计算当前时间点
    originalFrameTime.value = currentFrameIndexOriginal.value / videoInfo.value.fps;
  }
}

// 格式化时间为 MM:SS 格式
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}
</script>

<style scoped>
.result-area {
  background-color: #f9f9f9;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.detection-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 15px;
  border-radius: 8px;
  font-weight: bold;
  font-size: 18px;
  margin-bottom: 15px;
  background-color: #2ecc71;
  color: white;
}

.detection-status.fire-detected {
  background-color: #e74c3c;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(231, 76, 60, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(231, 76, 60, 0);
  }
}

.result-summary {
  margin-bottom: 20px;
}

.detection-info {
  text-align: center;
  font-size: 16px;
  margin-top: 10px;
}

.videos-container {
  background-color: #2d3436;
  padding: 20px;
  border-radius: 10px;
  margin-top: 25px;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
  gap: 25px;
  margin-bottom: 20px;
}

.videos-container h3 {
  color: #f39c12;
  font-size: 20px;
  margin-bottom: 15px;
  border-left: 4px solid #e74c3c;
  padding-left: 10px;
}

.video-player {
  width: 100%;
  height: auto;
  max-height: 500px;
  border-radius: 8px;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
  background-color: #000;
  margin-bottom: 20px;
  border: 3px solid #333;
}

.video-placeholder {
  width: 100%;
  height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: #1e272e;
  color: #dcdde1;
  border-radius: 8px;
  font-size: 16px;
  margin-bottom: 15px;
  border: 2px dashed #718093;
}

/* 帧播放器样式 */
.frame-player-container {
  width: 100%;
  margin-bottom: 20px;
}

.frame-player {
  background-color: #000;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
  border: 3px solid #333;
}

.frame-display-area {
  position: relative;
  width: 100%;
  height: 280px;
}

.frame-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.frame-loading {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #dcdde1;
  font-size: 16px;
}

.frame-progress-bar {
  background-color: #1e272e;
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.frame-controls {
  background-color: #1e272e;
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.frame-info {
  color: #dcdde1;
  font-size: 14px;
  margin-left: 10px;
}

.frame-error {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #dcdde1;
}

.frame-error p {
  margin: 5px 0;
}

.frame-error .el-icon {
  margin-bottom: 10px;
}

.processing-details {
  background-color: #1e272e;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.details-table {
  width: 100%;
  color: #dcdde1;
}

.details-table td {
  padding: 8px 0;
}

.details-table td:first-child {
  width: 180px;
}

.video-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  margin-top: 20px;
  flex-wrap: wrap;
}

.fire-frames {
  background: linear-gradient(145deg, #2d3436, #2c3e50);
  padding: 25px;
  border-radius: 10px;
  margin-top: 30px;
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
}

.fire-frames h3 {
  color: #ff7675;
  font-size: 22px;
  margin-bottom: 20px;
  text-align: center;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
}

.selected-frame-container {
  background-color: rgba(0, 0, 0, 0.8);
  padding: 20px;
  border-radius: 10px;
  margin-bottom: 25px;
  border: 2px solid #e74c3c;
}

.selected-frame-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.selected-frame-header h4 {
  margin: 0;
  color: #f39c12;
  font-size: 20px;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
}

.selected-frame-image {
  max-width: 100%;
  margin-bottom: 20px;
  text-align: center;
  background-color: #000;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
}

.selected-frame-image img {
  max-width: 100%;
  max-height: 600px;
  object-fit: contain;
}

.selected-frame-info {
  color: #ecf0f1;
}

.selected-frame-info p {
  margin: 5px 0;
}

.frames-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 15px;
  margin-top: 20px;
}

.frame-item {
  border: 1px solid #34495e;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
  background-color: #2c3e50;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.frame-item:hover {
  transform: translateY(-5px) scale(1.05);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  border-color: #e74c3c;
}

.frame-item img {
  width: 100%;
  height: 130px;
  object-fit: cover;
  cursor: pointer;
  border-bottom: 1px solid #34495e;
  transition: all 0.3s ease;
}

.frame-item:hover img {
  filter: brightness(1.2);
}

.frame-info {
  padding: 10px;
  background-color: #1e272e;
  color: #dcdde1;
  font-size: 12px;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.no-frames-message {
  text-align: center;
  padding: 40px 20px;
  background-color: #2c3e50;
  border-radius: 8px;
  margin: 20px 0;
  color: #ecf0f1;
  border: 1px dashed #7f8c8d;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.no-frames-message p:first-child {
  font-size: 20px;
  margin-bottom: 10px;
  font-weight: bold;
  color: #e74c3c;
}

.pause-icon {
  display: inline-block;
  width: 14px;
  height: 14px;
  line-height: 14px;
  font-size: 16px;
  vertical-align: middle;
  margin-right: 5px;
}
</style> 