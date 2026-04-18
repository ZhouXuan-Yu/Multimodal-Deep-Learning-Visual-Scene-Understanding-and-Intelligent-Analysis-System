from fastapi import APIRouter, UploadFile, File, Form
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/simple-test")
async def test_endpoint():
    """简单的测试端点 - 确认路由注册是否正常工作"""
    logger.info("✅ 测试端点被访问了")
    return {"status": "success", "message": "测试端点工作正常"}

@router.post("/simple-upload")
async def test_upload_endpoint(file: UploadFile = File(...)):
    """简单的文件上传测试端点"""
    content = await file.read()
    file_size = len(content)
    logger.info(f"✅ 文件上传测试端点被访问了: 文件名={file.filename}, 大小={file_size}字节")
    return {
        "status": "success", 
        "filename": file.filename,
        "size_bytes": file_size
    }
