"""
修复 route_planning.py 中的 _make_event_generator_for 函数
"""
import re

# 读取文件
file_path = r"D:\ModelService_graduation-main\ModelService_graduation-main\ModelService\Main\app\routers\route_planning.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 旧的代码模式
old_code = '''                for part in ollama_generate_stream(formatted_prompt, model=model):
                    if part:
                        # 先打印到后端日志
                        logger.info(f"[STREAM Ollama 后端] {part}")
                        # 稍微延时，确保后端先打印
                        import time
                        time.sleep(0.05)
                        # 再发送到前端
                    yield f"data: {json.dumps({'event':'chunk','content': part})}\\n\\n"
                
                logger.info(f"[STREAM] Ollama 流式生成完成")'''

# 新的代码
new_code = '''                full_response = ""
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
                logger.info(f"[STREAM] =========================================")'''

# 替换
if old_code in content:
    new_content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Code replaced successfully!")
else:
    print("WARNING: Old code pattern not found!")
    # 尝试查找部分匹配
    if 'ollama_generate_stream' in content:
        print("Found 'ollama_generate_stream' in file")
    if 'STREAM Ollama' in content:
        print("Found 'STREAM Ollama' in file")




