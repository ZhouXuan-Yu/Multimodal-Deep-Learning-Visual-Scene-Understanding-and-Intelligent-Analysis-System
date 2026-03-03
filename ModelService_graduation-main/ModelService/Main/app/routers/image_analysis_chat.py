from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel, Field
import requests
import logging
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色，如 'user' 或 'assistant'")
    content: str = Field(..., description="消息内容")

class ChatRequest(BaseModel):
    message: str = Field(..., description="用户发送的消息")
    model: str = Field(default="qwen2.5:3b", description="使用的模型名称")
    temperature: float = Field(default=0.7, ge=0, le=1, description="温度参数")

class Person(BaseModel):
    id: Optional[int] = None
    age: float = Field(default=0, description="年龄")
    age_confidence: float = Field(default=1.0, description="年龄置信度")
    gender: str = Field(default="unknown", description="性别")
    gender_confidence: float = Field(default=0, description="性别置信度")
    upper_color: str = Field(default="unknown", description="上衣颜色")
    upper_color_confidence: float = Field(default=0, description="上衣颜色置信度")
    lower_color: str = Field(default="unknown", description="下衣颜色")
    lower_color_confidence: float = Field(default=0, description="下衣颜色置信度")
    bbox: List[float] = Field(default=[0, 0, 0, 0], description="边界框坐标")

class AnalysisResult(BaseModel):
    persons: List[Person] = Field(default_factory=list, description="检测到的人物列表")
    detected: int = Field(default=0, description="检测到的人物数量")

class ImageAnalysisContext(BaseModel):
    currentAnalysis: AnalysisResult = Field(default_factory=AnalysisResult, description="当前分析结果")
    analysisHistory: List[AnalysisResult] = Field(default_factory=list, description="分析历史记录")

class ImageAnalysisRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="聊天消息列表")
    model: str = Field(default="qwen2.5:3b", description="使用的模型名称")
    temperature: float = Field(default=0.7, ge=0, le=1, description="温度参数")
    stream: bool = Field(default=False, description="是否使用流式输出")
    context: ImageAnalysisContext = Field(..., description="分析上下文")

def build_system_message(context: ImageAnalysisContext) -> str:
    """构建包含分析数据的系统消息"""
    persons = context.currentAnalysis.persons
    
    people_info = []
    for i, person in enumerate(persons, 1):
        info = f"""### 人物{i}
- **年龄**：{person.age:.1f}岁（置信度：{person.age_confidence * 100:.1f}%）
- **性别**：{person.gender}（置信度：{person.gender_confidence * 100:.1f}%）
- **上装**：{person.upper_color}（置信度：{person.upper_color_confidence * 100:.1f}%）
- **下装**：{person.lower_color}（置信度：{person.lower_color_confidence * 100:.1f}%）"""
        people_info.append(info)
    
    people_info_str = "\n\n".join(people_info) if people_info else "暂无人物分析数据"
    
    # 构建系统提示词
    system_prompt = f"""你是一个专业、友好的图像分析助手。我会为你提供当前图片的分析数据作为知识补充，请在回答用户问题时使用 Markdown 格式输出。

## 当前图片分析数据
**检测到的人物数量**：{len(persons)}

{people_info_str}

### 回答指南
1. 使用 Markdown 格式回答，包括：
   - 使用标题层级（#）组织内容
   - 使用列表（- 或 1.）展示信息
   - 使用粗体（**）强调重要信息
   - 使用表格展示对比数据
   - 适当使用引用（>）突出重要提示

2. 当用户询问图片相关信息时：
   - 准确引用分析数据
   - 使用 [MATCH_ID:序号] 标记具体人物
   - 将 unknown 或 null 表述为"未知"
   - 可以补充一些合理的观察和建议

3. 当用户询问与图片无关的问题：
   - 正常回答问题
   - 如果可以，自然地联系到图片内容

4. 如果没有分析数据：
   - 告知用户需要先分析图片
   - 提供上传和分析图片的指导

### 示例回答格式：

用户：图片里有几个人？
助手：
## 人物统计
在这张图片中，我检测到了 2 个人物。让我为您详细介绍：

1. [MATCH_ID:1] 第一位人物
   - 年龄：25岁
   - 性别：男性
   - 着装：红色上衣，蓝色下装

2. [MATCH_ID:2] 第二位人物
   - 年龄：30岁
   - 性别：女性
   - 着装：白色上衣，黑色下装

用户：谁穿着红色上衣？
助手：
### 着装分析
经过查找，[MATCH_ID:1] 这位 25 岁的男性穿着**红色上衣**，搭配蓝色下装。

> 💡 这种搭配看起来很有活力，红色上衣能够突出个人特色。

用户：这些人在做什么？
助手：
### 场景分析
抱歉，我只能分析出人物的基本特征，如年龄、性别和服装颜色。具体的动作和场景信息需要您自己观察判断。

不过从我检测到的信息来看：
- [MATCH_ID:1] 这位人物...
- [MATCH_ID:2] 另一位人物..."""

    return system_prompt

async def call_ollama_api(message: str) -> str:
    """调用 Ollama API"""
    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "qwen2.5:3b",
                "messages": [
                    {
                        "role": "user",
                        "content": message
                    }
                ]
            },
            timeout=180
        )
        response.raise_for_status()
        result = response.json()
        
        if "message" not in result:
            raise ValueError("Ollama API 返回格式异常")
            
        return result["message"]["content"]
        
    except Exception as e:
        logger.error(f"调用 Ollama API 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        logger.info(f"接收到聊天请求: {request.message}")
        
        # 调用 Ollama API
        logger.info("正在调用 Ollama API...")
        response = await call_ollama_api(request.message)
        
        # 打印完整的 API 响应
        logger.info(f"Ollama API 完整响应: {response}")
        
        return {
            "success": True,
            "data": response
        }
    except Exception as e:
        logger.error(f"聊天请求处理失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def stream_ollama_response(messages, model, temperature=0.7):
    """流式输出Ollama API响应"""
    ollama_request = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": temperature
        }
    }
    
    try:
        with requests.post(
            "http://localhost:11434/api/chat",
            json=ollama_request,
            stream=True,
            timeout=300
        ) as response:
            if response.status_code != 200:
                error_content = response.content.decode('utf-8')
                yield f"错误: {error_content}"
                return
                
            for line in response.iter_lines():
                if line:
                    try:
                        json_line = json.loads(line)
                        if "message" in json_line and "content" in json_line["message"]:
                            token = json_line["message"]["content"]
                            if token:
                                yield token
                    except json.JSONDecodeError:
                        logger.error(f"无法解析JSON: {line}")
                        continue
    except Exception as e:
        logger.error(f"流式输出异常: {str(e)}")
        yield f"\n\n获取响应时发生错误: {str(e)}"

@router.post("/stream")
async def image_analysis_chat_stream(request: Request):
    """图片分析聊天流式输出"""
    try:
        # 解析请求数据
        data = await request.json()
        messages = data.get("messages", [])
        context = data.get("context", {"currentAnalysis": {"persons": [], "detected": 0}})
        model = data.get("model", "qwen2.5:3b")
        temperature = data.get("temperature", 0.7)
        
        # 检查上下文数据格式
        current_analysis = ImageAnalysisContext(
            currentAnalysis=AnalysisResult(**context["currentAnalysis"]),
            analysisHistory=[]
        )
        
        # 构建系统消息
        system_message = {
            "role": "system",
            "content": build_system_message(current_analysis)
        }
        
        # 准备发送给 Ollama 的数据
        ollama_messages = [system_message]
        ollama_messages.extend(messages)
        
        # 流式响应
        return StreamingResponse(
            stream_ollama_response(ollama_messages, model, temperature),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"流式聊天请求处理失败: {str(e)}")
        return StreamingResponse(
            iter([f"错误: {str(e)}"]),
            media_type="text/plain"
        )

@router.post("/completions")
async def image_analysis_chat(request: ImageAnalysisRequest):
    """图片分析聊天"""
    try:
        print("\n=== 接收到新的聊天请求 ===")
        logger.info("接收到新的聊天请求")
        
        # 打印请求信息
        print(f"用户消息: {request.messages[-1].content if request.messages else 'No message'}")
        print(f"检测到的人数: {request.context.currentAnalysis.detected}")
        print(f"模型: {request.model}")
        print(f"是否流式输出: {request.stream}")
        
        # 如果请求流式输出，重定向到流式端点
        if request.stream:
            logger.info("请求流式输出，重定向到流式端点")
            return await image_analysis_chat_stream(Request(scope={"type": "http"}))
        
        # 验证并转换分析结果中的人物数据
        current_analysis = request.context.currentAnalysis
        persons_data = []
        
        for person_data in current_analysis.persons:
            # 使用 Person 模型创建新的对象，确保所有字段都有默认值
            person = Person(
                id=person_data.id if hasattr(person_data, 'id') else None,
                age=float(person_data.age) if hasattr(person_data, 'age') else 0.0,
                age_confidence=float(person_data.age_confidence) if hasattr(person_data, 'age_confidence') else 1.0,
                gender=person_data.gender if hasattr(person_data, 'gender') else "unknown",
                gender_confidence=float(person_data.gender_confidence) if hasattr(person_data, 'gender_confidence') else 0.0,
                upper_color=person_data.upper_color if hasattr(person_data, 'upper_color') else "unknown",
                upper_color_confidence=float(person_data.upper_color_confidence) if hasattr(person_data, 'upper_color_confidence') else 0.0,
                lower_color=person_data.lower_color if hasattr(person_data, 'lower_color') else "unknown",
                lower_color_confidence=float(person_data.lower_color_confidence) if hasattr(person_data, 'lower_color_confidence') else 0.0,
                bbox=person_data.bbox if hasattr(person_data, 'bbox') else [0, 0, 0, 0]
            )
            persons_data.append(person)
        
        # 更新 currentAnalysis 的 persons 列表
        request.context.currentAnalysis.persons = persons_data
        
        # 验证 Ollama 服务是否可用
        try:
            health_check = requests.get("http://localhost:11434/api/health", timeout=5)
            print(f"Ollama 服务状态: {health_check.status_code}")
        except Exception as e:
            print(f"Ollama 服务检查失败: {str(e)}")
            raise HTTPException(status_code=503, detail="Ollama 服务不可用")

        # 构建系统消息
        system_message = {
            "role": "system",
            "content": build_system_message(request.context)
        }

        # 准备发送给 Ollama 的数据
        messages = [system_message]
        messages.extend([{"role": msg.role, "content": msg.content} for msg in request.messages])
        
        ollama_request = {
            "model": request.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature
            }
        }

        # 发送请求到 Ollama
        print("\n[发送] 正在调用 Ollama API...")
        try:
            response = requests.post(
                "http://localhost:11434/api/chat",
                json=ollama_request,
                timeout=180
            )
            print(f"[响应] 状态码: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[错误] 非200响应: {response.text}")
                raise HTTPException(status_code=response.status_code, 
                                  detail=f"Ollama API 返回错误: {response.text}")
            
            result = response.json()
            print(f"[成功] 收到响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            return {
                "content": result["message"]["content"],
                "status": 200
            }
        except Exception as e:
            print(f"[错误] 调用 Ollama API 失败: {str(e)}")
            raise

    except Exception as e:
        print(f"[错误] 处理请求失败: {str(e)}")
        logger.error(f"处理请求时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))