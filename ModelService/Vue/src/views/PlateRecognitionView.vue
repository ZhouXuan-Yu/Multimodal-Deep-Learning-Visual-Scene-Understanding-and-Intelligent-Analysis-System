<template>
  <div class="plate-recognition-view">
    <div class="section-title">
      <h2>车牌监控系统</h2>
      <p>上传车牌图片设置目标，然后监控视频中的目标车牌</p>
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
                  :action="getApiUrl('/api/plate-monitoring/upload-image')"
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
          <!-- Step 2: 车牌选择界面 (当有识别结果但未设置目标时显示) -->
          <div v-if="monitoringResult && !targetPlate.plate_no" class="plate-selection">
            <h3>请选择目标车牌</h3>
            <el-table :data="monitoringResult.plates || []" border stripe>
              <el-table-column label="车牌号码">
                <template #default="{row}">
                  <span v-html="formatPlateNumber(row.plate_no, row.plate_type)"></span>
                </template>
              </el-table-column>
              <!-- 车牌颜色和车辆颜色列已根据需求移除 -->
              <el-table-column label="置信度">
                <template #default="{row}">
                  {{ (row.confidence * 100).toFixed(1) }}%
                </template>
              </el-table-column>
              <el-table-column label="操作">
                <template #default="{row}">
                  <el-button 
                    type="primary" 
                    size="small"
                    @click="setTargetPlate(row.plate_no, row.plate_color)"
                  >设为目标</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          
          <!-- Step 3: 视频监控分析 -->
          <div class="step-container" :class="{ 'active-step': targetPlate.plate_no, 'disabled-step': !targetPlate.plate_no }">
            <div class="step-header">
              <div class="step-number">2</div>
              <h3>上传视频进行监控</h3>
            </div>
            <div class="step-content">
              <div v-if="targetPlate.plate_no">
                <el-upload
                  class="upload-area"
                  :action="getApiUrl('/api/plate-monitoring/upload-video')"
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
                  <div class="upload-tip">系统将自动检测视频中是否出现目标车牌: {{ targetPlate.plate_no }}</div>
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
                    完成步骤1后才能进行视频监控
                  </template>
                </el-alert>
              </div>
            </div>
          </div>
          <!-- Step 4: 监控结果 -->
          <div v-if="monitorVideoStatus" class="monitoring-results">
            <h3>监控分析结果</h3>
            
            <!-- 进度条 -->
            <div v-if="monitorVideoStatus.status === 'processing'" class="progress-section">
              <el-progress 
                :percentage="monitorVideoStatus.progress" 
                :status="monitorVideoStatus.progress === 100 ? 'success' : ''"
                :stroke-width="20"
              ></el-progress>
              <div class="progress-message">{{ monitorVideoStatus.message }}</div>
            </div>
            
            <!-- 完成结果 -->
            <div v-else-if="monitorVideoStatus.status === 'completed'" class="results-section">
              <el-alert
                :title="monitorVideoStatus.match_count > 0 ? `发现目标车牌 ${targetPlate.plate_no}，共${monitorVideoStatus.match_count}次匹配` : `未在视频中发现目标车牌 ${targetPlate.plate_no}`"
                :type="monitorVideoStatus.match_count > 0 ? 'success' : 'warning'"
                :closable="false"
                show-icon
              ></el-alert>
              
              <!-- 视频播放区域 -->
              <div class="video-players">
                <div class="video-container">
                  <h4>处理后的完整视频</h4>
                  <video v-if="monitorVideoStatus.output_video" controls>
                    <source :src="monitorVideoStatus.output_video" type="video/mp4">
                    您的浏览器不支持视频播放
                  </video>
                </div>
                
                <div v-if="monitorVideoStatus.matches_video" class="video-container">
                  <h4>匹配片段视频</h4>
                  <video controls>
                    <source :src="monitorVideoStatus.matches_video" type="video/mp4">
                    您的浏览器不支持视频播放
                  </video>
                </div>
              </div>
              
              <!-- 匹配记录表格 -->
              <div v-if="monitorVideoStatus.matches && monitorVideoStatus.matches.length > 0" class="matches-table">
                <h4>匹配记录</h4>
                <el-table :data="monitorVideoStatus.matches" border stripe>
                  <el-table-column prop="frame_number" label="帧号" width="80"></el-table-column>
                  <el-table-column prop="plate_number" label="车牌号码"></el-table-column>
                  <el-table-column prop="timestamp" label="时间戳"></el-table-column>
                  <el-table-column label="置信度" width="100">
                    <template #default="{row}">
                      {{ (row.confidence * 100).toFixed(1) }}%
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
            
            <!-- 错误结果 -->
            <div v-else-if="monitorVideoStatus.status === 'error'" class="error-section">
              <el-alert
                title="处理失败"
                type="error"
                :description="monitorVideoStatus.message"
                :closable="false"
                show-icon
              ></el-alert>
            </div>
          </div>
        </div>
      </div>
    </el-card>
    
    <el-card class="feature-card">
      <div class="feature-grid">
        <div class="feature-item">
          <el-icon class="feature-icon"><Picture /></el-icon>
          <h3>车牌照片识别</h3>
          <p>支持上传照片设置目标车牌，系统会自动识别其中的车牌信息</p>
        </div>
        <div class="feature-item">
          <el-icon class="feature-icon"><VideoCamera /></el-icon>
          <h3>视频监控</h3>
          <p>对上传的视频进行分析，自动检测目标车牌的出现时间点</p>
        </div>
        <div class="feature-item">
          <el-icon class="feature-icon"><Timer /></el-icon>
          <h3>实时检测</h3>
          <p>采用高效监控算法，快速准确地检测目标车牌的出现</p>
        </div>
        <div class="feature-item">
          <el-icon class="feature-icon"><DataAnalysis /></el-icon>
          <h3>监控报警</h3>
          <p>当目标车牌出现时自动记录并生成报警信息，帮助更高效的监督管理</p>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { BACKEND_PORT } from '../port_config.js'
import axios from 'axios'
import { Upload, VideoCamera, Picture, DataAnalysis, Refresh, View } from '@element-plus/icons-vue'
import { ElMessage, ElNotification } from 'element-plus'
import { plateRecognitionApi } from '@/api/plateRecognition'
import { plateMonitoringApi } from '@/api/plateMonitoring'

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

// 图片上传成功处理
const handleUploadSuccess = (response, uploadFile) => {
  console.log('图片上传响应:', response)
  loading.value = false;
  
  // 首先检查响应是否为有效对象
  if (response) {
    // 判断响应结构 - 兼容新的API格式和旧的API格式
    const isNewFormat = response.processed_img_url && response.results;
    const isOldFormat = response.success && (response.origin_url || response.processed_url);
    
    if (isNewFormat) {
      // 新格式响应处理 - 查找车牌信息
      ElMessage.success('图片上传成功');
      
      // 从结果中提取车牌信息，只保留object_no为0的结果（车牌）
      console.log('识别结果详情:', JSON.stringify(response.results));
      
      // 详细记录每个检测到的车牌
      response.results.forEach((item, index) => {
        if (item.object_no === 0) {
          console.log(`检测到车牌 #${index}:`, 
            `车牌号=${item.plate_no}`, 
            `类型=${item.class_type}`, 
            `颜色=${item.plate_color}`, 
            `置信度=${item.score}`);
        }
      });
      
      const plateInfo = response.results
        .filter(item => item.object_no === 0) // 只保留车牌结果（object_no=0是车牌）
        .map(item => ({
          plateNumber: item.plate_no || item.plateNumber || '',
          plateType: item.class_type || item.plateType || '',
          plateColor: item.plate_color || item.plateColor || '',
          confidence: typeof item.score === 'number' ? item.score : (item.confidence || 0.8),
          rect: item.rect // 保存车牌位置信息用于可能的高亮显示
        }))
        .sort((a, b) => b.confidence - a.confidence); // 按置信度从高到低排序
      
      console.log('提取到的车牌信息数量:', plateInfo.length);
      console.log('提取到的车牌信息:', plateInfo);
      
      // 如果没有车牌信息，只记录空结果而不添加占位符
      if (plateInfo.length === 0) {
        console.log('未检测到车牌, 保持空结果');
        // 不再添加占位符数据
      }
      
      // 确保处理结果都是基本数据类型，避免可能的JSON序列化问题
      const safeProcessedImageUrl = response.processed_img_url || '';
      // 优先使用后端返回的原始图像URL，如果没有再使用上传文件的URL
      const safeOriginalImageUrl = response.origin_url || uploadFile.url;
      console.log('处理后图片URL:', safeProcessedImageUrl);
      console.log('原始图片URL:', safeOriginalImageUrl);
      
      // 设置处理结果
      processingResult.value = {
        originalImage: safeOriginalImageUrl, // 优先使用后端返回的原始图像URL
        processedImage: safeProcessedImageUrl,
        plateInfo: plateInfo,
        timestamp: new Date().getTime() // 添加时间戳以确保更新
      };
      
      // 确认是否成功设置了车牌信息
      console.log('设置到结果对象的车牌信息:', processingResult.value.plateInfo);
    } else if (isOldFormat) {
      // 旧格式响应处理
      ElMessage.success('图片上传成功');
      
      processingResult.value = {
        originalImage: response.origin_url,
        processedImage: response.processed_url,
        plateInfo: response.plate_info || []  // 如果没有车牌信息，使用空数组而不添加默认占位符
      };
    } else {
      // 不支持的响应格式
      console.error('不支持的响应格式:', response);
      ElMessage.error('图片处理失败: 响应格式不支持');
      return;
    }
    
    console.log('处理后的图片结果:', processingResult.value);
  } else {
    console.error('图片处理失败:', response);
    ElMessage.error(response?.message || '图片处理失败');
  }
}

// 视频上传成功处理
const handleVideoSuccess = (response, uploadFile) => {
  console.log('视频上传响应:', response)
  if (response && response.success) {
    ElMessage.success('视频上传成功，正在处理...')
    
    // 检查是否返回了处理ID（支持多种可能的ID字段名称）
    const processId = response.process_id || response.processId || response.id || (response.filename && response.filename.split('.')[0]) || null;
    console.log('获取到的处理ID:', processId);
    
    if (processId) {
      // 重置当前处理状态和结果
      processingResult.value = {
        processedVideo: null,
        analysis_results: [],
        statistics: {
          totalPlates: 0,
          processingTime: '0'
        },
        processing: true,
        progress: 0
      }
      
      // 开始轮询处理状态
      const statusCheckInterval = 2000 // 每2秒检查一次
      let checkCount = 0
      const maxChecks = 180 // 最多轮询6分钟
      
      const statusCheckTimer = setInterval(() => {
        checkCount++
        
        // 超过最大检查次数则停止
        if (checkCount > maxChecks) {
          clearInterval(statusCheckTimer)
          ElMessage.warning('视频处理超时，请稍后查看结果')
          processingResult.value.processing = false
          return
        }
        
        // 查询处理状态 - 使用之前获取的processId
        axios.get(`/api/plate-recognition/video-status/${processId}`)
          .then(statusResponse => {
            const statusData = statusResponse.data
            console.log('处理状态:', statusData)
            
            if (statusData.success) {
              // 更新进度
              processingResult.value.progress = statusData.progress || 0
              
              // 如果处理完成
              if (statusData.status === 'completed') {
                clearInterval(statusCheckTimer)
                
                // 获取完整结果
                axios.get(`/api/plate-recognition/video_results/${response.process_id}`)
                  .then(resultsResponse => {
                    const resultsData = resultsResponse.data
                    
                    if (resultsData.success) {
                      // 过滤有效的车牌结果（车牌号长度至少5个字符）
                      const validResults = (resultsData.results || []).filter(
                        result => result.plate_no && result.plate_no.length >= 5
                      )
                      
                      // 正确处理视频URL
                      let videoUrl = '';
                      
                      // 根据不同返回格式构建URL
                      if (resultsData.video_url) {
                        // 如果是完整URL，直接使用
                        if (resultsData.video_url.startsWith('http') || resultsData.video_url.startsWith('/api')) {
                          videoUrl = resultsData.video_url;
                        } 
                        // 如果是路径格式，添加static前缀
                        else if (resultsData.video_url.includes('static/')) {
                          videoUrl = `/api/plate-recognition/${resultsData.video_url}`;
                        }
                        // 如果只有文件名，构建完整路径
                        else {
                          videoUrl = `/api/plate-recognition/static/output/${resultsData.video_url}`;
                        }
                      } else if (resultsData.video_path) {
                        // 如果提供了video_path，使用它
                        videoUrl = `/api/plate-recognition/${resultsData.video_path}`;
                      } else if (response.video_url) {
                        // 后备选项：使用上传响应中的URL
                        videoUrl = response.video_url;
                      }
                      
                      console.log('构建的视频URL:', videoUrl)
                      
                      // 设置处理结果
                      processingResult.value = {
                        processedVideo: videoUrl,
                        analysis_results: validResults,
                        statistics: {
                          totalPlates: validResults.length,
                          processingTime: resultsData.processing_time || '0'
                        },
                        processing: false,
                        progress: 100
                      }
                      
                      console.log('处理后的视频结果:', processingResult.value)
                      ElMessage.success(`视频处理完成，检测到${validResults.length}个车牌`)
                      
                      // 更新视频结果列表
                      videoResults.value = validResults
                    } else {
                      ElMessage.error(resultsData.message || '获取视频结果失败')
                      processingResult.value.processing = false
                    }
                  })
                  .catch(error => {
                    console.error('获取视频结果错误:', error)
                    ElMessage.error('获取视频结果时发生错误')
                    processingResult.value.processing = false
                  })
              } else if (statusData.status === 'error') {
                // 处理失败
                clearInterval(statusCheckTimer)
                ElMessage.error(statusData.error || '视频处理失败')
                processingResult.value.processing = false
              }
              // 处理中状态继续轮询
            } else {
              console.error('获取状态失败:', statusData)
              ElMessage.warning(statusData.message || '获取处理状态失败')
            }
          })
          .catch(error => {
            console.error('查询处理状态错误:', error)
            // 不要立即停止轮询，可能是临时网络问题
          })
      }, statusCheckInterval)
    } else {
      ElMessage.warning('未获取到处理ID，无法追踪处理进度')
    }
  } else {
    console.error('视频上传失败:', response)
    ElMessage.error(response?.message || '视频上传失败')
  }
}

// 处理上传错误
const handleUploadError = (error) => {
  console.error('上传错误:', error)
  ElMessage.error('上传失败，请重试')
}

// 处理视频加载错误
const handleVideoError = (error) => {
  console.error('视频加载错误:', error)
  videoStatus.value = '加载失败'
  
  // 尝试重新构建URL
  if (processingResult.value && processingResult.value.processedVideo) {
    const currentUrl = processingResult.value.processedVideo
    console.log('当前视频URL:', currentUrl)
    
    // 尝试替代URL
    if (currentUrl.includes('/video/')) {
      // 尝试提取文件名并使用静态路径
      const filename = currentUrl.split('/').pop()
      if (filename) {
        const alternativeUrl = `/api/plate-recognition/static/output/${filename}`
        console.log('尝试替代URL:', alternativeUrl)
        processingResult.value.processedVideo = alternativeUrl
        videoStatus.value = '正在尝试替代URL'
      }
    }
  }
}

// 处理视频加载成功
const handleVideoLoaded = () => {
  console.log('视频加载成功')
  videoStatus.value = '加载成功'
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
    // 确保使用完整的URL前缀，特别是包含/api
    // 添加随机参数避免缓存
    const timestamp = new Date().getTime();
    const response = await axios.get(`/api/plate-recognition/status?t=${timestamp}`);
    
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
  console.log(`使用相对路径（将通过代理转发）: ${path}`)
  return path
}

// 处理图片URL，确保其可以正确显示
const getProperImageUrl = (url) => {
  if (!url) return ''
  
  console.log('处理图片URL:', url)
  
  // 如果是完整的URL（服务器返回的URL通常是完整的，如http://127.0.0.1:5000/...）
  if (url.startsWith('http://127.0.0.1:5000')) {
    const newUrl = url.replace('http://127.0.0.1:5000', '/api/plate-recognition')
    console.log('完整URL转换为:', newUrl)
    return newUrl
  }
  
  // 确保API路径正确
  if (url.startsWith('/api/plate-recognition')) {
    console.log('使用API路径:', url)
    return url
  }
  
  // 对于相对路径，确保以/开头
  if (!url.startsWith('/') && !url.startsWith('http')) {
    const newUrl = `/${url}`
    console.log('添加前导斜杠:', newUrl)
    return newUrl
  }
  
  console.log('URL保持不变:', url)
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

// 处理监控图片上传成功
const handleMonitorImageSuccess = (response) => {
  console.log('监控图片上传响应:', response)
  if (response) {
    ElMessage.success('图片处理成功')
    
    // 设置识别结果，用于选择目标车牌
    monitoringResult.value = {
      originalImage: response.originalImage || '',
      processedImage: response.processedImage || '',
      plates: response.plates || [],
      message: response.message
    }
    
    if (response.plates && response.plates.length === 0) {
      ElMessage.warning('没有识别到车牌，请尝试上传其他图片')
    } else if (response.plates && response.plates.length > 0) {
      ElMessage.success(`识别到 ${response.plates.length} 个车牌，请选择目标车牌`)
    }
  } else {
    ElMessage.error('图片处理失败')
  }
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

// 处理监控视频上传成功
const handleMonitorVideoSuccess = (response) => {
  console.log('监控视频上传响应:', response)
  if (response && response.success) {
    ElMessage.success('视频上传成功，开始监控分析...')
    
    // 获取处理ID并开始检查进度
    monitorProcessId.value = response.process_id || ''
    if (monitorProcessId.value) {
      monitorVideoStatus.value = {
        status: 'processing',
        message: '视频监控分析中...',
        progress: 0
      }
      
      // 开始检查进度
      startMonitorProgress()
    } else {
      ElMessage.error('无法获取处理ID')
    }
  } else {
    ElMessage.error(response?.message || '视频上传失败')
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
  margin-bottom: 24px;
}

.original-image h4,
.processed-image h4 {
  font-size: 16px;
  color: var(--el-text-color-primary);
  margin-bottom: 12px;
}

.el-image {
  width: 100%;
  max-height: 400px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
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

.feature-card {
  border-radius: 12px;
  background-color: var(--el-bg-color);
  border: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 24px;
  padding: 16px;
}

.feature-item {
  text-align: center;
  padding: 24px;
  border-radius: 8px;
  background-color: rgba(255, 255, 255, 0.03);
  transition: all 0.3s ease;
}

.feature-item:hover {
  transform: translateY(-5px);
  background-color: rgba(255, 255, 255, 0.06);
}

.feature-icon {
  font-size: 36px;
  margin-bottom: 16px;
  color: #ff6600;
}

.feature-item h3 {
  font-size: 18px;
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
}

.feature-item p {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
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
  padding: 20px;
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  background-color: var(--el-bg-color-page);
  transition: all 0.3s;
}

.active-step {
  border-color: var(--el-color-primary);
  box-shadow: 0 4px 12px rgba(var(--el-color-primary-rgb), 0.2);
}

.disabled-step {
  opacity: 0.6;
  pointer-events: none;
}

.step-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.step-number {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: var(--el-color-primary);
  color: white;
  font-weight: bold;
  margin-right: 12px;
}

.target-plate-info {
  margin-top: 16px;
}

.target-plate-details {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 8px;
}

.plate-number {
  font-size: 18px;
  font-weight: bold;
  color: var(--el-color-primary);
  background-color: rgba(var(--el-color-primary-rgb), 0.1);
  padding: 6px 12px;
  border-radius: 4px;
}

.timestamp {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.plate-selection {
  margin: 20px 0;
}

.disabled-message {
  margin-top: 12px;
}

.monitoring-results {
  margin-top: 30px;
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 20px;
}

.progress-section {
  margin: 16px 0;
}

.progress-message {
  margin-top: 8px;
  text-align: center;
  color: var(--el-text-color-secondary);
}

.results-section {
  margin-top: 16px;
}

.video-players {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
  margin: 24px 0;
}

.video-container {
  display: flex;
  flex-direction: column;
}

.video-container h4 {
  margin-bottom: 12px;
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.video-container video {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.matches-table {
  margin-top: 24px;
}
</style>
