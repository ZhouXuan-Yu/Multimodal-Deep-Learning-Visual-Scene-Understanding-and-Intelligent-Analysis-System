/**
 * 车辆监控相关API服务
 */
import axios from 'axios';

export default {
  /**
   * 检查车牌识别服务状态
   * @returns {Promise}
   */
  checkStatus() {
    return axios.get('/api/plate-recognition/status');
  },
  
  /**
   * 上传图片进行车牌识别
   * @param {FormData} formData - 包含图片的表单数据
   * @returns {Promise}
   */
  uploadImage(formData) {
    return axios.post('/api/plate-recognition/upload-image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  /**
   * 上传视频进行分析
   * @param {FormData} formData - 包含视频的表单数据
   * @returns {Promise}
   */
  uploadVideo(formData) {
    return axios.post('/api/plate-recognition/upload-video', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  /**
   * 上传视频进行车牌监控
   * @param {FormData} formData - 包含视频和目标车牌的表单数据
   * @returns {Promise}
   */
  uploadMonitorVideo(formData) {
    return axios.post('/api/plate-monitoring/upload-video', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  /**
   * 获取视频处理状态
   * @param {string} processId - 处理ID
   * @returns {Promise}
   */
  getVideoStatus(processId) {
    return axios.get(`/api/plate-recognition/video-status/${processId}`);
  },
  
  /**
   * 获取视频处理结果
   * @param {string} processId - 处理ID
   * @returns {Promise}
   */
  getVideoResults(processId) {
    return axios.get(`/api/plate-recognition/video-results/${processId}`);
  },
  
  /**
   * 获取监控视频处理状态
   * @param {string} processId - 处理ID
   * @returns {Promise}
   */
  getMonitorStatus(processId) {
    return axios.get(`/api/plate-monitoring/status/${processId}`);
  },
  
  /**
   * 获取监控视频处理结果
   * @param {string} processId - 处理ID
   * @returns {Promise}
   */
  getMonitorResults(processId) {
    return axios.get(`/api/plate-monitoring/results/${processId}`);
  },
  
  /**
   * 开始车牌识别服务
   * @returns {Promise}
   */
  startService() {
    return axios.post('/api/plate-recognition/start-service');
  },
  
  /**
   * 停止车牌识别服务
   * @returns {Promise}
   */
  stopService() {
    return axios.post('/api/plate-recognition/stop-service');
  }
}
