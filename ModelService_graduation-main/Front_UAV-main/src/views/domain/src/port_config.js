/**
 * 后端服务配置
 * 定义与后端API通信的端口和基础URL
 */

// 自动生成的端口配置文件 - 请勿手动修改
// 由vite.config.js于 2025-05-14T01:39:05.107Z 生成

// 后端API端口配置 - 确保与实际后端端口一致
export const BACKEND_PORT = 8082;

// 可以扩展添加其他配置
export const API_VERSION = 'v1';
export const USE_HTTPS = false;

// 获取完整的API基础URL
export function getBaseUrl() {
    const protocol = USE_HTTPS ? 'https' : 'http';
    return `${protocol}://localhost:${BACKEND_PORT}/api`;
}

/**
 * 构建API URL
 * @param {string} path - API路径
 * @returns {string} - 完整的API URL
 */
export function getApiUrl(path) {
    // 确保路径以/开头
    const apiPath = path.startsWith('/') ? path : `/${path}`;

    // 添加/api前缀（后端需要）
    const fullUrl = `/api${apiPath}`;
    console.log(`[port_config] 构建API URL: 原始路径=${path}, 处理后=${fullUrl}`);
    return fullUrl;
}

// 其他服务端口可以在这里添加
export const VIDEO_PORT = 8082;
export const STREAMING_PORT = 8083;

// 导出配置，便于其他模块使用
export default {
    BACKEND_PORT,
    getBaseUrl,
    getApiUrl
};