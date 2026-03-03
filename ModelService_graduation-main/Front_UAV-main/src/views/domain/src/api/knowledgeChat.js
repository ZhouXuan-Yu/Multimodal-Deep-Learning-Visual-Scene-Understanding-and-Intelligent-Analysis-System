import request from '../utils/request'
import { BACKEND_PORT } from '../port_config.js'

export const knowledgeChatApi = {
    /**
     * 发送消息到知识库聊天
     * @param {string} message - 用户消息
     * @param {boolean} webSearch - 是否开启联网搜索
     * @param {boolean} knowledgeGraphSearch - 是否进行知识图谱搜索
     * @param {boolean} localModelSearch - 是否进行本地模型搜索
     * @returns {Promise} - 返回fetch API的Response对象，可通过response.body.getReader()获取流数据
     */
    sendMessage(message, webSearch = false, knowledgeGraphSearch = false, localModelSearch = false) {
        console.log('=== 发送知识库聊天请求 ===')
        console.log('用户消息:', message)
        console.log('联网搜索:', webSearch)
        console.log('知识图谱检索:', knowledgeGraphSearch)
        console.log('本地模型检索:', localModelSearch)

        const requestData = {
            message: message.toString(),
            model: 'qwen2.5:3b',
            temperature: 0.7,
            web_search: webSearch,
            knowledge_graph_search: knowledgeGraphSearch,
            local_model_search: localModelSearch
        }

        // 使用fetch API处理SSE流式响应
        // 后端会返回text/event-stream格式的数据，每行以"data:"开头
        const apiUrl = `http://localhost:${BACKEND_PORT}/api/knowledge-chat/stream`;

        console.log('请求流式API:', apiUrl);

        return fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream' // 确保接收SSE格式
            },
            body: JSON.stringify(requestData)
        }).then(response => {
            if (!response.ok) {
                console.error('流式请求失败:', response.status, response.statusText);
                throw new Error(`HTTP错误! 状态: ${response.status}`);
            }
            console.log('流式响应开始接收...');
            return response;
        }).catch(error => {
            console.error('流式请求出错:', error);
            throw error;
        });
    },

    /**
     * 获取知识图谱数据
     * @returns {Promise}
     */
    getKnowledgeGraph() {
        // 使用Axios实例请求
        return request({
            url: '/knowledge-chat/graph',
            method: 'get'
        });
    },

    /**
     * 获取最新的本地模型搜索结果
     * @param {string} query - 查询内容
     * @returns {Promise}
     */
    getLatestLocalModelResults(query) {
        return request({
            url: `/knowledge-chat/latest-local-model-results?query=${encodeURIComponent(query)}`,
            method: 'get'
        });
    },

    /**
     * 添加节点到知识图谱
     * @param {Object} node - 节点数据
     * @param {Array} links - 连接数据
     * @returns {Promise}
     */
    addToKnowledgeGraph(node, links = []) {
        return request({
            url: '/knowledge-chat/graph/add',
            method: 'post',
            data: {
                node,
                links
            }
        })
    },

    /**
     * 导入无人机数据到知识图谱
     * @param {Object} droneData - 无人机数据，包含drones、brands和relationships
     * @returns {Promise}
     */
    importDroneData(droneData) {
        console.log('=== 导入无人机数据 ===');
        console.log('数据结构:', droneData);

        return request({
                url: '/knowledge-chat/graph/import-drones',
                method: 'post',
                data: droneData
            })
            .then(response => {
                console.log('导入成功，响应数据:', response);
                return response;
            })
            .catch(error => {
                console.error('导入无人机数据失败:', error);
                throw error;
            });
    },

    /**
     * 获取最新的搜索结果
     * @param {string} query - 查询内容
     * @returns {Promise}
     */
    getLatestResults(query) {
        return request({
            url: `/knowledge-chat/latest-search?query=${encodeURIComponent(query)}`,
            method: 'get'
        });
    },

    /**
     * 获取最新的知识图谱查询结果
     * @param {string} query - 查询内容 
     * @returns {Promise}
     */
    getLatestGraphResults(query) {
        return request({
            url: `/knowledge-chat/latest-graph?query=${encodeURIComponent(query)}`,
            method: 'get'
        });
    }
}