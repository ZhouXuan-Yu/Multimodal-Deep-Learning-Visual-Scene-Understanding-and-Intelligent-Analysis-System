import request from './request'

export const imageRecognitionApi = {
    /**
     * ����ͼƬ
     * @param {FormData} formData - ����ͼƬ�ļ��ͷ���ģʽ�ı�������
     * @returns {Promise} ���ط������
     */
    analyzeImage(formData) {
        console.log('发送图片分析请求(域前端):', {
            mode: formData.get('mode'),
            hasFile: formData.has('file')
        })

        return request({
            url: '/image-recognition/analyze',
            method: 'post',
            data: formData,
            headers: {
                'Content-Type': 'multipart/form-data'
            },
            timeout: 400000
        }).then(res => {
            console.log('图片分析原始响应(res):', res)

            // 兼容两种返回结构：
            // 1) 直接返回 { detected, persons, ... }
            // 2) 标准包装 { success, message, data: { detected, persons, ... } }
            let data = res

            if (res && typeof res === 'object' && res.success !== undefined) {
                if (res.success === false) {
                    const errMsg = res.message || res.error || '图像分析失败'
                    console.error('图像分析业务错误:', errMsg)
                    throw new Error(errMsg)
                }
                if (res.data) {
                    data = res.data
                }
            }

            // 详细调试信息
            console.log('解包后的分析数据(data):', JSON.stringify(data))
            console.log('persons 数组:', data.persons ? JSON.stringify(data.persons) : 'undefined')

            if (data.persons && data.persons.length > 0) {
                console.log('第一个 person 对象:', JSON.stringify(data.persons[0]))
                console.log(
                    'person.bbox:',
                    data.persons[0].bbox
                        ? `${typeof data.persons[0].bbox} [${data.persons[0].bbox}]`
                        : 'undefined'
                )
            }

            return data
        }).catch(error => {
            console.error('图片分析请求失败:', error)
            throw error
        })
    },

    /**
     * �������
     * @returns {Promise} ���ؽ���״̬
     */
    healthCheck() {
        return request({
            url: '/image-recognition/health',
            method: 'get'
        })
    },

    /**
     * ��ȡ����ģ���б�
     * @returns {Promise} ����ģ���б�
     */
    getAvailableModels() {
        return request({
            url: '/image-recognition/models',
            method: 'get'
        })
    }
}