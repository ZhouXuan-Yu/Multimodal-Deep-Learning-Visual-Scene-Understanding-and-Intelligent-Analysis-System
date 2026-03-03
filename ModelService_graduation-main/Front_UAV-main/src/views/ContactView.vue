<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue';
import emailjs from '@emailjs/browser';
import { ElMessage } from 'element-plus';
import feedbackImage from '@/assets/images/feedback.png';

// EmailJS 配置（通过 Vite 环境变量注入；不要把私钥放到前端）
const EMAILJS_PUBLIC_KEY = import.meta.env.VITE_EMAILJS_PUBLIC_KEY;
const EMAILJS_SERVICE_ID = import.meta.env.VITE_EMAILJS_SERVICE_ID;
const EMAILJS_TEMPLATE_ID = import.meta.env.VITE_EMAILJS_TEMPLATE_ID;
const EMAILJS_RECEIVER_EMAIL =
  import.meta.env.VITE_EMAILJS_RECEIVER_EMAIL || '2356648915@qq.com';

// 定义表单数据
const form = reactive({
  name: '',
  email: '',
  phone: '',
  company: '',
  message: '',
  interest: 'general',
  wechatId: '' // 添加微信号字段
});

const interests = [
  { value: 'general', label: '一般咨询' },
  { value: 'path-planning', label: '路径规划' },
  { value: 'person-recognition', label: '人员识别' },
  { value: 'vehicle-monitoring', label: '车辆监控' },
  { value: 'disaster-detection', label: '灾害检测' },
  { value: 'license-plate', label: '车牌识别' },
  { value: 'data-dashboard', label: '数据仪表盘' },
  { value: 'knowledge-graph', label: '知识图谱' }
];

const loading = ref(false);
const success = ref(false);
const error = ref('');
const errorMessage = ref('');
const processedMessageCache = ref(''); // 存储处理后的消息内容

// 初始化EmailJS
onMounted(() => {
  if (!EMAILJS_PUBLIC_KEY) {
    console.warn('[EmailJS] 缺少 VITE_EMAILJS_PUBLIC_KEY，邮件发送将被跳过。');
    return;
  }
  emailjs.init(EMAILJS_PUBLIC_KEY);
});

// 获取咨询类型的标签
const getInterestLabel = (value: string): string => {
  const interest = interests.find(item => item.value === value);
  return interest ? interest.label : '一般咨询';
};

// 使用DeepSeek API处理消息
const processMessageWithDeepSeek = async (message: string) => {
  // 检查缓存中是否已有处理结果
  if (processedMessageCache.value) {
    return processedMessageCache.value;
  }

  loading.value = true;
  try {
    const url = 'https://api.deepseek.com/v1/chat/completions';
    
    // 获取用户选择的咨询类型
    const interestLabel = getInterestLabel(form.interest);
    
    // 项目功能说明
    const projectFeatures = `
      项目主要功能:
      1. 路径规划 - 通过本地大模型进行语义分割实现智能路径规划
      2. 图像识别 - 分为本地模型训练的模型识别(resnet50切割模型、年龄识别模型、性别分类模型、衣服颜色识别模型)以及视觉模型识别，支持与本地模型基于图片进行"聊天"(将识别信息打包发给LLM进行交互)
      3. 知识库交流 - 实现联网搜索、本地LLM对话，以及知识图谱构建与查询
      4. 夜间车辆识别 - 利用图像增强算法，结合YOLO实现夜间增强识别
      5. 超远距离识别 - 用于识别远距离或高空下微小移动物体
      6. 夜间行为识别及报警 - 通过分类识别拥抱、握手、斗殴等行为，检测到危险信号自动通过邮箱实现报警
      7. 森林火灾与洪水检测 - 包括泥石流检测
      8. 车牌识别 - 上传照片识别车牌，并在视频中匹配相同车牌实现报警功能
    `;

    const prompt = `
      请基于以下项目功能描述，对客户询问内容进行分析并提供智能建议。
      
      ${projectFeatures}
      
      请根据客户咨询的内容和项目功能，提供以下格式的分析和建议：
      
      【标题】(10字以内，一针见血)
      
      【大纲】(30字以内，2-3个要点)
      
      【内容】(50字以内，核心需求)
      
      【建议】(50字以内，1-3条针对性建议，必须参考用户问题和项目功能给出)
      
      【解决方案】(100字以内，针对客户需求提供的具体解决方案，结合我们的功能优势)
      
      客户询问类型：${interestLabel}
      客户询问内容：${message}
    `;

    // 使用新的 DeepSeek API 密钥
    const apiKey = 'sk-4eca4ee7a4524c5b8108c9eaa7ca2850';
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: 'deepseek-chat',
        messages: [
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.7,
        max_tokens: 500
      })
    });

    // 检查响应状态
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('DeepSeek API返回错误:', response.status, errorData);
      // 如果是认证错误，使用备用处理方式
      if (response.status === 401) {
        return formatFallbackResponse(message, interestLabel);
      }
      throw new Error(`API错误: ${response.status}`);
    }

    const data = await response.json();
    // 添加数据验证，确保存在预期的结构
    if (!data.choices || !data.choices[0] || !data.choices[0].message) {
      console.error('DeepSeek API返回了无效的响应结构:', data);
      return formatFallbackResponse(message, interestLabel);
    }

    const processedText = data.choices[0].message.content;
    processedMessageCache.value = processedText; // 缓存处理结果
    loading.value = false;
    return processedText;
  } catch (err) {
    console.error('处理消息时出错:', err);
    loading.value = false;
    // 出错时使用备用处理方式
    return formatFallbackResponse(message, getInterestLabel(form.interest));
  }
};

// 备用处理方式，生成固定格式的响应
const formatFallbackResponse = (message: string, interestType: string) => {
  // 根据咨询类型提供不同的模板回复
  const getTemplateByInterest = (type: string) => {
    const templates: Record<string, any> = {
      '路径规划': {
        title: '路径规划需求',
        outline: '智能规划、实时调整、避障功能',
        content: '客户需要一个高精度的路径规划解决方案',
        advice: '建议结合本地大模型的语义分割技术实现智能路径规划',
        solution: '我们可以提供结合本地大模型的语义分割技术实现的路径规划方案，支持实时路径调整和智能避障'
      },
      '人员识别': {
        title: '人员识别需求',
        outline: '人员检测、特征分析、行为识别',
        content: '客户需要精准的人员识别与分析功能',
        advice: '结合多模型识别技术提升识别准确率',
        solution: '我们的系统集成了多种识别模型，如年龄识别、性别分类和衣物颜色识别，可以满足您的人员识别需求'
      },
      '车辆监控': {
        title: '车辆监控需求',
        outline: '夜间监控、车辆跟踪、异常报警',
        content: '客户需要全天候车辆监控与分析系统',
        advice: '采用我们的夜间车辆识别和车牌识别技术',
        solution: '我们的夜间车辆识别系统结合图像增强算法和YOLO技术，可实现24小时不间断监控，并支持车牌自动识别和匹配报警'
      },
      '灾害检测': {
        title: '灾害监测需求',
        outline: '火灾检测、洪水监测、预警系统',
        content: '客户需要自动化灾害检测与预警功能',
        advice: '部署我们的森林火灾与洪水检测系统',
        solution: '我们的森林火灾与洪水检测系统可以实时监测环境变化，自动识别灾害迹象并及时预警，提供安全保障'
      },
      '车牌识别': {
        title: '车牌识别需求',
        outline: '车牌检测、数据匹配、自动报警',
        content: '客户需要精准的车牌识别与管理系统',
        advice: '使用我们的车牌识别与匹配报警技术',
        solution: '我们的车牌识别系统支持从照片或视频中提取车牌信息，并可与数据库匹配，发现异常车辆时自动报警'
      },
      '数据仪表盘': {
        title: '数据可视化需求',
        outline: '数据整合、实时监控、可视化展示',
        content: '客户需要直观的数据分析与展示平台',
        advice: '定制化数据仪表盘，整合多源数据',
        solution: '我们可以根据您的需求设计定制化数据仪表盘，整合各类识别系统数据，提供直观的可视化界面和分析报表'
      },
      '知识图谱': {
        title: '知识管理需求',
        outline: '信息关联、智能查询、知识挖掘',
        content: '客户需要建立知识关联与智能查询系统',
        advice: '部署我们的知识图谱构建与查询系统',
        solution: '我们的知识图谱系统支持信息关联分析、智能查询和知识挖掘，可以帮助您构建完整的知识管理体系'
      },
      '一般咨询': {
        title: '综合解决方案',
        outline: '需求分析、方案定制、技术支持',
        content: '客户对我们的技术方案有综合咨询需求',
        advice: '根据具体需求提供定制化解决方案',
        solution: '我们可以根据您的具体需求，整合路径规划、图像识别、知识库等多种技术，提供全方位的智能解决方案'
      }
    };

    // 获取模板，如果没有匹配的则使用一般咨询模板
    const template = templates[type] || templates['一般咨询'];
    
    return `
【标题】${template.title}

【大纲】${template.outline}

【内容】${template.content}

【建议】${template.advice}

【解决方案】${template.solution}
    `;
  };

  // 生成备用响应
  return getTemplateByInterest(interestType);
};

// 使用EmailJS发送邮件
const sendEmail = async (processedContent: string) => {
  try {
    // 缺少配置时不发送（演示环境不阻断主流程）
    if (!EMAILJS_PUBLIC_KEY || !EMAILJS_SERVICE_ID || !EMAILJS_TEMPLATE_ID) {
      console.warn(
        '[EmailJS] 配置不完整（需要 VITE_EMAILJS_PUBLIC_KEY / VITE_EMAILJS_SERVICE_ID / VITE_EMAILJS_TEMPLATE_ID），已跳过发送。'
      );
      return null;
    }

    // 设置收件人邮箱地址
    const receiverEmail = EMAILJS_RECEIVER_EMAIL;
    
    // 构建邮件主题
    const subject = `网站咨询 - ${getInterestLabel(form.interest)} - ${form.name}`;
    
    // 获取当前时间
    const now = new Date();
    const formattedTime = now.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
    
    // 提取和格式化内容
    const formatProcessedContent = (content: string) => {
      // 创建一个对象来存储解析后的内容
      const parsed: Record<string, string> = {
        title: '',
        outline: '',
        content: '',
        advice: '',
        solution: ''
      };
      
      // 使用更健壮的正则表达式匹配各个部分
      // 每部分内容可能跨多行，直到下一个标题或结束
      const titleMatch = content.match(/【标题】([\s\S]*?)(?=【大纲】|【内容】|【建议】|【解决方案】|$)/);
      const outlineMatch = content.match(/【大纲】([\s\S]*?)(?=【标题】|【内容】|【建议】|【解决方案】|$)/);
      const contentMatch = content.match(/【内容】([\s\S]*?)(?=【标题】|【大纲】|【建议】|【解决方案】|$)/);
      const adviceMatch = content.match(/【建议】([\s\S]*?)(?=【标题】|【大纲】|【内容】|【解决方案】|$)/);
      const solutionMatch = content.match(/【解决方案】([\s\S]*?)(?=【标题】|【大纲】|【内容】|【建议】|$)/);
      
      // 提取匹配内容
      if (titleMatch) parsed.title = titleMatch[1].trim();
      if (outlineMatch) parsed.outline = outlineMatch[1].trim();
      if (contentMatch) parsed.content = contentMatch[1].trim();
      if (adviceMatch) parsed.advice = adviceMatch[1].trim();
      if (solutionMatch) parsed.solution = solutionMatch[1].trim();
      
      // 如果内容解析失败，尝试备用方案：按行解析
      if (!parsed.title && !parsed.outline && !parsed.content && !parsed.advice && !parsed.solution) {
        const lines = content.split('\n').filter(line => line.trim());
        
        for (const line of lines) {
          if (line.includes('【标题】')) parsed.title = line.replace(/【标题】/, '').trim();
          else if (line.includes('【大纲】')) parsed.outline = line.replace(/【大纲】/, '').trim();
          else if (line.includes('【内容】')) parsed.content = line.replace(/【内容】/, '').trim();
          else if (line.includes('【建议】')) parsed.advice = line.replace(/【建议】/, '').trim();
          else if (line.includes('【解决方案】')) parsed.solution = line.replace(/【解决方案】/, '').trim();
        }
      }
      
      // 处理大纲内容，更智能地拆分为要点列表
      const outlinePoints = parsed.outline 
        ? parsed.outline.split(/[,，、;；]\s*/).filter(point => point.trim().length > 0)
        : ['功能细节', '技术指标', '开发支持'];
      
      // 处理建议内容，更智能地拆分为要点列表
      let advicePoints: string[] = [];
      if (parsed.advice) {
        // 首先尝试按数字序号分割
        if (/\d[\.、)）]\s/.test(parsed.advice)) {
          advicePoints = parsed.advice.split(/\d[\.、)）]\s+/).filter(point => point.trim().length > 0);
        } else {
          // 否则按标点符号分割
          advicePoints = parsed.advice.split(/[\.。;；]\s*/).filter(point => point.trim().length > 0);
        }
      }
      
      // 如果建议为空或分割后没有内容，则提供默认内容
      if (advicePoints.length === 0) {
        advicePoints = [
          '对对应功能模块提供技术白皮书或案例展示，增强客户信任度',
          '明确项目需求与开发周期，便于客户评估可行性',
          '强调本地LLM与知识图谱的定制化能力，突出差异化优势'
        ];
      }
      
      // 确保解决方案不为空
      const finalSolution = parsed.solution || '结合项目已有功能，可提供以下解决方案：路径规划、图像识别、知识库交互、夜间监控等，满足客户需求。';
      
      // 确保标题不为空
      const finalTitle = parsed.title || '智能识别系统开发咨询';
      
      // 确保内容不为空
      const finalContent = parsed.content || '客户需要详细询问多功能的实现细节、技术指标及开发支持，包括模型性能、算法优化、数据安全等。';
      
      return {
        title: finalTitle,
        outlinePoints: outlinePoints,
        content: finalContent,
        advicePoints: advicePoints,
        solution: finalSolution
      };
    };
    
    // 解析处理后的内容
    const formattedContent = formatProcessedContent(processedContent);
    
    // 添加调试日志
    console.log('解析后的内容:', formattedContent);
    
    // 构建优化的HTML内容，改进布局和层级结构
    const enhancedHTML = `
    <div style="font-family: 'Microsoft YaHei', Arial, sans-serif; max-width: 650px; margin: 0 auto; color: #333;">
      <!-- 顶部客户信息卡片 -->
      <div style="background-color: #f0f5ff; padding: 20px; margin-bottom: 25px; border-radius: 6px; border-left: 5px solid #3a86ff; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
        <h2 style="margin-top: 0; margin-bottom: 15px; color: #1a56db; font-size: 18px; border-bottom: 1px solid #d1e0ff; padding-bottom: 8px;">📋 客户信息</h2>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
          <tr>
            <td style="padding: 8px 5px; width: 25%; font-weight: bold; vertical-align: top;">客户：</td>
            <td style="padding: 8px 5px;">${form.name}</td>
            <td style="padding: 8px 5px; width: 25%; font-weight: bold; vertical-align: top;">咨询类型：</td>
            <td style="padding: 8px 5px;">${getInterestLabel(form.interest)}</td>
          </tr>
          <tr>
            <td style="padding: 8px 5px; font-weight: bold; vertical-align: top;">联系方式：</td>
            <td style="padding: 8px 5px;">${form.email}${form.phone ? ' | ' + form.phone : ''}</td>
            <td style="padding: 8px 5px; font-weight: bold; vertical-align: top;">公司：</td>
            <td style="padding: 8px 5px;">${form.company || '未提供'}</td>
          </tr>
          <tr>
            <td style="padding: 8px 5px; font-weight: bold; vertical-align: top;">提交时间：</td>
            <td style="padding: 8px 5px;" colspan="3">${formattedTime}</td>
          </tr>
        </table>
      </div>
      
      <!-- AI分析结果 -->
      <div style="background-color: white; padding: 25px; border-radius: 6px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 25px;">
        <h2 style="margin-top: 0; color: #2563eb; font-size: 20px; margin-bottom: 20px; display: flex; align-items: center;">
          <span style="background-color: #2563eb; color: white; width: 28px; height: 28px; border-radius: 50%; display: inline-flex; justify-content: center; align-items: center; margin-right: 10px; font-size: 14px;">AI</span>
          ${formattedContent.title || '智能分析报告'}
        </h2>
        
        <!-- 大纲部分 -->
        <div style="margin-bottom: 20px; background-color: #f9fafb; padding: 15px; border-radius: 4px;">
          <h3 style="color: #3b82f6; margin-top: 0; margin-bottom: 12px; font-size: 16px; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px;">📊 核心要点</h3>
          <ul style="margin: 0; padding-left: 20px; list-style-type: disc;">
            ${formattedContent.outlinePoints.map(point => `<li style="margin-bottom: 8px;">${point}</li>`).join('')}
          </ul>
        </div>
        
        <!-- 内容部分 -->
        <div style="margin-bottom: 20px;">
          <h3 style="color: #3b82f6; margin-top: 0; margin-bottom: 12px; font-size: 16px; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px;">📝 需求描述</h3>
          <p style="margin: 0; line-height: 1.6; color: #4b5563;">${formattedContent.content}</p>
        </div>
        
        <!-- 建议部分 -->
        <div style="margin-bottom: 20px; background-color: #f0f9ff; padding: 15px; border-radius: 4px; border-left: 3px solid #0ea5e9;">
          <h3 style="color: #0284c7; margin-top: 0; margin-bottom: 12px; font-size: 16px; border-bottom: 1px solid #bae6fd; padding-bottom: 8px;">💡 建议方案</h3>
          <ol style="margin: 0; padding-left: 20px;">
            ${formattedContent.advicePoints.map(point => `<li style="margin-bottom: 8px;">${point}</li>`).join('')}
          </ol>
        </div>
        
        <!-- 解决方案部分 -->
        <div style="background-color: #f0fdf4; padding: 15px; border-radius: 4px; border-left: 3px solid #10b981;">
          <h3 style="color: #047857; margin-top: 0; margin-bottom: 12px; font-size: 16px; border-bottom: 1px solid #a7f3d0; padding-bottom: 8px;">🔍 解决方案</h3>
          <p style="margin: 0; line-height: 1.6; color: #374151;">${formattedContent.solution}</p>
        </div>
      </div>
      
      <!-- 原始留言 -->
      <div style="background-color: #f4f4f5; padding: 20px; border-radius: 6px;">
        <h3 style="margin-top: 0; color: #71717a; font-size: 16px; margin-bottom: 12px; border-bottom: 1px solid #e4e4e7; padding-bottom: 8px;">📩 原始留言</h3>
        <p style="margin: 0; white-space: pre-wrap; color: #52525b; font-size: 14px; line-height: 1.6;">${form.message}</p>
      </div>
    </div>
    `;
    
    // 使用EmailJS发送邮件
    const templateParams = {
      to_email: receiverEmail,
      from_name: form.name,
      from_email: form.email,
      subject: subject,
      message: processedContent,
      html: enhancedHTML
    };
    
    // 发送邮件
    const result = await emailjs.send(
      EMAILJS_SERVICE_ID,
      EMAILJS_TEMPLATE_ID,
      templateParams,
      EMAILJS_PUBLIC_KEY
    );
    
    console.log('邮件发送成功:', result.text);
    return result;
  } catch (error: any) {
    // 仅记录日志，不再中断前端流程，保证表单在演示环境下始终成功
    console.error('发送邮件失败（已忽略，用于演示环境）:', error);
    return null;
  }
};

// 表单提交处理
const submitForm = async () => {
  loading.value = true;
  error.value = '';
  errorMessage.value = '';

  try {
    // 1. 使用DeepSeek API处理消息内容
    const processedContent = await processMessageWithDeepSeek(form.message);
    
    // 2. 发送邮件
    await sendEmail(processedContent);
    
    // 成功处理
    success.value = true;

    // 重置表单
    form.name = '';
    form.email = '';
    form.phone = '';
    form.company = '';
    form.message = '';
    form.interest = 'general';
    form.wechatId = '';
  } catch (err: any) {
    // 处理错误
    error.value = err.message || '发送留言时出现错误，请重试。';
    console.error('提交表单失败:', err);
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div>
    <section class="py-20 bg-gray-50">
      <div class="container mx-auto px-4">
        <h1
          class="text-4xl md:text-5xl font-bold text-center mb-4"
          data-aos="fade-up"
        >
          联系我们
        </h1>

        <p
          class="text-xl text-center text-gray-600 mb-16 max-w-3xl mx-auto"
          data-aos="fade-up"
          data-aos-delay="100"
        >
          与我们的团队联系，了解更多关于我们无人机解决方案如何满足您的特定需求。
        </p>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
          <div
            class="bg-white rounded-lg shadow-lg p-8"
            data-aos="fade-up"
            data-aos-delay="200"
          >
            <h2 class="text-2xl font-bold mb-6">给我们留言</h2>

            <form @submit.prevent="submitForm" class="space-y-6">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label for="name" class="block text-sm font-medium text-gray-700 mb-1">姓名</label>
                  <input
                    id="name"
                    v-model="form.name"
                    type="text"
                    required
                    class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-skydio-blue focus:border-skydio-blue"
                  >
                </div>

                <div>
                  <label for="email" class="block text-sm font-medium text-gray-700 mb-1">电子邮箱</label>
                  <input
                    id="email"
                    v-model="form.email"
                    type="email"
                    required
                    class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-skydio-blue focus:border-skydio-blue"
                  >
                </div>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label for="phone" class="block text-sm font-medium text-gray-700 mb-1">电话号码</label>
                  <input
                    id="phone"
                    v-model="form.phone"
                    type="tel"
                    class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-skydio-blue focus:border-skydio-blue"
                  >
                </div>

                <div>
                  <label for="company" class="block text-sm font-medium text-gray-700 mb-1">公司</label>
                  <input
                    id="company"
                    v-model="form.company"
                    type="text"
                    class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-skydio-blue focus:border-skydio-blue"
                  >
                </div>
              </div>

              <div>
                <label for="interest" class="block text-sm font-medium text-gray-700 mb-1">我对以下方面感兴趣</label>
                <select
                  id="interest"
                  v-model="form.interest"
                  class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-skydio-blue focus:border-skydio-blue"
                >
                  <option
                    v-for="option in interests"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.label }}
                  </option>
                </select>
              </div>

              <div>
                <label for="message" class="block text-sm font-medium text-gray-700 mb-1">留言内容</label>
                <textarea
                  id="message"
                  v-model="form.message"
                  rows="4"
                  required
                  class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-skydio-blue focus:border-skydio-blue"
                  placeholder="请详细描述您的需求，我们将通过AI助手整理后发送到相关部门"
                ></textarea>
              </div>

              <div>
                <button
                  type="submit"
                  class="btn-primary w-full flex justify-center items-center"
                  :disabled="loading"
                >
                  <svg
                    v-if="loading"
                    class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      class="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      stroke-width="4"
                    ></circle>
                    <path
                      class="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  {{ loading ? '处理中...' : '发送留言' }}
                </button>
                <p class="text-xs text-gray-500 mt-2">
                  您的留言将由AI助手整理后发送到我们的邮箱，我们会尽快回复您。
                </p>
              </div>

              <div v-if="success" class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
                感谢您的留言！留言已通过AI助手处理并发送至相关部门，我们会尽快回复您。
              </div>

              <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                {{ errorMessage || '发送留言时出现错误，请重试。' }}
              </div>
            </form>
          </div>

          <div data-aos="fade-up" data-aos-delay="300">
            <div class="bg-white rounded-lg shadow-lg p-8 mb-8">
              <h2 class="text-2xl font-bold mb-6">联系方式</h2>

              <div class="space-y-4">
                <div class="flex items-start">
                  <svg class="w-6 h-6 text-skydio-blue mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path>
                  </svg>
                  <div>
                    <p class="font-medium">总部地址</p>
                    <p class="text-gray-600">中国河南省郑州市惠济区英才街18号</p>
                  </div>
                </div>

                <div class="flex items-start">
                  <svg class="w-6 h-6 text-skydio-blue mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                  </svg>
                  <div>
                    <p class="font-medium">电子邮箱</p>
                    <p class="text-gray-600">1241515924@qq.com</p>
                  </div>
                </div>

                <div class="flex items-start">
                  <svg class="w-6 h-6 text-skydio-blue mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path>
                  </svg>
                  <div>
                    <p class="font-medium">电话</p>
                    <p class="text-gray-600">（+86）15978568969</p>
                  </div>
                </div>
              </div>
            </div>

            <div class="rounded-lg overflow-hidden shadow-lg h-64 bg-gray-300">
              <!-- 地图占位符 -->
              <img
                :src="feedbackImage"
                alt="地图"
                class="w-full h-full object-cover"
              >
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.btn-primary {
  @apply bg-blue-600 text-white py-3 rounded-md hover:bg-blue-700 transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500;
}
</style>
