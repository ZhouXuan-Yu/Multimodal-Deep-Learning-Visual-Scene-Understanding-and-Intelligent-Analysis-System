// 灾害检测服务模块
// 使用fetch API直接与后端通信

/**
 * 灾害检测服务
 * 封装了与火灾检测相关的API调用
 */
const disasterDetectionService = {
    /**
     * 获取API URL
     * @param {string} path API路径
     * @returns {string} 完整的API URL
     */
    getApiUrl(path) {
        // 确保路径以/开头
        const apiPath = path.startsWith('/') ? path : `/${path}`;
        // 添加/api前缀（后端需要）
        const fullUrl = `/api${apiPath}`;
        console.log(`构建API URL: 原始路径=${path}, 处理后=${fullUrl}`);
        return fullUrl;
    },

    /**
     * 上传视频进行火灾检测
     * @param {FormData} formData 包含视频文件和参数的表单数据
     * @returns {Promise} 上传结果
     */
    async uploadVideoForDetection(formData) {
        try {
            const response = await fetch(this.getApiUrl('fire_detection_direct/upload-video'), {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `服务器错误 (${response.status})` }));
                throw new Error(errorData.detail || `上传失败: 服务器返回状态码 ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('视频上传失败:', error);
            throw error;
        }
    },

    /**
     * 获取视频处理状态
     * @param {string} processId 处理ID
     * @returns {Promise} 处理状态
     */
    async getVideoProcessingStatus(processId) {
        try {
            const response = await fetch(this.getApiUrl(`fire_detection_direct/video-status/${processId}`));

            if (!response.ok) {
                throw new Error(`获取处理状态失败: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('获取视频处理状态失败:', error);
            throw error;
        }
    },

    /**
     * 获取视频处理结果
     * @param {string} processId 处理ID
     * @returns {Promise} 处理结果
     */
    async getVideoResults(processId) {
        try {
            const response = await fetch(this.getApiUrl(`fire_detection_direct/detection-results/${processId}`));

            if (!response.ok) {
                throw new Error(`获取结果失败: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('获取视频处理结果失败:', error);
            throw error;
        }
    },

    /**
     * 上传图像进行火灾检测
     * @param {FormData} formData 包含图像文件和参数的表单数据
     * @returns {Promise} 检测结果
     */
    async detectImage(formData) {
        try {
            const response = await fetch(this.getApiUrl('fire_detection_direct/detect-image'), {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `服务器错误 (${response.status})` }));
                throw new Error(errorData.detail || `处理失败: 服务器返回状态码 ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('图像处理失败:', error);
            throw error;
        }
    },

    /**
     * 发送摄像头帧进行火灾检测
     * @param {FormData} formData 包含图像帧和参数的表单数据
     * @returns {Promise} 检测结果
     */
    async detectCameraFrame(formData) {
        try {
            const response = await fetch(this.getApiUrl('fire_detection_direct/detect-camera'), {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`摄像头帧处理失败: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('摄像头帧处理失败:', error);
            throw error;
        }
    },

    /**
     * 获取历史检测记录
     * @returns {Promise} - 历史记录列表
     */
    async getDetectionHistory() {
        try {
            const response = await fetch(this.getApiUrl('fire_detection_direct/history'));

            if (!response.ok) {
                throw new Error(`获取历史记录失败: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('获取历史记录失败:', error);
            throw error;
        }
    }
};

export default disasterDetectionService;