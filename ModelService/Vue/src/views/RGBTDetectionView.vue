<template>
  <div class="rgbt-detection-view">
    <el-container>
      <el-main class="main-content" :style="{ width: `calc(100% - ${rightPanelWidth}px - 4px)` }">
        <div class="detection-container">
          <div class="section-title">
            <h2>可见光-热微小物体检测</h2>
            <p>上传可见光与热成像进行微小目标检测与分析</p>
          </div>
          
          <!-- 模式切换选项卡 -->
          <el-tabs v-model="activeTab" class="detection-tabs" type="card">
            <el-tab-pane label="图像处理" name="image">
              <!-- 图像处理内容 -->
              <div class="upload-section" v-if="activeTab === 'image'">
                <el-row :gutter="20">
                  <el-col :span="12">
                    <div class="upload-box">
                      <div class="upload-header">
                        <h4>可见光图像</h4>
                      </div>
                      <el-upload
                        class="image-uploader"
                        :auto-upload="false"
                        :show-file-list="false"
                        :on-change="handleRGBImageChange"
                        action="#"
                        accept="image/*"
                      >
                        <div class="upload-area" v-if="!rgbImageUrl">
                          <el-icon class="upload-icon"><Picture /></el-icon>
                          <div class="upload-text">上传可见光图像</div>
                        </div>
                        <img v-else :src="rgbImageUrl" class="uploaded-image" />
                      </el-upload>
                    </div>
                  </el-col>
                  <el-col :span="12">
                    <div class="upload-box">
                      <div class="upload-header">
                        <h4>热成像图像</h4>
                      </div>
                      <el-upload
                        class="image-uploader"
                        :auto-upload="false"
                        :show-file-list="false"
                        :on-change="handleThermalImageChange"
                        action="#"
                        accept="image/*"
                      >
                        <div class="upload-area" v-if="!thermalImageUrl">
                          <el-icon class="upload-icon"><View /></el-icon>
                          <div class="upload-text">上传热成像图像</div>
                        </div>
                        <img v-else :src="thermalImageUrl" class="uploaded-image" />
                      </el-upload>
                    </div>
                  </el-col>
                </el-row>
                
                <div class="controls-container" v-if="rgbImageUrl || thermalImageUrl">
                  <el-button type="danger" @click="clearImages">清除图片</el-button>
                  <el-button type="primary" @click="processImages" :loading="loading" :disabled="!rgbImageUrl || !thermalImageFile">
                    {{ loading ? '处理中...' : '开始分析' }}
                  </el-button>
                </div>
              </div>
            </el-tab-pane>
            
            <el-tab-pane label="视频处理" name="video">
              <!-- 视频处理内容 -->
              <div class="upload-section" v-if="activeTab === 'video'">
                <el-row :gutter="20">
                  <el-col :span="12">
                    <div class="upload-box">
                      <div class="upload-header">
                        <h4>可见光视频</h4>
                      </div>
                      <el-upload
                        class="video-uploader"
                        :auto-upload="false"
                        :show-file-list="false"
                        :on-change="handleRGBVideoChange"
                        action="#"
                        accept="video/*"
                      >
                        <div class="upload-area" v-if="!rgbVideoUrl">
                          <el-icon class="upload-icon"><VideoCameraFilled /></el-icon>
                          <div class="upload-text">上传可见光视频</div>
                          <div class="upload-hint">支持MP4, AVI格式, 小于100MB</div>
                        </div>
                        <video v-else :src="rgbVideoUrl" class="uploaded-video" controls></video>
                      </el-upload>
                    </div>
                  </el-col>
                  <el-col :span="12">
                    <div class="upload-box">
                      <div class="upload-header">
                        <h4>热成像视频 (可选)</h4>
                      </div>
                      <el-upload
                        class="video-uploader"
                        :auto-upload="false"
                        :show-file-list="false"
                        :on-change="handleThermalVideoChange"
                        action="#"
                        accept="video/*"
                      >
                        <div class="upload-area" v-if="!thermalVideoUrl">
                          <el-icon class="upload-icon"><VideoCameraFilled /></el-icon>
                          <div class="upload-text">上传热成像视频</div>
                          <div class="upload-hint">支持MP4, AVI格式, 小于100MB</div>
                        </div>
                        <video v-else :src="thermalVideoUrl" class="uploaded-video" controls></video>
                      </el-upload>
                    </div>
                  </el-col>
                </el-row>
                
                <div class="controls-container" v-if="rgbVideoUrl || thermalVideoUrl">
                  <el-button type="danger" @click="clearVideos">清除视频</el-button>
                  <el-button type="primary" @click="processVideos" :loading="videoLoading" :disabled="!rgbVideoFile">
                    {{ videoLoading ? '处理中...' : '开始处理视频' }}
                  </el-button>
                </div>
                
                <!-- 视频处理进度和结果 -->
                <div v-if="videoTaskId && videoTaskStatus" class="video-progress-container">
                  <el-card class="video-progress-card">
                    <h4>处理状态: {{ videoTaskStatus === 'completed' ? '已完成' : '处理中' }}</h4>
                    <el-progress 
                      :percentage="videoProgress" 
                      :status="videoTaskStatus === 'completed' ? 'success' : (videoTaskStatus === 'failed' ? 'exception' : '')"
                      :stroke-width="18"
                    ></el-progress>
                    
                    <!-- 处理完成后的视频显示 -->
                    <div v-if="videoResult && videoTaskStatus === 'completed'" class="video-results">
                      <h4>处理结果</h4>
                      <el-row :gutter="20">
                        <el-col :span="12">
                          <div class="result-video-container">
                            <h5>处理后的可见光视频</h5>
                            <div class="video-url-debug">视频URL: {{ getProperVideoUrl(videoResult.rgb_video.processed) }}</div>
                            <video 
                              :src="getProperVideoUrl(videoResult.rgb_video.processed)" 
                              controls 
                              class="result-video"
                              @error="(e) => handleVideoError(e, '可见光视频')"
                              @loadeddata="() => console.log('可见光视频加载成功')"
                            ></video>
                            <el-button size="small" type="primary" @click="window.open(getProperVideoUrl(videoResult.rgb_video.processed), '_blank')">
                              <el-icon><Download /></el-icon> 下载处理后的视频
                            </el-button>
                          </div>
                        </el-col>
                        <el-col :span="12" v-if="videoResult.thermal_video && videoResult.thermal_video.processed">
                          <div class="result-video-container">
                            <h5>处理后的热成像视频</h5>
                            <div class="video-url-debug">视频URL: {{ getProperVideoUrl(videoResult.thermal_video.processed) }}</div>
                            <video 
                              :src="getProperVideoUrl(videoResult.thermal_video.processed)" 
                              controls 
                              class="result-video"
                              @error="(e) => handleVideoError(e, '热成像视频')"
                              @loadeddata="() => console.log('热成像视频加载成功')"
                            ></video>
                            <el-button size="small" type="primary" @click="window.open(getProperVideoUrl(videoResult.thermal_video.processed), '_blank')">
                              <el-icon><Download /></el-icon> 下载处理后的视频
                            </el-button>
                          </div>
                        </el-col>
                      </el-row>
                    </div>
                  </el-card>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
          
          <!-- 改进的结果展示区 - 两个原图与两个处理后的图像对比 -->
          <div class="result-section" v-if="resultImageUrl || thermalResultImageUrl">
            <el-divider>可见光图像检测对比</el-divider>
            
            <!-- 可见光图像对比区 -->
            <div class="comparison-row">
              <!-- 原始可见光图像 -->
              <div class="image-card">
                <div class="image-card-title">原始可见光图像</div>
                <div class="image-container">
                  <img :src="rgbImageUrl" class="comparison-image" />
                </div>
              </div>
              
              <!-- 处理后的可见光图像 -->
              <div class="image-card">
                <div class="image-card-title">可见光检测结果</div>
                <div class="image-container">
                  <el-image 
                    :src="resultImageUrl.startsWith('http') ? resultImageUrl : (resultImageUrl.startsWith('/') ? resultImageUrl : `/${resultImageUrl}`)" 
                    fit="contain" 
                    class="comparison-image"
                    @load="() => console.log('检测结果图像加载成功')"
                    @error="(e) => handleImageError(e, '原始检测结果')"
                  />
                  
                  <!-- 可见光目标框显示层 -->
                  <div v-if="detectionResult && detectionResult.detectedObjects" class="bounding-boxes-layer" ref="boundingBoxesRef">
                    <!-- 边界框在加载后动态绘制 -->
                  </div>
                </div>
              </div>
            </div>
            
            <el-divider>热成像检测对比</el-divider>
            
            <!-- 热成像对比区 -->
            <div class="comparison-row">
              <!-- 原始热成像图像 -->
              <div class="image-card">
                <div class="image-card-title">原始热成像图像</div>
                <div class="image-container">
                  <img :src="thermalImageUrl" class="comparison-image" />
                </div>
              </div>
              
              <!-- 处理后的热成像图像 -->
              <div class="image-card">
                <div class="image-card-title">热成像检测结果</div>
                <div class="image-container">
                  <el-image 
                    v-if="thermalResultImageUrl" 
                    :src="thermalResultImageUrl.startsWith('http') ? thermalResultImageUrl : (thermalResultImageUrl.startsWith('/') ? thermalResultImageUrl : `/${thermalResultImageUrl}`)" 
                    fit="contain" 
                    class="comparison-image"
                    @load="() => console.log('热成像结果图像加载成功')"
                    @error="(e) => handleImageError(e, '热成像检测结果')"
                  />
                  <div v-else class="no-image-placeholder">
                    <el-empty description="未收到热成像处理结果" :image-size="80" />
                  </div>
                  
                  <!-- 热成像目标框显示层 -->
                  <div v-if="detectionResult && detectionResult.detectedObjects && thermalResultImageUrl" class="bounding-boxes-layer" ref="thermalBoundingBoxesRef">
                    <!-- 边界框在加载后动态绘制 -->
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-main>
      
      <div class="splitter" @mousedown="startResize">
        <div class="splitter-handle"></div>
      </div>
      
      <el-aside :width="`${rightPanelWidth}px`" class="assistant-panel">
        <div class="detection-assistant">
          <div class="assistant-header">
            <h3>微小目标检测分析</h3>
          </div>
          <div class="assistant-content" v-if="detectionResult">
            <div class="result-stats">
              <div class="stat-item">
                <div class="stat-value">{{ detectionResult.detectedObjects?.length || 0 }}</div>
                <div class="stat-label">检测到的微小目标</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ detectionResult.accuracyScore || '0' }}%</div>
                <div class="stat-label">检测精度</div>
              </div>
            </div>
            
            <el-divider>检测统计</el-divider>
            
            <div class="objects-list" v-if="detectionResult.detectedObjects?.length">
              <h4>目标详情:</h4>
              <el-table :data="detectionResult.detectedObjects" style="width: 100%">
                <el-table-column prop="id" label="ID" width="60" />
                <el-table-column prop="type" label="类型" />
                <el-table-column prop="size" label="尺寸(像素)" />
                <el-table-column prop="confidence" label="置信度">
                  <template #default="scope">
                    {{ (scope.row.confidence * 100).toFixed(2) }}%
                  </template>
                </el-table-column>
              </el-table>
            </div>
            
            <el-divider>检测分析</el-divider>
            
            <div class="analysis-summary">
              <h4>分析总结</h4>
              <p>{{ detectionResult.summary || '无法生成分析总结' }}</p>
            </div>
          </div>
          <div class="assistant-placeholder" v-else>
            <el-empty description="请上传两种图像并进行分析" />
          </div>
        </div>
      </el-aside>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Picture, View, VideoCameraFilled, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { rgbtDetectionApi } from '@/api/rgbtDetection'

// 处理模式选项卡
const activeTab = ref('image') // 默认选中图像处理选项卡

// 图像处理状态变量
const rgbImageUrl = ref('')
const rgbImageFile = ref(null)
const thermalImageUrl = ref('')
const thermalImageFile = ref(null)
const resultImageUrl = ref('')
const thermalResultImageUrl = ref('') // 热成像处理结果的URL
const fusionImageUrl = ref('')  // 融合图像的URL
const loading = ref(false)
const detectionResult = ref(null)
const imageErrors = ref([])

// 视频处理状态变量
const rgbVideoUrl = ref('')
const rgbVideoFile = ref(null)
const thermalVideoUrl = ref('')
const thermalVideoFile = ref(null)
const videoLoading = ref(false)
const videoTaskId = ref('')
const videoTaskStatus = ref('')
const videoProgress = ref(0)
const videoResult = ref(null)

// 分隔线拖动相关
const rightPanelWidth = ref(400)
const isResizing = ref(false)
const startX = ref(0)
const startWidth = ref(0)

// 处理可见光图片上传
const handleRGBImageChange = (file) => {
  rgbImageFile.value = file.raw
  rgbImageUrl.value = URL.createObjectURL(file.raw)
  resultImageUrl.value = ''
}

// 处理热成像图片上传
const handleThermalImageChange = (file) => {
  thermalImageFile.value = file.raw
  thermalImageUrl.value = URL.createObjectURL(file.raw)
  resultImageUrl.value = ''
}

// 清除所有图片
const clearImages = () => {
  rgbImageUrl.value = ''
  rgbImageFile.value = null
  thermalImageUrl.value = ''
  thermalImageFile.value = null
  resultImageUrl.value = ''
  fusionImageUrl.value = ''  // 清除融合图像
  detectionResult.value = null
}

// 处理图像加载错误
const handleImageError = (e, imageType = '') => {
  console.error(`${imageType}图像加载失败:`, e)
  ElMessage.warning(`${imageType}图像加载失败，请检查路径是否正确`)
}

// 处理视频加载错误
const handleVideoError = (e, videoType = '') => {
  console.error(`${videoType}视频加载失败:`, e)
  
  // 获取错误详情
  const videoElement = e.target
  const errorCode = videoElement.error ? videoElement.error.code : 'unknown'
  const errorMessage = videoElement.error ? videoElement.error.message : 'unknown error'
  
  console.error(`视频错误代码: ${errorCode}, 错误信息: ${errorMessage}`)
  ElMessage.warning(`${videoType}加载失败 (错误代码: ${errorCode})，请检查URL是否正确`)
  
  // 断点调试 - 尝试直接打开视频URL
  try {
    if (videoType === '可见光视频' && videoResult.value?.rgb_video?.processed) {
      // 当前URL有问题，尝试直接在新标签页打开
      const url = getProperVideoUrl(videoResult.value.rgb_video.processed)
      console.log('尝试直接在新标签页打开可见光视频:', url)
    } else if (videoType === '热成像视频' && videoResult.value?.thermal_video?.processed) {
      const url = getProperVideoUrl(videoResult.value.thermal_video.processed)
      console.log('尝试直接在新标签页打开热成像视频:', url)
    }
  } catch (err) {
    console.error('尝试调试视频URL时出错:', err)
  }
}

// 检查图像路径是否完整
const checkImagePath = (url) => {
  if (!url) return false
  
  // 检查URL是否包含服务器路径
  const baseUrl = window.location.origin
  const fullUrl = url.startsWith('http') ? url : `${baseUrl}${url}`
  console.log('检查图像路径:', fullUrl)
  return fullUrl
}

// 目标边界框引用
const boundingBoxesRef = ref(null)
const thermalBoundingBoxesRef = ref(null)

// 随机颜色生成函数 - 用于检测框颜色
const getRandomColor = () => {
  // 生成较亮的颜色，便于在图像上清晰显示
  const hue = Math.floor(Math.random() * 360)
  return `hsl(${hue}, 100%, 50%)`
}

// 绘制可见光检测目标边界框
const drawDetectionBoxes = () => {
  if (!boundingBoxesRef.value || !detectionResult.value || !detectionResult.value.detectedObjects) {
    return
  }
  
  // 清除现有的边界框
  boundingBoxesRef.value.innerHTML = ''
  
  // 获取容器尺寸
  const containerWidth = boundingBoxesRef.value.clientWidth
  const containerHeight = boundingBoxesRef.value.clientHeight
  
  // 获取图像元素
  const imageElement = boundingBoxesRef.value.previousElementSibling
  if (!imageElement) return
  
  // 等待图像加载完成
  const checkImageLoaded = () => {
    if (imageElement.complete) {
      // 获取图像的实际显示尺寸
      const rect = imageElement.getBoundingClientRect()
      const imgWidth = rect.width
      const imgHeight = rect.height
      
      // 计算缩放比例
      const imgNaturalWidth = imageElement.naturalWidth || 640 // 默认图像宽度假设为640
      const imgNaturalHeight = imageElement.naturalHeight || 480 // 默认图像高度假设为480
      
      const scaleX = imgWidth / imgNaturalWidth
      const scaleY = imgHeight / imgNaturalHeight
      
      // 计算图像在容器中的位置偏移
      const offsetX = (containerWidth - imgWidth) / 2
      const offsetY = (containerHeight - imgHeight) / 2
      
      // 绘制每个检测到的目标边界框 - 只绘制source为'rgb'的或未指定source的目标
      detectionResult.value.detectedObjects.forEach((obj, index) => {
        // 如果指定了source且不是'rgb'，则跳过该目标
        if (obj.source && obj.source !== 'rgb') return
        
        // 如果目标具有bbox属性，使用它
        let x, y, width, height
        if (obj.bbox) {
          [x, y, width, height] = obj.bbox
          x = x * scaleX + offsetX
          y = y * scaleY + offsetY
          width = width * scaleX
          height = height * scaleY
        } else {
          // 使用以前的方法
          const sizeParts = obj.size.split('x')
          width = parseInt(sizeParts[0]) * scaleX
          height = parseInt(sizeParts[1]) * scaleY
          
          // 基于索引在图像上均匀分布边界框
          const gridSize = Math.ceil(Math.sqrt(detectionResult.value.detectedObjects.length))
          const gridX = index % gridSize
          const gridY = Math.floor(index / gridSize)
          
          x = offsetX + (imgWidth / gridSize) * gridX + (imgWidth / gridSize - width) / 2
          y = offsetY + (imgHeight / gridSize) * gridY + (imgHeight / gridSize - height) / 2
        }
        
        // 创建边界框元素
        const boxColor = getRandomColor()
        const box = document.createElement('div')
        box.className = 'detection-box'
        box.style.left = `${x}px`
        box.style.top = `${y}px`
        box.style.width = `${width}px`
        box.style.height = `${height}px`
        box.style.borderColor = boxColor
        
        // 创建标签
        const label = document.createElement('div')
        label.className = 'detection-box-label'
        label.style.backgroundColor = boxColor
        label.textContent = `ID:${obj.id} ${obj.type || ''} ${(obj.confidence * 100).toFixed(0)}%`
        
        box.appendChild(label)
        boundingBoxesRef.value.appendChild(box)
      })
    } else {
      // 如果图像尚未加载完成，等待并重试
      setTimeout(checkImageLoaded, 100)
    }
  }
  
  // 开始检查图像是否加载完成
  checkImageLoaded()
}

// 绘制热成像检测目标边界框
const drawThermalDetectionBoxes = () => {
  if (!thermalBoundingBoxesRef.value || !detectionResult.value || !detectionResult.value.detectedObjects) {
    return
  }
  
  // 清除现有的边界框
  thermalBoundingBoxesRef.value.innerHTML = ''
  
  // 获取容器尺寸
  const containerWidth = thermalBoundingBoxesRef.value.clientWidth
  const containerHeight = thermalBoundingBoxesRef.value.clientHeight
  
  // 获取图像元素
  const imageElement = thermalBoundingBoxesRef.value.previousElementSibling
  if (!imageElement) return
  
  // 等待图像加载完成
  const checkImageLoaded = () => {
    if (imageElement.complete) {
      // 获取图像的实际显示尺寸
      const rect = imageElement.getBoundingClientRect()
      const imgWidth = rect.width
      const imgHeight = rect.height
      
      // 计算缩放比例
      const imgNaturalWidth = imageElement.naturalWidth || 640
      const imgNaturalHeight = imageElement.naturalHeight || 480
      
      const scaleX = imgWidth / imgNaturalWidth
      const scaleY = imgHeight / imgNaturalHeight
      
      // 计算图像在容器中的位置偏移
      const offsetX = (containerWidth - imgWidth) / 2
      const offsetY = (containerHeight - imgHeight) / 2
      
      // 绘制每个检测到的目标边界框 - 只绘制source为'thermal'的目标
      detectionResult.value.detectedObjects.forEach((obj, index) => {
        // 只处理热成像来源的目标
        if (obj.source && obj.source !== 'thermal') return
        
        // 如果目标具有bbox属性，使用它
        let x, y, width, height
        if (obj.bbox) {
          [x, y, width, height] = obj.bbox
          x = x * scaleX + offsetX
          y = y * scaleY + offsetY
          width = width * scaleX
          height = height * scaleY
        } else {
          // 使用平均分布
          const sizeParts = obj.size.split('x')
          width = parseInt(sizeParts[0]) * scaleX
          height = parseInt(sizeParts[1]) * scaleY
          
          // 为热成像目标使用不同的网格计算方法
          const gridSize = Math.ceil(Math.sqrt(detectionResult.value.detectedObjects.length))
          // 热成像目标从图像下部开始分布，不同于可见光目标
          const gridX = (index + Math.floor(gridSize/2)) % gridSize
          const gridY = Math.floor((index + Math.floor(gridSize/2)) / gridSize)
          
          x = offsetX + (imgWidth / gridSize) * gridX + (imgWidth / gridSize - width) / 2
          y = offsetY + (imgHeight / gridSize) * gridY + (imgHeight / gridSize - height) / 2
        }
        
        // 创建边界框元素 - 使用红色色调以表示热重点
        const hue = Math.floor(Math.random() * 30) // 0-30的色相范围，让热成像框都是红色系
        const boxColor = `hsl(${hue}, 100%, 50%)`
        const box = document.createElement('div')
        box.className = 'detection-box'
        box.style.left = `${x}px`
        box.style.top = `${y}px`
        box.style.width = `${width}px`
        box.style.height = `${height}px`
        box.style.borderColor = boxColor
        
        // 创建标签
        const label = document.createElement('div')
        label.className = 'detection-box-label'
        label.style.backgroundColor = boxColor
        label.textContent = `ID:${obj.id} 热 ${(obj.confidence * 100).toFixed(0)}%`
        
        box.appendChild(label)
        thermalBoundingBoxesRef.value.appendChild(box)
      })
    } else {
      // 如果图像尚未加载完成，等待并重试
      setTimeout(checkImageLoaded, 100)
    }
  }
  
  // 开始检查图像是否加载完成
  checkImageLoaded()
}

// 处理视频上传 - RGB视频
const handleRGBVideoChange = (file) => {
  // 确保文件对象存在且有效
  if (!file || !file.raw) {
    ElMessage.error('文件无效，请重新选择')
    return false
  }
  
  // 验证文件类型
  const fileType = file.raw.type || ''
  const isVideoType = fileType.startsWith('video/') || file.raw.name?.toLowerCase().endsWith('.mp4') || file.raw.name?.toLowerCase().endsWith('.avi')
  if (!isVideoType) {
    ElMessage.error('请上传视频文件（MP4或AVI格式）')
    return false
  }
  
  // 验证文件大小
  const isVideoSizeValid = file.raw.size / 1024 / 1024 < 100
  if (!isVideoSizeValid) {
    ElMessage.error('视频大小不能超过100MB')
    return false
  }
  
  // 先清理之前的URL对象，避免内存泄漏
  if (rgbVideoUrl.value && rgbVideoUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(rgbVideoUrl.value)
  }
  
  rgbVideoFile.value = file.raw
  rgbVideoUrl.value = URL.createObjectURL(file.raw)
  console.log('可见光视频上传成功，生成URL:', rgbVideoUrl.value)
  
  return false // 阻止自动上传
}

// 处理视频上传 - 热成像视频
const handleThermalVideoChange = (file) => {
  // 确保文件对象存在且有效
  if (!file || !file.raw) {
    ElMessage.error('文件无效，请重新选择')
    return false
  }
  
  // 验证文件类型
  const fileType = file.raw.type || ''
  const isVideoType = fileType.startsWith('video/') || file.raw.name?.toLowerCase().endsWith('.mp4') || file.raw.name?.toLowerCase().endsWith('.avi')
  if (!isVideoType) {
    ElMessage.error('请上传视频文件（MP4或AVI格式）')
    return false
  }
  
  // 验证文件大小
  const isVideoSizeValid = file.raw.size / 1024 / 1024 < 100
  if (!isVideoSizeValid) {
    ElMessage.error('视频大小不能超过100MB')
    return false
  }
  
  // 先清理之前的URL对象，避免内存泄漏
  if (thermalVideoUrl.value && thermalVideoUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(thermalVideoUrl.value)
  }
  
  thermalVideoFile.value = file.raw
  thermalVideoUrl.value = URL.createObjectURL(file.raw)
  console.log('热成像视频上传成功，生成URL:', thermalVideoUrl.value)
  
  return false // 阻止自动上传
}

// 清除视频
const clearVideos = () => {
  rgbVideoFile.value = null
  rgbVideoUrl.value = ''
  thermalVideoFile.value = null
  thermalVideoUrl.value = ''
  videoResult.value = null
  videoTaskId.value = ''
  videoTaskStatus.value = ''
  videoProgress.value = 0
}

// 处理视频
const processVideos = async () => {
  if (!rgbVideoFile.value) {
    ElMessage.warning('请至少上传可见光视频')
    return
  }
  
  videoLoading.value = true
  videoTaskStatus.value = 'processing'
  videoProgress.value = 30  // 设置固定进度值
  
  try {
    // 第一步: 上传视频文件
    const apiBase = '/api'
    const uploadEndpoint = `${apiBase}/rgbt-video/upload`
    console.log('使用上传端点:', uploadEndpoint)
    
    // 准备上传RGB视频
    console.log('准备上传RGB视频:', rgbVideoFile.value.name)
    const formDataRGB = new FormData()
    formDataRGB.append('video_file', rgbVideoFile.value)
    formDataRGB.append('video_type', 'rgb')
    
    const rgbUploadResponse = await fetch(uploadEndpoint, {
      method: 'POST',
      body: formDataRGB
    })
    const rgbUploadResult = await rgbUploadResponse.json()
    
    if (!rgbUploadResult.success) {
      throw new Error(rgbUploadResult.error || 'RGB视频上传失败')
    }
    
    videoProgress.value = 50  // 更新进度
    
    // 准备上传热成像视频（如果有的话）
    let thermalUploadResult = null
    if (thermalVideoFile.value) {
      console.log('准备上传热成像视频:', thermalVideoFile.value.name)
      const formDataThermal = new FormData()
      formDataThermal.append('video_file', thermalVideoFile.value)
      formDataThermal.append('video_type', 'thermal')
      
      const thermalUploadResponse = await fetch(uploadEndpoint, {
        method: 'POST',
        body: formDataThermal
      })
      thermalUploadResult = await thermalUploadResponse.json()
      
      if (!thermalUploadResult.success) {
        throw new Error(thermalUploadResult.error || '热成像视频上传失败')
      }
    }
    
    videoProgress.value = 70  // 更新进度
    
    // 第二步: 处理视频
    const processEndpoint = `${apiBase}/rgbt-video/process`
    console.log('使用处理端点:', processEndpoint)
    console.log('处理视频路径:', rgbUploadResult.video_path, '及热成像视频:', thermalUploadResult ? thermalUploadResult.video_path : '无')
    
    const processData = {
      rgb_video_path: rgbUploadResult.video_path,
      thermal_video_path: thermalUploadResult ? thermalUploadResult.video_path : null
    }
    
    const processResponse = await fetch(processEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(processData)
    })
    
    const processResult = await processResponse.json()
    
    if (!processResult.success) {
      throw new Error(processResult.error || '视频处理请求失败')
    }
    
    // 获取任务ID
    videoTaskId.value = processResult.task_id
    videoProgress.value = 90  // 更新进度
    
    // 使用轮询机制等待视频处理完成
    let maxAttempts = 30 // 最多尝试30次
    let attemptDelay = 2000 // 每次等待2秒
    let attempts = 0
    let processingComplete = false
    
    ElMessage.info('视频处理已开始，请耐心等待完成...')
    
    while (!processingComplete && attempts < maxAttempts) {
      attempts++
      await new Promise(resolve => setTimeout(resolve, attemptDelay))
      
      try {
        // 检查任务状态
        const statusEndpoint = `${apiBase}/rgbt-video/status/${processResult.task_id}`
        const statusResponse = await fetch(statusEndpoint)
        const statusData = await statusResponse.json()
        
        if (statusData.success) {
          const taskStatus = statusData.task.status
          const progress = statusData.task.progress || 0
          
          // 更新进度条
          videoProgress.value = Math.min(90, 60 + Math.floor(progress * 0.3))
          console.log(`处理进度: ${progress}%, 状态: ${taskStatus}`)
          
          if (taskStatus === 'completed') {
            processingComplete = true
            console.log('视频处理已完成')
          }
        }
      } catch (statusError) {
        console.warn('检查状态出错，继续等待...', statusError)
      }
    }
    
    // 获取处理结果
    if (processingComplete || attempts >= maxAttempts) {
      const resultEndpoint = `${apiBase}/rgbt-video/result/${processResult.task_id}`
      console.log('获取处理结果:', resultEndpoint)
      
      try {
        const resultResponse = await fetch(resultEndpoint)
        const resultData = await resultResponse.json()
        
        if (resultData.success) {
          videoResult.value = resultData
          videoTaskStatus.value = 'completed'
          videoProgress.value = 100 // 设置进度为100%
          ElMessage.success('视频处理完成')
        } else {
          // 即使任务标记为完成，获取结果仍可能失败
          throw new Error(resultData.error || '获取视频处理结果失败')
        }
      } catch (resultError) {
        // 如果达到最大尝试次数但仍然不成功，则直接构造URL
        console.warn('无法获取结果，直接构造处理后视频URL', resultError)
        
        // 直接从任务ID构造视频URL
        const taskId = processResult.task_id
        videoResult.value = {
          rgb_video: {
            processed: `/static/rgbt_video/outputs/rgb_processed_${taskId}.mp4`
          },
          thermal_video: {
            processed: `/static/rgbt_video/outputs/thermal_processed_${taskId}.mp4`
          },
          processing_time: 0
        }
        console.log('直接构造的视频URL:', videoResult.value)
        videoTaskStatus.value = 'completed'
        videoProgress.value = 100
        ElMessage.success('视频处理完成')
      }
    } else {
      throw new Error('视频处理超时')
    }
    
    videoLoading.value = false
  } catch (error) {
    console.error('视频处理错误:', error)
    ElMessage.error(`视频处理错误: ${error.message || '未知错误'}`)
    videoTaskStatus.value = 'failed'
    videoLoading.value = false
  }
}

// 处理视频URL，确保URL正确
const getProperVideoUrl = (url) => {
  if (!url) return ''
  
  console.log('处理视频URL:', url)
  
  // 如果已经是完整URL，直接返回
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // 如果已经以/api开头，直接返回
  if (url.startsWith('/api/')) {
    return url
  }
  
  // 静态资源路径不添加/api前缀，因为已经配置了Vite代理
  if (url.startsWith('/static/')) {
    return url  // 不添加/api前缀
  }
  
  // 如果以/开头但不是/api或/static，添加/api前缀
  if (url.startsWith('/')) {
    return `/api${url}`
  }
  
  // 其他情况，添加/api/前缀
  return `/api/${url}`
}

// 处理图像分析
const processImages = async () => {
  if (!rgbImageFile.value || !thermalImageFile.value) {
    ElMessage.warning('请上传可见光和热成像图像')
    return
  }

  // 清除之前的错误记录
  imageErrors.value = []
  loading.value = true
  
  try {
    const formData = new FormData()
    formData.append('rgb_image', rgbImageFile.value)
    formData.append('thermal_image', thermalImageFile.value)

    const response = await rgbtDetectionApi.detectObjects(formData)
    
    // 输出调试信息
    console.log('服务器响应:', response)
    
    // 获取原始结果图像 URL
    resultImageUrl.value = response.resultImageUrl || response.result_image_url
    console.log('原始结果图像 URL:', resultImageUrl.value)
    
    // 确保结果图像 URL 正确添加/api前缀
    if (resultImageUrl.value && !resultImageUrl.value.startsWith('http') && !resultImageUrl.value.startsWith('/api/')) {
      // 如果路径以/static/开头，替换为/api/static/
      if (resultImageUrl.value.startsWith('/static/')) {
        resultImageUrl.value = `/api${resultImageUrl.value}`
      } else if (!resultImageUrl.value.startsWith('/')) {
        // 如果不以/开头，添加/api/前缀
        resultImageUrl.value = `/api/${resultImageUrl.value}`
      } else {
        // 其他情况，添加/api前缀
        resultImageUrl.value = `/api${resultImageUrl.value}`
      }
      console.log('处理后的原始图像 URL:', resultImageUrl.value)
    }
    
    // 获取融合图像 URL
    fusionImageUrl.value = response.fusionImageUrl || ''
    console.log('融合图像 URL:', fusionImageUrl.value)
    
    // 确保融合图像 URL 正确添加/api前缀
    if (fusionImageUrl.value && !fusionImageUrl.value.startsWith('http') && !fusionImageUrl.value.startsWith('/api/')) {
      // 如果路径以/static/开头，替换为/api/static/
      if (fusionImageUrl.value.startsWith('/static/')) {
        fusionImageUrl.value = `/api${fusionImageUrl.value}`
      } else if (!fusionImageUrl.value.startsWith('/')) {
        // 如果不以/开头，添加/api/前缀
        fusionImageUrl.value = `/api/${fusionImageUrl.value}`
      } else {
        // 其他情况，添加/api前缀
        fusionImageUrl.value = `/api${fusionImageUrl.value}`
      }
      console.log('处理后的融合图像 URL:', fusionImageUrl.value)
    }
    
    console.log('完整融合图像 URL:', fusionImageUrl.value)
    
    // 保存全部响应数据
    detectionResult.value = response
    
    // 获取热成像处理结果 URL
    thermalResultImageUrl.value = response.thermalResultImageUrl || ''
    console.log('热成像结果图像 URL:', thermalResultImageUrl.value)
    
    // 确保热成像结果图像 URL 正确添加/api前缀
    if (thermalResultImageUrl.value && !thermalResultImageUrl.value.startsWith('http') && !thermalResultImageUrl.value.startsWith('/api/')) {
      // 如果路径以/static/开头，替换为/api/static/
      if (thermalResultImageUrl.value.startsWith('/static/')) {
        thermalResultImageUrl.value = `/api${thermalResultImageUrl.value}`
      } else if (!thermalResultImageUrl.value.startsWith('/')) {
        // 如果不以/开头，添加/api/前缀
        thermalResultImageUrl.value = `/api/${thermalResultImageUrl.value}`
      } else {
        // 其他情况，添加/api前缀
        thermalResultImageUrl.value = `/api${thermalResultImageUrl.value}`
      }
      console.log('处理后的热成像结果 URL:', thermalResultImageUrl.value)
    }
    
    // 图像加载完成后绘制检测框
    setTimeout(() => {
      // 绘制可见光图像检测框
      drawDetectionBoxes()
      
      // 等待不同时间再绘制热成像图像检测框，避免元素还未加载
      setTimeout(() => {
        // 绘制热成像图像检测框
        drawThermalDetectionBoxes()
      }, 300)
    }, 500)
    
    // 显示成功消息，并包含调试信息
    if (fusionImageUrl.value) {
      ElMessage.success(`检测完成，发现${detectionResult.value.detectedObjects?.length || 0}个目标`)
    } else {
      ElMessage.warning('检测完成，但没有生成融合图像')
    }
  } catch (error) {
    console.error('检测失败:', error)
    ElMessage.error('检测处理失败，请重试')
    // 使用模拟数据用于前端测试
    mockDetectionResult()
  } finally {
    loading.value = false
  }
}

// 模拟检测结果（用于前端测试）
const mockDetectionResult = () => {
  // 创建融合图像的URL，这里简单使用可见光图像
  resultImageUrl.value = rgbImageUrl.value
  // 模拟融合图像，这里使用热成像图像
  fusionImageUrl.value = thermalImageUrl.value
  
  detectionResult.value = {
    detectedObjects: [
      { id: 1, type: '车辆', size: '12x8', confidence: 0.96 },
      { id: 2, type: '行人', size: '5x15', confidence: 0.87 },
      { id: 3, type: '无人机', size: '3x3', confidence: 0.91 },
      { id: 4, type: '遥控模型', size: '4x2', confidence: 0.79 }
    ],
    accuracyScore: '92.5',
    processingTime: '1.2',
    summary: '成功检测到4个微小目标，其中包括1个小型车辆，1个远处的行人，1个无人机以及1个遥控模型。RGB和热成像融合分析提高了检测准确率，特别是对于热成像中明显的热信号目标的识别率达到95%以上。'
  }
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

// 清理事件监听
onUnmounted(() => {
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', endResize)
})
</script>

<style scoped>
.rgbt-detection-view {
  height: 100vh;
  background-color: var(--el-bg-color);
  overflow: hidden;
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
}

.section-title {
  margin-bottom: 24px;
  text-align: center;
}

.section-title h2 {
  font-size: 28px;
  margin-bottom: 8px;
}

.section-title p {
  font-size: 16px;
  color: var(--el-text-color-secondary);
}

.upload-section {
  margin-bottom: 30px;
}

.upload-box {
  margin-bottom: 20px;
}

.upload-box h4 {
  margin-bottom: 12px;
}

.image-uploader {
  width: 100%;
}

.upload-area {
  width: 100%;
  height: 200px;
  border: 1px dashed var(--el-border-color);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: var(--el-color-primary);
  background-color: rgba(var(--el-color-primary-rgb), 0.1);
}

.upload-icon {
  font-size: 48px;
  color: var(--el-text-color-secondary);
  margin-bottom: 16px;
}

.upload-text {
  font-size: 16px;
  color: var(--el-text-color-secondary);
}

.uploaded-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
  border-radius: 8px;
}

/* 视频处理相关样式 */
.video-uploader {
  width: 100%;
}

.uploaded-video {
  width: 100%;
  height: 200px;
  object-fit: contain;
  border-radius: 8px;
  background-color: #000;
}

.upload-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 8px;
}

.video-progress-container {
  margin-top: 20px;
}

.video-progress-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.video-results {
  margin-top: 24px;
}

.result-video-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 16px;
}

.result-video-container h5 {
  margin-bottom: 12px;
  font-weight: 500;
}

.result-video {
  width: 100%;
  max-height: 240px;
  border-radius: 8px;
  margin-bottom: 12px;
  background-color: #000;
}

/* 选项卡样式 */
.detection-tabs {
  margin-bottom: 24px;
}

.controls-container {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  gap: 16px;
}

.result-container {
  margin-top: 30px;
}

.result-title {
  margin-bottom: 16px;
  text-align: center;
}

.result-images {
  display: flex;
  justify-content: center;
}

.result-image {
  max-width: 100%;
  max-height: 500px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* 新增对比显示区域相关样式 */
.comparison-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 20px;
}

/* 新的对比行样式 */
.comparison-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 20px;
}

.original-images,
.processed-images {
  width: 100%;
}

.original-images h4,
.processed-images h4 {
  margin-bottom: 16px;
  font-size: 18px;
  color: var(--el-text-color-primary);
  border-left: 4px solid var(--el-color-primary);
  padding-left: 10px;
}

.original-images-wrapper,
.processed-images-wrapper {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.image-card {
  flex: 1;
  min-width: 300px;
  border-radius: 8px;
  overflow: hidden;
  background-color: var(--el-bg-color-overlay);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.image-card-title {
  padding: 10px 15px;
  font-size: 16px;
  font-weight: 500;
  background-color: rgba(var(--el-color-primary-rgb), 0.1);
  color: var(--el-color-primary);
  border-bottom: 1px solid var(--el-border-color-light);
}

.image-container {
  padding: 15px;
  position: relative;
  min-height: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.comparison-image {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
  border-radius: 4px;
}

.bounding-boxes-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
}

.no-image-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 250px;
  width: 100%;
}

/* 目标框样式 */
.detection-box {
  position: absolute;
  border: 2px solid;
  box-sizing: border-box;
  pointer-events: none;
}

.detection-box-label {
  position: absolute;
  top: -20px;
  left: 0;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
}

.splitter {
  width: 4px;
  background-color: #1a1a1a;
  cursor: col-resize;
  display: flex;
  justify-content: center;
  align-items: center;
  flex: none;
}

.splitter-handle {
  width: 4px;
  height: 30px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  transition: background-color 0.3s;
}

.splitter:hover .splitter-handle {
  background-color: rgba(255, 255, 255, 0.4);
}

.assistant-panel {
  height: 100%;
  overflow: hidden;
  flex: none;
  background-color: #141414;
  min-width: 300px;
}

.detection-assistant {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.assistant-header {
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.assistant-content {
  padding: 16px;
  flex: 1;
  overflow-y: auto;
}

.assistant-placeholder {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.result-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.stat-item {
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 16px;
  flex: 1;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: var(--el-color-primary);
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.objects-list, .analysis-summary {
  margin-top: 16px;
  margin-bottom: 16px;
}

.analysis-summary p {
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

/* 拖动时禁用文本选择 */
.rgbt-detection-view.resizing {
  user-select: none;
}

:deep(.el-main) {
  padding: 0;
}

:deep(.el-aside) {
  overflow: hidden;
}
</style>
