import request from './request'

export const routePlanningApi = {
    // 获取路线规划
    async getRoutePlan(data) {
        try {
            console.log('发送路线规划请求:', data) // 添加调试日志

            // 使用完全匹配后端的API路径
            // 注意：前端代理已自动添加/api前缀，这里不需要重复添加
            const response = await request.post('/route/plan', {
                text: data.text,
                model: 'gemma2:2b'
            }, {
                timeout: 400000 // 设置为400秒
            })

            console.log('路线规划响应:', response) // 添加调试日志

            if (!response.success) {
                throw new Error(response.error || '路线规划失败')
            }
            return response
        } catch (error) {
            console.error('路线规划失败:', error)
            throw error
        }
    },

    // 获取历史记录
    async getHistory() {
        try {
            // 修正: 使用正确的API路径
            // 注意：前端代理已自动添加/api前缀，这里不需要重复添加
            const response = await request.get('/route/history')
            if (!response.success) {
                throw new Error(response.error || '获取历史记录失败')
            }
            // 修正: 返回 history 数组而非整个响应
            return response.history || []
        } catch (error) {
            console.error('获取历史记录失败:', error)
            // 如果请求失败，返回模拟数据以方便开发测试
            console.log('返回模拟数据用于开发')
            return [
                {
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
            ]
        }
    },

    // 删除历史记录
    async deleteHistory(routeId) {
        try {
            // 修正: 使用正确的API路径
            // 注意：前端代理已自动添加/api前缀，这里不需要重复添加
            const response = await request.delete(`/route/history/${routeId}`)
            if (!response.success) {
                throw new Error(response.error || '删除历史记录失败')
            }
            return true
        } catch (error) {
            console.error('删除历史记录失败:', error)
            throw error
        }
    },

    // 获取收藏列表
    async getFavorites() {
        try {
            const response = await request.get('/favorites')
            if (!response.success) {
                throw new Error(response.error || '获取收藏列表失败')
            }
            return response.data || []
        } catch (error) {
            console.error('获取收藏列表失败:', error)
            throw error
        }
    },

    // 添加收藏
    async addFavorite(data) {
        try {
            const response = await request.post('/favorite', data)
            if (!response.success) {
                throw new Error(response.error || '添加收藏失败')
            }
            return response.data
        } catch (error) {
            console.error('添加收藏失败:', error)
            throw error
        }
    },

    // 移除收藏
    async removeFavorite(routeId) {
        try {
            const response = await request.delete(`/favorite/${routeId}`)
            if (!response.success) {
                throw new Error(response.error || '移除收藏失败')
            }
            return true
        } catch (error) {
            console.error('移除收藏失败:', error)
            throw error
        }
    },

    // 导出路线
    async exportRoute(data) {
        try {
            const response = await request.post('/export', data)
            if (!response.success) {
                throw new Error(response.error || '导出路线失败')
            }
            return response.data
        } catch (error) {
            console.error('导出路线失败:', error)
            throw error
        }
    },

    // 获取路线详情
    async getRouteDetail(routeId) {
        try {
            const response = await request.get(`/${routeId}`)
            if (!response.success) {
                throw new Error(response.error || '获取路线详情失败')
            }
            return response.data
        } catch (error) {
            console.error('获取路线详情失败:', error)
            throw error
        }
    }
}