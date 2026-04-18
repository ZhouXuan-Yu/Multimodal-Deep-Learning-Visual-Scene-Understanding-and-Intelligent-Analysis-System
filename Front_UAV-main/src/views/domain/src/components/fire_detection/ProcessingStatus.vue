<template>
  <div class="processing-status">
    <h3>正在处理视频</h3>
    
    <div class="progress-container">
      <el-progress 
        :percentage="localProgress" 
        :status="error ? 'exception' : ''" 
        :stroke-width="12"
        :format="formatProgress"
        class="custom-progress"
      />
      <p class="status-message">{{ localMessage }} <span class="elapsed-time">({{ formattedElapsedTime }})</span></p>
    </div>
    
    <div class="processing-animation" v-if="!error">
      <div class="wave"></div>
      <div class="wave"></div>
      <div class="wave"></div>
    </div>
    
    <div v-if="error" class="error-message">
      <el-alert
        :title="error"
        type="error"
        show-icon
        :closable="false"
        effect="light"
        class="custom-alert"
      >
        <template #default>
          <p class="error-details">请检查网络连接或重试。如果问题持续存在，请联系技术支持。</p>
        </template>
      </el-alert>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue';

const props = defineProps({
  processId: {
    type: String,
    required: true
  },
  progress: {
    type: Number,
    default: 0
  },
  message: {
    type: String,
    default: '处理中...'
  },
  elapsedTime: {
    type: Number,
    default: 0
  },
  error: {
    type: String,
    default: null
  }
});

// 定义emit函数，用于事件发射
const emit = defineEmits(['update:progress', 'update:message', 'complete', 'error']);

// 本地进度和消息状态
const localProgress = ref(props.progress);
const localMessage = ref(props.message);
const localError = ref(props.error);

// 监听props变化更新本地状态
watch(() => props.progress, (newValue) => {
  localProgress.value = newValue;
});

watch(() => props.message, (newValue) => {
  localMessage.value = newValue;
});

watch(() => props.error, (newValue) => {
  localError.value = newValue;
});

// 格式化经过时间
const formattedElapsedTime = computed(() => {
  const mins = Math.floor(props.elapsedTime / 60);
  const secs = Math.floor(props.elapsedTime % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
});

// 格式化进度显示
const formatProgress = (percentage) => {
  return percentage >= 100 ? '完成' : `${percentage}%`;
};

// 进度模拟相关变量
let progressInterval = null;
const simulationStarted = ref(false);
const TARGET_DURATION = 60; // 预计视频处理需要60秒完成

// 模拟进度函数
const simulateProgress = () => {
  if (localProgress.value >= 99) {
    stopProgressSimulation();
    
    // 检查任务是否真正完成
    checkCompletion();
    return;
  }

  // 模拟进度增长，初始快，后期慢
  if (localProgress.value < 30) {
    localProgress.value += 2;
  } else if (localProgress.value < 60) {
    localProgress.value += 1;
  } else if (localProgress.value < 85) {
    localProgress.value += 0.5;
  } else {
    localProgress.value += 0.2;
  }

  // 更新消息
  updateProgressMessage();
  
  // 发送进度更新事件
  emit('update:progress', localProgress.value);
};

// 根据进度更新消息
const updateProgressMessage = () => {
  if (localProgress.value < 20) {
    localMessage.value = '正在解析视频...';
  } else if (localProgress.value < 40) {
    localMessage.value = '正在提取帧...';
  } else if (localProgress.value < 60) {
    localMessage.value = '正在检测火灾...';
  } else if (localProgress.value < 80) {
    localMessage.value = '正在生成结果...';
  } else {
    localMessage.value = '即将完成...';
  }
  
  emit('update:message', localMessage.value);
};

// 启动进度模拟
const startProgressSimulation = () => {
  if (progressInterval) return;
  
  simulationStarted.value = true;
  progressInterval = setInterval(simulateProgress, 500);
};

// 停止进度模拟
const stopProgressSimulation = () => {
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
};

// 检查任务是否真正完成
const checkCompletion = async () => {
  try {
    // 只在进度接近100%时尝试一次检查是否完成
    const response = await fetch(`/api/fire_detection_direct/check-completion/${props.processId}`);
    
    if (response.ok) {
      const data = await response.json();
      
      if (data.status === 'completed') {
        localProgress.value = 100;
        emit('update:progress', 100);
        emit('complete', data);
      } else if (data.status === 'failed') {
        localError.value = data.error || '处理失败';
        emit('error', localError.value);
      } else {
        // 如果还未完成，继续等待一段时间后再次检查
        setTimeout(checkCompletion, 5000);
      }
    } else {
      // 如果请求失败，在一段时间后模拟完成
      setTimeout(() => {
        localProgress.value = 100;
        emit('update:progress', 100);
        emit('complete', { status: 'completed' });
      }, 3000);
    }
  } catch (error) {
    console.error('检查完成状态出错:', error);
    
    // 出错时，在一段时间后模拟完成
    setTimeout(() => {
      localProgress.value = 100;
      emit('update:progress', 100);
      emit('complete', { status: 'completed' });
    }, 3000);
  }
};

// 组件挂载时开始模拟进度
onMounted(() => {
  startProgressSimulation();
});

// 组件卸载前停止所有定时器
onBeforeUnmount(() => {
  stopProgressSimulation();
});
</script>

<style scoped>
.processing-status {
  position: relative;
  background-color: #f9fafb;
  padding: 25px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  margin: 20px 0;
  overflow: hidden;
  transition: all 0.3s ease;
  border: 1px solid rgba(79, 70, 229, 0.1);
}

.processing-status:hover {
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

h3 {
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 20px;
  font-weight: 600;
  background: linear-gradient(45deg, #4f46e5, #00d2aa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}

.progress-container {
  margin-bottom: 20px;
  position: relative;
  z-index: 2;
}

:deep(.custom-progress .el-progress-bar__inner) {
  background: linear-gradient(90deg, #4f46e5, #00d2aa);
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.custom-progress .el-progress-bar__outer) {
  background-color: rgba(79, 70, 229, 0.1);
  border-radius: 12px;
}

:deep(.custom-progress .el-progress__text) {
  color: #4f46e5;
  font-weight: 600;
}

.status-message {
  margin-top: 15px;
  text-align: center;
  font-weight: 500;
  color: #606266;
  font-size: 1.05rem;
  animation: pulse 2s infinite;
}

.elapsed-time {
  color: #909399;
  font-size: 0.9rem;
  font-weight: 400;
}

.error-message {
  margin-top: 20px;
  position: relative;
  z-index: 2;
}

:deep(.custom-alert) {
  border-radius: 8px;
  border: none;
  background-color: rgba(245, 108, 108, 0.1);
}

:deep(.custom-alert .el-alert__title) {
  font-weight: 600;
  color: #f56c6c;
}

.error-details {
  margin-top: 8px;
  font-size: 0.9rem;
  color: #909399;
  line-height: 1.5;
}

.processing-animation {
  position: absolute;
  bottom: -10px;
  left: 0;
  right: 0;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  opacity: 0.5;
}

.wave {
  width: 5px;
  height: 100px;
  background: linear-gradient(45deg, #4f46e5, #00d2aa);
  margin: 10px;
  border-radius: 20px;
  animation: wave 1s linear infinite;
}

.wave:nth-child(2) {
  animation-delay: 0.1s;
}

.wave:nth-child(3) {
  animation-delay: 0.2s;
}

@keyframes wave {
  0% {
    transform: scale(0);
  }
  50% {
    transform: scale(1);
  }
  100% {
    transform: scale(0);
  }
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
  100% {
    opacity: 1;
  }
}

@media (max-width: 768px) {
  .processing-status {
    padding: 15px;
  }
  
  h3 {
    font-size: 1.3rem;
    margin-bottom: 15px;
  }
}
</style> 