"""
图谱更新器模块
从 characters.json 和 chapter_memory.json 更新 Kùzu 图谱

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-15
"""
import os
import json
import logging
from typing import Optional, List, Dict, Any, Set

from novelgen.graph.kuzu_store import KuzuStore
from novelgen.models import Character, CharactersConfig, ChapterMemoryEntry

logger = logging.getLogger(__name__)


class GraphUpdater:
    """图谱更新器
    
    负责从 JSON 文件（characters.json, chapter_memory.json）更新 Kùzu 图谱
    """
    
    def __init__(self, store: KuzuStore, project_dir: str):
        """初始化更新器
        
        Args:
            store: KuzuStore 实例
            project_dir: 项目目录路径
        """
        self.store = store
        self.project_dir = project_dir
        self._character_names: Set[str] = set()  # 缓存角色名列表用于事件参与者匹配
    
    @property
    def characters_file(self) -> str:
        """角色配置文件路径"""
        return os.path.join(self.project_dir, "characters.json")
    
    @property
    def chapter_memory_file(self) -> str:
        """章节记忆文件路径"""
        return os.path.join(self.project_dir, "chapter_memory.json")
    
    def rebuild_all(self) -> Dict[str, Any]:
        """从 JSON 文件全量重建图谱（幂等操作）
        
        Returns:
            重建结果统计
        """
        result = {
            "success": True,
            "characters_imported": 0,
            "relations_imported": 0,
            "chapters_imported": 0,
            "events_imported": 0,
            "errors": []
        }
        
        if not self.store.is_available:
            result["success"] = False
            result["errors"].append("Kùzu 不可用")
            return result
        
        # 连接数据库
        if not self.store.connect():
            result["success"] = False
            result["errors"].append("无法连接到数据库")
            return result
        
        try:
            # 初始化 Schema
            if not self.store.init_schema():
                result["success"] = False
                result["errors"].append("初始化 Schema 失败")
                return result
            
            # 清除现有数据
            self.store.clear_all()
            
            # 1. 导入角色和关系
            char_result = self._import_characters()
            result["characters_imported"] = char_result.get("characters", 0)
            result["relations_imported"] = char_result.get("relations", 0)
            if char_result.get("errors"):
                result["errors"].extend(char_result["errors"])
            
            # 2. 导入章节和事件
            mem_result = self._import_chapter_memories()
            result["chapters_imported"] = mem_result.get("chapters", 0)
            result["events_imported"] = mem_result.get("events", 0)
            if mem_result.get("errors"):
                result["errors"].extend(mem_result["errors"])
            
            logger.info(
                f"图谱重建完成: {result['characters_imported']} 角色, "
                f"{result['relations_imported']} 关系, "
                f"{result['chapters_imported']} 章节, "
                f"{result['events_imported']} 事件"
            )
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(f"重建过程中出错: {e}")
            logger.error(f"图谱重建失败: {e}")
        finally:
            self.store.close()
        
        return result
    
    def _import_characters(self) -> Dict[str, Any]:
        """从 characters.json 导入角色和关系
        
        Returns:
            导入结果统计
        """
        result = {
            "characters": 0,
            "relations": 0,
            "errors": []
        }
        
        if not os.path.exists(self.characters_file):
            logger.warning(f"角色文件不存在: {self.characters_file}")
            return result
        
        try:
            with open(self.characters_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            characters_config = CharactersConfig(**data)
            
            # 导入主角
            if characters_config.protagonist:
                if self._upsert_character(characters_config.protagonist):
                    result["characters"] += 1
                    self._character_names.add(characters_config.protagonist.name)
            
            # 导入反派
            if characters_config.antagonist:
                if self._upsert_character(characters_config.antagonist):
                    result["characters"] += 1
                    self._character_names.add(characters_config.antagonist.name)
            
            # 导入配角
            for char in characters_config.supporting_characters:
                if self._upsert_character(char):
                    result["characters"] += 1
                    self._character_names.add(char.name)
            
            # 导入关系
            all_chars = [characters_config.protagonist]
            if characters_config.antagonist:
                all_chars.append(characters_config.antagonist)
            all_chars.extend(characters_config.supporting_characters)
            
            for char in all_chars:
                if char and char.relationships:
                    for target_name, relation_desc in char.relationships.items():
                        # 检查目标角色是否存在于已导入的角色中
                        if target_name in self._character_names:
                            if self.store.upsert_relation(
                                from_name=char.name,
                                to_name=target_name,
                                relation_type=self._extract_relation_type(relation_desc),
                                description=relation_desc,
                                evidence_ref={"source": "characters.json"}
                            ):
                                result["relations"] += 1
            
            logger.info(f"导入角色: {result['characters']} 个, 关系: {result['relations']} 条")
            
        except Exception as e:
            error_msg = f"导入角色失败: {e}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
        
        return result
    
    def _upsert_character(self, char: Character) -> bool:
        """插入或更新单个角色"""
        return self.store.upsert_character(
            name=char.name,
            role=char.role,
            gender=char.gender,
            age=char.age,
            appearance=char.appearance,
            personality=char.personality,
            background=char.background,
            motivation=char.motivation,
            abilities=char.abilities
        )
    
    def _extract_relation_type(self, description: str) -> str:
        """从关系描述中提取关系类型
        
        简单启发式：取描述的前几个字作为类型
        """
        if not description:
            return "未知"
        
        # 常见关系类型关键词
        keywords = {
            "师徒": "师徒",
            "亦师亦友": "亦师亦友",
            "青梅竹马": "青梅竹马",
            "竞争对手": "竞争对手",
            "亦敌亦友": "亦敌亦友",
            "对立": "对立",
            "死敌": "死敌",
            "好友": "好友",
            "朋友": "朋友",
            "敌人": "敌人",
            "盟友": "盟友",
            "伙伴": "伙伴",
            "兄弟": "兄弟",
            "姐妹": "姐妹",
            "父子": "父子",
            "母女": "母女",
            "夫妻": "夫妻",
            "恋人": "恋人"
        }
        
        for keyword, relation_type in keywords.items():
            if keyword in description:
                return relation_type
        
        # 默认取前4个字
        return description[:4] if len(description) >= 4 else description
    
    def _import_chapter_memories(self) -> Dict[str, Any]:
        """从 chapter_memory.json 导入章节和事件
        
        Returns:
            导入结果统计
        """
        result = {
            "chapters": 0,
            "events": 0,
            "errors": []
        }
        
        if not os.path.exists(self.chapter_memory_file):
            logger.warning(f"章节记忆文件不存在: {self.chapter_memory_file}")
            return result
        
        try:
            with open(self.chapter_memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # chapter_memory.json 是一个列表
            if not isinstance(data, list):
                data = [data]
            
            for entry_data in data:
                entry = ChapterMemoryEntry(**entry_data)
                chapter_result = self._import_chapter_memory_entry(entry)
                result["chapters"] += chapter_result.get("chapters", 0)
                result["events"] += chapter_result.get("events", 0)
                if chapter_result.get("errors"):
                    result["errors"].extend(chapter_result["errors"])
            
            logger.info(f"导入章节: {result['chapters']} 个, 事件: {result['events']} 条")
            
        except Exception as e:
            error_msg = f"导入章节记忆失败: {e}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
        
        return result
    
    def _import_chapter_memory_entry(self, entry: ChapterMemoryEntry) -> Dict[str, Any]:
        """导入单条章节记忆
        
        Args:
            entry: 章节记忆条目
            
        Returns:
            导入结果统计
        """
        result = {
            "chapters": 0,
            "events": 0,
            "errors": []
        }
        
        # 1. 创建/更新章节节点
        if self.store.upsert_chapter(
            chapter_number=entry.chapter_number,
            chapter_title=entry.chapter_title,
            timeline_anchor=entry.timeline_anchor or "",
            location_summary=entry.location_summary or "",
            summary=entry.summary
        ):
            result["chapters"] = 1
        
        # 2. 创建事件节点（从 key_events）
        for i, event_desc in enumerate(entry.key_events):
            event_id = f"ch{entry.chapter_number}_e{i + 1}"
            
            # 构建 evidence_ref
            evidence_ref = {
                "chapter_number": entry.chapter_number,
                "source": f"chapter_memory.key_events[{i}]",
                "snippet": event_desc
            }
            
            if self.store.upsert_event(
                event_id=event_id,
                description=event_desc,
                chapter_number=entry.chapter_number,
                event_index=i + 1,
                evidence_ref=evidence_ref
            ):
                result["events"] += 1
                
                # 链接事件到章节
                self.store.link_event_to_chapter(event_id, entry.chapter_number)
                
                # 尝试匹配参与角色
                participants = self._match_participants(event_desc)
                for char_name in participants:
                    self.store.link_character_to_event(char_name, event_id)
        
        return result
    
    def _match_participants(self, event_desc: str) -> List[str]:
        """从事件描述中匹配参与角色
        
        使用简单的字符串匹配，从已知角色名列表中查找
        
        Args:
            event_desc: 事件描述文本
            
        Returns:
            匹配到的角色名列表
        """
        participants = []
        for name in self._character_names:
            if name in event_desc:
                participants.append(name)
        return participants
    
    def update_chapter(self, entry: ChapterMemoryEntry) -> Dict[str, Any]:
        """增量更新单章图谱（章节生成完成后调用）
        
        Args:
            entry: 章节记忆条目
            
        Returns:
            更新结果统计
        """
        result = {
            "success": True,
            "events_added": 0,
            "errors": []
        }
        
        if not self.store.is_available:
            result["success"] = False
            result["errors"].append("Kùzu 不可用")
            return result
        
        # 连接数据库
        if not self.store.connect():
            result["success"] = False
            result["errors"].append("无法连接到数据库")
            return result
        
        try:
            # 确保 Schema 已初始化
            self.store.init_schema()
            
            # 加载角色名列表（如果尚未加载）
            if not self._character_names:
                self._load_character_names()
            
            # 导入章节记忆
            import_result = self._import_chapter_memory_entry(entry)
            result["events_added"] = import_result.get("events", 0)
            if import_result.get("errors"):
                result["errors"].extend(import_result["errors"])
            
            logger.info(f"增量更新第 {entry.chapter_number} 章: 添加 {result['events_added']} 个事件")
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(f"增量更新失败: {e}")
            logger.error(f"增量更新章节 {entry.chapter_number} 失败: {e}")
        finally:
            self.store.close()
        
        return result
    
    def _load_character_names(self):
        """从 characters.json 加载角色名列表"""
        if not os.path.exists(self.characters_file):
            return
        
        try:
            with open(self.characters_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            characters_config = CharactersConfig(**data)
            
            if characters_config.protagonist:
                self._character_names.add(characters_config.protagonist.name)
            if characters_config.antagonist:
                self._character_names.add(characters_config.antagonist.name)
            for char in characters_config.supporting_characters:
                self._character_names.add(char.name)
            
            logger.debug(f"加载了 {len(self._character_names)} 个角色名")
            
        except Exception as e:
            logger.warning(f"加载角色名列表失败: {e}")


def create_graph_updater(project_dir: str) -> Optional[GraphUpdater]:
    """创建图谱更新器的工厂函数
    
    Args:
        project_dir: 项目目录路径
        
    Returns:
        GraphUpdater 实例，如果 Kùzu 不可用则返回 None
    """
    from novelgen.config import ProjectConfig
    
    try:
        config = ProjectConfig(project_dir=project_dir)
        
        if not config.graph_enabled:
            logger.info("图谱层已禁用")
            return None
        
        graph_dir = config.get_graph_dir()
        store = KuzuStore(graph_dir)
        
        if not store.is_available:
            logger.warning("Kùzu 不可用，图谱功能已禁用")
            return None
        
        return GraphUpdater(store, project_dir)
        
    except Exception as e:
        logger.error(f"创建图谱更新器失败: {e}")
        return None
