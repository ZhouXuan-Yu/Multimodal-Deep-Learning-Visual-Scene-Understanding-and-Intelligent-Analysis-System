/**
 * 视频追踪API接口
 */
import { post, get } from './request';
import { API_BASE_URL } from './config';

/**
 * 视频追踪API
 */
export const videoTrackingApi = {
    /**
     * 上传视频进行目标追踪
     * @param {FormData} formData - 包含视频文件和追踪参数的表单数据
     * @returns {Promise<Object>} - 追踪任务信息
     */
    uploadVideo(formData) {
        return post('/video-tracking/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },

    /**
     * 获取追踪状态
     * @param {string} trackingId - 追踪任务ID
     * @returns {Promise<Object>} - 追踪状态信息
     */
    getTrackingStatus(trackingId) {
        return get(`/video-tracking/status/${trackingId}`);
    },

    /**
     * 获取追踪结果
     * @param {string} trackingId - 追踪任务ID
     * @returns {Promise<Object>} - 追踪结果数据
     */
    getTrackingResult(trackingId) {
        return get(`/video-tracking/result/${trackingId}`);
    },

    /**
     * 获取处理后的视频
     * @param {string} trackingId - 追踪任务ID
     * @returns {string} - 处理后视频的URL
     */
    getProcessedVideoUrl(trackingId) {
        return `${API_BASE_URL}/video-tracking/processed-video/${trackingId}`;
    }
};

export default videoTrackingApi;