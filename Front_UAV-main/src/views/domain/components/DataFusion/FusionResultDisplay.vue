<template>
  <div class="fusion-result-display">
    <div class="results-container">
      <!-- 图像融合结果 -->
      <div v-if="resultType === 'image'" class="image-results">
        <div class="section-divider">
          <h3 class="divider-text">融合结果对比</h3>
        </div>
        
        <!-- 输入图像对比 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div class="image-card">
            <div class="card-header">
              <h4 class="card-title">原始可见光图像</h4>
            </div>
            <div class="card-content">
              <div class="image-container">
                <img :src="fusionResult?.rgbImageUrl || ''" class="result-image" alt="原始可见光图像" @error="handleImageError" />
              </div>
            </div>
          </div>
          
          <div class="image-card">
            <div class="card-header">
              <h4 class="card-title">原始热成像图像</h4>
            </div>
            <div class="card-content">
              <div class="image-container">
                <img :src="fusionResult?.thermalImageUrl || ''" class="result-image" alt="原始热成像图像" @error="handleImageError" />
              </div>
            </div>
          </div>
        </div>
        
        <!-- 融合结果 -->
        <div class="fusion-result-section">
          <div class="fusion-result-card">
            <div class="card-header">
              <h4 class="card-title">融合结果图像</h4>
            </div>
            <div class="card-content">
              <div class="fusion-image-container">
                <img :src="getProperImageUrl(fusionResult?.fusionImageUrl)" class="fusion-image" alt="融合结果图像" @error="handleImageError" />
              </div>
              <button @click="downloadImage(fusionResult?.fusionImageUrl, '融合结果.jpg')" class="download-btn">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                下载融合图像
              </button>
            </div>
          </div>
        </div>
        
        <!-- 融合元数据 -->
        <div v-if="fusionResult?.metadata" class="metadata-section">
          <div class="metadata-card">
            <div class="card-header">
              <h4 class="card-title">融合详情</h4>
            </div>
            <div class="metadata-content">
              <div class="metadata-row" v-if="fusionResult.metadata.fusionMethod">
                <div class="metadata-label">融合方法:</div>
                <div class="metadata-value">{{ fusionResult.metadata.fusionMethod }}</div>
              </div>
              <div class="metadata-row" v-if="fusionResult.metadata.processingTime">
                <div class="metadata-label">处理时间:</div>
                <div class="metadata-value">{{ fusionResult.metadata.processingTime }}秒</div>
              </div>
              <div class="metadata-row" v-if="fusionResult.metadata.enhancementLevel">
                <div class="metadata-label">增强等级:</div>
                <div class="metadata-value">{{ fusionResult.metadata.enhancementLevel }}</div>
              </div>
              <div class="metadata-row" v-if="fusionResult.metadata.resolution">
                <div class="metadata-label">分辨率:</div>
                <div class="metadata-value">{{ fusionResult.metadata.resolution }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 视频融合结果 -->
      <div v-if="resultType === 'video'" class="video-results">
        <div class="section-divider">
          <h3 class="divider-text">视频融合结果</h3>
        </div>
        
        <!-- 输入视频 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div class="video-card" v-if="fusionResult?.rgbVideoUrl">
            <div class="card-header">
              <h4 class="card-title">原始可见光视频</h4>
            </div>
            <div class="card-content">
              <div class="video-container">
                <video 
                  :src="getProperVideoUrl(fusionResult.rgbVideoUrl)" 
                  class="result-video" 
                  controls
                  @error="handleVideoError"
                ></video>
              </div>
            </div>
          </div>
          
          <div class="video-card" v-if="fusionResult?.thermalVideoUrl">
            <div class="card-header">
              <h4 class="card-title">原始热成像视频</h4>
            </div>
            <div class="card-content">
              <div class="video-container">
                <video 
                  :src="getProperVideoUrl(fusionResult.thermalVideoUrl)" 
                  class="result-video" 
                  controls
                  @error="handleVideoError"
                ></video>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 融合视频结果 -->
        <div class="fusion-result-section">
          <div class="fusion-result-card">
            <div class="card-header">
              <h4 class="card-title">融合结果视频</h4>
            </div>
            <div class="card-content">
              <div class="fusion-video-container">
                <video 
                  :src="getProperVideoUrl(fusionResult?.fusionVideoUrl)" 
                  class="fusion-video" 
                  controls
                  @error="handleVideoError"
                ></video>
              </div>
              <button @click="downloadVideo(fusionResult?.fusionVideoUrl, '融合结果.mp4')" class="download-btn">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                下载融合视频
              </button>
            </div>
          </div>
        </div>
        
        <!-- 融合元数据 -->
        <div v-if="fusionResult?.metadata" class="metadata-section">
          <div class="metadata-card">
            <div class="card-header">
              <h4 class="card-title">融合详情</h4>
            </div>
            <div class="metadata-content">
              <div class="metadata-row" v-if="fusionResult.metadata.fusionMethod">
                <div class="metadata-label">融合方法:</div>
                <div class="metadata-value">{{ fusionResult.metadata.fusionMethod }}</div>
              </div>
              <div class="metadata-row" v-if="fusionResult.metadata.processingTime">
                <div class="metadata-label">处理时间:</div>
                <div class="metadata-value">{{ fusionResult.metadata.processingTime }}秒</div>
              </div>
              <div class="metadata-row" v-if="fusionResult.metadata.enhancementLevel">
                <div class="metadata-label">增强等级:</div>
                <div class="metadata-value">{{ fusionResult.metadata.enhancementLevel }}</div>
              </div>
              <div class="metadata-row" v-if="fusionResult.metadata.resolution">
                <div class="metadata-label">分辨率:</div>
                <div class="metadata-value">{{ fusionResult.metadata.resolution }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 控制按钮 -->
      <div class="controls-container">
        <button 
          @click="$emit('restart')" 
          class="restart-btn"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          重新开始
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  resultType: {
    type: String,
    required: true,
    validator: value => ['image', 'video'].includes(value)
  },
  fusionResult: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['restart', 'error']);

// 构建完整URL
const getProperImageUrl = (url) => {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  if (url.startsWith('/')) return url;
  return `/${url}`;
};

// 构建视频URL
const getProperVideoUrl = (url) => {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  if (url.startsWith('/')) return url;
  return `/${url}`;
};

// 图像加载错误处理
const handleImageError = (event) => {
  console.error('图像加载失败:', event);
  emit('error', '图像加载失败，请检查图像URL是否正确');
};

// 视频加载错误处理
const handleVideoError = (event) => {
  console.error('视频加载失败:', event);
  emit('error', '视频加载失败，请检查视频URL是否正确');
};

// 下载图像
const downloadImage = (url, filename) => {
  if (!url) return;
  
  const a = document.createElement('a');
  a.href = getProperImageUrl(url);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

// 下载视频
const downloadVideo = (url, filename) => {
  if (!url) return;
  
  const a = document.createElement('a');
  a.href = getProperVideoUrl(url);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};
</script>

<style scoped>
.fusion-result-display {
  width: 100%;
}

.results-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.section-divider {
  position: relative;
  text-align: center;
  margin: 2rem 0;
}

.divider-text {
  position: relative;
  display: inline-block;
  background-color: white;
  padding: 0 1rem;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
  z-index: 1;
}

.section-divider::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background-color: #e2e8f0;
  z-index: 0;
}

.image-card, .video-card, .fusion-result-card, .metadata-card {
  background-color: white;
  border-radius: 0.5rem;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-header {
  padding: 1rem;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 1rem;
  font-weight: 500;
  color: #334155;
}

.card-content {
  padding: 1rem;
  position: relative;
}

.image-container, .video-container {
  position: relative;
  width: 100%;
  overflow: hidden;
  display: flex;
  justify-content: center;
  min-height: 200px;
}

.result-image, .result-video {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
}

.fusion-result-section {
  margin: 2rem 0;
}

.fusion-image-container, .fusion-video-container {
  position: relative;
  width: 100%;
  overflow: hidden;
  display: flex;
  justify-content: center;
  min-height: 300px;
  margin-bottom: 1rem;
}

.fusion-image, .fusion-video {
  max-width: 100%;
  max-height: 500px;
  object-fit: contain;
}

.metadata-section {
  margin-top: 2rem;
}

.metadata-content {
  padding: 1.5rem;
}

.metadata-row {
  display: flex;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.metadata-row:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.metadata-label {
  width: 6rem;
  font-weight: 500;
  color: #334155;
}

.metadata-value {
  flex: 1;
  color: #4b5563;
}

.controls-container {
  display: flex;
  justify-content: center;
  margin-top: 2rem;
}

.restart-btn, .download-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  background-color: #4f46e5;
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.restart-btn:hover, .download-btn:hover {
  background-color: #4338ca;
}

.download-btn {
  background-color: #0ea5e9;
}

.download-btn:hover {
  background-color: #0284c7;
}
</style>
