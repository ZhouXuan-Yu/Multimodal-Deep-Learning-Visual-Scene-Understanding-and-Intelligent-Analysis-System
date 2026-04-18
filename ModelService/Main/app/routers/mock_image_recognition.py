from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


def _generate_mock_persons() -> List[Dict[str, Any]]:
    """生成模拟人物特征数据，尽量贴近真实 image_recognition 返回结构"""
    genders = ["male", "female"]
    colors = ["red", "blue", "green", "black", "white", "yellow", "gray"]

    person_count = random.randint(1, 4)
    persons: List[Dict[str, Any]] = []

    for _ in range(person_count):
        gender = random.choice(genders)
        age = random.randint(18, 65)
        upper_color = random.choice(colors)
        lower_color = random.choice(colors)

        # 生成一个简单的 [x1, y1, x2, y2] 格式 bbox
        x1 = random.randint(50, 200)
        y1 = random.randint(50, 200)
        w = random.randint(80, 200)
        h = random.randint(120, 260)
        bbox = [x1, y1, x1 + w, y1 + h]

        persons.append(
            {
                "gender": gender,
                "gender_confidence": round(random.uniform(0.7, 0.98), 2),
                "age": age,
                "age_confidence": round(random.uniform(0.7, 0.98), 2),
                "upper_color": upper_color,
                "upper_color_confidence": round(random.uniform(0.7, 0.98), 2),
                "lower_color": lower_color,
                "lower_color_confidence": round(random.uniform(0.7, 0.98), 2),
                "confidence": round(random.uniform(0.75, 0.99), 2),
                "bbox": bbox,
            }
        )

    return persons


@router.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    mode: str = Form(default="normal"),
):
    """
    图像分析模拟实现

    当真实 image_recognition 模块加载失败时，由 main.py 通过 mock_image_recognition 作为后备模块使用。
    返回结构尽量保持为:
    {
        "success": true,
        "data": {
            "detected": int,
            "persons": [...],
            "processing_time": float,
            "mode": str,
            "timestamp": str
        }
    }
    以兼容前端 domain 智眸千析 页面和旧 Vue 前端。
    """
    try:
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="只支持图片文件")

        # 这里只做最小处理，不依赖任何重型模型或 GPU
        contents = await file.read()
        file_size_kb = round(len(contents) / 1024, 2)

        logger.info(
            f"[mock_image_recognition] 收到图像分析请求: "
            f"文件名={file.filename}, 大小={file_size_kb}KB, 模式={mode}"
        )

        persons = _generate_mock_persons()

        result: Dict[str, Any] = {
            "detected": len(persons),
            "persons": persons,
            "processing_time": round(random.uniform(0.5, 2.0), 2),
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # 与真实路由保持相同的外层结构：success + data
        return JSONResponse(
            {
                "success": True,
                "message": "使用 mock_image_recognition 返回模拟结果",
                "data": result,
            }
        )
    except HTTPException:
        # 直接抛出 HTTPException
        raise
    except Exception as e:
        logger.error(f"[mock_image_recognition] 图像分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查，供前端 /image-recognition/health 使用"""
    return {
        "success": True,
        "service": "mock_image_recognition",
        "status": "healthy",
        "message": "mock 图像识别服务已就绪（未加载真实模型）",
    }


@router.get("/models")
async def get_available_models():
    """返回可用模型列表的模拟实现"""
    models = [
        {
            "id": "mock_person_attributes",
            "name": "人物属性识别（模拟）",
            "description": "不依赖 GPU 的人物性别、年龄、服装颜色等特征模拟识别模型",
        },
        {
            "id": "mock_pose_detection",
            "name": "姿态检测（模拟）",
            "description": "返回固定关键点结构的姿态检测模拟模型",
        },
    ]
    return {
        "success": True,
        "message": "成功获取可用模型列表（mock_image_recognition）",
        "data": models,
    }

