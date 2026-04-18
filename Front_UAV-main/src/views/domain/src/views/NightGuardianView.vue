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
                <el-button type="primary" class="upload-btn">
                  <el-icon><Upload /></el-icon>
                  <span>选择视频</span>
                </el-button>
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
            <el-button type="success" :disabled="!selectedFile" :loading="isProcessing" @click="processVideo" class="process-btn">
              <el-icon><VideoPlay /></el-icon>
              开始处理
            </el-button>
            <el-button type="info" :disabled="!hasResults" @click="resetAll" class="reset-btn">
              <el-icon><RefreshRight /></el-icon>
              重置
            </el-button>
          </div>
        </el-card>
      </el-col>
      
      <!-- 中间面板：视频和行为预览 (扩展宽度) -->
      <el-col :span="18">
        <el-card class="video-card">
          <template #header>
            <div class="card-header">
              <h3>行为检测</h3>
              <div class="header-actions">
                <el-tag v-if="processingStatus" :type="getStatusType" class="status-tag">{{ processingStatus }}</el-tag>
                <el-button v-if="hasResults" type="primary" size="small" @click="showResultsDrawer = true" class="view-results-btn">
                  <el-icon><View /></el-icon>
                  查看结果
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="video-container">
            <div v-if="!selectedFile && !processedVideoUrl" class="placeholder">
              <el-empty description="请上传视频文件进行行为检测" :image-size="150">
                <template #image>
                  <el-icon class="empty-icon"><VideoCamera /></el-icon>
                </template>
              </el-empty>
            </div>
            
            <div v-else-if="isProcessing" class="processing-indicator">
              <el-progress type="circle" :percentage="processingPercentage" :width="120" :stroke-width="8" status="warning">
                <template #default="{ percentage }">
                  <span class="progress-text">{{ percentage.toFixed(0) }}%</span>
                  <span class="progress-label">处理中</span>
                </template>
              </el-progress>
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
                <el-button type="primary" @click="refreshVideo" class="refresh-btn">
                  <el-icon><Refresh /></el-icon>
                  刷新视频
                </el-button>
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
        
        <!-- 底部面板：统计信息 -->
        <el-card v-if="hasResults" class="statistics-panel">
          <el-row :gutter="20">
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-value">{{ processingTime ? `${processingTime.toFixed(2)}秒` : '未知' }}</div>
                <div class="stat-label">处理时间</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-card danger">
                <div class="stat-value">{{ getDangerCount }}</div>
                <div class="stat-label">危险行为</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-card warning">
                <div class="stat-value">{{ getWarningCount }}</div>
                <div class="stat-label">警告行为</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-card success">
                <div class="stat-value">{{ getNormalCount }}</div>
                <div class="stat-label">正常行为</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 结果抽屉 -->
    <el-drawer
      v-model="showResultsDrawer"
      title="检测结果详情"
      direction="rtl"
      size="30%"
      :show-close="true"
      :before-close="handleDrawerClose"
      class="results-drawer"
      :destroy-on-close="false"
    >
      <template #header>
        <div class="drawer-header">
          <h3>行为检测结果</h3>
          <el-tag v-if="getDangerCount > 0" type="danger" effect="dark" class="summary-tag">
            {{ getDangerCount }} 个危险行为
          </el-tag>
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
            :hollow="result.alert_level === 'green'"
            :size="result.alert_level === 'red' ? 'large' : 'normal'"
            class="timeline-item"
          >
            <div class="timeline-content">
              <div class="timeline-title">
                <strong>{{ result.action }}</strong>
              </div>
              <div class="result-details">
                <span class="confidence">置信度: {{ (result.confidence * 100).toFixed(2) }}%</span>
                <el-tag size="small" :type="getAlertTagType(result.alert_level)" effect="dark">
                  {{ getAlertLevelText(result.alert_level) }}
                </el-tag>
              </div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
      
      <template #footer>
        <div class="drawer-footer">
          <el-button @click="showResultsDrawer = false">关闭</el-button>
          <el-button type="primary" @click="exportResults" :disabled="!detectionResults.length">
            <el-icon><Download /></el-icon> 导出结果
          </el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { Loading, Upload, VideoPlay, RefreshRight, View, Refresh, VideoCamera, Download } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { uploadVideo, getProcessedVideoUrl } from '../api/nightGuardian';
import PageHeader from '../components/common/PageHeader.vue';

export default {
  name: 'NightGuardianView',
  components: {
    PageHeader,
    Loading,
    Upload,
    VideoPlay,
    RefreshRight,
    View,
    Refresh,
    VideoCamera,
    Download
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
    const processingPercentage = ref(0);
    const showResultsDrawer = ref(false);
    
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
        simulateProgress();
        
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
          
          // 设置模拟结果用于展示
          setTimeout(() => {
            // 只在开发模式下添加模拟数据
            if (process.env.NODE_ENV === 'development' && detectionResults.value.length === 0) {
              detectionResults.value = [
                { action: '行走', timestamp: 1.2, confidence: 0.95, alert_level: 'green' },
                { action: '奔跑', timestamp: 3.5, confidence: 0.87, alert_level: 'yellow' },
                { action: '可疑活动', timestamp: 5.8, confidence: 0.92, alert_level: 'red' },
                { action: '停留', timestamp: 8.2, confidence: 0.88, alert_level: 'green' },
                { action: '携带物品', timestamp: 12.5, confidence: 0.78, alert_level: 'yellow' }
              ];
              processingTime.value = 3.4;
            }
          }, 1500);
          
          // 等待一秒后设置处理完成状态
          setTimeout(() => {
            isProcessing.value = false;
            processingStatus.value = '处理完成';
            processingPercentage.value = 100;
            ElMessage.success('视频处理完成，已准备好视频播放');
          }, 2000);
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
    
    // 模拟处理进度
    function simulateProgress() {
      processingPercentage.value = 0;
      const interval = setInterval(() => {
        if (processingPercentage.value >= 90 || !isProcessing.value) {
          clearInterval(interval);
        } else {
          processingPercentage.value += Math.floor(Math.random() * 10) + 1;
          if (processingPercentage.value > 90) {
            processingPercentage.value = 90;
          }
        }
      }, 500);
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
      processingPercentage.value = 0;
      
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
    
    function handleDrawerClose(done) {
      done();
    }
    
    function exportResults() {
      try {
        const resultsString = JSON.stringify(detectionResults.value, null, 2);
        const blob = new Blob([resultsString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `night_guardian_results_${new Date().getTime()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        ElMessage.success('结果导出成功');
      } catch (error) {
        console.error('导出结果失败:', error);
        ElMessage.error('导出结果失败');
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
      processingPercentage,
      modelSettings,
      hasResults,
      getStatusType,
      getDangerCount,
      getWarningCount,
      getNormalCount,
      showResultsDrawer,
      
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
      getAlertLevelText,
      handleDrawerClose,
      exportResults
    };
  }
}
</script>

<style scoped>
.night-guardian-container {
  padding: 20px;
  padding-top: 70px; /* 增加顶部间距，避免被导航栏遮挡 */
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  background: linear-gradient(45deg, #4f46e5, #00d2aa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.settings-panel,
.video-card {
  margin-bottom: 20px;
  height: calc(100% - 20px);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(79, 70, 229, 0.1);
  transition: all 0.3s ease;
}

.settings-panel:hover,
.video-card:hover {
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.15);
  transform: translateY(-3px);
}

.settings-panel .el-upload__tip {
  color: #909399;
  font-size: 13px;
  margin-top: 8px;
}

.model-settings h4,
.upload-section h4 {
  color: #4b5563;
  font-size: 16px;
  margin-bottom: 12px;
  font-weight: 600;
}

.video-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.03);
}

.player {
  width: 100%;
  max-height: 500px;
  background: #000;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
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

.empty-icon {
  font-size: 60px;
  color: #d1d5db;
}

.processing-indicator p {
  margin-top: 20px;
  color: #6b7280;
  font-size: 16px;
}

.progress-text {
  font-size: 24px;
  font-weight: bold;
  color: #4f46e5;
  display: block;
}

.progress-label {
  font-size: 14px;
  color: #6b7280;
  margin-top: 5px;
  display: block;
}

:deep(.el-progress__text) {
  color: #4f46e5 !important;
}

:deep(.el-progress-circle path:last-child) {
  stroke: linear-gradient(90deg, #4f46e5, #00d2aa) !important;
}

.video-error {
  margin-top: 15px;
  padding: 15px;
  text-align: center;
  color: #F56C6C;
  background-color: rgba(245, 108, 108, 0.1);
  border-radius: 8px;
  backdrop-filter: blur(5px);
}

.action-buttons {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.upload-btn,
.process-btn,
.reset-btn,
.refresh-btn,
.view-results-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
  border-radius: 8px;
}

.upload-btn:hover,
.process-btn:hover,
.reset-btn:hover,
.refresh-btn:hover,
.view-results-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.process-btn {
  background: linear-gradient(45deg, #10b981, #059669);
  border: none;
}

.status-tag {
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 6px;
}

.results-list {
  max-height: calc(100vh - 180px);
  overflow-y: auto;
  padding: 15px;
}

.timeline-content {
  background-color: rgba(255, 255, 255, 0.8);
  padding: 12px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border: 1px solid #ebeef5;
  margin-bottom: 8px;
}

.timeline-title {
  font-size: 16px;
  margin-bottom: 8px;
  color: #374151;
}

.result-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.confidence {
  color: #6b7280;
  font-size: 14px;
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

.statistics-panel {
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(79, 70, 229, 0.1);
  margin-top: 20px;
  padding: 20px;
  transition: all 0.3s ease;
}

.statistics-panel:hover {
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.15);
  transform: translateY(-3px);
}

.stat-card {
  text-align: center;
  padding: 15px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(79, 70, 229, 0.1);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 5px;
  background: linear-gradient(45deg, #4f46e5, #00d2aa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-card.danger .stat-value {
  background: linear-gradient(45deg, #F56C6C, #FF9A9E);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-card.warning .stat-value {
  background: linear-gradient(45deg, #E6A23C, #FFD166);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-card.success .stat-value {
  background: linear-gradient(45deg, #10b981, #059669);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
}

.drawer-header h3 {
  margin: 0;
  font-size: 18px;
  color: #374151;
  font-weight: 600;
}

.summary-tag {
  font-size: 12px;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  padding: 10px 20px;
  gap: 10px;
}

:deep(.el-drawer) {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
}

:deep(.el-drawer__header) {
  margin-bottom: 20px;
  padding: 15px 20px;
  border-bottom: 1px solid #f0f0f0;
}

:deep(.el-drawer__body) {
  padding: 0;
}

:deep(.el-timeline-item__node--normal) {
  left: -1px;
}

:deep(.el-timeline-item:hover) {
  transform: translateX(5px);
  transition: all 0.3s ease;
}

:deep(.el-timeline-item__content) {
  margin-left: 25px;
}

.timeline-item {
  transition: all 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.settings-panel, .video-card, .statistics-panel {
  animation: fadeIn 0.5s ease-out;
}

@keyframes slideIn {
  from { transform: translateX(50px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

:deep(.el-timeline-item) {
  animation: slideIn 0.3s ease-out;
  animation-fill-mode: both;
}

:deep(.el-timeline-item:nth-child(1)) { animation-delay: 0.1s; }
:deep(.el-timeline-item:nth-child(2)) { animation-delay: 0.2s; }
:deep(.el-timeline-item:nth-child(3)) { animation-delay: 0.3s; }
:deep(.el-timeline-item:nth-child(4)) { animation-delay: 0.4s; }
:deep(.el-timeline-item:nth-child(5)) { animation-delay: 0.5s; }
:deep(.el-timeline-item:nth-child(6)) { animation-delay: 0.6s; }
:deep(.el-timeline-item:nth-child(7)) { animation-delay: 0.7s; }
:deep(.el-timeline-item:nth-child(8)) { animation-delay: 0.8s; }

/* 响应式样式 */
@media (max-width: 768px) {
  .night-guardian-container {
    padding: 10px;
    padding-top: 60px;
  }
  
  .el-row {
    flex-direction: column;
  }
  
  .el-col {
    width: 100% !important;
    max-width: 100% !important;
  }
  
  .player {
    max-height: 300px;
  }
  
  .statistics-panel .el-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
  
  .statistics-panel .el-col {
    margin-bottom: 10px;
  }
}
</style>
