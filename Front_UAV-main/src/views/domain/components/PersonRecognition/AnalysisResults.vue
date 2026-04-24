<template>
  <div class="analysis-results" v-if="analysisResult">
    <div class="results-container">
      <!-- 图像预览区域 -->
      <div class="image-display-container" ref="imageContainer">
        <!-- 原图像 -->
        <img 
          :src="analysisResult.image_url" 
          alt="分析图像" 
          class="analysis-image"
          ref="imageRef"
          @load="onImageLoad"
          :style="{
            transform: `scale(${zoomLevel}) translate(${panX}px, ${panY}px)`,
          }"
        />
        
        <!-- 人物标注层 -->
        <div 
          class="annotation-layer"
          :style="{
            transform: `scale(${zoomLevel}) translate(${panX}px, ${panY}px)`,
          }"
        >
          <div 
            v-for="(person, index) in analysisResult.persons" 
            :key="index"
            class="person-annotation"
            :class="{ 'active': activePersonId === index }"
            :style="calculateBoxStyle(person.bbox)"
            @click="selectPerson(index)"
          >
            <div class="annotation-label">{{ index + 1 }}</div>
          </div>
        </div>
        
        <!-- 图像控制区 -->
        <div class="image-controls">
          <button class="control-button" @click="zoomIn">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m4-3h-6" />
            </svg>
          </button>
          <button class="control-button" @click="zoomOut">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
            </svg>
          </button>
          <button class="control-button" @click="resetZoom">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
          </button>
        </div>
      </div>
      
      <!-- 分析结果详情 -->
      <div class="results-details">
        <div class="summary-container">
          <h3 class="summary-title">分析总结</h3>
          <div class="summary-stats">
            <div class="stat-item">
              <div class="stat-value">{{ analysisResult.persons?.length || 0 }}</div>
              <div class="stat-label">检测到的人物</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ analysisResult.processing_time?.toFixed(2) || 0 }}s</div>
              <div class="stat-label">处理时间</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ analysisResult.mode === 'enhanced' ? '增强' : '普通' }}</div>
              <div class="stat-label">分析模式</div>
            </div>
          </div>
        </div>
        
        <!-- 人物详细信息 -->
        <div class="persons-container">
          <div class="persons-header">
            <h3 class="persons-title">人物信息</h3>
            <div class="filter-option">
              <input 
                type="text" 
                v-model="searchQuery" 
                placeholder="搜索人物特征..." 
                class="search-input" 
              />
            </div>
          </div>
          
          <div class="persons-list">
            <div 
              v-for="(person, index) in filteredPersons" 
              :key="index"
              class="person-card"
              :class="{ 'active': activePersonId === index }"
              @click="selectPerson(index)"
            >
              <div class="person-header">
                <div class="person-id">人物 {{ index + 1 }}</div>
                <div 
                  class="confidence-badge"
                  :class="getConfidenceClass(person.confidence)"
                >
                  {{ formatConfidence(person.confidence) }}
                </div>
              </div>
              
              <div class="person-details">
                <div class="detail-item">
                  <div class="detail-label">性别</div>
                  <div class="detail-value">{{ translateGender(person.gender) }}</div>
                </div>
                <div class="detail-item">
                  <div class="detail-label">年龄</div>
                  <div class="detail-value">{{ formatAge(person.age) }}</div>
                </div>
                <div class="detail-item">
                  <div class="detail-label">上衣颜色</div>
                  <div class="detail-value">
                    <span 
                      class="color-swatch" 
                      :style="{ backgroundColor: person.upper_color || '#ccc' }"
                    ></span>
                    {{ translateColor(person.upper_color) || '未知' }}
                  </div>
                </div>
                <div class="detail-item">
                  <div class="detail-label">下装颜色</div>
                  <div class="detail-value">
                    <span 
                      class="color-swatch" 
                      :style="{ backgroundColor: person.lower_color || '#ccc' }"
                    ></span>
                    {{ translateColor(person.lower_color) || '未知' }}
                  </div>
                </div>
              </div>
              
              <div class="person-actions">
                <button class="action-button highlight-button" @click.stop="highlightPerson(index)">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </button>
                <button class="action-button focus-button" @click.stop="focusOnPerson(index)">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 操作按钮区域 -->
    <div class="actions-container">
      <button class="action-btn export-btn" @click="exportResults">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        导出分析结果
      </button>
      <button class="action-btn reset-btn" @click="resetAnalysis">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" class="w-5 h-5">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        重新分析
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, nextTick, watch } from 'vue';
import personRecognitionService from '../../services/personRecognitionService';

const props = defineProps({
  analysisResult: {
    type: Object,
    default: null
  },
  highlightedPersonIndex: {
    type: Number,
    default: null
  }
});

const emit = defineEmits(['reset', 'export-complete', 'select-person']);

// 状态管理
const imageRef = ref(null);
const imageContainer = ref(null);
const activePersonId = ref(null);
const searchQuery = ref('');
const zoomLevel = ref(1);
const panX = ref(0);
const panY = ref(0);
const isPanning = ref(false);
const startPanX = ref(0);
const startPanY = ref(0);
const initialPanX = ref(0);
const initialPanY = ref(0);

// 过滤人物列表
const filteredPersons = computed(() => {
  if (!props.analysisResult?.persons || !searchQuery.value) {
    return props.analysisResult?.persons || [];
  }
  
  const query = searchQuery.value.toLowerCase();
  return props.analysisResult.persons.filter(person => {
    const gender = translateGender(person.gender).toLowerCase();
    const upperColor = translateColor(person.upper_color).toLowerCase();
    const lowerColor = translateColor(person.lower_color).toLowerCase();
    const age = person.age ? person.age.toString() : '';
    
    return gender.includes(query) || 
           upperColor.includes(query) || 
           lowerColor.includes(query) || 
           age.includes(query);
  });
});

// 图像加载完成
const onImageLoad = () => {
  resetZoom();
};

// 外部高亮联动（来自父组件/助手）
watch(
  () => props.highlightedPersonIndex,
  (idx) => {
    if (idx === null || idx === undefined) return;
    if (!props.analysisResult?.persons?.length) return;
    if (idx < 0 || idx >= props.analysisResult.persons.length) return;
    activePersonId.value = idx;
  }
);

// 缩放控制
const zoomIn = () => {
  zoomLevel.value = Math.min(zoomLevel.value + 0.2, 3);
};

const zoomOut = () => {
  zoomLevel.value = Math.max(zoomLevel.value - 0.2, 0.5);
};

const resetZoom = () => {
  zoomLevel.value = 1;
  panX.value = 0;
  panY.value = 0;
};

// 平移控制
const startPan = (e) => {
  if (e.button !== 0) return; // 只响应左键
  
  isPanning.value = true;
  startPanX.value = e.clientX;
  startPanY.value = e.clientY;
  initialPanX.value = panX.value;
  initialPanY.value = panY.value;
  
  document.addEventListener('mousemove', handlePan);
  document.addEventListener('mouseup', endPan);
};

const handlePan = (e) => {
  if (!isPanning.value) return;
  
  const dx = e.clientX - startPanX.value;
  const dy = e.clientY - startPanY.value;
  
  panX.value = initialPanX.value + dx / zoomLevel.value;
  panY.value = initialPanY.value + dy / zoomLevel.value;
};

const endPan = () => {
  isPanning.value = false;
  document.removeEventListener('mousemove', handlePan);
  document.removeEventListener('mouseup', endPan);
};

// 选择人物
const selectPerson = (index) => {
  activePersonId.value = index;
  emit('select-person', index);
};

// 高亮人物
const highlightPerson = (index) => {
  // 先取消当前高亮
  activePersonId.value = null;
  
  // 短暂延时后再高亮，产生闪烁效果
  setTimeout(() => {
    activePersonId.value = index;
  }, 100);
};

// 聚焦人物
const focusOnPerson = (index) => {
  if (!props.analysisResult?.persons?.[index]?.bbox) return;
  
  const person = props.analysisResult.persons[index];
  const bbox = person.bbox;
  
  // 重置缩放
  resetZoom();
  
  // 将人物居中显示
  nextTick(() => {
    if (!imageRef.value || !imageContainer.value) return;
    
    const img = imageRef.value;
    const container = imageContainer.value;
    
    const imgWidth = img.naturalWidth;
    const imgHeight = img.naturalHeight;
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    
    if (!imgWidth || !imgHeight) return;

  // bbox 统一约定为 xyxy（像素或归一化 0~1）
  let [x1, y1, x2, y2] = bbox;
  if (x1 <= 1 && y1 <= 1 && x2 <= 1 && y2 <= 1) {
    x1 *= imgWidth;
    x2 *= imgWidth;
    y1 *= imgHeight;
    y2 *= imgHeight;
  }

    const centerX = (x1 + x2) / 2;
    const centerY = (y1 + y2) / 2;

    // 计算图像适配容器时的整体缩放比例
    const scaleX = containerWidth / imgWidth;
    const scaleY = containerHeight / imgHeight;
    const baseScale = Math.min(scaleX, scaleY);

    // 计算 container 中心点在图像坐标系下的位置
    const containerCenterX = containerWidth / 2;
    const containerCenterY = containerHeight / 2;

    // 将人物中心移到容器中心
    panX.value = (containerCenterX - centerX * baseScale) / zoomLevel.value;
    panY.value = (containerCenterY - centerY * baseScale) / zoomLevel.value;
    
    // 适当放大
    zoomLevel.value = 1.5;
  });
};

// 计算标注框样式
const calculateBoxStyle = (bbox) => {
  if (!bbox || bbox.length !== 4) {
    console.warn('标注框数据格式不正确:', bbox);
    return {};
  }
  
  try {
    const imgWidth = imageRef.value?.naturalWidth;
    const imgHeight = imageRef.value?.naturalHeight;

    // bbox 统一约定为 xyxy（像素或归一化 0~1）
    let [x1, y1, x2, y2] = bbox;
    if (imgWidth && imgHeight && x1 <= 1 && y1 <= 1 && x2 <= 1 && y2 <= 1) {
      x1 *= imgWidth;
      x2 *= imgWidth;
      y1 *= imgHeight;
      y2 *= imgHeight;
    }

    const width = x2 - x1;
    const height = y2 - y1;
    if (width <= 0 || height <= 0) return {};

    // 优先使用百分比（适配 object-fit: contain）
    if (imgWidth && imgHeight) {
      return {
        left: `${(x1 / imgWidth) * 100}%`,
        top: `${(y1 / imgHeight) * 100}%`,
        width: `${(width / imgWidth) * 100}%`,
        height: `${(height / imgHeight) * 100}%`
      };
    }

    // 兜底：无法获取 naturalSize 时使用像素
    return {
      left: `${x1}px`,
      top: `${y1}px`,
      width: `${width}px`,
      height: `${height}px`
    };
  } catch (error) {
    console.error('计算标记框样式出错:', error);
    return {
      left: '0%',
      top: '0%',
      width: '10%',
      height: '10%',
      border: '2px solid yellow' // 特殊颜色标记错误
    };
  }
};

// 导出分析结果
const exportResults = async () => {
  try {
    let exportUrl;
    try {
      // 尝试调用API服务导出
      exportUrl = await personRecognitionService.exportResults(props.analysisResult);
    } catch (error) {
      console.warn('API导出服务请求失败，使用本地导出:', error);
      // 生成本地JSON导出
      const exportData = JSON.stringify(props.analysisResult, null, 2);
      const blob = new Blob([exportData], { type: 'application/json' });
      exportUrl = URL.createObjectURL(blob);
    }
    
    // 创建临时链接并触发下载
    const link = document.createElement('a');
    link.href = exportUrl;
    link.download = `person-analysis-${new Date().getTime()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    emit('export-complete', {
      success: true,
      message: '分析结果导出成功'
    });
  } catch (error) {
    console.error('导出失败:', error);
    emit('export-complete', {
      success: false,
      message: '导出失败: ' + error.message
    });
  }
};

// 重置分析
const resetAnalysis = () => {
  emit('reset');
};

// 工具函数
const formatAge = (age) => {
  if (!age && age !== 0) return '未知';
  return `${age.toFixed(1)} 岁`;
};

const formatConfidence = (confidence) => {
  if (!confidence && confidence !== 0) return '未知';
  return `${(confidence * 100).toFixed(0)}%`;
};

const getConfidenceClass = (confidence) => {
  if (!confidence) return 'confidence-unknown';
  
  if (confidence >= 0.8) return 'confidence-high';
  if (confidence >= 0.5) return 'confidence-medium';
  return 'confidence-low';
};

const translateGender = (gender) => {
  const genderMap = {
    'male': '男性',
    'female': '女性',
    'unknown': '未知'
  };
  
  return genderMap[gender] || '未知';
};

const translateColor = (color) => {
  if (!color) return '未知';

  const colorMap = {
    'red': '红色', 'darkred': '深红色',
    'green': '绿色',
    'blue': '蓝色', 'darkblue': '深蓝色', 'lightblue': '浅蓝色',
    'yellow': '黄色',
    'orange': '橙色',
    'purple': '紫色',
    'pink': '粉色',
    'brown': '棕色',
    'black': '黑色',
    'white': '白色',
    'gray': '灰色', 'grey': '灰色', 'lightgray': '浅灰色', 'darkgray': '深灰色',
    'cyan': '青色',
    'multicolor': '彩色',
  };

  return colorMap[color] || color;
};

// 组件卸载时清理
onUnmounted(() => {
  document.removeEventListener('mousemove', handlePan);
  document.removeEventListener('mouseup', endPan);
});
</script>

<style scoped>
.analysis-results {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
}

.results-container {
  display: flex;
  gap: 1.5rem;
  width: 100%;
}

.image-display-container {
  position: relative;
  width: 60%;
  height: 500px;
  border-radius: 0.5rem;
  overflow: hidden;
  background-color: #111827;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  cursor: grab;
}

.image-display-container:active {
  cursor: grabbing;
}

.analysis-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  transition: transform 0.2s;
  will-change: transform;
}

.annotation-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  will-change: transform;
}

.person-annotation {
  position: absolute;
  border: 2px solid rgba(79, 70, 229, 0.7);
  background-color: rgba(79, 70, 229, 0.1);
  border-radius: 0.25rem;
  pointer-events: auto;
  cursor: pointer;
  transition: all 0.2s;
}

.person-annotation:hover {
  border-color: rgba(79, 70, 229, 1);
  background-color: rgba(79, 70, 229, 0.2);
}

.person-annotation.active {
  border-color: #f59e0b;
  background-color: rgba(245, 158, 11, 0.2);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4);
  }
  70% {
    box-shadow: 0 0 0 5px rgba(245, 158, 11, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0);
  }
}

.annotation-label {
  position: absolute;
  top: -10px;
  left: -10px;
  background-color: #4f46e5;
  color: white;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
}

.person-annotation.active .annotation-label {
  background-color: #f59e0b;
}

.image-controls {
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  display: flex;
  gap: 0.5rem;
  z-index: 10;
}

.control-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.8);
  color: #1f2937;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.control-button:hover {
  background-color: white;
  transform: scale(1.05);
}

.results-details {
  width: 40%;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.summary-container {
  background-color: white;
  border-radius: 0.5rem;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.summary-title {
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 1rem;
  font-size: 1.125rem;
}

.summary-stats {
  display: flex;
  justify-content: space-around;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: #4f46e5;
}

.stat-label {
  font-size: 0.875rem;
  color: #6b7280;
  margin-top: 0.25rem;
}

.persons-container {
  background-color: white;
  border-radius: 0.5rem;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.persons-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.persons-title {
  font-weight: 600;
  color: #1f2937;
  font-size: 1.125rem;
}

.search-input {
  padding: 0.5rem;
  border-radius: 0.375rem;
  border: 1px solid #e5e7eb;
  width: 180px;
  font-size: 0.875rem;
}

.persons-list {
  flex-grow: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.person-card {
  background-color: #f8fafc;
  border-radius: 0.375rem;
  padding: 0.75rem;
  border-left: 3px solid #e5e7eb;
  transition: all 0.2s;
  cursor: pointer;
}

.person-card:hover {
  background-color: #f1f5f9;
  border-left-color: #4f46e5;
}

.person-card.active {
  background-color: #eef2ff;
  border-left-color: #f59e0b;
}

.person-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.person-id {
  font-weight: 600;
  color: #1f2937;
}

.confidence-badge {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
}

.confidence-high {
  background-color: #dcfce7;
  color: #16a34a;
}

.confidence-medium {
  background-color: #fef9c3;
  color: #ca8a04;
}

.confidence-low {
  background-color: #fee2e2;
  color: #dc2626;
}

.confidence-unknown {
  background-color: #f3f4f6;
  color: #6b7280;
}

.person-details {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
}

.detail-label {
  font-size: 0.75rem;
  color: #6b7280;
  margin-bottom: 0.25rem;
}

.detail-value {
  font-weight: 500;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.color-swatch {
  width: 1rem;
  height: 1rem;
  border-radius: 0.25rem;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.person-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.action-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.25rem;
  background-color: #f1f5f9;
  color: #334155;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.action-button:hover {
  background-color: #e2e8f0;
}

.highlight-button:hover {
  color: #4338ca;
}

.focus-button:hover {
  color: #4338ca;
}

.actions-container {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.export-btn {
  background-color: #4f46e5;
  color: white;
  border: none;
}

.export-btn:hover {
  background-color: #4338ca;
}

.reset-btn {
  background-color: #f1f5f9;
  color: #334155;
  border: 1px solid #e2e8f0;
}

.reset-btn:hover {
  background-color: #e2e8f0;
}
</style>
