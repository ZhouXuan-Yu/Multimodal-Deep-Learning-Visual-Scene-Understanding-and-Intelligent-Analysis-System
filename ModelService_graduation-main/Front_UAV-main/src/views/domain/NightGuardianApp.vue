<script setup lang="ts">
import BasePage from './templates/BasePage.vue';
import NightGuardianView from './src/views/NightGuardianView.vue';

const title = '夜间守护者';

// 导入路由追踪工具以支持更好的API调试
import { setupRouteTracker } from './src/utils/route-tracker';

// 设置路由追踪器
setupRouteTracker();
</script>

<template>
  <BasePage :title="title">
    <div class="night-guardian-wrapper">
      <!-- 直接使用从项目2复制过来的组件 -->
      <NightGuardianView />
    </div>
  </BasePage>
</template>

<style scoped>
.night-guardian-wrapper {
  width: 100%;
  height: 100%;
  /* 确保从项目2复制过来的组件能正常显示 */
  display: flex;
  flex-direction: column;
}

/* 解决可能的样式冲突问题 */
:deep(.night-guardian-container) {
  width: 100%;
  height: 100%;
  padding: 0;
}

/* 优化移动端适配 */
@media (max-width: 768px) {
  .night-guardian-wrapper {
    padding: 0;
  }
}
</style>