"""
无人机知识图谱数据设置脚本
用于生成无人机样本数据并导入到Neo4j知识图谱中
"""

import os
import sys
import logging
import time

# 获取项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(project_root)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_knowledge_graph():
    """设置无人机知识图谱"""
    try:
        from app.utils.uav_data_generator import UAVDataGenerator
        from app.utils.uav_data_importer import UAVDataImporter
        from app.services.knowledge_graph_enhanced.knowledge_graph import knowledge_graph
        
        # 检查Neo4j连接
        if not knowledge_graph:
            logger.error("Neo4j知识图谱服务不可用，请确保Neo4j已启动并可访问")
            return False
        
        # 生成数据文件路径
        data_dir = os.path.join(project_root, "ModelService", "Main", "app", "data")
        os.makedirs(data_dir, exist_ok=True)
        data_file = os.path.join(data_dir, "uav_knowledge_data.json")
        
        # 1. 生成无人机数据
        logger.info("正在生成无人机知识数据...")
        generator = UAVDataGenerator()
        data = generator.generate_full_dataset()
        file_path = generator.save_to_file(data)
        logger.info(f"无人机知识数据已生成并保存到: {file_path}")
        logger.info(f"生成了 {len(data['nodes'])} 个节点和 {len(data['relations'])} 个关系")
        
        # 暂停一下，确保文件写入完成
        time.sleep(1)
        
        # 2. 导入数据到Neo4j知识图谱
        logger.info("正在将数据导入到Neo4j知识图谱...")
        importer = UAVDataImporter()
        result = importer.import_from_file(file_path)
        
        logger.info(f"数据导入结果: 成功导入 {result['nodes_imported']} 个节点和 {result['relations_imported']} 个关系")
        
        return True
    except Exception as e:
        logger.error(f"设置无人机知识图谱时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("开始设置无人机知识图谱...")
    success = setup_knowledge_graph()
    if success:
        logger.info("✅ 无人机知识图谱设置完成")
    else:
        logger.error("❌ 无人机知识图谱设置失败")
