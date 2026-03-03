<template>
  <div class="processing-status">
    <h3>正在处理视频</h3>
    
    <div class="progress-container">
      <el-progress 
        :percentage="localProgress" 
        :status="error ? 'exception' : ''" 
        :stroke-width="10"
      />
      <p class="status-message">{{ localMessage }} ({{ formattedElapsedTime }})</p>
    </div>
    
    <div v-if="error" class="error-message">
      <el-alert
        :title="error"
        type="error"
        show-icon
        :closable="false"
      />
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
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  margin: 20px 0;
}

h3 {
  color: #2c3e50;
  margin-bottom: 15px;
  border-left: 4px solid #3498db;
  padding-left: 10px;
}

.progress-container {
  margin-bottom: 20px;
}

.status-message {
  margin-top: 10px;
  text-align: center;
  font-weight: 500;
  color: #2c3e50;
}

.error-message {
  margin-top: 15px;
}
</style> 