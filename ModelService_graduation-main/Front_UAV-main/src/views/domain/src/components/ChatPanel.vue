<template>
  <div class="chat-panel">
    <el-card class="chat-card" shadow="never">
      <template #header>
        <div class="chat-header">
          <div class="assistant-title">
            <svg class="assistant-icon" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg" width="20" height="20">
              <path d="M128 128h256v256H128z" fill="#06b6d4"></path>
            </svg>
            <span class="assistant-name">智程助手</span>
          </div>
          <div class="header-actions">
            <el-button type="text" @click="clearHistory" title="清除历史">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </template>
      
      <div class="chat-content" ref="chatContent" role="log" aria-live="polite">
        <!-- 聊天历史 -->
        <div class="chat-messages">
          <div v-if="chatHistory.length === 0" class="empty-state">
            <div class="empty-title">智程助手已就绪</div>
            <div class="empty-sub">可询问：例如“从北京到上海怎么走？”</div>
          </div>

          <div v-for="(message, index) in chatHistory" 
               :key="index" 
               :class="['message-row', message.type === 'user' ? 'user' : 'system']">
            <div v-if="message.type !== 'user'" class="avatar-col">
              <div class="avatar assistant-avatar">智</div>
            </div>

            <div class="bubble-col">
              <div :class="['bubble', message.type === 'user' ? 'bubble-user' : 'bubble-assistant']">
                <div class="message-text" v-html="formatMessage(message.content)"></div>
              </div>
              <div class="message-time">{{ formatTime(message.timestamp) }}</div>
            </div>

            <div v-if="message.type === 'user'" class="avatar-col">
              <div class="avatar user-avatar">我</div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 输入区域 -->
      <div class="chat-input">
        <div class="input-wrapper">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="2"
            placeholder="请输入查询，例如：从北京到上海的路线..."
            @keyup.enter.ctrl="handleMessage"
            class="input-box"
          />
          <el-button type="primary" @click="handleMessage" :disabled="!inputMessage.trim()" class="send-button">
            发送
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import { useAnalysisStore } from '@/stores/analysis'
import { parseQuery, generateResultDescription } from '@/utils/queryParser'
import dayjs from 'dayjs'
import { chatApi } from '@/api/chat'

// Props
const props = defineProps({
  analysisResult: {
    type: Object,
    default: null
  }
})

// Emits
const emit = defineEmits(['query'])

// Store
const analysisStore = useAnalysisStore()

// Refs
const chatContent = ref(null)
const inputMessage = ref('')
const chatHistory = ref([
  {
    type: 'system',
    content: '你好！我是智能助手，可以帮你查找和分析图片中的人物。上传图片并分析后，你可以问我类似这样的问题：<br>- 找到穿绿色上衣的女性<br>- 帮我找年龄小于30岁的人<br>- 谁穿着蓝色的衣服？',
    timestamp: new Date()
  }
])

// Methods
const handleMessage = async (message) => {
  if (!inputMessage.value.trim()) return
  
  // 添加用户消息
  addMessage('user', inputMessage.value)
  
  // 处理查询
  const query = inputMessage.value
  inputMessage.value = ''
  
  if (!props.analysisResult) {
    addMessage('system', '请先上传并分析图片')
    return
  }
  
  try {
    // 调用本地大模型进行对话
    const response = await chatApi.sendMessage({
      messages: [
        {
          role: 'system',
          content: '你是一个图像分析助手，可以帮助用户查找和分析图片中的人物。请根据用户的描述，找到匹配的人物并生成自然的回复。'
        },
        {
          role: 'user',
          content: query
        }
      ],
      type: 'image_analysis'
    })
    
    // 解析查询条件
    const conditions = parseQuery(query)
    const matches = analysisStore.findMatchingPersons(conditions)
    
    // 生成回复
    let reply = ''
    if (matches.length > 0) {
      reply = generateResultDescription(matches, conditions)
      // 高亮匹配的人物
      matches.forEach((match, index) => {
        setTimeout(() => {
          analysisStore.setActivePerson(match.id)
        }, index * 1000)
      })
    } else {
      reply = '抱歉，我没有找到符合描述的人物。请尝试其他描述方式。'
    }
    
    // 添加系统回复
    addMessage('system', reply)
    
    // 发送查询事件
    emit('query', { query, matches })
    
  } catch (error) {
    console.error('处理查询失败:', error)
    addMessage('system', '抱歉，处理查询时出现错误，请重试。')
  }
}

const addMessage = (type, content) => {
  chatHistory.value.push({
    type,
    content,
    timestamp: new Date()
  })
  
  // 滚动到底部
  nextTick(() => {
    if (chatContent.value) {
      chatContent.value.scrollTop = chatContent.value.scrollHeight
    }
  })
}

const clearHistory = () => {
  chatHistory.value = [chatHistory.value[0]] // 保留系统欢迎消息
}

const formatMessage = (text) => {
  // 处理换行
  text = text.replace(/\n/g, '<br>')
  
  // 处理颜色关键词高亮
  Object.entries(COLOR_EN_TO_CN).forEach(([en, cn]) => {
    const pattern = new RegExp(cn, 'g')
    text = text.replace(pattern, `<span class="color-keyword" style="color: ${en}">${cn}</span>`)
  })
  
  return text
}

const formatTime = (timestamp) => {
  return dayjs(timestamp).format('HH:mm')
}

// 监听分析结果变化
watch(() => props.analysisResult, (newResult) => {
  if (newResult) {
    addMessage('system', `分析完成，检测到 ${newResult.num_faces} 个人物。你可以开始查询了！`)
  }
})
</script>

<style scoped>
.chat-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.chat-card {
  height: 100%;
  display: grid;
  grid-template-rows: 56px 1fr auto;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.assistant-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.assistant-icon {
  border-radius: 6px;
  padding: 4px;
  background: linear-gradient(90deg,#2dd4bf,#06b6d4);
  color: white;
}
.assistant-name {
  font-weight: 700;
  color: #111827;
}

.chat-messages {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px;
}
.message-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.avatar-col {
  width: 40px;
  display:flex;
  align-items: flex-end;
  justify-content:center;
}
.avatar {
  width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;
}
.assistant-avatar{background:linear-gradient(90deg,#2dd4bf,#06b6d4)}
.user-avatar{background:#6b7280}
.bubble-col{max-width:calc(100% - 100px)}
.bubble{padding:10px 12px;border-radius:10px;box-shadow:0 6px 12px rgba(0,0,0,0.04)}
.bubble-user{background:linear-gradient(180deg,#3b82f6,#2563eb);color:#fff;margin-left:auto}
.bubble-assistant{background:#f8fafc;color:#0f172a}
.message-time{font-size:12px;color:#9ca3af;margin-top:6px}
.empty-state{
  padding:30px;
  text-align:center;
  color:#9ca3af;
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  min-height:200px;
}

.chat-content {
  overflow-y: auto;
  padding: 12px;
  background: linear-gradient(180deg,#ffffff,#fbfdff);
}

.chat-messages {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  max-width: 80%;
  margin: 8px 0;
  padding: 12px;
  border-radius: 8px;
  word-break: break-word;
}

.message.user {
  align-self: flex-end;
  background-color: var(--el-color-primary-light-9);
  margin-left: 20%;
}

.message.system {
  align-self: flex-start;
  background-color: #f4f4f5;
  margin-right: 20%;
}

.color-keyword {
  font-weight: 500;
  padding: 0 2px;
}

.message-text {
  word-break: break-word;
  line-height: 1.4;
}

.message-time {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  text-align: right;
}

.chat-input {
  padding: 0;
  border-top: 1px solid var(--el-border-color-light);
  background-color: white;
}

.input-wrapper {
  display:flex;
  gap:8px;
  align-items:center;
  padding:12px;
  background: linear-gradient(180deg,#fff,#fbfdff);
  border-top: 1px solid #eef2f6;
}

.input-box ::v-deep .el-textarea__inner {
  border-radius: 10px;
  padding:12px;
  min-height:56px;
  box-shadow: inset 0 1px 2px rgba(16,24,40,0.03);
  border: 1px solid #e6eef6;
}

.send-button {
  height:48px;
  padding: 0 20px;
  border-radius:10px;
  background: linear-gradient(90deg,#3b82f6,#2563eb);
  color: #fff;
  border: none;
}
.send-button:hover { filter: brightness(0.97); }

.input-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

:deep(.el-textarea__inner) {
  resize: none;
}
</style> 