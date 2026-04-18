import axios from 'axios'
import { ElMessage } from 'element-plus'
import { BACKEND_PORT } from '../port_config.js'

// 动态获取后端端口
let backendPort = BACKEND_PORT // 首先使用配置文件中的端口

// 浏览器中可能变更过端口，优先使用localStorage值
const savedPort = localStorage.getItem('backendPort')
if (savedPort && !isNaN(parseInt(savedPort))) {
    backendPort = parseInt(savedPort)
    console.log(`从 localStorage 获取到后端端口: ${backendPort}`)
}

// 端口超出范围时使用默认端口
if (backendPort <= 0 || backendPort > 65535) {
    console.warn(`端口范围无效: ${backendPort}, 使用默认端口8001`)
    backendPort = 8001
}

console.log(`当前使用的后端端口: ${backendPort}`)

// 创建 axios 实例 - 修复路径重复问题
const service = axios.create({
    // 采用空的baseURL，避免与前端代码中的路径前缀重复
    baseURL: '', // 清除baseURL，因为前端代码中已经包含/api前缀
    timeout: 180000, // 超时时间为3分钟
    headers: {
        'Accept': 'application/json'
    },
    // 增强重试机制
    retry: 5, // 增加重试次数
    retryDelay: 2000, // 增加重试间隔
    retryCondition: (error) => {
        return axios.isAxiosError(error) && !error.response;
    }
})

// 请求拦截器
service.interceptors.request.use(
    config => {
        console.log('发送请求:', {
            url: config.url,
            method: config.method,
            data: config.data
        })
        return config
    },
    error => {
        console.error('请求错误:', error)
        return Promise.reject(error)
    }
)

// 响应拦截器
service.interceptors.response.use(
    response => {
        console.log('收到原始响应:', response)
        const res = response.data

        // 图像分析特殊处理：如果包含persons和detected字段，这是图像识别的直接响应
        if (res.persons !== undefined && res.detected !== undefined) {
            console.log('识别为图像分析响应，直接返回')
            return res
        }

        // 如果响应是直接的内容
        if (res.content !== undefined) {
            return res
        }

        // 如果响应包含 success 字段
        if (res.success !== undefined) {
            if (res.success === false) {
                console.error('业务处理失败:', res.message || res.error)
                ElMessage.error(res.message || res.error || '操作失败')
                return Promise.reject(new Error(res.message || res.error || '操作失败'))
            }

            // 特殊处理：如果是图像分析响应，检查data字段内是否包含persons结构
            if (res.data && res.data.persons !== undefined && res.data.detected !== undefined) {
                console.log('从success.data中提取图像分析响应')
                return res.data
            }

            // 如果成功，返回 data 字段
            return res.data || res
        }

        // 如果响应包含 error 字段
        if (res.error) {
            console.error('响应包含错误:', res.error)
            ElMessage.error(res.error)
            return Promise.reject(new Error(res.error))
        }

        // 其他情况直接返回响应数据
        return res
    },
    error => {
        console.error('响应错误:', error.response || error)

        // 处理超时错误
        if (error.code === 'ECONNABORTED') {
            ElMessage.error('请求超时，请重试')
            return Promise.reject(error)
        }

        // 处理网络错误
        if (!error.response) {
            ElMessage.error('网络连接失败，请检查网络')
            return Promise.reject(error)
        }

        // 处理HTTP错误
        const status = error.response.status
        const errorMsg = error.response.data ? error.response.data.detail || error.response.data.message : error.message

        switch (status) {
            case 422:
                console.error('参数验证失败:', error.response.data)
                ElMessage.error('请求参数验证失败，请检查输入')
                break
            case 500:
                console.error('服务器错误:', errorMsg)
                ElMessage.error(`服务器错误: ${errorMsg}`)
                break
            default:
                console.error(`HTTP错误 ${status}:`, errorMsg)
                ElMessage.error(errorMsg || '请求失败')
        }

        return Promise.reject(error)
    }
)

// 添加请求重试拦截器
service.interceptors.response.use(undefined, async(err) => {
    const config = err.config;

    if (!config || !config.retry) return Promise.reject(err);

    config.__retryCount = config.__retryCount || 0;

    if (config.__retryCount >= config.retry) {
        return Promise.reject(err);
    }

    config.__retryCount += 1;

    const backoff = new Promise(resolve => {
        setTimeout(() => {
            resolve();
        }, config.retryDelay || 1000);
    });

    await backoff;
    return service(config);
});

export default service