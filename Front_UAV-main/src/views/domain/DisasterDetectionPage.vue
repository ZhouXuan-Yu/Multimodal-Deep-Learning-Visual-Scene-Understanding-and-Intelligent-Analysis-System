<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import BaseFunctionPage from './BaseFunctionPage.vue';
import { ElMessage, ElButton } from 'element-plus';
import { checkApiConnection } from './services/api-proxy-check';

const router = useRouter();
const isChecking = ref(false);

const pageData = {
  title: '灾害预警',
  subtitle: '语义分割与异常模式监测，精准预警灾害风险。',
  description: '基于无人机航拍图像的森林火灾检测系统，实现对自然灾害的早期识别和监测。系统采用深度学习模型分析航拍图像，快速定位可能的灾害区域，为应急决策提供数据支持。',
  image: new URL('@/assets/function/fire.png', import.meta.url).href,
  features: [
    {
      title: '火灾语义分割',
      description: '应用U-Net网络架构对航拍图像进行像素级分割，精确标记火灾区域，评估火势范围和严重程度。',
      icon: 'https://ext.same-assets.com/794583279/2838098675.svg'
    },
    {
      title: '异常模式检测',
      description: '结合时序数据分析，识别火点扩散等异常模式，提前预警可能发生的灾害。',
      icon: 'https://ext.same-assets.com/794583279/2018733539.svg'
    },
    {
      title: '应急响应体系',
      description: '当识别到火灾会自动触发报警模块，实现实时灾害检测与报警。协助救援人员评估灾情并协调救援行动，提高应急响应效率。',
      icon: 'https://ext.same-assets.com/794583279/2067545548.svg'
    }
  ],
  actionRoute: '/domain/disaster-detection/app',
  actionText: '开始使用灾害预警'
};

// API连接检查
async function checkApi() {
  isChecking.value = true;
  try {
    await checkApiConnection();
  } catch (error) {
    ElMessage.error(`检查API连接失败: ${error.message}`);
  } finally {
    isChecking.value = false;
  }
}
</script>

<template>
  <BaseFunctionPage
    :title="pageData.title"
    :subtitle="pageData.subtitle"
    :description="pageData.description"
    :image="pageData.image"
    :features="pageData.features"
    :actionRoute="pageData.actionRoute"
    :actionText="pageData.actionText"
  >
    <!-- 添加API连接检查按钮 -->
    <template #extra>
      <div class="api-check-container">
        <el-button 
          type="info" 
          size="small" 
          @click="checkApi" 
          :loading="isChecking"
        >
          检查API连接
        </el-button>
        <div class="help-text">
          如遇连接问题，点击此按钮检查API可用性
        </div>
      </div>
    </template>
  </BaseFunctionPage>
</template>

<style scoped>
.api-check-container {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.help-text {
  font-size: 12px;
  color: #909399;
}
</style> 