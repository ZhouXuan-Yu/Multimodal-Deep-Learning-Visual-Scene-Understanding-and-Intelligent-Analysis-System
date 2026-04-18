<template>
  <div class="design-competition">
    <el-container>
      <el-main>
        <h1 class="title">车牌与车辆识别系统</h1>
        
        <!-- 功能选择卡片 -->
        <el-tabs v-model="activeTab" class="main-tabs">
          <el-tab-pane label="车牌识别" name="plate">
            <!-- 车牌识别区域 -->
            <div class="recognition-section">
              <el-upload
                class="upload-area"
                action="#"
                :auto-upload="false"
                :on-change="handlePlateImageChange"
                :show-file-list="false"
                accept="image/*"
              >
                <div v-if="!plateImage" class="upload-placeholder">
                  <el-icon class="upload-icon"><Plus /></el-icon>
                  <div class="upload-text">点击或拖拽图片至此处上传</div>
                  <div class="upload-hint">支持JPG、PNG等常见图片格式</div>
                </div>
                <img v-else :src="plateImage" class="preview-image" />
              </el-upload>
              
              <div class="action-buttons">
                <el-button type="primary" @click="recognizePlate" :disabled="!plateImage || plateLoading">
                  <el-icon v-if="plateLoading"><Loading /></el-icon>
                  {{ plateLoading ? '识别中...' : '开始识别' }}
                </el-button>
                <el-button @click="resetPlate" :disabled="plateLoading">重置</el-button>
              </div>
              
              <!-- 车牌识别结果 -->
              <transition name="fade">
                <div v-if="plateResult" class="result-section">
                  <el-result
                    icon="success"
                    title="车牌识别成功"
                    :sub-title="'识别结果: ' + plateResult.plate_number + ' (' + plateResult.color + ')'"
                  >
                    <template #extra>
                      <div class="result-details">
                        <el-descriptions :column="1" border>
                          <el-descriptions-item label="车牌号码">{{ plateResult.plate_number }}</el-descriptions-item>
                          <el-descriptions-item label="车牌颜色">{{ plateResult.color }}</el-descriptions-item>
                          <el-descriptions-item label="置信度">{{ (plateResult.confidence * 100).toFixed(2) + '%' }}</el-descriptions-item>
                        </el-descriptions>
                      </div>
                    </template>
                  </el-result>
                </div>
              </transition>
              
              <!-- 错误信息 -->
              <transition name="fade">
                <div v-if="plateError" class="error-message">
                  <el-alert
                    :title="plateError"
                    type="error"
                    :closable="false"
                    show-icon
                  />
                </div>
              </transition>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="车辆颜色识别" name="car">
            <!-- 车辆颜色识别区域 -->
            <div class="recognition-section">
              <el-upload
                class="upload-area"
                action="#"
                :auto-upload="false"
                :on-change="handleCarImageChange"
                :show-file-list="false"
                accept="image/*"
              >
                <div v-if="!carImage" class="upload-placeholder">
                  <el-icon class="upload-icon"><Plus /></el-icon>
                  <div class="upload-text">点击或拖拽图片至此处上传</div>
                  <div class="upload-hint">支持JPG、PNG等常见图片格式</div>
                </div>
                <img v-else :src="carImage" class="preview-image" />
              </el-upload>
              
              <div class="action-buttons">
                <el-button type="primary" @click="recognizeCar" :disabled="!carImage || carLoading">
                  <el-icon v-if="carLoading"><Loading /></el-icon>
                  {{ carLoading ? '识别中...' : '开始识别' }}
                </el-button>
                <el-button @click="resetCar" :disabled="carLoading">重置</el-button>
              </div>
              
              <!-- 车辆识别结果 -->
              <transition name="fade">
                <div v-if="carResult" class="result-section">
                  <el-result
                    icon="success"
                    title="车辆颜色识别成功"
                    :sub-title="'识别结果: ' + carResult.color"
                  >
                    <template #extra>
                      <div class="result-details">
                        <el-descriptions :column="1" border>
                          <el-descriptions-item label="车辆颜色">{{ carResult.color }}</el-descriptions-item>
                          <el-descriptions-item label="置信度">{{ (carResult.confidence * 100).toFixed(2) + '%' }}</el-descriptions-item>
                        </el-descriptions>
                      </div>
                    </template>
                  </el-result>
                </div>
              </transition>
              
              <!-- 错误信息 -->
              <transition name="fade">
                <div v-if="carError" class="error-message">
                  <el-alert
                    :title="carError"
                    type="error"
                    :closable="false"
                    show-icon
                  />
                </div>
              </transition>
            </div>
          </el-tab-pane>
        </el-tabs>

        <!-- 功能卡片区域 -->
        <div class="feature-cards">
          <div class="feature-card">
            <el-icon class="feature-icon"><Picture /></el-icon>
            <h3>高精度识别</h3>
            <p>采用深度学习算法，精准识别各类车牌和车辆颜色</p>
          </div>
          <div class="feature-card">
            <el-icon class="feature-icon"><VideoCamera /></el-icon>
            <h3>快速处理</h3>
            <p>优化的模型处理流程，确保识别结果快速返回</p>
          </div>
          <div class="feature-card">
            <el-icon class="feature-icon"><DataAnalysis /></el-icon>
            <h3>数据统计</h3>
            <p>提供识别结果详细分析，支持数据导出和报表生成</p>
          </div>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus, Picture, VideoCamera, DataAnalysis, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { designCompetitionApi } from '@/api/designCompetition'

// 当前活动标签页
const activeTab = ref('plate')

// 车牌识别相关状态
const plateImage = ref(null)
const plateFile = ref(null)
const plateLoading = ref(false)
const plateResult = ref(null)
const plateError = ref(null)

// 车辆识别相关状态
const carImage = ref(null)
const carFile = ref(null)
const carLoading = ref(false)
const carResult = ref(null)
const carError = ref(null)

// 车牌图片处理
const handlePlateImageChange = (file) => {
  plateFile.value = file.raw
  plateImage.value = URL.createObjectURL(file.raw)
  plateResult.value = null
  plateError.value = null
}

// 车辆图片处理
const handleCarImageChange = (file) => {
  carFile.value = file.raw
  carImage.value = URL.createObjectURL(file.raw)
  carResult.value = null
  carError.value = null
}

// 车牌识别
const recognizePlate = async () => {
  if (!plateFile.value) {
    ElMessage.warning('请先上传车牌图片')
    return
  }
  
  plateLoading.value = true
  plateError.value = null
  
  try {
    const formData = new FormData()
    formData.append('file', plateFile.value)
    
    const response = await designCompetitionApi.recognizePlate(formData)
    console.log('车牌识别响应:', response)
    
    if (response.data.success) {
      plateResult.value = response.data
      ElMessage.success('车牌识别成功!')
    } else {
      plateError.value = response.data.error || '车牌识别失败，请尝试其他图片'
      ElMessage.error(plateError.value)
    }
  } catch (error) {
    console.error('车牌识别请求出错:', error)
    plateError.value = error.response?.data?.detail || '车牌识别请求失败'
    ElMessage.error(plateError.value)
  } finally {
    plateLoading.value = false
  }
}

// 车辆颜色识别
const recognizeCar = async () => {
  if (!carFile.value) {
    ElMessage.warning('请先上传车辆图片')
    return
  }
  
  carLoading.value = true
  carError.value = null
  
  try {
    const formData = new FormData()
    formData.append('file', carFile.value)
    
    const response = await designCompetitionApi.recognizeCar(formData)
    console.log('车辆识别响应:', response)
    
    if (response.data.success) {
      carResult.value = response.data
      ElMessage.success('车辆颜色识别成功!')
    } else {
      carError.value = response.data.error || '车辆识别失败，请尝试其他图片'
      ElMessage.error(carError.value)
    }
  } catch (error) {
    console.error('车辆识别请求出错:', error)
    carError.value = error.response?.data?.detail || '车辆识别请求失败'
    ElMessage.error(carError.value)
  } finally {
    carLoading.value = false
  }
}

// 重置车牌识别
const resetPlate = () => {
  plateImage.value = null
  plateFile.value = null
  plateResult.value = null
  plateError.value = null
}

// 重置车辆识别
const resetCar = () => {
  carImage.value = null
  carFile.value = null
  carResult.value = null
  carError.value = null
}

// 组件挂载时
onMounted(() => {
  // 检查API可用性
  designCompetitionApi.healthCheck()
    .then(response => {
      console.log('设计比赛API健康状态:', response)
    })
    .catch(error => {
      console.error('API健康检查失败:', error)
    })
})
</script>

<style scoped>
.design-competition {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.title {
  font-size: 2.2rem;
  text-align: center;
  margin-bottom: 30px;
  background: linear-gradient(45deg, #ff6600, #ff9966);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 600;
  letter-spacing: 1px;
}

.main-tabs {
  max-width: 1000px;
  margin: 0 auto 30px;
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(255, 102, 0, 0.1);
}

:deep(.el-tabs__item) {
  font-size: 16px;
  padding: 0 24px;
  transition: all 0.3s ease;
}

:deep(.el-tabs__item.is-active) {
  color: #ff6600;
  font-weight: 600;
}

:deep(.el-tabs__active-bar) {
  background-color: #ff6600;
}

.recognition-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  animation: fadeIn 0.5s ease-out;
}

.upload-area {
  width: 100%;
  background-color: #f8f9fa;
  border: 2px dashed #e0e0e0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  padding: 20px;
  min-height: 300px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.upload-area:hover {
  border-color: #ff6600;
  background-color: rgba(255, 102, 0, 0.05);
  transform: translateY(-2px);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #777;
  width: 100%;
  height: 100%;
}

.upload-icon {
  font-size: 48px;
  color: #ff6600;
  margin-bottom: 16px;
}

.upload-text {
  margin-top: 10px;
  font-size: 18px;
  font-weight: 500;
  color: #444;
}

.upload-hint {
  margin-top: 8px;
  font-size: 14px;
  color: #999;
}

.preview-image {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  transition: transform 0.3s ease;
}

.preview-image:hover {
  transform: scale(1.02);
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin: 20px 0;
}

:deep(.el-button--primary) {
  background: linear-gradient(45deg, #ff6600, #ff9966);
  border: none;
  padding: 12px 24px;
  transition: all 0.3s;
}

:deep(.el-button--primary:hover) {
  transform: translateY(-2px);
  box-shadow: 0 8px 15px rgba(255, 102, 0, 0.2);
}

:deep(.el-button--default) {
  border-color: #ddd;
  color: #666;
  transition: all 0.3s;
}

:deep(.el-button--default:hover) {
  border-color: #ff6600;
  color: #ff6600;
}

.result-section {
  margin-top: 20px;
  border-radius: 12px;
  padding: 20px;
  background-color: white;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(255, 102, 0, 0.1);
}

.result-details {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

:deep(.el-descriptions) {
  margin-top: 20px;
}

:deep(.el-descriptions__label) {
  font-weight: 600;
  color: #666;
}

:deep(.el-descriptions__content) {
  color: #333;
}

.error-message {
  margin-top: 20px;
}

.feature-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 40px;
}

.feature-card {
  background: white;
  border-radius: 12px;
  padding: 30px;
  text-align: center;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(255, 102, 0, 0.1);
  transition: all 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-10px);
  box-shadow: 0 15px 35px rgba(255, 102, 0, 0.15);
}

.feature-icon {
  font-size: 40px;
  color: #ff6600;
  margin-bottom: 20px;
}

.feature-card h3 {
  font-size: 20px;
  margin-bottom: 12px;
  color: #333;
}

.feature-card p {
  color: #666;
  line-height: 1.6;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .title {
    font-size: 1.8rem;
  }
  
  .feature-cards {
    grid-template-columns: 1fr;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .action-buttons .el-button {
    width: 100%;
  }
}
</style>
