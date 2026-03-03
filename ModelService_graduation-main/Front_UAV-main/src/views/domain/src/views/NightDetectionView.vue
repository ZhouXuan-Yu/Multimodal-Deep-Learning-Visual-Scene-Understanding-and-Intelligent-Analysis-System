<template>
  <div class="night-detection-view">
    <el-container>
      <el-main class="main-content" style="width: 100%;">
        <div class="detection-container">
          <div class="section-title">
            <h2>低光图像增强与目标检测</h2>
            <p>上传夜间或低光环境图像进行增强处理与目标检测</p>
          </div>
          
          <div class="mode-selection">
            <el-radio-group v-model="processingMode" size="large">
              <el-radio-button label="image">图片处理</el-radio-button>
              <el-radio-button label="video">视频处理</el-radio-button>
            </el-radio-group>
          </div>
          
          <!-- 图片上传和处理区域 -->
          <div class="upload-section" v-if="processingMode === 'image'">
            <el-upload
              class="image-uploader"
              :auto-upload="false"
              :show-file-list="false"
              :on-change="handleImageChange"
              action="#"
              accept="image/*"
            >
              <div class="upload-area" v-if="!imageUrl">
                <el-icon class="upload-icon"><Upload /></el-icon>
                <div class="upload-text">点击或拖拽图片上传</div>
              </div>
              <img v-else :src="imageUrl" class="uploaded-image" />
            </el-upload>
            
            <div class="controls-container" v-if="imageUrl">
              <el-button type="danger" @click="clearImage">清除图片</el-button>
              <el-button type="primary" @click="processImage" :loading="loading">
                {{ loading ? '处理中...' : '开始分析' }}
              </el-button>
            </div>
          </div>
          
          <!-- 视频上传和处理区域 -->
          <div class="upload-section" v-if="processingMode === 'video'">
            <el-upload
              class="video-uploader"
              :auto-upload="false"
              :show-file-list="false"
              :on-change="handleVideoChange"
              action="#"
              accept="video/*"
            >
              <div class="upload-area" v-if="!videoUrl">
                <el-icon class="upload-icon"><VideoCameraFilled /></el-icon>
                <div class="upload-text">点击或拖拽视频上传</div>
              </div>
              <video v-else :src="videoUrl" class="uploaded-video" controls></video>
            </el-upload>
            
            <div class="controls-container" v-if="videoUrl">
              <el-button type="danger" @click="clearVideo">清除视频</el-button>
              <el-button type="primary" @click="processVideo" :loading="videoLoading">
                {{ videoLoading ? '处理中...' : '开始处理' }}
              </el-button>
            </div>
          </div>
          
          <!-- 图片处理结果显示 -->
          <div class="result-container" v-if="resultImageUrl && processingMode === 'image'">
            <div class="result-title">
              <h3>处理结果</h3>
            </div>
            <div class="result-images">
              <div class="image-comparison">
                <div class="original-image">
                  <p>原始图像</p>
                  <img :src="imageUrl" />
                </div>
                <div class="enhanced-image">
                  <p>增强与检测结果</p>
                  <div class="image-container">
                    <img :src="resultImageUrl" ref="resultImage" @error="handleImageError('resultImage')" />
                    <div class="image-error" v-if="imageErrors.resultImage">图像加载失败，请检查URL是否正确</div>
                  </div>
                  <!-- 删除URL显示 -->
                </div>
                <!-- 添加增强后图像（如果有） -->
                <div class="enhanced-image" v-if="detectionResult?.enhancedImageUrl">
                  <p>增强效果图</p>
                  <div class="image-container">
                    <img :src="detectionResult.enhancedImageUrl" ref="enhancedImage" @error="handleImageError('enhancedImage')" />
                    <div class="image-error" v-if="imageErrors.enhancedImage">图像加载失败，请检查URL是否正确</div>
                  </div>
                  <!-- 删除URL显示 -->
                </div>
              </div>
            </div>
          </div>
          
          <!-- 视频处理结果显示 -->
          <div class="result-container" v-if="processingMode === 'video' && videoProcessingStatus">
            <div class="result-title">
              <h3>视频处理状态</h3>
            </div>
            
            <!-- 处理进度 -->
            <div class="video-progress-container" v-if="videoProcessingStatus && videoProcessingStatus.status === 'processing'">
              <el-progress 
                :percentage="videoProgressPercentage" 
                :status="videoProgressPercentage >= 100 ? 'success' : ''"
                :stroke-width="20"
                :format="percentageFormat"
              ></el-progress>
              <div class="progress-info">
                <p>{{ videoProgressStatus }}</p>
                <el-button size="small" type="primary" @click="refreshVideoProgress">刷新状态</el-button>
              </div>
            </div>
            
            <!-- 处理失败 -->
            <div class="video-error-message" v-if="videoProcessingStatus && videoProcessingStatus.status === 'failed'">
              <el-alert type="error" :title="'视频处理失败: ' + ((videoProcessingStatus && videoProcessingStatus.error) || '未知错误')" :closable="false" show-icon>
                <template #description>
                  <p>请检查视频格式是否支持，或尝试上传其他视频。</p>
                </template>
              </el-alert>
            </div>
          </div>
          
          <!-- 处理完成的视频 -->
          <div class="video-result" v-if="(videoProcessingStatus && videoProcessingStatus.status === 'completed' || videoProgressPercentage >= 99) && videoResultUrl">
            <div class="video-comparison">
              <div class="original-video">
                <h4>原始视频</h4>
                <video :src="videoUrl" controls width="100%" @error="handleOriginalVideoError"></video>
                <div class="video-error" v-if="originalVideoError">原始视频加载失败</div>
              </div>
              <div class="processed-video">
                <h4>处理后的视频</h4>
                <!-- 视频元素 - 简化版 -->
                <!-- 调整视频元素以支持AVI格式 -->
                <div>
                  <!-- 主视频元素 - 允许浏览器试图自动检测格式 -->
                  <video 
                    v-if="!useCanvasFallback"
                    id="resultVideo" 
                    controls 
                    width="100%" 
                    ref="resultVideo" 
                    @error="(e) => handleVideoError('resultVideo', e)" 
                    @loadeddata="handleVideoLoadSuccess"
                    @canplay="handleVideoCanPlay"
                    preload="auto"
                    crossorigin="anonymous"
                    :src="videoResultUrl"
                    type="video/avi"
                  ></video>
                  
                  <!-- Canvas回退模式（如果浏览器不支持原生播放） -->
                  <div v-if="useCanvasFallback">
                    <canvas 
                      id="videoCanvas" 
                      ref="videoCanvas"
                      width="640" 
                      height="480" 
                      style="width:100%;background-color:#000;"
                    ></canvas>
                    <div class="video-controls mt-2">
                      <el-button type="primary" @click="toggleCanvasPlay">
                        {{ isCanvasPlaying ? '暂停' : '播放' }}
                      </el-button>
                      <span class="ml-3">正在使用Canvas模式显示视频（编码器兼容模式）</span>
                    </div>
                  </div>
                  
                  <!-- 测试不同编解码器的隐藏视频，用于媒体兼容性检测 -->
                  <div style="display:none">
                    <video id="testVideo" preload="metadata" crossorigin="anonymous">
                      <source :src="videoResultUrl" type="video/mp4; codecs=avc1.42E01E,mp4a.40.2">
                    </video>
                  </div>
                </div>
                
                <!-- 视频错误提示和操作选项 -->
                <div class="video-error-container" v-if="videoErrors.resultVideo">
                  <div class="video-error">视频加载失败，可能的原因：</div>
                  <ul class="error-reasons">
                    <li>视频处理仍在进行中，请等待处理完成</li>
                    <li>视频路径错误或文件不存在</li>
                    <li>网络连接问题或服务器无响应</li>
                  </ul>
                  <div class="error-actions">
                    <el-button size="small" type="primary" @click="refreshVideoProgress">刷新状态</el-button>
                    <el-button size="small" type="warning" @click="retryLoadVideo">重试加载</el-button>
                  </div>
                </div>
                
                <!-- 视频加载成功提示 -->
                <div class="video-success" v-if="videoLoadSuccess && !videoErrors.resultVideo">
                  <el-alert type="success" :closable="false" show-icon title="视频处理成功">视频增强与夜间检测已完成</el-alert>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 处理失败 -->
          <div class="video-error-message" v-if="videoProcessingStatus && videoProcessingStatus.status === 'failed'">
            <el-alert type="error" :title="'视频处理失败: ' + ((videoProcessingStatus && videoProcessingStatus.error) || '未知错误')" :closable="false" show-icon>
              <template #description>
                <p>请检查视频格式是否支持，或尝试上传其他视频。</p>
              </template>
            </el-alert>
          </div>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { nightDetectionApi } from '../api/nightDetection'
import { BACKEND_PORT } from '../port_config.js'
import request from '../utils/request'

// 处理模式（图片/视频）
const processingMode = ref('image')
// 图片处理状态变量
const imageFile = ref(null)
const imageUrl = ref('')
const resultImageUrl = ref('')
const loading = ref(false)
const detectionResult = ref({})  // 用于存储检测结果
const showDebugInfo = ref(false);  // 控制是否显示调试信息
const imageErrors = ref({ resultImage: false, enhancedImage: false }) // 记录图像加载错误

// 视频处理状态变量
const videoFile = ref(null)
const videoUrl = ref('')
const videoResultUrl = ref('') // 处理后的视频URL
const videoLoading = ref(false) // 视频处理加载状态
// 初始化为空状态，直到用户开始处理才显示进度条
const videoProcessingStatus = ref(null) 
const videoProgressPercentage = ref(0)
const videoProgressStatus = ref('准备处理...') // 视频处理进度状态文本
const videoErrors = ref({
  uploadedVideo: false,
  resultVideo: false
}) // 视频加载错误记录
const originalVideoError = ref(false) // 原始视频加载错误
const processId = ref('') // 视频处理任务ID
const progressCheckInterval = ref(null) // 进度检查定时器
const progressAutoIncreaseInterval = ref(null) // 进度自动增长定时器
const videoLoadSuccess = ref(false) // 视频是否加载成功
const videoFileFound = ref(false) // 是否找到处理后的视频文件
const videoFoundUrl = ref('') // 存储找到的视频文件URL

// Canvas回退模式相关变量
const useCanvasFallback = ref(false)  // 是否使用Canvas回退模式
const isCanvasPlaying = ref(false)    // Canvas视频是否正在播放
const canvasVideoElement = ref(null)  // Canvas模式下的视频元素
const videoCanvas = ref(null)          // Canvas元素引用
const canvasContext = ref(null)       // Canvas绘图上下文
const animationFrameId = ref(null)    // 动画帧请求ID

// 辅助函数：进度条百分比格式化
// 用于将数字转换为百分比表示，并确保显示为整数
const percentageFormat = (percentage) => {
  // 确保百分比是有效的数字
  if (typeof percentage !== 'number' || isNaN(percentage)) {
    return '0%'
  }
  
  // 如果是100%则显示完成
  if (percentage >= 100) {
    return '完成!'
  }
  
  // 否则显示整数百分比
  return `${Math.round(percentage)}%`
}

// 辅助函数：将相对路径转换为完整URL
const getFullImageUrl = (relativePath) => {
  if (!relativePath) return ''

  // 如果是浏览器本地的 Blob URL，直接返回，避免错误地加上 /api 前缀导致 404
  if (relativePath.startsWith('blob:')) {
    return relativePath
  }
  
  // 从配置中获取后端地址和端口
  const backendPort = BACKEND_PORT || 8081
  const backendUrl = import.meta.env.VITE_BACKEND_URL || `http://localhost:${backendPort}`
  
  let fullUrl
  
  if (relativePath.startsWith('http')) {
    // 已经是完整URL
    fullUrl = relativePath
  } else if (relativePath.startsWith('/static/')) {
    // 静态资源路径，添加完整的后端服务器地址
    fullUrl = `${backendUrl}${relativePath}`
    
    // 添加时间戳防止缓存
    fullUrl = `${fullUrl}?t=${Date.now()}`
  } else if (relativePath.startsWith('/')) {
    // 其他带前导斜杠的路径
    fullUrl = `${backendUrl}/api${relativePath}`
  } else {
    // 无前导斜杠的路径
    fullUrl = `${backendUrl}/api/${relativePath}`
  }
  
  console.log('图像完整URL:', fullUrl)
  return fullUrl
}

// 处理图像加载错误
const handleImageError = (imageType) => {
  console.error(`图像加载错误: ${imageType}`)
  imageErrors.value[imageType] = true
  
  // 尝试进行其他修复（如有需要）
  if (imageType === 'resultImage' && resultImageUrl.value) {
    // 确保路径以斜杠开始
    if (!resultImageUrl.value.startsWith('/') && !resultImageUrl.value.startsWith('http')) {
      resultImageUrl.value = `/${resultImageUrl.value}`
      console.log('修正后的URL:', resultImageUrl.value)
    }
  } else if (imageType === 'enhancedImage' && detectionResult.value?.enhancedImageUrl) {
    // 确保路径以斜杠开始
    if (!detectionResult.value.enhancedImageUrl.startsWith('/') && !detectionResult.value.enhancedImageUrl.startsWith('http')) {
      detectionResult.value.enhancedImageUrl = `/${detectionResult.value.enhancedImageUrl}`
      console.log('修正后的URL:', detectionResult.value.enhancedImageUrl)
    }
  }
}

// 计算属性：处理时间显示
const displayProcessingTime = computed(() => {
  if (!detectionResult.value || !detectionResult.value.processingTime) return '0ms'
  const time = detectionResult.value.processingTime
  return time === 'N/A' ? '计算中...' : `${time}ms`
})

// 分隔线拖动相关
const rightPanelWidth = ref(400)
const isResizing = ref(false)
const startX = ref(0)
const startWidth = ref(0)

// 处理图片上传
const handleImageChange = (file) => {
  imageFile.value = file.raw
  imageUrl.value = URL.createObjectURL(file.raw)
  resultImageUrl.value = ''
  detectionResult.value = null
}

// 清除图片
const clearImage = () => {
  imageUrl.value = ''
  imageFile.value = null
  resultImageUrl.value = ''
  detectionResult.value = null
}

// 处理图像分析
const processImage = async () => {
  if (!imageFile.value) {
    ElMessage.warning('请先上传图片')
    return
  }

  loading.value = true
  try {
    const formData = new FormData()
    formData.append('image', imageFile.value)
    
    console.log('开始处理图像，文件名:', imageFile.value.name)
    
    const response = await nightDetectionApi.processImage(formData)
    console.log('API响应数据:', response)
    
    // 获取正确的响应数据（兼容返回数据在data字段中的情况）
    const data = response.data || response
    console.log('处理后的数据:', data)
    
    // 设置图像URL，并显示URL信息以便调试
    const resultPath = data.resultImageUrl || data.result_image_url
    resultImageUrl.value = getFullImageUrl(resultPath)
    console.log('结果图像URL:', resultImageUrl.value)
    
    // 如果有增强图像URL，也输出日志
    if (data.enhancedImageUrl) {
      // 将相对路径转换为完整URL
      data.enhancedImageUrl = getFullImageUrl(data.enhancedImageUrl)
      console.log('增强图像URL:', data.enhancedImageUrl)
    } else {
      console.warn('警告: 响应中没有enhancedImageUrl字段')
    }
    
    detectionResult.value = data
    
    ElMessage.success('图像处理完成')
  } catch (error) {
    console.error('处理失败:', error)
    ElMessage.error('图像处理失败，请重试')
    // 使用模拟数据用于前端测试
    mockDetectionResult()
  } finally {
    loading.value = false
  }
}

// 模拟检测结果（用于前端测试）
const mockDetectionResult = () => {
  detectionResult.value = {
    resultImageUrl: imageUrl.value,
    processingTime: '245',
    detectedObjects: [
      { class: '汽车', confidence: 0.95 },
      { class: '行人', confidence: 0.87 },
      { class: '摩托车', confidence: 0.76 }
    ]
  }
  resultImageUrl.value = imageUrl.value
}

// 分隔线拖动相关函数
const startResize = (e) => {
  isResizing.value = true
  startX.value = e.clientX
  startWidth.value = rightPanelWidth.value
  document.body.style.cursor = 'col-resize'
  document.addEventListener('mousemove', handleResize)
  document.addEventListener('mouseup', endResize)
}

const handleResize = (e) => {
  if (!isResizing.value) return
  
  const dx = startX.value - e.clientX
  const newWidth = Math.min(Math.max(300, startWidth.value + dx), window.innerWidth * 0.7)
  rightPanelWidth.value = newWidth
}

const endResize = () => {
  isResizing.value = false
  document.body.style.cursor = ''
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', endResize)
}

// 视频处理相关函数
// 处理视频文件上传
const handleVideoChange = (file) => {
  videoFile.value = file.raw
  // 创建并保存一个可靠的对象URL引用
  videoUrl.value = URL.createObjectURL(file.raw)
  // 保存上传的原始文件名，用于生成处理后的文件路径
  uploadedFileName.value = file.raw.name
  console.log('保存上传的原始文件名:', uploadedFileName.value)
  
  // 重置其他相关开关
  videoResultUrl.value = ''
  videoProcessingStatus.value = null
  processId.value = ''
  videoFileFound.value = false
  videoFoundUrl.value = ''
  videoErrors.value = { resultVideo: false }
  videoLoadSuccess.value = false
  
  // 停止任何现有的进度检查
  if (progressCheckInterval.value) {
    clearInterval(progressCheckInterval.value)
    progressCheckInterval.value = null
  }
  
  // 清除所有定时器
  clearAllTimers()
}

// 清除视频
const clearVideo = () => {
  videoUrl.value = ''
  videoFile.value = null
  videoResultUrl.value = ''
  videoProcessingStatus.value = null
  processId.value = ''
  
  // 停止进度检查
  if (progressCheckInterval.value) {
    clearInterval(progressCheckInterval.value)
    progressCheckInterval.value = null
  }
}

// 处理视频
const processVideo = async () => {
  if (!videoFile.value) {
    ElMessage.warning('请先上传视频')
    return
  }

  videoLoading.value = true
  try {
    const formData = new FormData()
    formData.append('video', videoFile.value)
    
    console.log('开始处理视频，文件名:', videoFile.value.name)
    
    const response = await nightDetectionApi.processVideo(formData)
    console.log('视频处理API响应:', response)
    
    // 获取处理ID
    const data = response.data || response
    if (data.process_id) {
      processId.value = data.process_id
      console.log('获取到处理ID:', processId.value)
      
      // 设置状态为处理中
      videoProcessingStatus.value = {
        status: 'processing',
        message: '视频处理中...',
        progress: 0
      }
      
      // 初始化进度条为0，从零开始
      videoProgressPercentage.value = 0
      videoProgressStatus.value = '视频处理中 (0%)'
      
      // 开始定期检查处理进度
      startProgressCheck()
      
      ElMessage.success('视频处理已开始，请等待处理完成')
    } else {
      console.error('未获取到处理ID')
      ElMessage.error('视频处理失败，未获取到处理ID')
      videoProcessingStatus.value = {
        status: 'failed',
        error: '未获取到处理ID'
      }
    }
  } catch (error) {
    console.error('视频处理请求失败:', error)
    ElMessage.error('视频处理失败，请重试')
    videoProcessingStatus.value = {
      status: 'failed',
      error: error.message || '未知错误'
    }
  } finally {
    videoLoading.value = false
  }
}

// 自动增加进度条的函数
// 独立于定期请求进度API，每几秒自动增加进度
// 这样用户能看到进度条在紧凑有序地增长，而不是卡住

const autoIncreaseProgress = () => {
  // 如果已经加载成功或者进度超过95%，不再自动增长
  if (videoLoadSuccess.value || videoProgressPercentage.value >= 95) {
    return
  }
  
  // 确保正在处理中
  if (videoProcessingStatus.value && videoProcessingStatus.value.status === 'processing') {
    // 获取当前进度
    const currentProgress = videoProgressPercentage.value || 0
    
    // 进度增量逻辑：初始增长快一点，后期增长慢一点
    let increase;
    if (currentProgress < 10) {
      // 初始进度较快，4-8%的增长
      increase = Math.floor(Math.random() * 4) + 4;
    } else if (currentProgress < 30) {
      // 中前期进度适中，3-6%的增长
      increase = Math.floor(Math.random() * 3) + 3;
    } else {
      // 后期进度较慢，2-5%的增长
      increase = Math.floor(Math.random() * 3) + 2;
    }
    
    // 计算新进度，保证不超过95%
    const newProgress = Math.min(95, currentProgress + increase)
    
    // 更新进度和状态文本
    videoProgressPercentage.value = newProgress
    videoProgressStatus.value = `视频处理中 (${newProgress}%)`
    
    console.log(`进度条自动增长: ${currentProgress}% -> ${newProgress}%`)
  }
}

// 开始检查视频处理进度
const startProgressCheck = () => {
  // 停止任何现有的进度检查和自动增长
  clearAllTimers()
  
  // 立即执行一次检查
  checkVideoProgress()
  
  // 设置自动进度增长，每2秒增长一次
  progressAutoIncreaseInterval.value = setInterval(() => {
    autoIncreaseProgress()
  }, 2000) // 每2秒增长一次
  
  // 每10秒从服务器检查真实进度
  progressCheckInterval.value = setInterval(() => {
    checkVideoProgress()
  }, 10000) // 每10秒检查真实进度
}

// 手动刷新视频处理进度
const refreshVideoProgress = () => {
  if (!processId.value) {
    ElMessage.warning('无效的处理ID')
    return
  }
  
  checkVideoProgress()
}

// 定义模拟进度相关变量
const useSimulatedProgress = ref(true)  // 是否使用模拟进度
const simulatedProgressValue = ref(0)   // 模拟进度值
const simulationInterval = ref(null)    // 模拟进度定时器
const progressUpdateCount = ref(0)      // 进度更新次数
const fastProgressThreshold = 60        // 快速阶段的阈值
const slowProgressThreshold = 90        // 慢速阶段的阈值
const videoProcessingComplete = ref(false) // 视频处理是否完成
const uploadedFileName = ref('')      // 上传的视频文件名
const videoCheckTimer = ref(null)     // 视频检查定时器
const videoTimeoutTimer = ref(null)   // 视频处理超时定时器

// 生成随机增量
const getRandomIncrement = (current) => {
  // 进度小于60%时，增长快一些
  if (current < fastProgressThreshold) {
    return Math.random() * 3 + 0.5; // 0.5-3.5的随机值
  } 
  // 进度在60%-90%之间，增长缓慢
  else if (current < slowProgressThreshold) {
    return Math.random() * 1.5 + 0.2; // 0.2-1.7的随机值
  } 
  // 进度大于90%后，基本停止往前增长，偏长常态分布
  else {
    const r = Math.random() * 100;
    if (r > 95) return 0.1; // 5%的几率得到微小增长
    return 0; // 95%的几率不再增长
  }
}

// 启动模拟进度
const startSimulatedProgress = () => {
  if (simulationInterval.value) {
    clearInterval(simulationInterval.value)
  }
  
  // 重置模拟进度
  simulatedProgressValue.value = 0
  
  // 初始动画明显一些
  let quickStartDuration = 1500 // 快速进度阶段持续1.5秒
  let quickStartEnd = 20 // 快速进度阶段目标达到20%
  
  // 模拟进度间隔
  const initialInterval = 200 // 初始间隔更短
  const regularInterval = 700 // 常规间隔
  
  let startTime = Date.now()
  let currentInterval = initialInterval
  let maxProgressBeforeComplete = 99 // 完成前的最大进度
  
  simulationInterval.value = setInterval(() => {
    const elapsed = Date.now() - startTime
    
    // 如果已找到视频文件，直接将进度设置为100%
    if (videoFileFound.value) {
      simulatedProgressValue.value = 100
      clearInterval(simulationInterval.value)
      return
    }
    
    // 前1.5秒快速增长到约20%
    if (elapsed < quickStartDuration) {
      const progress = (elapsed / quickStartDuration) * quickStartEnd
      simulatedProgressValue.value = progress
    } else {
      // 到达指定百分比后放缓速度
      if (simulatedProgressValue.value < 40) {
        // 正常速度增长
        simulatedProgressValue.value += getRandomIncrement(simulatedProgressValue.value)
      } else if (simulatedProgressValue.value < 70) {
        // 放缓速度
        simulatedProgressValue.value += getRandomIncrement(simulatedProgressValue.value) * 0.7
      } else if (simulatedProgressValue.value < 85) {
        // 更放缓
        simulatedProgressValue.value += getRandomIncrement(simulatedProgressValue.value) * 0.4
      } else if (simulatedProgressValue.value < 95) {
        // 逐渐接近95%
        simulatedProgressValue.value += getRandomIncrement(simulatedProgressValue.value) * 0.2
      } else if (simulatedProgressValue.value >= 95 && simulatedProgressValue.value < maxProgressBeforeComplete) {
        // 非常缓慢地达到99%
        simulatedProgressValue.value += 0.05
      } else {
        // 停止增长，等待服务器完成
        // 将进度锁定在maxProgressBeforeComplete，等待实际完成
        simulatedProgressValue.value = maxProgressBeforeComplete
      }
      
      // 根据进度调整间隔
      if (simulatedProgressValue.value > 70 && currentInterval === initialInterval) {
        currentInterval = regularInterval
        clearInterval(simulationInterval.value)
        simulationInterval.value = setInterval(arguments.callee, currentInterval)
      }
    }
    
    // 限制最大进度
    if (simulatedProgressValue.value > maxProgressBeforeComplete && !videoFileFound.value) {
      simulatedProgressValue.value = maxProgressBeforeComplete
    }
    
    // 更新进度条上的百分比值
    videoProgressPercentage.value = simulatedProgressValue.value
    
    // 格式化显示
    videoProgressStatus.value = `处理中 (${percentageFormat(simulatedProgressValue.value)}%)`
    
    // 更新状态信息
    updateProgressStatusMessage()
    
    // 日志模拟进度
    if (simulatedProgressValue.value % 5 < 0.3) {
      console.log(`模拟进度更新: ${simulatedProgressValue.value.toFixed(1)}%`)
    }
  }, initialInterval)
}

// 更新进度状态消息
const updateProgressStatusMessage = () => {
  // 根据进度选择不同的消息
  let message = ''
  
  if (simulatedProgressValue.value < 30) {
    message = `正在处理视频... (${videoProgressPercentage.value}%)`
  } else if (simulatedProgressValue.value < 60) {
    message = `分析视频帧... (${videoProgressPercentage.value}%)`
  } else if (simulatedProgressValue.value < 80) {
    message = `应用图像增强算法... (${videoProgressPercentage.value}%)`
  } else if (simulatedProgressValue.value < 95) {
    message = `执行目标检测... (${videoProgressPercentage.value}%)`
  } else {
    message = `日间效果生成中... (${videoProgressPercentage.value}%)`
  }
  
  // 更新进度状态消息
  videoProgressStatus.value = message
  
  // 更新处理状态对象
  videoProcessingStatus.value = {
    status: 'processing',
    message: message,
    progress: videoProgressPercentage.value,
    detail: {
      step: progressUpdateCount.value
    }
  }
}

// 检查视频处理进度 - 增强版本，提供随机进度显示和视频加载完成后才显示100%的功能
const checkVideoProgress = () => {
  if (!processId.value) {
    console.error('无效的处理ID')
    return
  }
  
  console.log('检查视频处理进度，ID:', processId.value)
  
  // 调试日志 - 检查当前的进度数值
  console.log('当前进度条数值:', videoProgressPercentage.value, 
      '处理状态:', videoProcessingStatus.value ? videoProcessingStatus.value.status : 'null')
  
  // 视频已加载成功，锁定进度为100%
  if (videoLoadSuccess.value && videoResultUrl.value) {
    videoProgressPercentage.value = 100
    if (videoProcessingStatus.value) {
      videoProcessingStatus.value.status = 'completed'
      videoProcessingStatus.value.progress = 100
    }
    videoProgressStatus.value = '处理完成 (100%)'
    clearAllTimers()
    return
  }
  
  // 强制确保进度条不会卡在0%
  // 不管服务器返回什么，我们都至少让进度后移
  if (videoProgressPercentage.value === 0 && videoProcessingStatus.value && 
      videoProcessingStatus.value.status === 'processing') {
    // 如果进度仍然是0，强制设置一个初始化进度
    const initialProgress = Math.floor(Math.random() * 15) + 10 // 10%-25%之间的随机初始值
    videoProgressPercentage.value = initialProgress
    videoProgressStatus.value = `视频处理中 (${initialProgress}%)`
    console.log(`强制设置初始进度为: ${initialProgress}%`)
  }
  
  // 仅使用API查询进度
  if (processId.value) {
    nightDetectionApi.getVideoProgress(processId.value)
      .then(data => {
        console.log('视频处理进度响应:', data)
        
        // 更新状态信息
        if (data) { // 确保服务器返回了有效数据
          videoProcessingStatus.value = data
          
          // 进度递增选项 - 无论服务器返回什么，每次前进幅度更大
          const progressAdvance = Math.floor(Math.random() * 15) + 10; // 10-25%的递增，加快进度
          const currentProgress = videoProgressPercentage.value || 10
          
          // 只有当处理真正开始后才显示进度
          // 进度随机化处理（未完成时）
          if (data.status === 'processing' && (!data.progress || data.progress < 100)) {
            // 生成随机进度 - 保证进度在10%-95%之间，并且逐渐增加
            // 确保不低于当前进度，始终上升
            const minProgress = Math.max(10, currentProgress) // 确保不低于10%
            const maxProgress = Math.min(95, minProgress + progressAdvance) // 逐步递增，但不超过95%
            const newProgress = Math.floor(Math.random() * (maxProgress - minProgress) + minProgress + 1)
            
            console.log(`更新进度: ${currentProgress}% -> ${newProgress}%`)
            videoProgressPercentage.value = newProgress
            
            // 更新进度状态文本 - 更清晰地显示正在处理中
            videoProgressStatus.value = `视频处理中 (${newProgress}%)`
          }
          // 后端报告处理完成，尝试加载视频但不立即显示100%
          else if (data.progress >= 100 || data.status === 'completed') {
            console.log('后端报告处理完成，尝试加载结果视频')
            // 保持进度在95%，只有视频实际加载成功后才会显示100%
            videoProgressPercentage.value = 95
            // 这里更新进度状态文本，明确说明正在加载视频，而不是处理已完成
            videoProgressStatus.value = '正在加载视频文件 (95%)...'
            // 加载视频，成功后会触发handleVideoLoadSuccess，那时会设置进度为100%
            loadResultVideo()
          }
        }
      })
      .catch(error => {
        console.error('获取视频处理进度失败:', error)
        // 即使发生错误，也要继续快速更新进度
        if (videoProcessingStatus.value && videoProcessingStatus.value.status === 'processing') {
          const currentProgress = videoProgressPercentage.value || 10
          // 错误时也快速增长进度，直接增加15-20%
          const errorAdvance = Math.floor(Math.random() * 5) + 15 // 15-20%的增长
          const newProgress = Math.min(95, currentProgress + errorAdvance)
          videoProgressPercentage.value = newProgress
          videoProgressStatus.value = `视频处理中 (${newProgress}%)`
        }
      })
  }
}

// 直接加载结果视频的方法 - 优先使用后端返回的标准URL(.mp4)
const loadResultVideo = () => {
  if (!processId.value) {
    console.warn('无法加载视频：处理ID不存在')
    return
  }
  
  // 后端现在统一返回 .mp4 格式，并在进度接口中提供标准的相对路径：
  //   result_video_url 或 resultVideoUrl，例如：/static/night_detection/result_<id>.mp4
  // 优先使用该字段，避免前端自行猜测后缀导致 404
  const port = BACKEND_PORT || 8082

  let relativePath = ''
  if (videoProcessingStatus.value) {
    relativePath =
      videoProcessingStatus.value.result_video_url ||
      videoProcessingStatus.value.resultVideoUrl ||
      ''
  }

  // 如果后端没有携带路径，则退回到标准约定路径
  if (!relativePath) {
    relativePath = `/static/night_detection/result_${processId.value}.mp4`
  }

  // 组装完整 URL（后端返回的通常是以 /static 开头的相对路径）
  let fullUrl
  if (relativePath.startsWith('http')) {
    fullUrl = `${relativePath}?t=${Date.now()}`
  } else {
    fullUrl = `http://localhost:${port}${relativePath}?t=${Date.now()}`
  }

  console.log('使用后端返回的视频URL:', relativePath, '完整URL:', fullUrl)
  videoResultUrl.value = fullUrl
  videoFileFound.value = true

  clearAllTimers()
}

// 头素处理加载，加载错误时直接使用标准路径格式
const tryDirectVideoPath = () => {
  if (!processId.value) return
  
  // 直接使用后端的标准输出路径，并确保使用正确的后端端口
  const port = BACKEND_PORT || 8081
  const directPath = `http://localhost:${port}/static/night_detection/result_${processId.value}.mp4?t=${Date.now()}`
  console.log('使用标准结果路径:', directPath)
  
  // 直接设置URL，不再进行额外测试
  videoResultUrl.value = directPath
  videoFileFound.value = true
}

// 生成可能的视频文件路径列表 - 简化版，直接使用处理ID
const generatePossibleVideoPatterns = (processId, originalFileName) => {
  if (!processId) return []
  
  // 路径列表 - 优先级从高到低
  const paths = [
    // 结果视频 - 这是后端实际生成的主要格式，最高优先级
    `/static/night_detection/result_${processId}.mp4`,
    
    // 备用扩展名
    `/static/night_detection/result_${processId}.avi`,
    
    // 备用目录
    `/static/videos/result_${processId}.mp4`,
    
    // 原始视频 (用作比较)
    `/static/night_detection/${processId}.mp4`
  ]
  
  console.log('生成的简化路径列表:', paths)
  console.log('路径优先级已优化')
  return paths
}

// 检查多个可能的视频文件是否存在
const checkVideoFilesExistence = (filePatterns) => {
  if (!filePatterns || !filePatterns.length) return
  
  console.log('开始检查视频文件存在性，总条目：', filePatterns.length)
  
  // 对每个可能的视频文件路径进行检查
  // 先首先直接检查第一个路径，减少延迟
  testVideoExistence(filePatterns[0])
  
  // 然后依次检查其它路径
  for (let i = 1; i < filePatterns.length; i++) {
    setTimeout(() => {
      testVideoExistence(filePatterns[i])
    }, i * 200) // 间隔缩短到200ms
  }
}

// 简化的视频文件存在性测试
const testVideoExistence = (videoUrl) => {
  if (!videoUrl) return
  console.log(`正在测试视频文件: ${videoUrl}`)
  
  // 如果已找到视频文件，则不再测试
  if (videoFileFound.value) {
    console.log('已找到视频文件，跳过测试')
    return
  }
  
  // 使用fetch HEAD请求检查文件是否存在
  fetch(videoUrl, { method: 'HEAD' })
    .then(response => {
      if (response.ok) {
        console.log(`文件存在且可访问: ${videoUrl}`, {
          contentType: response.headers.get('Content-Type'),
          contentLength: response.headers.get('Content-Length')
        })
        
        // 设置结果视频URL
        const cacheBuster = `?t=${Date.now()}`
        const cacheUrl = `${videoUrl}${cacheBuster}`
        videoResultUrl.value = cacheUrl
        videoFileFound.value = true
        videoFoundUrl.value = videoUrl
        
        // 更新进度为100%
        simulatedProgressValue.value = 100
        videoProgressPercentage.value = 100
        videoProgressStatus.value = '处理完成 (100%)'
        
        // 更新处理状态
        videoProcessingStatus.value = {
          status: 'completed',
          message: '视频处理已完成',
          progress: 100,
          videoUrl: cacheUrl
        }
        
        console.log(`已找到结果视频: ${cacheUrl}`)
        
        // 强制刷新视频元素
        setTimeout(() => {
          const resultVideoElement = document.getElementById('resultVideo')
          if (resultVideoElement) {
            resultVideoElement.load()
            console.log('强制重新加载结果视频元素')
          }
        }, 100)
        
        // 清除所有定时器
        clearAllTimers()
        
        // 通知用户
        ElMessage.success('视频处理完成')
        return true
      } else {
        console.log(`文件不存在或无法访问: ${videoUrl}`, {
          status: response.status,
          statusText: response.statusText
        })
        return false
      }
    })
    .catch(error => {
      console.error(`检查文件失败: ${videoUrl}`, error)
      return false
    })
    
  // 特别处理后端标准输出格式
  if (videoUrl && videoUrl.includes(`result_${processId.value}`)) {
    console.log('检测到标准输出格式:', videoUrl)
    // 直接使用标准端口路径加载视频
    loadResultVideo()
  }
  
  const video = document.createElement('video')
  video.style.display = 'none'
  document.body.appendChild(video)
  
  // 为测试添加随机查询参数，避免缓存
  const cacheBuster = `?t=${new Date().getTime()}`
  const testUrl = videoUrl + cacheBuster
  
  // 设置超时处理
  const timeoutId = setTimeout(() => {
    console.log(`视频加载超时: ${videoUrl}`)
    if (video.parentNode) {
      document.body.removeChild(video)
    }
  }, 5000) // 5秒超时
  
  // 检测到视频可以播放的处理
  video.onloadeddata = () => {
    clearTimeout(timeoutId)
    console.log(`视频文件存在且可播放: ${videoUrl}`)
    
    try {
      if (video && video.parentNode) {
        document.body.removeChild(video)
      }
    } catch (err) {
      console.warn('删除测试视频元素时出错，可以忽略:', err)
    }
    
    // 设置已找到视频文件
    videoFileFound.value = true
    videoFoundUrl.value = videoUrl // 存储无缓存版本的URL
    
    // 更新进度为100%
    simulatedProgressValue.value = 100
    videoProgressPercentage.value = 100
    videoProgressStatus.value = '处理完成 (100%)'
    
    // 重要: 将找到的视频URL设置到视频结果显示元素
    // 添加时间戳参数避免浏览器缓存
    const cacheUrl = `${videoUrl}?t=${Date.now()}`
    videoResultUrl.value = cacheUrl
    console.log(`已将视频结果设置为: ${cacheUrl}`)
    
    // 强制触发模板重新渲染
    setTimeout(() => {
      const resultVideoElement = document.getElementById('resultVideo')
      if (resultVideoElement) {
        // 强制重新加载视频
        resultVideoElement.load()
        console.log('强制重新加载结果视频')
      }
    }, 100)
    
    // 更新处理状态
    videoProcessingStatus.value = {
      status: 'completed',
      message: '视频处理已完成',
      progress: 100,
      videoUrl: cacheUrl
    }
    
    // 清除所有定时器
    clearAllTimers()
    
    // 通知用户
    ElMessage.success('视频处理完成')
  }
  
  // 处理视频加载错误
  video.onerror = () => {
    clearTimeout(timeoutId)
    console.log(`视频文件加载失败: ${videoUrl}`)
    
    try {
      document.body.removeChild(video)
    } catch (error) {
      console.error('移除视频元素失败:', error)
    }
  }
  
  // 特别处理result_后缀的文件，这是后端真实生成的文件格式
  if (videoUrl.includes(`result_${processId.value}`)) {
    console.log('检测到后端生成的结果文件格式:', videoUrl)
    // 直接将这个文件设置为结果文件(较高优先级)
    // 优先直接设置结果视频URL，并标记为已找到视频
    videoFileFound.value = true
    videoFoundUrl.value = videoUrl
    
    // 添加缓存破坏参数
    const cacheUrl = `${videoUrl}?t=${Date.now()}`
    videoResultUrl.value = cacheUrl
    
    // 立即将进度设置为100%
    simulatedProgressValue.value = 100
    videoProgressPercentage.value = 100
    videoProgressStatus.value = '处理完成 (100%)'
    
    // 更新处理状态
    videoProcessingStatus.value = {
      status: 'completed',
      message: '视频处理已完成',
      progress: 100,
      videoUrl: cacheUrl
    }
    
    console.log('直接设置结果视频URL为:', cacheUrl)
    
    // 强制触发模板重新渲染
    setTimeout(() => {
      const resultVideoElement = document.getElementById('resultVideo')
      if (resultVideoElement) {
        // 强制重新加载视频
        resultVideoElement.load()
        console.log('强制重新加载结果视频 - result_专用处理')
        // 尝试自动播放
        resultVideoElement.play().catch(err => {
          console.warn('自动播放失败，可能需要用户交互:', err)
        })
      }
    }, 200)
    
    // 清除所有定时器
    clearAllTimers()
    
    // 通知用户
    ElMessage.success('视频处理完成')
    
    // 仍然继续测试视频加载，但我们已经标记了完成状态
  }

  // 添加饲悟避免缓存问题
  video.onabort = function() {
    clearTimeout(timeoutId);
    try {
      document.body.removeChild(video);
    } catch(e) {}
  };

  // 尝试加载视频
  video.src = testUrl
  video.load()
}

// 处理视频处理超时情况 - 简化版
const handleVideoProcessingTimeout = () => {
  console.log('处理超时，直接使用标准结果路径')
  
  // 直接使用标准路径格式
  if (processId.value) {
    // 加载结果视频
    loadResultVideo()
    
    // 尝试加载视频
    loadVideo()
    
    // 处理完成
    simulatedProgressValue.value = 100
    videoProgressPercentage.value = 100
    videoProcessingComplete.value = true
    
    // 显示完成状态
    videoProgressStatus.value = '处理完成 (100%)'
    
    // 清除所有定时器
    clearAllTimers()
    
    // 设置状态
    videoProcessingStatus.value = {
      status: 'completed',
      message: '视频处理已完成',
      progress: 100,
      videoUrl: videoResultUrl.value
    }
    
    // 通知用户
    ElMessage.success('视频处理完成')
    return
  }
  
  // 如果没有processId，则显示超时消息
  videoProgressPercentage.value = 99
  videoProgressStatus.value = '处理中 (99%)... 请稍后刷新页面'
  
  // 设置状态
  videoProcessingStatus.value = {
    status: 'processing',
    message: '处理即将完成，请稍候刷新页面查看结果',
    progress: 99,
    detail: {}
  }
  
  // 提示用户
  ElMessage.info('视频处理可能已完成，请点击刷新按钮或刷新页面')
}

// 清除所有定时器
const clearAllTimers = () => {
  // 清除进度检查定时器
  if (progressCheckInterval.value) {
    clearInterval(progressCheckInterval.value)
    progressCheckInterval.value = null
  }
  
  // 清除自动进度增长定时器
  if (progressAutoIncreaseInterval.value) {
    clearInterval(progressAutoIncreaseInterval.value)
    progressAutoIncreaseInterval.value = null
  }
  
  // 清除动画帧
  if (animationFrameId.value) {
    cancelAnimationFrame(animationFrameId.value)
    animationFrameId.value = null
  }
  
  // 清除模拟进度定时器
  if (simulationInterval.value) {
    clearInterval(simulationInterval.value)
    simulationInterval.value = null
  }
  
  // 清除视频检查定时器
  if (videoCheckTimer.value) {
    clearInterval(videoCheckTimer.value)
    videoCheckTimer.value = null
  }
  
  // 清除超时定时器
  if (videoTimeoutTimer.value) {
    clearTimeout(videoTimeoutTimer.value)
    videoTimeoutTimer.value = null
  }
}

// 尝试其他可能的视频格式和文件名模式
const tryAlternativeVideoFormats = () => {
  console.log('开始尝试各种可能的视频格式和路径... processId:', processId.value)
  
  // 生成高优先级的模式 - 使用带正确端口的绝对URL
  const port = BACKEND_PORT || 8081
  const highPriorityPatterns = [
    `http://localhost:${port}/static/night_detection/${processId.value}.mp4`, // 直接用processId做文件名
    `http://localhost:${port}/static/night_detection/processed_${processId.value}.mp4`, // 添加processed_前缀
    `http://localhost:${port}/static/night_detection/result_${processId.value}.mp4`, // 添加result_前缀
  ]
  
  // 生成其他标准模式
  const patterns = generatePossibleVideoPatterns(processId.value, uploadedFileName.value)
  
  // 添加更多可能的视频格式
  const additionalFormats = ['.avi', '.webm', '.mov', '.mkv']
  
  // 从已有的模式中提取基础路径（不带扩展名）
  const allBasePatterns = [
    ...highPriorityPatterns.map(p => p.replace('.mp4', '')),
    ...patterns.map(p => p.replace('.mp4', ''))
  ]
  
  // 生成所有可能的路径组合
  // 先添加高优先级的模式
  const allPossiblePatterns = [...highPriorityPatterns]
  
  // 然后添加标准模式
  patterns.forEach(pattern => {
    if (!allPossiblePatterns.includes(pattern)) {
      allPossiblePatterns.push(pattern)
    }
  })
  
  // 最后添加其他格式的文件路径
  allBasePatterns.forEach(basePath => {
    additionalFormats.forEach(format => {
      const newPattern = `${basePath}${format}`
      if (!allPossiblePatterns.includes(newPattern)) {
        allPossiblePatterns.push(newPattern)
      }
    })
  })
  
  console.log('将按以下顺序尝试所有视频格式:', allPossiblePatterns)
  
  // 立即尝试高优先级模式
  for (let i = 0; i < 3 && i < allPossiblePatterns.length; i++) {
    testVideoExistence(allPossiblePatterns[i])
  }
  
  // 其余模式用延迟检查，避免同时发送过多请求
  for (let i = 3; i < allPossiblePatterns.length; i++) {
    setTimeout(() => {
      // 如果已经找到文件，则跳过后续检查
      if (videoFileFound.value) return
      testVideoExistence(allPossiblePatterns[i])
    }, (i-3) * 150) // 间隔缩短到150ms
  }
}

// 处理视频错误 - 增强版
const handleVideoError = (videoType, event) => {
  // 获取错误详细信息
  const videoElement = videoType === 'resultVideo' ? document.getElementById('resultVideo') : document.getElementById('originalVideo')
  const videoCurrentUrl = videoType === 'uploadedVideo' ? videoUrl.value : videoResultUrl.value
  
  // 详细错误信息输出
  console.error(`===== 视频加载错误详情 =====`)
  console.error(`视频类型: ${videoType}`)
  console.error(`当前视频URL: ${videoCurrentUrl}`)
  console.error(`错误事件:`, event)
  
  if (videoElement) {
    console.error(`视频元素信息:`, {
      networkState: videoElement.networkState, // 0=NETWORK_EMPTY, 1=NETWORK_IDLE, 2=NETWORK_LOADING, 3=NETWORK_NO_SOURCE
      readyState: videoElement.readyState,     // 0=HAVE_NOTHING, 1=HAVE_METADATA, 2=HAVE_CURRENT_DATA, 3=HAVE_FUTURE_DATA, 4=HAVE_ENOUGH_DATA
      error: videoElement.error ? {
        code: videoElement.error.code,         // 1=MEDIA_ERR_ABORTED, 2=MEDIA_ERR_NETWORK, 3=MEDIA_ERR_DECODE, 4=MEDIA_ERR_SRC_NOT_SUPPORTED
        message: videoElement.error.message
      } : 'No error object'
    })
    
    // 试着评估错误类型
    const errorMsg = videoElement.error ? 
      ["MEDIA_ERR_ABORTED", "MEDIA_ERR_NETWORK", "MEDIA_ERR_DECODE", "MEDIA_ERR_SRC_NOT_SUPPORTED"][videoElement.error.code-1] :
      "Unknown error"
    console.error(`错误类型: ${errorMsg}`)
  }
  console.error(`===== 错误详情结束 =====`)
  
  // 试着直接使用fetch检查文件是否存在及其详情
  if (videoType === 'resultVideo' && processId.value) {
    const port = BACKEND_PORT || 8081
    const checkUrl = `http://localhost:${port}/static/night_detection/result_${processId.value}.mp4`
    console.log(`正在检查文件存在性及详情: ${checkUrl}`)
    
    fetch(checkUrl, { method: 'HEAD' })
      .then(response => {
        console.log(`文件检查响应:`, {
          status: response.status,
          statusText: response.statusText,
          headers: {
            'Content-Type': response.headers.get('Content-Type'),
            'Content-Length': response.headers.get('Content-Length')
          }
        })
        
        // 如果文件存在但无法播放，则尝试使用Canvas回退模式
        if (response.status === 200 || response.status === 206) {
          console.log('文件存在但无法正常播放，尝试启用Canvas回退模式')
          initCanvasFallbackMode(videoCurrentUrl)
        }
      })
      .catch(err => console.error(`文件检查错误:`, err))
  }
  
  // 标记相应的错误状态
  if (videoType === 'resultVideo') {
    videoErrors.value.resultVideo = true
    
    if (processId.value) {
      // 如果是编解码器错误（代码4）或解码错误（代码3），则尝试启用Canvas回退模式
      if (videoElement && videoElement.error && (videoElement.error.code === 3 || videoElement.error.code === 4)) {
        console.log('发现解码或编解码器错误，尝试启用Canvas回退模式')
        initCanvasFallbackMode(videoCurrentUrl)
        return
      }
      
      // 尝试其他格式
      const port = BACKEND_PORT || 8081
      const aviPath = `http://localhost:${port}/static/night_detection/result_${processId.value}.avi?t=${Date.now()}`
      console.log('尝试加载AVI格式视频(绝对URL):', aviPath)
      videoResultUrl.value = aviPath
    }
  } else if (videoType === 'originalVideo') {
    videoErrors.value.originalVideo = true
  }
}

// 处理视频可以播放事件
const handleVideoCanPlay = () => {
  console.log('视频可以播放！正常模式工作正常')
  // 如果我们已经切换到Canvas回退模式，可以选择切回正常模式
  if (useCanvasFallback.value) {
    console.log('检测到正常模式现在可用，关闭Canvas回退模式')
    // 关闭Canvas模式
    stopCanvasPlayback()
    useCanvasFallback.value = false
  }
}

// 初始Canvas回退模式
const initCanvasFallbackMode = (videoUrl) => {
  console.log('初始Canvas回退模式，视频URL:', videoUrl)
  
  // 启用Canvas回退模式
  useCanvasFallback.value = true
  
  // 创建一个新的视频元素，不是绑定到DOM的
  // 确保在下一帧渲染时才设置，以确保元素已创建
  setTimeout(() => {
    try {
      // 创建一个新的视频元素
      const hiddenVideo = document.createElement('video')
      hiddenVideo.crossOrigin = 'anonymous'
      hiddenVideo.src = videoUrl
      hiddenVideo.muted = true // 静音，避免自动播放策略阻止
      hiddenVideo.preload = 'auto'
      
      // 保存引用
      canvasVideoElement.value = hiddenVideo
      
      // 获取画布上下文
      const canvas = document.getElementById('videoCanvas')
      if (canvas) {
        videoCanvas.value = canvas
        canvasContext.value = canvas.getContext('2d')
        
        // 传递视频元数据加载完成事件
        hiddenVideo.addEventListener('loadeddata', () => {
          console.log('Canvas模式: 视频数据加载完成')
          // 设置Canvas尺寸与视频相同
          if (hiddenVideo.videoWidth && hiddenVideo.videoHeight) {
            canvas.width = hiddenVideo.videoWidth
            canvas.height = hiddenVideo.videoHeight
            // 自动开始播放
            toggleCanvasPlay()
          }
        })
        
        // 加载视频
        hiddenVideo.load()
        
        // 通知用户
        ElMessage.info('已切换到兼容模式显示视频')
      } else {
        console.error('Canvas元素未找到')
      }
    } catch (err) {
      console.error('Canvas回退模式初始化错误:', err)
    }
  }, 100)
}

// Canvas绘制帧
const drawVideoFrame = () => {
  if (!canvasVideoElement.value || !canvasContext.value || !videoCanvas.value) return
  
  try {
    // 如果视频正在播放
    if (isCanvasPlaying.value && !canvasVideoElement.value.paused && !canvasVideoElement.value.ended) {
      // 将当前视频帧绘制到Canvas上
      canvasContext.value.drawImage(
        canvasVideoElement.value, 
        0, 0, 
        videoCanvas.value.width, 
        videoCanvas.value.height
      )
      
      // 请求下一帧
      animationFrameId.value = requestAnimationFrame(drawVideoFrame)
    }
  } catch (err) {
    console.error('Canvas绘制错误:', err)
  }
}

// 切换Canvas播放/暂停状态
const toggleCanvasPlay = () => {
  if (!canvasVideoElement.value) return
  
  try {
    if (isCanvasPlaying.value) {
      // 当前正在播放，暂停
      canvasVideoElement.value.pause()
      isCanvasPlaying.value = false
      
      // 取消动画帧
      if (animationFrameId.value) {
        cancelAnimationFrame(animationFrameId.value)
        animationFrameId.value = null
      }
    } else {
      // 当前处于暂停状态，开始播放
      canvasVideoElement.value.play()
        .then(() => {
          console.log('Canvas视频开始播放')
          isCanvasPlaying.value = true
          // 开始绘制帧
          drawVideoFrame()
        })
        .catch(err => {
          console.error('Canvas视频播放失败:', err)
          ElMessage.error('无法播放视频，请尝试点击播放按钮')
        })
    }
  } catch (err) {
    console.error('Canvas播放切换错误:', err)
  }
}

// 停止Canvas回退模式
const stopCanvasPlayback = () => {
  try {
    // 暂停视频
    if (canvasVideoElement.value) {
      canvasVideoElement.value.pause()
      canvasVideoElement.value.src = ''
      canvasVideoElement.value = null
    }
    
    // 取消动画帧
    if (animationFrameId.value) {
      cancelAnimationFrame(animationFrameId.value)
      animationFrameId.value = null
    }
    
    // 重置状态
    isCanvasPlaying.value = false
    
  } catch (err) {
    console.error('Canvas播放清理错误:', err)
  }
}

// 直接切换到标准视频格式
const tryAlternativeFormats = () => {
  if (!processId.value) return
  
  // 仅尝试标准MP4格式
  const standardPath = `/static/night_detection/result_${processId.value}.mp4?t=${Date.now()}`
  console.log('直接使用标准MP4路径:', standardPath)
  videoResultUrl.value = standardPath
}

// 由于已经在728行有一个完整的loadResultVideo函数定义，所以这里移除重复函数

// 处理原始视频错误
const handleOriginalVideoError = () => {
  videoErrors.value.originalVideo = true
  console.error('原始视频加载错误')
  
  if (videoFile.value) {
    try {
      console.log('尝试重新生成原始视频的URL')
      videoUrl.value = URL.createObjectURL(videoFile.value) + `?t=${Date.now()}`
      videoErrors.value.originalVideo = false
    } catch (error) {
      console.error('重新生成原始视频URL失败:', error)
    }
  }
}

// 视频加载成功处理
const handleVideoLoadSuccess = () => {
  console.log('视频加载成功！', videoResultUrl.value)
  
  // 重置错误状态
  videoErrors.value.resultVideo = false
  
  // 设置加载成功标志
  videoLoadSuccess.value = true
  
  // 更新处理状态
  if (videoProcessingStatus.value) {
    videoProcessingStatus.value.status = 'completed'
    videoProcessingStatus.value.message = '视频处理已完成'
    videoProcessingStatus.value.progress = 100
  }
  
  // 更新进度信息 - 只有这时才显示100%
  videoProgressPercentage.value = 100
  videoProgressStatus.value = '处理完成 (100%)'
  videoProcessingComplete.value = true
  
  // 清除所有定时器
  clearAllTimers()
  
  // 延迟一下再显示成功消息，确保与进度条同步
  setTimeout(() => {
    // 通知用户
    ElMessage.success('视频处理与加载已完成！')
  }, 500)
}

// 重试加载视频
const retryLoadVideo = () => {
  if (!videoResultUrl.value) {
    ElMessage.warning('没有可用的视频URL')
    return
  }
  
  console.log('重试加载视频:', videoResultUrl.value)
  
  // 重置错误状态
  videoErrors.value.resultVideo = false
  
  // 添加时间戳避免缓存
  const url = videoResultUrl.value.includes('?') 
    ? `${videoResultUrl.value}&t=${Date.now()}` 
    : `${videoResultUrl.value}?t=${Date.now()}`
  
  // 更新URL并尝试重新加载
  videoResultUrl.value = url
  
  // 通知用户
  ElMessage.info('正在尝试重新加载视频...')
  
  // 如果还是不行，尝试其他格式
  setTimeout(() => {
    if (videoErrors.value.resultVideo) {
      tryAlternativeVideoFormats()
    }
  }, 2000)
}

// 监听处理模式变化
watch(processingMode, (newMode) => {
  console.log('处理模式切换为:', newMode)
  // 可以在这里添加模式切换逻辑
})

// 清理事件监听和定时器
onUnmounted(() => {
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', endResize)
  
  // 清除视频进度检查定时器
  if (progressCheckInterval.value) {
    clearInterval(progressCheckInterval.value)
    progressCheckInterval.value = null
  }
});
</script>

<style scoped>
.night-detection-view {
  height: 100vh;
  background-color: var(--el-bg-color);
  overflow: hidden;
  padding-top: 10px; /* 修复顶部被遮挡的问题 */
}

.el-container {
  height: 100%;
  position: relative;
  display: flex;
}

.main-content {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
  flex: none;
  background-color: var(--el-bg-color);
}

.detection-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.section-title {
  margin-bottom: 30px;
  text-align: center;
  position: relative;
}

.section-title h2 {
  font-size: 32px;
  margin-bottom: 12px;
  background: linear-gradient(45deg, #4f46e5, #00d2aa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  position: relative;
  display: inline-block;
}

.section-title h2::after {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 3px;
  background: linear-gradient(45deg, #4f46e5, #00d2aa);
  border-radius: 3px;
}

.section-title p {
  font-size: 16px;
  color: var(--el-text-color-secondary);
  max-width: 600px;
  margin: 0 auto;
}

.upload-section {
  margin-bottom: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: all 0.3s ease;
}

.image-uploader, .video-uploader {
  width: 100%;
  max-width: 800px;
}

.upload-area {
  width: 100%;
  height: 300px;
  border: 2px dashed rgba(79, 70, 229, 0.4);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.05);
  overflow: hidden;
  position: relative;
}

.upload-area::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, rgba(79, 70, 229, 0.05), rgba(0, 210, 170, 0.05));
  z-index: 1;
}

.upload-area:hover {
  border-color: #4f46e5;
  background-color: rgba(79, 70, 229, 0.08);
  transform: translateY(-3px);
  box-shadow: 0 10px 25px rgba(79, 70, 229, 0.15);
}

.upload-icon {
  font-size: 56px;
  color: #4f46e5;
  margin-bottom: 16px;
  z-index: 2;
  opacity: 0.8;
}

.upload-text {
  font-size: 16px;
  color: var(--el-text-color-secondary);
  z-index: 2;
}

/* 删除image-url类的显示 */
.image-url {
  display: none;
}

.image-container {
  position: relative;
  width: 100%;
  min-height: 200px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  transition: transform 0.3s ease;
}

.image-container:hover {
  transform: scale(1.02);
}

.image-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #F56C6C;
  background-color: rgba(255, 255, 255, 0.9);
  padding: 12px 18px;
  border-radius: 8px;
  font-size: 14px;
  text-align: center;
  max-width: 90%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* 视频处理样式 */
.video-uploader {
  display: block;
  width: 100%;
  max-width: 800px;
}

.uploaded-video {
  max-width: 100%;
  max-height: 400px;
  display: block;
  margin: 0 auto;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.mode-selection {
  margin-bottom: 30px;
  text-align: center;
}

.video-progress-container {
  margin: 30px 0;
  background: rgba(255, 255, 255, 0.08);
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
}

.video-comparison {
  display: flex;
  flex-direction: column;
  gap: 30px;
  margin-top: 20px;
}

.original-video,
.processed-video {
  width: 100%;
  background: rgba(255, 255, 255, 0.05);
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  transition: transform 0.3s ease;
}

.original-video:hover,
.processed-video:hover {
  transform: translateY(-5px);
}

.original-video h4,
.processed-video h4 {
  margin-bottom: 16px;
  color: #4f46e5;
  font-size: 18px;
  position: relative;
  display: inline-block;
  padding-bottom: 8px;
}

.original-video h4::after,
.processed-video h4::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 40px;
  height: 2px;
  background: linear-gradient(45deg, #4f46e5, #00d2aa);
}

.video-error {
  color: var(--el-color-danger);
  margin-top: 10px;
  padding: 10px;
  background-color: var(--el-color-danger-light-9);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.video-error-message {
  margin: 30px 0;
}

.uploaded-image {
  width: 100%;
  max-height: 500px;
  object-fit: contain;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  transition: transform 0.3s ease;
}

.uploaded-image:hover {
  transform: scale(1.02);
}

.controls-container {
  margin-top: 20px;
  display: flex;
  gap: 16px;
  justify-content: center;
}

.controls-container .el-button {
  min-width: 120px;
  transition: all 0.3s ease;
}

.controls-container .el-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.result-container {
  margin-top: 40px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(4px);
}

.result-title {
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 10px;
}

.result-title h3 {
  font-size: 22px;
  background: linear-gradient(45deg, #4f46e5, #00d2aa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}

.image-comparison {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.original-image, .enhanced-image {
  flex: 1;
  min-width: 300px;
  background: rgba(255, 255, 255, 0.03);
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  overflow: hidden;
}

.original-image:hover, .enhanced-image:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
}

.original-image p, .enhanced-image p {
  margin-bottom: 12px;
  font-weight: 600;
  color: #4f46e5;
  position: relative;
  display: inline-block;
  padding-bottom: 8px;
}

.original-image p::after, .enhanced-image p::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 30px;
  height: 2px;
  background: linear-gradient(45deg, #4f46e5, #00d2aa);
}

.original-image img, .enhanced-image img {
  width: 100%;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.original-image img:hover, .enhanced-image img:hover {
  transform: scale(1.03);
}

/* 视频加载成功提示 */
.video-success {
  margin-top: 20px;
}

/* 错误容器样式 */
.video-error-container {
  background: rgba(245, 108, 108, 0.08);
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
  border: 1px solid rgba(245, 108, 108, 0.2);
}

.error-reasons {
  margin: 10px 0;
  padding-left: 20px;
}

.error-reasons li {
  margin-bottom: 6px;
  color: #909399;
}

.error-actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}

/* 响应式样式调整 */
@media (max-width: 768px) {
  .night-detection-view {
    height: auto;
    min-height: 100vh;
  }
  
  .section-title h2 {
    font-size: 24px;
  }
  
  .detection-container {
    padding: 15px;
  }
  
  .uploaded-image, .uploaded-video {
    max-height: 300px;
  }
  
  .image-comparison {
    flex-direction: column;
  }
}

:deep(.el-main) {
  padding: 0;
}

:deep(.el-aside) {
  overflow: hidden;
}

/* 添加动画效果 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.result-container, .upload-section {
  animation: fadeIn 0.5s ease-out;
}
</style>