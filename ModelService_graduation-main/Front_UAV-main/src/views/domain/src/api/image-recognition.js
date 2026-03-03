import request from '@/utils/request'

export const imageRecognitionApi = {
  /**
   * 分析图片
   * @param {FormData} formData - 包含图片文件和分析模式的表单数据
   * @returns {Promise} 返回分析结果
   */
  analyzeImage(formData) {
    console.log('发送图片分析请求:', {
      mode: formData.get('mode'),
      hasFile: formData.has('file')
    })
    
    return request({
      url: '/api/image-recognition/analyze',
      method: 'post',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 400000
    }).then(response => {
      console.log('图片分析原始响应:', response)
      
      // 检查错误
      if (response.error) {
        console.error('分析错误:', response.error)
        throw new Error(response.error)
      }
      
      // 添加详细调试信息
      console.log('详细响应数据结构:', JSON.stringify(response))
      console.log('persons数组:', response.persons ? JSON.stringify(response.persons) : 'undefined')
      
      if (response.persons && response.persons.length > 0) {
        console.log('第一个person详情:', JSON.stringify(response.persons[0]))
        console.log('person.bbox类型:', response.persons[0].bbox ? 
          `${typeof response.persons[0].bbox} [${response.persons[0].bbox}]` : 'undefined')
      }
      
      // 直接返回响应，不做额外处理
      return response
    }).catch(error => {
      console.error('请求失败:', error)
      throw error
    })
  },

  /**
   * 健康检查
   * @returns {Promise} 返回健康状态
   */
  healthCheck() {
    return request({
      url: '/api/image-recognition/health',
      method: 'get'
    })
  },
  
  /**
   * 获取可用模型列表
   * @returns {Promise} 返回模型列表
   */
  getAvailableModels() {
    return request({
      url: '/api/image-recognition/models',
      method: 'get'
    })
  }
} 