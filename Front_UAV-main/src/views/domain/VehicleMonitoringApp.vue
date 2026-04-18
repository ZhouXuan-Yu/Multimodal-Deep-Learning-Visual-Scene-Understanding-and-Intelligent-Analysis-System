<script setup lang="ts">
import BasePage from './templates/BasePage.vue';
import { defineAsyncComponent, ref, onErrorCaptured } from 'vue';
import { ElLoading, ElMessage } from 'element-plus';

// 页面标题
const title = '车辆监控与报警';

// 加载状态
const isLoading = ref(false);
const loadError = ref(null);

// 错误处理
onErrorCaptured((err) => {
  loadError.value = err;
  ElMessage.error('组件加载失败，请刷新页面重试');
  return false;
});

// 加载中组件
const LoadingComponent = {
  template: `
    <div class="component-loading">
      <div class="loading-spinner"></div>
      <p>正在加载车牌识别系统...</p>
    </div>
  `
};

// 错误组件
const ErrorComponent = {
  template: `
    <div class="component-error">
      <el-icon><WarningFilled /></el-icon>
      <h3>加载失败</h3>
      <p>无法加载车牌识别系统，请刷新页面重试</p>
      <el-button type="primary" @click="reload">重新加载</el-button>
    </div>
  `,
  methods: {
    reload() {
      window.location.reload();
    }
  }
};

// 使用动态组件加载PlateRecognitionView
const PlateRecognitionView = defineAsyncComponent({
  loader: () => import('./src/views/PlateRecognitionView.vue'),
  loadingComponent: LoadingComponent,
  errorComponent: ErrorComponent,
  delay: 200,
  timeout: 10000
});

// 重新加载方法
const reloadPage = () => {
  window.location.reload();
};
</script>

<template>
  <BasePage :title="title">
    <div class="vehicle-monitoring-wrapper">
      <transition name="fade" mode="out-in">
        <PlateRecognitionView v-if="!loadError" />
        <div v-else class="error-container">
          <el-result
            icon="error"
            title="加载失败"
            sub-title="无法加载车牌识别系统，请刷新页面重试"
          >
            <template #extra>
              <el-button type="primary" @click="reloadPage">重新加载</el-button>
            </template>
          </el-result>
        </div>
      </transition>
    </div>
  </BasePage>
</template>

<style scoped>
.vehicle-monitoring-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.component-loading, .component-error {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 300px;
  width: 100%;
  text-align: center;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-left-color: #ff6600;
  margin-bottom: 16px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.component-error {
  color: #f56c6c;
}

.component-error h3 {
  margin: 16px 0;
  font-size: 20px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

:deep(.plate-recognition-view) {
  width: 100%;
  height: 100%;
}

/* 优化移动端适配 */
@media (max-width: 768px) {
  .vehicle-monitoring-wrapper {
    padding: 10px;
  }
}
</style>