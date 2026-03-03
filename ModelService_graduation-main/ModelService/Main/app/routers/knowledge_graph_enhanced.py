"""
知识图谱增强路由 - 提供知识图谱管理和查询接口
支持文档上传、知识检索、图谱可视化和问答等功能
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import os
import json
import logging
import hashlib
import asyncio
from typing import List, Dict, Any, Optional
import time
from datetime import datetime

# 导入自定义服务
from app.services.knowledge_graph_enhanced.vector_store import vector_store
from app.services.knowledge_graph_enhanced.knowledge_graph import knowledge_graph
from app.services.knowledge_graph_enhanced.text_processor import text_processor
from app.services.knowledge_graph_enhanced.ollama_client import ollama_client

# 配置日志
logger = logging.getLogger(__name__)

# 定义数据模型
class KnowledgeNode(BaseModel):
    id: Optional[str] = None
    text: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class KnowledgeRelation(BaseModel):
    source_id: str
    target_id: str
    relation_type: str = "RELATED_TO"
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)

class KnowledgeData(BaseModel):
    nodes: List[KnowledgeNode] = Field(default_factory=list)
    relations: Optional[List[KnowledgeRelation]] = Field(default_factory=list)

# 创建路由
router = APIRouter()

# 兼容旧的知识图谱系统数据模型
class KnowledgeChatRequest(BaseModel):
    message: str = Field(..., description="用户发送的消息")
    model: str = Field(default="qwen2.5:3b", description="使用的模型名称")
    temperature: float = Field(default=0.7, ge=0, le=1, description="温度参数")
    web_search: bool = Field(default=False, description="是否使用联网搜索")

# 路径定义
DOCUMENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "documents")
PROCESSED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed")

# 确保目录存在
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

@router.get("/status")
async def check_status():
    """检查各个组件的状态"""
    return {
        "vector_store": "available" if vector_store else "unavailable",
        "knowledge_graph": "available" if knowledge_graph else "unavailable",
        "text_processor": "available" if text_processor else "unavailable",
        "ollama_client": "available" if ollama_client else "unavailable",
        "documents_dir": os.path.exists(DOCUMENTS_DIR),
        "processed_dir": os.path.exists(PROCESSED_DIR),
        "timestamp": datetime.now().isoformat()
    }

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    description: str = Form(""),
    tags: str = Form("")
):
    """上传文档到知识库"""
    # 验证文件类型
    allowed_extensions = ['.txt', '.md', '.json', '.csv']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_ext}，目前支持: {', '.join(allowed_extensions)}")
    
    # 创建安全的文件名
    safe_filename = f"{int(time.time())}_{file.filename}"
    file_path = os.path.join(DOCUMENTS_DIR, safe_filename)
    
    # 保存上传的文件
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 解析标签
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
    
    # 解析元数据
    metadata = {
        "description": description,
        "tags": tag_list,
        "filename": file.filename,
        "upload_time": datetime.now().isoformat()
    }
    
    # 后台处理文档
    background_tasks.add_task(process_document, file_path, metadata)
    
    return {"message": f"文档 {file.filename} 上传成功，正在后台处理", "file_id": safe_filename}

async def process_document(file_path: str, metadata: Dict[str, Any]):
    """处理文档并添加到知识库"""
    try:
        logger.info(f"开始处理文档: {file_path}")
        
        # 处理文档
        chunks = text_processor.read_and_process_file(file_path)
        
        if not chunks:
            logger.error(f"文档处理失败，未生成文本块: {file_path}")
            return
        
        # 添加到向量存储
        vector_ids = vector_store.add_documents(chunks)
        
        # 添加到知识图谱
        if knowledge_graph:
            # 添加节点
            for chunk in chunks:
                knowledge_graph.add_knowledge_node(
                    chunk["id"],
                    chunk["text"],
                    chunk["metadata"]
                )
            
            # 添加关系
            for i in range(len(chunks) - 1):
                # 添加顺序关系
                knowledge_graph.add_relationship(
                    chunks[i]["id"],
                    chunks[i+1]["id"],
                    "NEXT",
                    {"type": "sequence"}
                )
                
                # 添加来源关系
                if "file_name" in chunks[i]["metadata"]:
                    source = chunks[i]["metadata"]["file_name"]
                    for j in range(i+1, len(chunks)):
                        if chunks[j]["metadata"].get("file_name") == source:
                            knowledge_graph.add_relationship(
                                chunks[i]["id"],
                                chunks[j]["id"],
                                "SAME_SOURCE",
                                {"source": source}
                            )
        
        # 保存处理后的文档块
        text_processor.save_processed_chunks(chunks, PROCESSED_DIR)
        
        logger.info(f"✅ 成功处理文档: {file_path}，添加了{len(chunks)}个文档块")
    except Exception as e:
        logger.error(f"❌ 处理文档失败: {str(e)}")

@router.post("/search")
async def search_knowledge(query: str, limit: int = Query(5, ge=1, le=20)):
    """搜索知识库"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="向量存储服务不可用")
    
    # 向量搜索
    vector_results = vector_store.search(query, k=limit)
    
    # 如果向量搜索没有结果，返回空
    if not vector_results:
        return {"results": [], "graph": None}
    
    # 获取文档ID
    doc_ids = [doc["id"] for doc in vector_results]
    
    # 如果Neo4j可用，获取知识图谱
    graph_data = None
    if knowledge_graph:
        graph_data = knowledge_graph.get_knowledge_graph(doc_ids, depth=1)
    
    return {
        "results": vector_results,
        "graph": graph_data
    }

@router.get("/graph")
async def get_knowledge_graph(
    query: Optional[str] = None,
    node_ids: Optional[str] = None,
    depth: int = Query(2, ge=0, le=3)
):
    """获取知识图谱"""
    if not knowledge_graph:
        raise HTTPException(status_code=503, detail="Neo4j知识图谱服务不可用")
    
    # 如果提供了查询，使用向量搜索找到相关节点
    if query:
        if not vector_store:
            raise HTTPException(status_code=503, detail="向量存储服务不可用")
        # 向量搜索
        vector_results = vector_store.search(query, k=5)
        doc_ids = [doc["id"] for doc in vector_results]
    # 如果提供了节点ID
    elif node_ids:
        doc_ids = node_ids.split(",")
    # 否则返回错误
    else:
        raise HTTPException(status_code=400, detail="必须提供查询或节点ID")
    
    # 获取知识图谱
    graph_data = knowledge_graph.get_knowledge_graph(doc_ids, depth=depth)
    
    return graph_data

@router.get("/graph/{node_id}")
async def get_knowledge_graph_for_node(node_id: str, depth: int = Query(2)):
    """获取以特定节点为中心的知识图谱子图"""
    if not knowledge_graph:
        raise HTTPException(status_code=503, detail="知识图谱服务不可用")
    
    try:
        # 获取以指定节点为中心的子图
        graph_data = knowledge_graph.get_knowledge_graph([node_id], depth=depth)
        # 转换为旧的格式以保持前端兼容性
        old_format = convert_to_old_format(graph_data)
        return old_format
    except Exception as e:
        logger.error(f"获取子图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取知识图谱失败: {str(e)}")

def convert_to_old_format(graph_data):
    """
    将新知识图谱格式转换为旧格式，确保前端兼容性
    """
    old_format = {
        "nodes": [],
        "links": []
    }
    
    # 转换节点
    for node in graph_data.get("nodes", []):
        old_format["nodes"].append({
            "id": node.get("id"),
            "label": node.get("name") or node.get("text") or node.get("id"),
            "group": 1,  # 默认分组
            "data": node.get("metadata") or {}
        })
    
    # 转换关系
    for link in graph_data.get("relationships", []):
        old_format["links"].append({
            "source": link.get("source"),
            "target": link.get("target"),
            "value": 1,
            "label": link.get("type")
        })
    
    return old_format

@router.get("/graph")
async def get_full_knowledge_graph(limit: int = Query(100)):
    """获取全部知识图谱数据"""
    if not knowledge_graph:
        # 如果服务不可用，返回示例数据（与旧API相同）
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
    
    try:
        # 获取全部图谱数据，有数量限制
        graph_data = knowledge_graph.get_full_graph(limit=limit)
        
        # 转换为旧的格式以保持前端兼容性
        old_format = convert_to_old_format(graph_data)
        return old_format
    except Exception as e:
        logger.error(f"获取完整图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取知识图谱失败: {str(e)}")

@router.post("/chat")
async def chat_with_knowledge(request: KnowledgeChatRequest):
    """与知识库进行对话"""
    if not vector_store or not ollama_client:
        raise HTTPException(status_code=503, detail="知识图谱服务不可用")
    
    try:
        # 搜索知识，找到相关上下文
        search_results = vector_store.similarity_search(request.message, k=3)
        
        # 拼接上下文
        context = "\n\n".join([doc["text"] for doc in search_results])
        
        # 生成提示
        prompt = f"""你是一个有用的AI助手。使用以下知识来回答问题。

知识上下文：
{context}

用户问题：{request.message}

如果知识上下文中没有相关信息，请说明你不知道，而不是编造信息。

请按照以下格式回答：

思考过程
[你对这个问题的思考分析，用中文深入思考]


[你的实际回答，不需要标题，直接给出答案内容]
"""
        
        # 使用Ollama生成流式回答
        stream_generator = ollama_client.generate(prompt, model=request.model, temperature=request.temperature, stream=True)
        
        # 返回流式响应
        return StreamingResponse(stream_response(stream_generator), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"知识图谱流式聊天失败: {str(e)}")
        # 发生异常时返回错误消息
        return StreamingResponse(
            stream_dummy_response(f"查询失败: {str(e)}"), 
            media_type="text/event-stream"
        )

async def stream_response(stream_gen):
    """流式响应格式化"""
    # 收集完整的应答
    full_response = ""
    for chunk in stream_gen:
        full_response += chunk

    # 处理格式化问题
    # 1. 检测是否有多个“思考过程”标题
    if full_response.count("思考过程") > 1:
        # 只保留第一个“思考过程”到第一个空行
        parts = full_response.split("思考过程", 1)
        first_part = "思考过程" + parts[1]
        # 找到第一个思考过程结束的空行
        if "\n\n" in first_part:
            thoughts = first_part.split("\n\n", 1)[0] + "\n\n"
            remaining = full_response.split("思考过程", 1)[1]
            # 找到第二部分内容（不包含“正式回答”标题）
            if "\n\n" in remaining:
                answer = remaining.split("\n\n", 1)[1]
                if "正式回答" in answer:
                    answer = answer.replace("正式回答", "").strip()
                
                full_response = thoughts + answer

    # 分块发送反馈，模拟流式体验
    chunk_size = 200  # 控制分块大小
    for i in range(0, len(full_response), chunk_size):
        chunk = full_response[i:i+chunk_size]
        yield f"data: {json.dumps({'content': chunk})}\n\n"
        await asyncio.sleep(0.05)  # 增加小延迟方便前端显示
    
    yield "data: [DONE]\n\n"

async def stream_dummy_response(text):
    """流式响应模拟"""
    for char in text:
        yield f"data: {json.dumps({'content': char})}\n\n"
    yield "data: [DONE]\n\n"

@router.delete("/document/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档"""
    # 从向量存储中删除
    vector_deleted = False
    if vector_store:
        vector_deleted = vector_store.delete_document(doc_id)
    
    # 从知识图谱中删除
    graph_deleted = False
    if knowledge_graph:
        graph_deleted = knowledge_graph.delete_node(doc_id)
    
    if not vector_deleted and not graph_deleted:
        raise HTTPException(status_code=404, detail=f"未找到文档: {doc_id}")
    
    return {
        "success": vector_deleted or graph_deleted,
        "vector_deleted": vector_deleted,
        "graph_deleted": graph_deleted
    }

@router.post("/add-json")
async def add_json_knowledge(data: KnowledgeData):
    """直接添加JSON格式的知识数据"""
    if not vector_store or not knowledge_graph:
        raise HTTPException(status_code=503, detail="知识图谱服务不可用")
    
    try:
        # 处理节点
        added_nodes = []
        for node in data.nodes:
            # 生成ID（如果没有提供）
            if not node.id:
                node.id = hashlib.md5(f"{node.text}_{time.time()}".encode()).hexdigest()
            
            # 添加到知识图谱
            knowledge_graph.add_knowledge_node(node.id, node.text, node.metadata)
            
            # 添加到向量存储
            doc = {"id": node.id, "text": node.text, "metadata": node.metadata}
            vector_store.add_documents([doc])
            
            added_nodes.append(node.id)
        
        # 处理关系
        added_relations = []
        if data.relations:
            for relation in data.relations:
                # 添加关系到知识图谱
                success = knowledge_graph.add_relationship(
                    relation.source_id,
                    relation.target_id,
                    relation.relation_type,
                    relation.properties
                )
                
                if success:
                    added_relations.append({
                        "source": relation.source_id,
                        "target": relation.target_id,
                        "type": relation.relation_type
                    })
        
        return {
            "success": True,
            "added_nodes": len(added_nodes),
            "added_relations": len(added_relations),
            "nodes": added_nodes,
            "message": f"成功添加{len(added_nodes)}个知识节点和{len(added_relations)}个关系"
        }
    
    except Exception as e:
        logger.error(f"添加JSON知识数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加知识数据失败: {str(e)}")

@router.get("/documents")
async def list_documents():
    """列出所有文档"""
    # 获取原始文档
    original_docs = []
    if os.path.exists(DOCUMENTS_DIR):
        for filename in os.listdir(DOCUMENTS_DIR):
            file_path = os.path.join(DOCUMENTS_DIR, filename)
            if os.path.isfile(file_path):
                original_docs.append({
                    "id": filename,
                    "name": filename.split("_", 1)[1] if "_" in filename else filename,
                    "path": file_path,
                    "size": os.path.getsize(file_path),
                    "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })
    
    return {"documents": original_docs}

@router.get("/models")
async def list_models():
    """列出所有可用的模型"""
    if not ollama_client:
        raise HTTPException(status_code=503, detail="Ollama服务不可用")
    
    models = ollama_client.list_models()
    return {"models": models}
