<template>
  <div class="page-header">
    <div class="header-content">
      <div class="title-section">
        <h1 class="title">{{ title }}</h1>
        <div v-if="subtitle" class="subtitle">{{ subtitle }}</div>
      </div>
      
      <div v-if="$slots.actions" class="actions-section">
        <slot name="actions"></slot>
      </div>
    </div>
    
    <el-divider />
  </div>
</template>

<script>
export default {
  name: 'PageHeader',
  props: {
    title: {
      type: String,
      required: true
    },
    subtitle: {
      type: String,
      default: ''
    }
  }
}
</script>

<style scoped>
.page-header {
  margin-bottom: 24px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.title {
  font-size: 28px;
  font-weight: 600;
  margin: 0;
  color: var(--el-text-color-primary);
}

.subtitle {
  margin-top: 8px;
  font-size: 16px;
  color: var(--el-text-color-secondary);
}

.actions-section {
  display: flex;
  gap: 12px;
}
</style>
