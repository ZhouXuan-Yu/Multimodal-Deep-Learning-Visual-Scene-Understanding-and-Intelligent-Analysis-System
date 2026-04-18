import axios from 'axios';

/**
 * 可见光-热微小物体检测服务
 * 处理与后端API的交互，包括图像和视频上传、处理和结果检索
 */
const rgbtDetectionService = {
  /**
   * 处理可见光和热成像图片
   * @param {FormData} formData 包含RGB图像和热成像图像的表单数据
   * @returns {Promise} 处理结果的Promise
   */
  async processImages(formData) {
    try {
      const response = await axios.post('/api/rgbt/process-images', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response.data;
    } catch (error) {
      console.error('处理图像时出错:', error);
      throw error;
    }
  },

  /**
   * 处理可见光和热成像视频
   * @param {FormData} formData 包含RGB视频和热成像视频的表单数据
   * @returns {Promise} 处理结果的Promise，包含任务ID
   */
  async processVideos(formData) {
    try {
      const response = await axios.post('/api/rgbt/process-videos', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response.data;
    } catch (error) {
      console.error('处理视频时出错:', error);
      throw error;
    }
  },

  /**
   * 检查视频处理任务状态
   * @param {string} taskId 任务ID
   * @returns {Promise} 任务状态信息
   */
  async checkVideoTaskStatus(taskId) {
    try {
      const response = await axios.get(`/api/rgbt/task-status/${taskId}`);
      return response.data;
    } catch (error) {
      console.error('检查任务状态时出错:', error);
      throw error;
    }
  },

  /**
   * 获取视频处理结果
   * @param {string} taskId 任务ID
   * @returns {Promise} 处理结果数据
   */
  async getVideoResult(taskId) {
    try {
      const response = await axios.get(`/api/rgbt/video-result/${taskId}`);
      return response.data;
    } catch (error) {
      console.error('获取视频结果时出错:', error);
      throw error;
    }
  },

  /**
   * 模拟检测结果（用于前端开发测试）
   * @param {string} mode 'image' 或 'video'
   * @returns {Object} 模拟的检测结果
   */
  mockDetectionResult(mode = 'image') {
    if (mode === 'image') {
      return {
        rgb_image: {
          processed: '/mock/processed_rgb_image.jpg',
          detections: [
            { x: 100, y: 100, width: 50, height: 50, class: '人员', confidence: 0.92 },
            { x: 300, y: 200, width: 40, height: 60, class: '车辆', confidence: 0.85 }
          ]
        },
        thermal_image: {
          processed: '/mock/processed_thermal_image.jpg',
          detections: [
            { x: 105, y: 105, width: 45, height: 48, class: '人员', confidence: 0.89 },
            { x: 305, y: 205, width: 38, height: 58, class: '车辆', confidence: 0.82 }
          ]
        }
      };
    } else {
      return {
        task_id: 'mock-task-123',
        status: 'completed',
        progress: 100,
        rgb_video: {
          processed: '/mock/processed_rgb_video.mp4'
        },
        thermal_video: {
          processed: '/mock/processed_thermal_video.mp4'
        }
      };
    }
  }
};

export default rgbtDetectionService;
