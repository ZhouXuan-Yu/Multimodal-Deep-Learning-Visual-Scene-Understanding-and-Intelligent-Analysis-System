<script setup>
import BasePage from './templates/BasePage.vue';
import KnowledgeBaseChat from './src/views/KnowledgeBaseChat.vue';

const title = '智慧知库';

// 导入路由追踪工具以支持更好的API调试
import { setupRouteTracker } from './src/utils/route-tracker';

// 设置路由追踪器
setupRouteTracker();
</script>

<template>
  <BasePage :title="title">
    <div class="knowledge-graph-container">
      <!-- 直接使用从项目2复制过来的组件 -->
      <KnowledgeBaseChat />
    </div>
  </BasePage>
</template>

<style scoped>
.knowledge-graph-container {
  width: 100%;
  height: calc(100vh - 60px); /* 减去顶部导航栏高度，确保不超出可视区域 */
  /* 确保从项目2复制过来的组件能正常显示 */
  display: flex;
  flex-direction: column;
  /* 解决被标题栏遮挡的问题 */
  padding-top: 60px;
  overflow: hidden;
  position: relative;
}

/* 解决可能的样式冲突问题 */
:deep(.knowledge-chat-container) {
  height: 100%; /* 使用容器的高度 */
  max-height: calc(100vh - 90px); /* 确保不会溢出视口 */
  background: linear-gradient(135deg, #0f1724 0%, #1a2234 50%, #22293d 100%); /* 更深邃的渐变背景 */
  border-radius: 12px; /* 圆角边框 */
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.25); /* 增强阴影效果 */
  margin: 0 auto;
  width: 98%; /* 稍微缩小宽度，留出边距 */
  border: 1px solid rgba(255, 255, 255, 0.08); /* 微妙的边框 */
  /* 确保内容可滚动 */
  overflow: hidden;
}

/* 确保聊天区域正确滚动 */
:deep(.chat-section) {
  max-height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

:deep(.chat-messages) {
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  /* 防止iOS橡皮筋效果导致的滚动问题 */
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}

/* 优化组件内部样式 */
:deep(.chat-header),
:deep(.graph-header) {
  background-color: rgba(12, 19, 34, 0.75); /* 更深色半透明背景 */
  backdrop-filter: blur(15px); /* 增强毛玻璃效果 */
  -webkit-backdrop-filter: blur(15px);
  border-radius: 10px 10px 0 0;
  padding: 16px 22px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); /* 添加微妙阴影 */
}

:deep(.chat-header h2),
:deep(.graph-header h2) {
  color: #e6f1ff; /* 更鲜明的标题颜色 */
  font-weight: 500;
  font-size: 1.25rem;
  letter-spacing: 0.5px;
}

:deep(.graph-container) {
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
  background-color: rgba(12, 19, 34, 0.45); /* 更深色背景 */
}

:deep(.message) {
  transition: transform 0.3s ease, opacity 0.3s ease;
  border-radius: 8px;
  overflow: hidden;
  background-color: rgba(28, 38, 59, 0.5); /* 消息框背景 */
  border-left: 3px solid rgba(77, 147, 255, 0.7); /* 左侧边框 */
}

:deep(.message:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2); /* 悬停阴影 */
}

:deep(.message.user-message) {
  background-color: rgba(32, 55, 88, 0.5); /* 用户消息背景 */
  border-left: 3px solid rgba(134, 207, 255, 0.8); /* 用户消息左侧边框 */
}

:deep(.message.bot-message) {
  background-color: rgba(28, 38, 59, 0.5); /* 机器人消息背景 */
  border-left: 3px solid rgba(77, 147, 255, 0.7); /* 机器人消息左侧边框 */
}

:deep(.el-button) {
  transition: all 0.3s ease;
  border-radius: 6px;
  font-weight: 500;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #3662a5 0%, #4285f4 100%); /* 蓝色渐变 */
  border: none;
  box-shadow: 0 4px 8px rgba(66, 133, 244, 0.2);
}

:deep(.el-button--success) {
  background: linear-gradient(135deg, #1e8e3e 0%, #34a853 100%); /* 绿色渐变 */
  border: none;
  box-shadow: 0 4px 8px rgba(52, 168, 83, 0.2);
}

:deep(.el-button--danger) {
  background: linear-gradient(135deg, #c53929 0%, #ea4335 100%); /* 红色渐变 */
  border: none;
  box-shadow: 0 4px 8px rgba(234, 67, 53, 0.2);
}

:deep(.el-button:hover) {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.25);
}

/* 优化移动端适配 */
@media (max-width: 768px) {
  .knowledge-graph-container {
    padding: 12px 0 0 0;
    height: calc(100vh - 50px); /* 移动端导航栏通常更小 */
  }
  
  :deep(.knowledge-chat-container) {
    height: calc(100vh - 70px);
    max-height: calc(100vh - 70px);
    width: 100%;
    border-radius: 8px;
    margin: 0;
  }
  
  :deep(.chat-messages) {
    padding: 10px;
  }
  
  :deep(.chat-header),
  :deep(.graph-header) {
    padding: 12px 16px;
  }
}
</style>