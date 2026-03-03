<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import BasePage from './templates/BasePage.vue';
import FireDetectionView from './src/views/FireDetectionView.vue';
import { ElMessage } from 'element-plus';
import { getApiUrl } from './src/port_config';

// 页面标题
const title = '灾害检测';

// 组件加载状态
const componentLoaded = ref(false);
const componentError = ref(null);

// 确保Element Plus图标和组件正确加载
onMounted(() => {
  try {
    // 初始化检查
    console.log('灾害检测应用已加载，验证组件:', FireDetectionView);
    componentLoaded.value = true;
    
    // 检查API连接
    testApiConnection();
  } catch (error) {
    console.error('加载灾害检测组件失败:', error);
    componentError.value = error.message;
    ElMessage.error(`组件加载失败: ${error.message}`);
  }
});

// 测试API连接
async function testApiConnection() {
  try {
    const testUrl = getApiUrl('fire_detection_direct/health');
    console.log(`测试API连接: ${testUrl}`);
    
    const response = await fetch(testUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });
    
    if (response.ok) {
      console.log('API连接正常');
    } else {
      console.warn(`API连接测试返回: ${response.status} ${response.statusText}`);
    }
  } catch (error) {
    console.error('API连接测试失败:', error);
  }
}

// 处理来自FireDetectionView的错误
const handleError = (error) => {
  console.error('火灾检测错误:', error);
  ElMessage.error(`处理错误: ${error}`);
};
</script>

<template>
  <BasePage :title="title">
    <div class="disaster-detection-container">
      
      <!-- 显示组件加载错误 -->
      <div v-if="componentError" class="error-container">
        <el-alert
          title="组件加载失败"
          type="error"
          description="无法加载火灾检测组件，请检查控制台日志"
          show-icon
          :closable="false"
        >
          <div class="error-details">{{ componentError }}</div>
        </el-alert>
        <el-button type="primary" @click="window.location.reload()">
          重新加载页面
        </el-button>
      </div>
      
      <!-- 直接嵌入FireDetectionView组件 -->
      <div v-else class="view-container">
        <FireDetectionView 
          @error="handleError"
          :get-api-url="getApiUrl"
        />
      </div>
    </div>
  </BasePage>
</template>

<style scoped>
.disaster-detection-container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;
}

.page-header h1 {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 10px;
}

.page-header p {
  font-size: 1.2rem;
  color: #7f8c8d;
}

.view-container {
  background-color: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.error-container {
  background-color: #fff3f3;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 20px;
  align-items: center;
  text-align: center;
}

.error-details {
  margin-top: 10px;
  padding: 10px;
  background-color: #f8f8f8;
  border-radius: 4px;
  font-family: monospace;
  white-space: pre-wrap;
  text-align: left;
}
</style>