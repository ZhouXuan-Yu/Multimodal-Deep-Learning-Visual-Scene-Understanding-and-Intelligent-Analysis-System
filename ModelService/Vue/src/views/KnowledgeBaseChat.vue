<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { ElMessage, ElDialog, ElSelect, ElOption } from 'element-plus';
import { UserFilled, Service } from '@element-plus/icons-vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import * as d3 from 'd3';
import { knowledgeChatApi } from '@/api/knowledgeChat';
import { useRoutePlanningStore } from '@/stores/routePlanning';
import { useAnalysisHistoryStore } from '@/stores/analysisHistory';

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

// 格式化 Markdown
const formatMarkdown = (text) => {
  if (!text) return '';
  return DOMPurify.sanitize(marked.parse(text));
};

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || isLoading.value) return;
  
  const message = userInput.value.trim();
  userInput.value = '';
  
  // 添加用户消息
  chatHistory.value.push({
    role: 'user',
    content: message
  });
  
  // 自动滚动到底部
  await nextTick();
  scrollToBottom();
  
  isLoading.value = true;
  searchResults.value = [];
  
  try {
    // 准备调用API
    const url = '/api/knowledge-chat/stream';
      const requestData = {
      message: message,
      web_search: webSearchEnabled.value,
      model: 'qwen3.5:4b'
    };

    // 使用流式输出
    isStreaming.value = true;
    streamingContent.value = '';
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
      throw new Error(`API错误: ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    // 保存当前消息的元数据(搜索结果)
    let currentSources = [];
    
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value, { stream: true });
      
      // 检查是否为JSON格式数据
      try {
        // 尝试将整个chunk作为JSON解析
        if (chunk.trim().startsWith('{') && chunk.includes('sources')) {
          const jsonData = JSON.parse(chunk.trim());
          if (jsonData.sources && Array.isArray(jsonData.sources)) {
            // 已找到搜索结果，存储它们
            currentSources = jsonData.sources;
            console.log('收到搜索结果:', currentSources);
            continue; // 不将元数据添加到显示内容
          }
        }
      } catch (e) {
        console.warn('解析JSON数据失败，作为普通文本处理');
      }
      
      // 处理普通文本内容
      streamingContent.value += chunk;
      
      // 自动滚动到底部
      scrollToBottom();
    }
    
    // 完成流式输出后，获取搜索结果和更新图谱
    if (webSearchEnabled.value) {
      // 尝试从响应中提取搜索结果
      // 包含网络搜索结果的可能格式：
      // 1. "网络搜索结果:" 格式
      // 2. "【网络搜索回答】" 格式
      let searchResultsFound = false;
      
      // 方法1：直接从服务器获取搜索结果
      try {
        const searchResponse = await fetch('/api/knowledge-chat/latest-search?query=' + encodeURIComponent(message));
        const searchData = await searchResponse.json();
        if (searchData && searchData.results && searchData.results.length > 0) {
          searchResults.value = searchData.results;
          searchResultsFound = true;
        }
      } catch (e) {
        console.error('获取搜索结果失败:', e);
      }
      
      // 方法2：从回答内容中解析（备用方案）
      if (!searchResultsFound) {
        // 尝试匹配【网络搜索回答】格式
        if (streamingContent.value.includes('【网络搜索回答】')) {
          const searchResultsPattern = /网络搜索结果:\s*\n([^#]*)/gs;
          const match = searchResultsPattern.exec(streamingContent.value);
          
          if (match && match[1]) {
            // 解析搜索结果链接
            const results = [];
            const linkPattern = /\[(.*?)\]\((.*?)\)\s*\n\s*(.*?)(?=\n\n|\n\d|$)/g;
            let linkMatch;
            
            while ((linkMatch = linkPattern.exec(match[1])) !== null) {
              results.push({
                title: linkMatch[1],
                url: linkMatch[2],
                snippet: linkMatch[3].trim()
              });
            }
            
            if (results.length > 0) {
              searchResults.value = results;
              searchResultsFound = true;
            }
          }
        }
      }
    }
    
    // 获取最新的知识图谱数据
    loadKnowledgeGraph();
    
    // 添加到聊天历史
    chatHistory.value.push({
      role: 'assistant',
      content: streamingContent.value,
      sources: currentSources
    });
    
  } catch (error) {
    console.error('聊天请求失败:', error);
    ElMessage.error('发送消息失败，请重试');
    
    chatHistory.value.push({
      role: 'assistant',
      content: '抱歉，我遇到了一些问题。请稍后再试。'
    });
  } finally {
    isLoading.value = false;
    isStreaming.value = false;
    streamingContent.value = '';
    
    // 自动滚动到底部
    await nextTick();
    scrollToBottom();
  }
};

// 自动滚动到底部
const scrollToBottom = () => {
  if (chatMessagesContainer.value) {
    chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
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
  const nodes = JSON.parse(JSON.stringify(knowledgeGraphData.value.nodes));
  const links = JSON.parse(JSON.stringify(knowledgeGraphData.value.links));
  
  // 创建层级结构
  const hierarchyGroups = {};
  
  // 按组分类节点
  nodes.forEach(node => {
    if (!hierarchyGroups[node.group]) {
      hierarchyGroups[node.group] = [];
    }
    hierarchyGroups[node.group].push(node);
  });
  
  // 给每个组分配一个角度范围，实现扇形布局
  const groupKeys = Object.keys(hierarchyGroups);
  const angleStep = (2 * Math.PI) / groupKeys.length;
  
  // 为每个组预设位置
  groupKeys.forEach((group, i) => {
    const angle = i * angleStep;
    const groupRadius = Math.min(width, height) * 0.35; // 组半径
    const centerX = width / 2 + groupRadius * Math.cos(angle);
    const centerY = height / 2 + groupRadius * Math.sin(angle);
    
    // 计算组内节点的位置
    const nodes = hierarchyGroups[group];
    const nodeRadius = 80; // 节点环绕半径
    
    if (nodes.length === 1) {
      // 如果组内只有一个节点，直接放在中心
      nodes[0].fx = centerX;
      nodes[0].fy = centerY;
    } else {
      // 如果有多个节点，环绕排列
      const nodeAngleStep = (2 * Math.PI) / nodes.length;
      nodes.forEach((node, j) => {
        const nodeAngle = j * nodeAngleStep;
        node.fx = centerX + nodeRadius * Math.cos(nodeAngle);
        node.fy = centerY + nodeRadius * Math.sin(nodeAngle);
      });
    }
  });
  
  // 设置links中的source和target为节点对象引用
  links.forEach(link => {
    // 找到对应的节点
    const sourceNode = nodes.find(node => node.id === link.source);
    const targetNode = nodes.find(node => node.id === link.target);
    
    if (sourceNode && targetNode) {
      link.source = sourceNode;
      link.target = targetNode;
    }
  });
  
  // 创建力导向图 - 使用分组力
  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(150))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("x", d3.forceX(d => d.fx || width/2).strength(d => d.fx ? 0.7 : 0.1))
    .force("y", d3.forceY(d => d.fy || height/2).strength(d => d.fy ? 0.7 : 0.1))
    .force("collision", d3.forceCollide().radius(40)); // 避免节点重叠
  
  // 添加缩放功能
  const zoom = d3.zoom()
    .scaleExtent([0.3, 5])
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
    .data(["default"])
    .enter().append("marker")
    .attr("id", d => `arrow-${d}`)
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 28) // 调整箭头位置
    .attr("refY", 0)
    .attr("markerWidth", 8)
    .attr("markerHeight", 8)
    .attr("orient", "auto")
    .append("path")
    .attr("fill", "#88a0c3")
    .attr("d", "M0,-5L10,0L0,5");
  
  // 添加组区域背景
  const groupAreas = graphGroup.selectAll(".group-area")
    .data(groupKeys)
    .enter()
    .append("g")
    .attr("class", "group-area");
  
  // 为每个组添加背景圈
  groupAreas.append("circle")
    .attr("class", "group-background")
    .attr("r", 120)
    .attr("fill", (d, i) => {
      // 使用更现代的配色方案 - 透明度更低以便看清节点
      const colors = [
        "rgba(93, 138, 168, 0.1)", // 湖蓝色
        "rgba(230, 169, 31, 0.1)",  // 琥珀色
        "rgba(147, 112, 219, 0.1)", // 中紫色
        "rgba(60, 179, 113, 0.1)",  // 中海蓝绿色
        "rgba(255, 99, 71, 0.1)"    // 番茄色
      ];
      return colors[i % colors.length];
    })
    .attr("stroke", (d, i) => {
      const colors = [
        "rgba(93, 138, 168, 0.3)", // 湖蓝色
        "rgba(230, 169, 31, 0.3)",  // 琥珀色
        "rgba(147, 112, 219, 0.3)", // 中紫色
        "rgba(60, 179, 113, 0.3)",  // 中海蓝绿色
        "rgba(255, 99, 71, 0.3)"    // 番茄色
      ];
      return colors[i % colors.length];
    })
    .attr("stroke-width", 2)
    .attr("cx", (d, i) => {
      const angle = i * angleStep;
      const groupRadius = Math.min(width, height) * 0.35;
      return width / 2 + groupRadius * Math.cos(angle);
    })
    .attr("cy", (d, i) => {
      const angle = i * angleStep;
      const groupRadius = Math.min(width, height) * 0.35;
      return height / 2 + groupRadius * Math.sin(angle);
    });
  
  // 添加组标签
  groupAreas.append("text")
    .attr("class", "group-label")
    .attr("x", (d, i) => {
      const angle = i * angleStep;
      const groupRadius = Math.min(width, height) * 0.35;
      return width / 2 + groupRadius * Math.cos(angle);
    })
    .attr("y", (d, i) => {
      const angle = i * angleStep;
      const groupRadius = Math.min(width, height) * 0.35;
      return height / 2 + groupRadius * Math.sin(angle) - 130; // 位于圈上方
    })
    .attr("text-anchor", "middle")
    .attr("fill", "rgba(255,255,255,0.7)")
    .attr("font-size", "14px")
    .attr("font-weight", "bold")
    .text(d => {
      // 获取组名称
      const groupLabels = {
        "1": "智能规划",
        "2": "图像识别",
        "3": "知识库",
        "4": "地点",
        "5": "人物"
      };
      return groupLabels[d] || `组 ${d}`;
    });
  
  // 绘制连接线
  const link = graphGroup.append("g")
    .selectAll("path")
    .data(links)
    .enter().append("path")
    .attr("class", "link")
    .attr("stroke", "#88a0c3")
    .attr("stroke-opacity", 0.6)
    .attr("stroke-width", d => Math.sqrt(d.value) * 1.5)
    .attr("fill", "none")
    .attr("marker-end", "url(#arrow-default)");
  
  // 添加连接线文本
  const linkText = graphGroup.append("g")
    .selectAll("text")
    .data(links)
    .enter().append("text")
    .attr("class", "link-text")
    .attr("fill", "#b3ccf5")
    .attr("font-size", "10px")
    .attr("text-anchor", "middle")
    .attr("dy", -5)
    .text(d => d.label || "");
  
  // 创建节点组
  const node = graphGroup.append("g")
    .selectAll("g")
    .data(nodes)
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
        .attr("r", 18)
        .attr("stroke-width", 3);
      
      // 放大文本
      d3.select(this).select("text")
        .transition()
        .duration(200)
        .attr("font-size", "14px");
      
      // 高亮相关连接
      link.each(function(l) {
        if (l.source.id === d.id || l.target.id === d.id) {
          d3.select(this)
            .transition()
            .duration(200)
            .attr("stroke-opacity", 1)
            .attr("stroke-width", Math.sqrt(l.value) * 2.5);
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
          dataList.append("li")
            .text(`${key}: ${value}`);
        });
      }
    })
    .on("mouseout", function(event, d) {
      // 恢复正常状态
      d3.select(this).select("circle")
        .transition()
        .duration(200)
        .attr("r", d => Math.max(6, 10 + d.label.length / 3))
        .attr("stroke-width", 2);
      
      // 恢复文本大小
      d3.select(this).select("text")
        .transition()
        .duration(200)
        .attr("font-size", "12px");
      
      // 恢复连接线状态
      link.transition()
        .duration(200)
        .attr("stroke-opacity", 0.6)
        .attr("stroke-width", l => Math.sqrt(l.value) * 1.5);
      
      // 移除提示框
      d3.select(graphContainer.value).selectAll(".graph-tooltip").remove();
    });
  
  // 为节点添加光晕效果
  node.append("circle")
    .attr("class", "glow")
    .attr("r", d => Math.max(8, 12 + d.label.length / 3) + 4)
    .attr("fill", "rgba(255, 255, 255, 0.1)")
    .attr("filter", "url(#glow)");
  
  // 添加节点圆圈
  node.append("circle")
    .attr("r", d => Math.max(6, 10 + d.label.length / 3)) // 根据文本长度调整大小
    .attr("fill", d => {
      // 使用更现代的配色方案
      const colors = [
        "#5D8AA8", // 湖蓝色
        "#E6A91F", // 琥珀色
        "#9370DB", // 中紫色
        "#3CB371", // 中海蓝绿色
        "#FF6347"  // 番茄色
      ];
      return colors[(d.group - 1) % colors.length];
    })
    .attr("stroke", "#fff")
    .attr("stroke-width", 2);
  
  // 添加渐变滤镜
  const defs = svg.append("defs");
  const filter = defs.append("filter")
    .attr("id", "glow")
    .attr("x", "-50%")
    .attr("y", "-50%")
    .attr("width", "200%")
    .attr("height", "200%");
  
  filter.append("feGaussianBlur")
    .attr("stdDeviation", "2.5")
    .attr("result", "coloredBlur");
  
  const feMerge = filter.append("feMerge");
  feMerge.append("feMergeNode").attr("in", "coloredBlur");
  feMerge.append("feMergeNode").attr("in", "SourceGraphic");
  
  // 添加节点标签
  node.append("text")
    .attr("dx", d => Math.max(8, 12 + d.label.length / 3) + 5) // 文本位置根据节点大小调整
    .attr("dy", ".35em")
    .text(d => d.label || d.id)
    .attr("fill", "#fff")
    .attr("font-family", "Arial, sans-serif")
    .attr("font-size", "12px")
    .attr("text-shadow", "0 1px 3px rgba(0,0,0,0.7)");
  
  // 添加节点悬停效果
  node.append("title")
    .text(d => {
      if (d.data && Object.keys(d.data).length > 0) {
        return Object.entries(d.data)
          .map(([key, value]) => `${key}: ${value}`)
          .join('\n');
      }
      return d.label || d.id;
    });
  
  // 更新位置
  simulation.on("tick", () => {
    // 更新组背景位置
    groupAreas.select(".group-background")
      .attr("cx", (d, i) => {
        const angle = i * angleStep;
        const groupRadius = Math.min(width, height) * 0.35;
        return width / 2 + groupRadius * Math.cos(angle);
      })
      .attr("cy", (d, i) => {
        const angle = i * angleStep;
        const groupRadius = Math.min(width, height) * 0.35;
        return height / 2 + groupRadius * Math.sin(angle);
      });
    
    // 更新组标签位置  
    groupAreas.select(".group-label")
      .attr("x", (d, i) => {
        const angle = i * angleStep;
        const groupRadius = Math.min(width, height) * 0.35;
        return width / 2 + groupRadius * Math.cos(angle);
      })
      .attr("y", (d, i) => {
        const angle = i * angleStep;
        const groupRadius = Math.min(width, height) * 0.35;
        return height / 2 + groupRadius * Math.sin(angle) - 130;
      });
    
    // 更新连接线路径
    link.attr("d", d => {
      const dx = d.target.x - d.source.x,
            dy = d.target.y - d.source.y,
            dr = Math.sqrt(dx * dx + dy * dy) * 1.5; // 弧度
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
      d.x = Math.max(20, Math.min(width - 20, d.x));
      d.y = Math.max(20, Math.min(height - 20, d.y));
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
    
    // 如果是分组的初始节点，保持固定位置
    const isGroupNode = hierarchyGroups[d.group] && 
                        hierarchyGroups[d.group].indexOf(d) !== -1;
    
    // 非组内核心节点则释放固定位置
    if (!isGroupNode) {
      d.fx = null;
      d.fy = null;
    }
  }
};

// 加载知识图谱数据
const loadKnowledgeGraph = async () => {
  try {
    const response = await knowledgeChatApi.getKnowledgeGraph();
    if (response && response.nodes && response.links) {
      knowledgeGraphData.value = response;
      initKnowledgeGraph();
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
  ElMessage.success('已清除聊天历史');
};

// 清除所有内容
const clearAll = () => {
  clearChatHistory();
  resetGraph();
  ElMessage.success('已清除所有内容');
};
</script>

<template>
  <div class="knowledge-chat-container">
    <div class="chat-section">
      <div class="chat-header">
        <h2>知识库聊天</h2>
        <div class="search-toggle">
          <span>联网搜索</span>
          <el-switch
            v-model="webSearchEnabled"
            active-color="#13ce66"
            inactive-color="#ff4949"
          ></el-switch>
        </div>
      </div>

      <div class="chat-messages" ref="chatMessagesContainer">
        <div v-for="(message, index) in chatHistory" :key="index" 
          :class="['message', message.role]">
          <div class="message-avatar">
            <el-avatar :icon="message.role === 'user' ? UserFilled : Service" 
              :size="40"
              :class="message.role">
            </el-avatar>
          </div>
          <div class="message-content">
            <div v-if="message.role === 'assistant' && message.content" 
              v-html="formatMarkdown(message.content)"
              class="markdown-content"
              :class="{'thinking-content': message.content.includes('## 思考过程')}">
            </div>
            <div v-else>
              {{ message.content }}
            </div>
            <div v-if="message.sources && message.sources.length > 0" class="sources-section">
              <div class="source-title">相关信息来源:</div>
              <div class="source-links">
                <div v-for="(source, sourceIdx) in message.sources" 
                  :key="sourceIdx" class="source-item">
                  <a :href="source.url" class="source-link" target="_blank" rel="noopener noreferrer">
                    {{ source.title || source.url }}
                  </a>
                  <div class="source-snippet">{{ source.snippet }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div v-if="isStreaming" class="message assistant">
          <div class="message-avatar">
            <el-avatar :icon="Service" :size="40" class="assistant"></el-avatar>
          </div>
          <div class="message-content">
            <div v-html="formatMarkdown(streamingContent)" class="markdown-content streaming"></div>
          </div>
        </div>
      </div>

      <div class="chat-input">
        <el-input
          v-model="userInput"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 4 }"
          placeholder="输入您的问题..."
          @keyup.enter="sendMessage"
        >
          <template #append>
            <el-button type="primary" @click="sendMessage" :loading="isLoading">
              发送
            </el-button>
          </template>
        </el-input>
      </div>
    </div>

    <div class="knowledge-graph-section">
      <div class="graph-header">
        <h2>知识图谱</h2>
        <div class="graph-controls">
          <el-button size="small" type="primary" @click="showSelectRecordsDialog">
            选择记录
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
</template>

<style scoped>
.knowledge-chat-container {
  display: flex;
  height: 100vh;
  max-height: 100vh;
  background: rgb(20, 20, 30);
  color: white;
}

.chat-section {
  flex: 3;
  display: flex;
  flex-direction: column;
  height: 100%;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
  padding: 1rem;
}

.knowledge-graph-section {
  flex: 2;
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 1rem;
}

.chat-header,
.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.graph-controls {
  display: flex;
  gap: 10px;
}

.search-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message {
  display: flex;
  max-width: 95%;
  gap: 10px;
  animation: fadeIn 0.3s ease-in-out;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.message-avatar .el-avatar.user {
  background: #1989fa;
}

.message-avatar .el-avatar.assistant {
  background: #67c23a;
}

.message-content {
  background: rgba(255, 255, 255, 0.05);
  padding: 12px 16px;
  border-radius: 8px;
  max-width: calc(100% - 60px);
}

.message.user .message-content {
  background: rgba(25, 137, 250, 0.1);
}

.message.assistant .message-content {
  background: rgba(103, 194, 58, 0.1);
}

.sources-section {
  margin-top: 10px;
  padding: 10px;
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.source-links {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.source-item {
  padding: 12px;
  background-color: rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: all 0.3s ease;
}

.source-item:hover {
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
  transform: translateY(-2px);
}

.source-link {
  color: #409eff;
  text-decoration: none;
  display: block;
  font-weight: bold;
  margin-bottom: 6px;
  font-size: 15px;
  border-bottom: 1px dotted #409eff;
  transition: all 0.2s ease;
  width: fit-content;
}

.source-link:hover {
  color: #66b1ff;
  text-decoration: none;
  border-bottom: 1px solid #66b1ff;
}

.source-snippet {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.5;
  background-color: rgba(255, 255, 255, 0.03);
  padding: 8px;
  border-radius: 4px;
  border-left: 2px solid rgba(255, 255, 255, 0.2);
}

.chat-input {
  padding: 12px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.graph-container {
  flex-grow: 1;
  background-color: #1a2236;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}

/* Markdown 样式 */
.markdown-content :deep(pre) {
  background: rgba(0, 0, 0, 0.2);
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}

.markdown-content :deep(code) {
  background: rgba(0, 0, 0, 0.2);
  padding: 2px 4px;
  border-radius: 3px;
}

.markdown-content :deep(a) {
  color: #1989fa;
  text-decoration: none;
  font-weight: bold;
  border-bottom: 1px dotted #1989fa;
  transition: all 0.2s ease;
}

.markdown-content :deep(a:hover) {
  color: #36adff;
  text-decoration: none;
  border-bottom: 1px solid #36adff;
}

.thinking-content {
  position: relative;
  padding-left: 12px;
  font-size: 0.95em;
  color: rgba(255, 255, 255, 0.7);
  border-left: 3px solid rgba(255, 140, 0, 0.6);
  background-color: rgba(30, 30, 30, 0.3);
}

.thinking-content :deep(h1) {
  font-size: 1.2em;
  color: #ff9933;
  margin-bottom: 8px;
  margin-top: 8px;
}

.thinking-content :deep(h2) {
  font-size: 1.2em;
  color: #ff9933;
  margin-bottom: 8px;
  margin-top: 8px;
  border-bottom: 1px solid rgba(255, 140, 0, 0.4);
  padding-bottom: 4px;
}

.markdown-content :deep(h2) {
  font-size: 1.3em;
  color: #67c23a;
  margin-bottom: 12px;
  margin-top: 16px;
  border-bottom: 1px solid rgba(103, 194, 58, 0.4);
  padding-bottom: 4px;
}

.link {
  transition: stroke-opacity 0.3s, stroke-width 0.3s;
}

.link:hover {
  stroke-opacity: 1;
  stroke-width: 3;
}

.node {
  cursor: pointer;
}

.link-text {
  pointer-events: none;
  user-select: none;
  text-shadow: 0 1px 2px rgba(0,0,0,0.8);
}

.select-records-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.record-selection-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.record-selection-group h3 {
  margin: 0;
  color: #409eff;
  font-size: 16px;
}

.record-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.record-option-title {
  font-weight: bold;
}

.record-option-date {
  font-size: 12px;
  color: #999;
}

.select-records-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
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

@keyframes pulse {
  0% {
    border-right: 3px solid rgba(103, 194, 58, 0);
  }
  50% {
    border-right: 3px solid rgba(103, 194, 58, 0.7);
  }
  100% {
    border-right: 3px solid rgba(103, 194, 58, 0);
  }
}
</style>
