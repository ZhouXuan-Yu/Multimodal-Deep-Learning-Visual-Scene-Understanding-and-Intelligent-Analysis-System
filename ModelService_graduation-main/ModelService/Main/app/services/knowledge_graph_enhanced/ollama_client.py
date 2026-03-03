"""
Ollama客户端 - 连接本地Ollama大语言模型服务
负责文本生成和问答推理
"""

import requests
import json
import logging
from typing import List, Dict, Any, Generator, Optional, Union
import os

# 配置日志
logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, base_url: Optional[str] = None, default_model: Optional[str] = None):
        """初始化Ollama客户端。
        优先使用环境变量 OLLAMA_URL (或 OLLAMA_BASE) 和 OLLAMA_MODEL 来配置。
        """
        # 优先读取环境变量，保持向后兼容
        env_url = os.getenv("OLLAMA_URL") or os.getenv("OLLAMA_BASE")
        if env_url:
            # 如果用户传入了完整的生成接口地址（包含 /api/...），截取 base 部分
            if "/api/" in env_url:
                base = env_url.split("/api/")[0]
            else:
                base = env_url
        else:
            base = base_url or "http://localhost:11434"

        self.base_url = base.rstrip("/")
        self.default_model = default_model or os.getenv("OLLAMA_MODEL") or "qwen3-vl"

        # 验证连接
        try:
            self._verify_connection()
            logger.info(f"✅ Ollama服务连接成功，默认模型: {self.default_model}, base_url: {self.base_url}")
        except Exception as e:
            logger.error(f"⚠️ Ollama服务连接失败: {str(e)}")
    
    def _verify_connection(self):
        """验证Ollama服务连接"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise Exception(f"服务返回状态码: {response.status_code}")
            return True
        except Exception as e:
            raise Exception(f"Ollama服务连接失败: {str(e)}")
    
    def generate(self, prompt: str, model: Optional[str] = None, 
                 stream: bool = False, **kwargs) -> Union[str, Generator[str, None, None]]:
        """生成文本"""
        url = f"{self.base_url}/api/generate"
        
        # 记录请求信息
        logger.info(f"[OLLAMA] 请求生成 - model: {model or self.default_model}, stream: {stream}")
        logger.info(f"[OLLAMA] prompt 内容: {prompt[:200]}..." if len(prompt) > 200 else f"[OLLAMA] prompt 内容: {prompt}")
        
        payload = {
            "model": model or self.default_model,
            "prompt": prompt,
            "stream": stream,
            **kwargs
        }
        
        if not stream:
            try:
                response = requests.post(url, json=payload, timeout=60)
                response.raise_for_status()
                result = response.json().get("response", "")
                logger.info(f"[OLLAMA] 生成成功，结果长度: {len(result)} 字符")
                logger.info(f"[OLLAMA] 生成结果预览: {result[:200]}..." if len(result) > 200 else f"[OLLAMA] 生成结果: {result}")
                return result
            except Exception as e:
                logger.error(f"❌ Ollama生成失败: {str(e)}")
                return f"生成失败: {str(e)}"
        else:
            return self._stream_generate(url, payload)
    
    def _stream_generate(self, url: str, payload: Dict[str, Any]) -> Generator[str, None, None]:
        """流式生成文本"""
        logger.info(f"[OLLAMA] 开始流式生成，model: {payload.get('model')}")
        try:
            response = requests.post(url, json=payload, stream=True, timeout=60)
            response.raise_for_status()
            
            chunk_count = 0
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    content = chunk.get("response", "")
                    if content:
                        chunk_count += 1
                        logger.info(f"[OLLAMA] 流式分片 #{chunk_count}: {content[:100]}...")
                        yield content
                    # 如果是最后一个消息
                    if chunk.get("done", False):
                        logger.info(f"[OLLAMA] 流式生成完成，共 {chunk_count} 个分片")
                        break
        except Exception as e:
            logger.error(f"❌ Ollama流式生成失败: {str(e)}")
            yield f"生成失败: {str(e)}"
    
    def generate_with_context(self, query: str, context: Union[str, List[Dict[str, Any]]], 
                              model: Optional[str] = None, stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """使用上下文生成回答"""
        # 如果context是文档列表，转换为文本
        if isinstance(context, list):
            # 提取文本并按分数排序
            context_text = "\n\n".join([
                f"文档 {i+1}:\n{doc.get('text', '')}" 
                for i, doc in enumerate(sorted(context, key=lambda x: x.get('score', 0), reverse=True))
            ])
        else:
            context_text = context
        
        prompt = f"""基于以下参考资料回答用户问题。
        如果参考资料中没有相关信息，请告知用户你不知道，不要编造答案。
        
        参考资料:
        {context_text}
        
        用户问题: {query}
        回答:"""
        
        return self.generate(prompt, model, stream)
    
    def list_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            # Ollama 的 tags 接口可能返回不同结构，尽量兼容
            payload = response.json()
            models = payload.get("models") or payload.get("tags") or payload
            logger.info(f"获取到可用模型信息: {type(models)}")
            return models if isinstance(models, list) else []
        except Exception as e:
            logger.error(f"❌ 获取模型列表失败: {str(e)}")
            return []

# 创建单例实例
try:
    ollama_client = OllamaClient()
    logger.info("Ollama客户端初始化成功")
except Exception as e:
    logger.error(f"⚠️ Ollama客户端初始化失败: {str(e)}")
    ollama_client = None
