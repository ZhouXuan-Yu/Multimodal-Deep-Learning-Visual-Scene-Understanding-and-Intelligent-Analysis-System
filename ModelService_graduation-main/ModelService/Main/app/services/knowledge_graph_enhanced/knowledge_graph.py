"""
知识图谱服务 - 使用Neo4j存储和查询知识图谱
负责知识的结构化存储和图形可视化
"""

from neo4j import GraphDatabase
import logging
from typing import List, Dict, Any, Optional

# 配置日志
logger = logging.getLogger(__name__)

class KnowledgeGraph:
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 username: str = "neo4j", 
                 password: str = "123"):
        """初始化Neo4j知识图谱"""
        self.uri = uri
        self.username = username
        self.password = password
        self.driver = None
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            self._verify_connection()
            logger.info("✅ Neo4j连接成功")
            # 确保知识节点约束存在
            self._create_constraints()
        except Exception as e:
            logger.error(f"❌ Neo4j连接失败: {str(e)}")
            raise
    
    def _verify_connection(self):
        """验证Neo4j连接"""
        with self.driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            if record and record["test"] == 1:
                return True
            else:
                raise Exception("Neo4j连接验证失败")
    
    def _create_constraints(self):
        """创建必要的约束"""
        with self.driver.session() as session:
            # 检查是否已存在约束
            check_result = session.run("""
            SHOW CONSTRAINTS
            WHERE name = 'knowledge_node_id'
            """)
            
            # 如果约束不存在，创建约束
            if len(list(check_result)) == 0:
                session.run("""
                CREATE CONSTRAINT knowledge_node_id IF NOT EXISTS 
                FOR (n:Knowledge) REQUIRE n.id IS UNIQUE
                """)
                logger.info("✅ 创建了Knowledge节点ID约束")
    
    def add_knowledge_node(self, node_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """添加知识节点"""
        with self.driver.session() as session:
            try:
                result = session.run(
                    """
                    MERGE (k:Knowledge {id: $id})
                    ON CREATE SET k.text = $text, k.metadata = $metadata, k.created = timestamp()
                    ON MATCH SET k.text = $text, k.metadata = $metadata, k.updated = timestamp()
                    RETURN k
                    """,
                    id=node_id, text=text, metadata=metadata or {}
                )
                return result.single() is not None
            except Exception as e:
                logger.error(f"❌ 添加知识节点失败: {str(e)}")
                return False
    
    def add_relationship(self, source_id: str, target_id: str, 
                         rel_type: str = "RELATED_TO", 
                         properties: Optional[Dict[str, Any]] = None) -> bool:
        """添加关系"""
        with self.driver.session() as session:
            try:
                result = session.run(
                    f"""
                    MATCH (s:Knowledge {{id: $source_id}})
                    MATCH (t:Knowledge {{id: $target_id}})
                    MERGE (s)-[r:{rel_type}]->(t)
                    ON CREATE SET r += $properties, r.created = timestamp()
                    ON MATCH SET r += $properties, r.updated = timestamp()
                    RETURN r
                    """,
                    source_id=source_id, target_id=target_id, properties=properties or {}
                )
                return result.single() is not None
            except Exception as e:
                logger.error(f"❌ 添加关系失败: {str(e)}")
                return False
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """获取节点"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (k:Knowledge {id: $id})
                RETURN k
                """,
                id=node_id
            )
            record = result.single()
            if record:
                node = record["k"]
                return {
                    "id": node["id"],
                    "text": node["text"],
                    "metadata": node.get("metadata", {})
                }
            return None
    
    def get_knowledge_graph(self, central_ids: List[str], depth: int = 2) -> Dict[str, Any]:
        """获取以给定ID为中心的子图"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH path = (k:Knowledge)-[*0..%d]-(related)
                WHERE k.id IN $ids
                RETURN path
                """ % depth,
                ids=central_ids
            )
            
            return self._format_graph_data(result)
    
    def search_nodes(self, text_query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """使用文本搜索节点"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (k:Knowledge)
                WHERE k.text CONTAINS $query
                RETURN k
                LIMIT $limit
                """,
                query=text_query, limit=limit
            )
            
            nodes = []
            for record in result:
                node = record["k"]
                nodes.append({
                    "id": node["id"],
                    "text": node["text"],
                    "metadata": node.get("metadata", {})
                })
            
            return nodes
    
    def _format_graph_data(self, result) -> Dict[str, Any]:
        """将结果格式化为前端可视化格式"""
        nodes = []
        relationships = []
        node_ids = set()
        
        for record in result:
            path = record["path"]
            
            # 处理节点
            for node in path.nodes:
                if node.id not in node_ids:
                    node_ids.add(node.id)
                    
                    # 提取节点属性
                    props = dict(node.items())
                    
                    # 构建节点
                    node_data = {
                        "id": str(node.id),
                        "labels": list(node.labels),
                        "properties": props
                    }
                    
                    nodes.append(node_data)
            
            # 处理关系
            for rel in path.relationships:
                # 构建关系
                rel_data = {
                    "id": str(rel.id),
                    "source": str(rel.start_node.id),
                    "target": str(rel.end_node.id),
                    "type": rel.type,
                    "properties": dict(rel.items())
                }
                
                relationships.append(rel_data)
        
        return {
            "nodes": nodes,
            "relationships": relationships
        }
    
    def delete_node(self, node_id: str) -> bool:
        """删除节点及其关系"""
        with self.driver.session() as session:
            try:
                result = session.run(
                    """
                    MATCH (k:Knowledge {id: $id})
                    DETACH DELETE k
                    RETURN count(k) as deleted
                    """,
                    id=node_id
                )
                record = result.single()
                return record and record["deleted"] > 0
            except Exception as e:
                logger.error(f"❌ 删除节点失败: {str(e)}")
                return False
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()

# 创建单例实例
try:
    knowledge_graph = KnowledgeGraph()
    logger.info("知识图谱服务初始化成功")
except Exception as e:
    logger.error(f"⚠️ Neo4j知识图谱初始化失败: {str(e)}")
    knowledge_graph = None
