<template>
  <div class="chat-assistant">
    <div class="chat-container">
      <!-- 使用 v-loading 指令替代 el-loading 组件 -->
      <div v-loading="store.loading">
        <!-- 错误提示 -->
        <el-alert
          v-if="store.error"
          :title="store.error"
          type="error"
          show-icon
          closable
          @close="clearError"
        />

        <!-- 网络连接状态提示 -->
        <el-alert
          v-if="connectionError"
          title="网络连接异常，请检查网络后重试"
          type="warning"
          show-icon
          closable
          @close="connectionError = false"
        />

        <!-- 聊天消息 -->
        <div class="chat-messages" ref="messagesContainer" aria-live="polite">
          <div v-if="store.chatHistory.length === 0" class="empty-state">
            <div class="empty-title">智程助手就绪</div>
            <div class="empty-sub">请输入问题，例如 “从北京北站到中关村怎么走”</div>
          </div>

          <div v-for="(message, index) in store.chatHistory" 
               :key="index"
               :class="['message-row', message.role]">
            <div v-if="message.role === 'assistant'" class="avatar-col">
              <div class="avatar assistant-avatar" title="智程助手">IA</div>
            </div>

            <div class="bubble-col">
              <div :class="['bubble', message.role === 'assistant' ? 'bubble-assistant' : 'bubble-user']">
                <div v-if="message.role === 'assistant'" class="markdown-content" v-html="marked(message.content, { breaks: true })"></div>
                <div v-else class="plain-text">{{ message.content }}</div>
              </div>
              <div class="meta">
                <span class="timestamp">{{ new Date(message.timestamp || message.time || Date.now()).toLocaleTimeString() }}</span>
              </div>
            </div>

            <div v-if="message.role === 'user'" class="avatar-col">
              <div class="avatar user-avatar" title="你">我</div>
            </div>
          </div>

          <!-- Typing indicator -->
          <div v-if="loading" class="message-row assistant typing-indicator-row">
            <div class="avatar-col">
              <div class="avatar assistant-avatar" title="智程助手">IA</div>
            </div>
            <div class="bubble-col">
              <div class="bubble bubble-assistant typing-indicator">
                <div class="dots"><span></span><span></span><span></span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 输入框 -->
      <div class="chat-input">
        <el-input
          ref="chatInput"
          v-model="userInput"
          type="textarea"
          :rows="3"
          placeholder="请输入您的问题..."
          @keyup.enter.ctrl="sendMessage"
          @keyup.enter.prevent="onEnter"
        />
        <el-button 
          type="primary" 
          @click="sendMessage"
          :loading="loading"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, getCurrentInstance } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import { useRouteStore } from '../../stores/routeStore'
import { ElMessage } from 'element-plus'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'
import { routePlanningApi } from '../../api/routePlanning'

// 配置 marked
marked.setOptions({
  highlight: (code, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return code
  },
  breaks: true,
  gfm: true
})

const store = useRouteStore()
const route = useRoute()
const userInput = ref('')
const loading = ref(false)
const messagesContainer = ref(null)
const connectionError = ref(false) // 添加连接错误状态
const chatInput = ref(null)

// 处理回车发送（Enter 发送，Shift+Enter 换行）
const onEnter = (e) => {
  if (e.shiftKey) {
    // 插入换行
    userInput.value += '\n'
  } else {
    sendMessage()
  }
}

// 根据路由获取当前聊天类型
const getChatType = () => {
  return 'route' // 在这个组件中，我们总是使用路径规划类型
}

// 清除错误信息
const clearError = () => {
  store.error = ''
}

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || loading.value) return;
  
  // 提取用户输入的消息
  const userMessage = userInput.value.trim();
  
  // 清空输入框
  userInput.value = '';
  loading.value = true;
  connectionError.value = false; // 重置连接错误状态
  
  try {
    // 添加用户消息到聊天列表
    store.addUserMessage(userMessage);
    
    // 获取发送时间
    const sendTime = Date.now();
    
    // 记录请求到调试组件
    const parent = getCurrentInstance()?.parent;
    if (parent?.refs?.requestDebugger) {
      parent.refs.requestDebugger.addRequestLog({
        text: userMessage,
        model: 'qwen3-vl:8b'
      });
    }
    
    // 调用路线规划API
    console.log(`发送路径规划请求: "${userMessage}"`);
    const response = await routePlanningApi.planRoute({
      text: userMessage,
      model: 'qwen3-vl:8b'
    });
    
    // 记录调试信息
    console.log('路径规划响应:', response);
    
    // 记录响应到调试组件
    if (parent?.refs?.requestDebugger && response) {
      parent.refs.requestDebugger.addResponseLog(response);
    }
    
    // 计算延迟时间
    const delay = Date.now() - sendTime;
    console.log(`请求耗时: ${delay}ms`);
    
    if (response && response.success) {
      // 添加助手消息到聊天列表
      store.addAssistantMessage({
        content: response.route_data.response_text || '路线规划成功',
        route_data: response.route_data,
        timestamp: Date.now()
      });
      
      // 如果响应时间过长，提示用户
      if (delay > 10000) {
        ElMessage({
          message: '路线规划成功，但响应时间较长，可能影响体验',
          type: 'info',
          duration: 3000
        });
      }
    } else {
      // 处理错误情况
      const errorMessage = response?.error || '路线规划失败，请稍后重试';
      store.addSystemMessage({
        content: `错误: ${errorMessage}`,
        isError: true
      });
      
      // 显示具体的错误提示
      ElMessage({
        message: `路线规划失败: ${errorMessage}`,
        type: 'error',
        duration: 5000
      });
      
      console.error('路线规划API错误:', errorMessage);
    }
  } catch (error) {
    // 处理异常情况
    console.error('发送消息失败:', error);
    
    // 检查是否是网络连接问题
    if (error.message.includes('Network Error') || error.message.includes('timeout')) {
      connectionError.value = true;
      
      // 添加友好的网络错误提示
      store.addSystemMessage({
        content: '网络连接异常，请检查您的网络连接后重试',
        isError: true
      });
    } else {
      // 添加错误消息到聊天列表
      store.addSystemMessage({
        content: `发送失败: ${error.message || '未知错误'}`,
        isError: true
      });
    }
    
    // 记录错误到调试工具
    const parent = getCurrentInstance()?.parent;
    if (parent?.refs?.requestDebugger) {
      parent.refs.requestDebugger.addErrorLog(error);
    }
    
    // 显示错误提示
    ElMessage.error('消息发送失败，请检查网络连接');
  } finally {
    loading.value = false;
    scrollToBottom();
    // 恢复焦点到输入框
    await nextTick()
    if (chatInput.value && chatInput.value.focus) {
      try { chatInput.value.focus() } catch(e) {}
    }
  }
};

// 滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 监听聊天历史变化
watch(() => store.chatHistory, () => {
  scrollToBottom()
}, { deep: true })

onMounted(async () => {
  // 不再调用loadChatHistory，改为初始化操作
  if (store.chatHistory.length === 0) {
    store.startNewRouteSession();
  }
  scrollToBottom();
})
</script>

<style scoped>
.chat-assistant {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--el-bg-color);
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  gap: 20px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.message {
  margin-bottom: 20px;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message-content {
  max-width: 80%;
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
}

.message.assistant .message-content {
  background: rgba(0, 255, 157, 0.1);
}

.chat-input {
  display: flex;
  gap: 12px;
}

.chat-input .el-input {
  flex: 1;
}

/* New chat UI styles */
.message-row {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  margin-bottom: 12px;
}
.message-row.user {
  justify-content: flex-end;
}
.avatar-col {
  width: 40px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: white;
  box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
.assistant-avatar {
  background: linear-gradient(135deg,#2dd4bf,#06b6d4);
}
.user-avatar {
  background: #6b7280;
}
.bubble-col {
  max-width: calc(100% - 100px);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.bubble {
  padding: 12px 14px;
  border-radius: 12px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.06);
  font-size: 14px;
  line-height: 1.4;
}
.bubble-user {
  background: linear-gradient(180deg,#3b82f6,#2563eb);
  color: white;
  align-self: flex-end;
}
.bubble-assistant {
  background: #f8fafc;
  color: #0f172a;
}
.meta {
  margin-top: 6px;
  font-size: 11px;
  color: rgba(15,23,42,0.5);
}
.timestamp {
  display: inline-block;
}
.empty-state {
  padding: 40px;
  text-align: center;
  color: rgba(15,23,42,0.45);
}
.empty-title {
  font-weight: 600;
  margin-bottom: 8px;
}
.typing-indicator {
  background: rgba(0,0,0,0.06);
}
.typing-indicator .dots {
  display: flex;
  gap: 6px;
}
.typing-indicator .dots span {
  width: 8px;
  height: 8px;
  background: rgba(0,0,0,0.35);
  border-radius: 50%;
  display: inline-block;
  animation: blink 1s infinite;
}
.typing-indicator .dots span:nth-child(2) { animation-delay: .15s }
.typing-indicator .dots span:nth-child(3) { animation-delay: .3s }
@keyframes blink { 0%, 80%, 100% { opacity: 0.3 } 40% { opacity: 1 } }

/* Custom scrollbar */
.chat-messages::-webkit-scrollbar { width: 10px; }
.chat-messages::-webkit-scrollbar-thumb { background: rgba(15,23,42,0.08); border-radius: 8px; }

.markdown-content :deep(pre) {
  background: rgba(0, 0, 0, 0.2);
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 10px 0;
}

.markdown-content :deep(code) {
  font-family: monospace;
  color: var(--el-color-primary);
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 0.9em;
}

.markdown-content :deep(p) {
  margin: 8px 0;
  line-height: 1.6;
}

.markdown-content :deep(ul), 
.markdown-content :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.typing-indicator .message-content {
  opacity: 0.8;
  font-style: italic;
  color: rgba(0,0,0,0.6);
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid var(--el-color-primary);
  margin: 8px 0;
  padding: 0 12px;
  color: rgba(255, 255, 255, 0.7);
}
</style> 