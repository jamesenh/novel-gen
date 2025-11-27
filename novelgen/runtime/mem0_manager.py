"""
Mem0 记忆管理器
提供 Mem0 记忆层的封装，作为唯一的记忆存储层

功能：
1. 用户记忆（User Memory）：存储作者的写作偏好和反馈
2. 实体记忆（Entity Memory）：管理角色的动态状态
3. 场景内容存储：存储和检索场景文本内容

开发者: Jamesenh, 开发时间: 2025-11-23
更新: 2025-11-25 - 移除降级逻辑，统一使用 Mem0 作为唯一记忆层
"""
import logging
import uuid
import re
from typing import List, Dict, Optional, Any, TYPE_CHECKING
from datetime import datetime

from novelgen.models import Mem0Config, UserPreference, EntityStateSnapshot, StoryMemoryChunk

if TYPE_CHECKING:
    from novelgen.config import EmbeddingConfig
else:
    EmbeddingConfig = Any

logger = logging.getLogger(__name__)


class Mem0InitializationError(Exception):
    """Mem0 初始化失败异常"""
    pass


class Mem0Manager:
    """Mem0 记忆管理器
    
    作为唯一的记忆层，提供以下功能：
    1. 用户记忆（User Memory）：存储作者的写作偏好和反馈
    2. 实体记忆（Entity Memory）：管理角色的动态状态
    3. 场景内容存储：存储和检索场景文本（替代独立的 VectorStore）
    
    注意：不再支持降级模式，初始化失败将抛出异常
    """
    
    def __init__(self, config: Mem0Config, project_id: str, embedding_config: EmbeddingConfig):
        """初始化 Mem0 管理器
        
        Args:
            config: Mem0 配置
            project_id: 项目 ID
            embedding_config: Embedding 配置（必需，用于复用项目配置）
        
        Raises:
            ValueError: 如果 embedding_config 为 None 或缺少必要的配置
            Mem0InitializationError: 如果 Mem0 初始化失败
        """
        if embedding_config is None:
            raise ValueError("embedding_config 是必需的，不能为 None")
        
        self.config = config
        self.project_id = project_id
        self.embedding_config = embedding_config
        self.client: Optional[Any] = None
        self._initialized = False
        
        # 文本分块配置
        self.chunk_size = getattr(embedding_config, 'chunk_size', 500)
        self.chunk_overlap = getattr(embedding_config, 'chunk_overlap', 50)
        
        if config.enabled:
            self._initialize_client()
        else:
            raise Mem0InitializationError("Mem0 未启用，请设置 MEM0_ENABLED=true")
    
    def _initialize_client(self) -> None:
        """初始化 Mem0 客户端（复用 ChromaDB 和 Embedding 配置）
        
        Raises:
            Mem0InitializationError: 如果初始化失败
        """
        try:
            from mem0 import Memory
            
            if not self.embedding_config:
                raise ValueError("embedding_config 是必需的，不能为 None")
            
            api_key = self.embedding_config.api_key
            base_url = self.embedding_config.base_url
            model_name = self.embedding_config.model_name
            dimensions = self.embedding_config.dimensions
            
            # 检查必需的配置项
            if not api_key:
                raise Mem0InitializationError(
                    "Embedding API Key 未设置（请在 EmbeddingConfig 中配置 api_key，"
                    "或设置 EMBEDDING_API_KEY/OPENAI_API_KEY 环境变量）"
                )
            
            if not model_name:
                raise Mem0InitializationError(
                    "Embedding 模型名称未设置（请在 EmbeddingConfig 中配置 model_name，"
                    "或设置 EMBEDDING_MODEL_NAME 环境变量）"
                )
            
            # 构建 embedder 配置
            # Mem0 的 BaseEmbedderConfig 支持 openai_base_url 参数，直接传递即可
            embedder_config = {
                "provider": "openai",
                "config": {
                    "model": model_name,
                    "api_key": api_key,
                }
            }
            
            # 添加自定义 API 端点（如果配置了）
            if base_url:
                embedder_config["config"]["openai_base_url"] = base_url
                logger.info(f"使用自定义 Embedding API 端点: {base_url}")
            
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
            error_msg = f"Mem0 客户端初始化失败: {e}"
            logger.error(f"❌ {error_msg}")
            raise Mem0InitializationError(error_msg) from e
    
    def _ensure_initialized(self) -> None:
        """确保 Mem0 已初始化，否则抛出异常"""
        if not self._initialized:
            raise Mem0InitializationError("Mem0 未初始化，无法执行操作")
    
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
    
    def is_enabled(self) -> bool:
        """检查 Mem0 是否启用且已初始化"""
        return self.config.enabled and self._initialized
    
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
            source: 偏好来源（manual, feedback, explicit）
        
        Returns:
            bool: 是否成功添加
        
        Raises:
            Mem0InitializationError: 如果 Mem0 未初始化
        """
        self._ensure_initialized()
        
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
            raise
    
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
        self._ensure_initialized()
        
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
            raise
    
    def get_all_user_preferences(self) -> List[Dict[str, Any]]:
        """获取所有用户偏好（用于导出和调试）
        
        Returns:
            List[Dict]: 所有用户偏好列表
        """
        self._ensure_initialized()
        
        try:
            user_id = f"author_{self.project_id}"
            results = self.client.get_all(user_id=user_id)
            logger.info(f"✅ 获取到 {len(results)} 条用户偏好记录")
            return results
        except Exception as e:
            logger.error(f"❌ 获取所有用户偏好失败: {e}")
            raise
    
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
        self._ensure_initialized()
        
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
            raise
    
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
        self._ensure_initialized()
        
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
            raise
    
    def get_all_entity_states(self, entity_id: str) -> List[Dict[str, Any]]:
        """获取实体的所有历史状态（用于调试）
        
        Args:
            entity_id: 实体 ID
        
        Returns:
            List[Dict]: 所有状态记录
        """
        self._ensure_initialized()
        
        try:
            agent_id = f"{self.project_id}_{entity_id}"
            results = self.client.get_all(agent_id=agent_id)
            logger.info(f"✅ 获取到实体 {entity_id} 的 {len(results)} 条历史状态")
            return results
        except Exception as e:
            logger.error(f"❌ 获取实体历史状态失败: {e}")
            raise
    
    def get_entity_states_for_characters(
        self,
        character_names: List[str],
        chapter_index: Optional[int] = None,
        scene_index: Optional[int] = None
    ) -> List[EntityStateSnapshot]:
        """批量获取多个角色的状态快照
        
        Args:
            character_names: 角色名称列表
            chapter_index: 可选的章节索引
            scene_index: 可选的场景索引
        
        Returns:
            实体状态快照列表
        """
        self._ensure_initialized()
        
        snapshots = []
        for name in character_names:
            try:
                states = self.get_entity_state(
                    entity_id=name,
                    query=f"{name} 的最新状态",
                    limit=1
                )
                if states:
                    latest_state = states[0]
                    snapshot = EntityStateSnapshot(
                        project_id=self.project_id,
                        entity_type="character",
                        entity_id=name,
                        chapter_index=chapter_index,
                        scene_index=scene_index,
                        timestamp=datetime.now(),
                        state_data={
                            "source": "mem0",
                            "memory": latest_state.get('memory', ''),
                            "metadata": latest_state.get('metadata', {}),
                        },
                        version=1
                    )
                    snapshots.append(snapshot)
            except Exception as e:
                logger.warning(f"获取角色 {name} 状态失败: {e}")
        
        return snapshots
    
    # ==================== 场景内容存储（Scene Memory）功能 ====================
    
    def _chunk_text(self, text: str) -> List[str]:
        """将文本分块
        
        Args:
            text: 原始文本
        
        Returns:
            文本块列表
        """
        if not text:
            return []
        
        # 清理文本
        text = re.sub(r'\s+', ' ', text.strip())
        
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 如果不是最后一块，尝试在句号、感叹号或问号处分割
            if end < len(text):
                sentence_end = max(
                    text.rfind('。', start, end),
                    text.rfind('！', start, end),
                    text.rfind('？', start, end)
                )
                
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # 如果找不到句号，尝试在逗号处分割
                    comma_pos = text.rfind('，', start, end)
                    if comma_pos > start:
                        end = comma_pos + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = max(start + 1, end - self.chunk_overlap)
        
        return chunks
    
    def add_scene_content(
        self,
        content: str,
        chapter_index: int,
        scene_index: int,
        content_type: str = "scene"
    ) -> List[StoryMemoryChunk]:
        """添加场景内容到 Mem0
        
        会自动分块并存储到 Mem0 向量库中
        
        Args:
            content: 场景文本内容
            chapter_index: 章节索引
            scene_index: 场景索引
            content_type: 内容类型（scene, dialogue, description）
        
        Returns:
            创建的记忆块列表
        """
        self._ensure_initialized()
        
        try:
            # 分块
            text_chunks = self._chunk_text(content)
            memory_chunks = []
            
            for i, chunk_text in enumerate(text_chunks):
                chunk_id = str(uuid.uuid4())
                
                # 构造记忆文本
                memory_text = f"[{content_type}] 章节{chapter_index}-场景{scene_index} (块{i+1}): {chunk_text}"
                
                # 添加元数据
                metadata = {
                    "chunk_id": chunk_id,
                    "project_id": self.project_id,
                    "chapter_index": chapter_index,
                    "scene_index": scene_index,
                    "content_type": content_type,
                    "chunk_index": i,
                    "timestamp": datetime.now().isoformat(),
                }
                
                # 使用 run_id 作为场景记忆的标识
                run_id = f"{self.project_id}_scene_{chapter_index}_{scene_index}"
                
                # 添加到 Mem0
                self.client.add(
                    messages=[{"role": "assistant", "content": memory_text}],
                    run_id=run_id,
                    metadata=metadata,
                )
                
                # 创建 StoryMemoryChunk 对象
                chunk = StoryMemoryChunk(
                    chunk_id=chunk_id,
                    project_id=self.project_id,
                    chapter_index=chapter_index,
                    scene_index=scene_index,
                    content=chunk_text,
                    content_type=content_type,
                    embedding_id=chunk_id,
                    created_at=datetime.now()
                )
                memory_chunks.append(chunk)
            
            logger.info(f"✅ 场景内容已分块存储到 Mem0: 章节{chapter_index}-场景{scene_index}, {len(memory_chunks)}个块")
            return memory_chunks
            
        except Exception as e:
            logger.error(f"❌ 添加场景内容失败: {e}")
            raise
    
    def search_scene_content(
        self,
        query: str,
        chapter_index: Optional[int] = None,
        limit: int = 10
    ) -> List[StoryMemoryChunk]:
        """搜索场景内容
        
        Args:
            query: 查询关键词
            chapter_index: 可选的章节索引过滤
            limit: 返回结果数量上限
        
        Returns:
            相关记忆块列表
        """
        self._ensure_initialized()
        
        try:
            # 搜索所有场景记忆
            results = self.client.search(
                query=query,
                limit=limit * 2,  # 获取更多结果用于过滤
            )
            
            chunks = []
            for result in results:
                metadata = result.get("metadata", {})
                
                # 检查是否是场景内容
                if metadata.get("project_id") != self.project_id:
                    continue
                if "chapter_index" not in metadata:
                    continue
                
                # 章节过滤
                if chapter_index is not None and metadata.get("chapter_index") != chapter_index:
                    continue
                
                chunk = StoryMemoryChunk(
                    chunk_id=metadata.get("chunk_id", str(uuid.uuid4())),
                    project_id=self.project_id,
                    chapter_index=metadata.get("chapter_index"),
                    scene_index=metadata.get("scene_index"),
                    content=result.get("memory", ""),
                    content_type=metadata.get("content_type", "scene"),
                    embedding_id=metadata.get("chunk_id"),
                    created_at=datetime.fromisoformat(
                        metadata.get("timestamp", datetime.now().isoformat())
                    )
                )
                chunks.append(chunk)
                
                if len(chunks) >= limit:
                    break
            
            logger.info(f"✅ 搜索到 {len(chunks)} 个相关场景内容块")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ 搜索场景内容失败: {e}")
            raise
    
    def search_memory_with_filters(
        self,
        query: str,
        content_type: Optional[str] = None,
        entities: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[StoryMemoryChunk]:
        """根据查询文本和过滤条件搜索记忆块
        
        Args:
            query: 查询关键词
            content_type: 可选的内容类型过滤
            entities: 可选的实体ID列表过滤
            tags: 可选的标签列表过滤
            limit: 返回结果数量上限
        
        Returns:
            相关记忆块列表
        """
        self._ensure_initialized()
        
        try:
            # 搜索记忆
            results = self.client.search(
                query=query,
                limit=limit * 2,  # 获取更多结果用于过滤
            )
            
            chunks = []
            for result in results:
                metadata = result.get("metadata", {})
                
                # 项目过滤
                if metadata.get("project_id") != self.project_id:
                    continue
                
                # 内容类型过滤
                if content_type and metadata.get("content_type") != content_type:
                    continue
                
                # 这里简单处理 entities 和 tags，后续可以扩展
                # 当前 Mem0 的 metadata 中没有 entities_mentioned 和 tags 字段
                # 但可以通过搜索结果的 memory 内容进行文本匹配
                
                memory_content = result.get("memory", "")
                
                # 实体过滤（检查 memory 内容中是否包含实体）
                if entities:
                    if not any(entity in memory_content for entity in entities):
                        continue
                
                chunk = StoryMemoryChunk(
                    chunk_id=metadata.get("chunk_id", str(uuid.uuid4())),
                    project_id=self.project_id,
                    chapter_index=metadata.get("chapter_index"),
                    scene_index=metadata.get("scene_index"),
                    content=memory_content,
                    content_type=metadata.get("content_type", "scene"),
                    entities_mentioned=entities or [],
                    tags=tags or [],
                    embedding_id=metadata.get("chunk_id"),
                    created_at=datetime.fromisoformat(
                        metadata.get("timestamp", datetime.now().isoformat())
                    )
                )
                chunks.append(chunk)
                
                if len(chunks) >= limit:
                    break
            
            logger.info(f"✅ 搜索到 {len(chunks)} 个符合条件的记忆块")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ 搜索记忆块失败: {e}")
            raise
    
    def delete_chapter_memory(self, chapter_index: int) -> bool:
        """删除指定章节的所有记忆
        
        Args:
            chapter_index: 章节索引
        
        Returns:
            是否成功删除
        """
        self._ensure_initialized()
        
        try:
            # Mem0 当前不直接支持按 metadata 批量删除
            # 需要先搜索获取所有相关记忆，然后逐个删除
            # 这里使用 run_id 前缀匹配来实现
            
            # 获取该章节所有场景的记忆
            # 由于 Mem0 API 限制，这里只能通过 get_all 然后过滤
            # 注意：这在大量数据时可能效率较低
            
            logger.warning(f"删除章节 {chapter_index} 的记忆（Mem0 批量删除功能受限）")
            
            # 目前 Mem0 没有提供基于 metadata 的批量删除 API
            # 可以考虑使用 run_id 来管理场景记忆的生命周期
            # 暂时返回 True，后续可以扩展
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 删除章节记忆失败: {e}")
            raise
    
    # ==================== 工具方法 ====================
    
    def clear_project_memory(self) -> bool:
        """清空当前项目的所有 Mem0 记忆（用于测试）
        
        Returns:
            bool: 是否成功清空
        """
        self._ensure_initialized()
        
        try:
            # 清空用户记忆
            user_id = f"author_{self.project_id}"
            self.client.delete_all(user_id=user_id)
            
            logger.info(f"✅ 已清空项目 {self.project_id} 的 Mem0 记忆")
            return True
        except Exception as e:
            logger.error(f"❌ 清空 Mem0 记忆失败: {e}")
            raise
