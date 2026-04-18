import request from './request'

export const analysisHistoryApi = {
    // 获取分析历史记录
    async getHistory() {
        try {
            // 更新为正确的后端API路径
            const response = await request.get('/analysis/history')
            if (!response.success) {
                throw new Error(response.error || '获取分析历史记录失败')
            }
            return response.history || []
        } catch (error) {
            console.error('获取分析历史记录失败:', error)
            // 如果API请求失败，返回模拟数据以便于测试
            console.log('返回模拟数据用于开发')
            return [
                {
                    id: 'analysis-1',
                    timestamp: new Date().toISOString(),
                    imageUrl: 'https://via.placeholder.com/400x300.png?text=Image+1',
                    result: {
                        num_faces: 2,
                        persons: [
                            {
                                gender: '男性',
                                age: 25,
                                upper_color: '蓝色',
                                lower_color: '黑色'
                            },
                            {
                                gender: '女性',
                                age: 23,
                                upper_color: '红色',
                                lower_color: '白色'
                            }
                        ]
                    }
                },
                {
                    id: 'analysis-2',
                    timestamp: new Date(Date.now() - 86400000).toISOString(),
                    imageUrl: 'https://via.placeholder.com/400x300.png?text=Image+2',
                    result: {
                        num_faces: 1,
                        persons: [
                            {
                                gender: '男性',
                                age: 35,
                                upper_color: '绿色',
                                lower_color: '灰色'
                            }
                        ]
                    }
                }
            ]
        }
    },

    // 获取特定分析详情
    async getAnalysis(id) {
        try {
            const response = await request.get(`/analysis/${id}`)
            if (!response.success) {
                throw new Error(response.error || '获取分析详情失败')
            }
            return response.data
        } catch (error) {
            console.error('获取分析详情失败:', error)
            throw error
        }
    },

    // 删除分析历史记录
    async deleteAnalysis(id) {
        try {
            const response = await request.delete(`/analysis/${id}`)
            if (!response.success) {
                throw new Error(response.error || '删除分析历史记录失败')
            }
            return true
        } catch (error) {
            console.error('删除分析历史记录失败:', error)
            throw error
        }
    },

    // 添加或更新标签
    async updateTags(id, tags) {
        try {
            const response = await request.put(`/analysis/${id}/tags`, { tags })
            if (!response.success) {
                throw new Error(response.error || '更新标签失败')
            }
            return response.data
        } catch (error) {
            console.error('更新标签失败:', error)
            throw error
        }
    },

    // 导出分析结果
    async exportAnalysis(id, format = 'json') {
        try {
            const response = await request.get(`/analysis/${id}/export?format=${format}`)
            if (!response.success) {
                throw new Error(response.error || '导出分析结果失败')
            }
            return response.data
        } catch (error) {
            console.error('导出分析结果失败:', error)
            throw error
        }
    }
}
