<template>
  <div class="detection-results">
    <div class="results-container">
      <!-- 图像处理结果 -->
      <div v-if="resultType === 'image'" class="image-results">
        <div class="section-divider">
          <h3 class="divider-text">检测结果对比</h3>
        </div>
        
        <!-- 可见光图像结果 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div class="image-card">
            <div class="card-header">
              <h4 class="card-title">原始可见光图像</h4>
            </div>
            <div class="card-content">
              <div class="image-container">
                <img :src="imageResults?.rgb_image?.original || ''" class="result-image" alt="原始可见光图像" @error="handleImageError" />
              </div>
            </div>
          </div>
          
          <div class="image-card">
            <div class="card-header">
              <h4 class="card-title">可见光检测结果</h4>
              <span v-if="imageResults?.rgb_image?.detections" class="detection-count">
                检测到 {{ imageResults.rgb_image.detections.length }} 个目标
              </span>
            </div>
            <div class="card-content">
              <div class="image-container">
                <img :src="imageResults?.rgb_image?.processed || ''" class="result-image" alt="处理后可见光图像" @error="handleImageError" />
                <div class="detection-canvas-wrapper" v-if="imageResults?.rgb_image?.detections">
                  <canvas ref="rgbBoundingBoxesCanvas" class="detection-canvas"></canvas>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 热成像图像结果 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6" v-if="imageResults?.thermal_image">
          <div class="image-card">
            <div class="card-header">
              <h4 class="card-title">原始热成像图像</h4>
            </div>
            <div class="card-content">
              <div class="image-container">
                <img :src="imageResults?.thermal_image?.original || ''" class="result-image" alt="原始热成像图像" @error="handleImageError" />
              </div>
            </div>
          </div>
          
          <div class="image-card">
            <div class="card-header">
              <h4 class="card-title">热成像检测结果</h4>
              <span v-if="imageResults?.thermal_image?.detections" class="detection-count">
                检测到 {{ imageResults.thermal_image.detections.length }} 个目标
              </span>
            </div>
            <div class="card-content">
              <div class="image-container">
                <img :src="imageResults?.thermal_image?.processed || ''" class="result-image" alt="处理后热成像图像" @error="handleImageError" />
                <div class="detection-canvas-wrapper" v-if="imageResults?.thermal_image?.detections">
                  <canvas ref="thermalBoundingBoxesCanvas" class="detection-canvas"></canvas>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 检测结果统计 -->
        <div class="detection-stats-container" v-if="hasDetections">
          <div class="stats-header">
            <h3 class="stats-title">目标检测统计</h3>
          </div>
          <div class="stats-content">
            <table class="stats-table">
              <thead>
                <tr>
                  <th>图像类型</th>
                  <th>目标类别</th>
                  <th>数量</th>
                  <th>平均置信度</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(stat, index) in detectionStats" :key="index">
                  <td>{{ stat.imageType }}</td>
                  <td>{{ stat.class }}</td>
                  <td>{{ stat.count }}</td>
                  <td>{{ (stat.avgConfidence * 100).toFixed(1) }}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      
      <!-- 视频处理结果 -->
      <div v-if="resultType === 'video'" class="video-results">
        <div class="section-divider">
          <h3 class="divider-text">视频处理结果</h3>
        </div>
        
        <!-- 可见光视频结果 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div class="video-card" v-if="videoResults?.rgb_video?.original">
            <div class="card-header">
              <h4 class="card-title">原始可见光视频</h4>
            </div>
            <div class="card-content">
              <div class="video-container">
                <video 
                  :src="videoResults.rgb_video.original" 
                  class="result-video" 
                  controls
                  @error="handleVideoError"
                ></video>
              </div>
            </div>
          </div>
          
          <div class="video-card" v-if="videoResults?.rgb_video?.processed">
            <div class="card-header">
              <h4 class="card-title">处理后的可见光视频</h4>
            </div>
            <div class="card-content">
              <div class="video-container">
                <video 
                  :src="videoResults.rgb_video.processed" 
                  class="result-video" 
                  controls
                  @error="handleVideoError"
                ></video>
              </div>
              <button @click="downloadVideo(videoResults.rgb_video.processed, '可见光检测结果.mp4')" class="download-btn">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                下载处理后的视频
              </button>
            </div>
          </div>
        </div>
        
        <!-- 热成像视频结果 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6" v-if="videoResults?.thermal_video">
          <div class="video-card" v-if="videoResults.thermal_video.original">
            <div class="card-header">
              <h4 class="card-title">原始热成像视频</h4>
            </div>
            <div class="card-content">
              <div class="video-container">
                <video 
                  :src="videoResults.thermal_video.original" 
                  class="result-video" 
                  controls
                  @error="handleVideoError"
                ></video>
              </div>
            </div>
          </div>
          
          <div class="video-card" v-if="videoResults.thermal_video.processed">
            <div class="card-header">
              <h4 class="card-title">处理后的热成像视频</h4>
            </div>
            <div class="card-content">
              <div class="video-container">
                <video 
                  :src="videoResults.thermal_video.processed" 
                  class="result-video" 
                  controls
                  @error="handleVideoError"
                ></video>
              </div>
              <button @click="downloadVideo(videoResults.thermal_video.processed, '热成像检测结果.mp4')" class="download-btn">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                下载处理后的视频
              </button>
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
import { ref, onMounted, computed, watch } from 'vue';

const props = defineProps({
  resultType: {
    type: String,
    required: true,
    validator: value => ['image', 'video'].includes(value)
  },
  imageResults: {
    type: Object,
    default: null
  },
  videoResults: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['restart', 'error']);

// Canvas引用
const rgbBoundingBoxesCanvas = ref(null);
const thermalBoundingBoxesCanvas = ref(null);

// 计算检测统计信息
const detectionStats = computed(() => {
  const stats = [];
  
  if (props.imageResults) {
    if (props.imageResults.rgb_image && props.imageResults.rgb_image.detections) {
      // 按类别分组
      const rgbClasses = {};
      props.imageResults.rgb_image.detections.forEach(det => {
        if (!rgbClasses[det.class]) {
          rgbClasses[det.class] = { count: 0, confidence: 0 };
        }
        rgbClasses[det.class].count++;
        rgbClasses[det.class].confidence += det.confidence;
      });
      
      // 转换为数组格式
      Object.keys(rgbClasses).forEach(className => {
        stats.push({
          imageType: '可见光',
          class: className,
          count: rgbClasses[className].count,
          avgConfidence: rgbClasses[className].confidence / rgbClasses[className].count
        });
      });
    }
    
    if (props.imageResults.thermal_image && props.imageResults.thermal_image.detections) {
      // 按类别分组
      const thermalClasses = {};
      props.imageResults.thermal_image.detections.forEach(det => {
        if (!thermalClasses[det.class]) {
          thermalClasses[det.class] = { count: 0, confidence: 0 };
        }
        thermalClasses[det.class].count++;
        thermalClasses[det.class].confidence += det.confidence;
      });
      
      // 转换为数组格式
      Object.keys(thermalClasses).forEach(className => {
        stats.push({
          imageType: '热成像',
          class: className,
          count: thermalClasses[className].count,
          avgConfidence: thermalClasses[className].confidence / thermalClasses[className].count
        });
      });
    }
  }
  
  return stats;
});

const hasDetections = computed(() => {
  return detectionStats.value.length > 0;
});

// 生成随机颜色
const getRandomColor = () => {
  const letters = '0123456789ABCDEF';
  let color = '#';
  for (let i = 0; i < 6; i++) {
    color += letters[Math.floor(Math.random() * 16)];
  }
  return color;
};

// 绘制检测边界框
const drawDetectionBoxes = (canvas, image, detections) => {
  if (!canvas || !image || !detections || detections.length === 0) return;
  
  const ctx = canvas.getContext('2d');
  const img = new Image();
  
  img.onload = () => {
    canvas.width = img.width;
    canvas.height = img.height;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // 为每个类别分配一个固定颜色
    const classColors = {};
    
    detections.forEach(detection => {
      // 如果该类别还没有颜色，则分配一个
      if (!classColors[detection.class]) {
        classColors[detection.class] = getRandomColor();
      }
      
      const color = classColors[detection.class];
      
      // 绘制边界框
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(detection.x, detection.y, detection.width, detection.height);
      
      // 绘制标签背景
      const text = `${detection.class}: ${(detection.confidence * 100).toFixed(0)}%`;
      ctx.font = '14px Arial';
      const textWidth = ctx.measureText(text).width;
      ctx.fillStyle = color;
      ctx.fillRect(detection.x, detection.y - 20, textWidth + 10, 20);
      
      // 绘制标签文本
      ctx.fillStyle = 'white';
      ctx.fillText(text, detection.x + 5, detection.y - 5);
    });
  };
  
  img.src = image;
};

// 图像加载错误处理
const handleImageError = (event) => {
  emit('error', '图像加载失败，请检查图像URL是否正确');
  console.error('图像加载错误:', event);
};

// 视频加载错误处理
const handleVideoError = (event) => {
  emit('error', '视频加载失败，请检查视频URL是否正确');
  console.error('视频加载错误:', event);
};

// 下载视频
const downloadVideo = (url, filename) => {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

// 组件挂载后处理
onMounted(() => {
  if (props.resultType === 'image' && props.imageResults) {
    // 绘制可见光检测框
    if (props.imageResults.rgb_image && 
        props.imageResults.rgb_image.processed && 
        props.imageResults.rgb_image.detections) {
      drawDetectionBoxes(
        rgbBoundingBoxesCanvas.value, 
        props.imageResults.rgb_image.processed, 
        props.imageResults.rgb_image.detections
      );
    }
    
    // 绘制热成像检测框
    if (props.imageResults.thermal_image && 
        props.imageResults.thermal_image.processed && 
        props.imageResults.thermal_image.detections) {
      drawDetectionBoxes(
        thermalBoundingBoxesCanvas.value, 
        props.imageResults.thermal_image.processed, 
        props.imageResults.thermal_image.detections
      );
    }
  }
});

// 监听结果变化，重新绘制检测框
watch(() => props.imageResults, (newVal) => {
  if (props.resultType === 'image' && newVal) {
    // 绘制可见光检测框
    if (newVal.rgb_image && 
        newVal.rgb_image.processed && 
        newVal.rgb_image.detections) {
      drawDetectionBoxes(
        rgbBoundingBoxesCanvas.value, 
        newVal.rgb_image.processed, 
        newVal.rgb_image.detections
      );
    }
    
    // 绘制热成像检测框
    if (newVal.thermal_image && 
        newVal.thermal_image.processed && 
        newVal.thermal_image.detections) {
      drawDetectionBoxes(
        thermalBoundingBoxesCanvas.value, 
        newVal.thermal_image.processed, 
        newVal.thermal_image.detections
      );
    }
  }
}, { deep: true });
</script>

<style scoped>
.detection-results {
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

.image-card, .video-card {
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

.detection-count {
  padding: 0.25rem 0.5rem;
  background-color: #4f46e5;
  color: white;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
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

.detection-canvas-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.detection-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.detection-stats-container {
  margin-top: 2rem;
  background-color: white;
  border-radius: 0.5rem;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stats-header {
  padding: 1rem;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.stats-title {
  font-size: 1.125rem;
  font-weight: 500;
  color: #334155;
}

.stats-content {
  padding: 1rem;
  overflow-x: auto;
}

.stats-table {
  width: 100%;
  border-collapse: collapse;
}

.stats-table th, .stats-table td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

.stats-table th {
  background-color: #f8fafc;
  font-weight: 500;
  color: #334155;
}

.stats-table td {
  color: #4b5563;
}

.controls-container {
  display: flex;
  justify-content: center;
  margin-top: 2rem;
}

.restart-btn {
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

.restart-btn:hover {
  background-color: #4338ca;
}

.download-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  margin-top: 0.75rem;
  background-color: #0ea5e9;
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.download-btn:hover {
  background-color: #0284c7;
}
</style>
