<script setup>
import { computed } from 'vue';

const props = defineProps({
  monitoringResults: {
    type: Object,
    default: () => ({
      matches: [],
      total_frames: 0,
      total_detections: 0,
      video_url: '',
      target_plate: ''
    })
  }
});

// 判断是否有结果
const hasResults = computed(() => {
  return props.monitoringResults && props.monitoringResults.matches && props.monitoringResults.matches.length > 0;
});

// 判断是否有视频
const hasVideo = computed(() => {
  return !!props.monitoringResults.video_url;
});

// 计算匹配率
const matchRate = computed(() => {
  if (!props.monitoringResults.total_frames || props.monitoringResults.total_frames === 0) {
    return '0%';
  }
  
  const rate = (props.monitoringResults.matches.length / props.monitoringResults.total_frames) * 100;
  return rate.toFixed(1) + '%';
});

// 格式化时间戳
const formatTimestamp = (timestamp) => {
  if (!timestamp) return '--';
  
  const seconds = Math.floor(timestamp);
  const milliseconds = Math.round((timestamp - seconds) * 1000);
  
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${milliseconds.toString().padStart(3, '0')}`;
};

// 格式化置信度
const formatConfidence = (confidence) => {
  if (confidence === undefined || confidence === null) return '--';
  return `${(confidence * 100).toFixed(1)}%`;
};

// 截取视频帧URL
const frameUrl = (match) => {
  return match.frame_url || '';
};
</script>

<template>
  <div class="monitoring-results">
    <div class="results-header">
      <h3 class="results-title">监控结果</h3>
      
      <div class="results-summary">
        <div class="summary-item">
          <div class="item-label">目标车牌</div>
          <div class="item-value target-plate">{{ monitoringResults.target_plate || '--' }}</div>
        </div>
        <div class="summary-item">
          <div class="item-label">总检测帧数</div>
          <div class="item-value">{{ monitoringResults.total_frames || 0 }}</div>
        </div>
        <div class="summary-item">
          <div class="item-label">匹配次数</div>
          <div class="item-value">{{ monitoringResults.matches?.length || 0 }}</div>
        </div>
        <div class="summary-item">
          <div class="item-label">匹配率</div>
          <div class="item-value">{{ matchRate }}</div>
        </div>
      </div>
    </div>
    
    <!-- 视频播放器 -->
    <div v-if="hasVideo" class="video-container">
      <video 
        controls 
        class="result-video"
        :src="monitoringResults.video_url"
      >
        您的浏览器不支持视频播放
      </video>
    </div>
    
    <!-- 匹配结果 -->
    <div v-if="hasResults" class="matches-container">
      <h4 class="matches-title">匹配列表</h4>
      
      <div class="matches-grid">
        <div 
          v-for="(match, index) in monitoringResults.matches" 
          :key="index"
          class="match-card"
        >
          <div class="match-image">
            <img 
              v-if="frameUrl(match)" 
              :src="frameUrl(match)" 
              alt="匹配帧" 
              class="frame-image"
            />
            <div v-else class="no-frame">无帧图像</div>
          </div>
          
          <div class="match-details">
            <div class="detail-row">
              <div class="detail-label">时间点</div>
              <div class="detail-value">{{ formatTimestamp(match.timestamp) }}</div>
            </div>
            <div class="detail-row">
              <div class="detail-label">车牌号</div>
              <div class="detail-value">{{ match.plate_no || '--' }}</div>
            </div>
            <div class="detail-row">
              <div class="detail-label">置信度</div>
              <div class="detail-value">{{ formatConfidence(match.confidence) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 无结果状态 -->
    <div v-else-if="monitoringResults.total_frames > 0" class="no-matches">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="8" y1="12" x2="16" y2="12"></line>
      </svg>
      <h3>未找到匹配结果</h3>
      <p>在监控视频中未找到与目标车牌匹配的结果</p>
    </div>
  </div>
</template>

<style scoped>
.monitoring-results {
  width: 100%;
  padding: 1.5rem;
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.results-header {
  margin-bottom: 1.5rem;
}

.results-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 1rem;
}

.results-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  background-color: #f9fafb;
  border-radius: 0.5rem;
  padding: 1rem;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.item-label {
  font-size: 0.75rem;
  color: #6b7280;
}

.item-value {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
}

.target-plate {
  color: #4f46e5;
}

.video-container {
  margin-bottom: 1.5rem;
  border-radius: 0.5rem;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.result-video {
  width: 100%;
  background-color: #000;
}

.matches-title {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 1rem;
}

.matches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.match-card {
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
}

.match-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.match-image {
  height: 120px;
  background-color: #f3f4f6;
}

.frame-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-frame {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 0.875rem;
}

.match-details {
  padding: 0.75rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
  padding: 0.25rem 0;
}

.detail-label {
  color: #6b7280;
}

.detail-value {
  font-weight: 500;
  color: #111827;
}

.no-matches {
  padding: 3rem 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #6b7280;
}

.no-matches h3 {
  margin: 1rem 0 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
}

.no-matches p {
  max-width: 24rem;
  font-size: 0.875rem;
  line-height: 1.5;
}
</style>
