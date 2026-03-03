<script setup>
import { computed } from 'vue';

const props = defineProps({
  recognitionData: {
    type: Object,
    default: () => ({
      plates: [],
      imageUrl: '',
      timestamp: ''
    })
  }
});

const emit = defineEmits(['set-target']);

// 设置目标车牌
const setTargetPlate = (plate) => {
  emit('set-target', plate);
};

// 格式化车牌置信度
const formatConfidence = (confidence) => {
  if (confidence === undefined || confidence === null) return '未知';
  return `${(confidence * 100).toFixed(1)}%`;
};

// 获取车牌类型标签
const getPlateTypeTag = (type) => {
  if (!type) return { label: '普通', color: '#64748b' };
  
  const typeMap = {
    'blue': { label: '普通蓝牌', color: '#3b82f6' },
    'green': { label: '新能源', color: '#10b981' },
    'yellow': { label: '黄牌', color: '#f59e0b' },
    'white': { label: '白色', color: '#64748b' },
    'black': { label: '黑色', color: '#1e293b' },
    'police': { label: '警车', color: '#ef4444' },
    'armed': { label: '武警', color: '#9333ea' },
    'military': { label: '军队', color: '#65a30d' },
    'embassy': { label: '使馆', color: '#0284c7' },
    'hongkong': { label: '港澳', color: '#6366f1' },
    'double': { label: '双层', color: '#f43f5e' }
  };
  
  return typeMap[type] || { label: type, color: '#64748b' };
};

// 格式化车牌号码，特殊处理双层车牌
const formatPlateNumber = (plateNo, plateType) => {
  if (!plateNo) return '';
  
  // 双层车牌通常有特殊格式，例如中间有'-'
  if (plateType === 'double' && plateNo.includes('-')) {
    const [upper, lower] = plateNo.split('-');
    return `<div class="double-plate">
              <div class="double-plate-upper">${upper}</div>
              <div class="double-plate-lower">${lower}</div>
            </div>`;
  }
  
  return plateNo;
};

// 获取车牌图片URL
const getPlateImageUrl = (plate) => {
  return plate.crop_url || '';
};

// 图片是否存在
const hasImage = computed(() => {
  return !!props.recognitionData.imageUrl;
});

// 有无识别结果
const hasPlates = computed(() => {
  return props.recognitionData.plates && props.recognitionData.plates.length > 0;
});
</script>

<template>
  <div class="recognition-results">
    <!-- 预览图片 -->
    <div v-if="hasImage" class="result-image-container">
      <img 
        :src="recognitionData.imageUrl" 
        alt="车牌识别图片" 
        class="result-image"
      />
    </div>
    
    <!-- 识别结果表格 -->
    <div v-if="hasPlates" class="result-table-container">
      <h3 class="result-title">识别结果</h3>
      <div class="result-timestamp">识别时间: {{ recognitionData.timestamp }}</div>
      
      <table class="result-table">
        <thead>
          <tr>
            <th>车牌图像</th>
            <th>车牌号码</th>
            <th>类型</th>
            <th>置信度</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(plate, index) in recognitionData.plates" :key="index">
            <td class="plate-image-cell">
              <img 
                v-if="getPlateImageUrl(plate)" 
                :src="getPlateImageUrl(plate)" 
                alt="车牌" 
                class="plate-image"
              />
              <div v-else class="no-plate-image">无图</div>
            </td>
            <td>
              <div v-if="plate.plate_type === 'double'" v-html="formatPlateNumber(plate.plate_no, plate.plate_type)" class="plate-number"></div>
              <div v-else class="plate-number">{{ plate.plate_no }}</div>
            </td>
            <td>
              <div 
                class="plate-type-tag"
                :style="{ backgroundColor: getPlateTypeTag(plate.plate_type).color + '20', 
                          color: getPlateTypeTag(plate.plate_type).color }"
              >
                {{ getPlateTypeTag(plate.plate_type).label }}
              </div>
            </td>
            <td>{{ formatConfidence(plate.confidence) }}</td>
            <td>
              <button class="target-button" @click="setTargetPlate(plate)">
                设为目标
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- 无结果状态 -->
    <div v-else-if="hasImage" class="no-results">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="6" width="20" height="12" rx="2" />
        <path d="M2 10h20" />
      </svg>
      <h3>未识别到车牌</h3>
      <p>系统未能在上传的图片中识别到任何车牌，请尝试上传清晰的包含车牌的图片。</p>
    </div>
  </div>
</template>

<style scoped>
.recognition-results {
  width: 100%;
  padding: 1.5rem;
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.result-image-container {
  margin-bottom: 1.5rem;
  border-radius: 0.375rem;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.result-image {
  width: 100%;
  max-height: 300px;
  object-fit: contain;
  background-color: #f3f4f6;
}

.result-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 0.5rem;
}

.result-timestamp {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 1rem;
}

.result-table-container {
  overflow-x: auto;
}

.result-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.result-table th {
  padding: 0.75rem 1rem;
  background-color: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.875rem;
  font-weight: 600;
  color: #4b5563;
}

.result-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.875rem;
  color: #1f2937;
}

.plate-image-cell {
  width: 100px;
}

.plate-image {
  height: 40px;
  object-fit: contain;
  background-color: #f3f4f6;
  border-radius: 0.25rem;
}

.no-plate-image {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f3f4f6;
  color: #9ca3af;
  font-size: 0.75rem;
  border-radius: 0.25rem;
}

.plate-number {
  font-weight: 500;
}

.double-plate {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.double-plate-upper,
.double-plate-lower {
  padding: 0.125rem 0.25rem;
  background-color: #f3f4f6;
  border-radius: 0.25rem;
  text-align: center;
}

.plate-type-tag {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.target-button {
  padding: 0.375rem 0.75rem;
  background-color: #4f46e5;
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.target-button:hover {
  background-color: #4338ca;
}

.no-results {
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #6b7280;
}

.no-results h3 {
  margin: 1rem 0 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
}

.no-results p {
  max-width: 24rem;
  font-size: 0.875rem;
  line-height: 1.5;
}
</style>
