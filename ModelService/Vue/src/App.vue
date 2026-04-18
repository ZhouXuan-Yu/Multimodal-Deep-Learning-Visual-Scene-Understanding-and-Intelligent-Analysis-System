<template>
  <AppLayout>
    <router-view></router-view>
  </AppLayout>
</template>

<script setup>
import 'element-plus/dist/index.css'
import AppLayout from '@/components/layout/AppLayout.vue'
</script>

<style>
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  background: #000000;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  color: #ffffff;
}

/* Element Plus Dark Theme Overrides */
:root {
  --el-color-primary: #00ff9d;
  --el-color-success: #67c23a;
  --el-color-warning: #e6a23c;
  --el-color-danger: #f56c6c;
  --el-color-info: #909399;
  
  --el-border-color: rgba(255, 255, 255, 0.1);
  --el-border-color-light: rgba(255, 255, 255, 0.05);
  --el-border-color-lighter: rgba(255, 255, 255, 0.02);
  
  --el-text-color-primary: #ffffff;
  --el-text-color-regular: rgba(255, 255, 255, 0.8);
  --el-text-color-secondary: rgba(255, 255, 255, 0.6);
  --el-text-color-placeholder: rgba(255, 255, 255, 0.3);
  
  --el-bg-color: #1a1a1a;
  --el-bg-color-overlay: #242424;
  --el-fill-color-blank: transparent;
}

/* 全局覆盖样式，确保功能按钮和对话框显示在最上层 */
/* 导航按钮组 */
.header .header-actions,
.header .action-buttons,
.header .action-button {
  position: relative !important;
  z-index: 10000 !important; /* 这个值必须足够高 */
}

/* 弹出的功能界面 - 确保这些元素始终在页面最顶层 */
.el-dialog__wrapper,
.el-drawer__wrapper,
.el-message-box__wrapper,
.el-notification,
.el-message,
.el-popover,
.el-dropdown-menu,
.el-tooltip__popper {
  position: fixed !important;
  z-index: 9999999 !important; /* 非常高的值确保显示在所有元素上层 */
}

/* 同样设置遮罩层的高度 */
.el-overlay,
.el-message-box__overlay,
.el-dialog__overlay,
.el-drawer__overlay {
  position: fixed !important;
  z-index: 9999998 !important; /* 比功能界面少一点，但仍然很高 */
}

/* 确保对话框内容和样式正确 */
.el-dialog,
.el-drawer,
.el-message-box {
  background-color: var(--el-bg-color) !important;
  box-shadow: 0 0 30px rgba(0, 0, 0, 0.7) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

/* 弹出的容器内部元素也要高z-index */
.el-dialog__header,
.el-dialog__body,
.el-dialog__footer,
.el-drawer__header,
.el-drawer__body,
.el-notification__content,
.el-message__content {
  position: relative !important;
  z-index: 10000000 !important; /* 比容器本身还要高 */
}

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>