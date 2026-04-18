import request from '@/utils/request'

export const imageAnalysisChatApi = {
  /**
   * 发送消息到本地大模型
   * @param {string} message - 用户消息
   * @param {Object} analysisData - 当前分析结果
   * @param {boolean} stream - 是否使用流式输出
   * @returns {Promise}
   */
  sendMessage(message, analysisData = null, stream = false) {
    console.log('=== 开始发送聊天请求 ===')
    console.log('用户消息:', message)
    console.log('分析数据:', analysisData)
    console.log('流式输出:', stream)

    if (!analysisData) {
      console.error('错误: 缺少分析数据')
      return Promise.reject(new Error('缺少图像分析数据'))
    }

    // 确保 analysisData 的格式正确
    const persons = Array.isArray(analysisData.persons) ? analysisData.persons : []
    const detected = parseInt(analysisData.detected || 0)
    
    console.log('解析后的人数:', detected)
    console.log('解析后的人物信息数组长度:', persons.length)
    
    const formattedAnalysisData = {
      currentAnalysis: {
        persons: persons.map((person, index) => ({
          id: index + 1,
          age: parseFloat(person.age || 0),
          age_confidence: parseFloat(person.age_confidence || 1.0),
          gender: person.gender || "unknown",
          gender_confidence: parseFloat(person.gender_confidence || 0),
          upper_color: person.upper_color || "unknown",
          upper_color_confidence: parseFloat(person.upper_color_confidence || 0),
          lower_color: person.lower_color || "unknown",
          lower_color_confidence: parseFloat(person.lower_color_confidence || 0),
          bbox: Array.isArray(person.bbox) ? person.bbox.map(Number) : [0, 0, 0, 0]
        })),
        detected: detected
      },
      analysisHistory: []
    }

    console.log('格式化后的请求数据:', formattedAnalysisData)
    console.log('人物信息:', JSON.stringify(formattedAnalysisData.currentAnalysis.persons, null, 2))

    const requestData = {
      messages: [{
        role: "user",
        content: message.toString()
      }],
      model: "qwen3.5:4b",
      temperature: 0.7,
      stream: stream,  // 添加流式输出选项
      context: formattedAnalysisData
    }

    console.log('发送到后端的完整数据:', JSON.stringify(requestData, null, 2))

    if (stream) {
      // 对于流式输出，我们返回fetch请求本身
      // 调用者需要处理流式响应
      return fetch('/api/image-analysis-chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
      });
    }

    // 非流式输出使用原来的请求方式
    return request({
      url: '/api/image-analysis-chat/completions',
      method: 'post',
      data: requestData,
      timeout: 180000,  // 增加超时时间到3分钟
      headers: {
        'Content-Type': 'application/json'
      }
    }).then(response => {
      console.log('收到后端响应:', response)
      return response
    }).catch(error => {
      console.error('请求失败:', error)
      throw error
    })
  }
}