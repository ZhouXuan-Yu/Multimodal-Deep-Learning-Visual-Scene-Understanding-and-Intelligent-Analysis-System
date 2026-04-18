import request from '@/utils/request'

export const knowledgeChatApi = {
    /**
     * 发送消息到知识库聊天
     * @param {string} message - 用户消息
     * @param {boolean} webSearch - 是否开启联网搜索
     * @param {string} model - 使用的模型
     * @returns {Promise}
     */
    sendMessage(message, webSearch = false, model = 'qwen3.5:4b') {
        console.log('=== 发送知识库聊天请求 ===')
        console.log('用户消息:', message)
        console.log('联网搜索:', webSearch)
        console.log('使用模型:', model)

        const requestData = {
            message: message.toString(),
            model: model,
            temperature: 0.7,
            web_search: webSearch
        }

        // 返回原始的fetch请求，以支持流式输出
        return fetch('/api/knowledge-chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
    },

    /**
     * 获取知识图谱数据
     * @returns {Promise}
     */
    getKnowledgeGraph() {
        return request({
            url: '/api/knowledge-chat/graph',
            method: 'get'
        })
    },

    /**
     * 添加节点到知识图谱
     * @param {Object} node - 节点数据
     * @param {Array} links - 连接数据
     * @returns {Promise}
     */
    addToKnowledgeGraph(node, links = []) {
        return request({
            url: '/api/knowledge-chat/graph/add',
            method: 'post',
            data: {
                node,
                links
            }
        })
    }
}