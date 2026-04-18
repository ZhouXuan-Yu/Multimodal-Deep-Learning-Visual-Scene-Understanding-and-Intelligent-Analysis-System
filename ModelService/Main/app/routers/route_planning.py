from fastapi import APIRouter, HTTPException, Request
from typing import Optional, Dict, List
from pydantic import BaseModel, Field
import requests
import json
import re
from datetime import datetime
import os
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 尝试导入 VectorStore，失败时设置为 None
try:
    from ..utils.vector_store import VectorStore
    vector_store = VectorStore()
    VECTOR_STORE_AVAILABLE = True
    logger.info("✅ VectorStore 初始化成功")
except Exception as e:
    logger.warning(f"⚠️ VectorStore 初始化失败: {e}，将使用内存存储")
    vector_store = None
    VECTOR_STORE_AVAILABLE = False

# 尝试导入 ollama_client，失败时设置为 None
try:
    from ..services.knowledge_graph_enhanced.ollama_client import ollama_client
    OLLAMA_CLIENT_AVAILABLE = ollama_client is not None
    if OLLAMA_CLIENT_AVAILABLE:
        logger.info("✅ OllamaClient 初始化成功")
    else:
        logger.warning("⚠️ OllamaClient 为 None")
except Exception as e:
    logger.warning(f"⚠️ OllamaClient 导入失败: {e}")
    ollama_client = None
    OLLAMA_CLIENT_AVAILABLE = False

# 直接检测 Ollama 服务是否可用（绕过 ollama_client 依赖）
OLLAMA_DIRECT_AVAILABLE = False
# 默认使用轻量级纯文本模型，降低资源占用
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")

def check_ollama_service(timeout: int = 3) -> bool:
    """快速探测 Ollama 服务是否可用（非阻塞、短超时）。"""
    global OLLAMA_DIRECT_AVAILABLE
    try:
        resp = requests.get(
            "http://localhost:11434/api/tags",
            timeout=timeout
        )
        if resp.status_code == 200:
            OLLAMA_DIRECT_AVAILABLE = True
            logger.info("✅ Ollama 服务可直接访问")
            return True
        else:
            OLLAMA_DIRECT_AVAILABLE = False
            return False
    except Exception as e:
        logger.warning(f"⚠️ Ollama 服务不可用: {e}")
        OLLAMA_DIRECT_AVAILABLE = False
        return False

# 启动时检查 Ollama 服务
logger.info("正在检查 Ollama 服务...")
if check_ollama_service(timeout=2):
    logger.info(f"✅ Ollama 服务可用，使用模型: {OLLAMA_MODEL}")
else:
    logger.warning("⚠️ Ollama 服务不可用，将使用备用解析")

def ollama_generate_sync(prompt: str, model: str = None) -> str:
    """非流式调用 Ollama API，返回完整响应。"""
    global OLLAMA_DIRECT_AVAILABLE
    logger.info(f"[OLLAMA SYNC] 开始生成，OLLAMA_DIRECT_AVAILABLE={OLLAMA_DIRECT_AVAILABLE}")
    
    if not OLLAMA_DIRECT_AVAILABLE:
        logger.warning(f"[OLLAMA SYNC] OLLAMA_DIRECT_AVAILABLE 为 False，返回 None")
        return None
    
    try:
        payload = {
            "model": model or OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.1,
                # 使用较小的生成长度和上下文长度，提升响应速度，降低资源占用
                "num_predict": 512,
                "num_ctx": 2048,
            }
        }
        logger.info(f"[OLLAMA SYNC] 发送请求到 Ollama (超时60秒)...")
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=60
        )
        logger.info(f"[OLLAMA SYNC] 响应状态码: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json().get("response", "")
            logger.info(f"[OLLAMA SYNC] Ollama 返回结果 (长度 {len(result)}): {result[:200]}...")
            return result
        else:
            logger.error(f"Ollama API 错误: {resp.status_code} - {resp.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"Ollama API 调用失败: {e}")
        OLLAMA_DIRECT_AVAILABLE = False
        return None

def ollama_generate_stream(prompt: str, model: str = None):
    """流式调用 Ollama API，返回生成器。"""
    global OLLAMA_DIRECT_AVAILABLE
    logger.info(f"[OLLAMA STREAM] 开始流式生成，OLLAMA_DIRECT_AVAILABLE={OLLAMA_DIRECT_AVAILABLE}")
    
    if not OLLAMA_DIRECT_AVAILABLE:
        logger.warning(f"[OLLAMA STREAM] OLLAMA_DIRECT_AVAILABLE 为 False，跳过生成")
        return
    
    try:
        payload = {
            "model": model or OLLAMA_MODEL,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.1,
                "top_p": 0.1,
                "num_predict": 2048,  # 增加生成长度
                "num_ctx": 4096,  # 增加上下文长度
            }
        }
        logger.info(f"[OLLAMA STREAM] 发送请求到 Ollama (GPU模式，超时120秒)...")
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=120,  # GPU 需要更长时间
            stream=True
        )
        logger.info(f"[OLLAMA STREAM] 响应状态码: {resp.status_code}")
        
        if resp.status_code == 200:
            chunk_count = 0
            full_response = ""
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line.decode('utf-8'))
                    if 'response' in data:
                        chunk_count += 1
                        # 不再逐条打印分片，避免控制台刷屏，仅累积完整输出
                        full_response += data['response']
                        yield data['response']
                    if data.get('done', False):
                        logger.info(f"[OLLAMA STREAM] 流式生成完成，共 {chunk_count} 个分片")
                        if full_response:
                            logger.info(f"[OLLAMA STREAM] 完整输出预览: {full_response[:500]}...")
                        break
        else:
            logger.error(f"Ollama API 流式错误: {resp.status_code} - {resp.text[:200]}")
            OLLAMA_DIRECT_AVAILABLE = False
            yield None
    except Exception as e:
        logger.error(f"OllAMA STREAM API 流式调用失败: {e}")
        OLLAMA_DIRECT_AVAILABLE = False
        yield None

# 从环境变量获取API密钥
AMAP_KEY = os.getenv('AMAP_KEY', '5c98219ee72ff8b122e46b8167333eb9')
# Ollama模型服务地址，可以根据实际情况配置
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')

# 定义API前缀，方便主应用程序进行路由注册
API_PREFIX = '/api/route'

router = APIRouter()

def is_ollama_available(model: str = None, timeout: int = 3) -> (bool, str):
    """快速探测 Ollama 服务是否可用（非阻塞、短超时）。
    返回 (available: bool, message: str)。"""
    try:
        probe_payload = {
            "model": model or OLLAMA_MODEL,
            "prompt": "ping",
            "stream": False,
            "options": {"temperature": 0.1}
        }
        resp = requests.post(OLLAMA_URL, json=probe_payload, timeout=timeout)
        if resp.status_code == 200:
            return True, "OK"
        else:
            return False, f"非200响应: {resp.status_code}"
    except Exception as e:
        return False, str(e)

class RoutePreferences(BaseModel):
    """路线偏好设置"""
    avoid_highways: bool = Field(default=False, description="避开高速")
    avoid_tolls: bool = Field(default=False, description="避开收费")
    avoid_congestion: bool = Field(default=True, description="避开拥堵")

class RouteInfo(BaseModel):
    """路线信息"""
    start_point: str = Field(..., description="起点")
    end_point: str = Field(..., description="终点")
    waypoints: List[str] = Field(default=[], description="途经点")
    departure_time: str = Field(default="", description="出发时间")
    arrival_time: str = Field(default="", description="到达时间")
    route_type: str = Field(default="LEAST_TIME", description="路线类型")

class RecommendedRoute(BaseModel):
    """推荐路线"""
    type: str = Field(..., description="路线类型")
    name: str = Field(..., description="路线名称")
    reason: str = Field(..., description="推荐原因")

class RouteRequest(BaseModel):
    """路线规划请求"""
    text: str = Field(..., description="用户输入文本")
    model: str = Field(default=os.getenv("OLLAMA_MODEL", "qwen3.5:4b"), description="使用的模型")
    historical_route: Optional[Dict] = Field(default=None, description="历史路线")

class RouteResponse(BaseModel):
    """路线规划响应"""
    success: bool = Field(..., description="是否成功")
    route_data: Optional[Dict] = Field(default=None, description="路线数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="时间戳")

ROUTE_PROMPT = """你是一个专业的路线规划助手。请分析用户的出行需求，并返回JSON格式的路线规划。

用户输入: {text}

历史路线: {historical_context}

请按照以下格式返回JSON：
{{
    "recommended_routes": [
        {{
            "type": "LEAST_TIME",
            "name": "推荐路线",
            "reason": "最快到达目的地"
        }},
        {{
            "type": "LEAST_FEE",
            "name": "备选路线",
            "reason": "费用较低"
        }}
    ],
    "route_info": {{
        "start_point": "起点",
        "end_point": "终点",
        "waypoints": [],
        "departure_time": "",
        "arrival_time": "",
        "route_type": "LEAST_TIME"
    }},
    "preferences": {{
        "avoid_highways": false,
        "avoid_tolls": false,
        "avoid_congestion": true
    }}
}}
"""

@router.post("/plan", response_model=RouteResponse)
async def create_route_plan(request: Request) -> RouteResponse:
    """创建路线规划"""
    try:
        # 直接读取请求体
        try:
            body = await request.json()
            logger.info(f"收到路线规划请求: {body}")
            
            # 提取必要参数
            text = body.get("text", "")
            model = body.get("model", os.getenv("OLLAMA_MODEL", "qwen3.5:4b"))
            
            if not text:
                return RouteResponse(
                    success=False,
                    error="请求缺少text字段"
                )
                
            # 使用提取的参数创建请求对象
            route_request = RouteRequest(text=text, model=model)
            
        except Exception as e:
            logger.error(f"解析路线规划请求失败: {str(e)}")
            return RouteResponse(
                success=False,
                error=f"无效的请求格式: {str(e)}"
            )
        
        # 获取相关的历史路线
        if VECTOR_STORE_AVAILABLE and vector_store:
            try:
                similar_routes = vector_store.query(route_request.text, n_results=1)
                historical_context = ""
                
                if similar_routes and similar_routes['documents']:
                    historical_context = similar_routes['documents'][0]
                    logger.info(f"找到相关历史路线: {historical_context[:100]}...")
                else:
                    logger.info("未找到相关历史路线")
            except Exception as e:
                logger.warning(f"查询历史路线失败: {e}，使用空历史")
                historical_context = ""
        else:
            logger.info("VectorStore 不可用，使用空历史")
            historical_context = ""
        
        # 检查Ollama服务是否可用
        logger.info(f"开始检查Ollama服务是否可用: {OLLAMA_URL}")
        try:
            # 尝试列出模型，这是官方API端点
            ollama_list = requests.get(
                "http://localhost:11434/api/tags",
                timeout=5
            )
            logger.info(f"Ollama模型列表检查响应: {ollama_list.status_code}")
            
            if ollama_list.status_code != 200:
                logger.error(f"Ollama服务不可用: {ollama_list.text}")
                # 如果Ollama服务不可用，使用简单的关键词解析方法进行路线分析
                return fallback_route_analysis(route_request.text)
        except requests.RequestException as e:
            logger.error(f"Ollama服务检查失败: {str(e)}")
            # 如果无法连接到Ollama服务，使用简单的关键词解析方法进行路线分析
            return fallback_route_analysis(route_request.text)
        
        # 调用 Ollama 分析用户需求
        try:
            logger.info(f"正在请求Ollama模型分析，URL: {OLLAMA_URL}, 模型: {route_request.model}")
            logger.info(f"请求内容: {route_request.text[:100]}...")
            
            ollama_response = requests.post(
                OLLAMA_URL,
                json={
                    "model": route_request.model,
                    "prompt": ROUTE_PROMPT.format(
                        text=route_request.text,
                        historical_context=historical_context
                    ),
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.1
                    }
                },
                timeout=60  # 路线规划使用较短超时，避免长时间卡住
            )
            logger.info(f"Ollama响应状态码: {ollama_response.status_code}")
            
            if ollama_response.status_code != 200:
                logger.error(f"Ollama响应错误: {ollama_response.text}")
                return fallback_route_analysis(route_request.text)
                
        except requests.RequestException as e:
            logger.error(f"Ollama请求失败: {str(e)}")
            return fallback_route_analysis(route_request.text)
        
        try:
            response_json = ollama_response.json()
            response_text = response_json["response"].strip()
            
            # 提取JSON内容
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if (start_idx >= 0 and end_idx > start_idx):
                response_text = response_text[start_idx:end_idx]
                response_text = response_text.replace('\n', ' ').replace('\r', ' ')
                response_text = re.sub(r'\s+', ' ', response_text)
                response_text = re.sub(r',\s*}', '}', response_text)
                response_text = re.sub(r',\s*]', ']', response_text)
                
                try:
                    route_analysis = json.loads(response_text)
                except json.JSONDecodeError:
                    response_text = response_text.replace("'", '"')
                    response_text = re.sub(r'([{,])\s*(\w+):', r'\1"\2":', response_text)
                    route_analysis = json.loads(response_text)
                
                # 验证和补充必要字段
                if 'route_info' not in route_analysis:
                    route_analysis['route_info'] = {}
                
                route_info = route_analysis['route_info']
                
                # 验证必要字段
                if not route_info.get('start_point') or not route_info.get('end_point'):
                    return RouteResponse(
                        success=False,
                        error="缺少起点或终点信息"
                    )
                
                # 补充默认值
                route_info.setdefault('waypoints', [])
                route_info.setdefault('departure_time', '')
                route_info.setdefault('arrival_time', '')
                route_info.setdefault('route_type', 'LEAST_TIME')
                
                # 验证路线类型
                valid_types = ['LEAST_TIME', 'LEAST_FEE', 'LEAST_DISTANCE']
                if route_info['route_type'] not in valid_types:
                    route_info['route_type'] = 'LEAST_TIME'
                
                # 确保推荐路线存在
                if 'recommended_routes' not in route_analysis:
                    route_analysis['recommended_routes'] = [
                        {
                            "type": route_info['route_type'],
                            "name": "推荐路线",
                            "reason": "根据您的需求推荐"
                        }
                    ]
                
                # 确保偏好设置存在
                if 'preferences' not in route_analysis:
                    route_analysis['preferences'] = {
                        "avoid_highways": False,
                        "avoid_tolls": False,
                        "avoid_congestion": True
                    }

                # 基于路线结果生成一句话关键信息，供前端直接展示
                waypoints = route_info.get('waypoints') or []
                waypoints_str = ''
                if isinstance(waypoints, list) and waypoints:
                    waypoints_str = '，途经 ' + '、'.join([str(w) for w in waypoints])

                # 选出一个主推荐路线（优先匹配 route_type）
                recommended_routes = route_analysis.get('recommended_routes') or []
                primary_route = None
                for r in recommended_routes:
                    try:
                        if r.get('type') == route_info.get('route_type'):
                            primary_route = r
                            break
                    except Exception:
                        continue
                if not primary_route and recommended_routes:
                    primary_route = recommended_routes[0]

                if primary_route:
                    summary = (
                        f"已为您规划从 {route_info.get('start_point')} 到 {route_info.get('end_point')} 的路线"
                        f"{waypoints_str}，推荐方案：{primary_route.get('name', '推荐路线')}（{primary_route.get('reason', '根据您的需求推荐')}）。"
                    )
                else:
                    summary = (
                        f"已为您规划从 {route_info.get('start_point')} 到 {route_info.get('end_point')} 的路线{waypoints_str}。"
                    )

                route_analysis['response_text'] = summary
                
                return RouteResponse(
                    success=True,
                    route_data=route_analysis
                )
            else:
                return RouteResponse(
                    success=False,
                    error="无法找到有效的JSON数据"
                )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {str(e)}")
            return fallback_route_analysis(route_request.text)
            
    except Exception as e:
        logger.error(f"路线规划异常: {str(e)}")
        return RouteResponse(
            success=False,
            error=f"路线规划失败: {str(e)}"
        )


def fallback_route_analysis(text: str) -> RouteResponse:
    """
    使用 Ollama API 或正则表达式解析路线。
    优先使用 Ollama API，只有在 Ollama 不可用时才使用正则表达式。
    """
    logger.info(f"开始解析路线: {text}")
    
    # 优先尝试使用 Ollama API 解析
    if OLLAMA_DIRECT_AVAILABLE:
        logger.info(f"使用 Ollama API 解析路线...")
        ollama_prompt = f"""你是一个路线解析助手。请从用户输入中提取起点、终点、途经点。

用户输入: {text}

请严格按照以下 JSON 格式返回（不要添加任何其他内容）：
{{
    "start_point": "起点名称",
    "end_point": "终点名称", 
    "waypoints": ["途经点1", "途经点2"],
    "route_type": "LEAST_TIME | LEAST_FEE | SHORTEST",
    "avoid_highways": false,
    "avoid_tolls": false,
    "avoid_congestion": true,
    "reason": "推荐原因"
}}

如果无法提取到完整信息，请返回默认值。"""
        
        result = ollama_generate_sync(ollama_prompt, model=OLLAMA_MODEL)
        
        if result:
            try:
                # 提取 JSON
                start_idx = result.find('{')
                end_idx = result.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = result[start_idx:end_idx]
                    data = json.loads(json_str)
                    logger.info(f"Ollama 解析结果: {data}")
                    
                    route_data = {
                        "recommended_routes": [
                            {
                                "type": data.get("route_type", "LEAST_TIME"),
                                "name": "推荐路线",
                                "reason": data.get("reason", "根据您的需求推荐")
                            },
                            {
                                "type": "LEAST_FEE",
                                "name": "备选路线",
                                "reason": "费用较低"
                            }
                        ],
                        "route_info": {
                            "start_point": data.get("start_point", "北京"),
                            "end_point": data.get("end_point", "郑州"),
                            "waypoints": data.get("waypoints", []),
                            "departure_time": "",
                            "arrival_time": "",
                            "route_type": data.get("route_type", "LEAST_TIME")
                        },
                        "preferences": {
                            "avoid_highways": data.get("avoid_highways", False),
                            "avoid_tolls": data.get("avoid_tolls", False),
                            "avoid_congestion": data.get("avoid_congestion", True)
                        }
                    }
                    route_data["response_text"] = f"已为您规划从 {route_data['route_info']['start_point']} 到 {route_data['route_info']['end_point']} 的路线"
                    route_data['note'] = '使用 Ollama API 智能解析'
                    route_data['used_fallback'] = False
                    
                    return RouteResponse(
                        success=True,
                        route_data=route_data,
                        error=None
                    )
            except json.JSONDecodeError as e:
                logger.warning(f"Ollama 返回结果解析失败: {e}，使用正则表达式")
            except Exception as e:
                logger.warning(f"Ollama 解析出错: {e}，使用正则表达式")
    
    # 回退到正则表达式解析
    logger.info("使用正则表达式解析路线...")
    
    # 使用简单的正则表达式提取起点和终点
    start_pattern = re.compile(r'从(.*?)到|从(.*?)至|从(.*?)出发|起点是?(.*?)，|起点[:：]?\s*(.*?)，')
    end_pattern = re.compile(r'到(.*?)的|至(.*?)的|去(.*?)的|终点是?(.*?)$|终点[:：]?\s*(.*?)$')
    
    # 尝试提取起点和终点
    start_matches = start_pattern.search(text)
    end_matches = end_pattern.search(text)
    
    start_point = None
    if start_matches:
        for group in start_matches.groups():
            if group:
                start_point = group.strip()
                break
    
    end_point = None
    if end_matches:
        for group in end_matches.groups():
            if group:
                end_point = group.strip()
                break
    
    # 如果无法提取，使用默认值
    # 如果初始正则无法提取，尝试更简单的分隔模式（处理“上海到北京”这类句子）
    if not start_point or not end_point:
        simple_sep = None
        if "到" in text:
            simple_sep = "到"
        elif "至" in text:
            simple_sep = "至"
        elif "->" in text:
            simple_sep = "->"
        elif " to " in text:
            simple_sep = " to "

        if simple_sep:
            parts = [p.strip() for p in text.split(simple_sep) if p.strip()]
            if len(parts) >= 2:
                # prefer to fill missing values
                if not start_point:
                    start_point = parts[0]
                if not end_point:
                    end_point = parts[1]

    start_point = start_point or "北京"
    end_point = end_point or "郑州"
    
    if "郑州工程技术学院" in text:
        waypoints = ["郑州工程技术学院"]
    else:
        waypoints = []
    
    # 构建基本的路线数据
    # 构建基本的路线数据（使用提取到的 start/end）
    route_data = {
        "recommended_routes": [
            {
                "type": "LEAST_TIME",
                "name": "推荐路线",
                "reason": "最快到达目的地"
            },
            {
                "type": "LEAST_FEE",
                "name": "备选路线",
                "reason": "费用较低"
            }
        ],
        "route_info": {
            "start_point": start_point,
            "end_point": end_point,
            "waypoints": waypoints,
            "departure_time": "",
            "arrival_time": "",
            "route_type": "LEAST_TIME"
        },
        "preferences": {
            "avoid_highways": False,
            "avoid_tolls": False,
            "avoid_congestion": True
        }
    }
    # 更新 response_text 以包含实际解析到的起终点，便于前端展示
    route_data["response_text"] = f"已为您规划从 {route_data['route_info']['start_point']} 到 {route_data['route_info']['end_point']} 的路线（回退结果）"
    # 标注为回退结果，便于前端显示提示
    route_data['note'] = '使用回退解析：Ollama 服务不可用或出现错误，返回简化建议。'
    route_data['used_fallback'] = True
    
    return RouteResponse(
        success=True,
        route_data=route_data,
        error=None
    )

@router.get("/history")
async def get_route_history():
    """获取路线历史"""
    try:
        if not VECTOR_STORE_AVAILABLE or not vector_store:
            return {
                "success": True,
                "history": [],
                "note": "VectorStore 不可用",
                "timestamp": datetime.now().isoformat()
            }
        documents = vector_store.get_all_documents()
        return {
            "success": True,
            "history": documents,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取路线历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history/{index}")
async def delete_route_history(index: int):
    """删除历史路线"""
    try:
        if not VECTOR_STORE_AVAILABLE or not vector_store:
            return {
                "success": False,
                "message": "VectorStore 不可用",
                "timestamp": datetime.now().isoformat()
            }
        success = vector_store.delete_document(index)
        return {
            "success": success,
            "message": "删除成功" if success else "删除失败",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_location(address: str) -> str:
    """获取地理编码"""
    try:
        logger.info(f"尝试获取地址[{address}]的地理编码")
        response = requests.get(
            "https://restapi.amap.com/v3/geocode/geo",
            params={
                "key": AMAP_KEY,
                "address": address
            },
            timeout=400  # 设置超时时间为400秒
        )
        data = response.json()
        if data["status"] == "1" and data["geocodes"]:
            location = data["geocodes"][0]["location"]
            logger.info(f"成功获取地址[{address}]的地理编码: {location}")
            return location
            
        # 地理编码未找到结果时使用默认值
        logger.warning(f"未找到地址[{address}]的地理编码结果，使用默认坐标")
        # 郑州市中心坐标
        return "113.665412,34.757975"
    except Exception as e:
        logger.error(f"地理编码请求失败: {str(e)}")
        # 返回默认坐标（郑州市中心）
        return "113.665412,34.757975"

async def get_route_plan(
    start: str,
    end: str,
    preferences: Dict,
    route_type: str
) -> Dict:
    """获取路线规划详情"""
    try:
        strategy = {
            "LEAST_TIME": 0,
            "LEAST_FEE": 1,
            "LEAST_DISTANCE": 2
        }.get(route_type, 0)
        
        response = requests.get(
            "https://restapi.amap.com/v3/direction/driving",
            params={
                "key": AMAP_KEY,  # 使用环境变量中的API密钥
                "origin": start,
                "destination": end,
                "strategy": strategy,
                "extensions": "all"
            },
            timeout=400  # 设置超时时间为400秒
        )
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"路线规划请求失败: {str(e)}")

# 添加OPTIONS方法支持
@router.options("/plan")
async def options_route_plan():
    return {"message": "OK"}

# 添加跨域路由的处理
@router.post("/plan", response_model=RouteResponse)
async def create_route_plan_direct(request: Request) -> RouteResponse:
    """直接创建路线规划 - 兼容Front_UAV前端"""
    logger.info("收到直接路线规划请求 - API路径: /plan")
    
    try:
        # 尝试处理请求
        response = await create_route_plan(request)
        logger.info(f"路线规划响应: {response}")
        return response
    except Exception as e:
        logger.error(f"处理路线规划请求失败: {str(e)}")
        return RouteResponse(
            success=False,
            error=f"路线规划失败: {str(e)}"
        )