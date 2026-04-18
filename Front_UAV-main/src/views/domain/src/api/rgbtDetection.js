import request from '../utils/request'

// 可见光-热微小物体检测API
export const rgbtDetectionApi = {
    // 检测物体
    async detectObjects(formData) {
        try {
            const response = await request.post('/rgbt-detection/detect', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            })
            return response
        } catch (error) {
            console.error('RGB-T检测失败:', error)
            throw error
        }
    },

    // 处理视频对
    async processVideoPair(formData) {
        try {
            const response = await request.post('/rgbt-detection/process-video-pair', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            })
            return response
        } catch (error) {
            console.error('处理RGB-T视频对失败:', error)
            throw error
        }
    },

    // 获取检测历史
    async getHistory() {
        try {
            const response = await request.get('/rgbt-detection/history')
            return response.history || []
        } catch (error) {
            console.error('获取RGB-T检测历史失败:', error)
            return []
        }
    },

    // 获取图像二进制数据
    async getImageBlob(imagePath) {
        try {
            if (!imagePath) return null

            // 提取图片ID和类型
            const match = imagePath.match(/result_([a-f0-9-]+)(_fusion|_thermal)?\.jpg$/)
            if (!match) return null

            const imageId = match[1]
            const imageType = match[2] ? match[2].substring(1) : 'original'

            // 使用getImageById API获取图片二进制数据
            const response = await request.get(`/rgbt-detection/image/${imageId}/${imageType}`, {
                responseType: 'blob'
            })

            return URL.createObjectURL(response)
        } catch (error) {
            console.error('获取图片二进制数据失败:', error)
            return null
        }
    },

    // 使用base64获取图片
    async getImageBase64(imagePath) {
        try {
            if (!imagePath) return null

            // 提取图片ID和类型
            const match = imagePath.match(/result_([a-f0-9-]+)(_fusion|_thermal)?\.jpg$/)
            if (!match) return null

            const imageId = match[1]
            const imageType = match[2] ? match[2].substring(1) : 'original'

            // 获取base64编码的图片
            const response = await request.get(`/rgbt-detection/image/${imageId}/${imageType}/base64`)

            if (response && response.data) {
                return `data:image/jpeg;base64,${response.data}`
            }
            return null
        } catch (error) {
            console.error('获取base64图片失败:', error)
            return null
        }
    }
}