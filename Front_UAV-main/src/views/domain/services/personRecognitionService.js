/**
 * 人物识别服务
 * 提供与人物特征识别相关的API调用
 */
import axios from 'axios';
import { BACKEND_PORT } from '../src/port_config.js';

// 获取后端API的基础URL
const getBaseUrl = () => {
    // 优先使用配置文件中的端口，保证与后端保持一致
    let port = BACKEND_PORT;

    // 仅用于调试：输出 localStorage 中的端口，帮助你发现端口不一致的问题
    const savedPort = localStorage.getItem('backendPort');
    if (savedPort && !isNaN(parseInt(savedPort))) {
        console.log(
            `[personRecognitionService] localStorage.backendPort = ${savedPort}（仅调试使用，实际请求仍使用 BACKEND_PORT=${BACKEND_PORT}）`
        );
    }

    // 检查端口是否在有效范围内
    if (port <= 0 || port > 65535) {
        console.warn(`[personRecognitionService] 端口范围无效: ${port}, 使用默认端口8082`);
        port = 8082;
    }

    const baseUrl = `http://localhost:${port}/api`;
    console.log(`[personRecognitionService] 使用后端基础URL: ${baseUrl}`);
    return baseUrl;
};

// 创建带有调试日志的axios实例
const axiosInstance = axios.create({
    baseURL: getBaseUrl(),
    timeout: 60000, // 增加超时时间到60秒
    headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
});

// 请求拦截器
axiosInstance.interceptors.request.use(
    config => {
        const finalBaseURL = config.baseURL || axiosInstance.defaults.baseURL;
        console.log('============================');
        console.log('[personRecognitionService] 发送请求到人物识别后端');
        console.log('[personRecognitionService] baseURL:', finalBaseURL);
        console.log('[personRecognitionService] url:', config.url);
        console.log('[personRecognitionService] method:', config.method);
        console.log('[personRecognitionService] 最终完整URL:', `${finalBaseURL}${config.url}`);
        console.log('[personRecognitionService] headers:', config.headers);
        console.log('[personRecognitionService] data:', config.data);
        console.log('============================');
        return config;
    },
    error => {
        console.error('[personRecognitionService] 请求在发送前出错:', error);
        return Promise.reject(error);
    }
);

// 响应拦截器
axiosInstance.interceptors.response.use(
    response => {
        if (process.env.NODE_ENV !== 'production') {
            console.log('[personRecognitionService] 请求成功, 状态码:', response.status);
            console.log('[personRecognitionService] 响应URL:', `${response.config.baseURL || axiosInstance.defaults.baseURL}${response.config.url}`);
        }
        return response;
    },
    error => {
        console.error('[personRecognitionService] 请求错误:', error.message);

        // 增强错误日志，区分不同阶段的问题
        if (error.response) {
            console.log('[personRecognitionService] 已收到响应但状态码非2xx');
            console.log('响应状态:', error.response.status);
            console.log('响应头:', error.response.headers);
            console.log('响应数据:', error.response.data);
        } else if (error.request) {
            console.log('[personRecognitionService] 请求已发送但**没有收到任何响应**（很可能是端口/地址不对或后端未启动）');
            console.log('请求对象:', error.request);
            if (error.config) {
                const finalBaseURL = error.config.baseURL || axiosInstance.defaults.baseURL;
                console.log('[personRecognitionService] 尝试访问的URL:', `${finalBaseURL}${error.config.url}`);
            }
        } else {
            console.log('[personRecognitionService] 在构造请求时出错:', error.message);
        }

        return Promise.reject(error);
    }
);

/**
 * 健康检查API
 * 检查后端服务是否正常运行
 * @returns {Promise} - 返回服务状态信息
 */
async function healthCheck() {
    try {
        const response = await axiosInstance.get('/health');
        return response.data;
    } catch (error) {
        console.error('健康检查失败:', error);
        throw error;
    }
}

/**
 * 上传图片进行人物特征分析
 * @param {FormData} formData - 包含图片的表单数据
 * @param {string} mode - 分析模式: 'normal' 或 'enhanced'
 * @returns {Promise} - 返回分析结果
 */
async function analyzeImage(formData, mode = 'normal') {
    try {
        // 确保表单数据中包含模式
        if (!formData.has('mode')) {
            formData.append('mode', mode);
        }

        console.log('发送图片分析请求:', {
            mode,
            hasFile: formData.has('file'),
            formData: Array.from(formData.entries())
        });

        // 确保formData包含正确的字段名称
        if (formData.has('file')) {
            // 参考前端项目2的API调用
            const response = await axiosInstance.post('/image-recognition/analyze', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });

            // 处理响应
            const data = response.data;
            console.log('图片分析响应:', data);

            // 检查是否为嵌套响应结构
            if (data.success && data.data) {
                // 处理嵌套结构 {success: true, data: {...}}
                return data.data;
            }

            return data;
        } else {
            throw new Error('表单数据中缺少文件');
        }
    } catch (error) {
        console.error('图片分析请求失败:', error);
        throw error;
    }
}

// 导出服务
export default {
    healthCheck,
    analyzeImage
};