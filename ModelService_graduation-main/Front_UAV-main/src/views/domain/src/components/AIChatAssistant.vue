<template>
  <div class="chat-assistant">
    <div class="chat-container">
      <!-- 聊天标题 -->
      <div class="chat-title">
        <div class="assistant-name">
          <svg t="1747102188514" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="4650" width="24" height="24"><path d="M79.11424 270.67904l116.2496 66.9952a97.1776 97.1776 0 0 0-4.87424 30.57664v268.7232a97.53088 97.53088 0 0 0 47.39584 83.72736l219.42784 131.31264a97.28 97.28 0 0 0 15.4112 7.45984v153.84576a97.6384 97.6384 0 0 1-11.06944-5.70368L120.32 803.34848a97.51552 97.51552 0 0 1-47.44704-83.62496v-414.72c0-11.89376 2.19648-23.5008 6.2464-34.32448z m871.4752 34.32448v414.67392a97.52576 97.52576 0 0 1-47.44704 83.67104L561.8176 1007.6672c-3.6096 2.0992-7.31648 3.99872-11.06944 5.6576v-157.6448c2.28864-1.1264 4.5312-2.34496 6.72768-3.6608l219.42784-131.31264a97.53088 97.53088 0 0 0 47.44192-83.72736V368.25088a97.07008 97.07008 0 0 0-1.36192-16.384l124.3904-71.68c2.0992 7.99744 3.2256 16.3328 3.2256 24.81664zM561.8176 17.06496l336.59904 201.39008-118.2464 68.11648c-1.0752-0.70144-2.16576-1.3824-3.26656-2.048l-219.42784-131.31264a97.52576 97.52576 0 0 0-100.15744 0L248.32 278.28224l-113.76128-65.536L461.65504 17.06496a97.52576 97.52576 0 0 1 100.15744 0z" p-id="4651" fill="#09b980"></path><path d="M264.60672 365.22496L483.84 491.0336v275.98848a97.34144 97.34144 0 0 1-31.7952-12.09344L304.7936 667.1616a97.52576 97.52576 0 0 1-47.54432-83.77344V402.3808c0-12.96896 2.5856-25.5488 7.31136-37.15584h0.0512z m482.10944 37.15584v181.00736c0 34.3552-18.07872 66.18112-47.5904 83.77344l-147.21536 87.76704c-2.58048 1.51552-5.21728 2.92864-7.90016 4.2496V499.6608l201.04704-115.27168c1.11104 5.9392 1.664 11.9552 1.65888 17.99168z m-194.80576-171.54048l147.26144 87.77216a97.536 97.536 0 0 1 17.26464 13.16352l-193.39264 110.83776h-3.21536L304.29696 318.90432l0.49152-0.34304L452.0448 230.78912a97.52576 97.52576 0 0 1 99.86048 0v0.0512z" p-id="4652" fill="#09b980"></path></svg>
          <span>智程助手</span>
        </div>
        <div class="chat-status" v-if="store.loading">
          <el-icon class="rotating"><Loading /></el-icon>
          <span>思考中...</span>
        </div>
      </div>

      <!-- 聊天内容区域 -->
      <div class="chat-content">
        <!-- 错误提示 -->
        <el-alert
          v-if="store.error"
          :title="store.error"
          type="error"
          show-icon
        />
        
        <!-- 聊天消息 -->
        <div class="chat-messages" ref="messagesContainer">
          <div v-for="(message, index) in store.chatHistory" 
               :key="index"
               :class="['message-wrapper', message.role]">
            <div class="avatar">
              <template v-if="message.role === 'assistant'">
                <svg t="1747102188514" class="model-icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="4650" width="24" height="24"><path d="M79.11424 270.67904l116.2496 66.9952a97.1776 97.1776 0 0 0-4.87424 30.57664v268.7232a97.53088 97.53088 0 0 0 47.39584 83.72736l219.42784 131.31264a97.28 97.28 0 0 0 15.4112 7.45984v153.84576a97.6384 97.6384 0 0 1-11.06944-5.70368L120.32 803.34848a97.51552 97.51552 0 0 1-47.44704-83.62496v-414.72c0-11.89376 2.19648-23.5008 6.2464-34.32448z m871.4752 34.32448v414.67392a97.52576 97.52576 0 0 1-47.44704 83.67104L561.8176 1007.6672c-3.6096 2.0992-7.31648 3.99872-11.06944 5.6576v-157.6448c2.28864-1.1264 4.5312-2.34496 6.72768-3.6608l219.42784-131.31264a97.53088 97.53088 0 0 0 47.44192-83.72736V368.25088a97.07008 97.07008 0 0 0-1.36192-16.384l124.3904-71.68c2.0992 7.99744 3.2256 16.3328 3.2256 24.81664zM561.8176 17.06496l336.59904 201.39008-118.2464 68.11648c-1.0752-0.70144-2.16576-1.3824-3.26656-2.048l-219.42784-131.31264a97.52576 97.52576 0 0 0-100.15744 0L248.32 278.28224l-113.76128-65.536L461.65504 17.06496a97.52576 97.52576 0 0 1 100.15744 0z" p-id="4651" fill="#09b980"></path><path d="M264.60672 365.22496L483.84 491.0336v275.98848a97.34144 97.34144 0 0 1-31.7952-12.09344L304.7936 667.1616a97.52576 97.52576 0 0 1-47.54432-83.77344V402.3808c0-12.96896 2.5856-25.5488 7.31136-37.15584h0.0512z m482.10944 37.15584v181.00736c0 34.3552-18.07872 66.18112-47.5904 83.77344l-147.21536 87.76704c-2.58048 1.51552-5.21728 2.92864-7.90016 4.2496V499.6608l201.04704-115.27168c1.11104 5.9392 1.664 11.9552 1.65888 17.99168z m-194.80576-171.54048l147.26144 87.77216a97.536 97.536 0 0 1 17.26464 13.16352l-193.39264 110.83776h-3.21536L304.29696 318.90432l0.49152-0.34304L452.0448 230.78912a97.52576 97.52576 0 0 1 99.86048 0v0.0512z" p-id="4652" fill="#09b980"></path></svg>
              </template>
              <template v-else>
                <svg t="1747289737197" class="user-icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="8639" width="24" height="24"><path d="M502.496 63.136c125.888 0 227.936 100.384 227.936 224.192 0 123.84-102.048 224.224-227.936 224.224-125.888 0-227.936-100.384-227.936-224.224C274.56 163.488 376.64 63.136 502.496 63.136L502.496 63.136zM502.496 63.136c125.888 0 227.936 100.384 227.936 224.192 0 123.84-102.048 224.224-227.936 224.224-125.888 0-227.936-100.384-227.936-224.224C274.56 163.488 376.64 63.136 502.496 63.136L502.496 63.136zM417.024 586.304l189.984 0c162.624 0 294.432 129.632 294.432 289.6l0 18.656c0 63.04-131.84 65.44-294.432 65.44l-189.984 0c-162.624 0-294.432-0.096-294.432-65.44l0-18.656C122.592 715.936 254.4 586.304 417.024 586.304L417.024 586.304zM417.024 586.304" fill="#409EFF" p-id="8640"></path></svg>
              </template>
            </div>
            <div class="message">
              <div class="message-content">
                <div v-if="message.role === 'assistant'">
                  <!-- 流式片段高亮追加 -->
                  <div v-if="message.chunks && message.chunks.length" class="streamed-content">
                    <template v-for="(chunk, ci) in message.chunks" :key="ci">
                      <span class="stream-chunk" v-html="chunk"></span>
                    </template>
                  </div>

                  <!-- 结构化思考步骤时间线 -->
                  <div v-if="message.thinking_steps && message.thinking_steps.length" class="thinking-steps">
                    <div v-for="(step, si) in message.thinking_steps" :key="si" class="thinking-step-card">
                      <div class="step-index">步骤 {{ si + 1 }}</div>
                      <div class="step-body">
                        <div class="step-title" v-if="step.title">{{ step.title }}</div>
                        <div class="step-text">{{ step.text || step.content || JSON.stringify(step) }}</div>
                      </div>
                    </div>
                  </div>

                  <!-- 最终文本 -->
                  <div class="markdown-content" v-if="message.content" v-html="marked(message.content, { breaks: true })"></div>

                  <!-- 打字指示器（当流式进行中显示） -->
                  <div v-if="message.streaming" class="typing-indicator small">
                    <span></span><span></span><span></span>
                  </div>
                </div>
                <div v-else>{{ message.content }}</div>
              </div>
              <div class="message-time">
                {{ formatTime(message.timestamp) }}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 输入框 -->
      <div class="chat-input">
        <el-input
          v-model="userInput"
          type="textarea"
          :rows="2"
          placeholder="请输入您的问题，例如：从北京到上海的路线..."
          @keyup.enter.ctrl="sendMessage"
          :disabled="store.loading"
        />
        <el-button 
          type="primary" 
          @click="sendMessage"
          :loading="store.loading"
          :disabled="!userInput.trim()"
          class="send-btn"
        >
          发送
        </el-button>
      </div>
      <div class="shortcut-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>提示：按 Ctrl + Enter 快速发送</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import { useMainStore } from '../stores'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'
import { Loading, InfoFilled } from '@element-plus/icons-vue'

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

const store = useMainStore()
const route = useRoute()
const userInput = ref('')
const loading = ref(false)
const messagesContainer = ref(null)

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
}

// 根据路由获取当前聊天类型
const getChatType = () => {
  const path = route.path
  console.log('当前路由路径:', path)
  
  // 扩大匹配范围，包含更多可能的路径规划相关路径
  if (path.includes('route') || path.includes('planning') || path.includes('path')) {
    console.log('识别为路径规划聊天类型')
    return 'route'
  }
  if (path.includes('image-recognition')) return 'image'
  if (path.includes('video-tracking')) return 'video'
  
  // 增加路径规划检测 - 如果消息中包含地点之间路线的关键词也视为路径规划
  if (userInput.value) {
    const routeKeywords = ['从', '到', '去', '路线', '规划', '行程', '怎么走']
    const hasRouteKeywords = routeKeywords.some(keyword => userInput.value.includes(keyword))
    if (hasRouteKeywords && userInput.value.length < 100) {
      console.log('根据内容识别为路径规划聊天')
      return 'route'
    }
  }
  
  console.log('识别为一般聊天类型')
  return 'general'
}

// 检测是否是路径规划请求
const isRouteRequest = (text) => {
  if (!text) return false
  
  // 中文路线请求模式识别
  const routePattern = /从(.+?)到(.+)/
  const hasRoutePattern = routePattern.test(text)
  
  // 关键词检测
  const routeKeywords = ['从', '到', '去', '路线', '规划', '行程', '怎么走']
  const hasRouteKeywords = routeKeywords.some(keyword => text.includes(keyword))
  
  return hasRoutePattern || (hasRouteKeywords && text.length < 100)
}

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || store.loading) return
  
  const message = userInput.value
  userInput.value = ''
  
  try {
    // 判断是否是路径规划请求
    const messageType = isRouteRequest(message) ? 'route' : getChatType()
    console.log(`[AIChatAssistant] 发送消息，类型: ${messageType}, 内容: ${message}`)
    
    // 如果是路径规划请求，强制设置类型为route
    await store.sendChatMessage({
      type: messageType,
      content: message
    })
  } catch (error) {
    console.error('发送消息失败:', error)
  } finally {
    scrollToBottom()
  }
}

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
  // 加载历史消息
  await store.loadChatHistory(getChatType())
  
  // 调试消息
  console.log('[AIChatAssistant] 组件已挂载，聊天类型:', getChatType())
  // 初始滚动到底部
  scrollToBottom()
})
</script>

<style scoped>
.chat-assistant {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  position: relative;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0;
  height: 100%;
  width: 100%;
  max-height: 100%;
  overflow: hidden;
}

.chat-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: #f9f9f9;
  border-bottom: 1px solid #eaeaea;
  flex-shrink: 0;
  z-index: 10;
}

.assistant-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #333333;
}

.chat-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #666666;
}

.rotating {
  animation: rotate 1.5s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.chat-content {
  flex: 1;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #ffffff;
  scroll-behavior: smooth;
  min-height: 100px;
}

.message-wrapper {
  display: flex;
  margin-bottom: 20px;
  gap: 12px;
}

.message-wrapper.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
}

.message-wrapper.assistant .avatar {
  background: rgba(9, 185, 128, 0.1);
}

.message-wrapper.user .avatar {
  background: rgba(64, 158, 255, 0.1);
}

.model-icon {
  width: 24px;
  height: 24px;
}

.user-icon {
  width: 24px;
  height: 24px;
}

.message {
  max-width: 80%;
}

.message-content {
  padding: 12px 16px;
  border-radius: 12px;
  background: #f5f5f5;
  font-size: 14px;
  line-height: 1.6;
  position: relative;
  word-break: break-word;
}

.message-wrapper.assistant .message-content {
  background: #eef9f5;
  color: #333333;
  border: 1px solid rgba(9, 185, 128, 0.15);
}

.message-wrapper.user .message-content {
  background: #ecf5ff;
  color: #333333;
  border: 1px solid rgba(64, 158, 255, 0.15);
}

.message-time {
  margin-top: 6px;
  font-size: 12px;
  color: #999999;
  text-align: right;
}

.chat-input {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  background: #f9f9f9;
  border-top: 1px solid #eaeaea;
  flex-shrink: 0;
}

.chat-input .el-input {
  flex: 1;
}

.shortcut-hint {
  padding: 0 20px 12px 20px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #999999;
  background: #f9f9f9;
  flex-shrink: 0;
}

.send-btn {
  padding: 0 20px;
}

.markdown-content :deep(pre) {
  background: rgba(0, 0, 0, 0.03);
  padding: 15px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 10px 0;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.markdown-content :deep(code) {
  font-family: Consolas, Monaco, 'Andale Mono', monospace;
  color: #096dd9;
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 0.9em;
  background-color: rgba(0, 0, 0, 0.05);
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

.markdown-content :deep(blockquote) {
  border-left: 4px solid #09b980;
  margin: 8px 0;
  padding: 0 12px;
  color: #666666;
  background-color: rgba(9, 185, 128, 0.05);
}

.markdown-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
}

.markdown-content :deep(table th),
.markdown-content :deep(table td) {
  border: 1px solid #eaeaea;
  padding: 8px 12px;
  text-align: left;
}

.markdown-content :deep(table th) {
  background-color: #f5f5f5;
  font-weight: 600;
}

/* 流式片段样式 */
.streamed-content {
  display: inline-block;
  margin-bottom: 6px;
}
.stream-chunk {
  display: inline-block;
  background: linear-gradient(90deg, rgba(59,130,246,0.08), rgba(34,197,94,0.03));
  padding: 6px 8px;
  margin-right: 6px;
  border-radius: 6px;
  transition: background 0.5s ease;
  animation: pop 0.35s ease;
}

@keyframes pop {
  0% { transform: translateY(6px); opacity: 0; }
  100% { transform: translateY(0); opacity: 1; }
}

/* 小型打字指示器 */
.typing-indicator.small {
  display: inline-flex;
  gap: 6px;
  margin-top: 6px;
}
.typing-indicator.small span {
  width: 6px;
  height: 6px;
  background: #9ca3af;
  border-radius: 50%;
  animation: blink 1.2s infinite;
}

/* 思考步骤卡片 */
.thinking-steps {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.thinking-step-card {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  background: rgba(9,185,128,0.04);
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid rgba(9,185,128,0.06);
}
.step-index {
  font-weight: 600;
  color: #06b6d4;
  min-width: 46px;
}
.step-body .step-title {
  font-weight: 600;
  margin-bottom: 4px;
}
.step-body .step-text {
  color: #374151;
  font-size: 0.95rem;
}
</style> 