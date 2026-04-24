"""
图像识别路由 (person_recognition.py)

使用 Qwen3-VL 视觉大模型进行人物检测 + 属性识别。

策略：Qwen3-VL 在结构化 JSON 输出上不稳定，因此采用两步法：
  Step 1: 请求自然语言图像描述
  Step 2: 从文字描述中解析结构化数据

支持模式：
  - normal    : 仅 Qwen3-VL
  - enhanced  : 同 normal（Qwen3-VL 已是最强视觉分析）
"""
import os
import re
import json
import time
import base64
import logging
import warnings
import io
from typing import List, Dict, Any, Tuple
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import requests  # 使用 requests 而非 urllib（确保 Ollama 图片处理正常）

logger = logging.getLogger(__name__)
router = APIRouter()

# ─────────────────────────────────────────────────────────────
# 1. 全局配置
# ─────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.parent.parent
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3-vl:8b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT_S", "120"))

# 颜色标准映射
STANDARD_COLORS = {
    "红": "red", "黄": "yellow", "蓝": "blue", "绿": "green",
    "黑": "black", "白": "white", "灰": "gray", "紫": "purple",
    "橙": "orange", "粉": "pink", "棕": "brown", "青": "cyan",
    "red": "red", "yellow": "yellow", "blue": "blue", "green": "green",
    "black": "black", "white": "white", "gray": "gray", "grey": "gray",
    "purple": "purple", "orange": "orange", "pink": "pink", "brown": "brown",
    "cyan": "cyan",
    "深红": "darkred", "浅蓝": "lightblue", "深蓝": "darkblue",
    "浅灰": "lightgray", "暗红": "darkred",
}

COLOR_EN_TO_CN = {
    "red": "红色", "darkred": "深红色",
    "blue": "蓝色", "darkblue": "深蓝色", "lightblue": "浅蓝色",
    "green": "绿色",
    "yellow": "黄色",
    "orange": "橙色",
    "purple": "紫色",
    "pink": "粉色",
    "brown": "棕色",
    "black": "黑色",
    "white": "白色",
    "gray": "灰色", "grey": "灰色", "lightgray": "浅灰色",
    "cyan": "青色",
}

# ─────────────────────────────────────────────────────────────
# 2. 工具函数
# ─────────────────────────────────────────────────────────────
def standardize_color(color: Any, default: str = "gray") -> str:
    if not color:
        return default
    c = str(color).strip().lower()
    return STANDARD_COLORS.get(c, c)


def translate_color(color: Any, to_chinese: bool = False) -> str:
    c = standardize_color(color)
    if to_chinese:
        return COLOR_EN_TO_CN.get(c, c)
    return c


def parse_age(raw_age: Any) -> int:
    if raw_age is None:
        return 0
    s = str(raw_age).strip()
    if "-" in s:
        parts = s.replace("+", "").split("-")
        try:
            return (int(parts[0]) + int(parts[-1])) // 2
        except Exception:
            pass
    s = s.replace("+", "")
    try:
        return int(float(s))
    except Exception:
        return 0


def clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(val, hi))


def iou_xyxy(a: List[float], b: List[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def nms_boxes(boxes: List[List[float]], iou_thresh: float = 0.5) -> List[List[float]]:
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
    keep = []
    for b in boxes:
        if not any(iou_xyxy(b, k) > iou_thresh for k in keep):
            keep.append(b)
    return keep


def get_image_dimensions(image_bytes: bytes) -> Tuple[int, int]:
    try:
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            import struct
            w = struct.unpack(">I", image_bytes[16:20])[0]
            h = struct.unpack(">I", image_bytes[20:24])[0]
            return int(w), int(h)
        img = Image.open(io.BytesIO(image_bytes))
        return img.width, img.height
    except Exception:
        return 1920, 1080


# ─────────────────────────────────────────────────────────────
# 3. Qwen3-VL 调用（两步法：文字描述 → 结构化解析）
# ─────────────────────────────────────────────────────────────
DESCRIPTION_PROMPT = """请仔细分析这张图像，详细描述图中所有人物的特征。
对于图中的每个人物，请按以下格式描述：
[人物N]
性别: male/female
年龄: 具体数字
上衣: 具体颜色
下装: 具体颜色

只描述你确定的人物，不要编造。如果图中有N个人，就描述N个。"""


def call_qwen_describe(image_bytes: bytes) -> str:
    """
    调用 Qwen3-VL 获取自然语言图像描述。
    使用 /api/chat 接口 + requests。
    """
    try:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
    except Exception as e:
        return f"[ERROR: 图片编码失败: {e}]"

    messages = [
        {"role": "system", "content": "你是一个严谨的图像分析助手。只描述图中真实可见的内容，不要编造。"},
        {"role": "user", "content": DESCRIPTION_PROMPT, "images": [b64]},
    ]

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "messages": messages,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 1024,
                },
            },
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        return f"[ERROR: Ollama 请求失败: {e}]"

    content = ""
    if isinstance(result, dict):
        msg = result.get("message") or {}
        content = msg.get("content", "") or ""

    if not content:
        return "[ERROR: Ollama 返回空内容]"
    return content


# ─────────────────────────────────────────────────────────────
# 4. 自然语言 → 结构化数据解析
# ─────────────────────────────────────────────────────────────
def parse_description_to_structured(
    description: str, img_w: int, img_h: int
) -> Dict[str, Any]:
    """
    从 Qwen3-VL 的文字描述中解析出结构化人物数据。
    采用多策略解析：
      1. 正则匹配 [人物N] / Person N / 人物 N
      2. 提取 gender, age, upper/lower clothing color
      3. 智能估计 bbox（按人数均分图像宽度）
    """
    persons: List[Dict[str, Any]] = []

    # 检测有多少个人
    person_patterns = [
        r'\[人物\s*(\d+)\]', r'人物\s*(\d+)', r'Person\s*(\d+)',
        r'person\s*(\d+)', r'第\s*(\d+)\s*个?[人物人物]',
        r'共\s*(\d+)\s*个?人', r'(\d+)\s*个?人',
    ]
    max_person = 0
    for pattern in person_patterns:
        matches = re.findall(pattern, description, re.IGNORECASE)
        for m in matches:
            try:
                n = int(m)
                if n > max_person:
                    max_person = n
            except ValueError:
                pass

    # 也按段落计数（每个 [人物N] 或 Person N 出现一次）
    section_matches = re.findall(
        r'\[人物\s*\d+\]|(?:^|\n)(?:人物|Person)\s*\d+',
        description, re.IGNORECASE | re.MULTILINE
    )
    if len(section_matches) > max_person:
        max_person = len(section_matches)

    # 如果正则没找到，尝试从描述推断（常见人群数量词）
    if max_person == 0:
        count_words = re.findall(
            r'(?:一个人|两个人|三个人|四个人|五个人|六个人|单人|多人|一个人物|两个人物)',
            description
        )
        if count_words:
            w = count_words[0]
            if '一' in w or '单' in w: max_person = 1
            elif '两' in w: max_person = 2
            elif '三' in w: max_person = 3
            elif '四' in w: max_person = 4
            elif '五' in w: max_person = 5
            elif '六' in w: max_person = 6

    if max_person == 0:
        # 没有任何人物信息
        return {"detected": 0, "persons": [], "raw_description": description}

    logger.info(f"[person_recognition] 从描述中解析到 {max_person} 个人")

    # 性别解析
    def parse_gender(block: str) -> Tuple[str, float]:
        block_lower = block.lower()
        if re.search(r'\b(男|male|man|男性)\b', block_lower):
            return "male", 0.85
        if re.search(r'\b(女|female|woman|女性|lady)\b', block_lower):
            return "female", 0.85
        return "unknown", 0.0

    # 年龄解析
    def parse_age_str(block: str) -> Tuple[int, float]:
        # 匹配 "年龄: 25" 或 "25岁" 或 "20多岁"
        m = re.search(r'年龄[:：]\s*(\d+)', block)
        if m:
            return int(m.group(1)), 0.8
        m = re.search(r'(\d+)\s*岁', block)
        if m:
            return int(m.group(1)), 0.8
        m = re.search(r'(\d+)\s*多?岁', block)
        if m:
            return int(m.group(1)), 0.6
        return 0, 0.0

    # 颜色解析
    COLOR_KEYWORDS = {
        'black': ['黑', 'black'],
        'white': ['白', 'white'],
        'gray': ['灰', 'gray', 'grey'],
        'red': ['红', 'red'],
        'blue': ['蓝', 'blue'],
        'green': ['绿', 'green'],
        'yellow': ['黄', 'yellow'],
        'orange': ['橙', 'orange'],
        'purple': ['紫', 'purple'],
        'pink': ['粉', 'pink'],
        'brown': ['棕', 'brown'],
        'cyan': ['青', 'cyan'],
        'darkblue': ['深蓝', '藏青', 'dark blue'],
        'lightblue': ['浅蓝', '淡蓝', 'light blue'],
    }

    def parse_color(block: str, region: str) -> Tuple[str, float]:
        """从文字块中提取衣服颜色。region='upper' 或 'lower'。"""
        block_lower = block.lower()
        # 先看明确说的
        for color, keywords in COLOR_KEYWORDS.items():
            for kw in keywords:
                # 找 "上衣: 蓝色" 或 "穿蓝色"
                upper_patterns = [
                    rf'上衣[:：]\s*{re.escape(kw)}',
                    rf'穿\s*{re.escape(kw)}',
                    rf'{re.escape(kw)}\s*色',
                ]
                lower_patterns = [
                    rf'下装[:：]\s*{re.escape(kw)}',
                    rf'穿\s*{re.escape(kw)}',
                ]
                if region == 'upper':
                    for p in upper_patterns:
                        if re.search(p, block_lower):
                            return color, 0.9
                else:
                    for p in lower_patterns:
                        if re.search(p, block_lower):
                            return color, 0.9
        return "gray", 0.3

    # 按段落分割（每个 [人物N] 开始一段）
    sections = re.split(r'\[人物\s*\d+\]', description)
    # 第一个元素是前言，忽略；从第二个开始是每个人物
    sections = [s.strip() for s in sections[1:] if s.strip()]

    # 如果分段数量 == 人数，用分段；否则按人数均分
    if len(sections) == max_person:
        blocks = sections
    else:
        # 简单策略：把所有描述当做一个块处理
        blocks = [description] * max_person

    # 均分图像宽度估算 bbox
    # 假设人物从左到右排列
    margin = int(img_w * 0.05)
    usable_w = img_w - 2 * margin
    per_person_w = usable_w // max_person
    per_person_h = int(img_h * 0.75)
    y2 = int(img_h * 0.9)
    y1 = y2 - per_person_h

    for i in range(max_person):
        if i < len(blocks):
            block = blocks[i]
        else:
            block = description  # 回退

        gender, g_conf = parse_gender(block)
        age, a_conf = parse_age_str(block)
        upper_color, uc_conf = parse_color(block, "upper")
        lower_color, lc_conf = parse_color(block, "lower")

        x1 = margin + i * per_person_w
        x2 = x1 + per_person_w
        x1 = clamp(x1, 0, img_w - 1)
        x2 = clamp(x2, 0, img_w)

        person = {
            "gender": gender,
            "gender_confidence": g_conf,
            "age": age if age > 0 else parse_age_from_desc(block),
            "age_confidence": a_conf if age > 0 else 0.4,
            "upper_color": upper_color,
            "upper_color_confidence": uc_conf,
            "lower_color": lower_color,
            "lower_color_confidence": lc_conf,
            "confidence": max(g_conf, uc_conf, lc_conf),
            "bbox": [x1, y1, x2, y2],
        }

        logger.info(
            f"  人物{i+1}: gender={gender}, age={person['age']}, "
            f"upper={upper_color}, lower={lower_color}, "
            f"bbox=[{x1},{y1},{x2},{y2}]"
        )
        persons.append(person)

    return {"detected": len(persons), "persons": persons}


def parse_age_from_desc(block: str) -> int:
    """从描述块中用更宽松的方式提取年龄。"""
    # 尝试各种年龄表述
    patterns = [
        r'(\d{1,3})\s*岁',
        r'年龄[:：]\s*(\d+)',
        r'(\d{2})[\s-]?\d{2}\s*岁',
    ]
    for pat in patterns:
        m = re.search(pat, block)
        if m:
            age = int(m.group(1))
            if 1 <= age <= 100:
                return age
    # 文字描述
    if re.search(r'(年轻|二十|三十|四十|五十)', block):
        if '二十' in block: return 22
        if '三十' in block: return 32
        if '四十' in block: return 42
        if '五十' in block: return 52
        if '年轻' in block: return 25
    return 0


# ─────────────────────────────────────────────────────────────
# 5. 主分析函数
# ─────────────────────────────────────────────────────────────
def analyze_image(image_bytes: bytes) -> Dict[str, Any]:
    """分析图像：两步法（文字描述 → 结构化解析）。"""
    start = time.time()

    img_w, img_h = get_image_dimensions(image_bytes)
    logger.info(f"[person_recognition] 图像尺寸: {img_w}x{img_h}")

    # Step 1: 获取 Qwen3-VL 的文字描述
    description = call_qwen_describe(image_bytes)
    logger.info(f"[person_recognition] Qwen3-VL 描述: {description[:200]}")

    if description.startswith("[ERROR"):
        return {
            "error": description,
            "detected": 0,
            "persons": [],
            "processing_time": time.time() - start,
            "mode": "qwen3-vl",
        }

    # Step 2: 从描述解析结构化数据
    result = parse_description_to_structured(description, img_w, img_h)
    result["processing_time"] = time.time() - start
    result["mode"] = "qwen3-vl"

    logger.info(
        f"[person_recognition] 分析完成: {result.get('detected', 0)} 人, "
        f"耗时 {result['processing_time']:.2f}s"
    )
    return result


# ─────────────────────────────────────────────────────────────
# 6. FastAPI 路由
# ─────────────────────────────────────────────────────────────
@router.post("/analyze")
async def analyze_image_endpoint(
    file: UploadFile = File(...),
    mode: str = Form(default="normal"),
):
    """
    图像分析端点（两步法：Qwen3-VL 文字描述 → 结构化解析）。
    """
    try:
        if not file.content_type.startswith("image/"):
            raise HTTPException(400, "只支持图片文件")

        contents = await file.read()
        size_kb = len(contents) / 1024
        logger.info(
            f"[person_recognition] 收到分析请求: "
            f"file={file.filename}, size={size_kb:.1f}KB, mode={mode}"
        )

        result = analyze_image(contents)

        if "error" in result:
            raise HTTPException(500, result["error"])

        return JSONResponse({
            "success": True,
            "data": result,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[person_recognition] 分析失败: {e}")
        raise HTTPException(500, str(e))


@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "person_recognition (Qwen3-VL 文字描述法)",
        "ollama_model": OLLAMA_MODEL,
        "ollama_url": OLLAMA_BASE_URL,
    }


@router.get("/models")
async def list_models():
    return {
        "success": True,
        "data": [
            {
                "id": "qwen3-vl:8b",
                "name": "Qwen3-VL 8B (本地 Ollama)",
                "description": "多模态视觉语言模型，通过文字描述法识别人物属性",
                "type": "vision",
            }
        ],
    }
