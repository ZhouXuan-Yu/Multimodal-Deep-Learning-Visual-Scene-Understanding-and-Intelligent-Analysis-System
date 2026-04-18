import axios from 'axios';

/**
 * 多状态数据融合服务
 * 封装了与数据融合相关的API调用
 */
const dataFusionService = {
  /**
   * 构建API URL
   * @param {string} path - API路径
   * @returns {string} - 完整URL
   */
  getApiUrl(path) {
    const baseUrl = '/api/data-fusion';
    return `${baseUrl}${path}`;
  },

  /**
   * 处理可见光和热成像图像融合
   * @param {FormData} formData - 包含可见光和热成像图片的表单数据
   * @returns {Promise} - 处理结果
   */
  processImageFusion(formData) {
    return axios.post(this.getApiUrl('/image-fusion'), formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },

  /**
   * 处理视频多模态融合
   * @param {FormData} formData - 包含视频的表单数据
   * @returns {Promise} - 处理结果，包含任务ID
   */
  processVideoFusion(formData) {
    return axios.post(this.getApiUrl('/video-fusion'), formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },

  /**
   * 获取视频融合处理状态
   * @param {string} taskId - 任务ID
   * @returns {Promise} - 处理状态
   */
  getVideoFusionStatus(taskId) {
    return axios.get(this.getApiUrl(`/video-status/${taskId}`));
  },

  /**
   * 获取视频融合结果
   * @param {string} taskId - 任务ID
   * @returns {Promise} - 处理结果
   */
  getVideoFusionResult(taskId) {
    return axios.get(this.getApiUrl(`/video-result/${taskId}`));
  },

  /**
   * 模拟融合图像生成（用于前端开发测试）
   * @returns {Object} 模拟的融合结果
   */
  mockFusionResult() {
    return {
      success: true,
      fusionImageUrl: '/mock/fusion_result.jpg',
      rgbImageUrl: '/mock/original_rgb.jpg',
      thermalImageUrl: '/mock/original_thermal.jpg',
      metadata: {
        fusionMethod: 'Deep Learning Fusion',
        processingTime: 1.24,
        enhancementLevel: 'high',
        resolution: '1920x1080'
      }
    };
  },

  /**
   * 获取可用的融合方法
   * @returns {Promise} - 融合方法列表
   */
  getFusionMethods() {
    return axios.get(this.getApiUrl('/fusion-methods'));
  },
  
  /**
   * 获取历史融合记录
   * @returns {Promise} - 历史记录列表
   */
  getFusionHistory() {
    return axios.get(this.getApiUrl('/history'));
  }
};

export default dataFusionService;
