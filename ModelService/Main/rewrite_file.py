"""
完整重写 route_planning.py - 解决所有问题
"""
import re

file_path = r"D:\ModelService_graduation-main\ModelService_graduation-main\ModelService\Main\app\routers\route_planning.py"

new_content = '''from fastapi import APIRouter, HTTPException, Request, FastAPI
from typing import Optional, Dict, List
from pydantic import BaseModel, Field
import requests
import json
import re
from datetime import datetime
import os
import logging
from fastapi.responses import StreamingResponse

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 尝试导入 VectorStore，失败时设置为 None
try:
    from ..utils.vector_store import VectorStore
    vector_store = VectorStore()
    VECTOR_STORE_AVAILABLE = True
    logger.info("VectorStore 初始化成功")
except Exception as e:
    logger.warning(f"VectorStore 初始化失败: {e}，将使用内存存储")
    vector_store = None
    VECTOR_STORE_AVAILABLE = False

# Ollama模型配置
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')

def get_ollama_status() -> bool:
    """获取 Ollama 当前状态"""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            return True
        return False
    except:
        return False

def ollama_generate_sync(prompt: str, model: str = None) -> str:
    """同步调用 Ollama API，直接返回完整响应。"""
    model_to_use = model or OLLAMA_MODEL
    
    logger.info(f"[OLLAMA] =========================================")
    logger.info(f"[OLLAMA] 开始生成")
    logger.info(f"[OLLAMA] 模型: {model_to_use}")
    logger.info(f"[OLLAMA] 提示词长度: {len(prompt)} 字符")
    
    try:
        payload = {
            "model": model_to_use,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.1,
                "num_predict": 4096,
                "num_ctx": 8192,
            }
        }
        
        logger.info(f"[OLLAMA] 发送请求到 Ollama...")
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=180
        )
        
        if resp.status_code == 200:
            result = resp.json().get("response", "")
            logger.info(f"[OLLAMA] 响应状态: {resp.status_code}")
            logger.info(f"[OLLAMA] 响应长度: {len(result)} 字符")
            logger.info(f"[OLLAMA] =========================================")
            logger.info(f"[OLLAMA] 【AI完整回复】")
            logger.info(f"{result}")
            logger.info(f"[OLLAMA] =========================================")
            return result
        else:
            logger.error(f"[OLLAMA] API 错误: {resp.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"[OLLAMA] 调用失败: {e}")
        return None

# 从环境变量获取API密钥
AMAP_KEY = os.getenv('AMAP_KEY', '5c98219ee72ff8b122e46b8167333eb9')

# 定义API前缀
API_PREFIX = '/api/route'
router = APIRouter()

class RoutePreferences(BaseModel):
    avoid_highways: bool = Field(default=False)
    avoid_tolls: bool = Field(default=False)
    avoid_congestion: bool = Field(default=True)

class RouteInfo(BaseModel):
    start_point: str = Field(...)
    end_point: str = Field(...)
    waypoints: List[str] = Field(default=[])
    departure_time: str = Field(default="")
    arrival_time: str = Field(default="")
    route_type: str = Field(default="LEAST_TIME")

class RecommendedRoute(BaseModel):
    type: str = Field(...)
    name: str = Field(...)
    reason: str = Field(...)

class RouteRequest(BaseModel):
    text: str = Field(...)
    model: str = Field(default=os.getenv("OLLAMA_MODEL", "qwen3.5:4b"))

class RouteResponse(BaseModel):
    success: bool = Field(...)
    route_data: Optional[Dict] = Field(default=None)
    error: Optional[str] = Field(default=None)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

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

def fallback_route_analysis(text: str) -> RouteResponse:
    """使用 Ollama API 或正则表达式解析路线"""
    logger.info(f"[解析] 开始解析路线: {text}")
    
    ollama_available = get_ollama_status()
    
    if ollama_available:
        logger.info(f"[解析] 使用 Ollama API 解析...")
        ollama_prompt = f"""你是一个路线解析助手。请从用户输入中提取起点、终点、途经点。

用户输入: {text}

请严格按照以下 JSON 格式返回：
{{
    "start_point": "起点名称",
    "end_point": "终点名称",
    "waypoints": ["途经点1"],
    "route_type": "LEAST_TIME",
    "reason": "推荐原因"
}}

如果无法提取，请返回默认值。"""
        
        result = ollama_generate_sync(ollama_prompt, model=OLLAMA_MODEL)
        
        if result:
            try:
                start_idx = result.find('{')
                end_idx = result.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = result[start_idx:end_idx]
                    data = json.loads(json_str)
                    logger.info(f"[解析] Ollama结果: {data}")
                    
                    route_data = {
                        "recommended_routes": [
                            {"type": data.get("route_type", "LEAST_TIME"), "name": "推荐路线", "reason": data.get("reason", "根据您的需求推荐")},
                            {"type": "LEAST_FEE", "name": "备选路线", "reason": "费用较低"}
                        ],
                        "route_info": {
                            "start_point": data.get("start_point", "北京"),
                            "end_point": data.get("end_point", "上海"),
                            "waypoints": data.get("waypoints", []),
                            "departure_time": "",
                            "arrival_time": "",
                            "route_type": data.get("route_type", "LEAST_TIME")
                        },
                        "preferences": {
                            "avoid_highways": False,
                            "avoid_tolls": False,
                            "avoid_congestion": True
                        }
                    }
                    route_data["response_text"] = f"已为您规划从 {route_data['route_info']['start_point']} 到 {route_data['route_info']['end_point']} 的路线"
                    route_data['note'] = '使用 Ollama API 智能解析'
                    route_data['used_fallback'] = False
                    
                    return RouteResponse(success=True, route_data=route_data, error=None)
            except Exception as e:
                logger.warning(f"[解析] Ollama解析失败: {e}，使用正则表达式")
    
    # 正则表达式解析
    logger.info("[解析] 使用正则表达式解析...")
    
    simple_sep = None
    if "到" in text:
        simple_sep = "到"
    elif "至" in text:
        simple_sep = "至"
    elif "->" in text:
        simple_sep = "->"
    
    start_point = "北京"
    end_point = "上海"
    
    if simple_sep:
        parts = [p.strip() for p in text.split(simple_sep) if p.strip()]
        if len(parts) >= 2:
            start_point = parts[0] if parts[0] else start_point
            end_point = parts[1] if len(parts) > 1 and parts[1] else end_point
    
    waypoints = []
    if "郑州工程技术学院" in text:
        waypoints = ["郑州工程技术学院"]
    
    route_data = {
        "recommended_routes": [
            {"type": "LEAST_TIME", "name": "推荐路线", "reason": "最快到达目的地"},
            {"type": "LEAST_FEE", "name": "备选路线", "reason": "费用较低"}
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
    route_data["response_text"] = f"已为您规划从 {start_point} 到 {end_point} 的路线（回退结果）"
    route_data['note'] = '使用回退解析'
    route_data['used_fallback'] = True
    
    return RouteResponse(success=True, route_data=route_data, error=None)

@router.post("/plan/stream")
async def stream_route_plan_post(request: Request):
    """
    POST 路线规划接口 - 直接返回结果，不流式输出
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    text = body.get("text", "") or ""
    model = body.get("model", OLLAMA_MODEL)
    
    logger.info(f"[规划] =========================================")
    logger.info(f"[规划] 收到请求: {text}")
    logger.info(f"[规划] 使用模型: {model}")
    
    # Step 1: 开始分析
    logger.info(f"[规划] Step 1: 开始分析用户输入")
    
    # Step 2: 调用 Ollama
    logger.info(f"[规划] Step 2: 调用 Ollama...")
    formatted_prompt = ROUTE_PROMPT.format(text=text, historical_context="")
    
    ai_response = ollama_generate_sync(formatted_prompt, model=model)
    if ai_response:
        logger.info(f"[规划] AI响应已接收，长度: {len(ai_response)}")
    
    # Step 3: 生成结构化数据
    logger.info(f"[规划] Step 3: 解析路线信息...")
    final = fallback_route_analysis(text)
    
    route_data = None
    if hasattr(final, 'route_data') and final.route_data:
        route_data = final.route_data
    elif isinstance(final, dict):
        route_data = final
    
    if route_data:
        logger.info(f"[规划] 结构化路线数据:")
        logger.info(json.dumps(route_data, ensure_ascii=False, indent=2))
        logger.info(f"[规划] =========================================")
        return {
            "event": "done",
            "route_data": route_data
        }
    else:
        logger.error(f"[规划] 无法生成路线数据")
        return {
            "event": "error",
            "content": "无法生成路线数据"
        }

@router.get("/check-ollama")
async def check_ollama_status():
    """检查Ollama服务状态"""
    ollama_available = get_ollama_status()
    
    if ollama_available:
        return {
            "status": "connected",
            "message": "Ollama 服务已连接",
            "model": OLLAMA_MODEL,
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "status": "error",
            "message": "Ollama 服务未启动",
            "model": OLLAMA_MODEL,
            "timestamp": datetime.now().isoformat()
        }

@router.get("/history")
async def get_route_history():
    """获取路线历史"""
    try:
        if not VECTOR_STORE_AVAILABLE or not vector_store:
            return {"success": True, "history": [], "note": "VectorStore 不可用"}
        documents = vector_store.get_all_documents()
        return {"success": True, "history": documents}
    except Exception as e:
        logger.error(f"获取路线历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history/{index}")
async def delete_route_history(index: int):
    """删除历史路线"""
    try:
        if not VECTOR_STORE_AVAILABLE or not vector_store:
            return {"success": False, "message": "VectorStore 不可用"}
        success = vector_store.delete_document(index)
        return {"success": success, "message": "删除成功" if success else "删除失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_location(address: str) -> str:
    """获取地理编码"""
    try:
        response = requests.get(
            "https://restapi.amap.com/v3/geocode/geo",
            params={"key": AMAP_KEY, "address": address},
            timeout=10
        )
        data = response.json()
        if data["status"] == "1" and data["geocodes"]:
            return data["geocodes"][0]["location"]
    except:
        pass
    return "113.665412,34.757975"

async def get_route_plan(start: str, end: str, preferences: Dict, route_type: str) -> Dict:
    """获取路线规划详情"""
    try:
        strategy = {"LEAST_TIME": 0, "LEAST_FEE": 1, "LEAST_DISTANCE": 2}.get(route_type, 0)
        response = requests.get(
            "https://restapi.amap.com/v3/direction/driving",
            params={
                "key": AMAP_KEY,
                "origin": start,
                "destination": end,
                "strategy": strategy,
                "extensions": "all"
            },
            timeout=10
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def register_route_planning_page(app: FastAPI):
    """注册路线规划聊天页面"""
    from fastapi.responses import FileResponse
    from pathlib import Path
    
    @app.get("/route-planning/")
    async def route_planning_page():
        template_path = Path(__file__).parent.parent / "templates" / "chat" / "route_planning.html"
        if template_path.exists():
            return FileResponse(template_path)
        else:
            return {"error": "模板文件不存在", "path": str(template_path)}
'''

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("SUCCESS: 文件已完全重写!")
print("- 删除所有流式输出和分片打印")
print("- 改为同步直接调用 Ollama")
print("- 直接打印完整 AI 回复")
print("- API改为直接返回JSON，不使用SSE")




