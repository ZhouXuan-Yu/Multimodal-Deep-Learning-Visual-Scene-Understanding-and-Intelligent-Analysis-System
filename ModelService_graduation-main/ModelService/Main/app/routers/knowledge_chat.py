"""
无人机知识图谱聊天和检索模块

这个模块提供了与无人机知识图谱交互的API，以及基于知识图谱的聊天功能
"""
import os
import re
import json
import random
import logging
import time
import asyncio
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, Query, Body, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, JSONResponse
import requests
import duckduckgo_search as ddg_search
from neo4j import GraphDatabase
import numpy as np

# 设置模块级别的标志 - 直接禁用高级依赖
SENTENCE_TRANSFORMERS_AVAILABLE = False
FAISS_AVAILABLE = False

# 不再尝试导入这些库
print("⚠️ 使用简单关键词搜索替代sentence_transformers")
print("⚠️ 使用模拟向量索引替代faiss")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Neo4j连接类定义
class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        if self.driver:
            self.driver.close()
            
    def query(self, query, parameters=None):
        if not parameters:
            parameters = {}
            
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]
    
    def search_in_graph(self, query_text, limit=5):
        keywords = query_text.lower().split()
        results = []
        
        try:
            # 简化的Cypher查询 - 基于关键词匹配
            cypher_query = """
            MATCH (n)
            WHERE any(keyword IN $keywords WHERE toLower(n.name) CONTAINS keyword 
                  OR toLower(coalesce(n.description,'')) CONTAINS keyword)
            RETURN n
            LIMIT $limit
            """
            
            records = self.query(cypher_query, {"keywords": keywords, "limit": limit})
            
            for record in records:
                if 'n' in record:
                    node = record['n']
                    results.append({
                        "text": f"{node.get('name', 'Unknown')}: {node.get('description', '')}",
                        "id": node.get('id', node.get('name', 'unknown')),
                        "type": node.get('type', 'unknown')
                    })
            
            return results
        except Exception as e:
            logger.error(f"Neo4j搜索失败: {str(e)}")
            return []
    
    def get_knowledge_graph(self, node_limit=100, relationship_limit=200):
        try:
            # 获取节点
            nodes_query = """
            MATCH (n)
            RETURN n
            LIMIT $limit
            """
            
            nodes_result = self.query(nodes_query, {"limit": node_limit})
            
            # 获取关系
            rels_query = """
            MATCH (n)-[r]->(m)
            RETURN n.name as source, m.name as target, type(r) as label
            LIMIT $limit
            """
            
            rels_result = self.query(rels_query, {"limit": relationship_limit})
            
            # 构建图谱数据
            graph = {"nodes": [], "links": []}
            
            for record in nodes_result:
                if 'n' in record:
                    node = record['n']
                    graph["nodes"].append({
                        "id": node.get('name', node.get('id', f"node_{random.randint(1000, 9999)}")),
                        "label": node.get('name', "未命名"),
                        "group": 1,
                        "data": {k: v for k, v in node.items() if k not in ['id', 'name']}
                    })
            
            for rel in rels_result:
                graph["links"].append({
                    "source": rel.get('source', ""),
                    "target": rel.get('target', ""),
                    "value": 1,
                    "label": rel.get('label', "")
                })
            
            return graph
        except Exception as e:
            logger.error(f"获取知识图谱失败: {str(e)}")
            # 返回空图谱
            return {"nodes": [], "links": []}
    
    def add_knowledge(self, node_data, links_data=None):
        try:
            # 添加节点
            node_query = """
            MERGE (n:{label} {{name: $name}})
            ON CREATE SET n += $props
            RETURN n
            """.format(label=node_data.get('type', 'Concept'))
            
            props = {k: v for k, v in node_data.items() if k not in ['type']}
            props['name'] = node_data.get('label', node_data.get('id', 'Unknown'))
            
            self.query(node_query, {"name": props['name'], "props": props})
            
            # 添加关系
            if links_data:
                for link in links_data:
                    rel_query = """
                    MATCH (a {{name: $source}})
                    MATCH (b {{name: $target}})
                    MERGE (a)-[r:{rel_type}]->(b)
                    RETURN r
                    """.format(rel_type=link.get('label', 'RELATED_TO'))
                    
                    self.query(rel_query, {
                        "source": link.get('source', ""),
                        "target": link.get('target', "")
                    })
            
            return True
        except Exception as e:
            logger.error(f"添加知识到图谱失败: {str(e)}")
            return False

# 重要：正确注册路由对象，确保前缀与前端请求匹配
router = APIRouter(prefix="/knowledge-chat")

# Neo4j连接配置 
# 使用bolt协议而不是neo4j协议，解决路由信息检索问题
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "123"

class KnowledgeChatRequest(BaseModel):
    message: str = Field(..., description="用户发送的消息")
    model: str = Field(default="qwen2.5:3b", description="使用的模型名称")
    temperature: float = Field(default=0.7, ge=0, le=1, description="温度参数")
    web_search: bool = Field(default=False, description="是否使用联网搜索")
    knowledge_graph_search: bool = Field(default=False, description="是否使用知识图谱搜索")
    local_model_search: bool = Field(default=False, description="是否使用本地模型搜索")

class KnowledgeNode(BaseModel):
    id: str
    label: str
    group: int = 1
    data: Dict[str, Any] = Field(default_factory=dict)

class KnowledgeLink(BaseModel):
    source: str
    target: str
    value: int = 1
    label: Optional[str] = None

class KnowledgeGraph(BaseModel):
    nodes: List[KnowledgeNode] = Field(default_factory=list)
    links: List[KnowledgeLink] = Field(default_factory=list)

# 本地向量检索模型配置
LOCAL_MODEL_PATH = os.path.join(os.path.dirname(__file__), "../models/sentence_transformer")
FAISS_INDEX_PATH = os.path.join(os.path.dirname(__file__), "../data/faiss_indexes/drones_knowledge.index")
FAISS_DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/faiss_indexes/drones_knowledge_data.json")

# 加载本地向量检索模型
local_model = None
faiss_index = None
faiss_data = None

# 存储最新搜索结果的全局变量
latest_search_results = {}
latest_graph_results = {}
latest_local_model_results = {}

# 初始化Neo4j连接
neo4j_connection = None
try:
    neo4j_connection = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    logger.info("✅ 成功连接Neo4j数据库")
except Exception as e:
    logger.error(f"❌ 无法连接Neo4j数据库: {str(e)}")
    logger.warning("无人机知识图谱功能将不可用，但不影响其他功能")

def load_local_model():
    global local_model, faiss_index, faiss_data
    
    logger.warning("使用简单关键词匹配替代向量搜索")
    
    try:
        # 加载基本知识数据作为备用
        try:
            faiss_data_path = os.path.join(os.path.dirname(__file__), "../static/night_detection/models/drones_knowledge_graph.json")
            if not os.path.exists(faiss_data_path):
                # 尝试在不同位置查找
                faiss_data_path = os.path.join(os.path.dirname(__file__), "../../static/night_detection/models/drones_knowledge_graph.json")
            
            if os.path.exists(faiss_data_path):
                with open(faiss_data_path, 'r', encoding='utf-8') as f:
                    graph_data = json.load(f)
            
                # 创建简单的假数据结构
                faiss_data = []
                
                # 处理无人机数据
                for drone in graph_data.get('drones', []):
                    faiss_data.append({
                        "id": drone.get('model'),
                        "text": f"无人机模型: {drone.get('model')} - {drone.get('description', '')}",
                        "category": "drone",
                        "node_type": "无人机",
                        "data": drone
                    })
                
                # 处理品牌数据
                for brand in graph_data.get('brands', []):
                    faiss_data.append({
                        "id": brand.get('name'),
                        "text": f"无人机品牌: {brand.get('name')} - {brand.get('description', '')}",
                        "category": "brand",
                        "node_type": "品牌",
                        "data": brand
                    })
                
                logger.info(f"加载了 {len(faiss_data)} 条备用知识数据")
                return True
            else:
                # 如果找不到实际文件，使用模拟数据
                logger.warning("找不到知识图谱数据文件，使用模拟数据")
                faiss_data = [
                    {
                        "id": "DJI Mavic 3",
                        "text": "无人机模型: DJI Mavic 3 - 高端消费级无人机，配备哈苏相机",
                        "category": "drone",
                        "node_type": "无人机"
                    },
                    {
                        "id": "DJI",
                        "text": "无人机品牌: DJI - 全球领先的无人机制造商",
                        "category": "brand",
                        "node_type": "品牌"
                    }
                ]
                logger.info("使用2条模拟知识数据")
                return True
        except Exception as e:
            logger.error(f"创建备用数据失败: {str(e)}")
            # 使用极简数据
            faiss_data = [
                {
                    "id": "模拟数据",
                    "text": "这是一条模拟的知识库数据，用于测试功能",
                    "category": "test",
                    "node_type": "测试"
                }
            ]
            return True
    except Exception as e:
        logger.error(f"加载本地模型失败: {str(e)}")
        return False
    
def perform_local_model_search(query, num_results=5):
    """使用本地模型对知识库进行语义搜索"""
    global latest_local_model_results
    
    try:
        logger.info(f"执行关键词搜索: {query}")
            
        # 加载数据（如果尚未加载）
        if faiss_data is None:
            success = load_local_model()
            if not success:
                logger.error("加载备用数据失败")
                return []
        
        # 简单的关键词匹配
        keywords = query.lower().split()
        matched_results = []
        
        for item in faiss_data:
            text = item.get("text", "").lower()
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            
            if score > 0:
                # 添加相关度分数
                item_copy = item.copy()
                item_copy["relevance"] = score / len(keywords)
                matched_results.append(item_copy)
        
        # 按相关度排序
        matched_results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        
        # 保存最新结果
        latest_local_model_results[query] = {
            "query": query,
            "results": matched_results[:num_results]
        }
        
        logger.info(f"找到 {len(matched_results[:num_results])} 条匹配结果")
        return matched_results[:num_results]
    except Exception as e:
        logger.error(f"关键词搜索失败: {str(e)}")
        return []

# DuckDuckGo搜索
def perform_web_search(query, num_results=3):
    """使用DuckDuckGo进行网络搜索"""
    global latest_search_results
    try:
        logger.info(f"执行网络搜索: {query}")
        
        # 尝试使用DuckDuckGo搜索
        try:
            logger.info("使用DuckDuckGo搜索...")
            search_results = ddg_search.DDGS().text(query, max_results=num_results)
            if search_results and len(search_results) > 0:
                logger.info(f"DuckDuckGo搜索成功，获取到 {len(search_results)} 条结果")
                
                # 储存搜索结果
                latest_search_results[query] = search_results
                return search_results
        except Exception as e:
            logger.warning(f"DuckDuckGo搜索失败: {str(e)}")
        
        # 尝试使用备用搜索API
        try:
            # 备用方案：使用简单的HTTP请求访问DuckDuckGo API
            logger.info("使用备用DuckDuckGo API...")
            base_url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json"
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = []
                
                # 处理可能的结果结构
                if "AbstractText" in data and data["AbstractText"]:
                    results.append({
                        "title": data.get("Heading", "DuckDuckGo结果"),
                        "href": data.get("AbstractURL", ""),
                        "body": data["AbstractText"]
                    })
                
                # 处理相关话题
                if "RelatedTopics" in data:
                    for topic in data["RelatedTopics"][:num_results-len(results)]:
                        if "Text" in topic and "FirstURL" in topic:
                            results.append({
                                "title": topic.get("Text", "").split(" - ")[0],
                                "href": topic.get("FirstURL", ""),
                                "body": topic.get("Text", "")
                            })
                
                if results:
                    logger.info(f"备用DuckDuckGo搜索成功，获取到 {len(results)} 条结果")
                    
                    # 储存搜索结果
                    latest_search_results[query] = results
                    return results
        except Exception as e:
            logger.warning(f"备用DuckDuckGo搜索失败: {str(e)}")
        
        # 使用硬编码的基本结果作为最后手段
        logger.warning("所有搜索方法都失败，使用硬编码的基本回答")
        basic_results = [
            {
                "title": "基本搜索结果",
                "href": "",
                "body": f"关于'{query}'的搜索功能暂不可用，但我可以尝试回答这个问题。"
            }
        ]
        latest_search_results[query] = basic_results
        return basic_results
        
    except Exception as e:
        logger.error(f"网络搜索失败: {str(e)}")
        # 返回空结果而不是抛出异常
        return []

# 流式响应
import os

def stream_ollama_response(messages, model: str = None, temperature=0.7, search_results=None):
    """流式输出Ollama API响应"""
    try:
        # 首先发送搜索结果作为元数据
        if search_results:
            sources = []
            if isinstance(search_results, list):
                # 如果已经是标准格式的列表
                sources = search_results
            else:
                # 兼容旧格式：将字符串转换为列表
                sources.append({
                    "title": "搜索结果",
                    "snippet": search_results,
                    "url": ""
                })
                
            # 发送元数据
            meta_json = json.dumps({
                "sources": sources
            })
            yield f"{meta_json}\n\n"
        
        # 添加搜索结果到消息中
        if search_results:
            search_content = "以下是相关信息搜索结果：\n\n"
            
            if isinstance(search_results, list):
                for idx, result in enumerate(search_results):
                    title = result.get("title", f"结果 {idx+1}")
                    body = result.get("snippet", "")
                    url = result.get("url", "")
                
                    search_content += f"【{title}】\n{body}\n{url}\n\n"
            else:
                search_content += search_results
            
            # 添加搜索结果到系统消息
            messages.append({
                "role": "system",
                "content": search_content
            })
            
            # 添加指令，要求模型先思考再回答
            messages.append({
                "role": "system",
                "content": """必须严格按照以下格式回答问题，这是关键要求：

第一部分必须以"## 思考过程"（两个井号+空格+思考过程）作为标题开始。
第二部分必须以"## 正式回答"（两个井号+空格+正式回答）作为标题开始。

格式示例：
## 思考过程
[在这里详细分析信息]

## 正式回答
[在这里给出最终答案]

这种格式至关重要，请必须遵守。不要使用其他格式或标题替代。"""
            })
        
        # 准备Ollama API调用，支持通过环境变量配置地址和默认模型
        env_ollama = os.getenv("OLLAMA_URL") or os.getenv("OLLAMA_BASE") or "http://localhost:11434"
        base = env_ollama.split("/api")[0].rstrip("/")
        api_url = f"{base}/api/chat"
        headers = {"Content-Type": "application/json"}
        model_to_use = model or os.getenv("OLLAMA_MODEL") or "qwen3-vl"

        data = {
            "model": model_to_use,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }
        
        # 发送请求并流式处理响应
        response = requests.post(api_url, json=data, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        
        # 记录完整响应
        full_content = ""
        
        # 处理模型输出
        for line in response.iter_lines():
            if line:
                # 解析JSON响应
                try:
                    chunk = json.loads(line)
                    if "message" in chunk:
                        content = chunk["message"].get("content", "")
                        if content:
                            full_content += content
                            yield content
                except json.JSONDecodeError:
                    logger.warning(f"无法解析JSON: {line}")
        
        # 强制格式化全部内容，确保标题格式正确
        if full_content and not ("## 思考过程" in full_content and "## 正式回答" in full_content):
            # 尝试查找思考过程和正式回答的分隔点
            
            # 定义可能的分隔标记，按优先级排序
            delimiters = [
                "正式回答", "以下是我的回答", "下面是我的回答", 
                "总结一下", "综上所述", "因此，", "所以，",
                "根据以上信息", "根据提供的信息",
                "\n\n思考过程\n", "\n思考过程\n", "思考过程：", "思考：",
                "\n\n正式回答\n", "\n正式回答\n", "正式回答：", "回答："
            ]
            
            # 查找最佳分隔点
            best_delimiter = None
            best_position = -1
            
            for delimiter in delimiters:
                position = full_content.find(delimiter)
                # 确保分隔点不在开头附近，至少在20%之后
                if position > len(full_content) * 0.2 and (best_position == -1 or position < best_position):
                    best_delimiter = delimiter
                    best_position = position
            
            # 如果找到好的分隔点
            if best_position > 0:
                # 分割内容
                thinking = full_content[:best_position].strip()
                answer = full_content[best_position:].strip()
                
                # 对于某些分隔符，我们需要调整答案部分
                if best_delimiter in ["总结一下", "综上所述", "因此，", "所以，", "根据以上信息", "根据提供的信息"]:
                    # 这些分隔符应该是思考的一部分，而不是答案的开头
                    thinking = full_content[:best_position + len(best_delimiter)].strip()
                    answer = full_content[best_position + len(best_delimiter):].strip()
                
                # 清除之前的输出
                yield "\n\n===重新格式化内容===\n\n"
                
                # 发送正确格式的思考部分
                yield "## 思考过程\n\n"
                yield thinking
                
                # 发送正确格式的回答部分
                yield "\n\n## 正式回答\n\n"
                yield answer
            else:
                # 如果找不到好的分隔点，使用简单的二分法
                mid_point = len(full_content) // 2
                
                # 找到最近的段落分隔符
                paragraph_break = full_content.find("\n\n", mid_point)
                if paragraph_break == -1 or paragraph_break > mid_point + 200:  # 如果找不到或太远
                    paragraph_break = mid_point
                
                thinking = full_content[:paragraph_break].strip()
                answer = full_content[paragraph_break:].strip()
                
                # 清除之前的输出
                yield "\n\n===重新格式化内容===\n\n"
                
                # 发送正确格式的思考部分
                yield "## 思考过程\n\n"
                yield thinking
                
                # 发送正确格式的回答部分
                yield "\n\n## 正式回答\n\n"
                yield answer
        # 如果没有任何响应，发送错误消息
        if not full_content:
            error_message = "抱歉，无法从语言模型获取回答。请稍后再试。"
            yield error_message
    
    except requests.exceptions.RequestException as req_error:
        # 如果Ollama API请求出错
        error_message = f"抱歉，无法连接到语言模型服务: {str(req_error)}"
        logger.error(error_message)
        yield error_message
    
    except Exception as general_error:
        # 其他异常情况
        error_message = f"抱歉，处理回答时出错: {str(general_error)}"
        logger.error(error_message)
        yield error_message

@router.post("/stream")
async def knowledge_chat_stream(request: Request):
    """知识库聊天流式输出"""
    try:
        # 解析请求
        data = await request.json()
        message = data.get("message", "")
        model = data.get("model", "qwen2.5:3b")
        temperature = data.get("temperature", 0.7)
        web_search = data.get("web_search", False)
        knowledge_graph_search = data.get("knowledge_graph_search", False)
        local_model_search = data.get("local_model_search", False)
        
        logger.info(f"收到知识库聊天请求: {message[:50] if message else ''}...")
        logger.info(f"搜索选项: 联网={web_search}, 知识图谱={knowledge_graph_search}, 本地模型={local_model_search}")
        
        # 存储所有搜索结果
        all_search_results = []
        combined_context = ""
        
        # 1. 从知识图谱中获取相关信息
        graph_results = []
        if knowledge_graph_search and neo4j_connection:
            try:
                logger.info("正在搜索知识图谱...")
                graph_results = neo4j_connection.search_in_graph(message, limit=5)
                # 保存图谱查询结果供前端使用
                if graph_results:
                    latest_graph_results[message] = graph_results
                    logger.info(f"从知识图谱中找到 {len(graph_results)} 条相关信息")
                    
                    # 添加到组合上下文
                    knowledge_context = "\n\n".join([
                        f"--- 知识图谱信息 {i+1} ---\n{result['text'] if isinstance(result, dict) and 'text' in result else str(result)}" 
                        for i, result in enumerate(graph_results)
                    ])
                    combined_context += f"\n\n知识图谱提供的相关信息:\n{knowledge_context}"
                else:
                    logger.info("知识图谱中未找到相关信息")
            except Exception as e:
                logger.error(f"知识图谱搜索出错: {str(e)}")
                # 继续执行，不中断流程
        
        # 2. 使用本地模型进行语义搜索
        local_model_results = []
        if local_model_search:
            try:
                logger.info("正在使用本地模型进行语义搜索...")
                local_model_results = perform_local_model_search(message, num_results=5)
                
                if local_model_results:
                    logger.info(f"本地模型搜索找到 {len(local_model_results)} 条相关信息")
                    
                    # 添加到组合上下文
                    local_model_context = "\n\n".join([
                        f"--- 语义搜索结果 {i+1} ---\n{result.get('text', '')}" 
                        for i, result in enumerate(local_model_results)
                    ])
                    combined_context += f"\n\n本地语义搜索提供的相关信息:\n{local_model_context}"
                else:
                    logger.info("本地模型搜索未找到相关信息")
            except Exception as e:
                logger.error(f"本地模型搜索出错: {str(e)}")
                # 继续执行，不中断流程
        
        # 3. 进行网络搜索（如果启用）
        web_search_results = None
        search_results = []
        if web_search:
            try:
                logger.info("正在进行网络搜索...")
                search_results = perform_web_search(message)
                if search_results:
                    web_search_results = "\n\n".join([
                        f"--- 搜索结果 {i+1} ---\n标题: {result['title']}\n链接: {result['href']}\n摘要: {result['body']}"
                        for i, result in enumerate(search_results)
                    ])
                    # 保存搜索结果以便前端获取
                    latest_search_results[message] = search_results
                    logger.info(f"找到 {len(search_results)} 条网络搜索结果")
                    
                    # 添加网络搜索结果到all_search_results
                    for result in search_results:
                        all_search_results.append({
                            "title": result.get("title", ""),
                            "snippet": result.get("body", ""),
                            "url": result.get("href", "")
                        })
            except Exception as e:
                logger.error(f"网络搜索出错: {str(e)}")
                # 继续执行，不中断流程
        
        # 构建消息历史
        system_message = "你是一个智能助手，结合知识图谱和向量知识库提供专业、准确的回答。"
        user_content = message
        
        # 如果有任何检索结果，将其添加到用户提问中
        if combined_context:
            user_content = f"用户问题: {message}\n{combined_context}\n\n请根据以上信息来回答用户问题。如果提供的信息与问题无关，请主要基于你自己的知识回答。"
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_content}
        ]
        
        # 创建和使用stream生成器
        def stream_generator():
            try:
                # 使用之前定义的stream_ollama_response函数
                for chunk in stream_ollama_response(
                    messages, 
                    model=model, 
                    temperature=temperature, 
                    search_results=all_search_results if all_search_results else None
                ):
                    # 将每个块封装为SSE格式
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                    
                # 发送完成标记
                yield "data: [DONE]\n\n"
            except Exception as e:
                # 在生成器内部捕获异常
                logger.exception(f"流式生成过程中出错: {str(e)}")
                error_message = f"处理请求时出错: {str(e)}"
                yield f"data: {json.dumps({'error': error_message, 'content': error_message})}\n\n"
                yield "data: [DONE]\n\n"
            
        # 返回流式响应
            return StreamingResponse(
            stream_generator(),
                media_type="text/event-stream"
            )
    
    except Exception as e:
        # 主函数中的异常处理
        logger.exception(f"知识库聊天请求处理失败: {str(e)}")
        
        # 捕获错误信息到局部变量
        error_message = str(e)
        
        # 返回错误流
        async def error_stream():
            yield f"data: {json.dumps({'error': error_message, 'content': f'很抱歉，处理您的请求时出现了问题: {error_message}'})}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            status_code=200  # 返回200而不是500，让前端能够正常处理错误消息
        )

@router.get("/graph")
async def get_knowledge_graph():
    """获取知识图谱数据"""
    try:
        if neo4j_connection:
            return neo4j_connection.get_knowledge_graph()
        else:
            # 返回示例图谱数据
            return {
                "nodes": [
                    {"id": "智能规划", "label": "智能规划", "group": 1},
                    {"id": "图像识别", "label": "图像识别", "group": 2},
                    {"id": "知识库", "label": "知识库", "group": 3},
                    {"id": "北京", "label": "北京", "group": 4},
                    {"id": "上海", "label": "上海", "group": 4}
                ],
                "links": [
                    {"source": "知识库", "target": "智能规划", "value": 1},
                    {"source": "知识库", "target": "图像识别", "value": 1},
                    {"source": "智能规划", "target": "北京", "value": 1},
                    {"source": "智能规划", "target": "上海", "value": 1}
                ]
            }
    except Exception as e:
        logger.error(f"获取知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/graph/add")
async def add_to_knowledge_graph(node: KnowledgeNode, links: List[KnowledgeLink] = None):
    """添加节点和连接到知识图谱"""
    try:
        if neo4j_connection:
            node_data = {
                "id": node.id,
                "label": node.label,
                "type": "Concept",
                "data": node.data
            }
            
            links_data = []
            if links:
                for link in links:
                    links_data.append({
                        "source": link.source,
                        "target": link.target,
                        "label": link.label or "RELATED_TO"
                    })
            
            success = neo4j_connection.add_knowledge(node_data, links_data)
            if success:
                return {"success": True, "data": neo4j_connection.get_knowledge_graph()}
            
        raise HTTPException(status_code=500, detail="添加知识到图谱失败")
    except Exception as e:
        logger.error(f"添加知识图谱节点失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest-search")
async def get_latest_search_results(query: str):
    """获取最新的搜索结果"""
    global latest_search_results
    if query in latest_search_results:
        return {"results": latest_search_results[query]}
    return {"results": []}

@router.get("/latest-graph")
async def get_latest_graph_results(query: str):
    """获取最新的知识图谱查询结果"""
    global latest_graph_results
    if query in latest_graph_results:
        return {"results": latest_graph_results[query]}
    return {"results": []}

@router.post("/graph/import-drones")
async def import_drone_data(data: dict):
    """导入无人机知识图谱数据"""
    try:
        # 增加详细的日志记录
        logger.info(f"收到无人机数据导入请求，数据大小: {len(str(data))}字节")
        logger.info(f"数据结构: drones={len(data.get('drones', []))}, brands={len(data.get('brands', []))}, relationships={len(data.get('relationships', []))}")
        
        if not neo4j_connection:
            logger.error("Neo4j连接不可用")
            return {"success": False, "error": "Neo4j连接不可用"}
            
        # 统计信息
        stats = {
            "nodes_created": 0,
            "relationships_created": 0,
            "properties_set": 0
        }
        
        # 创建约束和索引（确保唯一性）
        try:
            constraints_query = """
            CREATE CONSTRAINT drone_model_unique IF NOT EXISTS 
            FOR (d:Drone) REQUIRE d.model IS UNIQUE;
            
            CREATE CONSTRAINT brand_name_unique IF NOT EXISTS 
            FOR (b:Brand) REQUIRE b.name IS UNIQUE;
            
            CREATE INDEX part_type_index IF NOT EXISTS 
            FOR (p:Part) ON (p.type);
            """
            neo4j_connection.query(constraints_query)
            logger.info("创建Neo4j约束和索引成功")
        except Exception as e:
            logger.warning(f"创建Neo4j约束和索引失败: {str(e)}")
        
        # 创建无人机节点
        for drone in data.get('drones', []):
            drone_query = """
            MERGE (d:Drone {model: $model})
            ON CREATE SET d.brand = $brand,
                          d.flight_time = $flight_time,
                          d.max_speed = $max_speed,
                          d.max_flight_distance = $max_flight_distance,
                          d.takeoff_weight = $takeoff_weight,
                          d.id = $model,
                          d.label = $model,
                          d.type = 'Drone',
                          d.name = $model
            RETURN count(d) as count
            """
            result = neo4j_connection.query(drone_query, drone)
            stats["nodes_created"] += result[0]["count"]
            stats["properties_set"] += 7
        
        # 创建品牌节点
        for brand in data.get('brands', []):
            brand_query = """
            MERGE (b:Brand {name: $name})
            ON CREATE SET b.founded = $founded,
                          b.headquarters = $headquarters,
                          b.id = $name,
                          b.label = $name,
                          b.type = 'Brand',
                          b.name = $name
            RETURN count(b) as count
            """
            result = neo4j_connection.query(brand_query, brand)
            stats["nodes_created"] += result[0]["count"]
            stats["properties_set"] += 6
        
        # 创建部件节点 - 收集所有唯一部件
        all_parts = set()
        for drone in data.get('drones', []):
            all_parts.update(drone.get('parts', []))
        
        for part in all_parts:
            part_query = """
            MERGE (p:Part {type: $type})
            ON CREATE SET p.name = $type,
                         p.id = $type,
                         p.label = $type,
                         p.type = 'Component'
            RETURN count(p) as count
            """
            result = neo4j_connection.query(part_query, {"type": part})
            stats["nodes_created"] += result[0]["count"]
            stats["properties_set"] += 4
        
        # 创建关系
        for rel in data.get('relationships', []):
            if rel.get('relationship_type') == 'BRAND':
                rel_query = """
                MATCH (d:Drone {model: $drone_model})
                MATCH (b:Brand {name: $brand_name})
                MERGE (d)-[r:BRAND_OF]->(b)
                RETURN count(r) as count
                """
                result = neo4j_connection.query(rel_query, {
                    "drone_model": rel.get('drone_model'),
                    "brand_name": rel.get('brand_name')
                })
                stats["relationships_created"] += result[0]["count"]
            
            elif rel.get('relationship_type') == 'HAS_PART':
                rel_query = """
                MATCH (d:Drone {model: $drone_model})
                MATCH (p:Part {type: $part_type})
                MERGE (d)-[r:HAS_PART]->(p)
                RETURN count(r) as count
                """
                result = neo4j_connection.query(rel_query, {
                    "drone_model": rel.get('drone_model'),
                    "part_type": rel.get('part')
                })
                stats["relationships_created"] += result[0]["count"]
        
        # 更新知识图谱缓存
        updated_graph = neo4j_connection.get_knowledge_graph()
        
        # 记录成功信息
        logger.info(f"无人机数据导入成功，统计: {stats}")
        
        return {
            "success": True, 
            "message": "无人机数据导入成功",
            "stats": stats,
            "graph": updated_graph
        }
        
    except Exception as e:
        logger.error(f"导入无人机数据失败: {str(e)}")
        import traceback
        logger.error(f"完整错误: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}

# 添加测试端点
@router.post("/graph/test-import")
@router.get("/graph/test-import")
async def test_import_endpoint():
    """测试知识图谱导入端点是否可访问"""
    logger.info("测试知识图谱导入端点被调用")
    return {
        "success": True,
        "message": "测试端点可访问",
        "neo4j_status": "可用" if neo4j_connection else "不可用"
    }

@router.get("/latest-local-model-results")
async def get_latest_local_model_results(query: str):
    """获取最新的本地模型搜索结果"""
    global latest_local_model_results
    if query in latest_local_model_results:
        return {"results": latest_local_model_results[query]}
    return {"results": []}

# 尝试加载本地模型
load_local_model()
