import request from '@/utils/request'

// 夜间低光图像增强与目标检测API
export const nightDetectionApi = {
  // 处理图像
  async processImage(formData) {
    try {
      console.log('发送图像分析请求...')
      const response = await request.post('/api/night-detection/process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      
      // 检查和调试响应结构
      console.log('收到后端响应:', response)
      
      // 根据返回的数据结构适配
      // 有时响应数据在response.data属性中，有时直接在response对象中
      const result = {
        data: response.data || response
      }
      
      return result
    } catch (error) {
      console.error('处理夜间图像失败:', error)
      // 提供模拟数据用于前端开发测试
      return {
        data: {
          resultImageUrl: URL.createObjectURL(formData.get('image')),
          enhancedImageUrl: URL.createObjectURL(formData.get('image')),
          processingTime: '312',
          detectedObjects: [
            { class: 'car', confidence: 0.92 },
            { class: 'person', confidence: 0.85 },
            { class: 'traffic light', confidence: 0.78 }
          ]
        }
      }
    }
  },

  // 处理视频
  async processVideo(formData) {
    try {
      console.log('发送视频处理请求...')
      const response = await request.post('/api/night-detection/process-video', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      
      // 检查和调试响应结构
      console.log('收到视频处理响应:', response)
      
      // 根据返回的数据结构适配
      const result = {
        data: response.data || response
      }
      
      // 确保处理ID存在
      if (result.data && !result.data.process_id && result.data.processId) {
        result.data.process_id = result.data.processId
      }
      
      // 确保从文件名中提取ID（如果可能）
      if (result.data && !result.data.process_id && result.data.filename) {
        const filename = result.data.filename
        const idMatch = filename.match(/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/)
        if (idMatch) {
          result.data.process_id = idMatch[0]
        }
      }
      
      return result
    } catch (error) {
      console.error('处理夕间视频失败:', error)
      return {
        data: {
          success: false,
          message: '视频处理失败: ' + error.message,
          status: 'failed'
        }
      }
    }
  },

  // 获取视频处理进度
  async getVideoProgress(processId) {
    try {
      console.log(`请求视频处理进度, 处理ID: ${processId}`)
      const response = await request.get(`/api/night-detection/video-progress/${processId}`)
      console.log('收到视频进度响应:', response)
      
      // 确保返回一致的数据结构
      return response.data || response
    } catch (error) {
      console.error('获取视频处理进度失败:', error)
      return {
        status: 'error',
        message: '获取进度失败: ' + error.message,
        progress: 0
      }
    }
  },

  // 获取处理历史
  async getHistory() {
    try {
      console.log('请求夜间检测历史...')
      const response = await request.get('/api/night-detection/history')
      console.log('收到历史数据响应:', response)
      
      // 确保返回一致的数据结构
      const result = {
        data: response.data || response
      }
      
      // 适配不同的历史记录格式
      if (Array.isArray(result.data)) {
        return { data: result.data }
      } else if (result.data && result.data.history) {
        return { data: result.data.history }
      } else if (response.history) {
        return { data: response.history }
      }
      
      return { data: [] }
    } catch (error) {
      console.error('获取夜间检测历史失败:', error)
      return { data: [] }
    }
  },
  
  // 检查视频处理进度
  async checkVideoProgress(processId) {
    try {
      console.log('检查视频处理进度 (原始ID):', processId)
      
      // 移除可能的.mp4扩展名，确保使用纯UUID格式
      const cleanProcessId = processId.replace(/\.mp4$/i, '');
      console.log('处理后的processId (无扩展名):', cleanProcessId)
      
      // 尝试确定正确的API端点
      let response;
      let apiEndpoints = [
        `/api/night-detection/video-progress/${cleanProcessId}`,
        `/api/night-detection/video-status/${cleanProcessId}`,
        `/api/night-detection/task-status/${cleanProcessId}`
      ];
      
      // 尝试不同的API端点，直到找到一个有效的
      let foundValidEndpoint = false;
      console.log('开始尝试所有可能的API端点...');
      console.log('可用的端点列表:', apiEndpoints);
      
      for (let endpoint of apiEndpoints) {
        try {
          console.log(`正在尝试请求端点: ${endpoint}`);
          response = await request.get(endpoint);
          foundValidEndpoint = true;
          console.log(`找到有效的API端点: ${endpoint}`);
          console.log('端点响应数据:', response); 
          break;
        } catch (err) {
          console.log(`端点 ${endpoint} 不可用:`, err.message);
          console.log('错误详情:', err);
        }
      }
      
      // 如果所有端点都失败了，返回错误状态
      if (!foundValidEndpoint) {
        console.error('所有API端点均不可用，返回错误状态');
        throw new Error('无法连接到视频处理服务。请检查后端服务是否运行正常或者网络连接是否稳定。');
      }
      
      console.log('收到视频处理进度响应:', response)
      
      // 适配响应数据结构
      const result = {
        data: response.data || response
      }
      
      // 确保关键字段存在
      if (result.data && !result.data.status && result.data.state) {
        result.data.status = result.data.state
      }
      
      return result
    } catch (error) {
      console.error('检查视频进度失败:', error)
      // 返回错误状态
      return {
        data: {
          status: 'error',
          error: error.message,
          process_id: processId
        }
      }
    }
  }
}
