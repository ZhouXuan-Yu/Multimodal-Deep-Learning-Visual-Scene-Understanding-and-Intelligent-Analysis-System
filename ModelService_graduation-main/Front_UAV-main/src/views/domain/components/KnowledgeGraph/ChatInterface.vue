<script setup>
import { ref, onMounted, watch, nextTick } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import knowledgeGraphService from '../../services/knowledgeGraphService';

const props = defineProps({
  initialMessages: {
    type: Array,
    default: () => [
      {
        role: 'assistant',
        content: '你好！我是知识库智能助手。我可以帮你查询关于旅行、图像识别等信息，还可以联网搜索最新资料。请问有什么我可以帮助你的？'
      }
    ]
  }
});

const emit = defineEmits(['messageSubmit']);

const userInput = ref('');
const chatHistory = ref(props.initialMessages);
const isLoading = ref(false);
const isStreaming = ref(false);
const streamingContent = ref('');
const chatMessagesContainer = ref(null);
const webSearchEnabled = ref(false);

// 格式化markdown
const formatMarkdown = (text) => {
  if (!text) return '';
  const sanitizedHtml = DOMPurify.sanitize(marked.parse(text));
  return sanitizedHtml;
};

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || isLoading.value) return;
  
  // 添加用户消息到聊天历史
  chatHistory.value.push({
    role: 'user',
    content: userInput.value
  });
  
  // 清空输入框
  const message = userInput.value;
  userInput.value = '';
  
  // 开始加载状态
  isLoading.value = true;
  
  try {
    // 添加一个临时的AI回复消息，用于显示流式响应
    chatHistory.value.push({
      role: 'assistant',
      content: '',
      streaming: true
    });
    
    await nextTick();
    scrollToBottom();
    
    // 调用API发送消息
    const response = await knowledgeGraphService.sendMessage(
      message,
      webSearchEnabled.value
    );
    
    if (!response.ok) {
      throw new Error('网络请求失败');
    }
    
    // 处理流式响应
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    isStreaming.value = true;
    streamingContent.value = '';
    
    let lastMessage = chatHistory.value[chatHistory.value.length - 1];
    
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.substring(6);
          if (data === '[DONE]') {
            // 流式响应结束
          } else {
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                streamingContent.value += parsed.content;
                // 更新最后一条消息的内容
                lastMessage.content = streamingContent.value;
                await nextTick();
                scrollToBottom();
              }
            } catch (e) {
              console.error('解析流式响应失败', e);
            }
          }
        }
      }
    }
    
    // 流式响应结束，更新聊天历史
    lastMessage.streaming = false;
    
  } catch (error) {
    console.error('发送消息失败', error);
    // 添加错误消息
    chatHistory.value.push({
      role: 'system',
      content: '消息发送失败，请重试。'
    });
  } finally {
    isLoading.value = false;
    isStreaming.value = false;
    streamingContent.value = '';
    scrollToBottom();
  }
};

// 滚动到底部
const scrollToBottom = () => {
  if (chatMessagesContainer.value) {
    chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
  }
};

// 清除聊天历史
const clearChatHistory = () => {
  chatHistory.value = [
    {
      role: 'assistant',
      content: '聊天历史已清空，有什么我可以帮你的吗？'
    }
  ];
};

// 监听聊天历史变化，自动滚动到底部
watch(chatHistory, () => {
  nextTick(scrollToBottom);
}, { deep: true });

onMounted(() => {
  scrollToBottom();
});
</script>

<template>
  <div class="chat-interface">
    <!-- 聊天消息区域 -->
    <div ref="chatMessagesContainer" class="chat-messages">
      <div 
        v-for="(message, index) in chatHistory" 
        :key="index"
        :class="['message-container', message.role]"
      >
        <div class="avatar">
          <span v-if="message.role === 'user'" class="avatar-icon user-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
          </span>
          <span v-else-if="message.role === 'assistant'" class="avatar-icon ai-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"></path>
              <path d="M8.5 8.5v.01"></path>
              <path d="M16 12v.01"></path>
              <path d="M12 16v.01"></path>
            </svg>
          </span>
          <span v-else class="avatar-icon system-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 5v14"></path>
              <path d="M5 12h14"></path>
            </svg>
          </span>
        </div>
        <div class="message-content">
          <div v-if="message.streaming" class="message-text streaming">
            <div v-html="formatMarkdown(message.content)"></div>
            <span class="cursor"></span>
          </div>
          <div v-else class="message-text" v-html="formatMarkdown(message.content)"></div>
        </div>
      </div>
    </div>
    
    <!-- 输入区域 -->
    <div class="chat-input-container">
      <div class="options">
        <label class="web-search-toggle">
          <input type="checkbox" v-model="webSearchEnabled">
          <span>联网搜索</span>
        </label>
        <button 
          @click="clearChatHistory" 
          class="clear-button"
          title="清空聊天历史"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 6h18"></path>
            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
          </svg>
        </button>
      </div>
      <div class="input-area">
        <textarea 
          v-model="userInput" 
          @keydown.enter.prevent="sendMessage"
          placeholder="输入你的问题..."
          :disabled="isLoading"
        ></textarea>
        <button 
          @click="sendMessage" 
          :disabled="isLoading || !userInput.trim()"
          class="send-button"
        >
          <svg v-if="isLoading" class="loading-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 2L11 13"></path>
            <path d="M22 2l-7 20-4-9-9-4 20-7z"></path>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-interface {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: white;
  border-radius: 0.5rem;
  overflow: hidden;
}

.chat-messages {
  flex-grow: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 300px;
  max-height: 500px;
}

.message-container {
  display: flex;
  gap: 0.75rem;
  animation: fadeIn 0.3s ease-in-out;
}

.message-container.user {
  justify-content: flex-end;
}

.avatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  border-radius: 50%;
}

.user-icon {
  background-color: #4f46e5;
}

.ai-icon {
  background-color: #10b981;
}

.system-icon {
  background-color: #f59e0b;
}

.message-content {
  flex-grow: 1;
  max-width: calc(100% - 60px);
}

.message-text {
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  background-color: #f3f4f6;
  font-size: 0.875rem;
  line-height: 1.5;
}

.user .message-text {
  background-color: #e0e7ff;
}

.assistant .message-text {
  background-color: #f3f4f6;
}

.system .message-text {
  background-color: #fef3c7;
  color: #92400e;
}

.streaming .cursor {
  display: inline-block;
  width: 0.5rem;
  height: 1rem;
  background-color: #000;
  margin-left: 0.25rem;
  animation: blink 1s step-end infinite;
}

.chat-input-container {
  padding: 1rem;
  border-top: 1px solid #e5e7eb;
}

.options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.web-search-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #4b5563;
  cursor: pointer;
}

.clear-button {
  background: none;
  border: none;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem;
  border-radius: 0.25rem;
}

.clear-button:hover {
  background-color: #f3f4f6;
}

.input-area {
  display: flex;
  gap: 0.5rem;
}

textarea {
  flex-grow: 1;
  padding: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  resize: none;
  height: 2.5rem;
  font-size: 0.875rem;
  line-height: 1.25rem;
  outline: none;
}

textarea:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.1);
}

.send-button {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #4f46e5;
  color: white;
  border: none;
  border-radius: 0.5rem;
  padding: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.send-button:disabled {
  background-color: #9ca3af;
  cursor: not-allowed;
}

.send-button:not(:disabled):hover {
  background-color: #4338ca;
}

.loading-icon {
  animation: rotate 1s linear infinite;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
