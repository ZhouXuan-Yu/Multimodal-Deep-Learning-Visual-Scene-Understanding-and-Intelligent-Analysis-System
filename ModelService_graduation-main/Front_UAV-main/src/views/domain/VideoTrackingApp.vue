<template>
  <div class="video-tracking-app">
    <div class="app-header">
      <h1>视频目标追踪系统</h1>
      <div class="app-description">
        上传视频进行智能目标追踪分析，支持多种追踪算法和目标类型
      </div>
    </div>

    <div class="main-content">
      <!-- 上传组件 -->
      <div class="upload-section" v-if="!processingId">
        <el-upload
          class="video-uploader"
          drag
          action="#"
          :http-request="uploadVideo"
          :show-file-list="false"
          :before-upload="beforeUpload"
          accept="video/*"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            拖放视频文件到此处或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持MP4, AVI, MOV等格式视频文件，大小不超过500MB
            </div>
          </template>
        </el-upload>

        <div class="tracking-options">
          <h3>追踪选项</h3>
          <el-form label-position="top">
            <el-form-item label="追踪算法">
              <el-select v-model="trackingOptions.algorithm" placeholder="选择追踪算法">
                <el-option label="ByteTrack (推荐)" value="bytetrack" />
                <el-option label="DeepSORT" value="deepsort" />
                <el-option label="StrongSORT" value="strongsort" />
                <el-option label="BOTSORT" value="botsort" />
              </el-select>
            </el-form-item>
            <el-form-item label="目标类型">
              <el-select v-model="trackingOptions.targetType" placeholder="选择目标类型">
                <el-option label="所有目标" value="all" />
                <el-option label="仅人员" value="person" />
                <el-option label="仅车辆" value="vehicle" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
            <el-form-item label="置信度阈值">
              <el-slider v-model="trackingOptions.confidenceThreshold" :min="0" :max="1" :step="0.05" :format-tooltip="value => Math.round(value * 100) + '%'" />
            </el-form-item>
          </el-form>
        </div>
      </div>

      <!-- 处理进度 -->
      <div class="processing-section" v-if="processingId && !completed">
        <h2>视频处理中...</h2>
        <el-progress :percentage="processingProgress" :status="processingProgress < 100 ? '' : 'success'" />
        <div class="progress-info">
          <p>处理ID: {{ processingId }}</p>
          <p>状态: {{ processingStatus }}</p>
          <p v-if="estimatedTimeRemaining">预计剩余时间: {{ estimatedTimeRemaining }}</p>
        </div>
        <el-button type="danger" @click="cancelProcessing">取消处理</el-button>
      </div>

      <!-- 结果展示 -->
      <div class="results-section" v-if="completed">
        <h2>处理完成</h2>
        
        <div class="video-comparison">
          <div class="original-video">
            <h3>原始视频</h3>
            <video ref="originalVideo" controls>
              <source :src="originalVideoUrl" type="video/mp4" />
              您的浏览器不支持HTML5视频
            </video>
          </div>
          
          <div class="processed-video">
            <h3>追踪结果</h3>
            <video ref="processedVideo" controls>
              <source :src="processedVideoUrl" type="video/mp4" />
              您的浏览器不支持HTML5视频
            </video>
          </div>
        </div>
        
        <div class="tracking-statistics">
          <h3>追踪统计</h3>
          <el-descriptions border :column="3">
            <el-descriptions-item label="追踪目标总数">{{ statistics.totalObjects || 0 }}</el-descriptions-item>
            <el-descriptions-item label="追踪人员数量">{{ statistics.persons || 0 }}</el-descriptions-item>
            <el-descriptions-item label="追踪车辆数量">{{ statistics.vehicles || 0 }}</el-descriptions-item>
            <el-descriptions-item label="平均追踪时长">{{ statistics.avgTrackDuration || '0s' }}</el-descriptions-item>
            <el-descriptions-item label="最长追踪时长">{{ statistics.maxTrackDuration || '0s' }}</el-descriptions-item>
            <el-descriptions-item label="检测帧率">{{ statistics.fps || '0 FPS' }}</el-descriptions-item>
          </el-descriptions>
        </div>
        
        <div class="action-buttons">
          <el-button type="primary" @click="downloadResult">下载结果视频</el-button>
          <el-button @click="resetProcessing">处理新视频</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { ElMessage, ElNotification } from 'element-plus';
import { videoTrackingApi } from './api/videoTracking';
import { UploadFilled } from '@element-plus/icons-vue';

// 状态管理
const processingId = ref(null);
const processingProgress = ref(0);
const processingStatus = ref('');
const completed = ref(false);
const estimatedTimeRemaining = ref('');
const originalVideo = ref(null);
const processedVideo = ref(null);
const originalVideoUrl = ref('');
const processedVideoUrl = ref('');
const statistics = reactive({
  totalObjects: 0,
  persons: 0,
  vehicles: 0,
  avgTrackDuration: '',
  maxTrackDuration: '',
  fps: ''
});

// 追踪选项
const trackingOptions = reactive({
  algorithm: 'bytetrack',
  targetType: 'all',
  confidenceThreshold: 0.5
});

// 轮询定时器
let pollingTimer = null;

// 开始定时轮询进度
const startPolling = (id) => {
  if (pollingTimer) clearInterval(pollingTimer);
  
  pollingTimer = setInterval(async () => {
    try {
      const response = await videoTrackingApi.getTrackingStatus(id);
      
      processingProgress.value = response.progress || 0;
      processingStatus.value = response.status || '处理中';
      estimatedTimeRemaining.value = response.estimated_time || '';
      
      if (response.status === 'completed') {
        clearInterval(pollingTimer);
        loadResults(id);
      }
    } catch (error) {
      console.error('获取处理进度失败:', error);
      ElMessage.error('获取处理进度失败，请刷新页面重试');
    }
  }, 2000);
};

// 加载处理结果
const loadResults = async (id) => {
  try {
    const result = await videoTrackingApi.getTrackingResult(id);
    
    // 设置视频URL
    processedVideoUrl.value = videoTrackingApi.getProcessedVideoUrl(id);
    originalVideoUrl.value = result.original_video_url || '';
    
    // 设置统计数据
    statistics.totalObjects = result.statistics?.total_objects || 0;
    statistics.persons = result.statistics?.persons || 0;
    statistics.vehicles = result.statistics?.vehicles || 0;
    statistics.avgTrackDuration = result.statistics?.avg_track_duration || '0s';
    statistics.maxTrackDuration = result.statistics?.max_track_duration || '0s';
    statistics.fps = result.statistics?.fps || '0 FPS';
    
    // 更新状态
    completed.value = true;
    
    ElNotification({
      title: '处理完成',
      message: '视频处理已完成，可以查看结果',
      type: 'success'
    });
  } catch (error) {
    console.error('加载结果失败:', error);
    ElMessage.error('加载结果失败，请刷新页面重试');
  }
};

// 上传前验证
const beforeUpload = (file) => {
  // 检查文件类型
  const isVideo = file.type.startsWith('video/');
  if (!isVideo) {
    ElMessage.error('请上传视频文件!');
    return false;
  }
  
  // 检查文件大小 (500MB)
  const isLt500M = file.size / 1024 / 1024 < 500;
  if (!isLt500M) {
    ElMessage.error('视频大小不能超过500MB!');
    return false;
  }
  
  return true;
};

// 上传视频处理
const uploadVideo = async (options) => {
  try {
    const formData = new FormData();
    formData.append('file', options.file);
    formData.append('track_type', trackingOptions.targetType);
    formData.append('algorithm', trackingOptions.algorithm);
    formData.append('confidence_threshold', trackingOptions.confidenceThreshold);
    
    ElMessage.info('正在上传视频，请稍候...');
    
    const response = await videoTrackingApi.uploadVideo(formData);
    
    if (response.tracking_id) {
      processingId.value = response.tracking_id;
      processingProgress.value = 0;
      processingStatus.value = '初始化中';
      completed.value = false;
      
      startPolling(response.tracking_id);
      
      ElMessage.success('视频上传成功，开始处理');
    } else {
      throw new Error('上传失败，未获取到处理ID');
    }
  } catch (error) {
    console.error('上传视频失败:', error);
    ElMessage.error(`上传视频失败: ${error.message || '服务器错误'}`);
  }
};

// 取消处理
const cancelProcessing = () => {
  if (pollingTimer) clearInterval(pollingTimer);
  
  processingId.value = null;
  processingProgress.value = 0;
  processingStatus.value = '';
  completed.value = false;
  
  ElMessage.info('已取消视频处理');
};

// 下载结果视频
const downloadResult = () => {
  if (processedVideoUrl.value) {
    window.open(processedVideoUrl.value, '_blank');
  }
};

// 重置处理状态
const resetProcessing = () => {
  processingId.value = null;
  processingProgress.value = 0;
  processingStatus.value = '';
  completed.value = false;
  originalVideoUrl.value = '';
  processedVideoUrl.value = '';
  
  // 重置统计数据
  Object.keys(statistics).forEach(key => {
    if (typeof statistics[key] === 'number') {
      statistics[key] = 0;
    } else {
      statistics[key] = '';
    }
  });
};

// 生命周期钩子
onMounted(() => {
  // 在组件挂载时可以执行一些初始化操作
});

onUnmounted(() => {
  // 清除定时器
  if (pollingTimer) clearInterval(pollingTimer);
});
</script>

<style scoped>
.video-tracking-app {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.app-header {
  text-align: center;
  margin-bottom: 30px;
}

.app-header h1 {
  font-size: 28px;
  color: #303133;
  margin-bottom: 10px;
}

.app-description {
  color: #606266;
  font-size: 16px;
}

.main-content {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.upload-section {
  display: flex;
  gap: 30px;
  flex-wrap: wrap;
}

.video-uploader {
  flex: 1;
  min-width: 300px;
}

.tracking-options {
  flex: 1;
  min-width: 300px;
}

.processing-section {
  text-align: center;
  padding: 30px;
}

.progress-info {
  margin: 20px 0;
  text-align: left;
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
}

.video-comparison {
  display: flex;
  gap: 20px;
  margin: 20px 0;
  flex-wrap: wrap;
}

.original-video,
.processed-video {
  flex: 1;
  min-width: 400px;
}

.original-video video,
.processed-video video {
  width: 100%;
  border-radius: 4px;
  background: #000;
}

.tracking-statistics {
  margin: 30px 0;
}

.action-buttons {
  margin-top: 20px;
  display: flex;
  justify-content: center;
  gap: 15px;
}

@media (max-width: 768px) {
  .upload-section,
  .video-comparison {
    flex-direction: column;
  }
}
</style> 