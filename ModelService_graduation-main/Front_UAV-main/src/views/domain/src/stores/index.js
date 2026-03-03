import { defineStore } from 'pinia'
import { routePlanningApi } from '../api/routePlanning'

export const useMainStore = defineStore('main', {
    state: () => ({
        chatHistory: [],
        currentChatType: 'general',
        loading: false,
        error: null,
        routeSessionStartTime: null, // 当前路线规划会话的开始时间
        selectedRouteRecord: null, // 从路线记录中选择的记录
        routeRecords: [], // 路线记录列表
        loadSelectedRecord: false, // 标记是否需要加载选中的路线记录
    }),

    getters: {
        getLastMessage: (state) => {
            return state.chatHistory.length > 0 ? state.chatHistory[state.chatHistory.length - 1] : null
        },

        // 获取选中的路线记录
        getSelectedRouteRecord: (state) => {
            return state.selectedRouteRecord
        }
    },

    actions: {
        // 加载聊天历史
        async loadChatHistory(type) {
            this.loading = true
            try {
                // 从本地存储获取聊天历史，避免调用不必要的后端API
                const storedHistoryKey = `chatHistory_${type || 'general'}`;
                let chatHistory = [];

                const storedHistory = localStorage.getItem(storedHistoryKey);
                if (storedHistory) {
                    try {
                        chatHistory = JSON.parse(storedHistory) || [];
                    } catch (e) {
                        console.error('解析本地存储的聊天历史失败:', e);
                    }
                }

                this.chatHistory = chatHistory;
                this.currentChatType = type;
            } catch (error) {
                console.error('加载聊天历史失败:', error)
                this.error = error.message
            } finally {
                this.loading = false
            }
        },

        // 发送聊天消息
        async sendChatMessage({ type, content }) {
            console.log(`[Store] 发送聊天消息，类型: ${type}, 内容: ${content}`);
            this.loading = true;
            this.error = null;

            try {
                let response;
                if (type === 'route') {
                    // 路径规划请求（流式）
                    try {
                        console.log('[Store] 准备调用流式路线规划API');

                        // 先将用户消息加入历史
                        this.chatHistory.push({
                            role: 'user',
                            content,
                            timestamp: new Date().toISOString(),
                        });

                        // 添加助手占位消息（将被流式更新）
                        const assistantIndex = this.chatHistory.push({
                            role: 'assistant',
                            content: '',           // 最终文本
                            chunks: [],            // 流式片段数组（用于高亮追加）
                            thinking_steps: [],    // 结构化思考步骤
                            streaming: true,       // 正在流式接收
                            route_data: null,
                            timestamp: new Date().toISOString(),
                        }) - 1;

                        // 打开 EventSource 流
                        const es = routePlanningApi.planRouteStream(
                            { text: content, model: 'qwen3-vl:8b' },
                            (payload) => {
                                // onMessage
                                if (!payload || !payload.event) return;
                                if (payload.event === 'chunk') {
                                    // 路线规划场景下，大模型会输出结构化 JSON 分片。
                                    // 这些分片不适合作为对话内容展示，这里直接忽略，只保留最终总结句。
                                    return;
                                } else if (payload.event === 'thinking_start') {
                                    // 可以记录一个思考开始的步骤
                                    this.chatHistory[assistantIndex].thinking_steps.push({ stage: 'start', text: payload.content || '正在分析' });
                                } else if (payload.event === 'done') {
                                    // payload.route_data contains final data
                                    const rd = payload.route_data || payload.routeData || payload.route_data;
                                    this.chatHistory[assistantIndex].route_data = rd;
                                    // 标记流式结束
                                    this.chatHistory[assistantIndex].streaming = false;
                                    // 如果后端返回有 response_text，优先使用它作为最终显示（只展示这一句关键信息）
                                    const finalText = (rd && rd.response_text) ? rd.response_text : '路线规划完成';
                                    this.chatHistory[assistantIndex].content = finalText;
                                    // 保存历史
                                    this.saveChatHistoryToLocalStorage();
                                }
                            },
                            () => {
                                // onDone
                                console.log('[Store] 流式路线规划完成');
                                es.close && es.close();
                                this.loading = false;
                            },
                            (err) => {
                                // onError
                                console.error('[Store] 流式路线规划错误:', err);
                                this.chatHistory.push({
                                    role: 'assistant',
                                    content: `抱歉，路线规划失败: ${err && err.message ? err.message : '网络或服务错误'}`,
                                    timestamp: new Date().toISOString(),
                                });
                                es.close && es.close();
                                this.loading = false;
                            }
                        );

                        // 返回一个 Promise，当流结束或发生错误时 resolve/reject
                        return new Promise((resolve, reject) => {
                            // 简单超时保护（例如 2 分钟）
                            const timeout = setTimeout(() => {
                                console.warn('[Store] 流式请求超时，自动关闭');
                                es.close && es.close();
                                this.loading = false;
                                resolve({ success: false, error: 'timeout' });
                            }, 120000);

                            // we cannot easily detect done event here, but onDone will set loading false
                            // resolve immediately to allow UI continue; frontend history will be updated by callbacks
                            resolve({ success: true });
                        });

                    } catch (error) {
                        console.error('[Store] 路线规划请求失败:', error);
                        this.chatHistory.push({
                            role: 'assistant',
                            content: `抱歉，路线规划失败: ${error.message || '未知错误'}`,
                            timestamp: new Date().toISOString(),
                        });
                        this.saveChatHistoryToLocalStorage();
                        throw error;
                    }
                } else {
                    // 普通聊天请求
                    this.chatHistory.push({
                        role: 'user',
                        content,
                        timestamp: new Date().toISOString(),
                    });

                    // 这里可以调用其他聊天API，如知识图谱等

                    return {
                        success: true,
                        message: '消息已发送'
                    };
                }
            } catch (error) {
                console.error('[Store] 发送聊天消息失败:', error);
                this.error = error.message;
                throw error;
            } finally {
                this.loading = false;
            }
        },

        // 将聊天历史保存到本地存储
        saveChatHistoryToLocalStorage() {
            try {
                const historyKey = `chatHistory_${this.currentChatType}`;
                localStorage.setItem(historyKey, JSON.stringify(this.chatHistory));
            } catch (error) {
                console.error('保存聊天历史到本地存储失败:', error);
            }
        },

        // 开始新的路径规划会话
        startNewRouteSession() {
            console.log('[Store] 开始新的路径规划会话');
            this.routeSessionStartTime = new Date().toISOString();
            this.chatHistory = [];
            this.currentChatType = 'route';

            // 清除本地存储中的路径规划聊天历史
            localStorage.removeItem('chatHistory_route');
        },

        // 保存路线记录
        saveRouteRecord(routeInfo) {
            try {
                if (!routeInfo) return false;

                // 创建新记录
                const newRecord = {
                    id: `route-${Date.now()}`,
                    title: `从 ${routeInfo.start_point} 到 ${routeInfo.end_point} 的路线`,
                    created_at: new Date().toISOString(),
                    routeInfo
                };

                // 添加到记录列表
                this.routeRecords.unshift(newRecord);

                // 将记录保存到本地存储
                this.saveRouteRecordsToLocalStorage();

                return true;
            } catch (error) {
                console.error('保存路线记录失败:', error);
                return false;
            }
        },

        // 将路线记录保存到本地存储
        saveRouteRecordsToLocalStorage() {
            try {
                localStorage.setItem('routeRecords', JSON.stringify(this.routeRecords));
            } catch (error) {
                console.error('保存路线记录到本地存储失败:', error);
            }
        },

        // 加载路线记录
        loadRouteRecords() {
            try {
                const storedRecords = localStorage.getItem('routeRecords');
                if (storedRecords) {
                    this.routeRecords = JSON.parse(storedRecords) || [];
                }
            } catch (error) {
                console.error('加载路线记录失败:', error);
            }
        },

        // 获取路线记录列表
        getRouteRecords() {
            // 如果本地记录为空，尝试从本地存储加载
            if (this.routeRecords.length === 0) {
                this.loadRouteRecords();
            }
            return this.routeRecords;
        },

        // 选择路线记录
        selectRouteRecord(recordId) {
            const record = this.routeRecords.find(r => r.id === recordId);
            if (record) {
                this.selectedRouteRecord = record;
                return true;
            }
            return false;
        },

        // 设置选中的路线记录（从父组件调用）
        setSelectedRouteRecord(record) {
            this.selectedRouteRecord = record;
            this.loadSelectedRecord = true; // 设置加载标记
            return true;
        },

        // 加载选中的路线记录
        loadSelectedRouteRecord() {
            return this.selectedRouteRecord;
        },

        // 删除路线记录
        deleteRouteRecord(recordId) {
            const index = this.routeRecords.findIndex(r => r.id === recordId);
            if (index !== -1) {
                this.routeRecords.splice(index, 1);
                this.saveRouteRecordsToLocalStorage();

                // 如果删除的是当前选中的记录，则清除选中状态
                if (this.selectedRouteRecord && this.selectedRouteRecord.id === recordId) {
                    this.selectedRouteRecord = null;
                }

                return true;
            }
            return false;
        }
    }
})