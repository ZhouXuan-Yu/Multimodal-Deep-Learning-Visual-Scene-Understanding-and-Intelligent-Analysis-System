/**
 * 夜间增强识别服务
 * 提供与低光图像增强和目标检测相关的API调用
 */
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8082/api';

const nightEnhancementService = {
  /**
   * 上传图片进行低光增强和目标检测
   * @param {FormData} formData - 包含图片的表单数据
   * @returns {Promise} - 返回处理结果
   */
  async processImage(formData) {
    try {
      const response = await axios.post(`${API_BASE_URL}/night-detection/process-image`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response.data;
    } catch (error) {
      console.error('图片处理请求失败:', error);
      throw error;
    }
  },

  /**
   * 上传视频进行处理
   * @param {FormData} formData - 包含视频的表单数据
   * @returns {Promise} - 返回处理ID
   */
  async processVideo(formData) {
    try {
      const response = await axios.post(`${API_BASE_URL}/night-detection/process-video`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response.data;
    } catch (error) {
      console.error('视频上传请求失败:', error);
      throw error;
    }
  },

  /**
   * 获取视频处理状态
   * @param {string} processId - 处理ID
   * @returns {Promise} - 返回处理状态信息
   */
  async getVideoStatus(processId) {
    try {
      const response = await axios.get(`${API_BASE_URL}/night-detection/video-status/${processId}`);
      return response.data;
    } catch (error) {
      console.error('获取视频状态失败:', error);
      throw error;
    }
  },

  /**
   * 从URL中获取处理结果图片
   * @param {string} imageUrl - 图片URL
   * @returns {Promise} - 返回图片数据
   */
  async getImageResult(imageUrl) {
    try {
      const response = await axios.get(imageUrl, {
        responseType: 'blob'
      });
      return URL.createObjectURL(response.data);
    } catch (error) {
      console.error('获取图片结果失败:', error);
      throw error;
    }
  },

  /**
   * 检查文件是否存在
   * @param {string} url - 文件URL
   * @returns {Promise<boolean>} - 返回文件是否存在
   */
  async checkFileExists(url) {
    try {
      const response = await axios.head(url);
      return response.status === 200;
    } catch (error) {
      return false;
    }
  },

  /**
   * 生成可能的视频文件路径
   * @param {string} processId - 处理ID
   * @param {string} originalFileName - 原始文件名
   * @returns {Array<string>} - 返回可能的视频文件路径列表
   */
  generatePossibleVideoPatterns(processId, originalFileName) {
    const baseFileName = originalFileName.split('.')[0];
    const possiblePatterns = [
      `${API_BASE_URL}/night-detection/results/${processId}/output.mp4`,
      `${API_BASE_URL}/night-detection/results/${processId}/output.avi`,
      `${API_BASE_URL}/night-detection/results/${processId}/${baseFileName}_enhanced.mp4`,
      `${API_BASE_URL}/night-detection/results/${processId}/${baseFileName}_enhanced.avi`,
      `${API_BASE_URL}/night-detection/results/${processId}/${baseFileName}_processed.mp4`,
      `${API_BASE_URL}/night-detection/results/${processId}/${baseFileName}_processed.avi`
    ];
    return possiblePatterns;
  }
};

export default nightEnhancementService;
