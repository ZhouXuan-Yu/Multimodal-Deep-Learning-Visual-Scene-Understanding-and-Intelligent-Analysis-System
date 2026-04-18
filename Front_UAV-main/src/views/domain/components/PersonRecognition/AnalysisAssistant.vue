<template>
  <div class="analysis-assistant">
    <div class="assistant-header">
      <div class="assistant-title">
        <svg class="assistant-icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="24" height="24">
          <path d="M79.11424 270.67904l116.2496 66.9952a97.1776 97.1776 0 0 0-4.87424 30.57664v268.7232a97.53088 97.53088 0 0 0 47.39584 83.72736l219.42784 131.31264a97.28 97.28 0 0 0 15.4112 7.45984v153.84576a97.6384 97.6384 0 0 1-11.06944-5.70368L120.32 803.34848a97.51552 97.51552 0 0 1-47.44704-83.62496v-414.72c0-11.89376 2.19648-23.5008 6.2464-34.32448z m871.4752 34.32448v414.67392a97.52576 97.52576 0 0 1-47.44704 83.67104L561.8176 1007.6672c-3.6096 2.0992-7.31648 3.99872-11.06944 5.6576v-157.6448c2.28864-1.1264 4.5312-2.34496 6.72768-3.6608l219.42784-131.31264a97.53088 97.53088 0 0 0 47.44192-83.72736V368.25088a97.07008 97.07008 0 0 0-1.36192-16.384l124.3904-71.68c2.0992 7.99744 3.2256 16.3328 3.2256 24.81664zM561.8176 17.06496l336.59904 201.39008-118.2464 68.11648c-1.0752-0.70144-2.16576-1.3824-3.26656-2.048l-219.42784-131.31264a97.52576 97.52576 0 0 0-100.15744 0L248.32 278.28224l-113.76128-65.536L461.65504 17.06496a97.52576 97.52576 0 0 1 100.15744 0z" fill="currentColor"></path>
          <path d="M264.60672 365.22496L483.84 491.0336v275.98848a97.34144 97.34144 0 0 1-31.7952-12.09344L304.7936 667.1616a97.52576 97.52576 0 0 1-47.54432-83.77344V402.3808c0-12.96896 2.5856-25.5488 7.31136-37.15584h0.0512z m482.10944 37.15584v181.00736c0 34.3552-18.07872 66.18112-47.5904 83.77344l-147.21536 87.76704c-2.58048 1.51552-5.21728 2.92864-7.90016 4.2496V499.6608l201.04704-115.27168c1.11104 5.9392 1.664 11.9552 1.65888 17.99168z m-194.80576-171.54048l147.26144 87.77216a97.536 97.536 0 0 1 17.26464 13.16352l-193.39264 110.83776h-3.21536L304.29696 318.90432l0.49152-0.34304L452.0448 230.78912a97.52576 97.52576 0 0 1 99.86048 0v0.0512z" fill="currentColor"></path>
        </svg>
        <span>智眸助手</span>
      </div>
      <div class="header-actions">
        <button class="action-btn" @click="clearChat" title="清空聊天">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 6H21M19 6V20C19 21.1046 18.1046 22 17 22H7C5.89543 22 5 21.1046 5 20V6M8 6V4C8 2.89543 8.89543 2 10 2H14C15.1046 2 16 2.89543 16 4V6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M10 11V17M14 11V17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </div>
    
    <div class="assistant-content">
      <div class="chat-container" ref="chatContainerRef">
        <div class="messages">
          <div v-for="(message, index) in chatMessages" 
               :key="index" 
               :class="['message', message.role]">
            <div v-if="message.role === 'assistant'" class="message-avatar">
              <svg class="avatar-svg" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="26" height="26">
                <path d="M79.11424 270.67904l116.2496 66.9952a97.1776 97.1776 0 0 0-4.87424 30.57664v268.7232a97.53088 97.53088 0 0 0 47.39584 83.72736l219.42784 131.31264a97.28 97.28 0 0 0 15.4112 7.45984v153.84576a97.6384 97.6384 0 0 1-11.06944-5.70368L120.32 803.34848a97.51552 97.51552 0 0 1-47.44704-83.62496v-414.72c0-11.89376 2.19648-23.5008 6.2464-34.32448z m871.4752 34.32448v414.67392a97.52576 97.52576 0 0 1-47.44704 83.67104L561.8176 1007.6672c-3.6096 2.0992-7.31648 3.99872-11.06944 5.6576v-157.6448c2.28864-1.1264 4.5312-2.34496 6.72768-3.6608l219.42784-131.31264a97.53088 97.53088 0 0 0 47.44192-83.72736V368.25088a97.07008 97.07008 0 0 0-1.36192-16.384l124.3904-71.68c2.0992 7.99744 3.2256 16.3328 3.2256 24.81664zM561.8176 17.06496l336.59904 201.39008-118.2464 68.11648c-1.0752-0.70144-2.16576-1.3824-3.26656-2.048l-219.42784-131.31264a97.52576 97.52576 0 0 0-100.15744 0L248.32 278.28224l-113.76128-65.536L461.65504 17.06496a97.52576 97.52576 0 0 1 100.15744 0z" fill="currentColor"></path>
                <path d="M264.60672 365.22496L483.84 491.0336v275.98848a97.34144 97.34144 0 0 1-31.7952-12.09344L304.7936 667.1616a97.52576 97.52576 0 0 1-47.54432-83.77344V402.3808c0-12.96896 2.5856-25.5488 7.31136-37.15584h0.0512z m482.10944 37.15584v181.00736c0 34.3552-18.07872 66.18112-47.5904 83.77344l-147.21536 87.76704c-2.58048 1.51552-5.21728 2.92864-7.90016 4.2496V499.6608l201.04704-115.27168c1.11104 5.9392 1.664 11.9552 1.65888 17.99168z m-194.80576-171.54048l147.26144 87.77216a97.536 97.536 0 0 1 17.26464 13.16352l-193.39264 110.83776h-3.21536L304.29696 318.90432l0.49152-0.34304L452.0448 230.78912a97.52576 97.52576 0 0 1 99.86048 0v0.0512z" fill="currentColor"></path>
              </svg>
            </div>
            <div v-else class="message-avatar user-avatar">
              <svg viewBox="0 0 24 24" width="26" height="26" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 12C14.7614 12 17 9.76142 17 7C17 4.23858 14.7614 2 12 2C9.23858 2 7 4.23858 7 7C7 9.76142 9.23858 12 12 12Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M20.5899 22C20.5899 18.13 16.7399 15 11.9999 15C7.25991 15 3.40991 18.13 3.40991 22" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="message-bubble">
              <div class="message-content" v-html="formatMessage(message.content)"></div>
              
              <div v-if="message.matches && message.matches.length" class="matches-container">
                <div v-for="match in message.matches" 
                     :key="match.id" 
                     class="match-item" 
                     @click="$emit('highlight-person', match.id)">
                  <div class="match-label">人物 {{ match.id + 1 }}</div>
                  <div class="match-details">
                    <span class="detail-item">{{ translateGender(match.gender) }}</span>
                    <span class="detail-item">{{ Math.round(match.age) }}岁</span>
                    <span class="color-tag" :style="getColorStyle(match.upper_color)">
                      上衣: {{ translateColor(match.upper_color) }}
                    </span>
                    <span class="color-tag" :style="getColorStyle(match.lower_color)">
                      下装: {{ translateColor(match.lower_color) }}
                    </span>
                  </div>
                </div>
              </div>
              
              <div class="message-time">{{ formatTime(message.timestamp) }}</div>
            </div>
          </div>
          
          <!-- 流式输出显示 -->
          <div v-if="isStreaming" class="message assistant">
            <div class="message-avatar">
              <svg class="avatar-svg" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="26" height="26">
                <path d="M79.11424 270.67904l116.2496 66.9952a97.1776 97.1776 0 0 0-4.87424 30.57664v268.7232a97.53088 97.53088 0 0 0 47.39584 83.72736l219.42784 131.31264a97.28 97.28 0 0 0 15.4112 7.45984v153.84576a97.6384 97.6384 0 0 1-11.06944-5.70368L120.32 803.34848a97.51552 97.51552 0 0 1-47.44704-83.62496v-414.72c0-11.89376 2.19648-23.5008 6.2464-34.32448z m871.4752 34.32448v414.67392a97.52576 97.52576 0 0 1-47.44704 83.67104L561.8176 1007.6672c-3.6096 2.0992-7.31648 3.99872-11.06944 5.6576v-157.6448c2.28864-1.1264 4.5312-2.34496 6.72768-3.6608l219.42784-131.31264a97.53088 97.53088 0 0 0 47.44192-83.72736V368.25088a97.07008 97.07008 0 0 0-1.36192-16.384l124.3904-71.68c2.0992 7.99744 3.2256 16.3328 3.2256 24.81664zM561.8176 17.06496l336.59904 201.39008-118.2464 68.11648c-1.0752-0.70144-2.16576-1.3824-3.26656-2.048l-219.42784-131.31264a97.52576 97.52576 0 0 0-100.15744 0L248.32 278.28224l-113.76128-65.536L461.65504 17.06496a97.52576 97.52576 0 0 1 100.15744 0z" fill="currentColor"></path>
                <path d="M264.60672 365.22496L483.84 491.0336v275.98848a97.34144 97.34144 0 0 1-31.7952-12.09344L304.7936 667.1616a97.52576 97.52576 0 0 1-47.54432-83.77344V402.3808c0-12.96896 2.5856-25.5488 7.31136-37.15584h0.0512z m482.10944 37.15584v181.00736c0 34.3552-18.07872 66.18112-47.5904 83.77344l-147.21536 87.76704c-2.58048 1.51552-5.21728 2.92864-7.90016 4.2496V499.6608l201.04704-115.27168c1.11104 5.9392 1.664 11.9552 1.65888 17.99168z m-194.80576-171.54048l147.26144 87.77216a97.536 97.536 0 0 1 17.26464 13.16352l-193.39264 110.83776h-3.21536L304.29696 318.90432l0.49152-0.34304L452.0448 230.78912a97.52576 97.52576 0 0 1 99.86048 0v0.0512z" fill="currentColor"></path>
              </svg>
            </div>
            <div class="message-bubble">
              <div class="message-content" v-html="formatMessage(streamingContent)"></div>
            </div>
          </div>
          
          <!-- 思考指示器 -->
          <div v-if="isProcessing && !isStreaming" class="message assistant">
            <div class="message-avatar">
              <svg class="avatar-svg" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="26" height="26">
                <path d="M79.11424 270.67904l116.2496 66.9952a97.1776 97.1776 0 0 0-4.87424 30.57664v268.7232a97.53088 97.53088 0 0 0 47.39584 83.72736l219.42784 131.31264a97.28 97.28 0 0 0 15.4112 7.45984v153.84576a97.6384 97.6384 0 0 1-11.06944-5.70368L120.32 803.34848a97.51552 97.51552 0 0 1-47.44704-83.62496v-414.72c0-11.89376 2.19648-23.5008 6.2464-34.32448z m871.4752 34.32448v414.67392a97.52576 97.52576 0 0 1-47.44704 83.67104L561.8176 1007.6672c-3.6096 2.0992-7.31648 3.99872-11.06944 5.6576v-157.6448c2.28864-1.1264 4.5312-2.34496 6.72768-3.6608l219.42784-131.31264a97.53088 97.53088 0 0 0 47.44192-83.72736V368.25088a97.07008 97.07008 0 0 0-1.36192-16.384l124.3904-71.68c2.0992 7.99744 3.2256 16.3328 3.2256 24.81664zM561.8176 17.06496l336.59904 201.39008-118.2464 68.11648c-1.0752-0.70144-2.16576-1.3824-3.26656-2.048l-219.42784-131.31264a97.52576 97.52576 0 0 0-100.15744 0L248.32 278.28224l-113.76128-65.536L461.65504 17.06496a97.52576 97.52576 0 0 1 100.15744 0z" fill="currentColor"></path>
                <path d="M264.60672 365.22496L483.84 491.0336v275.98848a97.34144 97.34144 0 0 1-31.7952-12.09344L304.7936 667.1616a97.52576 97.52576 0 0 1-47.54432-83.77344V402.3808c0-12.96896 2.5856-25.5488 7.31136-37.15584h0.0512z m482.10944 37.15584v181.00736c0 34.3552-18.07872 66.18112-47.5904 83.77344l-147.21536 87.76704c-2.58048 1.51552-5.21728 2.92864-7.90016 4.2496V499.6608l201.04704-115.27168c1.11104 5.9392 1.664 11.9552 1.65888 17.99168z m-194.80576-171.54048l147.26144 87.77216a97.536 97.536 0 0 1 17.26464 13.16352l-193.39264 110.83776h-3.21536L304.29696 318.90432l0.49152-0.34304L452.0448 230.78912a97.52576 97.52576 0 0 1 99.86048 0v0.0512z" fill="currentColor"></path>
              </svg>
            </div>
            <div class="message-bubble">
              <div class="thinking-indicator">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="input-container">
        <input 
          type="text" 
          class="query-input" 
          v-model="query" 
          @keyup.enter="sendQuery" 
          :disabled="isProcessing || !props.analysisResult"
          :placeholder="props.analysisResult ? '请输入您的问题...' : '请先上传并分析图片...'"
        />
        <button 
          class="send-button" 
          @click="sendQuery" 
          :disabled="isProcessing || !query || !props.analysisResult"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M10.3009 13.6948L20.102 3.89355M10.5795 14.1663L12.8019 19.1549C13.339 20.2554 13.6075 20.8056 13.9458 20.9096C14.2394 21.0001 14.5594 20.9488 14.811 20.7726C15.0975 20.5719 15.2389 19.9792 15.5219 18.7939L19.6151 4.46269C19.8762 3.3467 20.0067 2.78871 19.8691 2.47366C19.7474 2.19966 19.5048 2.00096 19.2159 1.9317C18.8834 1.8528 18.3019 2.08466 17.1389 2.54839L3.92493 8.33471C2.65673 8.84299 2.02262 9.09713 1.84846 9.40082C1.69772 9.66539 1.68491 9.99732 1.81712 10.2726C1.96985 10.5912 2.56186 10.7973 3.74589 11.2094L8.6902 12.9559C9.36765 13.2062 9.70637 13.3314 9.96124 13.5555C10.182 13.7507 10.3547 13.9996 10.4631 14.2752C10.5868 14.5897 10.5868 14.9465 10.5868 15.6602V19.9879C10.5868 20.7798 10.5868 21.1757 10.7993 21.3338C10.9879 21.474 11.2441 21.4749 11.4658 21.3337C11.7119 21.1752 11.8301 20.7684 12.0663 19.9547L13.826 15.4871" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
      
      <div class="features-container">
        <div class="feature-label">快速查询</div>
        <div class="quick-queries">
          <button 
            v-for="(query, idx) in quickQueries" 
            :key="idx" 
            class="quick-query-btn"
            @click="useQuickQuery(query)"
            :disabled="isProcessing || !props.analysisResult"
          >
            {{ query }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted } from 'vue';
import personRecognitionService from '../../services/personRecognitionService';
import imageAnalysisChatService from '../../services/imageAnalysisChatService';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

const props = defineProps({
  analysisResult: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['highlight-person']);

// 状态变量
const query = ref('');
const chatMessages = ref([]);
const chatContainerRef = ref(null);
const isProcessing = ref(false);
const isStreaming = ref(false);
const streamingContent = ref('');

// 快速查询
const quickQueries = [
  '查找所有男性',
  '查找所有女性',
  '找到穿黑色上衣的人',
  '找到穿蓝色下装的人',
  '人物统计信息'
];

// 发送查询
const sendQuery = async () => {
  if (!query.value || !props.analysisResult || isProcessing.value) return;
  
  const queryText = query.value;
  query.value = '';
  isProcessing.value = true;
  
  // 添加用户消息
  addMessage({
    role: 'user',
    content: queryText,
    timestamp: new Date()
  });
  
  try {
    // 滚动到底部
    scrollToBottom();
    
    // 优先尝试使用后端大模型API
    let response = null;
    let useBackendApi = true;
    streamingContent.value = '';
    
    try {
      console.log('尝试使用后端大模型API处理查询...');
      // 使用流式输出
      isStreaming.value = true;
      
      const apiResponse = await imageAnalysisChatService.sendMessage(
      queryText, 
        props.analysisResult,
        true // 使用流式输出
      );
      
      if (!apiResponse.ok) {
        throw new Error(`API错误: ${apiResponse.status}`);
      }
      
      // 处理流式响应
      const reader = apiResponse.body.getReader();
      const decoder = new TextDecoder();
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        // 解码并添加到内容
        const chunk = decoder.decode(value, { stream: true });
        streamingContent.value += chunk;
        
        // 自动滚动到底部
        scrollToBottom();
      }
      
      // 流式响应结束，更新消息
      const matches = findMatchesFromText(streamingContent.value, props.analysisResult.persons);
      
      // 添加最终消息
      addMessage({
        role: 'assistant',
        content: streamingContent.value,
        matches: matches,
        timestamp: new Date()
      });
      
      // 如果有匹配的人物，选中第一个
      if (matches && matches.length > 0) {
        emit('highlight-person', matches[0].id);
      }
      
      // 成功处理，不需要使用本地处理
      useBackendApi = false;
    } catch (error) {
      console.warn('后端大模型API请求失败，切换到本地处理:', error);
      useBackendApi = false;
    } finally {
      isStreaming.value = false;
    }
    
    // 如果后端API处理失败，使用本地处理
    if (useBackendApi) {
      console.log('使用本地处理逻辑进行查询...');
      response = fallbackQueryHandler(queryText, props.analysisResult.persons);
    
    // 添加助手回复
    addMessage({
      role: 'assistant',
      content: response.response,
      matches: response.matches || [],
      timestamp: new Date()
    });
    
    // 如果有匹配的人物，选中第一个
    if (response.matches && response.matches.length > 0) {
      emit('highlight-person', response.matches[0].id);
      }
    }
  } catch (error) {
    console.error('处理查询时出错:', error);
    
    addMessage({
      role: 'assistant',
      content: '很抱歉，处理您的查询时遇到了问题。请尝试重新提问或者使用快速查询。',
      timestamp: new Date()
    });
  } finally {
    isProcessing.value = false;
    streamingContent.value = '';
  }
};

// 从大模型回复中提取匹配的人物
const findMatchesFromText = (text, persons) => {
  // 尝试从文本中识别提到的人物
  const matches = [];
  
  if (!persons || !Array.isArray(persons) || persons.length === 0) {
    return matches;
  }
  
  // 检查文本是否提到了特定的人物编号
  const personRegex = /人物\s*(\d+)/g;
  let match;
  
  while ((match = personRegex.exec(text)) !== null) {
    const personNum = parseInt(match[1]);
    if (personNum > 0 && personNum <= persons.length) {
      // 人物索引是基于0的，但显示是从1开始
      const person = persons[personNum - 1];
      
      // 避免重复添加
      if (!matches.some(m => m.id === personNum - 1)) {
        matches.push({
          id: personNum - 1,
          ...person
        });
      }
    }
  }
  
  // 如果没有找到特定人物，但文本包含特定特征，可以尝试匹配
  const lowerText = text.toLowerCase();
  
  if (matches.length === 0) {
    persons.forEach((person, index) => {
      let shouldInclude = false;
      
      // 性别匹配检查
      if (
        (lowerText.includes('男') && person.gender === 'male') ||
        (lowerText.includes('女') && person.gender === 'female')
      ) {
        shouldInclude = true;
      }
      
      // 颜色匹配检查
      const colorMap = {
        '红': 'red', '蓝': 'blue', '绿': 'green', '黄': 'yellow',
        '黑': 'black', '白': 'white', '灰': 'gray'
      };
      
      for (const [cn, en] of Object.entries(colorMap)) {
        if (lowerText.includes(cn) || lowerText.includes(en)) {
          if (person.upper_color === en || person.lower_color === en) {
            shouldInclude = true;
            break;
          }
        }
      }
      
      if (shouldInclude) {
        matches.push({
          id: index,
          ...person
        });
      }
    });
  }
  
  return matches;
};

// 备用查询处理函数
const fallbackQueryHandler = (query, persons) => {
  // 简单关键词匹配
  const queryLower = query.toLowerCase();
  const matches = [];
  
  // 记录匹配的标准
  const matchReasons = {
    gender: false,
    age: false,
    upperColor: false,
    lowerColor: false,
    position: false
  };
  
  // 匹配逻辑
  persons.forEach((person, index) => {
    let isMatch = false;
    const personMatches = {};
    
    // 性别匹配
    if (
      (queryLower.includes('男') && person.gender === 'male') ||
      (queryLower.includes('女') && person.gender === 'female')
    ) {
      isMatch = true;
      matchReasons.gender = true;
      personMatches.gender = true;
    }
    
    // 年龄匹配
    if (
      ((queryLower.includes('年轻') || queryLower.includes('小于30')) && person.age < 30) ||
      ((queryLower.includes('老') || queryLower.includes('大于50')) && person.age > 50) ||
      (queryLower.includes('中年') && person.age >= 30 && person.age <= 50)
    ) {
      isMatch = true;
      matchReasons.age = true;
      personMatches.age = true;
    }
    
    // 颜色匹配 - 上衣
    const upperColors = {
      '红': 'red', '蓝': 'blue', '绿': 'green', '黄': 'yellow',
      '黑': 'black', '白': 'white', '灰': 'gray'
    };
    
    for (const [cn, en] of Object.entries(upperColors)) {
      if ((queryLower.includes(cn + '上衣') || queryLower.includes(cn + '衣') || 
           queryLower.includes(en + ' upper') || queryLower.includes(en + ' shirt')) && 
          person.upper_color === en) {
        isMatch = true;
        matchReasons.upperColor = true;
        personMatches.upperColor = true;
        break;
      }
    }
    
    // 颜色匹配 - 下装
    const lowerColors = {
      '红': 'red', '蓝': 'blue', '绿': 'green', '黄': 'yellow',
      '黑': 'black', '白': 'white', '灰': 'gray'
    };
    
    for (const [cn, en] of Object.entries(lowerColors)) {
      if ((queryLower.includes(cn + '裤') || queryLower.includes(cn + '下装') || 
           queryLower.includes(en + ' lower') || queryLower.includes(en + ' pants')) && 
          person.lower_color === en) {
        isMatch = true;
        matchReasons.lowerColor = true;
        personMatches.lowerColor = true;
        break;
      }
    }
    
    // 位置匹配
    if ((queryLower.includes('左') || queryLower.includes('left')) && person.bbox && person.bbox[0] < 50) {
      isMatch = true;
      matchReasons.position = true;
      personMatches.position = 'left';
    } else if ((queryLower.includes('右') || queryLower.includes('right')) && person.bbox && person.bbox[0] > 50) {
      isMatch = true;
      matchReasons.position = true;
      personMatches.position = 'right';
    }
    
    // 如果匹配，添加到结果
    if (isMatch) {
      matches.push({
        id: index,
        ...person,
        matchReasons: personMatches
      });
    }
  });
  
  // 生成回复
  let response = '';
  
  if (queryLower.includes('统计') || queryLower.includes('有多少') || queryLower.includes('几个') || queryLower.includes('多少人')) {
    // 统计信息
    let maleCount = 0;
    let femaleCount = 0;
    
    persons.forEach(person => {
      if (person.gender === 'male') maleCount++;
      else if (person.gender === 'female') femaleCount++;
    });
    
    response = `## 人物统计信息\n\n图中共检测到 ${persons.length} 个人物，其中：\n- 男性：${maleCount} 人\n- 女性：${femaleCount} 人\n\n可以继续询问更详细的信息。`;
  } else if (matches.length > 0) {
    // 匹配结果
    if (matches.length === 1) {
      const person = matches[0];
      response = `## 找到匹配的人物\n\n检测到 1 个符合条件的人物：\n\n### 人物 ${person.id + 1}\n- 性别：${translateGender(person.gender)} (置信度: ${Math.round(person.gender_confidence * 100)}%)\n- 年龄：${Math.round(person.age)} 岁 (置信度: ${Math.round(person.age_confidence * 100)}%)\n- 上衣颜色：${translateColor(person.upper_color)} (置信度: ${Math.round(person.upper_color_confidence * 100)}%)\n- 下装颜色：${translateColor(person.lower_color)} (置信度: ${Math.round(person.lower_color_confidence * 100)}%)`;
    } else {
      response = `## 找到多个匹配的人物\n\n检测到 ${matches.length} 个符合条件的人物：\n\n`;
      
      matches.forEach((person, idx) => {
        response += `### 人物 ${person.id + 1}\n- 性别：${translateGender(person.gender)}\n- 年龄：${Math.round(person.age)} 岁\n- 上衣颜色：${translateColor(person.upper_color)}\n- 下装颜色：${translateColor(person.lower_color)}\n\n`;
      });
    }
  } else {
    // 没有匹配结果
    response = '## 未找到匹配结果\n\n很抱歉，未能找到符合您描述的人物。请尝试使用其他特征进行查询，如性别、年龄、衣物颜色等。';
  }
  
  return {
    response,
    matches
  };
};

// 添加消息到聊天记录
const addMessage = (message) => {
  chatMessages.value.push(message);
  
  // 滚动到底部
  nextTick(() => {
    scrollToBottom();
  });
};

// 使用快速查询
const useQuickQuery = (queryText) => {
  if (isProcessing.value) return;
  query.value = queryText;
  sendQuery();
};

// 清空聊天记录
const clearChat = () => {
  chatMessages.value = [];
  
  // 添加欢迎消息
  if (props.analysisResult) {
    addMessage({
      role: 'assistant',
      content: `# 欢迎使用智眸助手\n\n我已经分析了您的图片，检测到 ${props.analysisResult.persons?.length || 0} 个人物。\n\n您可以向我询问以下类型的问题：\n- 找到所有男性/女性\n- 找到穿特定颜色衣服的人\n- 找到位于图片左侧/右侧的人\n- 找到年龄最大/最小的人\n- 获取图片中人物的统计信息\n\n您也可以使用下方的快捷查询按钮，或者输入自己的问题。`,
      timestamp: new Date()
    });
  }
};

// 格式化消息内容（Markdown -> HTML）
const formatMessage = (content) => {
  if (!content) return '';
  
  // 使用DOMPurify清理HTML，防止XSS攻击
  return DOMPurify.sanitize(marked.parse(content));
};

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '';
  
  const date = new Date(timestamp);
  return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
};

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainerRef.value) {
      chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight;
    }
  });
};

// 获取颜色样式
const getColorStyle = (colorName) => {
  const colorMap = {
    'red': { bg: '#ef4444', text: 'white' },
    'blue': { bg: '#3b82f6', text: 'white' },
    'green': { bg: '#10b981', text: 'white' },
    'yellow': { bg: '#f59e0b', text: 'black' },
    'black': { bg: '#1f2937', text: 'white' },
    'white': { bg: '#f3f4f6', text: 'black' },
    'gray': { bg: '#6b7280', text: 'white' }
  };
  
  const color = colorMap[colorName] || { bg: '#6b7280', text: 'white' };
  return `background-color: ${color.bg}; color: ${color.text};`;
};

// 翻译性别
const translateGender = (gender) => {
  const genderMap = {
    'male': '男性',
    'female': '女性',
    'unknown': '未知'
  };
  
  return genderMap[gender] || gender;
};

// 翻译颜色
const translateColor = (color) => {
  const colorMap = {
    'red': '红色',
    'blue': '蓝色',
    'green': '绿色',
    'yellow': '黄色',
    'black': '黑色',
    'white': '白色',
    'gray': '灰色'
  };
  
  return colorMap[color] || color;
};

// 监听分析结果变化
watch(() => props.analysisResult, (newResult) => {
  if (newResult) {
    // 清空聊天记录
    chatMessages.value = [];
    
    // 添加欢迎消息
    addMessage({
      role: 'assistant',
      content: `# 欢迎使用智眸助手\n\n我已经分析了您的图片，检测到 ${newResult.persons?.length || 0} 个人物。\n\n您可以向我询问以下类型的问题：\n- 找到所有男性/女性\n- 找到穿特定颜色衣服的人\n- 找到位于图片左侧/右侧的人\n- 找到年龄最大/最小的人\n- 获取图片中人物的统计信息\n\n您也可以使用下方的快捷查询按钮，或者输入自己的问题。`,
      timestamp: new Date()
    });
  }
});

// 组件挂载
onMounted(() => {
  // 如果已有分析结果，显示欢迎消息
  if (props.analysisResult) {
    addMessage({
      role: 'assistant',
      content: `# 欢迎使用智眸助手\n\n我已经分析了您的图片，检测到 ${props.analysisResult.persons?.length || 0} 个人物。\n\n您可以向我询问以下类型的问题：\n- 找到所有男性/女性\n- 找到穿特定颜色衣服的人\n- 找到位于图片左侧/右侧的人\n- 找到年龄最大/最小的人\n- 获取图片中人物的统计信息\n\n您也可以使用下方的快捷查询按钮，或者输入自己的问题。`,
      timestamp: new Date()
    });
  }
});
</script>

<style scoped>
.analysis-assistant {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  background-color: rgba(250, 250, 252, 0.95);
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.05);
  border-radius: 16px;
  overflow: hidden;
}

.assistant-header {
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(90deg, #f8f9fa, #f1f3f5);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
}

.assistant-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #333;
  letter-spacing: 0.5px;
}

.assistant-icon {
  color: #4361ee;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: rgba(67, 97, 238, 0.08);
  border: none;
  border-radius: 8px;
  color: #4361ee;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: rgba(67, 97, 238, 0.16);
}

.assistant-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  overflow: hidden;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f8f9fa;
}

.messages {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 94%;
  animation: fadeIn 0.3s ease;
}

.message-avatar {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  background: rgba(67, 97, 238, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4361ee;
}

.user-avatar {
  background: rgba(67, 97, 238, 0.05);
  color: #6c757d;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-bubble {
  background: #fff;
  border-radius: 16px;
  padding: 14px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  flex: 1;
  max-width: calc(100% - 52px);
}

.message.user .message-bubble {
  background: rgba(67, 97, 238, 0.08);
  border-bottom-right-radius: 4px;
}

.message.assistant .message-bubble {
  background: #fff;
  border-bottom-left-radius: 4px;
}

.message-content {
  font-size: 15px;
  line-height: 1.6;
  color: #333;
  overflow-wrap: break-word;
}

.message-content :deep(h1),
.message-content :deep(h2),
.message-content :deep(h3) {
  color: #4361ee;
  margin-top: 16px;
  margin-bottom: 12px;
  font-weight: 600;
}

.message-content :deep(h1) {
  font-size: 1.5em;
  border-bottom: 1px solid rgba(67, 97, 238, 0.1);
  padding-bottom: 8px;
}

.message-content :deep(h2) {
  font-size: 1.3em;
}

.message-content :deep(h3) {
  font-size: 1.1em;
}

.message-content :deep(ul),
.message-content :deep(ol) {
  padding-left: 20px;
  margin: 12px 0;
}

.message-content :deep(li) {
  margin-bottom: 6px;
}

.message-content :deep(strong) {
  color: #4361ee;
  font-weight: 600;
}

.message-content :deep(code) {
  background: rgba(67, 97, 238, 0.08);
  color: #4361ee;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.message-time {
  font-size: 12px;
  color: #adb5bd;
  margin-top: 6px;
  text-align: right;
}

.matches-container {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.match-item {
  background: rgba(67, 97, 238, 0.05);
  border: 1px solid rgba(67, 97, 238, 0.1);
  border-radius: 10px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.match-item:hover {
  background: rgba(67, 97, 238, 0.08);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(67, 97, 238, 0.1);
}

.match-label {
  color: #4361ee;
  font-weight: 600;
  margin-bottom: 6px;
  font-size: 13px;
}

.match-details {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-item {
  background: rgba(67, 97, 238, 0.05);
  color: #495057;
  padding: 4px 8px;
  border-radius: 4px;
}

.color-tag {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.input-container {
  display: flex;
  gap: 10px;
  padding: 16px;
  background: #fff;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  position: relative;
}

.input-container::before {
  content: '';
  position: absolute;
  top: -10px;
  left: 0;
  right: 0;
  height: 10px;
  background: linear-gradient(to bottom, rgba(248, 249, 250, 0), rgba(248, 249, 250, 1));
  pointer-events: none;
}

.query-input {
  flex: 1;
  padding: 12px 16px;
  background: #f8f9fa;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  color: #333;
  font-size: 15px;
  transition: all 0.2s ease;
}

.query-input:focus {
  outline: none;
  border-color: #4361ee;
  box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.1);
}

.query-input::placeholder {
  color: #adb5bd;
}

.send-button {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #4361ee;
  border: none;
  border-radius: 12px;
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
}

.send-button:hover:not(:disabled) {
  background: #3a56d4;
  transform: translateY(-2px);
}

.send-button:disabled {
  background: #dee2e6;
  cursor: not-allowed;
}

.features-container {
  padding: 10px 16px 16px;
  background: #fff;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.feature-label {
  font-size: 12px;
  color: #adb5bd;
  margin-bottom: 10px;
}

.quick-queries {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-query-btn {
  padding: 8px 12px;
  background: #f8f9fa;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  color: #4361ee;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-query-btn:hover:not(:disabled) {
  background: rgba(67, 97, 238, 0.08);
  transform: translateY(-2px);
}

.quick-query-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.thinking-indicator {
  display: flex;
  gap: 6px;
  justify-content: center;
  padding: 12px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4361ee;
  animation: pulse 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}

.dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes pulse {
  0%, 80%, 100% { 
    transform: scale(0.6);
    opacity: 0.6;
  }
  40% { 
    transform: scale(1);
    opacity: 1;
  }
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

/* 自定义滚动条 */
.chat-container::-webkit-scrollbar {
  width: 6px;
}

.chat-container::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.02);
  border-radius: 3px;
}

.chat-container::-webkit-scrollbar-thumb {
  background: rgba(67, 97, 238, 0.2);
  border-radius: 3px;
}

.chat-container::-webkit-scrollbar-thumb:hover {
  background: rgba(67, 97, 238, 0.4);
}

/* 浮动效果 */
@keyframes float {
  0% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-5px);
  }
  100% {
    transform: translateY(0px);
  }
}

.match-item:hover .match-label {
  animation: float 2s ease-in-out infinite;
}
</style>
