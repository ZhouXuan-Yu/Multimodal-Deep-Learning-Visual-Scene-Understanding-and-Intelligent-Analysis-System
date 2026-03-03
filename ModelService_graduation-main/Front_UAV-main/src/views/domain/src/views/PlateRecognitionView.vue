<template>
  <div class="plate-recognition-view">
    <div class="section-title">
      <h2>车牌智能监控系统</h2>
      <p>上传车牌图片设置目标，智能监控识别视频中的车辆信息</p>
    </div>
    
    <el-card class="main-card">
      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="10" animated />
        <div class="loading-text">正在加载车牌监控系统...</div>
      </div>
      <div v-else class="plate-system-container">
        <div class="monitoring-section">
          <!-- Step 1: 设置目标车牌 -->
          <div class="step-container" :class="{ 'active-step': !targetPlate.plate_no }">
            <div class="step-header">
              <div class="step-number">1</div>
              <h3>设置目标车牌</h3>
            </div>
            <div class="step-content">
              <div v-if="!targetPlate.plate_no" class="upload-container">
                <el-upload
                  class="upload-area"
                  :action="getApiUrl('/plate-monitoring/upload-image')"
                  :on-success="handleMonitorImageSuccess"
                  :on-error="handleUploadError"
                  :before-upload="beforeUpload"
                  :show-file-list="false"
                  accept=".jpg,.jpeg,.png"
                  drag
                >
                  <el-icon class="upload-icon"><Upload /></el-icon>
                  <div class="upload-text">上传包含车牌的图片</div>
                  <div class="upload-tip">系统将识别所有车牌，您可从中选择目标</div>
                </el-upload>
              </div>
              <div v-else class="target-plate-info">
                <el-alert
                  title="已设置目标车牌"
                  type="success"
                  :closable="false"
                  show-icon
                >
                  <template #default>
                    <div class="target-plate-details">
                      <span class="plate-number">{{ targetPlate.plate_no }}</span>
                      <span class="timestamp">设置时间: {{ targetPlate.timestamp }}</span>
                      <el-button type="danger" size="small" @click="clearTargetPlate">清除目标</el-button>
                    </div>
                  </template>
                </el-alert>
              </div>
            </div>
          </div>
          <!-- 步骤2: 车牌选择界面 (当有识别结果但未设置目标时显示) -->
          <div v-if="monitoringResult && !targetPlate.plate_no" class="plate-selection">
            <h3>请选择目标车牌</h3>
            <!-- 添加图片显示区域 -->
            <div class="result-images">
              <div class="original-image">
                <h4>原始图片</h4>
                <el-image 
                  :src="monitoringResult.originalImage" 
                  fit="contain"
                  @error="handleImageError"
                  :preview-src-list="[monitoringResult.originalImage]">
                </el-image>
              </div>
              <div class="processed-image">
                <h4>处理后图片</h4>
                <el-image 
                  :src="monitoringResult.processedImage" 
                  fit="contain"
                  @error="handleImageError"
                  :preview-src-list="[monitoringResult.processedImage]">
                </el-image>
              </div>
            </div>
            <div class="selection-container">
              <el-table :data="monitoringResult.plates || []" border stripe class="plate-table">
                <el-table-column label="车牌号码">
                  <template #default="{row}">
                    <span v-html="formatPlateNumber(row.plate_no, row.plate_type)" class="plate-text"></span>
                  </template>
                </el-table-column>
                <!-- 增加车牌颜色列 -->
                <el-table-column label="车牌颜色" width="100">
                  <template #default="{row}">
                    <el-tag type="info">{{ row.color || '未知' }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="置信度">
                  <template #default="{row}">
                    <el-tag :type="getConfidenceType(row.confidence)" class="confidence-tag">
                      {{ (row.confidence * 100).toFixed(1) }}%
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120">
                  <template #default="{row}">
                    <el-button 
                      type="primary" 
                      size="small"
                      @click="setTargetPlate(row.plate_no, row.color)"
                      class="set-target-btn"
                    >设为目标</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
          
          <!-- 步骤3: 视频监控分析 -->
          <div class="step-container" :class="{ 'active-step': targetPlate.plate_no, 'disabled-step': !targetPlate.plate_no }">
            <div class="step-header">
              <div class="step-number">2</div>
              <h3>上传视频进行监控</h3>
            </div>
            <div class="step-content">
              <div v-if="targetPlate.plate_no">
                <el-upload
                  class="upload-area"
                  :action="getApiUrl('/plate-monitoring/upload-video')"
                  :on-success="handleMonitorVideoSuccess"
                  :on-error="handleUploadError"
                  :before-upload="beforeVideoUpload"
                  :show-file-list="false"
                  accept=".mp4,.avi,.mov"
                  drag
                  :disabled="!targetPlate.plate_no"
                >
                  <el-icon class="upload-icon"><VideoCamera /></el-icon>
                  <div class="upload-text">上传视频进行目标车牌监控</div>
                  <div class="upload-tip">系统将智能检测视频中出现的目标车牌: <strong>{{ targetPlate.plate_no }}</strong></div>
                </el-upload>
              </div>
              <div v-else class="disabled-message">
                <el-alert
                  title="请先设置目标车牌"
                  type="info"
                  :closable="false"
                  show-icon
                >
                  <template #default>
                    完成步骤1后才能进行视频监控分析
                  </template>
                </el-alert>
              </div>
            </div>
          </div>
          <!-- 步骤4: 监控结果 -->
          <div v-if="monitorVideoStatus" class="monitoring-results">
            <h3>车牌监控分析结果</h3>
            
            <!-- 将transition移到外部，包装所有条件渲染元素 -->
            <transition name="fade">
              <div v-if="monitorVideoStatus.status === 'processing'" class="progress-section">
                <el-progress 
                  :percentage="monitorVideoStatus.progress" 
                  :status="monitorVideoStatus.progress === 100 ? 'success' : ''"
                  :stroke-width="20"
                  :format="percent => `${percent}%`"
                  class="progress-bar"
                ></el-progress>
                <div class="progress-message">{{ monitorVideoStatus.message }}</div>
                <div class="progress-details">正在处理车牌监控视频，请稍候...</div>
              </div>
              
              <div v-else-if="monitorVideoStatus.status === 'completed'" class="results-section">
                <el-alert
                  :title="monitorVideoStatus.match_count > 0 ? `成功发现目标车牌 ${targetPlate.plate_no}，共${monitorVideoStatus.match_count}次匹配` : `未在视频中发现目标车牌 ${targetPlate.plate_no}`"
                  :type="monitorVideoStatus.match_count > 0 ? 'success' : 'warning'"
                  :closable="false"
                  show-icon
                  class="result-alert"
                ></el-alert>
                
                <!-- 视频播放区域 -->
                <div class="video-players">
                  <div class="video-container">
                    <h4 class="video-title">处理后的完整视频</h4>
                    <video v-if="monitorVideoStatus.output_video" controls class="player" @error="handleVideoError">
                      <source :src="getProperVideoUrl(monitorVideoStatus.output_video)" type="video/mp4">
                      您的浏览器不支持视频播放
                    </video>
                    <div v-else class="empty-video">
                      <el-icon><VideoCamera /></el-icon>
                      <p>无可用视频</p>
                    </div>
                  </div>
                  
                  <div v-if="monitorVideoStatus.matches_video" class="video-container">
                    <h4 class="video-title">车牌匹配片段</h4>
                    <video controls class="player" @error="handleVideoError">
                      <source :src="getProperVideoUrl(monitorVideoStatus.matches_video)" type="video/mp4">
                      您的浏览器不支持视频播放
                    </video>
                  </div>
                </div>
                
                <!-- 匹配记录表格 -->
                <div v-if="monitorVideoStatus.matches && monitorVideoStatus.matches.length > 0" class="matches-table">
                  <h4 class="table-title">车牌匹配记录</h4>
                  <el-table 
                    :data="monitorVideoStatus.matches" 
                    border 
                    stripe
                    class="detection-table"
                    :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: 'bold' }"
                  >
                    <el-table-column prop="frame_number" label="帧编号" width="90"></el-table-column>
                    <el-table-column prop="plate_number" label="车牌号码" width="120">
                      <template #default="{row}">
                        <span class="plate-label">{{ row.plate_number }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="timestamp" label="时间戳"></el-table-column>
                    <el-table-column label="置信度" width="120">
                      <template #default="{row}">
                        <el-tag :type="getConfidenceType(row.confidence)" class="confidence-tag">
                          {{ (row.confidence * 100).toFixed(1) }}%
                        </el-tag>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </div>
              
              <div v-else-if="monitorVideoStatus.status === 'error'" class="error-section">
                <el-alert
                  title="处理失败"
                  type="error"
                  :description="monitorVideoStatus.message"
                  :closable="false"
                  show-icon
                  class="error-alert"
                ></el-alert>
                <div class="error-suggestion">
                  <p>可能原因:</p>
                  <ul>
                    <li>视频文件格式不支持</li>
                    <li>视频文件损坏</li>
                    <li>服务器处理错误</li>
                  </ul>
                  <p>请尝试上传其他视频文件或稍后重试</p>
                </div>
              </div>
            </transition>
          </div>
        </div>
      </div>
    </el-card>
    
    <div class="feature-section">
      <h2 class="feature-title">系统功能</h2>
      <div class="feature-grid">
        <div class="feature-item">
          <el-icon class="feature-icon"><Picture /></el-icon>
          <h3>车牌照片识别</h3>
          <p>支持上传照片设置目标车牌，系统会自动识别其中的车牌信息</p>
        </div>
        <div class="feature-item">
          <el-icon class="feature-icon"><VideoCamera /></el-icon>
          <h3>视频监控</h3>
          <p>对上传的视频进行智能分析，精准检测目标车牌的出现时间点</p>
        </div>

        <div class="feature-item">
          <el-icon class="feature-icon"><AlarmClock /></el-icon>
          <h3>报警机制</h3>
          <p>当目标车牌出现时自动记录并生成报警信息，帮助更高效的监督管理</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { BACKEND_PORT } from '../port_config.js'
import axios from 'axios'
import { Upload, VideoCamera, Picture, DataAnalysis, Refresh, View, AlarmClock } from '@element-plus/icons-vue'
import { ElMessage, ElNotification } from 'element-plus'
import { plateRecognitionApi } from '../api/plateRecognition'
import { plateMonitoringApi } from '../api/plateMonitoring'

// 获取置信度对应的标签类型
const getConfidenceType = (confidence) => {
  const percent = confidence * 100;
  if (percent >= 90) return 'success';
  if (percent >= 70) return 'primary';
  if (percent >= 50) return 'warning';
  return 'danger';
}

// 状态变量
const loading = ref(true)
const activeTab = ref('image')
const serviceStatus = ref('loading') // 服务状态变量
const serviceStatusText = ref('正在连接服务...') // 服务状态文本变量
const serviceRunning = ref(false) // 服务运行状态变量
const processingResult = ref(null)
const videoResults = ref([]) // 视频结果数组
const videoStatus = ref('') // 视频状态变量

// 车牌监控状态变量
const targetPlate = ref({ plate_no: '', plate_color: '', timestamp: '' })
const monitoringResult = ref(null)
const monitorVideoStatus = ref(null)
const monitorProcessId = ref('')
const monitorProgressTimer = ref(null)

// 上传前检查图片
const beforeUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  const isLt5M = file.size / 1024 / 1024 < 5

  if (!isImage) {
    ElMessage.error('只能上传图片文件!')
    return false
  }
  if (!isLt5M) {
    ElMessage.error('图片大小不能超过 5MB!')
    return false
  }
  return true
}

// 上传前检查视频
const beforeVideoUpload = (file) => {
  const isVideo = file.type.startsWith('video/')
  const isLt50M = file.size / 1024 / 1024 < 50

  if (!isVideo) {
    ElMessage.error('只能上传视频文件!')
    return false
  }
  if (!isLt50M) {
    ElMessage.error('视频大小不能超过 50MB!')
    return false
  }
  return true
}

// 处理监控图片上传成功
const handleMonitorImageSuccess = (response) => {
  console.log('监控图片上传响应:', response)
  if (response) {
    ElMessage.success('图片处理成功')
    
    // 设置识别结果，用于选择目标车牌
    monitoringResult.value = {
      originalImage: getProperImageUrl(response.originalImage || ''),
      processedImage: getProperImageUrl(response.processedImage || response.visualized_image || ''),
      plates: response.plates || [],
      message: response.message
    }
    
    console.log('处理后的图片结果:', {
      originalImage: monitoringResult.value.originalImage,
      processedImage: monitoringResult.value.processedImage
    })
    
    if (response.plates && response.plates.length === 0) {
      ElMessage.warning('没有识别到车牌，请尝试上传其他图片')
    } else if (response.plates && response.plates.length > 0) {
      ElMessage.success(`识别到 ${response.plates.length} 个车牌，请选择目标车牌`)
    }
  } else {
    ElMessage.error('图片处理失败')
  }
}

// 处理监控视频上传成功
const handleMonitorVideoSuccess = (response) => {
  console.log('监控视频上传响应:', response)
  if (response && (response.success || response.process_id)) {
    ElMessage.success('视频上传成功，开始监控分析...')
    
    // 获取处理ID并开始检查进度
    monitorProcessId.value = response.process_id || response.processId || response.id || ''
    console.log('获取到的视频处理ID:', monitorProcessId.value)
    
    if (monitorProcessId.value) {
      monitorVideoStatus.value = {
        status: 'processing',
        message: '视频监控分析中...',
        progress: 0
      }
      
      // 开始检查进度
      startMonitorProgress()
    } else if (response.output_video) {
      // 处理直接返回结果的情况
      monitorVideoStatus.value = {
        status: 'completed',
        message: '视频处理已完成',
        progress: 100,
        output_video: getProperVideoUrl(response.output_video),
        matches_video: getProperVideoUrl(response.matches_video || ''),
        match_count: response.match_count || 0,
        matches: response.matches || []
      }
      
      ElMessage.success('视频监控分析完成')
    } else {
      ElMessage.error('无法获取处理ID或视频结果')
    }
  } else {
    ElMessage.error(response?.message || response?.error || '视频上传失败')
  }
}

// 处理上传错误
const handleUploadError = (error) => {
  console.error('上传错误:', error)
  ElMessage.error('上传失败，请重试')
}

// 处理视频加载错误
const handleVideoError = (event) => {
  console.error('视频加载错误:', event)
  ElMessage.warning('视频加载失败，尝试使用备用路径')
  
  // 尝试使用备用路径
  const videoElement = event.target
  const sourceElement = videoElement.querySelector('source')
  if (sourceElement) {
    const currentSrc = sourceElement.getAttribute('src')
    console.log('当前视频路径:', currentSrc)
    
    // 如果当前路径是API路径格式，尝试使用直接路径
    if (currentSrc && currentSrc.startsWith('/api/')) {
      const alternativeSrc = currentSrc.replace('/api/plate-recognition', '/api')
      console.log('尝试备用路径:', alternativeSrc)
      sourceElement.setAttribute('src', alternativeSrc)
      videoElement.load() // 重新加载视频
    }
  }
}

// 处理图片加载错误
const handleImageError = (event) => {
  console.error('图片加载错误:', event)
  ElMessage.warning('图片加载失败，尝试使用备用路径')
  
  // 尝试使用备用路径
  const imgElement = event.target
  const currentSrc = imgElement.getAttribute('src')
  console.log('当前图片路径:', currentSrc)
  
  // 如果当前路径是API路径格式，尝试使用直接路径
  if (currentSrc && currentSrc.startsWith('/api/')) {
    const alternativeSrc = currentSrc.replace('/api/plate-recognition', '/api')
    console.log('尝试备用路径:', alternativeSrc)
    imgElement.setAttribute('src', alternativeSrc)
  }
}

// 获取车牌类型对应的标签样式
function getPlateTypeTag(type) {
  if (!type) return 'primary'
  
  const typeMap = {
    '普通': 'primary',
    '蓝': 'primary',     // 蓝牌
    '黄': 'warning',     // 黄牌
    '新能源': 'success',
    '绿': 'success',     // 绿牌
    '警车': 'danger',
    '军车': 'warning',
    '使馆': 'info',
    '双层黄牌': 'warning',
    '双层黄': 'warning',
    '双层蓝牌': 'primary',
    '双层蓝': 'primary',
    '双层绿牌': 'success',
    '双层绿': 'success',
    '学习车牌': 'info'
  }
  return typeMap[type] || 'primary'
}

// 获取车牌颜色对应的16进制颜色值
function getPlateColorHex(color) {
  if (!color) return '#409EFF'
  
  const colorMap = {
    '蓝色': '#409EFF',
    '黄色': '#E6A23C',
    '绿色': '#67C23A',
    '白色': '#DCDFE6',
    '黑色': '#303133',
    '红色': '#F56C6C'
  }
  return colorMap[color] || '#409EFF'
}

// 检查后端服务是否可用
const checkBackendService = async () => {
  try {
    console.log('正在检查车牌识别服务状态...');
    // 添加随机参数避免缓存
    const timestamp = new Date().getTime();
    const response = await axios.get(`/api/plate-recognition/status?t=${timestamp}`);
    // 注意：这里不需要改，因为直接使用axios而非request实例，所以需要保留/api前缀
    
    console.log('服务状态响应:', response.data);
    serviceStatus.value = response.data.status;
    
    if (serviceStatus.value === 'ok') {
      serviceStatusText.value = '服务正常';
      serviceRunning.value = true;
      loading.value = false;
      ElMessage.success('车牌识别服务已准备就绪');
    } else if (serviceStatus.value === 'starting') {
      serviceStatusText.value = '服务正在启动中...';
      serviceRunning.value = false;
      // 延迟后再次检查
      setTimeout(() => checkBackendService(), 3000);
    } else {
      serviceStatusText.value = '服务未运行';
      serviceRunning.value = false;
      ElMessage.warning('车牌识别服务状态异常: ' + response.data.message || '未知原因');
    }
  } catch (error) {
    console.error('检查服务状态失败:', error);
    // 输出更多错误信息以便调试
    if (error.response) {
      console.error('错误响应数据:', error.response.data);
      console.error('错误响应状态:', error.response.status);
    } else if (error.request) {
      console.error('请求发送但无响应:', error.request);
    } else {
      console.error('请求配置错误:', error.message);
    }
    
    serviceStatus.value = 'error';
    serviceStatusText.value = '服务连接失败';
    serviceRunning.value = false;
    loading.value = false;
    ElMessage.error('车牌识别服务未启动，请稍后再试')
  }
}

// 使用代理路径 - 快捷方式
const getApiUrl = (path) => {
  // 直接返回相对路径，让Vite代理来处理
  const apiPath = `/api${path}` // 添加/api前缀，因为upload组件会直接发送请求而不经过request实例
  console.log(`使用相对路径（将通过代理转发）: ${apiPath}`)
  return apiPath
}

// 处理图片URL，确保其可以正确显示
const getProperImageUrl = (url) => {
  if (!url) return ''
  
  console.log('处理图片URL:', url)
  
  // 如果是完整的URL（服务器返回的URL通常是完整的，如http://127.0.0.1:5000/...）
  if (url.startsWith('http://127.0.0.1:5000') || url.startsWith('http://localhost:5000')) {
    const newUrl = url.replace(/http:\/\/(127.0.0.1|localhost):5000/, '/api/plate-recognition')
    console.log('完整URL转换为:', newUrl)
    return newUrl
  }
  
  // 确保API路径正确
  if (url.startsWith('/api/plate-recognition') || url.startsWith('/api/plate-monitoring')) {
    console.log('使用API路径:', url)
    return url
  }
  
  // 如果是从static目录开始的相对路径
  if (url.startsWith('static/')) {
    const newUrl = `/api/plate-recognition/${url}`
    console.log('相对static路径转换为:', newUrl)
    return newUrl
  }
  
  // 对于相对路径，确保以/开头
  if (!url.startsWith('/') && !url.startsWith('http')) {
    const newUrl = `/api/plate-recognition/${url}`
    console.log('添加API前缀:', newUrl)
    return newUrl
  }
  
  console.log('URL保持不变:', url)
  return url
}

// 处理视频URL，确保其可以正确显示
const getProperVideoUrl = (url) => {
  if (!url) return ''
  
  console.log('处理视频URL:', url)
  
  // 与图片处理类似，但针对视频格式
  if (url.startsWith('http://127.0.0.1:5000') || url.startsWith('http://localhost:5000')) {
    const newUrl = url.replace(/http:\/\/(127.0.0.1|localhost):5000/, '/api/plate-recognition')
    console.log('完整视频URL转换为:', newUrl)
    return newUrl
  }
  
  // 已经是API路径的情况
  if (url.startsWith('/api/')) {
    return url
  }
  
  // 如果是从static目录开始的相对路径
  if (url.includes('static/') || url.includes('output/')) {
    const newUrl = `/api/plate-recognition/${url}`
    console.log('相对视频路径转换为:', newUrl)
    return newUrl
  }
  
  // 对于相对路径，添加API前缀
  if (!url.startsWith('/') && !url.startsWith('http')) {
    const newUrl = `/api/plate-recognition/video/${url}`
    console.log('添加视频API前缀:', newUrl)
    return newUrl
  }
  
  return url
}

// 车牌监控功能方法
// 检查是否有目标车牌设置
const checkTargetPlate = async () => {
  // 目前接口不存在，暂时禁用请求以避免 404 错误
  console.log('车牌监控功能待实现，暂时使用空对象');
  
  /* 暂时禁用真实请求
  try {
    const response = await axios.get(getApiUrl('/api/plate-monitoring/target-plate'))
    if (response.data && response.data.plate_no) {
      targetPlate.value = response.data
    }
  } catch (error) {
    console.log('获取目标车牌失败:', error)
  }
  */
  
  // 目前直接返回空对象
  return {};
}

// 格式化车牌号码，正确处理单行和双行车牌
const formatPlateNumber = (plateNo, plateType) => {
  console.log('得到车牌号:', plateNo, '车牌类型:', plateType)
  
  // 空值检查
  if (!plateNo) return ''
  
  // 双层车牌判断 - 优先通过验证字符串长度和车牌类型信息
  const isDoublePlate = (
    plateNo.length === 8 || 
    (plateType && (plateType.includes('双行') || plateType.includes('双层')))
  )
  
  console.log('是否双层车牌:', isDoublePlate)
  
  if (isDoublePlate) {
    // 如果车牌号长度不为8，但车牌类型显示是双层，应该返回原始值
    if (plateNo.length !== 8) {
      console.warn('双层车牌长度不为8:', plateNo)
      return plateNo
    }
    
    // 双层车牌格式化 - 修改为更明显的格式与颜色
    const firstPart = plateNo.substring(0, 2)  // 京E
    const secondPart = plateNo.substring(2)    // A5331
    
    // 使用HTML标记增强可读性
    return `<span style="color:#E69511;font-weight:bold">${firstPart[0]} ${firstPart[1]}<br/>${secondPart[0]} ${secondPart.substring(1)}</span>`
  } else if (plateNo.length === 7) {
    // 单层车牌格式化
    return `${plateNo[0]} ${plateNo[1]}${plateNo.substring(2)}`
  }
  
  // 其他情况直接返回原值
  return plateNo
}

// 设置目标车牌
const setTargetPlate = async (plateNumber, plateColor) => {
  try {
    const formData = new FormData()
    formData.append('plate_number', plateNumber) // 使用正确的参数名 plate_number
    formData.append('plate_color', plateColor || '蓝色')
    
    const response = await plateMonitoringApi.setTargetPlate(formData)
    if (response) {
      targetPlate.value = {
        plate_no: plateNumber,
        plate_color: plateColor || '蓝色',
        timestamp: new Date().toLocaleString()
      }
      monitoringResult.value = null // 清除选择界面
      ElMessage.success(`已设置目标车牌: ${formatPlateNumber(plateNumber)}`)
    } else {
      ElMessage.error(response?.message || '设置目标车牌失败')
    }
  } catch (error) {
    console.error('设置目标车牌失败:', error)
    ElMessage.error('设置目标车牌失败')
  }
}

// 清除目标车牌
const clearTargetPlate = async () => {
  try {
    const response = await plateMonitoringApi.clearTargetPlate()
    if (response && response.success) {
      targetPlate.value = { plate_no: '', plate_color: '', timestamp: '' }
      monitorVideoStatus.value = null
      ElMessage.success('已清除目标车牌')
    } else {
      ElMessage.error(response?.message || '清除目标车牌失败')
    }
  } catch (error) {
    console.error('清除目标车牌失败:', error)
    ElMessage.error('清除目标车牌失败')
  }
}

// 开始检查监控进度
const startMonitorProgress = () => {
  // 清除可能存在的定时器
  if (monitorProgressTimer.value) {
    clearInterval(monitorProgressTimer.value)
  }
  
  // 立即检查一次
  checkMonitorProgress()
  
  // 每3秒检查一次进度
  monitorProgressTimer.value = setInterval(() => {
    checkMonitorProgress()
  }, 3000)
}

// 检查监控进度
const checkMonitorProgress = async () => {
  if (!monitorProcessId.value) {
    return
  }
  
  try {
    const response = await plateMonitoringApi.getVideoStatus(monitorProcessId.value)
    console.log('监控视频处理状态:', response)
    
    if (response) {
      // 更新状态
      monitorVideoStatus.value = response
      
      // 如果处理完成或出错，停止轮询
      if (response.status === 'completed' || response.status === 'error') {
        clearInterval(monitorProgressTimer.value)
        monitorProgressTimer.value = null
        
        // 显示完成或错误消息
        if (response.status === 'completed') {
          ElMessage.success('视频监控分析完成')
        } else {
          ElMessage.error(`处理失败: ${response.message || '未知错误'}`)
        }
      }
    }
  } catch (error) {
    console.error('检查监控进度失败:', error)
  }
}

// 模拟检查后端服务
const simulateBackendService = () => {
  setTimeout(() => {
    // 模拟服务已启动
    serviceRunning.value = true
    serviceStatus.value = 'running'
    serviceStatusText.value = '服务已就绪'
    loading.value = false
    
    ElNotification({
      title: '车牌识别系统已就绪',
      message: '您现在可以上传图片或视频进行车牌识别',
      type: 'success',
      duration: 3000
    })
    
    // 检查是否有已设置的目标车牌
    checkTargetPlate()
  }, 2000) // 2秒后显示服务已启动
}

onMounted(() => {
  // 页面加载时显示提示
  ElNotification({
    title: '正在加载车牌识别系统',
    message: '系统正在初始化，请稍候...',
    type: 'info',
    duration: 3000
  })
  
  // 使用模拟服务检查
  simulateBackendService()
})
</script>

<style scoped>
.plate-recognition-view {
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
  background: linear-gradient(45deg, #ff3d00, #ff9e00);
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
}

.section-title p {
  font-size: 16px;
  color: var(--el-text-color-secondary);
}

.main-card {
  margin-bottom: 24px;
  border-radius: 12px;
  overflow: hidden;
  background-color: var(--el-bg-color);
  border: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.loading-container {
  padding: 32px;
  height: 600px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.loading-text {
  text-align: center;
  margin-top: 16px;
  color: var(--el-text-color-secondary);
}

.plate-system-container {
  padding: 20px;
}

.upload-section {
  margin-bottom: 24px;
}

.upload-area {
  width: 100%;
  border: 2px dashed var(--el-border-color);
  border-radius: 8px;
  padding: 30px;
  text-align: center;
  transition: all 0.3s;
  background-color: var(--el-bg-color-page);
}

.upload-area:hover {
  border-color: var(--el-color-primary);
  background-color: rgba(var(--el-color-primary-rgb), 0.05);
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 16px;
  color: #ff6600;
}

.upload-text {
  font-size: 16px;
  color: var(--el-text-color-primary);
  margin-bottom: 8px;
}

.upload-tip {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.result-section {
  margin-top: 32px;
}

.result-section h3 {
  font-size: 20px;
  color: var(--el-text-color-primary);
  margin-bottom: 16px;
}

.result-images {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
  margin: 20px 0;
}

.original-image, .processed-image {
  display: flex;
  flex-direction: column;
}

.original-image h4, .processed-image h4 {
  font-size: 16px;
  margin-bottom: 10px;
  color: #333;
}

.empty-video {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f8f8f8;
  height: 200px;
  border-radius: 8px;
  color: #999;
}

.empty-video .el-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

:deep(.el-image) {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  height: 300px;
  background-color: #f8f8f8;
}

:deep(.el-image-viewer__wrapper) {
  z-index: 2050;
}

.plate-info {
  margin-top: 24px;
}

.plate-info h4 {
  font-size: 16px;
  color: var(--el-text-color-primary);
  margin-bottom: 12px;
}

.plate-details {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.plate-number {
  font-size: 16px;
  font-weight: bold;
}

.confidence {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.video-result {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
}

.video-player {
  margin-bottom: 24px;
}

.result-video {
  width: 100%;
  max-height: 400px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.video-stats {
  margin-top: 16px;
}

.video-stats h4 {
  font-size: 16px;
  color: var(--el-text-color-primary);
  margin-bottom: 12px;
}

.mt-4 {
  margin-top: 16px;
}

.feature-section {
  padding: 40px 20px;
  background: linear-gradient(145deg, #f8f9fa, #ffffff);
  border-radius: 16px;
  margin-bottom: 30px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.feature-title {
  text-align: center;
  font-size: 28px;
  margin-bottom: 30px;
  color: #333;
  position: relative;
  font-weight: 600;
}

.feature-title:after {
  content: "";
  display: block;
  width: 80px;
  height: 4px;
  background: linear-gradient(45deg, #ff6600, #ff9966);
  margin: 15px auto 0;
  border-radius: 2px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 30px;
  padding: 20px;
}

.feature-item {
  text-align: center;
  padding: 30px 20px;
  border-radius: 16px;
  background-color: white;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.feature-item:hover {
  transform: translateY(-10px);
  box-shadow: 0 15px 30px rgba(255, 102, 0, 0.2);
}

.feature-icon {
  font-size: 50px;
  margin-bottom: 20px;
  color: #ff6600;
  background: linear-gradient(45deg, #ff6600, #ff9966);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.feature-item h3 {
  font-size: 20px;
  margin-bottom: 15px;
  color: #333;
  font-weight: 600;
}

.feature-item p {
  font-size: 15px;
  color: #666;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .feature-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .plate-recognition-iframe {
    height: 450px;
  }
}

/* 车牌监控样式 */
.monitoring-section {
  padding: 20px 0;
}

.step-container {
  margin-bottom: 30px;
  padding: 25px;
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  background-color: #fff;
  transition: all 0.3s;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
}

.active-step {
  border-color: #ff6600;
  box-shadow: 0 8px 20px rgba(255, 102, 0, 0.15);
}

.disabled-step {
  opacity: 0.7;
  pointer-events: none;
}

.step-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.step-number {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(45deg, #ff6600, #ff9966);
  color: white;
  font-weight: bold;
  margin-right: 15px;
  box-shadow: 0 4px 10px rgba(255, 102, 0, 0.3);
}

.step-container h3 {
  font-size: 18px;
  color: #333;
  font-weight: 600;
  margin: 0;
}

.target-plate-info {
  margin-top: 20px;
}

.target-plate-details {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 10px;
}

.plate-number {
  font-size: 20px;
  font-weight: bold;
  color: #ff6600;
  background-color: rgba(255, 102, 0, 0.1);
  padding: 8px 16px;
  border-radius: 6px;
  letter-spacing: 1px;
}

.timestamp {
  font-size: 14px;
  color: #666;
}

.plate-selection {
  margin: 25px 0;
  animation: fadeIn 0.5s ease-out;
}

.plate-selection h3 {
  margin-bottom: 15px;
  font-size: 18px;
  color: #333;
  font-weight: 600;
}

.selection-container {
  background: white;
  border-radius: 12px;
  padding: 10px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
}

.plate-table {
  width: 100%;
}

.plate-text {
  font-weight: 600;
  color: #333;
}

.confidence-tag {
  padding: 6px 10px;
  border-radius: 4px;
  font-weight: 500;
}

.set-target-btn {
  background: linear-gradient(45deg, #ff6600, #ff9966);
  border: none;
  transition: all 0.3s;
}

.set-target-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(255, 102, 0, 0.2);
}

.disabled-message {
  margin-top: 15px;
  animation: fadeIn 0.5s ease-out;
}

.monitoring-results {
  margin-top: 40px;
  border-top: 1px solid #ebeef5;
  padding-top: 30px;
  animation: fadeIn 0.5s ease-out;
}

.monitoring-results h3 {
  font-size: 22px;
  color: #333;
  margin-bottom: 20px;
  font-weight: 600;
  position: relative;
  display: inline-block;
}

.monitoring-results h3:after {
  content: "";
  display: block;
  width: 50%;
  height: 3px;
  background: linear-gradient(45deg, #ff6600, #ff9966);
  position: absolute;
  bottom: -8px;
  left: 0;
  border-radius: 3px;
}

.progress-section {
  margin: 25px 0;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
}

.progress-bar {
  height: 10px;
}

.progress-message {
  margin-top: 15px;
  text-align: center;
  color: #333;
  font-weight: 500;
  font-size: 16px;
}

.progress-details {
  margin-top: 10px;
  text-align: center;
  color: #666;
  font-size: 14px;
}

.results-section {
  margin-top: 25px;
}

.result-alert {
  margin-bottom: 25px;
}

.video-players {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 30px;
  margin: 30px 0;
}

.video-container {
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.video-container:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.15);
}

.video-title {
  padding: 15px;
  margin: 0;
  text-align: center;
  font-size: 18px;
  color: #333;
  font-weight: 600;
  background: #f8f9fa;
  border-bottom: 1px solid #ebeef5;
}

.player {
  width: 100%;
  background-color: #000;
  aspect-ratio: 16/9;
}

.matches-table {
  margin-top: 30px;
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.table-title {
  font-size: 18px;
  color: #333;
  margin-bottom: 15px;
  font-weight: 600;
}

.detection-table {
  width: 100%;
}

.plate-label {
  font-weight: 600;
  padding: 5px 10px;
  background: rgba(255, 102, 0, 0.1);
  border-radius: 4px;
  color: #ff6600;
}

.error-section {
  margin: 30px 0;
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
}

.error-alert {
  margin-bottom: 20px;
}

.error-suggestion {
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  color: #666;
}

.error-suggestion ul {
  margin: 10px 0;
  padding-left: 20px;
}

.error-suggestion li {
  margin-bottom: 5px;
}

.upload-area {
  border-radius: 12px;
  border: 2px dashed #e4e7ed;
  padding: 30px;
  transition: all 0.3s ease;
}

.upload-area:hover {
  border-color: #ff6600;
  background-color: rgba(255, 102, 0, 0.03);
}

.upload-icon {
  font-size: 48px;
  color: #ff6600;
  margin-bottom: 15px;
}

.upload-text {
  font-size: 16px;
  margin-bottom: 8px;
  color: #333;
  font-weight: 500;
}

.upload-tip {
  font-size: 14px;
  color: #666;
}

/* 添加动画效果 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeScale {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
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

.fade-scale-enter-active,
.fade-scale-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-scale-enter-from,
.fade-scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
