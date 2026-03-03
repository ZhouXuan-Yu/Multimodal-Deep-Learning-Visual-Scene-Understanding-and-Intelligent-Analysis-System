<template>
  <BaseFunctionPage
    title="智行追踪"
    subtitle="视频目标追踪系统"
    description="基于先进目标追踪算法的智能视频分析平台，实现多目标实时追踪与行为分析，打造安全高效的监控体系。"
    :features="features"
    action-text="开始使用"
    action-path="/domain/video-tracking/app"
    bg-image="/images/video-tracking-bg.jpg"
  />
</template>

<script setup>
import BaseFunctionPage from './BaseFunctionPage.vue';

const features = [
  {
    title: '实时目标追踪',
    description: '支持多种目标类型的实时追踪，包括人员、车辆、动物等，准确率高达95%以上',
    icon: 'tracking'
  },
  {
    title: '轨迹可视化',
    description: '自动生成目标运动轨迹可视化图表，支持历史轨迹回放与分析',
    icon: 'trajectory'
  },
  {
    title: '异常行为识别',
    description: '自动识别异常行为模式，及时发出预警，提供安全保障',
    icon: 'warning'
  },
  {
    title: '多目标同时跟踪',
    description: '支持同时追踪多个目标，并保持各自的身份标识',
    icon: 'multi-target'
  }
];
</script>

<style scoped>
/* 组件特定样式 */
</style> 