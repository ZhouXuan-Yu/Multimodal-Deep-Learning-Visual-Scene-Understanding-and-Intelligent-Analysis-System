<template>
  <div class="test-fusion-container">
    <h1>融合图像生成测试</h1>
    
    <div class="upload-section">
      <div class="upload-container">
        <h3>可见光图像</h3>
        <el-upload
          class="uploader"
          action=""
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleRGBImageChange"
        >
          <div class="upload-area" v-if="!rgbImageUrl">
            <el-icon class="upload-icon"><Plus /></el-icon>
            <div class="upload-text">上传可见光图像</div>
          </div>
          <img v-else :src="rgbImageUrl" class="uploaded-image" />
        </el-upload>
      </div>
      
      <div class="upload-container">
        <h3>热成像图像</h3>
        <el-upload
          class="uploader"
          action=""
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleThermalImageChange"
        >
          <div class="upload-area" v-if="!thermalImageUrl">
            <el-icon class="upload-icon"><Plus /></el-icon>
            <div class="upload-text">上传热成像图像</div>
          </div>
          <img v-else :src="thermalImageUrl" class="uploaded-image" />
        </el-upload>
      </div>
    </div>
    
    <div class="controls-container" v-if="rgbImageUrl && thermalImageUrl">
      <el-button type="danger" @click="clearImages">清除图片</el-button>
      <el-button type="primary" @click="testFusion" :loading="loading">
        {{ loading ? '处理中...' : '测试融合图像' }}
      </el-button>
    </div>
    
    <div class="result-section" v-if="fusionImageUrl">
      <h2>融合图像结果</h2>
      <div class="image-container">
        <el-image 
          :src="getFullUrl(fusionImageUrl)" 
          fit="contain" 
          class="result-image"
          @load="() => console.log('融合图像加载成功')"
          @error="handleImageError"
        />
        <div class="image-info">
          <p>相对路径: {{ fusionImageUrl }}</p>
          <p>完整URL: {{ getFullUrl(fusionImageUrl) }}</p>
        </div>
      </div>
    </div>
    
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      show-icon
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const rgbImageUrl = ref('')
const rgbImageFile = ref(null)
const thermalImageUrl = ref('')
const thermalImageFile = ref(null)
const fusionImageUrl = ref('')
const loading = ref(false)
const errorMessage = ref('')

// 处理可见光图片上传
const handleRGBImageChange = (file) => {
  rgbImageFile.value = file.raw
  rgbImageUrl.value = URL.createObjectURL(file.raw)
  fusionImageUrl.value = ''
}

// 处理热成像图片上传
const handleThermalImageChange = (file) => {
  thermalImageFile.value = file.raw
  thermalImageUrl.value = URL.createObjectURL(file.raw)
  fusionImageUrl.value = ''
}

// 清除所有图片
const clearImages = () => {
  rgbImageUrl.value = ''
  rgbImageFile.value = null
  thermalImageUrl.value = ''
  thermalImageFile.value = null
  fusionImageUrl.value = ''
  errorMessage.value = ''
}

// 构建完整的URL
const getFullUrl = (path) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `http://localhost:8888${path}`
}

// 处理图像加载错误
const handleImageError = (e) => {
  console.error('融合图像加载失败:', e)
  errorMessage.value = `图像加载失败，URL: ${fusionImageUrl.value}，尝试完整URL: ${getFullUrl(fusionImageUrl.value)}`
}

// 测试融合图像生成
const testFusion = async () => {
  if (!rgbImageFile.value || !thermalImageFile.value) {
    ElMessage.warning('请先上传可见光和热成像图片')
    return
  }
  
  loading.value = true
  errorMessage.value = ''
  
  try {
    const formData = new FormData()
    formData.append('rgb_image', rgbImageFile.value)
    formData.append('thermal_image', thermalImageFile.value)
    
    console.log('正在发送测试请求...')
    const response = await axios.post(
      'http://localhost:8888/api/rgbt-detection/test-fusion',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )
    
    console.log('测试响应:', response.data)
    
    if (response.data.success) {
      fusionImageUrl.value = response.data.fusionImageUrl
      ElMessage.success('融合图像生成成功')
    } else {
      errorMessage.value = `服务器处理失败: ${response.data.message}`
      ElMessage.error('融合图像生成失败')
    }
  } catch (error) {
    console.error('测试请求失败:', error)
    errorMessage.value = `请求错误: ${error.message}`
    ElMessage.error('请求失败，请检查网络和服务器')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.test-fusion-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.upload-section {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.upload-container {
  flex: 1;
  border: 1px solid #eee;
  border-radius: 4px;
  padding: 15px;
}

.uploader {
  width: 100%;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
}

.upload-area:hover {
  border-color: #409EFF;
}

.upload-icon {
  font-size: 28px;
  color: #8c939d;
}

.upload-text {
  margin-top: 8px;
  color: #606266;
}

.uploaded-image {
  width: 100%;
  height: 200px;
  object-fit: contain;
}

.controls-container {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin: 20px 0;
}

.result-section {
  margin-top: 30px;
  border: 1px solid #eee;
  border-radius: 4px;
  padding: 15px;
}

.image-container {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.result-image {
  width: 100%;
  max-height: 400px;
}

.image-info {
  margin-top: 10px;
  width: 100%;
  padding: 10px;
  background-color: #f9f9f9;
  border-radius: 4px;
}
</style>
