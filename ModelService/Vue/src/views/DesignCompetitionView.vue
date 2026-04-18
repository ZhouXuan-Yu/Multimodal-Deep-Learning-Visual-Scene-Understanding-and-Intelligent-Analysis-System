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
                  <el-icon><Plus /></el-icon>
                  <div class="upload-text">点击或拖拽图片至此处</div>
                </div>
                <img v-else :src="plateImage" class="preview-image" />
              </el-upload>
              
              <div class="action-buttons">
                <el-button type="primary" @click="recognizePlate" :disabled="!plateImage || plateLoading">
                  {{ plateLoading ? '识别中...' : '开始识别' }}
                </el-button>
                <el-button @click="resetPlate" :disabled="plateLoading">重置</el-button>
              </div>
              
              <!-- 车牌识别结果 -->
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
              
              <!-- 错误信息 -->
              <div v-if="plateError" class="error-message">
                <el-alert
                  :title="plateError"
                  type="error"
                  :closable="false"
                  show-icon
                />
              </div>
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
                  <el-icon><Plus /></el-icon>
                  <div class="upload-text">点击或拖拽图片至此处</div>
                </div>
                <img v-else :src="carImage" class="preview-image" />
              </el-upload>
              
              <div class="action-buttons">
                <el-button type="primary" @click="recognizeCar" :disabled="!carImage || carLoading">
                  {{ carLoading ? '识别中...' : '开始识别' }}
                </el-button>
                <el-button @click="resetCar" :disabled="carLoading">重置</el-button>
              </div>
              
              <!-- 车辆识别结果 -->
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
              
              <!-- 错误信息 -->
              <div v-if="carError" class="error-message">
                <el-alert
                  :title="carError"
                  type="error"
                  :closable="false"
                  show-icon
                />
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
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
}

.title {
  font-size: 2rem;
  text-align: center;
  margin-bottom: 30px;
  color: var(--el-text-color-primary);
}

.main-tabs {
  max-width: 1000px;
  margin: 0 auto;
}

.recognition-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
}

.upload-area {
  width: 100%;
  background-color: var(--el-fill-color-lighter);
  border: 1px dashed var(--el-border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  padding: 20px;
  min-height: 300px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.upload-area:hover {
  border-color: var(--el-color-primary);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
}

.upload-text {
  margin-top: 10px;
  font-size: 16px;
}

.preview-image {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin: 20px 0;
}

.result-section {
  margin-top: 20px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 20px;
  background-color: var(--el-bg-color);
}

.result-details {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

.error-message {
  margin-top: 20px;
}
</style>
