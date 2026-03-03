import os
import sys
import yaml
import torch
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HGTMT_Manager")

class HGTMTManager:
    """HGTMT跟踪器管理工具，用于管理配置、模型和资源"""
    
    def __init__(self, hgtmt_path=None):
        """初始化HGTMT管理器"""
        # 设置HGTMT项目路径
        if hgtmt_path is None:
            self.hgtmt_path = os.path.join(os.getcwd(), "HGTMT-main", "HGTMT-main")
        else:
            self.hgtmt_path = hgtmt_path
            
        # 确保HGTMT路径在系统路径中
        if self.hgtmt_path not in sys.path:
            sys.path.append(self.hgtmt_path)
            
        # 设置配置文件路径
        self.cfg_path = os.path.join(self.hgtmt_path, "tracking", "cfgs", "rgbt_tiny_cfg.yaml")
        
        # 设置模型路径
        self.model_dir = os.path.join(os.getcwd(), "models")
        os.makedirs(self.model_dir, exist_ok=True)
        
        # 检查环境
        self.cuda_available = torch.cuda.is_available()
        self.device = torch.device("cuda:0" if self.cuda_available else "cpu")
        
        # 存储配置和跟踪器
        self.config = None
        self.tracker = None
        
    def check_environment(self):
        """检查运行环境是否满足要求"""
        logger.info(f"检查HGTMT运行环境...")
        
        # 检查HGTMT路径是否存在
        if not os.path.exists(self.hgtmt_path):
            logger.error(f"HGTMT项目路径不存在: {self.hgtmt_path}")
            return False
            
        # 检查配置文件是否存在
        if not os.path.exists(self.cfg_path):
            logger.error(f"HGTMT配置文件不存在: {self.cfg_path}")
            return False
            
        # 检查PyTorch版本
        logger.info(f"PyTorch版本: {torch.__version__}")
        logger.info(f"CUDA可用: {self.cuda_available}")
        if self.cuda_available:
            logger.info(f"CUDA版本: {torch.version.cuda}")
            
        return True
        
    def load_config(self):
        """加载HGTMT配置文件"""
        try:
            with open(self.cfg_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"成功加载配置: {self.cfg_path}")
            return self.config
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            return None
            
    def initialize_tracker(self):
        """初始化HGTMT跟踪器"""
        if not self.check_environment():
            logger.error("环境检查失败，无法初始化跟踪器")
            return None
            
        if self.config is None and not self.load_config():
            logger.error("无法加载配置，无法初始化跟踪器")
            return None
            
        try:
            # 尝试导入HGTMT跟踪器
            from tracking.tracker_rgbt_graph_track_graph_crossmodal2 import Tracker
            
            # 初始化跟踪器
            logger.info("正在初始化HGTMT跟踪器...")
            self.tracker = Tracker(self.config["tracktor"], self.device)
            logger.info("成功初始化HGTMT跟踪器")
            return self.tracker
            
        except ImportError as e:
            logger.error(f"导入HGTMT跟踪器失败: {str(e)}")
            logger.info("请确保HGTMT项目完整且所有依赖已安装")
            return None
        except Exception as e:
            logger.error(f"初始化跟踪器时发生错误: {str(e)}")
            return None
            
    def download_pretrained_models(self):
        """下载预训练模型（如果需要）"""
        # 这里可以添加自动下载HGTMT预训练模型的代码
        # 但HGTMT的模型可能需要手动下载并放置到正确位置
        pass
        
    def get_model_path(self, model_name):
        """获取模型文件路径"""
        return os.path.join(self.model_dir, model_name)
