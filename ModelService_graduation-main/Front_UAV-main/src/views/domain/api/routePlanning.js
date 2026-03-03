import { post, get, del } from './request';

/**
 * 路线规划API接口
 */
export const routePlanningApi = {
    /**
     * 创建路线规划
     * @param {Object} params - 路线规划参数
     * @returns {Promise<Object>} - 路线规划结果
     */
    planRoute: (params) => {
        console.log('[routePlanningApi] 调用路线规划API，原始参数:', params);

        // 准备请求参数，确保与后端API格式一致
        const requestParams = {
            text: params.text || '',
            model: params.model || 'qwen3-vl:8b'
        };

        // 如果有历史路线，添加到请求参数
        if (params.historical_route) {
            requestParams.historical_route = params.historical_route;
        }

        console.log('[routePlanningApi] 请求参数处理后:', requestParams);
        console.log('[routePlanningApi] 将发送POST请求到: /route/plan');

        // 调用后端API
        return post('/route/plan', requestParams, {
            timeout: 400000 // 设置为400秒，与前端项目2保持一致
        }).then(response => {
            console.log('[routePlanningApi] 路线规划API返回成功:', response);

            // 检查响应格式
            if (!response) {
                throw new Error('路线规划响应为空');
            }

            // 直接返回响应对象，由调用方处理具体内容
            return response;

        }).catch(error => {
            console.error('[routePlanningApi] 路线规划API错误:', error);
            console.error('[routePlanningApi] 错误详情:', {
                message: error.message,
                request: requestParams,
                status: error.response ? error.response.status : '未知状态码',
                statusText: error.response ? error.response.statusText : '未知状态信息',
                data: error.response ? error.response.data : '无响应数据'
            });

            // 抛出更详细的错误信息
            const errorMsg = error.response && error.response.data && error.response.data.error ?
                error.response.data.error :
                error.message || '路线规划服务异常';

            throw new Error(`路线规划失败: ${errorMsg}`);
        });
    },

    /**
     * 获取路线历史
     * @returns {Promise<Object>} - 路线历史数据
     */
    getRouteHistory: () => {
        return get('/route/history');
    },

    /**
     * 删除路线历史
     * @param {number} index - 历史记录索引
     * @returns {Promise<Object>} - 操作结果
     */
    deleteRouteHistory: (index) => {
        return del(`/route/history/${index}`);
    },

    /**
     * 获取地理编码
     * @param {string} address - 地址
     * @returns {Promise<string>} - 地理编码（经纬度）
     */
    getGeocoding: (address) => {
        console.log('请求地址地理编码:', address);

        if (!address) {
            return Promise.reject(new Error('地址不能为空'));
        }

        // 使用后端地理编码API
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
     * @param {string} start - 起点经纬度
     * @param {string} end - 终点经纬度
     * @param {Object} preferences - 路线偏好设置
     * @param {string} routeType - 路线类型
     * @returns {Promise<Object>} - 路线详情
     */
    getRoutePlan: (start, end, preferences, routeType) => {
        return get('/route/detail', {
            start,
            end,
            preferences: JSON.stringify(preferences),
            route_type: routeType
        });
    },

    // 获取历史记录
    getHistory: async function() {
        try {
            const response = await get('/route/history');
            if (!response.success) {
                throw new Error(response.error || '获取历史记录失败');
            }
            return response.history || [];
        } catch (error) {
            console.error('获取历史记录失败:', error);
            // 如果请求失败，返回模拟数据以方便开发测试
            console.log('返回模拟数据用于开发');
            return [{
                    id: 'route-1',
                    title: '北京到上海的旅行',
                    created_at: new Date().toISOString(),
                    destinations: [
                        { name: '北京', description: '起点' },
                        { name: '上海', description: '终点' }
                    ]
                },
                {
                    id: 'route-2',
                    title: '广州到深圳的商务旅行',
                    created_at: new Date(Date.now() - 86400000).toISOString(),
                    destinations: [
                        { name: '广州', description: '起点' },
                        { name: '深圳', description: '终点' }
                    ]
                }
            ];
        }
    },

    // 删除历史记录
    deleteHistory: async function(routeId) {
        try {
            const response = await del(`/route/history/${routeId}`);
            if (!response.success) {
                throw new Error(response.error || '删除历史记录失败');
            }
            return true;
        } catch (error) {
            console.error('删除历史记录失败:', error);
            throw error;
        }
    },

    // 获取收藏列表
    getFavorites: async function() {
        try {
            const response = await get('/favorites');
            if (!response.success) {
                throw new Error(response.error || '获取收藏列表失败');
            }
            return response.data || [];
        } catch (error) {
            console.error('获取收藏列表失败:', error);
            throw error;
        }
    },

    // 添加收藏
    addFavorite: async function(data) {
        try {
            const response = await post('/favorite', data);
            if (!response.success) {
                throw new Error(response.error || '添加收藏失败');
            }
            return response.data;
        } catch (error) {
            console.error('添加收藏失败:', error);
            throw error;
        }
    },

    // 移除收藏
    removeFavorite: async function(routeId) {
        try {
            const response = await del(`/favorite/${routeId}`);
            if (!response.success) {
                throw new Error(response.error || '移除收藏失败');
            }
            return true;
        } catch (error) {
            console.error('移除收藏失败:', error);
            throw error;
        }
    },

    // 导出路线
    exportRoute: async function(data) {
        try {
            const response = await post('/export', data);
            if (!response.success) {
                throw new Error(response.error || '导出路线失败');
            }
            return response.data;
        } catch (error) {
            console.error('导出路线失败:', error);
            throw error;
        }
    },

    /**
     * 通过自然语言搜索路线
     * @param {string} query - 自然语言路线查询，如"从北京到上海"
     * @returns {Promise<Object>} - 路线规划结果
     */
    searchRoute: async function(query) {
        try {
            const response = await post('/route/planning', { query });
            return response.data;
        } catch (error) {
            console.error('路线搜索失败:', error);
            return { error: error.message || '路线搜索服务异常' };
        }
    },

    /**
     * 获取交通状况
     * @param {string} cityName - 城市名称
     * @returns {Promise<Object>} - 交通状况信息
     */
    getTrafficInfo: async function(cityName) {
        try {
            const response = await get('/route/traffic', { params: { city: cityName } });
            return response.data;
        } catch (error) {
            console.error('获取交通状况失败:', error);
            return { error: error.message || '获取交通状况失败' };
        }
    },

    /**
     * 分享路线
     * @param {string} routeId - 路线ID
     * @returns {Promise<Object>} - 分享结果（包含分享链接）
     */
    shareRoute: async function(routeId) {
        try {
            const response = await post('/route/share', { routeId });
            return response.data;
        } catch (error) {
            console.error('分享路线失败:', error);
            return { error: error.message || '分享路线失败' };
        }
    },

    // 根据文本获取路线
    getPlanByText: (text, signal) => {
        console.log('通过文本获取路线:', text);
        return post('/route/plan_by_text', { text }, { signal });
    }
};

export default routePlanningApi;