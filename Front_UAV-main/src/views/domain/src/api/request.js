import axios from 'axios'
import { ElMessage } from 'element-plus'
import { BACKEND_PORT } from '../port_config.js'

// 获取后端端口
const backendPort = BACKEND_PORT || 8081

// 创建axios实例
const service = axios.create({
    baseURL: `http://localhost:${backendPort}/api`,
    timeout: 180000, // 超时时间为3分钟
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
})

// 请求拦截器
service.interceptors.request.use(
    config => {
        // 打印请求信息
        console.log('============================')
        console.log('【前端请求】发送请求给后端:')
        console.log(`URL: ${config.url}`)
        console.log(`方法: ${config.method?.toUpperCase()}`)
        console.log('请求数据:', config.data)
        console.log('查询参数:', config.params)
        console.log('============================')

        return config
    },
    error => {
        console.error('请求发送失败:', error)
        return Promise.reject(error)
    }
)

// 响应拦截器
service.interceptors.response.use(
    response => {
        console.log('收到原始响应:', response)
            // 直接返回响应数据，不进行额外处理
        return response.data
    },
    error => {
        if (error.response) {
            console.error('API响应错误:', error.response.data)
            ElMessage.error((error.response.data && error.response.data.message) || '请求失败')
        } else if (error.request) {
            console.error('网络连接失败:', error.request)
            ElMessage.error('网络连接失败')
        } else {
            console.error('请求配置错误:', error.message)
            ElMessage.error('请求配置错误')
        }
        return Promise.reject(error)
    }
)

// 导出封装好的请求方法
export const get = (url, params = {}, config = {}) => {
    console.log(`[API] 发送GET请求: ${url}`, params)
    return service({
        method: 'get',
        url,
        params,
        ...config
    })
}

export const post = (url, data = {}, config = {}) => {
    console.log(`[API] 发送POST请求: ${url}`, data)
    return service({
        method: 'post',
        url,
        data,
        ...config
    })
}

export const put = (url, data = {}, config = {}) => {
    return service({
        method: 'put',
        url,
        data,
        ...config
    })
}

export const del = (url, params = {}, config = {}) => {
    return service({
        method: 'delete',
        url,
        params,
        ...config
    })
}

// 导出request实例
export { service as request }

export default {
    get,
    post,
    put,
    del
}