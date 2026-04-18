from fastapi import APIRouter, HTTPException, Request, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import requests
import logging
import json
import os

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

ChatModelDefault = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")

class ChatMessage(BaseModel):
    role: str
    content: str

# 添加更灵活的聊天请求模型
class SimpleChatRequest(BaseModel):
    """简化版聊天请求，支持直接发送content字段"""
    content: str
    type: str = "general"
    model: str = ChatModelDefault

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = ChatModelDefault
    type: str = "general"

@router.post("/completions")
async def chat_completion(request: Request):
    """聊天完成，支持灵活的请求格式"""
    try:
        # 直接读取请求体
        try:
            body = await request.json()
            logger.info(f"收到请求体: {body}")
        except Exception as e:
            logger.error(f"解析请求体失败: {str(e)}")
            return {
                "message": f"无效的请求格式: {str(e)}"
            }
        
        # 解析请求参数
        content = ""
        model = ChatModelDefault
        chat_type = body.get("type", "general")
        
        # 灵活处理不同的请求格式
        if "messages" in body and isinstance(body["messages"], list) and len(body["messages"]) > 0:
            # 标准格式
            messages = body["messages"]
            content = messages[-1].get("content", "")
            if "model" in body:
                model = body["model"]
        elif "content" in body:
            # 简化格式
            content = body["content"]
            if "model" in body:
                model = body["model"]
        else:
            logger.error("无法解析请求: 缺少content或messages字段")
            return {
                "message": "无效的请求格式: 缺少content或messages字段"
            }
        
        logger.info(f"解析后的参数: content={content}, model={model}, type={chat_type}")
        
        # 根据聊天类型处理
        if chat_type == "route":
            try:
                # 调用路线规划API
                route_result = await handle_route_planning(content, model)
                logger.info(f"路线规划结果: {route_result}")
                return route_result
            except Exception as route_error:
                logger.error(f"路线规划异常: {str(route_error)}")
                # 如果路线规划失败，返回默认消息
                return {
                    "message": f"无法完成路线规划: {str(route_error)}"
                }
            
        # 否则尝试使用模拟数据响应，避免依赖外部服务
        try:
            # 首先检查是否可以使用Ollama服务
            logger.info(f"检查Ollama服务可用性")
            try:
                # 使用环境变量配置 Ollama 地址（支持 OLLAMA_URL 或 OLLAMA_BASE）
                env_ollama = os.getenv("OLLAMA_URL") or os.getenv("OLLAMA_BASE") or "http://localhost:11434"
                base = env_ollama.split("/api")[0].rstrip("/")
                tags_url = f"{base}/api/tags"

                # 使用短超时检查服务可用性
                ollama_check = requests.get(tags_url, timeout=2)
                if ollama_check.status_code != 200:
                    raise Exception(f"Ollama服务响应代码非200: {ollama_check.status_code}")
            except Exception as check_error:
                # 服务不可用，返回模拟数据
                logger.warning(f"Ollama服务不可用: {str(check_error)}")
                return {
                    "message": f"您好，我是您的AI助手。目前我在离线模式下工作，只能提供基本功能。请问有什么我可以帮助您的吗？"
                }
                
            # Ollama服务可用，调用API
            logger.info(f"调用Ollama API，提示: {content}, 模型: {model}")
            # 使用环境变量配置 Ollama 地址（支持 OLLAMA_URL 或 OLLAMA_BASE）
            env_ollama = os.getenv("OLLAMA_URL") or os.getenv("OLLAMA_BASE") or "http://localhost:11434"
            base = env_ollama.split("/api")[0].rstrip("/")
            generate_url = f"{base}/api/generate"

            ollama_response = requests.post(
                generate_url,
                json={
                    "model": model or ChatModelDefault,
                    "prompt": content,
                    "stream": False
                },
                timeout=60  # 设置60秒超时
            )
            
            logger.info(f"Ollama响应状态: {ollama_response.status_code}")
            
            if ollama_response.status_code == 200:
                return {
                    "message": ollama_response.json()["response"]
                }
            else:
                # API响应不成功，返回默认消息
                logger.error(f"Ollama API调用失败: {ollama_response.text}")
                return {
                    "message": f"我已收到您的消息，但目前我无法生成适当的回应。请您尝试提供更多信息或换一种提问方式。"
                }
                
        except Exception as e:
            # 捕获所有异常，确保始终返回有效消息
            logger.error(f"处理聊天请求异常: {str(e)}")
            return {
                "message": "很抱歉，我正在经历一些技术问题。请稍后再试或者提供更简单的指令。"
            }
            
    except Exception as e:
        # 全局异常处理，始终确保返回有效响应
        logger.error(f"聊天处理全局异常: {str(e)}")
        return {
            "message": f"非常抱歉，服务器在处理您的请求时遇到问题。请稍后再试。"
        }

async def handle_route_planning(content: str, model: str):
    """处理路线规划请求"""
    try:
        import json
        from fastapi import Request as FastAPIRequest
        
        # 创建一个模拟的Request对象
        class MockRequest(FastAPIRequest):
            async def json(self):
                return {"text": content, "model": model}
        
        # 导入路由规划模块中的函数
        from .route_planning import create_route_plan, fallback_route_analysis
        
        # 首先尝试使用fallback方法，这样即使Ollama服务不可用也能返回结果
        logger.info(f"使用备用路线分析方法处理: {content}")
        try:
            result = fallback_route_analysis(content)
            logger.info(f"备用路线分析结果: {result}")
            return {"message": json.dumps(result.__dict__)}
        except Exception as fallback_error:
            logger.error(f"备用路线分析失败: {str(fallback_error)}")
            
            # 如果备用方法失败，尝试原方法
            try:
                mock_request = MockRequest(scope={"type": "http"})
                result = await create_route_plan(mock_request)
                logger.info(f"路线规划结果: {result}")
                return {"message": json.dumps(result.__dict__)}
            except Exception as e:
                logger.error(f"路线规划API调用失败: {str(e)}")
                return {"message": f"处理路线规划请求时出错: {str(e)}"}
    
    except Exception as e:
        logger.error(f"路线规划处理异常: {str(e)}")
        return {
            "message": f"处理路线规划请求时出错: {str(e)}"
        }

@router.get("/completions/history")
async def get_chat_history(type: str = "general"):
    """获取聊天历史"""
    try:
        logger.info(f"获取聊天历史，类型: {type}")
        # 这里可以添加数据库查询逻辑
        history = []  # 暂时返回空列表
        
        # 如果是路线规划类型，尝试获取路线历史
        if type == "route":
            try:
                from .route_planning import get_route_history
                return await get_route_history()
            except Exception as route_error:
                logger.error(f"获取路线规划历史失败: {str(route_error)}")
                # 失败时返回空历史而不是抛出异常
                return {"history": []}
                
        return {"history": history}
    except Exception as e:
        logger.error(f"获取聊天历史异常: {str(e)}")
        # 返回错误信息，但不抛出异常，避免500错误
        return {"history": [], "error": str(e)}