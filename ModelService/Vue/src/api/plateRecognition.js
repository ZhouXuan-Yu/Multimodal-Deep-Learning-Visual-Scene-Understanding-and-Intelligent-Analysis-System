import request from '@/utils/request'

// 车牌识别API客户端
export const plateRecognitionApi = {
  // 检查车牌识别服务状态
  checkStatus() {
    return request.get('/api/plate-recognition/status')
  },
  
  // 上传图片进行车牌识别
  uploadImage(formData) {
    return request.post('/api/plate-recognition/upload-image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  // 上传视频进行分析
  uploadVideo(formData) {
    return request.post('/api/plate-recognition/upload-video', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  // 获取视频处理状态
  getVideoStatus(processId) {
    return request.get(`/api/plate-recognition/video-status/${processId}`)
  },
  
  // 获取视频处理结果
  getVideoResults(processId) {
    return request.get(`/api/plate-recognition/video-results/${processId}`)
  },
  
  // 开始车牌识别服务
  startService() {
    return request.post('/api/plate-recognition/start-service')
  },
  
  // 停止车牌识别服务
  stopService() {
    return request.post('/api/plate-recognition/stop-service')
  }
}
