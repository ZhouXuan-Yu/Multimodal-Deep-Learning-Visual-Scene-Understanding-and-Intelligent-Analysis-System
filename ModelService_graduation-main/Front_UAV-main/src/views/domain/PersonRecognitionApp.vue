<script setup>
// 导入所需的组件和库
import { ref } from 'vue';
import BasePage from './templates/BasePage.vue';
import AnalysisAssistant from './components/PersonRecognition/AnalysisAssistant.vue';
import AnalysisResults from './components/PersonRecognition/AnalysisResults.vue';
import ImageUploader from './components/PersonRecognition/ImageUploader.vue';
import personRecognitionService from './services/personRecognitionService';

// 页面标题
const title = '智眸千析';

// 状态管理
const analysisResult = ref(null);
const activePersonId = ref(null);
const highlightedPersonIndex = ref(null);
const isAnalyzing = ref(false);
const analysisProgress = ref(0);
const progressTimer = ref(null);
const notification = ref({ show: false, message: '', type: 'info' });
// 当后端未返回 image_url 时，我们会用 URL.createObjectURL 生成本地预览；需要在重置/切换时释放
const localObjectUrl = ref(null);

// 处理文件分析
const handleAnalyze = async (data) => {
  if (isAnalyzing.value) return;
  
  isAnalyzing.value = true;
  analysisProgress.value = 0;
  startProgressAnimation();
  
  try {
    // 尝试调用后端API
    const formData = new FormData();
    formData.append('file', data.file);
    formData.append('mode', data.mode || 'normal');
    
    console.log('发起分析请求，使用实际后端API数据', {
      mode: data.mode,
      fileName: data.file.name,
      fileSize: data.file.size,
      fileType: data.file.type
    });
    
    const response = await personRecognitionService.analyzeImage(formData, data.mode);
    console.log('原始响应数据:', response);
    
    // 处理嵌套响应结构 - 检查并提取data字段
    let result;
    if (response.success && response.data) {
      // 响应格式为 {success: true, data: {...}} 的情况
      result = response.data;
      console.log('从嵌套响应中提取数据:', result);
    } else {
      // 响应格式为直接数据的情况
      result = response;
    }
    
    // 确保图片URL添加到结果中
    if (result && !result.image_url) {
      // 释放上一次生成的 objectURL，避免内存泄漏
      if (localObjectUrl.value) {
        URL.revokeObjectURL(localObjectUrl.value);
        localObjectUrl.value = null;
      }
      localObjectUrl.value = URL.createObjectURL(data.file);
      result.image_url = localObjectUrl.value;
    }
    
    // 确保检测到的人物数据格式正确
    if (result && result.persons && result.persons.length > 0) {
      // 确保每个人物对象包含必要字段
      result.persons = result.persons.map((person, index) => {
        // bbox 在后端统一为 xyxy（像素坐标）。这里不再猜测/转换为 xywh，避免误判导致画框错乱。
        
        // 确保所有必要字段都有默认值
        return {
          gender: person.gender || 'unknown',
          gender_confidence: person.gender_confidence || 0.5,
          age: person.age || 0,
          age_confidence: person.age_confidence || 0.5,
          upper_color: person.upper_color || 'unknown',
          upper_color_confidence: person.upper_color_confidence || 0.5,
          lower_color: person.lower_color || 'unknown',
          lower_color_confidence: person.lower_color_confidence || 0.5,
          confidence: person.confidence || 0.5,
          bbox: person.bbox || [0, 0, 100, 100],
          ...person
        };
      });
    }
    
    // 确保结果包含必要的字段
    result = {
      detected: result.detected || (result.persons ? result.persons.length : 0),
      persons: result.persons || [],
      success: true,
      processing_time: result.processing_time || 0,
      mode: result.mode || data.mode,
      image_url: result.image_url,
      ...result
    };
    
    console.log('处理后的分析结果:', result);
    analysisResult.value = result;
    showNotification(`分析完成，检测到 ${result.persons?.length || 0} 个人物`, 'success');
  } catch (error) {
    console.error('分析失败:', error);
    showNotification('分析失败: ' + error.message, 'error');
    
    // 错误处理不再自动使用模拟数据
    throw error;
  } finally {
    isAnalyzing.value = false;
    stopProgressAnimation();
    analysisProgress.value = 100;
  }
};

// 处理重置分析
const handleResetAnalysis = () => {
  analysisResult.value = null;
  activePersonId.value = null;
  highlightedPersonIndex.value = null;
  if (localObjectUrl.value) {
    URL.revokeObjectURL(localObjectUrl.value);
    localObjectUrl.value = null;
  }
};

// 处理选择人物
const handleSelectPerson = (personId) => {
  activePersonId.value = personId;
};

// 助手/列表触发的高亮
const highlightPerson = (index) => {
  highlightedPersonIndex.value = index;
  activePersonId.value = index;
};

// 处理导出完成
const handleExportComplete = (data) => {
  showNotification(data.message, data.success ? 'success' : 'error');
};

// 处理错误
const handleError = (message) => {
  showNotification(message, 'error');
};

// 显示通知
const showNotification = (message, type = 'info') => {
  notification.value = {
    show: true,
    message,
    type
  };
  
  // 3秒后自动关闭
  setTimeout(() => {
    notification.value.show = false;
  }, 3000);
};

const closeNotification = () => {
  notification.value.show = false;
};

// 开始进度动画
const startProgressAnimation = () => {
  if (progressTimer.value) clearInterval(progressTimer.value);
  
  progressTimer.value = setInterval(() => {
    if (analysisProgress.value < 95) {
      const increment = analysisProgress.value < 50 ? 5 : 
                      analysisProgress.value < 75 ? 2 : 
                      analysisProgress.value < 90 ? 1 : 0.5;
      
      analysisProgress.value = Math.min(95, analysisProgress.value + increment);
    } else {
      clearInterval(progressTimer.value);
    }
  }, 300);
};

// 停止进度动画
const stopProgressAnimation = () => {
  if (progressTimer.value) {
    clearInterval(progressTimer.value);
    progressTimer.value = null;
  }
};

// 生成模拟分析结果
const generateMockAnalysisResult = (file, mode) => {
  // 模拟2-5个人物
  const personCount = Math.floor(Math.random() * 4) + 2;
  
  // 创建模拟人物数据
  const persons = [];
  for (let i = 0; i < personCount; i++) {
    const isEnhanced = mode === 'enhanced';
    
    // 随机生成人物特征
    const gender = Math.random() > 0.5 ? 'male' : 'female';
    const age = Math.floor(Math.random() * 60) + 15; // 15-75岁
    
    // 随机生成衣服颜色
    const colors = ['red', 'blue', 'green', 'black', 'white', 'yellow', 'gray'];
    const upperColor = colors[Math.floor(Math.random() * colors.length)];
    const lowerColor = colors[Math.floor(Math.random() * colors.length)];
    
    // 生成随机边界框 - [x1, y1, x2, y2]格式
    const boxWidth = Math.floor(Math.random() * 200) + 100;
    const boxHeight = Math.floor(Math.random() * 300) + 200;
    const x1 = Math.floor(Math.random() * 500);
    const y1 = Math.floor(Math.random() * 300);
    const x2 = x1 + boxWidth;
    const y2 = y1 + boxHeight;
    
    persons.push({
      gender,
      gender_confidence: isEnhanced ? 0.95 : 0.85,
      age,
      age_confidence: isEnhanced ? 0.92 : 0.82,
      upper_color: upperColor,
      upper_color_confidence: isEnhanced ? 0.9 : 0.8,
      lower_color: lowerColor,
      lower_color_confidence: isEnhanced ? 0.88 : 0.78,
      confidence: isEnhanced ? 0.95 : 0.85,
      bbox: [x1, y1, x2, y2] // 使用[x1,y1,x2,y2]格式与API返回一致
    });
  }
  
  // 生成图片URL
  const imageUrl = URL.createObjectURL(file);
  
  // 返回模拟结果 - 结构与API返回一致
  return {
    detected: persons.length,
    persons,
    success: true,
    processing_time: 1.5,
    mode,
    image_url: imageUrl,
    result_image_url: imageUrl,
    timestamp: new Date().toISOString()
  };
};
</script>

<template>
  <BasePage :title="title">
    <div class="person-recognition">
      <div v-if="!analysisResult" class="app-intro">
        <h2 class="intro-title">智眸千析 - 人物特征分析</h2>
        <p class="intro-text">基于深度学习技术的人物特征识别与分析系统，能够自动从图像中识别和提取人物的多维特征信息。系统支持性别、年龄、服装颜色等多项特征的精确识别，并通过自然语言交互界面提供查询结果。</p>
      </div>
      
      <div class="person-recognition-container">
        <div class="main-content">
          <div class="analysis-section">
            <image-uploader 
              @analyze="handleAnalyze" 
              @error="handleError"
              @remove-image="handleResetAnalysis"
              :isProcessing="isAnalyzing"
              :analysisProgress="analysisProgress"
              :hidePreview="!!analysisResult"
            />
            
            <analysis-results 
              v-if="analysisResult" 
              :analysis-result="analysisResult" 
              :highlighted-person-index="highlightedPersonIndex"
              @reset="handleResetAnalysis"
              @export-complete="handleExportComplete"
              @select-person="handleSelectPerson"
            />
          </div>
          
          <div class="assistant-section">
            <analysis-assistant 
              :analysis-result="analysisResult"
              @highlight-person="highlightPerson"
            />
          </div>
        </div>
        
        <!-- 通知消息 -->
        <div v-if="notification.show" 
             :class="['notification', `notification-${notification.type}`]">
          <span class="notification-content">{{ notification.message }}</span>
          <span class="close-btn" @click="closeNotification">&times;</span>
        </div>
      </div>
    </div>
  </BasePage>
</template>

<style scoped>
.person-recognition {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.person-recognition-container {
  width: 100%;
  height: calc(100vh - 160px);
  min-height: 680px;
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  background: linear-gradient(135deg, rgba(25, 30, 35, 0.95), rgba(15, 20, 25, 0.95));
}

.main-content {
  display: flex;
  height: 100%;
}

.analysis-section {
  flex-grow: 1;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-width: 0; /* 确保内容可以正常缩小 */
  overflow: auto;
}

.assistant-section {
  width: 450px;
  min-width: 350px;
  max-width: 500px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-left: 1px solid rgba(0, 255, 157, 0.1);
  height: 100%;
}

.app-intro {
  background: linear-gradient(90deg, rgba(30, 35, 40, 0.7), rgba(25, 30, 35, 0.7));
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
  border-left: 4px solid #00ff9d;
}

.intro-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 0.75rem;
  text-shadow: 0 0 10px rgba(0, 255, 157, 0.3);
}

.intro-text {
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
}

/* 通知样式 */
.notification {
  position: absolute;
  top: 1rem;
  right: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 16rem;
  max-width: 24rem;
  animation: slide-in 0.3s ease-out;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  z-index: 100;
}

.notification-success {
  background: linear-gradient(45deg, rgba(16, 185, 129, 0.8), rgba(5, 150, 105, 0.8));
  color: white;
  border-left: 4px solid #10b981;
}

.notification-error {
  background: linear-gradient(45deg, rgba(239, 68, 68, 0.8), rgba(220, 38, 38, 0.8));
  color: white;
  border-left: 4px solid #ef4444;
}

.notification-info {
  background: linear-gradient(45deg, rgba(59, 130, 246, 0.8), rgba(37, 99, 235, 0.8));
  color: white;
  border-left: 4px solid #3b82f6;
}

.notification-content {
  flex-grow: 1;
}

.close-btn {
  font-weight: bold;
  cursor: pointer;
  margin-left: 1rem;
  opacity: 0.8;
  transition: all 0.2s ease;
}

.close-btn:hover {
  opacity: 1;
  transform: scale(1.1);
}

@keyframes slide-in {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* 响应式调整 */
@media (max-width: 1280px) {
  .main-content {
    flex-direction: column;
  }
  
  .analysis-section {
    height: 60%;
    overflow-y: auto;
  }
  
  .assistant-section {
    width: 100%;
    min-width: 100%;
    height: 40%;
    border-left: none;
    border-top: 1px solid rgba(0, 255, 157, 0.1);
  }
}
</style>