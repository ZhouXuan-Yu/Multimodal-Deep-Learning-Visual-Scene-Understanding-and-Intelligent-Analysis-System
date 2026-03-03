/**
 * 知识图谱相关API服务
 */
import axios from 'axios';

export default {
  /**
   * 发送消息到知识库聊天
   * @param {string} message - 用户消息
   * @param {boolean} webSearch - 是否开启联网搜索
   * @param {string} model - 使用的模型
   * @returns {Promise}
   */
  sendMessage(message, webSearch = false, model = 'qwen2.5:3b') {
    console.log('=== 发送知识库聊天请求 ===');
    console.log('用户消息:', message);
    console.log('联网搜索:', webSearch);
    console.log('使用模型:', model);

    const requestData = {
      message: message.toString(),
      model: model,
      temperature: 0.7,
      web_search: webSearch
    };

    // 返回原始的fetch请求，以支持流式输出
    return fetch('/api/knowledge-chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestData)
    });
  },

  /**
   * 获取知识图谱数据
   * @returns {Promise}
   */
  getKnowledgeGraph() {
    return axios.get('/api/knowledge-chat/graph');
  },
  
  /**
   * 上传文件到知识库
   * @param {File} file - 要上传的文件
   * @param {Object} options - 附加选项
   * @returns {Promise}
   */
  uploadDocument(file, options = {}) {
    const formData = new FormData();
    formData.append('file', file);
    
    if (options.description) {
      formData.append('description', options.description);
    }
    
    if (options.tags) {
      formData.append('tags', options.tags);
    }
    
    return axios.post('/api/knowledge-graph/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  /**
   * 获取知识库文档列表
   * @returns {Promise}
   */
  getDocumentsList() {
    return axios.get('/api/knowledge-graph/documents');
  }
}
