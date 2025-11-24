"""
Mem0 客户端管理器
提供 Mem0 记忆层的封装，支持用户记忆和实体记忆管理

开发者: Jamesenh, 开发时间: 2025-11-23
"""
import logging
from typing import List, Dict, Optional, Any, TYPE_CHECKING
from datetime import datetime

from novelgen.models import Mem0Config, UserPreference, EntityStateSnapshot

if TYPE_CHECKING:
    from novelgen.config import EmbeddingConfig
else:
    EmbeddingConfig = Any

logger = logging.getLogger(__name__)


class Mem0Manager:
    """Mem0 记忆管理器
    
    提供以下功能：
    1. 用户记忆（User Memory）：存储作者的写作偏好和反馈
    2. 实体记忆（Entity Memory）：管理角色的动态状态
    """
    
    def __init__(self, config: Mem0Config, project_id: str, embedding_config: EmbeddingConfig):
        """初始化 Mem0 管理器
        
        Args:
            config: Mem0 配置
            project_id: 项目 ID
            embedding_config: Embedding 配置（必需，用于复用项目配置）
        
        Raises:
            ValueError: 如果 embedding_config 为 None 或缺少必要的配置
        """
        if embedding_config is None:
            raise ValueError("embedding_config 是必需的，不能为 None")
        
        self.config = config
        self.project_id = project_id
        self.embedding_config = embedding_config
        self.client: Optional[Any] = None
        self._initialized = False
        
        if config.enabled:
            self._initialize_client()
    
    def _initialize_client(self) -> None:
        """初始化 Mem0 客户端（复用 ChromaDB 和 Embedding 配置）"""
        try:
            from mem0 import Memory
            
            # 完全使用 embedding_config 配置，不进行降级
            if not self.embedding_config:
                raise ValueError("embedding_config 是必需的，不能为 None")
            
            api_key = self.embedding_config.api_key
            base_url = self.embedding_config.base_url
            model_name = self.embedding_config.model_name
            dimensions = self.embedding_config.dimensions
            
            # 检查必需的配置项
            if not api_key:
                raise ValueError(
                    "Embedding API Key 未设置（请在 EmbeddingConfig 中配置 api_key，"
                    "或设置 EMBEDDING_API_KEY/OPENAI_API_KEY 环境变量）"
                )
            
            if not model_name:
                raise ValueError(
                    "Embedding 模型名称未设置（请在 EmbeddingConfig 中配置 model_name，"
                    "或设置 EMBEDDING_MODEL_NAME 环境变量）"
                )
            
            # 构建 embedder 配置
            embedder_config = {
                "provider": "openai",
                "config": {
                    "model": model_name,
                    "api_key": api_key,
                }
            }
            
            # 注意：Mem0 的 BaseEmbedderConfig 不支持 base_url 参数
            # 如果需要使用自定义 API 端点，需要通过环境变量 OPENAI_BASE_URL 设置
            if base_url:
                import os
                logger.info(f"检测到自定义 base_url: {base_url}")
                logger.info("Mem0 将通过环境变量 OPENAI_BASE_URL 使用自定义端点")
                # 临时设置环境变量，让 Mem0 的 OpenAI 客户端使用自定义端点
                os.environ["OPENAI_BASE_URL"] = base_url
            
            # 如果配置了 dimensions，添加进去
            if dimensions:
                embedder_config["config"]["embedding_dims"] = dimensions
            
            # 配置 Mem0 使用本地 ChromaDB
            mem0_config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": self.config.collection_name,
                        "path": self.config.chroma_path,
                    }
                },
                "embedder": embedder_config,
            }
            
            self.client = Memory.from_config(mem0_config)
            self._initialized = True
            logger.info(
                f"✅ Mem0 客户端初始化成功（使用 ChromaDB: {self.config.chroma_path}, "
                f"Embedding 模型: {model_name}）"
            )
            
        except Exception as e:
            logger.warning(f"⚠️ Mem0 客户端初始化失败: {e}")
            logger.warning("将使用降级模式（仅 SQLite/ChromaDB）")
            self._initialized = False
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查
        
        Returns:
            Dict 包含状态信息
        """
        if not self.config.enabled:
            return {
                "enabled": False,
                "status": "disabled",
                "message": "Mem0 未启用"
            }
        
        if not self._initialized:
            return {
                "enabled": True,
                "status": "failed",
                "message": "Mem0 初始化失败"
            }
        
        try:
            # 尝试执行一个简单的查询测试连接
            user_id = f"author_{self.project_id}"
            self.client.search(query="test", user_id=user_id, limit=1)
            
            return {
                "enabled": True,
                "status": "healthy",
                "message": "Mem0 运行正常",
                "chroma_path": self.config.chroma_path,
                "collection": self.config.collection_name,
            }
        except Exception as e:
            return {
                "enabled": True,
                "status": "error",
                "message": f"Mem0 查询失败: {e}"
            }
    
    # ==================== 用户记忆（User Memory）功能 ====================
    
    def add_user_preference(
        self,
        preference_type: str,
        content: str,
        source: str = "manual"
    ) -> bool:
        """添加用户偏好到 Mem0
        
        Args:
            preference_type: 偏好类型（writing_style, tone, character_development, plot_preference）
            content: 偏好内容
            source: 偏好来源（manual, feedback, explicit）。注意：不从修订过程记录偏好
        
        Returns:
            bool: 是否成功添加
        """
        if not self._initialized:
            logger.warning("Mem0 未初始化，跳过用户偏好存储")
            return False
        
        try:
            user_id = f"author_{self.project_id}"
            
            # 构造记忆文本（Mem0 会自动去重和合并）
            memory_text = f"[{preference_type}] {content}"
            
            # 添加元数据
            metadata = {
                "preference_type": preference_type,
                "source": source,
                "project_id": self.project_id,
                "timestamp": datetime.now().isoformat(),
            }
            
            # 添加到 Mem0
            self.client.add(
                messages=[{"role": "user", "content": memory_text}],
                user_id=user_id,
                metadata=metadata,
            )
            
            logger.info(f"✅ 用户偏好已添加到 Mem0: {preference_type} - {content[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加用户偏好失败: {e}")
            return False
    
    def search_user_preferences(
        self,
        query: Optional[str] = None,
        preference_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """检索用户偏好
        
        Args:
            query: 查询关键词（可选，如果为空则返回所有）
            preference_type: 偏好类型过滤（可选）
            limit: 返回结果数量
        
        Returns:
            List[Dict]: 检索到的偏好列表
        """
        if not self._initialized:
            logger.warning("Mem0 未初始化，返回空列表")
            return []
        
        try:
            user_id = f"author_{self.project_id}"
            
            # 如果没有提供查询，使用通用查询
            search_query = query or "writing preferences and style"
            
            # 检索记忆
            results = self.client.search(
                query=search_query,
                user_id=user_id,
                limit=limit,
            )
            
            # 过滤结果（如果指定了 preference_type）
            filtered_results = []
            for result in results:
                metadata = result.get("metadata", {})
                if preference_type and metadata.get("preference_type") != preference_type:
                    continue
                filtered_results.append(result)
            
            logger.info(f"✅ 检索到 {len(filtered_results)} 条用户偏好")
            return filtered_results
            
        except Exception as e:
            logger.error(f"❌ 检索用户偏好失败: {e}")
            return []
    
    def get_all_user_preferences(self) -> List[Dict[str, Any]]:
        """获取所有用户偏好（用于导出和调试）
        
        Returns:
            List[Dict]: 所有用户偏好列表
        """
        if not self._initialized:
            return []
        
        try:
            user_id = f"author_{self.project_id}"
            results = self.client.get_all(user_id=user_id)
            logger.info(f"✅ 获取到 {len(results)} 条用户偏好记录")
            return results
        except Exception as e:
            logger.error(f"❌ 获取所有用户偏好失败: {e}")
            return []
    
    # ==================== 实体记忆（Entity Memory）功能 ====================
    
    def add_entity_state(
        self,
        entity_id: str,
        entity_type: str,
        state_description: str,
        chapter_index: Optional[int] = None,
        scene_index: Optional[int] = None,
    ) -> bool:
        """添加实体状态到 Mem0（使用 Agent Memory）
        
        Args:
            entity_id: 实体 ID（如角色名）
            entity_type: 实体类型（character, location, item）
            state_description: 状态描述（自然语言）
            chapter_index: 章节索引（可选）
            scene_index: 场景索引（可选）
        
        Returns:
            bool: 是否成功添加
        """
        if not self._initialized:
            logger.warning("Mem0 未初始化，跳过实体状态存储")
            return False
        
        try:
            agent_id = f"{self.project_id}_{entity_id}"
            
            # 构造记忆文本
            location_info = ""
            if chapter_index is not None:
                location_info = f" (章节 {chapter_index}"
                if scene_index is not None:
                    location_info += f", 场景 {scene_index}"
                location_info += ")"
            
            memory_text = f"[{entity_type}] {entity_id}{location_info}: {state_description}"
            
            # 添加元数据
            metadata = {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "project_id": self.project_id,
                "chapter_index": chapter_index,
                "scene_index": scene_index,
                "timestamp": datetime.now().isoformat(),
            }
            
            # 添加到 Mem0（使用 Agent Memory）
            self.client.add(
                messages=[{"role": "assistant", "content": memory_text}],
                agent_id=agent_id,
                metadata=metadata,
            )
            
            logger.info(f"✅ 实体状态已添加到 Mem0: {entity_id} - {state_description[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加实体状态失败: {e}")
            return False
    
    def get_entity_state(
        self,
        entity_id: str,
        query: Optional[str] = None,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """获取实体的最新状态
        
        Args:
            entity_id: 实体 ID
            query: 查询关键词（可选）
            limit: 返回结果数量
        
        Returns:
            List[Dict]: 实体状态列表（按时间倒序）
        """
        if not self._initialized:
            logger.warning("Mem0 未初始化，返回空列表")
            return []
        
        try:
            agent_id = f"{self.project_id}_{entity_id}"
            
            # 如果没有提供查询，使用实体 ID 作为查询
            search_query = query or f"{entity_id} current state"
            
            # 检索记忆
            results = self.client.search(
                query=search_query,
                agent_id=agent_id,
                limit=limit,
            )
            
            logger.info(f"✅ 检索到实体 {entity_id} 的 {len(results)} 条状态记录")
            return results
            
        except Exception as e:
            logger.error(f"❌ 检索实体状态失败: {e}")
            return []
    
    def get_all_entity_states(self, entity_id: str) -> List[Dict[str, Any]]:
        """获取实体的所有历史状态（用于调试）
        
        Args:
            entity_id: 实体 ID
        
        Returns:
            List[Dict]: 所有状态记录
        """
        if not self._initialized:
            return []
        
        try:
            agent_id = f"{self.project_id}_{entity_id}"
            results = self.client.get_all(agent_id=agent_id)
            logger.info(f"✅ 获取到实体 {entity_id} 的 {len(results)} 条历史状态")
            return results
        except Exception as e:
            logger.error(f"❌ 获取实体历史状态失败: {e}")
            return []
    
    # ==================== 工具方法 ====================
    
    def clear_project_memory(self) -> bool:
        """清空当前项目的所有 Mem0 记忆（用于测试）
        
        Returns:
            bool: 是否成功清空
        """
        if not self._initialized:
            logger.warning("Mem0 未初始化，无法清空")
            return False
        
        try:
            # 清空用户记忆
            user_id = f"author_{self.project_id}"
            self.client.delete_all(user_id=user_id)
            
            logger.info(f"✅ 已清空项目 {self.project_id} 的 Mem0 记忆")
            return True
        except Exception as e:
            logger.error(f"❌ 清空 Mem0 记忆失败: {e}")
            return False

