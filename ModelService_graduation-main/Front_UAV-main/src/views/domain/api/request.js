import axios from 'axios'
import { ElMessage } from 'element-plus'
import { API_BASE_URL, API_TIMEOUT } from './config'

// 设置文档编码
// @ts-check
// -*- coding: utf-8 -*-

// 创建axios实例
const instance = axios.create({
    baseURL: API_BASE_URL, // 使用配置文件中的API基础URL
    timeout: API_TIMEOUT, // 使用配置文件中的超时设置
    headers: {
        'Content-Type': 'application/json;charset=UTF-8',
        'Accept': 'application/json;charset=UTF-8',
    }
})

// 请求拦截器 - 改进URL处理逻辑，确保不出现错误的API路径
instance.interceptors.request.use(
    config => {
        // 添加完整的调试信息打印
        console.log('============================')
        console.log('【前端请求】发送请求给后端:')
        console.log('【前端请求】基础URL:', instance.defaults.baseURL)
        console.log('【前端请求】请求URL:', config.url)

        // URL处理 - 检查并修复可能导致问题的URL路径
        let url = config.url || '';

        // 1. 先移除开头的斜杠，避免与baseURL拼接出现双斜杠
        if (url.startsWith('/')) {
            url = url.substring(1);
        }

        // 2. 检查是否以'api/'开头，如果是则移除
        // 这是因为baseURL已经包含了'/api'
        if (url.startsWith('api/')) {
            url = url.substring(4);
        }

        // 3. 检查并移除可能的重复路径段
        // 例如，如果baseURL是'/api'，并且url是'/api/route/plan'，则会导致'/api/api/route/plan'
        const apiPrefix = 'api/';
        if (url.includes(apiPrefix) && !url.startsWith(apiPrefix)) {
            const apiIndex = url.indexOf(apiPrefix);
            url = url.substring(apiIndex + 4); // 移除'api/'
        }

        // 4. 检查并移除重复的路径段，比如 'route/route/'
        const pathSegments = url.split('/');
        for (let i = 1; i < pathSegments.length; i++) {
            if (pathSegments[i] === pathSegments[i - 1]) {
                pathSegments.splice(i, 1);
                i--; // 调整索引，因为数组长度减少了
            }
        }
        url = pathSegments.join('/');

        // 更新配置中的URL
        config.url = url;

        // 5. 处理请求头的特殊配置，确保CORS请求正确
        config.headers = {
            ...config.headers,
            'X-Requested-With': 'XMLHttpRequest'
        };

        // 如果是POST或PUT请求，确保内容类型设置正确
        if (config.method === 'post' || config.method === 'put') {
            if (!config.headers['Content-Type']) {
                config.headers['Content-Type'] = 'application/json;charset=UTF-8';
            }
        }

        // 打印最终的URL信息，包含baseURL以便于调试
        console.log(`完整请求地址: ${config.baseURL}/${config.url}`)
        console.log(`方法: ${config.method.toUpperCase()}`)
        console.log('请求头:', JSON.stringify(config.headers))
        console.log('请求数据:', config.data)
        console.log('查询参数:', config.params)
        console.log('请求配置:', JSON.stringify({
            timeout: config.timeout,
            withCredentials: config.withCredentials
        }))
        console.log('============================')

        return config
    },
    error => {
        // 对请求错误做些什么
        console.error('【请求拦截器】请求发送失败:', error)
        return Promise.reject(error)
    }
)

// 响应拦截器
instance.interceptors.response.use(
    response => {
        // 打印完整的响应信息
        console.log('============================')
        console.log('【前端接收】收到后端响应:')
        console.log(`完整URL: ${response.config.baseURL}${response.config.url}`)
        console.log(`状态: ${response.status} ${response.statusText}`)
        console.log('响应数据:', response.data)
        console.log('============================')

        // 处理返回的数据
        const res = response.data

        // 如果响应是直接的内容或API直接返回的数据
        if (!res || typeof res !== 'object' || res.content !== undefined) {
            return res
        }

        // 处理标准响应格式
        if (res.success !== undefined) {
            if (res.success === false) {
                const errorMsg = res.message || res.error || '操作失败'
                console.error('【业务错误】:', errorMsg)
                ElMessage.error(errorMsg)
                return Promise.reject(new Error(errorMsg))
            }
            return res
        }

        // 如果响应包含error字段
        if (res.error) {
            console.error('【响应错误】:', res.error)
            ElMessage.error(res.error)
            return Promise.reject(new Error(res.error))
        }

        // 其他情况直接返回响应数据
        return res
    },
    error => {
        // 打印完整的错误信息
        console.log('============================')
        console.log('【前端错误】响应处理错误:')
        console.log(`错误消息: ${error.message}`)

        if (error.response) {
            console.log(`状态码: ${error.response.status} ${error.response.statusText}`)
            console.log('响应数据:', error.response.data)
            console.log('请求URL:', error.config.url)
            console.log('请求方法:', error.config.method.toUpperCase())
            console.log('请求数据:', error.config.data)
        } else if (error.request) {
            console.log('未收到响应，请求内容:', error.request)
            if (error.config && error.config.url) {
                console.log('请求URL:', error.config.url)
            }
            if (error.config && error.config.method) {
                console.log('请求方法:', error.config.method.toUpperCase())
            }
            if (error.config && error.config.data) {
                console.log('请求数据:', error.config.data)
            }
            if (error.message && (error.message.includes('Network') || error.message.includes('CORS'))) {
                console.error('可能存在网络连接问题或跨域限制问题')
            }
        } else {
            console.log('请求配置错误:', error.message)
        }
        console.log('============================')

        // 处理错误显示
        let errorMsg = '请求失败'
        if (error.response && error.response.data) {
            if (typeof error.response.data === 'string') {
                errorMsg = error.response.data
            } else if (error.response.data.error) {
                errorMsg = error.response.data.error
            } else if (error.response.data.message) {
                errorMsg = error.response.data.message
            }
        } else if (error.message) {
            errorMsg = error.message

            if (error.message.includes('timeout')) {
                errorMsg = '请求超时，请稍后再试'
            } else if (error.message.includes('Network')) {
                errorMsg = '网络连接失败，请检查网络设置'
            }
        }

        ElMessage.error('请求错误: ' + errorMsg)
        return Promise.reject(error)
    }
)

// 导出封装好的请求方法
export const request = instance

/**
 * 封装GET请求
 * @param {string} url - 请求URL
 * @param {Object} params - 请求参数
 * @param {Object} config - 其他配置
 * @returns {Promise} - axios promise
 */
export const get = (url, params = {}, config = {}) => {
    return instance({
        method: 'get',
        url,
        params,
        ...config
    })
}

/**
 * 封装POST请求
 * @param {string} url - 请求URL
 * @param {Object} data - 请求数据
 * @param {Object} config - 其他配置
 * @returns {Promise} - axios promise
 */
export const post = (url, data = {}, config = {}) => {
    console.log(`[post] 发送POST请求到: ${url}`, data);

    return instance({
        method: 'post',
        url,
        data,
        ...config
    }).catch(error => {
        console.error(`[post] POST请求失败: ${url}`, error);
        throw error;
    })
}

/**
 * 封装PUT请求
 * @param {string} url - 请求URL
 * @param {Object} data - 请求数据
 * @param {Object} config - 其他配置
 * @returns {Promise} - axios promise
 */
export const put = (url, data = {}, config = {}) => {
    return instance({
        method: 'put',
        url,
        data,
        ...config
    })
}

/**
 * 封装DELETE请求
 * @param {string} url - 请求URL
 * @param {Object} params - 请求参数
 * @param {Object} config - 其他配置
 * @returns {Promise} - axios promise
 */
export const del = (url, params = {}, config = {}) => {
    return instance({
        method: 'delete',
        url,
        params,
        ...config
    })
}

// 导出所有请求方法
export default {
    request,
    get,
    post,
    put,
    del
}