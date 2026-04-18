import request from '@/utils/request'

// 设计竞赛项目API客户端
export const designCompetitionApi = {
  // 车牌识别
  recognizePlate(formData) {
    return request.post('/api/design-competition/recognize-plate', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  // 车辆识别
  recognizeCar(formData) {
    return request.post('/api/design-competition/recognize-car', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  // 健康检查
  healthCheck() {
    return request.get('/api/design-competition/health')
  }
}
