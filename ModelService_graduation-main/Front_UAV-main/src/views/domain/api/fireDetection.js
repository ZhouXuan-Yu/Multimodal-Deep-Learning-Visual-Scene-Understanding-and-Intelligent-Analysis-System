/**
 * 火灾检测API接口
 */
import { post, get } from './request';
import { API_BASE_URL } from './config';

/**
 * 火灾检测API
 */
export const fireDetectionApi = {
    /**
     * 上传视频进行火灾检测
     * @param {FormData} formData - 包含视频文件和检测参数的表单数据
     * @returns {Promise<Object>} - 检测任务信息
     */
    uploadVideo(formData) {
        return post('/fire_detection_direct/upload-video', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },

    /**
     * 图像火灾检测
     * @param {FormData} formData - 包含图像文件和检测参数的表单数据
     * @returns {Promise<Object>} - 检测结果
     */
    detectImage(formData) {
        return post('/fire_detection_direct/detect-image', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },

    /**
     * 获取视频处理状态
     * @param {string} processId - 处理任务ID
     * @returns {Promise<Object>} - 处理状态信息
     */
    getVideoStatus(processId) {
        return get(`/fire_detection_direct/video-status/${processId}`);
    },

    /**
     * 获取检测结果
     * @param {string} processId - 处理任务ID
     * @returns {Promise<Object>} - 检测结果数据
     */
    getDetectionResults(processId) {
        return get(`/fire_detection_direct/detection-results/${processId}`);
    },

    /**
     * 获取处理后的视频URL
     * @param {string} processId - 处理任务ID
     * @returns {string} - 处理后视频的URL
     */
    getResultVideoUrl(processId) {
        return `${API_BASE_URL}/fire_detection_direct/result-video/${processId}`;
    }
};

export default fireDetectionApi;