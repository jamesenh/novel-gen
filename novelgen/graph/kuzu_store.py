"""
Kùzu 图谱存储模块
提供嵌入式图数据库的连接、初始化、Schema 定义和基础查询功能

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-15
"""
import os
import json
import logging
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class KuzuStore:
    """Kùzu 嵌入式图谱存储
    
    每个项目对应一个独立的 Kùzu 数据库实例，存储在 projects/<id>/data/graph/
    """
    
    # Schema 版本号，用于未来的 Schema 迁移
    SCHEMA_VERSION = 1
    
    def __init__(self, graph_dir: str, read_only: bool = False):
        """初始化 Kùzu 存储
        
        Args:
            graph_dir: 图谱存储目录路径
            read_only: 是否以只读模式打开
        """
        self.graph_dir = graph_dir
        self.read_only = read_only
        self._db = None
        self._conn = None
        self._kuzu_available = False
        
        # 尝试导入 kuzu
        try:
            import kuzu
            self._kuzu = kuzu
            self._kuzu_available = True
        except ImportError:
            logger.warning("Kùzu 未安装，图谱功能不可用。请运行: pip install kuzu")
            self._kuzu = None
    
    @property
    def is_available(self) -> bool:
        """检查 Kùzu 是否可用"""
        return self._kuzu_available
    
    def connect(self) -> bool:
        """连接到数据库
        
        Returns:
            连接是否成功
        """
        if not self._kuzu_available:
            return False
        
        try:
            # Kùzu 0.11+ 使用单个数据库文件而非目录
            # 确保父目录存在
            parent_dir = os.path.dirname(self.graph_dir)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            
            # 如果存在同名的空目录（旧版本遗留），删除它
            if os.path.isdir(self.graph_dir):
                import shutil
                # 检查目录是否为空或仅包含旧版 Kùzu 数据
                dir_contents = os.listdir(self.graph_dir)
                if not dir_contents:
                    # 空目录，删除它
                    os.rmdir(self.graph_dir)
                    logger.info(f"已删除空的图谱目录: {self.graph_dir}")
                else:
                    # 非空目录，可能是旧版数据，需要迁移
                    logger.warning(f"发现旧版 Kùzu 目录结构，正在删除并重建...")
                    shutil.rmtree(self.graph_dir)
            
            # 打开数据库（Kùzu 0.11+ 会创建单个数据库文件）
            self._db = self._kuzu.Database(self.graph_dir, read_only=self.read_only)
            self._conn = self._kuzu.Connection(self._db)
            
            logger.info(f"已连接到 Kùzu 数据库: {self.graph_dir}")
            return True
        except Exception as e:
            logger.error(f"连接 Kùzu 数据库失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self._conn is not None:
            self._conn = None
        if self._db is not None:
            self._db = None
    
    def init_schema(self) -> bool:
        """初始化图谱 Schema（幂等操作）
        
        Schema 包含：
        - Character 节点：角色信息
        - Chapter 节点：章节信息
        - Event 节点：事件信息（来自 key_events）
        - RELATES_TO 关系：角色之间的关系
        - PARTICIPATES 关系：角色参与事件
        - OCCURS_IN 关系：事件发生在章节中
        
        Returns:
            初始化是否成功
        """
        if not self._conn:
            logger.error("未连接到数据库，无法初始化 Schema")
            return False
        
        try:
            # 创建 Character 节点表
            self._execute_safe("""
                CREATE NODE TABLE IF NOT EXISTS Character(
                    name STRING PRIMARY KEY,
                    role STRING,
                    gender STRING,
                    age INT64,
                    appearance STRING,
                    personality STRING,
                    background STRING,
                    motivation STRING,
                    abilities STRING,
                    created_at STRING
                )
            """)
            
            # 创建 Chapter 节点表
            self._execute_safe("""
                CREATE NODE TABLE IF NOT EXISTS Chapter(
                    chapter_number INT64 PRIMARY KEY,
                    chapter_title STRING,
                    timeline_anchor STRING,
                    location_summary STRING,
                    summary STRING,
                    created_at STRING
                )
            """)
            
            # 创建 Event 节点表
            self._execute_safe("""
                CREATE NODE TABLE IF NOT EXISTS Event(
                    event_id STRING PRIMARY KEY,
                    description STRING,
                    chapter_number INT64,
                    event_index INT64,
                    evidence_ref STRING,
                    created_at STRING
                )
            """)
            
            # 创建 RELATES_TO 关系表（角色之间的关系）
            self._execute_safe("""
                CREATE REL TABLE IF NOT EXISTS RELATES_TO(
                    FROM Character TO Character,
                    relation_type STRING,
                    description STRING,
                    evidence_ref STRING,
                    created_at STRING
                )
            """)
            
            # 创建 PARTICIPATES 关系表（角色参与事件）
            self._execute_safe("""
                CREATE REL TABLE IF NOT EXISTS PARTICIPATES(
                    FROM Character TO Event,
                    role_in_event STRING,
                    created_at STRING
                )
            """)
            
            # 创建 OCCURS_IN 关系表（事件发生在章节中）
            self._execute_safe("""
                CREATE REL TABLE IF NOT EXISTS OCCURS_IN(
                    FROM Event TO Chapter,
                    created_at STRING
                )
            """)
            
            logger.info("图谱 Schema 初始化成功")
            return True
        except Exception as e:
            logger.error(f"初始化 Schema 失败: {e}")
            return False
    
    def _execute_safe(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """安全执行 Cypher 查询
        
        Args:
            query: Cypher 查询语句
            params: 查询参数
            
        Returns:
            查询结果或 None（出错时）
        """
        if not self._conn:
            logger.error("未连接到数据库")
            return None
        
        try:
            if params:
                result = self._conn.execute(query, params)
            else:
                result = self._conn.execute(query)
            return result
        except Exception as e:
            logger.debug(f"执行查询时出错: {e}\n查询: {query}")
            return None
    
    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """执行 Cypher 查询并返回结果列表
        
        Args:
            query: Cypher 查询语句
            params: 查询参数
            
        Returns:
            结果列表，每个元素为一行数据的字典
        """
        result = self._execute_safe(query, params)
        if result is None:
            return None
        
        try:
            rows = []
            columns = result.get_column_names()
            while result.has_next():
                row = result.get_next()
                rows.append(dict(zip(columns, row)))
            return rows
        except Exception as e:
            logger.error(f"解析查询结果失败: {e}")
            return None
    
    # ==================== Character CRUD ====================
    
    def upsert_character(
        self,
        name: str,
        role: str = "",
        gender: str = "",
        age: Optional[int] = None,
        appearance: str = "",
        personality: str = "",
        background: str = "",
        motivation: str = "",
        abilities: Optional[List[str]] = None
    ) -> bool:
        """插入或更新角色节点
        
        Args:
            name: 角色名称（主键）
            role: 角色定位
            gender: 性别
            age: 年龄
            appearance: 外貌
            personality: 性格
            background: 背景
            motivation: 动机
            abilities: 能力列表
            
        Returns:
            操作是否成功
        """
        from datetime import datetime
        
        abilities_str = json.dumps(abilities or [], ensure_ascii=False)
        created_at = datetime.now().isoformat()
        
        # 使用 MERGE 实现 upsert 语义
        query = """
            MERGE (c:Character {name: $name})
            SET c.role = $role,
                c.gender = $gender,
                c.age = $age,
                c.appearance = $appearance,
                c.personality = $personality,
                c.background = $background,
                c.motivation = $motivation,
                c.abilities = $abilities,
                c.created_at = $created_at
        """
        
        result = self._execute_safe(query, {
            "name": name,
            "role": role,
            "gender": gender,
            "age": age if age is not None else 0,
            "appearance": appearance,
            "personality": personality,
            "background": background,
            "motivation": motivation,
            "abilities": abilities_str,
            "created_at": created_at
        })
        
        return result is not None
    
    def get_character(self, name: str) -> Optional[Dict[str, Any]]:
        """获取角色信息
        
        Args:
            name: 角色名称
            
        Returns:
            角色信息字典或 None
        """
        query = """
            MATCH (c:Character {name: $name})
            RETURN c.name, c.role, c.gender, c.age, c.appearance, 
                   c.personality, c.background, c.motivation, c.abilities
        """
        
        result = self.execute(query, {"name": name})
        if result and len(result) > 0:
            row = result[0]
            # 解析 abilities JSON 字符串
            abilities_str = row.get("c.abilities", "[]")
            try:
                abilities = json.loads(abilities_str) if abilities_str else []
            except json.JSONDecodeError:
                abilities = []
            
            return {
                "name": row.get("c.name"),
                "role": row.get("c.role"),
                "gender": row.get("c.gender"),
                "age": row.get("c.age"),
                "appearance": row.get("c.appearance"),
                "personality": row.get("c.personality"),
                "background": row.get("c.background"),
                "motivation": row.get("c.motivation"),
                "abilities": abilities
            }
        return None
    
    def get_all_characters(self) -> List[Dict[str, Any]]:
        """获取所有角色"""
        query = """
            MATCH (c:Character)
            RETURN c.name, c.role, c.gender
            ORDER BY c.name
        """
        
        result = self.execute(query)
        if result:
            return [
                {
                    "name": row.get("c.name"),
                    "role": row.get("c.role"),
                    "gender": row.get("c.gender")
                }
                for row in result
            ]
        return []
    
    # ==================== Relation CRUD ====================
    
    def upsert_relation(
        self,
        from_name: str,
        to_name: str,
        relation_type: str,
        description: str = "",
        evidence_ref: Optional[Dict[str, Any]] = None
    ) -> bool:
        """插入或更新角色关系
        
        Args:
            from_name: 起始角色名
            to_name: 目标角色名
            relation_type: 关系类型
            description: 关系描述
            evidence_ref: 证据引用
            
        Returns:
            操作是否成功
        """
        from datetime import datetime
        
        evidence_str = json.dumps(evidence_ref or {}, ensure_ascii=False)
        created_at = datetime.now().isoformat()
        
        # 使用 MERGE 实现 upsert 语义
        query = """
            MATCH (a:Character {name: $from_name})
            MATCH (b:Character {name: $to_name})
            MERGE (a)-[r:RELATES_TO]->(b)
            SET r.relation_type = $relation_type,
                r.description = $description,
                r.evidence_ref = $evidence_ref,
                r.created_at = $created_at
        """
        
        result = self._execute_safe(query, {
            "from_name": from_name,
            "to_name": to_name,
            "relation_type": relation_type,
            "description": description,
            "evidence_ref": evidence_str,
            "created_at": created_at
        })
        
        return result is not None
    
    def get_relations(self, name: str, with_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取角色的关系列表
        
        Args:
            name: 角色名称
            with_name: 可选，指定另一个角色名以查询两者之间的关系
            
        Returns:
            关系列表
        """
        if with_name:
            # 查询两个角色之间的直接关系
            query = """
                MATCH (a:Character {name: $name})-[r:RELATES_TO]-(b:Character {name: $with_name})
                RETURN a.name AS from_name, b.name AS to_name, 
                       r.relation_type, r.description, r.evidence_ref
            """
            result = self.execute(query, {"name": name, "with_name": with_name})
        else:
            # 查询角色的所有关系
            query = """
                MATCH (a:Character {name: $name})-[r:RELATES_TO]-(b:Character)
                RETURN a.name AS from_name, b.name AS to_name,
                       r.relation_type, r.description, r.evidence_ref
            """
            result = self.execute(query, {"name": name})
        
        if result:
            relations = []
            for row in result:
                evidence_str = row.get("r.evidence_ref", "{}")
                try:
                    evidence = json.loads(evidence_str) if evidence_str else {}
                except json.JSONDecodeError:
                    evidence = {}
                
                relations.append({
                    "from_name": row.get("from_name"),
                    "to_name": row.get("to_name"),
                    "relation_type": row.get("r.relation_type"),
                    "description": row.get("r.description"),
                    "evidence_ref": evidence
                })
            return relations
        return []
    
    # ==================== Chapter & Event CRUD ====================
    
    def upsert_chapter(
        self,
        chapter_number: int,
        chapter_title: str,
        timeline_anchor: str = "",
        location_summary: str = "",
        summary: str = ""
    ) -> bool:
        """插入或更新章节节点"""
        from datetime import datetime
        
        created_at = datetime.now().isoformat()
        
        query = """
            MERGE (ch:Chapter {chapter_number: $chapter_number})
            SET ch.chapter_title = $chapter_title,
                ch.timeline_anchor = $timeline_anchor,
                ch.location_summary = $location_summary,
                ch.summary = $summary,
                ch.created_at = $created_at
        """
        
        result = self._execute_safe(query, {
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "timeline_anchor": timeline_anchor,
            "location_summary": location_summary,
            "summary": summary,
            "created_at": created_at
        })
        
        return result is not None
    
    def upsert_event(
        self,
        event_id: str,
        description: str,
        chapter_number: int,
        event_index: int,
        evidence_ref: Dict[str, Any]
    ) -> bool:
        """插入或更新事件节点
        
        Args:
            event_id: 事件ID（如 ch1_e1）
            description: 事件描述
            chapter_number: 章节号
            event_index: 事件在章节中的索引
            evidence_ref: 证据引用
        """
        from datetime import datetime
        
        evidence_str = json.dumps(evidence_ref, ensure_ascii=False)
        created_at = datetime.now().isoformat()
        
        query = """
            MERGE (e:Event {event_id: $event_id})
            SET e.description = $description,
                e.chapter_number = $chapter_number,
                e.event_index = $event_index,
                e.evidence_ref = $evidence_ref,
                e.created_at = $created_at
        """
        
        result = self._execute_safe(query, {
            "event_id": event_id,
            "description": description,
            "chapter_number": chapter_number,
            "event_index": event_index,
            "evidence_ref": evidence_str,
            "created_at": created_at
        })
        
        return result is not None
    
    def link_event_to_chapter(self, event_id: str, chapter_number: int) -> bool:
        """将事件链接到章节"""
        from datetime import datetime
        
        created_at = datetime.now().isoformat()
        
        query = """
            MATCH (e:Event {event_id: $event_id})
            MATCH (ch:Chapter {chapter_number: $chapter_number})
            MERGE (e)-[r:OCCURS_IN]->(ch)
            SET r.created_at = $created_at
        """
        
        result = self._execute_safe(query, {
            "event_id": event_id,
            "chapter_number": chapter_number,
            "created_at": created_at
        })
        
        return result is not None
    
    def link_character_to_event(
        self,
        character_name: str,
        event_id: str,
        role_in_event: str = ""
    ) -> bool:
        """将角色链接到事件（参与关系）"""
        from datetime import datetime
        
        created_at = datetime.now().isoformat()
        
        query = """
            MATCH (c:Character {name: $character_name})
            MATCH (e:Event {event_id: $event_id})
            MERGE (c)-[r:PARTICIPATES]->(e)
            SET r.role_in_event = $role_in_event,
                r.created_at = $created_at
        """
        
        result = self._execute_safe(query, {
            "character_name": character_name,
            "event_id": event_id,
            "role_in_event": role_in_event,
            "created_at": created_at
        })
        
        return result is not None
    
    def get_events(
        self,
        character_name: Optional[str] = None,
        chapter_number: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取事件列表
        
        Args:
            character_name: 可选，按角色过滤
            chapter_number: 可选，按章节过滤
            
        Returns:
            事件列表
        """
        if character_name and chapter_number:
            query = """
                MATCH (c:Character {name: $character_name})-[:PARTICIPATES]->(e:Event)-[:OCCURS_IN]->(ch:Chapter {chapter_number: $chapter_number})
                RETURN e.event_id, e.description, e.chapter_number, e.evidence_ref
                ORDER BY e.event_index
            """
            result = self.execute(query, {"character_name": character_name, "chapter_number": chapter_number})
        elif character_name:
            query = """
                MATCH (c:Character {name: $character_name})-[:PARTICIPATES]->(e:Event)
                RETURN e.event_id, e.description, e.chapter_number, e.evidence_ref
                ORDER BY e.chapter_number, e.event_index
            """
            result = self.execute(query, {"character_name": character_name})
        elif chapter_number:
            query = """
                MATCH (e:Event)-[:OCCURS_IN]->(ch:Chapter {chapter_number: $chapter_number})
                RETURN e.event_id, e.description, e.chapter_number, e.evidence_ref
                ORDER BY e.event_index
            """
            result = self.execute(query, {"chapter_number": chapter_number})
        else:
            query = """
                MATCH (e:Event)
                RETURN e.event_id, e.description, e.chapter_number, e.evidence_ref
                ORDER BY e.chapter_number, e.event_index
            """
            result = self.execute(query)
        
        if result:
            events = []
            for row in result:
                evidence_str = row.get("e.evidence_ref", "{}")
                try:
                    evidence = json.loads(evidence_str) if evidence_str else {}
                except json.JSONDecodeError:
                    evidence = {}
                
                events.append({
                    "event_id": row.get("e.event_id"),
                    "description": row.get("e.description"),
                    "chapter_number": row.get("e.chapter_number"),
                    "evidence_ref": evidence
                })
            return events
        return []
    
    # ==================== 清理与重建 ====================
    
    def clear_all(self) -> bool:
        """清除所有数据（保留 Schema）
        
        Returns:
            操作是否成功
        """
        try:
            # 删除所有关系
            self._execute_safe("MATCH ()-[r]->() DELETE r")
            # 删除所有节点
            self._execute_safe("MATCH (n) DELETE n")
            
            logger.info("已清除所有图谱数据")
            return True
        except Exception as e:
            logger.error(f"清除数据失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """获取图谱统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            "characters": 0,
            "chapters": 0,
            "events": 0,
            "relations": 0,
            "participates": 0
        }
        
        # 统计节点数
        for label, key in [("Character", "characters"), ("Chapter", "chapters"), ("Event", "events")]:
            result = self.execute(f"MATCH (n:{label}) RETURN count(*) AS cnt")
            if result and len(result) > 0:
                stats[key] = result[0].get("cnt", 0)
        
        # 统计关系数
        result = self.execute("MATCH ()-[r:RELATES_TO]->() RETURN count(*) AS cnt")
        if result and len(result) > 0:
            stats["relations"] = result[0].get("cnt", 0)
        
        result = self.execute("MATCH ()-[r:PARTICIPATES]->() RETURN count(*) AS cnt")
        if result and len(result) > 0:
            stats["participates"] = result[0].get("cnt", 0)
        
        return stats
