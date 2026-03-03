import { post, get, del } from './request';
import { getBaseUrl } from '../port_config.js';

/**
 * 路线规划API接口
 */
export const routePlanningApi = {
    /**
     * 创建路线规划
     * @param {Object} params - 路线规划参数
     * @returns {Promise<Object>} - 路线规划结果
     */
    getRoutePlan: (params) => {
        console.log('[routePlanningApi] 调用路线规划API，参数:', params);

        // 准备请求参数，确保与后端API格式一致
        const requestParams = {
            text: params.text || '',
            // 默认使用轻量级纯文本模型，降低延迟和资源占用
            model: params.model || 'qwen2.5:3b'
        };

        // 如果有历史路线，添加到请求参数
        if (params.historical_route) {
            requestParams.historical_route = params.historical_route;
        }

        console.log('[routePlanningApi] 发送POST请求到: /route/plan');

        // 调用后端API（与后端 60 秒超时保持同一量级，这里稍长一些以容错）
        return post('/route/plan', requestParams, {
            timeout: 90000 // 90 秒：避免长时间无响应
        }).then(response => {
            console.log('[routePlanningApi] 收到路线规划响应:', response);
            return response;
        }).catch(error => {
            console.error('[routePlanningApi] 路线规划请求失败:', error);
            throw error;
        });
    },

    /**
     * 获取路线规划历史记录
     * @returns {Promise<Array>} - 历史记录列表
     */
    getHistory: () => {
        console.log('[routePlanningApi] 获取路线规划历史记录');
        return get('/route/history');
    },

    /**
     * 删除路线规划历史记录
     * @param {string} recordId - 历史记录ID
     * @returns {Promise<boolean>} - 是否成功删除
     */
    deleteHistory: (recordId) => {
        console.log(`[routePlanningApi] 删除历史记录: ${recordId}`);
        return del(`/route/history/${recordId}`);
    },

    /**
     * 获取地理编码
     * @param {string} address - 地址
     * @returns {Promise<Object>} - 地理编码（经纬度）
     */
    getGeocoding: (address) => {
        if (!address) {
            return Promise.reject(new Error('地址不能为空'));
        }
        return get(`/route/location?address=${encodeURIComponent(address)}`);
    },

    /**
     * 保存路线
     * @param {Object} routeData - 路线数据
     * @returns {Promise<Object>} - 操作结果
     */
    saveRoute: (routeData) => {
        return post('/route/save', routeData);
    },

    /**
     * 获取路线详情
     * @param {string} start - 起点
     * @param {string} end - 终点
     * @param {Object} preferences - 路线偏好
     * @param {string} routeType - 路线类型
     * @returns {Promise<Object>} - 路线详情
     */
    getRoutePlanDetails: (start, end, preferences, routeType) => {
        return get('/route/detail', {
            start,
            end,
            preferences: JSON.stringify(preferences),
            route_type: routeType
        });
    },

    /**
     * 获取收藏的路线
     * @returns {Promise<Array>} - 收藏列表
     */
    getFavorites: () => {
        console.log('[routePlanningApi] 获取收藏列表');
        return get('/route/favorites');
    },

    /**
     * 添加路线到收藏
     * @param {Object} route - 路线信息
     * @returns {Promise<Object>} - 添加结果
     */
    addFavorite: (route) => {
        console.log('[routePlanningApi] 添加路线到收藏:', route);
        return post('/route/favorites', route);
    },

    /**
     * 从收藏中移除路线
     * @param {string} routeId - 路线ID
     * @returns {Promise<boolean>} - 是否成功移除
     */
    removeFavorite: (routeId) => {
        console.log(`[routePlanningApi] 从收藏中移除路线: ${routeId}`);
        return del(`/route/favorites/${routeId}`);
    },

    /**
     * 导出路线
     * @param {Object} data - 导出数据
     * @returns {Promise<Object>} - 导出结果
     */
    exportRoute: (data) => {
        return post('/route/export', data);
    },

    /**
     * 分享路线
     * @param {string} routeId - 路线ID
     * @returns {Promise<Object>} - 分享结果（包含分享链接）
     */
    shareRoute: (routeId) => {
        return post('/route/share', { routeId });
    },

    /**
     * 根据文本获取路线
     * @param {string} text - 查询文本
     * @param {AbortSignal} signal - 取消请求信号
     * @returns {Promise<Object>} - 路线数据
     */
    getPlanByText: (text, signal) => {
        return post('/route/plan_by_text', { text }, { signal });
    },

    // 原本的流式路线规划（/route/plan/stream）已下线，统一改为一次性非流式调用。

    /**
     * 获取交通状况
     * @param {string} cityName - 城市名称
     * @returns {Promise<Object>} - 交通状况信息
     */
    getTrafficInfo: (cityName) => {
        return get('/route/traffic', { city: cityName });
    }
};

export default routePlanningApi;