"""
修复 route_planning.py - 删除流式输出，直接打印结果
"""
import re

file_path = r"D:\ModelService_graduation-main\ModelService_graduation-main\ModelService\Main\app\routers\route_planning.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================
# 1. 重写 ollama_generate_stream - 只返回最终结果
# ============================================

old_stream_func = '''def ollama_generate_stream(prompt: str, model: str = None):
    """流式调用 Ollama API，返回生成器。"""
    model_to_use = model or OLLAMA_MODEL
    logger.info(f"[OLLAMA STREAM] =========================================")
    logger.info(f"[OLLAMA STREAM] 开始流式生成，模型: {model_to_use}")
    logger.info(f"[OLLAMA STREAM] 提示词长度: {len(prompt)} 字符")
    
    try:
        payload = {
            "model": model_to_use,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.1,
                "top_p": 0.1,
                "num_predict": 2048,
                "num_ctx": 4096,
            }
        }
        logger.info(f"[OLLAMA STREAM] 发送请求到 Ollama (超时300秒)...")
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=300,
            stream=True
        )
        logger.info(f"[OLLAMA STREAM] 响应状态: {resp.status_code}")
        
        if resp.status_code == 200:
            chunk_count = 0
            full_response = ""
            logger.info(f"[OLLAMA STREAM] =========================================")
            logger.info(f"[OLLAMA STREAM] 【思考过程开始】")
            logger.info(f"[OLLAMA STREAM] -----------------------------------------")
            
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line.decode('utf-8'))
                    if 'response' in data:
                        chunk_content = data['response']
                        chunk_count += 1
                        full_response += chunk_content
                        
                        # 打印每个分片内容到后端日志
                        logger.info(f"[OLLAMA STREAM] 分片{chunk_count}: {chunk_content}")
                        
                        # 每50个分片打印进度
                        if chunk_count % 50 == 0:
                            logger.info(f"[OLLAMA STREAM] ...已接收 {chunk_count} 个分片，当前内容长度: {len(full_response)}")
                        
                        yield chunk_content
                    
                    if data.get('done', False):
                        logger.info(f"[OLLAMA STREAM] -----------------------------------------")
                        logger.info(f"[OLLAMA STREAM] 【思考过程结束】")
                        logger.info(f"[OLLAMA STREAM] 共接收 {chunk_count} 个分片")
                        logger.info(f"[OLLAMA STREAM] 完整内容: {full_response}")
                        logger.info(f"[OLLAMA STREAM] =========================================")
                        break
        else:
            logger.error(f"[OLLAMA STREAM] API 错误: {resp.status_code}")
            yield None
    except Exception as e:
        logger.error(f"[OLLAMA STREAM] 调用失败: {e}")
        yield None'''

new_stream_func = '''def ollama_generate_sync(prompt: str, model: str = None) -> str:
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
            logger.error(f"[OLLAMA] API 错误: {resp.status_code} - {resp.text[:200]}")
            return None
            
    except Exception as e:
        logger.error(f"[OLLAMA] 调用失败: {e}")
        return None'''

content = content.replace(old_stream_func, new_stream_func)

# ============================================
# 2. 重写 _make_event_generator_for - 改为同步调用
# ============================================

old_event_gen = '''def _make_event_generator_for(text: str, model: str):
    """返回一个 generator，用于 StreamingResponse；可被多个路由复用"""
    # 每次请求时动态检查 Ollama 状态
    ollama_available = get_ollama_status()
    logger.info(f"[STREAM] Ollama 服务状态: {ollama_available}")
    
    async def generator():
        try:
            yield f"data: {json.dumps({'event':'thinking_start','content':'开始分析用户输入'})}\\n\\n"

            # 使用直接 Ollama API
            if ollama_available:
                logger.info(f"[STREAM] 使用 Ollama 直接 API 流式生成，model={model}")
                formatted_prompt = ROUTE_PROMPT.format(text=text, historical_context="")
                logger.info(f"[STREAM] Ollama prompt: {formatted_prompt[:200]}...")
                
                logger.info(f"[STREAM] 正在等待 Ollama 生成响应...")
                full_response = ""
                chunk_count = 0
                logger.info(f"[STREAM] =========================================")
                logger.info(f"[STREAM] 【Ollama思考过程】开始流式接收...")
                
                for part in ollama_generate_stream(formatted_prompt, model=model):
                    if part:
                        full_response += part
                        chunk_count += 1
                        # 打印每个分片到后端日志
                        logger.info(f"[STREAM] Chunk{chunk_count}: {part}")
                        # 发送到前端
                        yield f"data: {json.dumps({'event':'chunk','content': part})}\\n\\n"
                    else:
                        logger.warning(f"[STREAM] 收到空分片")
                
                logger.info(f"[STREAM] 【Ollama思考过程】结束，共 {chunk_count} 个分片")
                logger.info(f"[STREAM] 完整内容: {full_response}")
                logger.info(f"[STREAM] =========================================")
            else:
                # Ollama 不可用，发送错误消息并停止
                error_msg = "⚠️ Ollama 本地大模型服务未启动，请确保 Ollama 服务正在运行（localhost:11434）"
                logger.error(f"[STREAM] {error_msg}")
                yield f"data: {json.dumps({'event':'error','content': error_msg})}\\n\\n"
                yield "data: [DONE]\\n\\n"
                return

            logger.info(f"[STREAM] 调用 fallback_route_analysis 生成结构化数据...")
            final = fallback_route_analysis(text)
            route_data = final.route_data if hasattr(final, 'route_data') and final.route_data else (final if isinstance(final, dict) else None)
            
            if route_data:
                payload = {"event": "done", "route_data": route_data}
                logger.info(f"[STREAM] 发送结构化 route_data")
            yield f"data: {json.dumps(payload, default=str)}\\n\\n"
            
            yield "data: [DONE]\\n\\n"
        except Exception as e:
            logger.exception(f"[STREAM] 流式处理出错: {str(e)}")
            yield f"data: {json.dumps({'event':'error','content': str(e)})}\\n\\n"
            yield "data: [DONE]\\n\\n"
    
    return generator'''

new_event_gen = '''def _make_event_generator_for(text: str, model: str):
    """
    生成路线规划结果，直接打印到后端日志，不进行流式输出。
    """
    logger.info(f"[规划] =========================================")
    logger.info(f"[规划] 收到请求: {text}")
    
    async def generator():
        try:
            # Step 1: 开始分析
            logger.info(f"[规划] Step 1: 开始分析用户输入")
            yield f"data: {json.dumps({'event':'thinking_start','content':'开始分析...'})}\\n\\n"
            
            # Step 2: 调用 Ollama
            formatted_prompt = ROUTE_PROMPT.format(text=text, historical_context="")
            logger.info(f"[规划] Step 2: 调用 Ollama 模型...")
            logger.info(f"[规划] Prompt: {formatted_prompt[:100]}...")
            
            # 同步调用，直接获取完整结果
            ai_response = ollama_generate_sync(formatted_prompt, model=model)
            
            if ai_response:
                logger.info(f"[规划] AI 响应已接收，长度: {len(ai_response)}")
            else:
                logger.warning(f"[规划] AI 响应为空")
            
            # Step 3: 解析并生成结构化数据
            logger.info(f"[规划] Step 3: 解析路线信息...")
            final = fallback_route_analysis(text)
            route_data = None
            
            if hasattr(final, 'route_data') and final.route_data:
                route_data = final.route_data
            elif isinstance(final, dict):
                route_data = final
            
            if route_data:
                # 打印结构化数据
                logger.info(f"[规划] 结构化路线数据:")
                logger.info(json.dumps(route_data, ensure_ascii=False, indent=2))
                logger.info(f"[规划] =========================================")
                
                # 发送最终结果到前端
                yield f"data: {json.dumps({'event':'done','route_data': route_data})}\\n\\n"
            else:
                logger.error(f"[规划] 无法生成路线数据")
                yield f"data: {json.dumps({'event':'error','content': '无法生成路线数据'})}\\n\\n"
            
            yield "data: [DONE]\\n\\n"
            
        except Exception as e:
            logger.exception(f"[规划] 处理出错: {str(e)}")
            yield f"data: {json.dumps({'event':'error','content': str(e)})}\\n\\n"
            yield "data: [DONE]\\n\\n"
    
    return generator'''

content = content.replace(old_event_gen, new_event_gen)

# ============================================
# 3. 移除旧的 ollama_generate_sync（现在重命名为上面了）
# ============================================

# 删除旧的同步函数（因为我们现在直接用重命名后的）
old_sync_pattern = r'''def ollama_generate_sync\(prompt: str, model: str = None\) -> str:
    """非流式调用 Ollama API，返回完整响应。"""
    model_to_use = model or OLLAMA_MODEL
    
    logger\.info\(f"\[OLLAMA SYNC\] 开始生成，模型: \{model_to_use\}"\)
    logger\.info\(f"\[OLLAMA SYNC\] 提示词长度: \{len\(prompt\)\} 字符\)
    
    # 测试Ollama连接
    try:
        test_resp = requests\.get\("http://localhost:11434/api/tags", timeout=3\)
        logger\.info\(f"\[OLLAMA SYNC\] Ollama状态: \{test_resp\.status_code\}"\)
    except Exception as e:
        logger\.warning\(f"\[OLLAMA SYNC\] Ollama连接测试失败: \{e\}"\)
    
    try:
        payload = \{
            "model": model_to_use,
            "prompt": prompt,
            "stream": False,
            "options": \{
                "temperature": 0\.1,
                "top_p": 0\.1,
                "num_predict": 2048,
                "num_ctx": 4096,
            \}
        \}
        logger\.info\(f"\[OLLAMA SYNC\] 发送请求到 Ollama \(超时180秒\)。\.\.\."\)
        resp = requests\.post\(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=180
        \)
        logger\.info\(f"\[OLLAMA SYNC\] 响应状态码: \{resp\.status_code\}"\)
        
        if resp\.status_code == 200:
            result = resp\.json\(\)\.get\("response", ""\)
            logger\.info\(f"\[OLLAMA SYNC\] Ollama 返回结果 \(长度 \{len\(result\)\}\): \{result\[:100\]\}\.\.\."\)
            return result
        else:
            logger\.error\(f"Ollama API 错误: \{resp\.status_code\} - \{resp\.text\[:200\]\}"\)
            return None
    except Exception as e:
        logger\.error\(f"Ollama API 调用失败: \{e\}"\)
        return None'''

# 替换为空
content = re.sub(old_sync_pattern, '', content)

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: 代码已修复!")
print("- 删除所有流式分片打印")
print("- 改为同步直接调用 Ollama")
print("- 直接打印完整 AI 回复")




