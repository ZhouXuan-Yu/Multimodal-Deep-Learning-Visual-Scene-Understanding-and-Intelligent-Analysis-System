import request from '../utils/request'

// 车牌监控API客户端
export const plateMonitoringApi = {
    // 上传图片进行车牌识别
    uploadImage(formData) {
        return request.post('/plate-monitoring/upload-image', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        })
    },

    // 设置目标车牌
    setTargetPlate(plateData) {
        return request.post('/plate-monitoring/set-target-plate', plateData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        })
    },

    // 上传视频进行分析
    uploadVideo(formData) {
        return request.post('/plate-monitoring/upload-video', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        })
    },

    // 获取视频处理状态
    getVideoStatus(processId) {
        return request.get(`/plate-monitoring/video-status/${processId}`)
    },

    // 获取当前目标车牌信息
    getTargetPlate() {
        return request.get('/plate-monitoring/target-plate')
    },

    // 清除目标车牌
    clearTargetPlate() {
        return request.post('/plate-monitoring/clear-target-plate')
    }
}