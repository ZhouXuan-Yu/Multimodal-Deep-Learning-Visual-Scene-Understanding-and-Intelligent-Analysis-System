<template>
  <div class="guide-system">
    <!-- 引导步骤 -->
    <div class="guide-modal" v-if="showGuide">
      <div class="guide-content">
        <h2>欢迎使用路径规划功能</h2>
        <p>本功能可以帮助您规划从一个地点到另一个地点的路线。</p>
        
        <div class="guide-steps">
          <div 
            v-for="(step, index) in guideSteps" 
            :key="index"
            :class="['guide-step', { 'active': currentStep === index }]"
            @click="setCurrentStep(index)"
          >
            <div class="step-number">{{ index + 1 }}</div>
            <div class="step-text">{{ step.title }}</div>
          </div>
        </div>
        
        <div class="step-content">
          <h3>{{ guideSteps[currentStep].title }}</h3>
          <p>{{ guideSteps[currentStep].description }}</p>
          
          <!-- 快速操作按钮 -->
          <div v-if="currentStep === 1" class="quick-actions">
            <div 
              v-for="(action, actionIndex) in quickActions" 
              :key="actionIndex"
              class="quick-action"
              @click="emitQuickAction(action)"
            >
              <div class="action-title">{{ action.title }}</div>
              <div class="action-description">{{ action.description }}</div>
            </div>
          </div>
          
          <!-- 建议列表 -->
          <div v-if="currentStep === 2" class="suggestions">
            <div 
              v-for="(suggestion, index) in suggestions" 
              :key="index"
              class="suggestion-item"
              @click="emitApplySuggestion(suggestion)"
            >
              <el-icon><Location /></el-icon>
              <span>{{ suggestion.text }}</span>
            </div>
          </div>
        </div>
        
        <div class="guide-footer">
          <el-button 
            v-if="currentStep > 0" 
            @click="prevStep"
          >
            上一步
          </el-button>
          <el-button 
            v-if="currentStep < guideSteps.length - 1" 
            type="primary" 
            @click="nextStep"
          >
            下一步
          </el-button>
          <el-button 
            v-else 
            type="success" 
            @click="completeGuide"
          >
            完成
          </el-button>
          <el-button 
            @click="skipGuide"
          >
            跳过
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Location } from '@element-plus/icons-vue'

// 引导状态
const showGuide = ref(false)
const currentStep = ref(0)

// 引导步骤
const guideSteps = [
  {
    title: '开始使用',
    description: '通过路径规划功能，您可以输入起点和终点，系统将为您规划最优路线。您也可以添加途经点，指定交通方式等。'
  },
  {
    title: '快速操作',
    description: '您可以使用以下快速操作来开始路线规划：'
  },
  {
    title: '常用目的地',
    description: '以下是一些常用的目的地建议：'
  }
]

// 快速操作
const quickActions = [
  {
    id: 'route-1',
    title: '规划简单路线',
    description: '从北京到上海的最快路线',
    prompt: '规划从{start}到{end}的最快路线'
  },
  {
    id: 'route-2',
    title: '多站点路线',
    description: '从北京到上海，途经{spots}',
    prompt: '规划从{start}到{end}，途经{spots}的路线'
  },
  {
    id: 'route-3',
    title: '经济路线',
    description: '从北京到上海的经济路线（低收费）',
    prompt: '规划从{start}到{end}的经济路线，尽量避免高速收费'
  }
]

// 建议列表
const suggestions = [
  { text: '北京西站到首都机场' },
  { text: '上海虹桥到外滩' },
  { text: '广州白云机场到珠江新城' },
  { text: '深圳宝安机场到世界之窗' }
]

// 发射事件
const emit = defineEmits(['quick-action', 'apply-suggestion'])

// 下一步
const nextStep = () => {
  if (currentStep.value < guideSteps.length - 1) {
    currentStep.value++
  }
}

// 上一步
const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

// 设置当前步骤
const setCurrentStep = (step) => {
  currentStep.value = step
}

// 完成引导
const completeGuide = () => {
  showGuide.value = false
  localStorage.setItem('route-guide-completed', 'true')
}

// 跳过引导
const skipGuide = () => {
  showGuide.value = false
  localStorage.setItem('route-guide-completed', 'true')
}

// 重置引导
const resetGuide = () => {
  localStorage.removeItem('route-guide-completed')
  currentStep.value = 0
  showGuide.value = true
}

// 快速操作事件
const emitQuickAction = (action) => {
  emit('quick-action', action)
  completeGuide()
}

// 应用建议事件
const emitApplySuggestion = (suggestion) => {
  emit('apply-suggestion', suggestion)
  completeGuide()
}

// 检查是否需要显示引导
onMounted(() => {
  const guideCompleted = localStorage.getItem('route-guide-completed')
  if (!guideCompleted) {
    showGuide.value = true
  }
})

// 暴露方法给父组件
defineExpose({
  resetGuide
})
</script>

<style scoped>
.guide-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.guide-content {
  width: 700px;
  max-width: 90%;
  background: var(--el-bg-color);
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
  padding: 30px;
}

.guide-steps {
  display: flex;
  justify-content: space-between;
  margin: 30px 0;
  position: relative;
}

.guide-steps::before {
  content: '';
  position: absolute;
  top: 20px;
  left: 40px;
  right: 40px;
  height: 2px;
  background: var(--el-border-color-light);
  z-index: 0;
}

.guide-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  z-index: 1;
  width: 120px;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--el-color-info-light-9);
  border: 2px solid var(--el-border-color);
  display: flex;
  justify-content: center;
  align-items: center;
  font-weight: bold;
  margin-bottom: 8px;
}

.guide-step.active .step-number {
  background: var(--el-color-primary);
  color: white;
  border-color: var(--el-color-primary);
}

.step-text {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  text-align: center;
}

.guide-step.active .step-text {
  color: var(--el-color-primary);
  font-weight: bold;
}

.step-content {
  min-height: 200px;
  margin-bottom: 20px;
}

.guide-footer {
  display: flex;
  justify-content: space-between;
  padding-top: 20px;
  border-top: 1px solid var(--el-border-color-light);
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 20px;
}

.quick-action {
  background: var(--el-color-primary-light-9);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.quick-action:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.action-title {
  font-weight: bold;
  margin-bottom: 8px;
  color: var(--el-color-primary);
}

.action-description {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.suggestions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 20px;
}

.suggestion-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: var(--el-color-info-light-9);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  gap: 8px;
}

.suggestion-item:hover {
  background: var(--el-color-primary-light-9);
}
</style> 