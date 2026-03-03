from pathlib import Path

from ultralytics import YOLO


def main():
    """
    简单本地测试脚本：
    - 调用电脑摄像头进行火焰/烟雾检测
    - 使用与后端相同的权重文件路径
    """
    # 项目根目录：当前这个 detect.py 所在目录
    project_root = Path(__file__).resolve().parent

    # 与后端 fire_detector.py 中 MODEL_DIR 保持一致：
    # ModelService/Main/models/fire_detection/fire_smoke_v11.pt
    weights_path = (
        project_root
        / "ModelService"
        / "Main"
        / "models"
        / "fire_detection"
        / "fire_smoke_v11.pt"
    )

    if not weights_path.exists():
        raise FileNotFoundError(
            f"未找到权重文件：{weights_path}\n"
            f"请从 Roboflow Universe 下载 Fire+Smoke 模型（如 best.pt 或 fire_smoke_v11.pt），"
            f"并重命名为 fire_smoke_v11.pt 放到上述目录。"
        )

    # 1. 加载模型
    model = YOLO(str(weights_path))

    # 2. 开启预测：source='0' 表示默认摄像头，conf=0.4 为置信度阈值
    # show=True 会弹出实时检测窗口
    model.predict(source=0, show=True, conf=0.4)


if __name__ == "__main__":
    main()

