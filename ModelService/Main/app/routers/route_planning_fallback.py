from fastapi import APIRouter, Request
from typing import Dict, Any
from datetime import datetime
import re
import logging
import sys

# 设置日志 - 同时配置控制台输出
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # 设置为 DEBUG 级别

# 添加控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(name)s: %(message)s'))
logger.addHandler(console_handler)

# 使用 print 作为备用，确保总是显示
def debug_print(*args, **kwargs):
    print(f"[FALLBACK-DEBUG]", *args, **kwargs)

router = APIRouter()
API_PREFIX = "/api/route"


def parse_route_from_text(text: str) -> tuple:
    """
    从文本中解析起点和终点
    支持的格式:
    - "上海到北京"
    - "从上海到北京"
    - "从上海至北京"
    - "上海至北京"
    - "上海 -> 北京"
    - "从上海出发到北京"
    """
    debug_print("=" * 60)
    debug_print(f"开始解析文本: '{text}'")
    debug_print(f"文本长度: {len(text)}")
    debug_print(f"文本类型: {type(text)}")
    debug_print("=" * 60)
    
    if not text:
        debug_print("收到空文本，使用默认地址: 北京 -> 郑州")
        return "北京", "郑州"

    # 直接使用简单的方法分割 "上海到北京" 这类格式
    # 这种方法比正则更可靠
    debug_print(f"检查是否包含 '到': {'到' in text}")
    if "到" in text:
        parts = text.split("到")
        debug_print(f"按 '到' 分割结果: {parts}")
        if len(parts) >= 2:
            start = parts[0].strip()
            end = parts[-1].strip()
            debug_print(f"提取: start='{start}', end='{end}'")
            debug_print(f"检查: start={bool(start)}, end={bool(end)}, start!=end: {start != end}")
            if start and end and start != end:
                debug_print(f"✅ 使用 '到' 分割解析成功: 起点={start}, 终点={end}")
                return start, end

    # 检查 "至"
    if "至" in text:
        parts = text.split("至")
        debug_print(f"按 '至' 分割结果: {parts}")
        if len(parts) >= 2:
            start = parts[0].strip()
            end = parts[-1].strip()
            if start and end and start != end:
                debug_print(f"✅ 使用 '至' 分割解析成功: 起点={start}, 终点={end}")
                return start, end

    # 检查 "->"
    if "->" in text:
        parts = text.split("->")
        debug_print(f"按 '->' 分割结果: {parts}")
        if len(parts) >= 2:
            start = parts[0].strip()
            end = parts[-1].strip()
            if start and end and start != end:
                debug_print(f"✅ 使用 '->' 分割解析成功: 起点={start}, 终点={end}")
                return start, end

    # 尝试使用正则表达式作为备选
    patterns = [
        # 从X到Y 或 从X至Y
        (r'从(.+?)(?:到|至)(.+)', 2),
        # X到Y 或 X至Y
        (r'(.+?)(?:到|至)(.+)', 2),
        # X -> Y
        (r'(.+?)\s*->\s*(.+)', 2),
        # 从X出发到Y
        (r'从(.+?)出发.*到(.+)', 2),
    ]

    for i, (pattern, group_count) in enumerate(patterns):
        debug_print(f"尝试正则模式 {i+1}: {pattern}")
        match = re.search(pattern, text)
        if match:
            debug_print(f"模式 {i+1} 匹配: groups={match.groups()}")
            start = match.group(1).strip()
            end = match.group(2).strip()
            if start and end and start != end:
                debug_print(f"✅ 使用正则解析成功: 起点={start}, 终点={end}")
                return start, end

    # 如果无法解析，使用默认值
    debug_print(f"❌ 无法解析文本 '{text}'，使用默认地址: 北京 -> 郑州")
    return "北京", "郑州"


@router.post("/plan")
async def fallback_plan(request: Request) -> Dict[str, Any]:
    """
    Fallback route planning endpoint used when the real route_planning
    module cannot be imported (missing dependencies). Returns a simple
    placeholder response so the frontend can continue to function.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    text = body.get("text", "") if isinstance(body, dict) else ""

    # 解析起点和终点
    start_point, end_point = parse_route_from_text(text)

    # Simple dummy route_data
    route_data = {
        "response_text": f"（回退）已为您规划从 {start_point} 到 {end_point} 的路线",
        "recommended_routes": [
            {
                "type": "FALLBACK",
                "name": "默认路线",
                "reason": "后端未加载高级模块，使用占位结果"
            }
        ],
        "route_info": {
            "start_point": start_point,
            "end_point": end_point,
            "waypoints": [],
            "departure_time": "",
            "arrival_time": ""
        }
    }

    return {
        "success": True,
        "route_data": route_data,
        "error": None,
        "note": "使用回退解析：高级路线规划模块不可用，返回占位结果。",
        "used_fallback": True,
        "timestamp": datetime.now().isoformat()
    }





