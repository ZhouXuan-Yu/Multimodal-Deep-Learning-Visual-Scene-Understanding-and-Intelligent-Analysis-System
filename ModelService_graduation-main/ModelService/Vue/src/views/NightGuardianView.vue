<template>
  <div class="night-guardian-container">
    <page-header title="夜间保卫者系统" subtitle="红外视频行为检测与预警"></page-header>
    
    <el-row :gutter="20">
      <!-- 左侧面板：视频上传和设置 -->
      <el-col :span="6">
        <el-card class="settings-panel">
          <template #header>
            <div class="card-header">
              <h3>系统设置</h3>
            </div>
          </template>
          
          <div class="upload-section">
            <h4>视频上传</h4>
            <el-upload
              class="video-uploader"
              :action="null"
              :auto-upload="false"
              :on-change="handleFileChange"
              :limit="1"
              :file-list="fileList"
              accept="video/*"
            >
              <template #trigger>
                <el-button type="primary">选择视频</el-button>
              </template>
              <template #tip>
                <div class="el-upload__tip">请选择红外视频文件，支持mp4, mov等格式</div>
              </template>
            </el-upload>
          </div>
          
          <el-divider></el-divider>
          
          <div class="model-settings">
            <h4>模型配置</h4>
            <el-form :model="modelSettings" label-position="top">
              <el-form-item label="模型类型">
                <el-select v-model="modelSettings.modelType" placeholder="选择模型">
                  <el-option label="默认模型 (推荐)" value="OptimizedActionNetLite"></el-option>
                </el-select>
              </el-form-item>
              
              <el-form-item label="保存关键帧">
                <el-switch v-model="modelSettings.saveFrames"></el-switch>
              </el-form-item>
            </el-form>
          </div>
          
          <div class="action-buttons">
            <el-button type="success" :disabled="!selectedFile" :loading="isProcessing" @click="processVideo">开始处理</el-button>
            <el-button type="info" :disabled="!hasResults" @click="resetAll">重置</el-button>
          </div>
        </el-card>
      </el-col>
      
      <!-- 中间面板：视频和行为预览 -->
      <el-col :span="12">
        <el-card class="video-card">
          <template #header>
            <div class="card-header">
              <h3>行为检测</h3>
              <el-tag v-if="processingStatus" :type="getStatusType">{{ processingStatus }}</el-tag>
            </div>
          </template>
          
          <div class="video-container">
            <div v-if="!selectedFile && !processedVideoUrl" class="placeholder">
              <el-empty description="请上传视频文件进行行为检测"></el-empty>
            </div>
            
            <div v-else-if="isProcessing" class="processing-indicator">
              <el-icon class="is-loading"><Loading /></el-icon>
              <p>正在处理视频，请耐心等待...</p>
            </div>
            
            <div v-else-if="processedVideoUrl" class="video-player">
              <video 
                ref="videoPlayer"
                controls
                autoplay
                class="player"
                :src="processedVideoUrl"
                @error="handleVideoError"
                @loadeddata="handleVideoLoaded"
              ></video>
              <div v-if="videoError" class="video-error">
                <p>视频加载失败: {{ videoError }}</p>
                <el-button type="primary" @click="refreshVideo">刷新视频</el-button>
              </div>
            </div>
            
            <div v-else class="video-preview">
              <video 
                ref="previewPlayer"
                controls
                class="player"
                :src="previewUrl"
              ></video>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧面板：结果和警报 -->
      <el-col :span="6">
        <el-card class="results-panel">
          <template #header>
            <div class="card-header">
              <h3>检测结果</h3>
            </div>
          </template>
          
          <div v-if="!detectionResults.length" class="no-results">
            <el-empty description="暂无检测结果"></el-empty>
          </div>
          
          <div v-else class="results-list">
            <el-timeline>
              <el-timeline-item
                v-for="(result, index) in detectionResults"
                :key="index"
                :type="getAlertType(result.alert_level)"
                :color="getAlertColor(result.alert_level)"
                :timestamp="`${formatTimestamp(result.timestamp)}秒`"
              >
                <strong>{{ result.action }}</strong>
                <div class="result-details">
                  <span>置信度: {{ (result.confidence * 100).toFixed(2) }}%</span>
                  <el-tag size="small" :type="getAlertTagType(result.alert_level)">
                    {{ getAlertLevelText(result.alert_level) }}
                  </el-tag>
                </div>
              </el-timeline-item>
            </el-timeline>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 底部面板：统计信息 -->
    <el-card v-if="hasResults" class="statistics-panel">
      <el-descriptions title="处理统计" :column="4" border>
        <el-descriptions-item label="处理时间">
          {{ processingTime ? `${processingTime.toFixed(2)}秒` : '未知' }}
        </el-descriptions-item>
        <el-descriptions-item label="危险行为">
          {{ getDangerCount }}次
        </el-descriptions-item>
        <el-descriptions-item label="警告行为">
          {{ getWarningCount }}次
        </el-descriptions-item>
        <el-descriptions-item label="正常行为">
          {{ getNormalCount }}次
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { Loading } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { uploadVideo, getProcessedVideoUrl } from '@/api/nightGuardian';
import PageHeader from '@/components/common/PageHeader.vue';

export default {
  name: 'NightGuardianView',
  components: {
    PageHeader,
    Loading
  },
  setup() {
    // 状态管理
    const selectedFile = ref(null);
    const fileList = ref([]);
    const isProcessing = ref(false);
    const taskId = ref('');
    const processingStatus = ref('');
    const detectionResults = ref([]);
    const processedVideoUrl = ref('');
    const videoError = ref('');
    const previewUrl = ref('');
    const processingTime = ref(null);
    
    // 视频播放器引用
    const videoPlayer = ref(null);
    const previewPlayer = ref(null);
    
    // 模型设置
    const modelSettings = ref({
      modelType: 'OptimizedActionNetLite',
      threshold: 0.6,
      clipLen: 16,
      saveFrames: true
    });
    
    // 计算属性
    const hasResults = computed(() => detectionResults.value.length > 0);
    
    const getStatusType = computed(() => {
      if (!processingStatus.value) return '';
      switch (processingStatus.value) {
        case '处理完成':
          return 'success';
        case '处理中':
          return 'warning';
        case '处理失败':
          return 'danger';
        default:
          return 'info';
      }
    });
    
    const getDangerCount = computed(() => {
      return detectionResults.value.filter(r => r.alert_level === 'red').length;
    });
    
    const getWarningCount = computed(() => {
      return detectionResults.value.filter(r => r.alert_level === 'yellow').length;
    });
    
    const getNormalCount = computed(() => {
      return detectionResults.value.filter(r => r.alert_level === 'green').length;
    });
    
    // 方法
    function handleFileChange(file) {
      selectedFile.value = file.raw;
      
      // 创建本地视频预览URL
      if (previewUrl.value) {
        URL.revokeObjectURL(previewUrl.value);
      }
      previewUrl.value = URL.createObjectURL(file.raw);
    }
    
    async function processVideo() {
      if (!selectedFile.value) {
        ElMessage.warning('请先选择视频文件');
        return;
      }
      
      try {
        // 设置处理中状态
        isProcessing.value = true;
        processingStatus.value = '处理中';
        
        // 上传视频并处理
        const response = await uploadVideo(selectedFile.value, {
          modelType: modelSettings.value.modelType,
          saveFrames: modelSettings.value.saveFrames
        });
        
        console.log('上传响应:', response);
        
        // 获取任务ID和处理后的视频URL
        if (response && response.task_id) {
          // 保存任务ID
          taskId.value = response.task_id;
          ElMessage.success('视频上传成功，正在处理中...');
          
          // 清空原来的预览URL
          if (previewUrl.value) {
            URL.revokeObjectURL(previewUrl.value);
            previewUrl.value = '';
          }
          
          // 设置一个直接的请求URL，不通过中间函数
          const directVideoUrl = `/api/night-guardian/video/${taskId.value}`;
          console.log('尝试加载处理后的视频:', directVideoUrl);
          
          // 设置处理后的视频URL
          processedVideoUrl.value = directVideoUrl;
          
          // 等待一秒后设置处理完成状态
          setTimeout(() => {
            isProcessing.value = false;
            processingStatus.value = '处理完成';
            ElMessage.success('视频处理完成，已准备好视频播放');
          }, 1000);
        } else {
          ElMessage.error('视频处理失败');
          isProcessing.value = false;
          processingStatus.value = '处理失败';
        }
      } catch (error) {
        console.error('处理视频失败:', error);
        ElMessage.error('处理视频失败');
        isProcessing.value = false;
        processingStatus.value = '处理失败';
      }
    }
    
    // 处理视频加载错误
    function handleVideoError(e) {
      console.error('视频加载错误:', e);
      videoError.value = '视频可能仍在处理中或加载失败';
    }
    
    // 视频加载成功
    function handleVideoLoaded() {
      console.log('视频加载成功');
      videoError.value = '';
    }
    
    // 刷新视频
    function refreshVideo() {
      if (taskId.value) {
        // 添加时间戳刷新视频URL缓存
        const timestamp = new Date().getTime();
        processedVideoUrl.value = `/api/night-guardian/video/${taskId.value}?t=${timestamp}`;
        videoError.value = '';
        console.log('刷新视频:', processedVideoUrl.value);
      }
    }
    
    function resetAll() {
      // 重置状态
      selectedFile.value = null;
      fileList.value = [];
      isProcessing.value = false;
      taskId.value = '';
      processingStatus.value = '';
      detectionResults.value = [];
      processingTime.value = null;
      videoError.value = '';
      
      // 清除视频URL
      if (previewUrl.value) {
        URL.revokeObjectURL(previewUrl.value);
        previewUrl.value = '';
      }
      processedVideoUrl.value = '';
    }
    
    function formatTimestamp(seconds) {
      return seconds.toFixed(1);
    }
    
    function getAlertType(level) {
      switch (level) {
        case 'red':
          return 'danger';
        case 'yellow':
          return 'warning';
        default:
          return 'success';
      }
    }
    
    function getAlertColor(level) {
      switch (level) {
        case 'red':
          return '#F56C6C';
        case 'yellow':
          return '#E6A23C';
        default:
          return '#67C23A';
      }
    }
    
    function getAlertTagType(level) {
      switch (level) {
        case 'red':
          return 'danger';
        case 'yellow':
          return 'warning';
        default:
          return 'success';
      }
    }
    
    function getAlertLevelText(level) {
      switch (level) {
        case 'red':
          return '危险';
        case 'yellow':
          return '警告';
        default:
          return '正常';
      }
    }
    
    // 生命周期钩子
    onMounted(() => {
      // 页面加载时的初始化
    });
    
    onUnmounted(() => {
      // 清理工作
      if (previewUrl.value) {
        URL.revokeObjectURL(previewUrl.value);
      }
    });
    
    return {
      // 状态
      selectedFile,
      fileList,
      isProcessing,

      processingStatus,
      detectionResults,
      processedVideoUrl,
      previewUrl,
      videoError,
      processingTime,
      modelSettings,
      hasResults,
      getStatusType,
      getDangerCount,
      getWarningCount,
      getNormalCount,
      
      // 引用
      videoPlayer,
      previewPlayer,
      
      // 方法
      handleFileChange,
      processVideo,

      resetAll,
      formatTimestamp,
      handleVideoError,
      handleVideoLoaded,
      refreshVideo,
      getAlertType,
      getAlertColor,
      getAlertTagType,
      getAlertLevelText
    };
  }
}
</script>

<style scoped>
.night-guardian-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
}

.settings-panel,
.video-card,
.results-panel,
.statistics-panel {
  margin-bottom: 20px;
  height: calc(100% - 20px);
}

.video-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.player {
  width: 100%;
  max-height: 400px;
  background: #000;
}

.placeholder,
.processing-indicator {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  width: 100%;
}

.processing-indicator p {
  margin-top: 20px;
  color: #909399;
}

.video-error {
  margin-top: 10px;
  padding: 10px;
  text-align: center;
  color: #F56C6C;
  background-color: #FEF0F0;
  border-radius: 4px;
}

.action-buttons {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.results-list {
  max-height: 400px;
  overflow-y: auto;
}

.result-details {
  display: flex;
  justify-content: space-between;
  margin-top: 5px;
}

.no-results {
  height: 400px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.upload-section,
.model-settings {
  margin-bottom: 20px;
}
</style>
