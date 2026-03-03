<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { ElMessage, ElDialog, ElSelect, ElOption } from 'element-plus';
import { UserFilled, Service } from '@element-plus/icons-vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import * as d3 from 'd3';
import { knowledgeChatApi } from '../api/knowledgeChat';
import { useRoutePlanningStore } from '../stores/routePlanning';
import { useAnalysisHistoryStore } from '../stores/analysisHistory';
import { request } from '../api/request'; // 添加request导入

// 状态管理
const userInput = ref('');
const chatHistory = ref([
  {
    role: 'assistant',
    content: '你好！我是知识库智能助手。我可以帮你查询关于旅行、图像识别等信息，还可以联网搜索最新资料。请问有什么我可以帮助你的？'
  }
]);
const isLoading = ref(false);
const isStreaming = ref(false);
const streamingContent = ref('');
const chatMessagesContainer = ref(null);
const graphContainer = ref(null);
const webSearchEnabled = ref(false);
const knowledgeGraphSearchEnabled = ref(false);
const localModelSearchEnabled = ref(false);

// 路线规划和图片识别记录
const routePlanningStore = useRoutePlanningStore();
const analysisHistoryStore = useAnalysisHistoryStore();
const routeHistory = ref([]);
const analysisHistory = ref([]);
const selectedRouteId = ref('');
const selectedAnalysisId = ref('');
const selectRecordsDialogVisible = ref(false);

// 知识图谱数据
const knowledgeGraphData = ref({
  nodes: [
    { id: "智能规划", label: "智能规划", group: 1 },
    { id: "图像识别", label: "图像识别", group: 2 },
    { id: "知识库", label: "知识库", group: 3 },
    { id: "北京", label: "北京", group: 4 },
    { id: "上海", label: "上海", group: 4 },
    { id: "人物", label: "人物", group: 5 }
  ],
  links: [
    { source: "智能规划", target: "北京", value: 1 },
    { source: "智能规划", target: "上海", value: 1 },
    { source: "图像识别", target: "人物", value: 1 },
    { source: "知识库", target: "智能规划", value: 1 },
    { source: "知识库", target: "图像识别", value: 1 }
  ]
});

// 搜索结果
const searchResults = ref([]);
const localModelResults = ref([]);
const knowledgeGraphResults = ref([]);

// 添加布局管理
const layoutMode = ref('split'); // 'split', 'chat', 'graph'

// 切换布局函数
const switchLayout = (mode) => {
  layoutMode.value = mode;
  // 延迟重新初始化图谱，避免切换布局时图谱尺寸错误
  if (mode === 'split' || mode === 'graph') {
    setTimeout(() => {
      initKnowledgeGraph();
    }, 100);
  }
};

// 格式化 Markdown
const formatMarkdown = (text) => {
  if (!text) return '';
  
  // 先检查是否为JSON字符串
  if (typeof text === 'string' && text.trim().startsWith('{') && text.trim().endsWith('}')) {
    try {
      const jsonObj = JSON.parse(text);
      // 如果是JSON对象，并且有content字段，使用content渲染
      if (jsonObj.content) {
        // 设置marked选项
        marked.setOptions({
          breaks: true,
          gfm: true,
          headerIds: true,
          sanitize: false
        });
        return DOMPurify.sanitize(marked.parse(jsonObj.content));
      }
    } catch (e) {
      console.log('非有效JSON，作为普通文本处理');
    }
  }
  
  // 设置marked选项
  marked.setOptions({
    breaks: true,
    gfm: true,
    headerIds: true,
    sanitize: false
  });
  
  return DOMPurify.sanitize(marked.parse(text));
};

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || isLoading.value) return;
  
  const message = userInput.value.trim();
  userInput.value = '';
  
  // 添加用户消息到聊天历史
  chatHistory.value.push({
    role: 'user',
    content: message
  });
  
  // 滚动到底部
  await nextTick();
  if (chatMessagesContainer.value) {
    chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
  }
  
  try {
    // 设置加载状态
    isLoading.value = true;
    isStreaming.value = true;
    streamingContent.value = '';
    
    // 添加临时的AI回复占位
    const tempReplyIndex = chatHistory.value.length;
    chatHistory.value.push({
      role: 'assistant',
      content: '',
      isStreaming: true,
      sources: [],
      graphNodes: []
    });
    
    // 发送请求，传递三种搜索方式的开关状态
    const response = await knowledgeChatApi.sendMessage(
      message, 
      webSearchEnabled.value,
      knowledgeGraphSearchEnabled.value,
      localModelSearchEnabled.value
    );
    
    if (!response.ok) throw new Error('网络请求失败');
    
    // 清空搜索结果
    searchResults.value = [];
    localModelResults.value = [];
    knowledgeGraphResults.value = [];
    
    // 创建TextDecoder解码UTF-8文本
    const decoder = new TextDecoder();
    const reader = response.body.getReader();
    let accumulatedContent = '';
    let sourceData = null;
    
    // 使用新的流式处理逻辑 - 处理SSE格式
    const processStream = async () => {
      try {
        let buffer = '';
        let rawResponse = '';
    
    while (true) {
          const { done, value } = await reader.read();
      if (done) break;
      
          // 解码块并添加到完整响应
      const chunk = decoder.decode(value, { stream: true });
          rawResponse += chunk;
          
          // 用于前端展示的内容 - 直接累积到界面上
          if (chunk.trim()) {
            try {
              // 检查是否为SSE格式
              if (chunk.startsWith('data:')) {
                const dataContent = chunk.substring(5).trim();
                
                // 检查是否为结束标记
                if (dataContent === '[DONE]') {
                  console.log('流传输结束');
                  continue;
                }
                
                // 尝试解析为JSON
                try {
                  const jsonData = JSON.parse(dataContent);
                  if (jsonData && jsonData.content) {
                    accumulatedContent += jsonData.content;
                    streamingContent.value = accumulatedContent;
                    chatHistory.value[tempReplyIndex].content = accumulatedContent;
                    
                    // 如果包含sources信息，直接更新
          if (jsonData.sources && Array.isArray(jsonData.sources)) {
                      chatHistory.value[tempReplyIndex].sources = jsonData.sources;
                      searchResults.value = jsonData.sources;
                    }
                  }
                } catch (jsonError) {
                  console.log('数据不是有效JSON，作为纯文本处理', dataContent);
                  // 如果不是有效JSON，作为纯文本处理
                  accumulatedContent += dataContent;
                  streamingContent.value = accumulatedContent;
                  chatHistory.value[tempReplyIndex].content = accumulatedContent;
                }
              } else {
                // 不是SSE格式，可能是纯文本
                accumulatedContent += chunk;
                streamingContent.value = accumulatedContent;
                chatHistory.value[tempReplyIndex].content = accumulatedContent;
        }
      } catch (e) {
              console.error('处理块数据失败:', e);
              // 作为纯文本添加
              accumulatedContent += chunk;
              streamingContent.value = accumulatedContent;
              chatHistory.value[tempReplyIndex].content = accumulatedContent;
            }
            
            // 滚动到底部
            if (chatMessagesContainer.value) {
              chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
            }
          }
        }
        
        console.log('流结束，完整响应:', rawResponse);
        
        // 处理完整响应，提取元数据
        try {
          // 分析rawResponse找出所有data:行
          const dataLines = rawResponse.split('\n')
            .filter(line => line.startsWith('data:'))
            .map(line => line.substring(5).trim())
            .filter(line => line && line !== '[DONE]');
          
          // 尝试从最后一个完整的JSON响应中提取有用信息
          if (dataLines.length > 0) {
            let metadataFound = false;
            
            // 从后向前遍历，查找包含sources的响应
            for (let i = dataLines.length - 1; i >= 0; i--) {
              try {
                const jsonData = JSON.parse(dataLines[i]);
                
                // 如果包含sources信息
                if (jsonData.sources && Array.isArray(jsonData.sources)) {
                  console.log('找到参考资料:', jsonData.sources);
                  chatHistory.value[tempReplyIndex].sources = jsonData.sources;
                  searchResults.value = jsonData.sources;
                  metadataFound = true;
                  break;
                }
              } catch (e) {
                continue; // 继续检查下一行
              }
            }
            
            // 如果没找到metadata，尝试通过API获取
            if (!metadataFound) {
              console.log('未在流中找到参考资料，尝试通过API获取');
            }
          }
        } catch (e) {
          console.error('处理完整响应元数据失败:', e);
        }
        
        // 最后再尝试通过API获取最新的资料
        if (webSearchEnabled.value) {
          try {
            console.log('尝试通过API获取搜索结果');
            const searchData = await knowledgeChatApi.getLatestResults(message);
        if (searchData && searchData.results && searchData.results.length > 0) {
              console.log('通过API获取到参考资料:', searchData.results);
              chatHistory.value[tempReplyIndex].sources = searchData.results;
          searchResults.value = searchData.results;
            }
          } catch (searchError) {
            console.error('获取搜索结果失败:', searchError);
          }
        }
        
        // 获取知识图谱查询结果
        if (knowledgeGraphSearchEnabled.value) {
          try {
            console.log('尝试通过API获取知识图谱结果');
            const graphData = await knowledgeChatApi.getLatestGraphResults(message);
            if (graphData && graphData.results && graphData.results.length > 0) {
              console.log('通过API获取到知识图谱节点:', graphData.results);
              chatHistory.value[tempReplyIndex].graphNodes = graphData.results;
              knowledgeGraphResults.value = graphData.results;
              
              // 高亮知识图谱中对应的节点
              if (graphData.results[0].id) {
                highlightNode(graphData.results[0].id);
              }
            }
          } catch (graphError) {
            console.error('获取知识图谱查询结果失败:', graphError);
          }
        }
      } catch (e) {
        console.error('处理流失败:', e);
        throw e;
      }
    };
    
    // 开始处理流
    await processStream();
    
    // 获取搜索结果和本地模型结果
    let sources = sourceData ? [...sourceData] : [];
    
    // 获取搜索结果(如果前面没有获取到)
    if (webSearchEnabled.value && !sourceData) {
      try {
        const searchData = await knowledgeChatApi.getLatestResults(message);
        if (searchData && searchData.results && searchData.results.length > 0) {
          searchResults.value = searchData.results;
          sources = [...sources, ...searchData.results.map(r => ({...r, type: 'web'}))];
        }
      } catch (searchError) {
        console.error('获取搜索结果失败:', searchError);
      }
    }
    
    // 获取知识图谱查询结果
    let graphNodes = [];
    if (knowledgeGraphSearchEnabled.value) {
      try {
        const graphData = await knowledgeChatApi.getLatestGraphResults(message);
        if (graphData && graphData.results && graphData.results.length > 0) {
          knowledgeGraphResults.value = graphData.results;
          graphNodes = graphData.results;
          
          // 高亮知识图谱中对应的节点
          if (graphData.results[0].id) {
            highlightNode(graphData.results[0].id);
          }
        }
      } catch (graphError) {
        console.error('获取知识图谱查询结果失败:', graphError);
      }
    }
    
    // 获取本地模型搜索结果
    if (localModelSearchEnabled.value) {
      try {
        const localModelData = await knowledgeChatApi.getLatestLocalModelResults(message);
        if (localModelData && localModelData.results) {
          localModelResults.value = localModelData.results;
          if (localModelData.results.sources) {
            sources = [...sources, ...localModelData.results.sources.map(r => ({...r, type: 'local'}))];
          }
        }
      } catch (localModelError) {
        console.error('获取本地模型搜索结果失败:', localModelError);
      }
    }
    
    // 更新消息中的引用源和知识图谱节点
    chatHistory.value[tempReplyIndex].sources = sources;
    chatHistory.value[tempReplyIndex].graphNodes = graphNodes;
    
    // 获取最新的知识图谱数据
    loadKnowledgeGraph();
    
    // 更新流式状态
    chatHistory.value[tempReplyIndex].isStreaming = false;
  } catch (error) {
    console.error('发送消息失败:', error);
    // 处理错误
    chatHistory.value.pop(); // 移除临时回复
    chatHistory.value.push({
      role: 'assistant',
      content: `抱歉，发生了错误：${error.message}`
    });
  } finally {
    isLoading.value = false;
    isStreaming.value = false;
  }
};

// 初始化知识图谱
const initKnowledgeGraph = () => {
  if (!graphContainer.value) return;
  
  const width = graphContainer.value.clientWidth;
  const height = graphContainer.value.clientHeight;
  
  // 清除已有的SVG
  d3.select(graphContainer.value).selectAll("*").remove();
  
  // 创建SVG
  const svg = d3.select(graphContainer.value)
    .append("svg")
    .attr("width", width)
    .attr("height", height);
  
  // 数据转换为D3格式
  // 深拷贝，以防修改原始数据
  const rawNodes = JSON.parse(JSON.stringify(knowledgeGraphData.value.nodes || []));
  const rawLinks = JSON.parse(JSON.stringify(knowledgeGraphData.value.links || []));
  
  // 处理节点数据
  // 将所有节点格式化为统一结构
  const nodes = [];
  const nodeMap = new Map();
  
  // 首先收集所有节点
  rawNodes.forEach(node => {
    // 为节点创建统一的数据结构
    const processedNode = {
      id: node.id || node.name || node.model,
      label: node.label || node.name || node.model,
      group: node.group || node.category || "default",
      data: {},
      type: node.category || "default",
      isCentral: node.is_central || false
    };
    
    // 收集节点的所有其他属性作为数据
    Object.keys(node).forEach(key => {
      if (!['id', 'label', 'group', 'category', 'is_central'].includes(key)) {
        processedNode.data[key] = node[key];
      }
    });
    
    nodes.push(processedNode);
    nodeMap.set(processedNode.id, processedNode);
  });
  
  // 处理连接线
  const links = [];
  rawLinks.forEach(link => {
    // 标准化连接线结构
    const processedLink = {
      source: link.source || "",
      target: link.target || "",
      label: link.relationship_type || link.label || "",
      value: link.value || 1
    };
  
    // 只添加两端节点都存在的连接
    if (nodeMap.has(processedLink.source) && nodeMap.has(processedLink.target)) {
      links.push(processedLink);
    }
  });
  
  // 添加缩放功能
  const zoom = d3.zoom()
    .scaleExtent([0.2, 5])
    .on("zoom", (event) => {
      graphGroup.attr("transform", event.transform);
    });
  
  svg.call(zoom);
  
  // 添加渐变背景
  svg.append("defs").append("linearGradient")
    .attr("id", "graph-gradient")
    .attr("gradientUnits", "userSpaceOnUse")
    .attr("x1", 0).attr("y1", 0)
    .attr("x2", width).attr("y2", height)
    .selectAll("stop")
    .data([
      {offset: "0%", color: "#1a2236"},
      {offset: "100%", color: "#2d3746"}
    ])
    .enter().append("stop")
    .attr("offset", d => d.offset)
    .attr("stop-color", d => d.color);
  
  svg.append("rect")
    .attr("width", width)
    .attr("height", height)
    .attr("fill", "url(#graph-gradient)");
  
  const graphGroup = svg.append("g");
  
  // 添加箭头定义
  graphGroup.append("defs").selectAll("marker")
    .data(["default", "highlight"])
    .enter().append("marker")
    .attr("id", d => `arrow-${d}`)
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", d => d === "highlight" ? 30 : 28) // 调整箭头位置
    .attr("refY", 0)
    .attr("markerWidth", d => d === "highlight" ? 10 : 8)
    .attr("markerHeight", d => d === "highlight" ? 10 : 8)
    .attr("orient", "auto")
    .append("path")
    .attr("fill", d => d === "highlight" ? "#4299e1" : "#88a0c3")
    .attr("d", "M0,-5L10,0L0,5");
  
  // 找到中央节点
  let centralNode = nodes.find(node => node.isCentral) || nodes[0];
  
  // 根据层级组织节点
  const nodesByLevel = {};
  const processedNodes = new Set();
  
  // 深度优先遍历，分配层级
  function assignLevels(nodeId, level = 0) {
    if (processedNodes.has(nodeId)) return;
    processedNodes.add(nodeId);
    
    if (!nodesByLevel[level]) nodesByLevel[level] = [];
    const node = nodeMap.get(nodeId);
    if (node) {
      nodesByLevel[level].push(node);
      
      // 查找所有直接连接的节点
      links.forEach(link => {
        if (link.source === nodeId) {
          assignLevels(link.target, level + 1);
        }
      });
    }
  }
  
  // 从中心节点开始分配层级
  assignLevels(centralNode.id);
  
  // 给未处理的节点分配层级 (可能是孤立节点或新添加节点)
  nodes.forEach(node => {
    if (!processedNodes.has(node.id)) {
      if (!nodesByLevel[1]) nodesByLevel[1] = [];
      nodesByLevel[1].push(node);
      processedNodes.add(node.id);
    }
  });
  
  // 转换后的节点数组
  const orderedNodes = Object.values(nodesByLevel).flat();
  
  // 处理连接线的源和目标，确保为对象引用
  const processedLinks = links.map(link => {
    const sourceNode = orderedNodes.find(node => node.id === link.source);
    const targetNode = orderedNodes.find(node => node.id === link.target);
    
    if (sourceNode && targetNode) {
      return {
        ...link,
        source: sourceNode,
        target: targetNode
      };
    }
    return null;
  }).filter(link => link !== null);
  
  // 创建力导向图
  const simulation = d3.forceSimulation(orderedNodes)
    .force("link", d3.forceLink(processedLinks)
      .id(d => d.id)
      .distance(link => {
        // 根据连接类型调整距离
        switch (link.label) {
          case "包含": return 100;
          case "生产": return 120;
          case "使用": return 150;
          case "采用": return 120;
          case "应用于": return 150;
          case "用于": return 130;
          case "相关": return 180;
          default: return 120;
        }
      }))
    .force("charge", d3.forceManyBody()
      .strength(d => d.isCentral ? -1000 : -500)) // 中央节点排斥力更强
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("x", d3.forceX().strength(0.1))
    .force("y", d3.forceY().strength(0.1))
    .force("collision", d3.forceCollide().radius(d => 
      d.isCentral ? 70 : (d.group === "分类" || d.group === "部件" || d.group === "技术" || d.group === "应用" ? 50 : 30)
    )); // 避免节点重叠
  
  // 获取组颜色
  function getGroupColor(group) {
    const colorMap = {
      "默认": "#5D8AA8",
      "分类": "#E6A91F",
      "部件": "#9370DB", 
      "技术": "#3CB371",
      "应用": "#FF6347",
      "品牌": "#6A5ACD",
      "消费级": "#20B2AA",
      "专业级": "#FF4500",
      "工业级": "#4682B4",
      "军用级": "#D2691E",
      "default": "#5D8AA8"
      };
    return colorMap[group] || colorMap.default;
  }
  
  // 绘制连接线
  const link = graphGroup.append("g")
    .selectAll("path")
    .data(processedLinks)
    .enter().append("path")
    .attr("class", "link")
    .attr("stroke", "#88a0c3")
    .attr("stroke-opacity", 0.6)
    .attr("stroke-width", d => Math.sqrt(d.value || 1) * 1.5)
    .attr("fill", "none")
    .attr("marker-end", "url(#arrow-default)");
  
  // 添加连接线文本
  const linkText = graphGroup.append("g")
    .selectAll("text")
    .data(processedLinks)
    .enter().append("text")
    .attr("class", "link-text")
    .attr("fill", "#b3ccf5")
    .attr("font-size", "10px")
    .attr("text-anchor", "middle")
    .attr("dy", -5)
    .text(d => d.label || "关联");
  
  // 创建节点组
  const node = graphGroup.append("g")
    .selectAll("g")
    .data(orderedNodes)
    .enter().append("g")
    .attr("class", "node")
    .call(d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended))
    .on("mouseover", function(event, d) {
      // 高亮当前节点
      d3.select(this).select("circle")
        .transition()
        .duration(200)
        .attr("r", d.isCentral ? 40 : 22)
        .attr("stroke-width", 3);
      
      // 放大文本
      d3.select(this).select("text")
        .transition()
        .duration(200)
        .attr("font-size", d.isCentral ? "16px" : "14px");
      
      // 高亮相关连接
      link.each(function(l) {
        if (l.source.id === d.id || l.target.id === d.id) {
          d3.select(this)
            .transition()
            .duration(200)
            .attr("stroke", "#4299e1")
            .attr("stroke-opacity", 1)
            .attr("stroke-width", Math.sqrt(l.value || 1) * 2.5)
            .attr("marker-end", "url(#arrow-highlight)");
          
          // 高亮相关节点
          node.each(function(n) {
            if (n.id === (l.source.id === d.id ? l.target.id : l.source.id)) {
              d3.select(this).select("circle")
                .transition()
                .duration(200)
                .attr("r", n.isCentral ? 35 : 18)
                .attr("stroke-width", 2);
            }
          });
        }
      });
      
      // 显示详细信息提示框
      if (d.data && Object.keys(d.data).length > 0) {
        const tooltip = d3.select(graphContainer.value)
          .append("div")
          .attr("class", "graph-tooltip")
          .style("position", "absolute")
          .style("background-color", "rgba(0, 0, 0, 0.8)")
          .style("color", "white")
          .style("padding", "10px")
          .style("border-radius", "5px")
          .style("box-shadow", "0 0 10px rgba(0, 0, 0, 0.5)")
          .style("pointer-events", "none")
          .style("z-index", "1000")
          .style("font-size", "12px")
          .style("left", (event.pageX + 10) + "px")
          .style("top", (event.pageY - 20) + "px");
          
        // 添加标题
        tooltip.append("div")
          .style("font-weight", "bold")
          .style("font-size", "14px")
          .style("margin-bottom", "5px")
          .text(d.label || d.id);
          
        // 添加数据内容
        const dataList = tooltip.append("ul")
          .style("margin", "0")
          .style("padding", "0 0 0 15px");
          
        Object.entries(d.data).forEach(([key, value]) => {
          // 过滤掉不需要显示的字段
          if (!['parts', 'description', 'data'].includes(key)) {
          dataList.append("li")
            .text(`${key}: ${value}`);
          }
        });
      }
    })
    .on("mouseout", function(event, d) {
      // 恢复正常状态
      d3.select(this).select("circle")
        .transition()
        .duration(200)
        .attr("r", d => d.isCentral ? 30 : (d.group === "分类" || d.group === "部件" || d.group === "技术" || d.group === "应用" ? 20 : 15))
        .attr("stroke-width", 2);
      
      // 恢复文本大小
      d3.select(this).select("text")
        .transition()
        .duration(200)
        .attr("font-size", d => d.isCentral ? "14px" : "12px");
      
      // 恢复连接线状态
      link.transition()
        .duration(200)
        .attr("stroke", "#88a0c3")
        .attr("stroke-opacity", 0.6)
        .attr("stroke-width", l => Math.sqrt(l.value || 1) * 1.5)
        .attr("marker-end", "url(#arrow-default)");
      
      // 恢复所有节点状态
      node.select("circle")
        .transition()
        .duration(200)
        .attr("r", d => d.isCentral ? 30 : (d.group === "分类" || d.group === "部件" || d.group === "技术" || d.group === "应用" ? 20 : 15))
        .attr("stroke-width", 2);
      
      // 移除提示框
      d3.select(graphContainer.value).selectAll(".graph-tooltip").remove();
    });
  
  // 为节点添加光晕效果
  const filters = svg.append("defs").append("filter")
    .attr("id", "glow")
    .attr("x", "-50%")
    .attr("y", "-50%")
    .attr("width", "200%")
    .attr("height", "200%");
  
  filters.append("feGaussianBlur")
    .attr("stdDeviation", "2.5")
    .attr("result", "coloredBlur");
  
  const feMerge = filters.append("feMerge");
  feMerge.append("feMergeNode").attr("in", "coloredBlur");
  feMerge.append("feMergeNode").attr("in", "SourceGraphic");
  
  // 添加节点圆圈
  node.append("circle")
    .attr("r", d => d.isCentral ? 30 : (d.group === "分类" || d.group === "部件" || d.group === "技术" || d.group === "应用" ? 20 : 15))
    .attr("fill", d => getGroupColor(d.group))
    .attr("stroke", "#fff")
    .attr("stroke-width", 2)
    .attr("filter", "url(#glow)");
  
  // 添加节点标签
  node.append("text")
    .attr("dx", d => d.isCentral ? 0 : 20)
    .attr("dy", d => d.isCentral ? 45 : ".35em")
    .attr("text-anchor", d => d.isCentral ? "middle" : "start")
    .text(d => d.label || d.id)
    .attr("fill", "#fff")
    .attr("font-family", "Arial, sans-serif")
    .attr("font-size", d => d.isCentral ? "14px" : "12px")
    .attr("font-weight", d => d.isCentral ? "bold" : "normal")
    .attr("text-shadow", "0 1px 3px rgba(0,0,0,0.7)");
  
  // 添加节点悬停效果
  node.append("title")
    .text(d => {
      if (d.data && Object.keys(d.data).length > 0) {
        return Object.entries(d.data)
          .filter(([key]) => !['parts', 'description', 'data'].includes(key))
          .map(([key, value]) => `${key}: ${value}`)
          .join('\n');
      }
      return d.label || d.id;
    });
  
  // 更新位置
  simulation.on("tick", () => {
    // 更新连接线路径 - 使用曲线连接
    link.attr("d", d => {
      const dx = d.target.x - d.source.x,
            dy = d.target.y - d.source.y,
            dr = Math.sqrt(dx * dx + dy * dy) * 1.2;
      return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
    });
    
    // 更新连接线文本位置
    linkText.attr("transform", d => {
      const x = (d.source.x + d.target.x) / 2;
      const y = (d.source.y + d.target.y) / 2;
      return `translate(${x},${y})`;
    });
    
    // 更新节点位置
    node.attr("transform", d => {
      // 确保节点不超出边界
      d.x = Math.max(30, Math.min(width - 30, d.x));
      d.y = Math.max(30, Math.min(height - 30, d.y));
      return `translate(${d.x},${d.y})`;
    });
  });
  
  // 拖拽函数
  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }
  
  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }
  
  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
  
  // 初始布局优化
  // 在前100次迭代中调整力度，使布局更好看
  let i = 0;
  simulation.on("tick.custom", () => {
    i++;
    if (i >= 100) {
      simulation.on("tick.custom", null);
    }
  });
};

// 加载知识图谱数据
const loadKnowledgeGraph = async () => {
  try {
    const response = await knowledgeChatApi.getKnowledgeGraph();
    if (response && response.nodes && response.links) {
      knowledgeGraphData.value = response;
      initKnowledgeGraph();
    } else {
      // 使用后端提供的无人机知识图谱数据
      try {
        // 加载本地数据
        const localResponse = await fetch('/static/night_detection/models/drones_knowledge_graph.json');
        if (localResponse.ok) {
          const data = await localResponse.json();
          
          // 转换数据格式为前端展示需要的格式
          const nodes = [];
          
          // 处理无人机数据
          if (data.drones) {
            data.drones.forEach(drone => {
              nodes.push({
                id: drone.model,
                label: drone.model,
                group: drone.category || "1",
                is_central: drone.is_central || false,
                data: drone
              });
            });
          }
          
          // 处理品牌数据
          if (data.brands) {
            data.brands.forEach(brand => {
              nodes.push({
                id: brand.name,
                label: brand.name,
                group: brand.category || "2",
                data: brand
              });
            });
          }
          
          // 处理分类数据
          if (data.categories) {
            data.categories.forEach(category => {
              nodes.push({
                id: category.name,
                label: category.name,
                group: category.category || "3",
                data: category
              });
            });
          }
          
          // 处理部件数据
          if (data.components) {
            data.components.forEach(component => {
              nodes.push({
                id: component.name,
                label: component.name,
                group: component.category || "4",
                data: component
              });
            });
          }
          
          // 处理技术数据
          if (data.technologies) {
            data.technologies.forEach(tech => {
              nodes.push({
                id: tech.name,
                label: tech.name,
                group: tech.category || "5",
                data: tech
              });
            });
          }
          
          // 处理应用数据
          if (data.applications) {
            data.applications.forEach(app => {
              nodes.push({
                id: app.name,
                label: app.name,
                group: app.category || "6",
                data: app
              });
            });
          }
          
          // 转换关系数据
          const links = data.relationships ? data.relationships.map(rel => ({
            source: rel.source,
            target: rel.target,
            label: rel.relationship_type,
            value: 1.5
          })) : [];
          
          knowledgeGraphData.value = { nodes, links };
          initKnowledgeGraph();
        } else {
          throw new Error("本地数据加载失败");
        }
      } catch (localError) {
        console.error('加载本地知识图谱数据失败:', localError);
        // 失败时使用示例数据
        initKnowledgeGraph();
      }
    }
  } catch (error) {
    console.error('获取知识图谱失败:', error);
    // 失败时使用示例数据
    initKnowledgeGraph();
  }
};

// 加载历史记录
const loadHistoryRecords = async () => {
  try {
    // 加载路线规划历史
    await routePlanningStore.getHistory();
    routeHistory.value = routePlanningStore.history;
    
    // 图片识别历史直接从store中获取
    analysisHistory.value = analysisHistoryStore.analysisHistory;
  } catch (error) {
    console.error('加载历史记录失败:', error);
    ElMessage.error('加载历史记录失败，请重试');
  }
};

// 显示选择记录对话框
const showSelectRecordsDialog = () => {
  loadHistoryRecords();
  selectRecordsDialogVisible.value = true;
};

// 生命周期钩子
onMounted(() => {
  // 初始化知识图谱
  loadKnowledgeGraph();
  
  // 初始化导入数据
  resetDroneImport();
  
  // 响应窗口大小变化
  window.addEventListener('resize', () => {
    initKnowledgeGraph();
  });
});

// 在组件卸载时清理
onUnmounted(() => {
  window.removeEventListener('resize', initKnowledgeGraph);
});

// 监听webSearchEnabled变化
watch(webSearchEnabled, (newVal) => {
  ElMessage.info(`联网搜索已${newVal ? '启用' : '禁用'}`);
});

// 监听knowledgeGraphSearchEnabled变化
watch(knowledgeGraphSearchEnabled, (newVal) => {
  ElMessage.info(`知识图谱检索已${newVal ? '启用' : '禁用'}`);
});

// 监听localModelSearchEnabled变化
watch(localModelSearchEnabled, (newVal) => {
  ElMessage.info(`本地模型检索已${newVal ? '启用' : '禁用'}`);
});

// 应用选择的记录到知识图谱
const applySelectedRecords = async () => {
  try {
    const selectedData = {
      routeId: selectedRouteId.value,
      analysisId: selectedAnalysisId.value
    };
    
    // 构建新的图谱数据
    let newGraphData = { nodes: [], links: [] };
    
    // 添加路线规划数据到图谱
    if (selectedRouteId.value) {
      const routeDetail = routeHistory.value.find(r => r.id === selectedRouteId.value);
      if (routeDetail) {
        // 添加路线节点
        newGraphData.nodes.push({
          id: `route_${routeDetail.id}`,
          label: `路线: ${routeDetail.title || '未命名路线'}`,
          group: 1,
          data: {
            type: 'Route',
            id: routeDetail.id,
            description: routeDetail.description || '无描述'
          }
        });
        
        // 添加目的地节点和连接
        if (routeDetail.destinations && routeDetail.destinations.length > 0) {
          routeDetail.destinations.forEach((dest, index) => {
            const destId = `dest_${routeDetail.id}_${index}`;
            newGraphData.nodes.push({
              id: destId,
              label: dest.name || `目的地 ${index + 1}`,
              group: 2,
              data: {
                type: 'Destination',
                description: dest.description || '无描述'
              }
            });
            
            // 添加连接
            newGraphData.links.push({
              source: `route_${routeDetail.id}`,
              target: destId,
              label: '包含',
              value: 1
            });
          });
        }
      }
    }
    
    // 添加图片分析数据到图谱
    if (selectedAnalysisId.value) {
      const analysisDetail = analysisHistoryStore.getAnalysisById(selectedAnalysisId.value);
      if (analysisDetail && analysisDetail.result) {
        // 添加图片分析节点
        newGraphData.nodes.push({
          id: `analysis_${analysisDetail.id}`,
          label: `图片分析: ${new Date(analysisDetail.timestamp).toLocaleString()}`,
          group: 3,
          data: {
            type: 'ImageAnalysis',
            id: analysisDetail.id,
            imageUrl: analysisDetail.imageUrl,
            timestamp: analysisDetail.timestamp
          }
        });
        
        // 添加检测到的人物节点和连接
        if (analysisDetail.result.persons && analysisDetail.result.persons.length > 0) {
          analysisDetail.result.persons.forEach((person, index) => {
            const personId = `person_${analysisDetail.id}_${index}`;
            newGraphData.nodes.push({
              id: personId,
              label: `人物 ${index + 1}`,
              group: 4,
              data: {
                type: 'Person',
                gender: person.gender,
                age: person.age,
                upperColor: person.upper_color,
                lowerColor: person.lower_color
              }
            });
            
            // 添加连接
            newGraphData.links.push({
              source: `analysis_${analysisDetail.id}`,
              target: personId,
              label: '检测到',
              value: 1
            });
          });
        }
      }
    }
    
    // 如果两种记录都选择了，创建它们之间的连接
    if (selectedRouteId.value && selectedAnalysisId.value) {
      newGraphData.links.push({
        source: `route_${selectedRouteId.value}`,
        target: `analysis_${selectedAnalysisId.value}`,
        label: '关联',
        value: 2
      });
    }
    
    // 合并新图谱数据和现有图谱数据
    const combinedNodes = [...knowledgeGraphData.value.nodes];
    const combinedLinks = [...knowledgeGraphData.value.links];
    
    // 添加新节点（避免重复）
    newGraphData.nodes.forEach(node => {
      if (!combinedNodes.find(n => n.id === node.id)) {
        combinedNodes.push(node);
      }
    });
    
    // 添加新连接（避免重复）
    newGraphData.links.forEach(link => {
      if (!combinedLinks.find(l => 
          l.source === link.source && 
          l.target === link.target && 
          l.label === link.label)) {
        combinedLinks.push(link);
      }
    });
    
    // 更新图谱数据
    knowledgeGraphData.value = {
      nodes: combinedNodes,
      links: combinedLinks
    };
    
    // 重新初始化图谱
    initKnowledgeGraph();
    
    selectRecordsDialogVisible.value = false;
    ElMessage.success('已将选定记录添加到知识图谱');
  } catch (error) {
    console.error('应用记录失败:', error);
    ElMessage.error('应用记录失败，请重试');
  }
};

// 清除选择
const clearSelection = () => {
  selectedRouteId.value = '';
  selectedAnalysisId.value = '';
  ElMessage.success('已清除选择');
};

// 重置图谱
const resetGraph = async () => {
  try {
    // 清空当前知识图谱数据
    knowledgeGraphData.value = {
      nodes: [
        { id: "智能规划", label: "智能规划", group: 1 },
        { id: "图像识别", label: "图像识别", group: 2 },
        { id: "知识库", label: "知识库", group: 3 },
        { id: "北京", label: "北京", group: 4 },
        { id: "上海", label: "上海", group: 4 },
        { id: "人物", label: "人物", group: 5 }
      ],
      links: [
        { source: "智能规划", target: "北京", value: 1 },
        { source: "智能规划", target: "上海", value: 1 },
        { source: "图像识别", target: "人物", value: 1 },
        { source: "知识库", target: "智能规划", value: 1 },
        { source: "知识库", target: "图像识别", value: 1 }
      ]
    };
    
    // 重新渲染图谱
    initKnowledgeGraph();
    
    // 清空聊天搜索结果
    searchResults.value = [];
    localModelResults.value = [];
    knowledgeGraphResults.value = [];
    
    // 清空选择
    clearSelection();
    
    ElMessage.success('已重置知识图谱');
  } catch (error) {
    console.error('重置图谱失败:', error);
    ElMessage.error('重置图谱失败，请重试');
  }
};

// 清除聊天历史
const clearChatHistory = () => {
  chatHistory.value = [{
    role: 'assistant',
    content: '你好！我是知识库智能助手。我可以帮你查询关于旅行、图像识别等信息，还可以联网搜索最新资料。请问有什么我可以帮助你的？'
  }];
  searchResults.value = [];
  localModelResults.value = [];
  knowledgeGraphResults.value = [];
  ElMessage.success('已清除聊天历史');
};

// 清除所有内容
const clearAll = () => {
  clearChatHistory();
  resetGraph();
  ElMessage.success('已清除所有内容');
};

// 显示导入无人机数据对话框
const showDroneImportDialog = () => {
  droneImportDialogVisible.value = true;
};

// 导入无人机数据对话框
const droneImportDialogVisible = ref(false);
const droneJsonInput = ref('');
const isDroneImporting = ref(false);
const localFileInput = ref(null);
const importTab = ref('text');

// 加载本地JSON文件
const handleFileChange = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  // 检查文件类型
  if (file.type !== 'application/json' && !file.name.endsWith('.json')) {
    ElMessage.warning('请选择JSON文件');
    return;
  }
  
  // 读取文件内容
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const content = e.target.result;
      // 验证JSON格式
      JSON.parse(content);
      droneJsonInput.value = content;
      ElMessage.success('文件加载成功');
    } catch (error) {
      ElMessage.error('无效的JSON文件');
      console.error('JSON解析错误:', error);
    }
  };
  reader.onerror = () => {
    ElMessage.error('文件读取失败');
  };
  reader.readAsText(file);
};

// 加载我们创建的示例文件
const loadCreatedExample = async () => {
  try {
    // 使用相对路径访问我们创建的JSON文件
    const response = await fetch('/static/night_detection/models/drones_knowledge_graph.json');
    if (!response.ok) {
      throw new Error(`HTTP错误! 状态: ${response.status}`);
    }
    const data = await response.text();
    droneJsonInput.value = data;
    ElMessage.success('已加载详细的无人机知识图谱示例');
  } catch (error) {
    console.error('加载示例文件失败:', error);
    ElMessage.error('加载示例文件失败');
  }
};

// 默认的示例数据
const defaultDroneJson = `{
  "drones": [
    {
      "model": "无人机技术",
      "brand": "中心节点",
      "is_central": true,
      "description": "无人机技术知识体系",
      "parts": []
    },
    {
      "model": "大疆经纬M300RTK",
      "brand": "DJI",
      "flight_time": "55分钟",
      "max_speed": "83 km/h",
      "max_flight_distance": "15 km",
      "takeoff_weight": "9kg",
      "category": "工业级",
      "parts": ["飞行控制系统", "电机系统", "电池系统", "相机云台", "视觉系统"]
    },
    {
      "model": "大疆精灵4Pro",
      "brand": "DJI",
      "flight_time": "30分钟",
      "max_speed": "72 km/h",
      "max_flight_distance": "7 km",
      "takeoff_weight": "1.4kg",
      "category": "消费级",
      "parts": ["飞行控制系统", "电机系统", "电池系统", "相机云台"]
    }
  ],
  "brands": [
    {
      "name": "DJI",
      "founded": "2006年",
      "headquarters": "深圳",
      "market_share": "70%以上",
      "category": "品牌"
    }
  ],
  "categories": [
    {"name": "无人机分类", "category": "分类"},
    {"name": "消费级", "category": "分类"},
    {"name": "工业级", "category": "分类"}
  ],
  "components": [
    {"name": "核心部件", "category": "部件"},
    {"name": "飞行控制系统", "category": "部件", "description": "控制飞行姿态和导航"},
    {"name": "电机系统", "category": "部件", "description": "提供升力和机动性"},
    {"name": "电池系统", "category": "部件", "description": "提供能源"},
    {"name": "相机云台", "category": "部件", "description": "稳定成像系统"},
    {"name": "视觉系统", "category": "部件", "description": "感知环境和避障"}
  ],
  "relationships": [
    {"source": "无人机技术", "target": "无人机分类", "relationship_type": "包含"},
    {"source": "无人机技术", "target": "核心部件", "relationship_type": "包含"},
    {"source": "无人机技术", "target": "DJI", "relationship_type": "相关"},
    
    {"source": "无人机分类", "target": "消费级", "relationship_type": "包含"},
    {"source": "无人机分类", "target": "工业级", "relationship_type": "包含"},
    
    {"source": "核心部件", "target": "飞行控制系统", "relationship_type": "包含"},
    {"source": "核心部件", "target": "电机系统", "relationship_type": "包含"},
    {"source": "核心部件", "target": "电池系统", "relationship_type": "包含"},
    {"source": "核心部件", "target": "相机云台", "relationship_type": "包含"},
    {"source": "核心部件", "target": "视觉系统", "relationship_type": "包含"},
    
    {"source": "消费级", "target": "大疆精灵4Pro", "relationship_type": "包含"},
    {"source": "工业级", "target": "大疆经纬M300RTK", "relationship_type": "包含"},
    
    {"source": "DJI", "target": "大疆经纬M300RTK", "relationship_type": "生产"},
    {"source": "DJI", "target": "大疆精灵4Pro", "relationship_type": "生产"},
    
    {"source": "大疆经纬M300RTK", "target": "飞行控制系统", "relationship_type": "包含"},
    {"source": "大疆经纬M300RTK", "target": "电机系统", "relationship_type": "包含"},
    {"source": "大疆经纬M300RTK", "target": "电池系统", "relationship_type": "包含"},
    {"source": "大疆经纬M300RTK", "target": "相机云台", "relationship_type": "包含"},
    {"source": "大疆经纬M300RTK", "target": "视觉系统", "relationship_type": "包含"}
  ]
}`;

// 重置导入框
const resetDroneImport = () => {
  droneJsonInput.value = defaultDroneJson;
};

// 使用示例数据
const useExampleData = () => {
  droneJsonInput.value = defaultDroneJson;
  ElMessage.success('已加载示例数据');
};

// 导入无人机数据
const importDroneData = async () => {
  if (!droneJsonInput.value.trim()) {
    ElMessage.warning('请输入无人机数据JSON');
    return;
  }
  
  try {
    // 解析JSON
    const droneData = JSON.parse(droneJsonInput.value);
    
    // 基本验证
    if (!droneData.drones || !Array.isArray(droneData.drones) || droneData.drones.length === 0) {
      ElMessage.warning('无人机数据格式无效：缺少drones数组或为空');
      return;
    }
    
    if (!droneData.brands || !Array.isArray(droneData.brands) || droneData.brands.length === 0) {
      ElMessage.warning('无人机数据格式无效：缺少brands数组或为空');
      return;
    }
    
    if (!droneData.relationships || !Array.isArray(droneData.relationships) || droneData.relationships.length === 0) {
      ElMessage.warning('无人机数据格式无效：缺少relationships数组或为空');
      return;
    }
    
    // 显示导入中
    isDroneImporting.value = true;
    
    // 调用API导入数据
    const response = await knowledgeChatApi.importDroneData(droneData);
    
    if (response && response.success) {
      ElMessage.success(`导入成功！创建了${response.stats.nodes_created}个节点和${response.stats.relationships_created}个关系`);
      
      // 如果返回了更新后的图谱，直接使用
      if (response.graph && response.graph.nodes && response.graph.links) {
        knowledgeGraphData.value = response.graph;
        initKnowledgeGraph();
      } else {
        // 否则重新加载图谱
        loadKnowledgeGraph();
      }
      
      // 关闭对话框
      droneImportDialogVisible.value = false;
    } else {
      ElMessage.error(`导入失败：${response.error || '未知错误'}`);
    }
  } catch (error) {
    console.error('导入无人机数据失败:', error);
    ElMessage.error(`导入失败：${error.message || '无法解析JSON数据'}`);
  } finally {
    isDroneImporting.value = false;
  }
};

// 高亮知识图谱中的节点
const highlightNode = (nodeId) => {
  if (!nodeId) return;
  
  // 找到图谱中对应的节点
  const node = knowledgeGraphData.value.nodes.find(n => n.id === nodeId);
  if (!node) {
    console.warn(`未找到节点: ${nodeId}`);
    return;
  }
  
  // 切换到拆分或图谱视图，确保图谱可见
  if (layoutMode.value === 'chat') {
    switchLayout('split');
  }
  
  // 高亮显示节点（通过添加CSS类或触发D3事件）
  const svg = d3.select(graphContainer.value).select('svg');
  const nodeElements = svg.selectAll('.node');
  
  // 重置所有节点样式
  nodeElements.classed('highlighted', false)
    .select('circle')
    .transition()
    .duration(200)
    .attr('r', d => d.id === nodeId ? 12 : 8)
    .style('stroke-width', d => d.id === nodeId ? 3 : 1.5);
  
  // 高亮目标节点
  nodeElements.filter(d => d.id === nodeId)
    .classed('highlighted', true)
    .select('circle')
    .transition()
    .duration(500)
    .attr('r', 15)
    .style('stroke', '#FF5722')
    .style('stroke-width', 3);
  
  // 显示通知
  ElMessage.success(`已高亮节点: ${node.label || nodeId}`);
};
</script>

<template>
  <div class="knowledge-chat-container">
    <!-- 标题栏 -->
    <div class="app-header">
      <div class="app-title">
        <span class="title-icon">🔍</span>
        <h1>智慧知库</h1>
        <div class="title-badge">知识图谱增强</div>
        </div>
      <div class="header-actions">
        <!-- 布局切换按钮 -->
        <div class="layout-switcher">
          <div 
            class="layout-button" 
            :class="{ active: layoutMode === 'split' }"
            @click="switchLayout('split')"
            title="分屏模式"
          >
            <i class="layout-icon split-icon"></i>
      </div>
          <div 
            class="layout-button" 
            :class="{ active: layoutMode === 'chat' }"
            @click="switchLayout('chat')"
            title="仅聊天"
          >
            <i class="layout-icon chat-icon"></i>
          </div>
          <div 
            class="layout-button" 
            :class="{ active: layoutMode === 'graph' }"
            @click="switchLayout('graph')"
            title="仅图谱"
          >
            <i class="layout-icon graph-icon"></i>
            </div>
            </div>
        <div class="web-search-toggle">
          <span>联网搜索</span>
          <el-switch v-model="webSearchEnabled" />
                </div>
        <div class="web-search-toggle">
          <span>知识图谱检索</span>
          <el-switch v-model="knowledgeGraphSearchEnabled" />
              </div>
        <div class="web-search-toggle">
          <span>本地模型检索</span>
          <el-switch v-model="localModelSearchEnabled" />
            </div>
        </div>
      </div>

    <!-- 搜索结果和聊天区域 -->
    <div class="main-content" :class="layoutMode">
      <!-- 聊天区域 -->
      <div class="chat-section">
      <div class="chat-messages" ref="chatMessagesContainer">
          <div v-for="(message, index) in chatHistory" :key="index" class="message" :class="message.role">
          <div class="message-avatar">
              <el-icon v-if="message.role === 'user'" class="avatar-icon">
                <UserFilled />
              </el-icon>
              <el-icon v-else class="avatar-icon assistant-icon">
                <Service />
              </el-icon>
          </div>
          <div class="message-content">
              <div v-if="message.role === 'assistant'" class="assistant-meta">
                <span class="assistant-name">知识库助手</span>
                <div class="assistant-tags">
                  <span v-if="webSearchEnabled" class="tag">联网搜索</span>
                  <span v-if="knowledgeGraphSearchEnabled" class="tag">知识图谱</span>
                  <span v-if="localModelSearchEnabled" class="tag">本地模型</span>
            </div>
            </div>
              <div v-if="message.isStreaming" class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div v-else class="markdown-content" v-html="formatMarkdown(message.content)"></div>
              
              <!-- 添加引用源显示 -->
            <div v-if="message.sources && message.sources.length > 0" class="sources-section">
                <div class="sources-title">参考资料</div>
                <div v-for="(source, sIdx) in message.sources" :key="sIdx" class="source-item">
                  <div class="source-title">
                    <a v-if="source.url" :href="source.url" target="_blank" rel="noopener">{{ source.title || '未命名资源' }}</a>
                    <span v-else>{{ source.title || '本地知识' }}</span>
                </div>
                  <div class="source-snippet">{{ source.snippet || source.content || '' }}</div>
                  <div class="source-type">{{ source.type === 'web' ? '网络资源' : '知识库' }}</div>
              </div>
            </div>

              <!-- 添加知识图谱节点引用 -->
              <div v-if="message.graphNodes && message.graphNodes.length > 0" class="graph-nodes-section">
                <div class="graph-nodes-title">知识图谱节点</div>
                <div v-for="(node, nIdx) in message.graphNodes" :key="nIdx" 
                     class="graph-node-item" 
                     @click="highlightNode(node.id)">
                  <div class="node-title">{{ node.label || node.name || node.id }}</div>
                  <div v-if="node.category" class="node-category">
                    <span class="node-tag" :class="node.category">{{ node.category }}</span>
          </div>
                  <div v-if="node.description" class="node-description">{{ node.description }}</div>
        </div>
          </div>
          </div>
        </div>
      </div>

      <!-- 聊天输入框 -->
      <div class="chat-input-container">
        <textarea 
          v-model="userInput"
          @keydown.enter.prevent="sendMessage" 
          placeholder="输入您的问题..."
          rows="3"
        ></textarea>
        <el-button class="send-button" type="primary" @click="sendMessage" :disabled="isLoading">
              发送
            </el-button>
      </div>
    </div>

      <!-- 右侧知识图谱区域 -->
      <div class="knowledge-graph-section" v-show="layoutMode === 'split' || layoutMode === 'graph'">
      <div class="graph-header">
        <h2>知识图谱</h2>
        <div class="graph-controls">
          <el-button size="small" type="primary" @click="showSelectRecordsDialog">
            选择记录
          </el-button>
            <el-button size="small" type="success" @click="showDroneImportDialog">
              导入无人机数据
          </el-button>
          <el-button size="small" type="danger" @click="clearAll">
            清除所有内容
          </el-button>
        </div>
      </div>
      <div class="graph-container" ref="graphContainer">
        <!-- D3知识图谱将在这里渲染 -->
      </div>
    </div>
  </div>

  <!-- 选择记录对话框 -->
  <el-dialog
    v-model="selectRecordsDialogVisible"
    title="选择记录"
    width="600px"
  >
    <div class="select-records-content">
      <div class="record-selection-group">
        <h3>路线规划记录</h3>
        <el-select
          v-model="selectedRouteId"
          placeholder="选择路线规划记录"
          clearable
          style="width: 100%"
        >
          <el-option
            v-for="route in routeHistory"
            :key="route.id"
            :label="route.title || `路线 ${route.id.substring(0, 8)}`"
            :value="route.id"
          >
            <div class="record-option">
              <div class="record-option-title">{{ route.title || `路线 ${route.id.substring(0, 8)}` }}</div>
              <div class="record-option-date">{{ new Date(route.created_at || Date.now()).toLocaleString() }}</div>
            </div>
          </el-option>
        </el-select>
      </div>
      
      <div class="record-selection-group">
        <h3>图片识别记录</h3>
        <el-select
          v-model="selectedAnalysisId"
          placeholder="选择图片识别记录"
          clearable
          style="width: 100%"
        >
          <el-option
            v-for="analysis in analysisHistory"
            :key="analysis.id"
            :label="`图片分析 ${new Date(analysis.timestamp).toLocaleString()}`"
            :value="analysis.id"
          >
            <div class="record-option">
              <div class="record-option-title">图片分析 {{ analysis.id.substring(0, 8) }}</div>
              <div class="record-option-date">{{ new Date(analysis.timestamp).toLocaleString() }}</div>
            </div>
          </el-option>
        </el-select>
      </div>
    </div>
    
    <div class="select-records-buttons">
      <el-button @click="selectRecordsDialogVisible = false">取消</el-button>
      <el-button @click="clearSelection">清除选择</el-button>
      <el-button @click="resetGraph">重置图谱</el-button>
      <el-button type="primary" @click="applySelectedRecords">应用</el-button>
    </div>
  </el-dialog>

    <!-- 无人机数据导入对话框 -->
    <el-dialog
      v-model="droneImportDialogVisible"
      title="导入无人机数据"
      width="800px"
      class="drone-import-dialog-wrapper"
    >
      <div class="drone-import-dialog">
        <div class="import-instructions">
          <h3>使用说明</h3>
          <p>请选择以下方式之一导入无人机知识图谱数据：</p>
          
          <div class="import-tabs">
            <div 
              class="import-tab" 
              :class="{ active: importTab === 'text' }" 
              @click="importTab = 'text'"
            >
              手动输入
            </div>
            <div 
              class="import-tab" 
              :class="{ active: importTab === 'file' }" 
              @click="importTab = 'file'"
            >
              导入文件
            </div>
          </div>
          
          <div class="tab-content">
            <!-- 手动输入选项卡 -->
            <div v-show="importTab === 'text'" class="text-tab-content">
              <p>在文本框中输入符合格式的无人机JSON数据，必须包含以下主要部分：</p>
              <ul>
                <li><strong>drones</strong>：无人机型号列表，包含各种属性</li>
                <li><strong>brands</strong>：品牌信息列表</li>
                <li><strong>relationships</strong>：关系列表，定义无人机与品牌、部件间的关系</li>
              </ul>
              <div class="import-actions">
                <el-button type="primary" size="small" @click="useExampleData">使用简单示例</el-button>
                <el-button type="success" size="small" @click="loadCreatedExample">加载详细示例</el-button>
                <el-button size="small" @click="resetDroneImport">重置</el-button>
              </div>
            </div>
            
            <!-- 导入文件选项卡 -->
            <div v-show="importTab === 'file'" class="file-tab-content">
              <p>请选择一个JSON格式的无人机数据文件：</p>
              <div class="file-upload-area">
                <input 
                  type="file" 
                  ref="localFileInput" 
                  accept=".json,application/json" 
                  @change="handleFileChange" 
                  style="display:none"
                />
                <el-button type="primary" @click="localFileInput.click()">
                  选择文件
                </el-button>
                <span class="file-name" v-if="localFileInput && localFileInput.files && localFileInput.files[0]">
                  已选择: {{ localFileInput.files[0].name }}
                </span>
                <span class="file-name" v-else>未选择文件</span>
              </div>
              <div class="file-instructions">
                <p>文件必须是有效的JSON格式，且包含无人机数据的必要结构。</p>
                <p>您也可以使用我们提供的<a href="/static/night_detection/models/drones_knowledge_graph.json" target="_blank">示例文件</a>作为参考。</p>
              </div>
            </div>
          </div>
        </div>
        
        <div class="import-form">
          <el-input
            v-model="droneJsonInput"
            type="textarea"
            :rows="15"
            placeholder="请输入JSON格式的无人机数据..."
            class="json-input"
          ></el-input>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="droneImportDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="importDroneData" :loading="isDroneImporting">
            导入数据
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.knowledge-chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #0f1724 0%, #1a2234 50%, #22293d 100%);
  overflow: hidden;
  position: relative;
  /* 移除固定padding，改为内部元素控制间距 */
  padding: 0;
  margin: 0;
  box-sizing: border-box;
}

.app-header {
  background: rgba(12, 19, 34, 0.75);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  position: relative;
  z-index: 10;
  /* 添加更明显的阴影提升层次感 */
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
}

.app-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-icon {
  font-size: 1.5rem;
}

.app-title h1 {
  color: #e6f1ff;
  font-weight: 500;
  font-size: 1.4rem;
  margin: 0;
  letter-spacing: 0.5px;
}

.title-badge {
  background: linear-gradient(135deg, #3182ce 0%, #4299e1 100%);
  color: white;
  font-size: 0.7rem;
  padding: 3px 8px;
  border-radius: 12px;
  font-weight: 500;
  margin-left: 10px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* 布局切换器样式 */
.layout-switcher {
  display: flex;
  background: rgba(26, 32, 44, 0.4);
  border-radius: 8px;
  padding: 4px;
  margin-right: 10px;
}

.layout-button {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.layout-button:hover {
  background: rgba(255, 255, 255, 0.1);
}

.layout-button.active {
  background: rgba(66, 153, 225, 0.3);
}

.layout-icon {
  width: 16px;
  height: 16px;
  display: block;
  background-position: center;
  background-repeat: no-repeat;
  background-size: contain;
}

.split-icon {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%23e2e8f0' viewBox='0 0 16 16'%3E%3Cpath d='M0 3a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3zm8.5-1v12h5.5a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1H8.5zm-1 0H2a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h5.5V2z'/%3E%3C/svg%3E");
}

.chat-icon {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%23e2e8f0' viewBox='0 0 16 16'%3E%3Cpath d='M8 15c4.418 0 8-3.134 8-7s-3.582-7-8-7-8 3.134-8 7c0 1.76.743 3.37 1.97 4.6-.097 1.016-.417 2.13-.771 2.966-.079.186.074.394.273.362 2.256-.37 3.597-.938 4.18-1.234A9.06 9.06 0 0 0 8 15z'/%3E%3C/svg%3E");
}

.graph-icon {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%23e2e8f0' viewBox='0 0 16 16'%3E%3Cpath fill-rule='evenodd' d='M6 3.5A1.5 1.5 0 0 1 7.5 2h1A1.5 1.5 0 0 1 10 3.5v1A1.5 1.5 0 0 1 8.5 6h-1A1.5 1.5 0 0 1 6 4.5v-1zM7.5 3a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5h-1zM10 6.5A1.5 1.5 0 0 1 11.5 5h1A1.5 1.5 0 0 1 14 6.5v1A1.5 1.5 0 0 1 12.5 9h-1A1.5 1.5 0 0 1 10 7.5v-1zm1.5-.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5h-1zM10 10.5a1.5 1.5 0 0 1 1.5-1.5h1A1.5 1.5 0 0 1 14 10.5v1a1.5 1.5 0 0 1-1.5 1.5h-1a1.5 1.5 0 0 1-1.5-1.5v-1zm1.5-.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5h-1zM2 10.5A1.5 1.5 0 0 1 3.5 9h1A1.5 1.5 0 0 1 6 10.5v1A1.5 1.5 0 0 1 4.5 13h-1A1.5 1.5 0 0 1 2 11.5v-1zm1.5-.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5h-1zM6 6.5A1.5 1.5 0 0 1 7.5 5h1A1.5 1.5 0 0 1 10 6.5v1A1.5 1.5 0 0 1 8.5 9h-1A1.5 1.5 0 0 1 6 7.5v-1zm1.5-.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5h-1z'/%3E%3C/svg%3E");
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
  /* 使用flex布局自适应高度 */
  height: calc(100vh - 80px); /* 减去header高度 */
  box-sizing: border-box;
}

/* 布局模式样式 */
.main-content.split .chat-section {
  display: flex;
  flex-direction: column;
  width: 40%;
  /* 确保内容可滚动 */
  overflow: hidden;
  height: 100%;
}

.main-content.split .knowledge-graph-section {
  width: 60%;
  /* 确保内容可滚动 */
  overflow: hidden;
  height: 100%;
}

.main-content.chat .chat-section {
  width: 100%;
}

.main-content.graph .knowledge-graph-section {
  width: 100%;
}

.chat-section {
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(26, 32, 44, 0.2);
  transition: width 0.3s ease;
  /* 使用flex布局自适应高度 */
  height: 100%;
  overflow: hidden;
}

.knowledge-graph-section {
  display: flex;
  flex-direction: column;
  background: rgba(26, 32, 44, 0.3);
  transition: width 0.3s ease;
  /* 确保占满整个高度 */
  height: 100%;
}

.chat-header, .graph-header {
  /* 将背景修改为毛玻璃效果 */
  background-color: rgba(12, 19, 34, 0.65);
  backdrop-filter: blur(15px);
  -webkit-backdrop-filter: blur(15px);
  padding: 16px 22px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 5;
}

.chat-header h2, .graph-header h2 {
  color: #e6f1ff;
  font-weight: 500;
  font-size: 1.25rem;
  margin: 0;
  letter-spacing: 0.5px;
}

.web-search-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #cbd5e0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px; /* 添加消息之间的间距 */
  /* 移除固定高度，让容器自适应 */
  height: auto;
  min-height: 200px; /* 提供最小高度 */
  max-height: calc(100vh - 200px); /* 设置最大高度，避免挤压其他元素 */
  overscroll-behavior: contain; /* 防止滚动传播 */
  scrollbar-width: thin; /* 细滚动条 */
  -ms-overflow-style: none; /* IE和Edge */
  padding-bottom: 20px;
  background-color: rgba(20, 30, 45, 0.5);
  position: relative;
  box-sizing: border-box;
}

.message {
  position: relative;
  margin-bottom: 16px;
  max-width: 95%;
  word-wrap: break-word;
  animation: fadeIn 0.3s ease-out;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  line-height: 1.6;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  overflow: visible; /* 改为visible，确保内容溢出时也能显示 */
  /* 添加背景色，确保内容可读 */
  background-color: rgba(30, 41, 59, 0.8);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.message.user {
  /* 使用更淡的渐变背景 */
  background: linear-gradient(135deg, rgba(44, 82, 130, 0.8) 0%, rgba(42, 67, 101, 0.8) 100%);
  color: #e2e8f0;
  align-self: flex-end;
  border-right: 3px solid #4299e1;
}

.message.assistant {
  /* 使用更淡的渐变背景 */
  background: linear-gradient(135deg, rgba(30, 42, 59, 0.8) 0%, rgba(45, 55, 72, 0.8) 100%);
  color: #e2e8f0;
  align-self: flex-start;
  border-left: 4px solid #4299e1;
}

.typing-indicator {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 4px;
  padding: 8px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background-color: #4299e1;
  border-radius: 50%;
  display: inline-block;
  animation: typing-bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes typing-bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* 参考资料样式 */
.sources-section {
  margin-top: 16px;
  border-top: 1px dashed rgba(255, 255, 255, 0.2);
  padding: 16px;
  background: rgba(30, 41, 59, 0.4);
  border-radius: 8px;
  margin-bottom: 12px;
  /* 设置独立滚动区域，限制最大高度 */
  max-height: 300px;
  overflow-y: auto;
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.2);
}

.sources-title {
  font-size: 14px;
  font-weight: 500;
  color: #a0aec0;
  margin-bottom: 8px;
}

.source-item {
  padding: 8px 12px;
  margin-bottom: 8px;
  background-color: rgba(45, 55, 72, 0.5);
  border-radius: 8px;
  border-left: 3px solid #3182ce;
  transition: all 0.2s ease;
}

.source-item:hover {
  background-color: rgba(45, 55, 72, 0.7);
  transform: translateY(-2px);
}

.source-title {
  font-weight: 500;
  margin-bottom: 4px;
}

.source-title a {
  color: #63b3ed;
  text-decoration: none;
}

.source-title a:hover {
  text-decoration: underline;
}

.source-snippet {
  font-size: 12px;
  color: #cbd5e0;
  margin-bottom: 4px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.source-type {
  font-size: 11px;
  color: #a0aec0;
  text-align: right;
}

/* 知识图谱节点样式 */
.graph-nodes-section {
  margin-top: 16px;
  border-top: 1px dashed rgba(255, 255, 255, 0.2);
  padding: 16px;
  background: rgba(30, 41, 59, 0.4);
  border-radius: 8px;
  margin-bottom: 12px;
  /* 设置独立滚动区域，限制最大高度 */
  max-height: 300px;
  overflow-y: auto;
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.2);
}

.graph-nodes-title {
  font-size: 14px;
  font-weight: 500;
  color: #a0aec0;
  margin-bottom: 8px;
}

.graph-node-item {
  padding: 8px 12px;
  margin-bottom: 8px;
  background-color: rgba(45, 55, 72, 0.5);
  border-radius: 8px;
  border-left: 3px solid #38a169;
  cursor: pointer;
  transition: all 0.2s ease;
}

.graph-node-item:hover {
  background-color: rgba(45, 55, 72, 0.7);
  transform: translateX(5px);
}

.node-title {
  font-weight: 500;
  margin-bottom: 4px;
  color: #e2e8f0;
}

.node-category {
  margin-bottom: 4px;
}

.node-tag {
  display: inline-block;
  padding: 2px 6px;
  font-size: 11px;
  border-radius: 4px;
  margin-right: 4px;
  background-color: rgba(56, 161, 105, 0.3);
  color: #9ae6b4;
}

.node-description {
  font-size: 12px;
  color: #cbd5e0;
  line-height: 1.4;
}

.message-input {
  display: flex;
  padding: 16px;
  background-color: rgba(26, 32, 44, 0.8);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.message-input textarea {
  flex: 1;
  padding: 14px 18px;
  border: none;
  border-radius: 10px;
  background-color: rgba(74, 85, 104, 0.6);
  color: #e2e8f0;
  resize: none;
  outline: none;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  font-size: 15px;
}

.message-input textarea:focus {
  background-color: rgba(74, 85, 104, 0.8);
  box-shadow: 0 0 0 2px rgba(66, 153, 225, 0.5);
}

.send-button {
  margin-left: 12px;
  padding: 10px 20px;
  font-size: 16px;
  height: 60px; /* 调整按钮高度与输入框匹配 */
  align-self: flex-end;
  transition: transform 0.2s ease;
  border-radius: 10px;
  background: linear-gradient(135deg, #3182ce 0%, #4299e1 100%);
}

.send-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.graph-controls {
  display: flex;
  gap: 10px;
}

.graph-container {
  flex: 1;
  overflow: hidden;
  position: relative;
  border-radius: 0;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.2);
  /* 确保图谱有足够的显示空间 */
  min-height: calc(100vh - 200px);
}

/* 响应式布局 */
@media (max-width: 992px) {
  .header-actions {
    flex-wrap: wrap;
  }
  
  .main-content.split {
    flex-direction: column;
  }
  
  .main-content.split .chat-section,
  .main-content.split .knowledge-graph-section {
    width: 100%;
  }
  
  .main-content.split .chat-section {
    height: 50%;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
  
  .main-content.split .knowledge-graph-section {
    height: 50%;
  }
}

/* 手机端优化 */
@media (max-width: 576px) {
  .knowledge-chat-container {
    padding-top: 10px;
  }
  
  .app-header {
    flex-direction: column;
    align-items: flex-start;
  padding: 12px 16px;
    /* 确保在移动设备上有足够的顶部间距 */
    margin-top: 15px;
  }
  
  .chat-messages {
    padding-top: 40px;
  }
  
  .title-badge {
    font-size: 0.6rem;
    padding: 2px 6px;
  }
  
  .graph-header {
    flex-direction: column;
    align-items: flex-start;
  padding: 10px;
}

  .graph-controls {
  margin-top: 10px;
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
}

  .main-content.split .chat-section {
    height: 60%;
}

  .main-content.split .knowledge-graph-section {
    height: 40%;
}
}

/* 对话框样式 */
.select-records-dialog .el-dialog__body {
  padding: 16px 22px;
  max-height: 60vh;
  overflow-y: auto;
  background-color: #1a2234;
  border-radius: 0 0 12px 12px;
}

.select-records-dialog .el-dialog__header {
  background-color: #1a2234;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 16px 22px;
  border-radius: 12px 12px 0 0;
}

.select-records-dialog .el-dialog__title {
  color: #e6f1ff;
  font-weight: 500;
}

.record-option {
  padding: 14px;
  border-radius: 10px;
  margin-bottom: 12px;
  transition: all 0.3s ease;
  cursor: pointer;
  background-color: rgba(45, 55, 72, 0.6);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-left: 3px solid transparent;
}

.record-option:hover {
  background-color: rgba(74, 85, 104, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-left: 3px solid #4299e1;
}

.record-option h3 {
  margin: 0 0 8px 0;
  color: #e2e8f0;
  font-weight: 500;
}

.record-option p {
  margin: 0;
  color: #a0aec0;
  font-size: 0.9rem;
  line-height: 1.5;
}

/* 无人机数据导入对话框样式 */
.drone-import-dialog-wrapper :deep(.el-dialog__body) {
  padding: 20px;
  /* 添加模糊背景效果 */
  background-color: rgba(30, 41, 59, 0.9);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.drone-import-dialog {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.import-instructions {
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
}

.import-instructions h3 {
  color: #e2e8f0;
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 1.1rem;
}

.import-instructions p, .import-instructions ul {
  color: #cbd5e0;
  margin: 8px 0;
}

.import-instructions ul {
  padding-left: 20px;
}

.import-tabs {
  display: flex;
  margin: 15px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.import-tab {
  padding: 8px 15px;
  cursor: pointer;
  color: #a0aec0;
  border-bottom: 2px solid transparent;
  transition: all 0.3s ease;
}

.import-tab.active {
  color: #4299e1;
  border-bottom-color: #4299e1;
}

.import-tab:hover:not(.active) {
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.05);
}

.tab-content {
  padding: 15px 0;
}

.file-tab-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.file-upload-area {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 10px 0;
}

.file-name {
  color: #a0aec0;
  font-size: 0.9rem;
}

.file-instructions {
  background: rgba(0, 0, 0, 0.2);
  padding: 10px;
  border-radius: 4px;
  margin-top: 10px;
}

.file-instructions p {
  margin: 5px 0;
  font-size: 0.9rem;
}

.file-instructions a {
  color: #4299e1;
  text-decoration: none;
}

.file-instructions a:hover {
  text-decoration: underline;
}

.import-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.json-input {
  background: rgba(15, 23, 42, 0.3);
  border-color: rgba(255, 255, 255, 0.1);
}

.json-input :deep(textarea) {
  color: #e2e8f0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9rem;
}

/* 动画效果 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
  }

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes pulse {
  0% { border-right: 3px solid rgba(66, 153, 225, 0); }
  50% { border-right: 3px solid rgba(66, 153, 225, 0.7); }
  100% { border-right: 3px solid rgba(66, 153, 225, 0); }
}

/* 搜索结果区域 */
.search-results {
  /* 使搜索结果区域背景更透明 */
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  padding: 15px;
  margin: 15px 15px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.search-results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 10px;
}

.search-results-header h3 {
  font-size: 16px;
  color: #e2e8f0;
  margin: 0;
  font-weight: 500;
}

.search-results-section {
  margin-bottom: 15px;
}

.search-results-section h4 {
  font-size: 14px;
  color: #a0aec0;
  margin: 10px 0;
  padding-bottom: 5px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.search-result-item {
  padding: 10px;
  margin-bottom: 10px;
  border-radius: 6px;
  /* 使背景更透明 */
  background-color: rgba(30, 41, 59, 0.3);
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.search-result-item:hover {
  /* 悬停时稍微加深背景 */
  background-color: rgba(45, 55, 72, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.search-result-item.graph-result {
  border-left-color: #3182ce;
}

.search-result-item.model-result {
  border-left-color: #805ad5;
}

.search-result-item .result-title {
  font-weight: 600;
  margin-bottom: 5px;
  color: #e2e8f0;
}

.search-result-item .result-title a {
  color: #63b3ed;
  text-decoration: none;
}

.search-result-item .result-title a:hover {
  text-decoration: underline;
  color: #4299e1;
}

.search-result-item .result-snippet {
  font-size: 14px;
  color: #cbd5e0;
  margin-bottom: 5px;
  line-height: 1.4;
}

.search-result-item .result-relevance {
  font-size: 12px;
  color: #a0aec0;
  text-align: right;
  margin-top: 5px;
}

/* 知识图谱节点标签 */
.node-tag {
  display: inline-block;
  padding: 2px 6px;
  font-size: 12px;
  font-weight: normal;
  border-radius: 4px;
  margin-right: 6px;
  color: white;
  background-color: #3B82F6;
}

/* 不同类型的节点标签颜色 */
.node-tag.无人机 { background-color: #EF4444; }
.node-tag.品牌 { background-color: #F59E0B; }
.node-tag.分类 { background-color: #10B981; }
.node-tag.部件 { background-color: #3B82F6; }
.node-tag.技术 { background-color: #8B5CF6; }
.node-tag.应用 { background-color: #EC4899; }
.node-tag.软件 { background-color: #0EA5E9; }
.node-tag.集成 { background-color: #14B8A6; }
.node-tag.知识 { background-color: #6366F1; }

/* 元数据标签 */
.metadata-tag {
  display: inline-block;
  padding: 2px 5px;
  margin: 2px;
  font-size: 11px;
  background-color: rgba(107, 114, 128, 0.3);
  color: #d1d5db;
  border-radius: 3px;
}

/* 图谱高亮节点 */
.node.highlighted circle {
  stroke: #FF5722 !important;
  stroke-width: 3px !important;
  filter: drop-shadow(0 0 8px rgba(255, 87, 34, 0.5)) !important;
}

/* 助手标签 */
.assistant-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.assistant-name {
  font-weight: 600;
  color: #63b3ed;
}

.assistant-tags {
  display: flex;
  gap: 5px;
}

.assistant-tags .tag {
  font-size: 11px;
  padding: 2px 6px;
  background-color: rgba(59, 130, 246, 0.2);
  color: #63b3ed;
  border-radius: 4px;
}

/* 替换助手头像为SVG */
.message.assistant .message-avatar .avatar-icon {
  display: none; /* 隐藏原图标 */
}

.message.assistant .message-avatar {
  position: relative;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message.assistant .message-avatar::before {
  content: "";
  position: absolute;
  width: 24px;
  height: 24px;
  background-image: url("data:image/svg+xml,%3Csvg t='1747102188514' class='icon' viewBox='0 0 1024 1024' version='1.1' xmlns='http://www.w3.org/2000/svg' p-id='4650' width='200' height='200'%3E%3Cpath d='M79.11424 270.67904l116.2496 66.9952a97.1776 97.1776 0 0 0-4.87424 30.57664v268.7232a97.53088 97.53088 0 0 0 47.39584 83.72736l219.42784 131.31264a97.28 97.28 0 0 0 15.4112 7.45984v153.84576a97.6384 97.6384 0 0 1-11.06944-5.70368L120.32 803.34848a97.51552 97.51552 0 0 1-47.44704-83.62496v-414.72c0-11.89376 2.19648-23.5008 6.2464-34.32448z m871.4752 34.32448v414.67392a97.52576 97.52576 0 0 1-47.44704 83.67104L561.8176 1007.6672c-3.6096 2.0992-7.31648 3.99872-11.06944 5.6576v-157.6448c2.28864-1.1264 4.5312-2.34496 6.72768-3.6608l219.42784-131.31264a97.53088 97.53088 0 0 0 47.44192-83.72736V368.25088a97.07008 97.07008 0 0 0-1.36192-16.384l124.3904-71.68c2.0992 7.99744 3.2256 16.3328 3.2256 24.81664zM561.8176 17.06496l336.59904 201.39008-118.2464 68.11648c-1.0752-0.70144-2.16576-1.3824-3.26656-2.048l-219.42784-131.31264a97.52576 97.52576 0 0 0-100.15744 0L248.32 278.28224l-113.76128-65.536L461.65504 17.06496a97.52576 97.52576 0 0 1 100.15744 0z' p-id='4651' fill='%234299e1'%3E%3C/path%3E%3Cpath d='M264.60672 365.22496L483.84 491.0336v275.98848a97.34144 97.34144 0 0 1-31.7952-12.09344L304.7936 667.1616a97.52576 97.52576 0 0 1-47.54432-83.77344V402.3808c0-12.96896 2.5856-25.5488 7.31136-37.15584h0.0512z m482.10944 37.15584v181.00736c0 34.3552-18.07872 66.18112-47.5904 83.77344l-147.21536 87.76704c-2.58048 1.51552-5.21728 2.92864-7.90016 4.2496V499.6608l201.04704-115.27168c1.11104 5.9392 1.664 11.9552 1.65888 17.99168z m-194.80576-171.54048l147.26144 87.77216a97.536 97.536 0 0 1 17.26464 13.16352l-193.39264 110.83776h-3.21536L304.29696 318.90432l0.49152-0.34304L452.0448 230.78912a97.52576 97.52576 0 0 1 99.86048 0v0.0512z' p-id='4652' fill='%234299e1'%3E%3C/path%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-size: contain;
}

/* 优化聊天消息容器 */
.message-content {
  flex: 1;
  overflow-wrap: break-word;
  line-height: 1.5;
  position: relative;
  padding: 4px;
}

/* 修复markdown内容显示 */
.markdown-content {
  color: #e2e8f0;
  line-height: 1.6;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  margin-top: 16px;
  margin-bottom: 8px;
  color: #fff;
}

.markdown-content :deep(p) {
  margin-bottom: 12px;
}

.markdown-content :deep(pre) {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
  margin: 12px 0;
}

.markdown-content :deep(code) {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  background: rgba(0, 0, 0, 0.15);
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 0.9em;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  padding-left: 20px;
  margin-bottom: 12px;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid #4299e1;
  padding-left: 12px;
  color: #a0aec0;
  margin: 12px 0;
}

/* 增加聊天输入框的尺寸和样式 */
.chat-input-container {
  padding: 20px;
  background-color: rgba(26, 32, 44, 0.7);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  position: relative;
  z-index: 5;
  display: flex;
  align-items: flex-end;
  /* 确保底部有足够间距 */
  margin-bottom: 10px;
}

.chat-input-container textarea {
  flex: 1;
  min-height: 60px; /* 增加输入框高度 */
  max-height: 150px; /* 设置最大高度 */
  padding: 14px 18px;
  border: none;
  border-radius: 12px;
  background-color: rgba(45, 55, 72, 0.6);
  color: #e2e8f0;
  resize: vertical; /* 允许垂直拉伸 */
  outline: none;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  font-size: 15px;
  line-height: 1.5;
}

.chat-input-container textarea:focus {
  background-color: rgba(74, 85, 104, 0.7);
  box-shadow: 0 0 0 2px rgba(66, 153, 225, 0.5);
}

.send-button {
  margin-left: 12px;
  padding: 10px 20px;
  font-size: 16px;
  height: 60px; /* 调整按钮高度与输入框匹配 */
  align-self: flex-end;
  transition: transform 0.2s ease;
  border-radius: 10px;
  background: linear-gradient(135deg, #3182ce 0%, #4299e1 100%);
}

.send-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.graph-controls {
  display: flex;
  gap: 10px;
}

.graph-container {
  flex: 1;
  overflow: hidden;
  position: relative;
  border-radius: 0;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.2);
  /* 确保图谱有足够的显示空间 */
  min-height: calc(100vh - 200px);
}

/* 响应式布局 */
@media (max-width: 992px) {
  .header-actions {
    flex-wrap: wrap;
  }
  
  .main-content.split {
    flex-direction: column;
  }
  
  .main-content.split .chat-section,
  .main-content.split .knowledge-graph-section {
    width: 100%;
  }
  
  .main-content.split .chat-section {
    height: 50%;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
  
  .main-content.split .knowledge-graph-section {
    height: 50%;
  }
}

/* 手机端优化 */
@media (max-width: 576px) {
  .knowledge-chat-container {
    padding-top: 10px;
  }
  
  .app-header {
    flex-direction: column;
    align-items: flex-start;
  padding: 12px 16px;
    /* 确保在移动设备上有足够的顶部间距 */
    margin-top: 15px;
  }
  
  .chat-messages {
    padding-top: 40px;
  }
  
  .title-badge {
    font-size: 0.6rem;
    padding: 2px 6px;
  }
  
  .graph-header {
    flex-direction: column;
    align-items: flex-start;
  padding: 10px;
}

  .graph-controls {
  margin-top: 10px;
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
}

  .main-content.split .chat-section {
    height: 60%;
}

  .main-content.split .knowledge-graph-section {
    height: 40%;
}
}

/* 对话框样式 */
.select-records-dialog .el-dialog__body {
  padding: 16px 22px;
  max-height: 60vh;
  overflow-y: auto;
  background-color: #1a2234;
  border-radius: 0 0 12px 12px;
}

.select-records-dialog .el-dialog__header {
  background-color: #1a2234;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 16px 22px;
  border-radius: 12px 12px 0 0;
}

.select-records-dialog .el-dialog__title {
  color: #e6f1ff;
  font-weight: 500;
}

.record-option {
  padding: 14px;
  border-radius: 10px;
  margin-bottom: 12px;
  transition: all 0.3s ease;
  cursor: pointer;
  background-color: rgba(45, 55, 72, 0.6);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-left: 3px solid transparent;
}

.record-option:hover {
  background-color: rgba(74, 85, 104, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-left: 3px solid #4299e1;
}

.record-option h3 {
  margin: 0 0 8px 0;
  color: #e2e8f0;
  font-weight: 500;
}

.record-option p {
  margin: 0;
  color: #a0aec0;
  font-size: 0.9rem;
  line-height: 1.5;
}

/* 无人机数据导入对话框样式 */
.drone-import-dialog-wrapper :deep(.el-dialog__body) {
  padding: 20px;
  /* 添加模糊背景效果 */
  background-color: rgba(30, 41, 59, 0.9);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.drone-import-dialog {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.import-instructions {
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
}

.import-instructions h3 {
  color: #e2e8f0;
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 1.1rem;
}

.import-instructions p, .import-instructions ul {
  color: #cbd5e0;
  margin: 8px 0;
}

.import-instructions ul {
  padding-left: 20px;
}

.import-tabs {
  display: flex;
  margin: 15px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.import-tab {
  padding: 8px 15px;
  cursor: pointer;
  color: #a0aec0;
  border-bottom: 2px solid transparent;
  transition: all 0.3s ease;
}

.import-tab.active {
  color: #4299e1;
  border-bottom-color: #4299e1;
}

.import-tab:hover:not(.active) {
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.05);
}

.tab-content {
  padding: 15px 0;
}

.file-tab-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.file-upload-area {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 10px 0;
}

.file-name {
  color: #a0aec0;
  font-size: 0.9rem;
}

.file-instructions {
  background: rgba(0, 0, 0, 0.2);
  padding: 10px;
  border-radius: 4px;
  margin-top: 10px;
}

.file-instructions p {
  margin: 5px 0;
  font-size: 0.9rem;
}

.file-instructions a {
  color: #4299e1;
  text-decoration: none;
}

.file-instructions a:hover {
  text-decoration: underline;
}

.import-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.json-input {
  background: rgba(15, 23, 42, 0.3);
  border-color: rgba(255, 255, 255, 0.1);
}

.json-input :deep(textarea) {
  color: #e2e8f0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9rem;
}

/* 动画效果 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
  }

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes pulse {
  0% { border-right: 3px solid rgba(66, 153, 225, 0); }
  50% { border-right: 3px solid rgba(66, 153, 225, 0.7); }
  100% { border-right: 3px solid rgba(66, 153, 225, 0); }
}

/* 搜索结果区域 */
.search-results {
  /* 使搜索结果区域背景更透明 */
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  padding: 15px;
  margin: 15px 15px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.search-results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 10px;
}

.search-results-header h3 {
  font-size: 16px;
  color: #e2e8f0;
  margin: 0;
  font-weight: 500;
}

.search-results-section {
  margin-bottom: 15px;
}

.search-results-section h4 {
  font-size: 14px;
  color: #a0aec0;
  margin: 10px 0;
  padding-bottom: 5px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.search-result-item {
  padding: 10px;
  margin-bottom: 10px;
  border-radius: 6px;
  /* 使背景更透明 */
  background-color: rgba(30, 41, 59, 0.3);
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.search-result-item:hover {
  /* 悬停时稍微加深背景 */
  background-color: rgba(45, 55, 72, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.search-result-item.graph-result {
  border-left-color: #3182ce;
}

.search-result-item.model-result {
  border-left-color: #805ad5;
}

.search-result-item .result-title {
  font-weight: 600;
  margin-bottom: 5px;
  color: #e2e8f0;
}

.search-result-item .result-title a {
  color: #63b3ed;
  text-decoration: none;
}

.search-result-item .result-title a:hover {
  text-decoration: underline;
  color: #4299e1;
}

.search-result-item .result-snippet {
  font-size: 14px;
  color: #cbd5e0;
  margin-bottom: 5px;
  line-height: 1.4;
}

.search-result-item .result-relevance {
  font-size: 12px;
  color: #a0aec0;
  text-align: right;
  margin-top: 5px;
}

/* 知识图谱节点标签 */
.node-tag {
  display: inline-block;
  padding: 2px 6px;
  font-size: 12px;
  font-weight: normal;
  border-radius: 4px;
  margin-right: 6px;
  color: white;
  background-color: #3B82F6;
}

/* 不同类型的节点标签颜色 */
.node-tag.无人机 { background-color: #EF4444; }
.node-tag.品牌 { background-color: #F59E0B; }
.node-tag.分类 { background-color: #10B981; }
.node-tag.部件 { background-color: #3B82F6; }
.node-tag.技术 { background-color: #8B5CF6; }
.node-tag.应用 { background-color: #EC4899; }
.node-tag.软件 { background-color: #0EA5E9; }
.node-tag.集成 { background-color: #14B8A6; }
.node-tag.知识 { background-color: #6366F1; }

/* 元数据标签 */
.metadata-tag {
  display: inline-block;
  padding: 2px 5px;
  margin: 2px;
  font-size: 11px;
  background-color: rgba(107, 114, 128, 0.3);
  color: #d1d5db;
  border-radius: 3px;
}

/* 图谱高亮节点 */
.node.highlighted circle {
  stroke: #FF5722 !important;
  stroke-width: 3px !important;
  filter: drop-shadow(0 0 8px rgba(255, 87, 34, 0.5)) !important;
}

/* 助手标签 */
.assistant-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.assistant-name {
  font-weight: 600;
  color: #63b3ed;
}

.assistant-tags {
  display: flex;
  gap: 5px;
}

.assistant-tags .tag {
  font-size: 11px;
  padding: 2px 6px;
  background-color: rgba(59, 130, 246, 0.2);
  color: #63b3ed;
  border-radius: 4px;
}

/* 替换助手头像为SVG */
.message.assistant .message-avatar .avatar-icon {
  display: none; /* 隐藏原图标 */
}

.message.assistant .message-avatar {
  position: relative;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message.assistant .message-avatar::before {
  content: "";
  position: absolute;
  width: 24px;
  height: 24px;
  background-image: url("data:image/svg+xml,%3Csvg t='1747102188514' class='icon' viewBox='0 0 1024 1024' version='1.1' xmlns='http://www.w3.org/2000/svg' p-id='4650' width='200' height='200'%3E%3Cpath d='M79.11424 270.67904l116.2496 66.9952a97.1776 97.1776 0 0 0-4.87424 30.57664v268.7232a97.53088 97.53088 0 0 0 47.39584 83.72736l219.42784 131.31264a97.28 97.28 0 0 0 15.4112 7.45984v153.84576a97.6384 97.6384 0 0 1-11.06944-5.70368L120.32 803.34848a97.51552 97.51552 0 0 1-47.44704-83.62496v-414.72c0-11.89376 2.19648-23.5008 6.2464-34.32448z m871.4752 34.32448v414.67392a97.52576 97.52576 0 0 1-47.44704 83.67104L561.8176 1007.6672c-3.6096 2.0992-7.31648 3.99872-11.06944 5.6576v-157.6448c2.28864-1.1264 4.5312-2.34496 6.72768-3.6608l219.42784-131.31264a97.53088 97.53088 0 0 0 47.44192-83.72736V368.25088a97.07008 97.07008 0 0 0-1.36192-16.384l124.3904-71.68c2.0992 7.99744 3.2256 16.3328 3.2256 24.81664zM561.8176 17.06496l336.59904 201.39008-118.2464 68.11648c-1.0752-0.70144-2.16576-1.3824-3.26656-2.048l-219.42784-131.31264a97.52576 97.52576 0 0 0-100.15744 0L248.32 278.28224l-113.76128-65.536L461.65504 17.06496a97.52576 97.52576 0 0 1 100.15744 0z' p-id='4651' fill='%234299e1'%3E%3C/path%3E%3Cpath d='M264.60672 365.22496L483.84 491.0336v275.98848a97.34144 97.34144 0 0 1-31.7952-12.09344L304.7936 667.1616a97.52576 97.52576 0 0 1-47.54432-83.77344V402.3808c0-12.96896 2.5856-25.5488 7.31136-37.15584h0.0512z m482.10944 37.15584v181.00736c0 34.3552-18.07872 66.18112-47.5904 83.77344l-147.21536 87.76704c-2.58048 1.51552-5.21728 2.92864-7.90016 4.2496V499.6608l201.04704-115.27168c1.11104 5.9392 1.664 11.9552 1.65888 17.99168z m-194.80576-171.54048l147.26144 87.77216a97.536 97.536 0 0 1 17.26464 13.16352l-193.39264 110.83776h-3.21536L304.29696 318.90432l0.49152-0.34304L452.0448 230.78912a97.52576 97.52576 0 0 1 99.86048 0v0.0512z' p-id='4652' fill='%234299e1'%3E%3C/path%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-size: contain;
}

/* 优化聊天消息容器 */
.message-content {
  flex: 1;
  overflow-wrap: break-word;
  line-height: 1.5;
  position: relative;
  padding: 4px;
}

/* 修复markdown内容显示 */
.markdown-content {
  color: #e2e8f0;
  line-height: 1.6;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  margin-top: 16px;
  margin-bottom: 8px;
  color: #fff;
}

.markdown-content :deep(p) {
  margin-bottom: 12px;
}

.markdown-content :deep(pre) {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
  margin: 12px 0;
}

.markdown-content :deep(code) {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  background: rgba(0, 0, 0, 0.15);
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 0.9em;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  padding-left: 20px;
  margin-bottom: 12px;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid #4299e1;
  padding-left: 12px;
  color: #a0aec0;
  margin: 12px 0;
}

/* 增加聊天输入框的尺寸和样式 */
.chat-input-container {
  padding: 20px;
  background-color: rgba(26, 32, 44, 0.7);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  position: relative;
  z-index: 5;
  display: flex;
  align-items: flex-end;
  /* 确保底部有足够间距 */
  margin-bottom: 10px;
}

.chat-input-container textarea {
  flex: 1;
  min-height: 70px; /* 提供合适的初始高度 */
  max-height: 150px; /* 设置最大高度，防止过度扩展 */
  padding: 14px 18px;
  border: none;
  border-radius: 12px;
  background-color: rgba(45, 55, 72, 0.6);
  color: #e2e8f0;
  resize: vertical; /* 允许垂直拉伸调整高度 */
  outline: none;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  font-size: 15px;
  line-height: 1.5;
  overflow-y: auto; /* 允许内容滚动 */
  scrollbar-width: thin; /* 细滚动条 */
}

.chat-input-container textarea:focus {
  background-color: rgba(74, 85, 104, 0.7);
  box-shadow: 0 0 0 2px rgba(66, 153, 225, 0.5);
}

.send-button {
  margin-left: 12px;
  padding: 10px 20px;
  height: 70px; /* 调整按钮高度与输入框匹配 */
  border-radius: 10px;
  background: linear-gradient(135deg, #3182ce 0%, #4299e1 100%);
  font-size: 16px;
}

.send-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

/* 添加思考过程和正式回答的样式 */
.markdown-content :deep(h2:first-of-type) {
  margin-top: 0;
  color: #4299e1;
  font-size: 1.25rem;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.markdown-content :deep(h2:nth-of-type(2)) {
  color: #48bb78;
  font-size: 1.25rem;
  padding-bottom: 6px;
  margin-top: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.node.highlighted circle {
  stroke: #FF5722 !important;
  stroke-width: 3px !important;
  filter: drop-shadow(0 0 8px rgba(255, 87, 34, 0.5)) !important;
}

/* 添加助手图标样式 */
.message.assistant .message-avatar .avatar-icon {
  display: none !important;
}

.message.assistant .message-avatar {
  position: relative;
  width: 32px;
  height: 32px;
}

.message.assistant .message-avatar::before {
  content: "";
  position: absolute;
  top: 4px;
  left: 4px;
  width: 24px;
  height: 24px;
  background-image: url("data:image/svg+xml,%3Csvg t='1747102188514' class='icon' viewBox='0 0 1024 1024' version='1.1' xmlns='http://www.w3.org/2000/svg' p-id='4650' width='200' height='200'%3E%3Cpath d='M79.11424 270.67904l116.2496 66.9952a97.1776 97.1776 0 0 0-4.87424 30.57664v268.7232a97.53088 97.53088 0 0 0 47.39584 83.72736l219.42784 131.31264a97.28 97.28 0 0 0 15.4112 7.45984v153.84576a97.6384 97.6384 0 0 1-11.06944-5.70368L120.32 803.34848a97.51552 97.51552 0 0 1-47.44704-83.62496v-414.72c0-11.89376 2.19648-23.5008 6.2464-34.32448z m871.4752 34.32448v414.67392a97.52576 97.52576 0 0 1-47.44704 83.67104L561.8176 1007.6672c-3.6096 2.0992-7.31648 3.99872-11.06944 5.6576v-157.6448c2.28864-1.1264 4.5312-2.34496 6.72768-3.6608l219.42784-131.31264a97.53088 97.53088 0 0 0 47.44192-83.72736V368.25088a97.07008 97.07008 0 0 0-1.36192-16.384l124.3904-71.68c2.0992 7.99744 3.2256 16.3328 3.2256 24.81664zM561.8176 17.06496l336.59904 201.39008-118.2464 68.11648c-1.0752-0.70144-2.16576-1.3824-3.26656-2.048l-219.42784-131.31264a97.52576 97.52576 0 0 0-100.15744 0L248.32 278.28224l-113.76128-65.536L461.65504 17.06496a97.52576 97.52576 0 0 1 100.15744 0z' p-id='4651' fill='%234299e1'%3E%3C/path%3E%3Cpath d='M264.60672 365.22496L483.84 491.0336v275.98848a97.34144 97.34144 0 0 1-31.7952-12.09344L304.7936 667.1616a97.52576 97.52576 0 0 1-47.54432-83.77344V402.3808c0-12.96896 2.5856-25.5488 7.31136-37.15584h0.0512z m482.10944 37.15584v181.00736c0 34.3552-18.07872 66.18112-47.5904 83.77344l-147.21536 87.76704c-2.58048 1.51552-5.21728 2.92864-7.90016 4.2496V499.6608l201.04704-115.27168c1.11104 5.9392 1.664 11.9552 1.65888 17.99168z m-194.80576-171.54048l147.26144 87.77216a97.536 97.536 0 0 1 17.26464 13.16352l-193.39264 110.83776h-3.21536L304.29696 318.90432l0.49152-0.34304L452.0448 230.78912a97.52576 97.52576 0 0 1 99.86048 0v0.0512z' p-id='4652' fill='%234299e1'%3E%3C/path%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-size: contain;
}

/* 修复markdown内容显示 */
.markdown-content {
  color: #e2e8f0;
  line-height: 1.6;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  margin-top: 16px;
  margin-bottom: 8px;
  color: #fff;
}

.markdown-content :deep(p) {
  margin-bottom: 12px;
}

.markdown-content :deep(pre) {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
  margin: 12px 0;
}

.markdown-content :deep(code) {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  background: rgba(0, 0, 0, 0.15);
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 0.9em;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  padding-left: 20px;
  margin-bottom: 12px;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid #4299e1;
  padding-left: 12px;
  color: #a0aec0;
  margin: 12px 0;
}

/* 增加聊天输入框的尺寸和样式 */
.chat-input-container {
  padding: 20px;
  background-color: rgba(26, 32, 44, 0.7);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  position: relative;
  z-index: 5;
  display: flex;
  align-items: flex-end;
}

.chat-input-container textarea {
  flex: 1;
  min-height: 70px; /* 增加输入框高度 */
  max-height: 150px; /* 设置最大高度 */
  padding: 14px 18px;
  border: none;
  border-radius: 12px;
  background-color: rgba(45, 55, 72, 0.6);
  color: #e2e8f0;
  resize: vertical; /* 允许垂直拉伸 */
  outline: none;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  font-size: 15px;
  line-height: 1.5;
}

.chat-input-container textarea:focus {
  background-color: rgba(74, 85, 104, 0.7);
  box-shadow: 0 0 0 2px rgba(66, 153, 225, 0.5);
}

.send-button {
  margin-left: 12px;
  padding: 10px 20px;
  height: 70px; /* 调整按钮高度与输入框匹配 */
  border-radius: 10px;
  background: linear-gradient(135deg, #3182ce 0%, #4299e1 100%);
  font-size: 16px;
}

.send-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

/* 添加思考过程和正式回答的样式 */
.markdown-content :deep(h2:first-of-type) {
  margin-top: 0;
  color: #4299e1;
  font-size: 1.25rem;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.markdown-content :deep(h2:nth-of-type(2)) {
  color: #48bb78;
  font-size: 1.25rem;
  padding-bottom: 6px;
  margin-top: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.message-content {
  padding: 16px;
  color: #e2e8f0;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  word-break: break-word;
  /* 移除固定最大高度，允许内容扩展 */
  max-height: none;
  /* 允许长内容在消息内滚动 */
  overflow-y: visible;
  height: auto;
}

/* 修改markdown内容样式 */
.markdown-content {
  color: #e2e8f0;
  line-height: 1.6;
  /* 确保内容不会被截断 */
  overflow: visible;
  height: auto;
}

/* 添加滚动条样式 */
.chat-messages::-webkit-scrollbar,
.sources-section::-webkit-scrollbar,
.graph-nodes-section::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.chat-messages::-webkit-scrollbar-track,
.sources-section::-webkit-scrollbar-track,
.graph-nodes-section::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb,
.sources-section::-webkit-scrollbar-thumb,
.graph-nodes-section::-webkit-scrollbar-thumb {
  background: rgba(66, 153, 225, 0.5);
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover,
.sources-section::-webkit-scrollbar-thumb:hover,
.graph-nodes-section::-webkit-scrollbar-thumb:hover {
  background: rgba(66, 153, 225, 0.8);
}
</style>
