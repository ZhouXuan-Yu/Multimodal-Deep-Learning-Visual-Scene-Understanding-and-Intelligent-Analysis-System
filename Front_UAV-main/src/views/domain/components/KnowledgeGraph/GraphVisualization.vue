<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue';
import * as d3 from 'd3';

const props = defineProps({
  graphData: {
    type: Object,
    required: true
  },
  width: {
    type: Number,
    default: 800
  },
  height: {
    type: Number,
    default: 600
  }
});

const graphContainer = ref(null);
let simulation = null;
let svg = null;

// 初始化知识图谱可视化
const initGraph = () => {
  if (!graphContainer.value || !props.graphData) return;
  
  // 清空容器
  d3.select(graphContainer.value).selectAll("*").remove();
  
  // 创建SVG容器
  svg = d3.select(graphContainer.value)
    .append("svg")
    .attr("width", props.width)
    .attr("height", props.height)
    .attr("viewBox", [0, 0, props.width, props.height])
    .classed("graph-svg", true);
    
  // 添加箭头定义
  svg.append("defs")
    .append("marker")
    .attr("id", "arrow")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 20)
    .attr("refY", 0)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("fill", "#999")
    .attr("d", "M0,-5L10,0L0,5");
  
  // 创建力导向图
  simulation = d3.forceSimulation(props.graphData.nodes)
    .force("link", d3.forceLink(props.graphData.links).id(d => d.id).distance(100))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(props.width / 2, props.height / 2))
    .force("collide", d3.forceCollide().radius(60));
  
  // 创建连接线
  const link = svg.append("g")
    .selectAll("line")
    .data(props.graphData.links)
    .join("line")
    .attr("stroke", "#999")
    .attr("stroke-opacity", 0.6)
    .attr("stroke-width", d => Math.sqrt(d.value))
    .attr("marker-end", "url(#arrow)");
  
  // 创建节点分组
  const node = svg.append("g")
    .selectAll(".node")
    .data(props.graphData.nodes)
    .join("g")
    .attr("class", "node")
    .call(d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended));
  
  // 添加节点圆圈
  node.append("circle")
    .attr("r", 20)
    .attr("fill", d => getNodeColor(d.group));
  
  // 添加文本标签
  node.append("text")
    .attr("text-anchor", "middle")
    .attr("dy", ".35em")
    .text(d => d.label || d.id)
    .attr("fill", "white");
  
  // 定义力导向图的tick事件
  simulation.on("tick", () => {
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);
    
    node
      .attr("transform", d => `translate(${d.x},${d.y})`);
  });
  
  // 拖拽事件处理函数
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
};

// 根据节点组获取颜色
const getNodeColor = (group) => {
  const colors = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
  ];
  return colors[group % colors.length];
};

// 监听图数据变化重新渲染
watch(() => props.graphData, () => {
  if (props.graphData && props.graphData.nodes && props.graphData.links) {
    initGraph();
  }
}, { deep: true });

onMounted(() => {
  if (props.graphData && props.graphData.nodes && props.graphData.links) {
    initGraph();
  }
});

onUnmounted(() => {
  if (simulation) {
    simulation.stop();
  }
});
</script>

<template>
  <div ref="graphContainer" :style="`width: ${width}px; height: ${height}px;`" class="graph-container">
    <div v-if="!graphData || !graphData.nodes || !graphData.links" class="graph-loading">
      <p>加载知识图谱中...</p>
    </div>
  </div>
</template>

<style scoped>
.graph-container {
  position: relative;
  background-color: #f8fafc;
  border-radius: 0.5rem;
  overflow: hidden;
}

.graph-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  color: #64748b;
}

.graph-svg {
  width: 100%;
  height: 100%;
}

.node {
  cursor: pointer;
}

.node:hover circle {
  stroke: #000;
  stroke-width: 2px;
}

.node text {
  font-size: 12px;
  pointer-events: none;
}
</style>
