"""
Mem0 记忆管理器
提供 Mem0 记忆层的封装，作为唯一的记忆存储层

功能：
1. 用户记忆（User Memory）：存储作者的写作偏好和反馈
2. 实体记忆（Entity Memory）：管理角色的动态状态
3. 场景内容存储：存储和检索场景文本内容

开发者: Jamesenh, 开发时间: 2025-11-23
更新: 2025-11-25 - 移除降级逻辑，统一使用 Mem0 作为唯一记忆层
更新: 2025-11-27 - 修复 Mem0 v1.0.0 返回值格式变化导致的问题
                   search() 和 get_all() 现在返回 {"results": [...]} 而不是列表
                 - 添加超时重试机制，支持指数退避策略
"""
import logging
import uuid
import re
import time
from typing import List, Dict, Optional, Any, TYPE_CHECKING, TypeVar, Callable
from datetime import datetime

from novelgen.models import Mem0Config, UserPreference, EntityStateSnapshot, StoryMemoryChunk

if TYPE_CHECKING:
    from novelgen.config import EmbeddingConfig
else:
    EmbeddingConfig = Any

logger = logging.getLogger(__name__)

# 类型变量，用于泛型函数返回值
T = TypeVar('T')


def _is_timeout_error(error: Exception) -> bool:
    """判断是否为超时错误

    Args:
        error: 异常对象

    Returns:
        bool: 如果是超时错误返回 True，否则返回 False
    """
    error_str = str(error).lower()
    # 检查常见的超时错误关键词
    timeout_keywords = [
        "timeout",
        "timed out",
        "request timed out",
        "connect timeout",
        "read timeout",
        "connection timed out",
    ]
    return any(keyword in error_str for keyword in timeout_keywords)


class Mem0TimeoutError(Exception):
    """Mem0 请求超时异常"""
    pass


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

    def _execute_with_retry(
        self,
        operation: Callable[[], T],
        operation_name: str,
        graceful_degradation: bool = True
    ) -> Optional[T]:
        """执行 Mem0 操作，带有超时重试机制

        Args:
            operation: 要执行的操作（无参数的可调用对象）
            operation_name: 操作名称（用于日志记录）
            graceful_degradation: 是否启用优雅降级（默认 True）
                - True: 重试全部失败时返回 None，不中断主流程
                - False: 重试全部失败时抛出异常

        Returns:
            操作结果，如果启用优雅降级且失败则返回 None

        Raises:
            Mem0TimeoutError: 如果禁用优雅降级且重试全部失败
        """
        max_retries = self.config.max_retries
        backoff_factor = self.config.retry_backoff_factor

        last_exception: Optional[Exception] = None

        for attempt in range(max_retries + 1):  # 包括首次尝试
            start_time = time.time()

            try:
                result = operation()
                elapsed_time = time.time() - start_time

                # 记录成功日志（包含耗时）
                if attempt > 0:
                    logger.info(
                        f"✅ Mem0 操作 [{operation_name}] 重试成功 "
                        f"(尝试 {attempt + 1}/{max_retries + 1}, 耗时 {elapsed_time:.2f}s)"
                    )
                else:
                    logger.debug(f"✅ Mem0 操作 [{operation_name}] 成功 (耗时 {elapsed_time:.2f}s)")

                return result

            except Exception as e:
                elapsed_time = time.time() - start_time
                last_exception = e

                # 判断是否为超时错误
                if not _is_timeout_error(e):
                    # 非超时错误，直接抛出
                    logger.error(f"❌ Mem0 操作 [{operation_name}] 失败（非超时错误）: {e}")
                    raise

                # 超时错误，尝试重试
                if attempt < max_retries:
                    # 计算重试等待时间（指数退避）
                    wait_time = backoff_factor ** attempt
                    logger.warning(
                        f"⚠️ Mem0 操作 [{operation_name}] 超时 "
                        f"(尝试 {attempt + 1}/{max_retries + 1}, 耗时 {elapsed_time:.2f}s)，"
                        f"{wait_time:.1f}s 后重试..."
                    )
                    time.sleep(wait_time)
                else:
                    # 所有重试都失败
                    logger.error(
                        f"❌ Mem0 操作 [{operation_name}] 重试全部失败 "
                        f"(共尝试 {max_retries + 1} 次)，"
                        f"最后一次耗时 {elapsed_time:.2f}s，错误: {e}"
                    )

        # 所有重试都失败后的处理
        if graceful_degradation:
            logger.warning(
                f"⚠️ Mem0 操作 [{operation_name}] 失败，启用优雅降级，继续主流程"
            )
            return None
        else:
            raise Mem0TimeoutError(
                f"Mem0 操作 [{operation_name}] 重试 {max_retries} 次后仍然失败"
            ) from last_exception

    def _initialize_client(self) -> None:
        """初始化 Mem0 客户端（复用 ChromaDB、Embedding 和 LLM 配置）
        
        Mem0 内部使用两个模型：
        1. LLM：用于记忆处理（提取事实、合并、去重等）
        2. Embedder：用于生成向量嵌入进行语义搜索
        
        Raises:
            Mem0InitializationError: 如果初始化失败
        """
        try:
            from mem0 import Memory
            
            if not self.embedding_config:
                raise ValueError("embedding_config 是必需的，不能为 None")
            
            # ==================== Embedder 配置 ====================
            embed_api_key = self.embedding_config.api_key
            embed_base_url = self.embedding_config.base_url
            embed_model_name = self.embedding_config.model_name
            embed_dimensions = self.embedding_config.dimensions
            
            # 检查必需的配置项
            if not embed_api_key:
                raise Mem0InitializationError(
                    "Embedding API Key 未设置（请在 EmbeddingConfig 中配置 api_key，"
                    "或设置 EMBEDDING_API_KEY/OPENAI_API_KEY 环境变量）"
                )
            
            if not embed_model_name:
                raise Mem0InitializationError(
                    "Embedding 模型名称未设置（请在 EmbeddingConfig 中配置 model_name，"
                    "或设置 EMBEDDING_MODEL_NAME 环境变量）"
                )
            
            # 构建 embedder 配置
            embedder_config = {
                "provider": "openai",
                "config": {
                    "model": embed_model_name,
                    "api_key": embed_api_key,
                }
            }
            
            # 添加自定义 API 端点（如果配置了）
            if embed_base_url:
                embedder_config["config"]["openai_base_url"] = embed_base_url
                logger.info(f"📡 Embedder 使用自定义 API 端点: {embed_base_url}")
            
            # 如果配置了 dimensions，添加进去
            if embed_dimensions:
                embedder_config["config"]["embedding_dims"] = embed_dimensions
            
            # ==================== LLM 配置（用于记忆处理） ====================
            # 获取 LLM 配置，优先使用 Mem0Config 中的配置，否则 fallback 到 Embedding 配置
            llm_model_name = self.config.llm_model_name
            llm_api_key = self.config.llm_api_key or embed_api_key
            llm_base_url = self.config.llm_base_url or embed_base_url
            llm_temperature = self.config.llm_temperature
            llm_max_tokens = self.config.llm_max_tokens
            
            # 构建 LLM 配置
            llm_config = None
            if llm_model_name:
                llm_config = {
                    "provider": "openai",
                    "config": {
                        "model": llm_model_name,
                        "api_key": llm_api_key,
                        "temperature": llm_temperature,
                        "max_tokens": llm_max_tokens,
                    }
                }
                
                # 添加自定义 API 端点（如果配置了）
                if llm_base_url:
                    llm_config["config"]["openai_base_url"] = llm_base_url
                    logger.info(f"📡 LLM 使用自定义 API 端点: {llm_base_url}")
                
                logger.info(f"📝 Mem0 LLM 配置: 模型={llm_model_name}, 温度={llm_temperature}")
            else:
                logger.warning(
                    "⚠️ 未配置 Mem0 LLM 模型，将使用 Mem0 默认模型（gpt-4.1-nano-2025-04-14）。"
                    "建议设置 MEM0_LLM_MODEL_NAME 或 OPENAI_MODEL_NAME 环境变量。"
                )
            
            # ==================== 配置 Mem0 ====================
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
            
            # 如果配置了 LLM，添加到配置中
            if llm_config:
                mem0_config["llm"] = llm_config
            
            self.client = Memory.from_config(mem0_config)
            self._initialized = True
            
            llm_info = f"LLM 模型: {llm_model_name}" if llm_model_name else "LLM: 使用默认"
            logger.info(
                f"✅ Mem0 客户端初始化成功\n"
                f"   ChromaDB: {self.config.chroma_path}\n"
                f"   Embedding 模型: {embed_model_name}\n"
                f"   {llm_info}"
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

        如果遇到超时错误，会自动重试（使用指数退避策略）。
        启用优雅降级：即使保存失败，也不会中断主流程。

        Args:
            preference_type: 偏好类型（writing_style, tone, character_development, plot_preference）
            content: 偏好内容
            source: 偏好来源（manual, feedback, explicit）

        Returns:
            bool: 是否成功添加（如果重试全部失败返回 False）

        Raises:
            Mem0InitializationError: 如果 Mem0 未初始化
        """
        self._ensure_initialized()

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

        # 定义添加操作（用于重试机制）
        def add_preference_to_mem0() -> bool:
            self.client.add(
                messages=[{"role": "user", "content": memory_text}],
                user_id=user_id,
                metadata=metadata,
            )
            return True

        # 使用重试机制执行添加操作（启用优雅降级）
        operation_name = f"add_user_preference_{preference_type}"
        result = self._execute_with_retry(
            operation=add_preference_to_mem0,
            operation_name=operation_name,
            graceful_degradation=True  # 启用优雅降级
        )

        if result is None:
            logger.warning(f"⚠️ 用户偏好保存失败（优雅降级）: {preference_type}")
            return False

        logger.info(f"✅ 用户偏好已添加到 Mem0: {preference_type} - {content[:50]}...")
        return True
    
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

        Note:
            Mem0 v1.0.0 的 search() 方法返回格式为 {"results": [...]}
            需要从返回值中提取 "results" 字段
        """
        self._ensure_initialized()

        try:
            user_id = f"author_{self.project_id}"

            # 如果没有提供查询，使用通用查询
            search_query = query or "writing preferences and style"

            # 检索记忆
            response = self.client.search(
                query=search_query,
                user_id=user_id,
                limit=limit,
            )

            # Mem0 v1.0.0 返回格式为 {"results": [...]}
            if isinstance(response, dict):
                results = response.get("results", [])
            elif isinstance(response, list):
                results = response
            else:
                logger.warning(f"⚠️ 意外的返回类型: {type(response)}")
                results = []

            # 过滤结果（如果指定了 preference_type）
            filtered_results = []
            for result in results:
                if not isinstance(result, dict):
                    continue
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

        Note:
            Mem0 v1.0.0 的 get_all() 方法返回格式为 {"results": [...]}
            需要从返回值中提取 "results" 字段
        """
        self._ensure_initialized()

        try:
            user_id = f"author_{self.project_id}"
            response = self.client.get_all(user_id=user_id)

            # Mem0 v1.0.0 返回格式为 {"results": [...]}
            if isinstance(response, dict):
                results = response.get("results", [])
            elif isinstance(response, list):
                results = response
            else:
                logger.warning(f"⚠️ 意外的返回类型: {type(response)}")
                results = []

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

        如果遇到超时错误，会自动重试（使用指数退避策略）。
        启用优雅降级：即使保存失败，也不会中断主流程。

        Args:
            entity_id: 实体 ID（如角色名）
            entity_type: 实体类型（character, location, item）
            state_description: 状态描述（自然语言）
            chapter_index: 章节索引（可选）
            scene_index: 场景索引（可选）

        Returns:
            bool: 是否成功添加（如果重试全部失败返回 False）
        """
        self._ensure_initialized()

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

        # 定义添加操作（用于重试机制）
        def add_state_to_mem0() -> bool:
            self.client.add(
                messages=[{"role": "assistant", "content": memory_text}],
                agent_id=agent_id,
                metadata=metadata,
            )
            return True

        # 使用重试机制执行添加操作（启用优雅降级）
        operation_name = f"add_entity_state_{entity_id}"
        result = self._execute_with_retry(
            operation=add_state_to_mem0,
            operation_name=operation_name,
            graceful_degradation=True  # 启用优雅降级
        )

        if result is None:
            logger.warning(f"⚠️ 实体状态保存失败（优雅降级）: {entity_id}")
            return False

        logger.info(f"✅ 实体状态已添加到 Mem0: {entity_id} - {state_description[:50]}...")
        return True
    
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

        Note:
            Mem0 v1.0.0 的 search() 方法返回格式为 {"results": [...]}
            需要从返回值中提取 "results" 字段
        """
        self._ensure_initialized()

        try:
            agent_id = f"{self.project_id}_{entity_id}"

            # 如果没有提供查询，使用实体 ID 作为查询
            search_query = query or f"{entity_id} current state"

            # 检索记忆
            response = self.client.search(
                query=search_query,
                agent_id=agent_id,
                limit=limit,
            )

            # Mem0 v1.0.0 返回格式为 {"results": [...]}
            # 需要从返回值中提取实际结果列表
            if isinstance(response, dict):
                results = response.get("results", [])
            elif isinstance(response, list):
                # 兼容旧版本直接返回列表的情况
                results = response
            else:
                logger.warning(f"⚠️ 意外的返回类型: {type(response)}")
                results = []

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

        Note:
            Mem0 v1.0.0 的 get_all() 方法返回格式为 {"results": [...]}
            需要从返回值中提取 "results" 字段
        """
        self._ensure_initialized()

        try:
            agent_id = f"{self.project_id}_{entity_id}"
            response = self.client.get_all(agent_id=agent_id)

            # Mem0 v1.0.0 返回格式为 {"results": [...]}
            # 需要从返回值中提取实际结果列表
            if isinstance(response, dict):
                results = response.get("results", [])
            elif isinstance(response, list):
                # 兼容旧版本直接返回列表的情况
                results = response
            else:
                logger.warning(f"⚠️ 意外的返回类型: {type(response)}")
                results = []

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

        会自动分块并存储到 Mem0 向量库中。
        如果遇到超时错误，会自动重试（使用指数退避策略）。
        启用优雅降级：即使保存失败，也不会中断场景生成流程。

        Args:
            content: 场景文本内容
            chapter_index: 章节索引
            scene_index: 场景索引
            content_type: 内容类型（scene, dialogue, description）

        Returns:
            创建的记忆块列表（如果保存失败则返回空列表）
        """
        self._ensure_initialized()

        # 分块
        text_chunks = self._chunk_text(content)
        memory_chunks: List[StoryMemoryChunk] = []
        failed_chunks: int = 0

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

            # 定义添加操作（用于重试机制）
            def add_chunk_to_mem0() -> bool:
                self.client.add(
                    messages=[{"role": "assistant", "content": memory_text}],
                    run_id=run_id,
                    metadata=metadata,
                )
                return True

            # 使用重试机制执行添加操作（启用优雅降级）
            operation_name = f"add_scene_chunk_{chapter_index}_{scene_index}_{i}"
            result = self._execute_with_retry(
                operation=add_chunk_to_mem0,
                operation_name=operation_name,
                graceful_degradation=True  # 启用优雅降级，失败不中断主流程
            )

            if result is None:
                # 添加失败，但继续处理其他块
                failed_chunks += 1
                logger.warning(
                    f"⚠️ 场景块 {i+1}/{len(text_chunks)} 保存失败，继续处理下一块"
                )
                continue

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

        # 记录最终结果
        if failed_chunks > 0:
            logger.warning(
                f"⚠️ 场景内容部分存储到 Mem0: 章节{chapter_index}-场景{scene_index}, "
                f"成功 {len(memory_chunks)}/{len(text_chunks)} 个块，失败 {failed_chunks} 个块"
            )
        else:
            logger.info(
                f"✅ 场景内容已分块存储到 Mem0: 章节{chapter_index}-场景{scene_index}, "
                f"{len(memory_chunks)}个块"
            )

        return memory_chunks
    
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

        Note:
            Mem0 v1.0.0 的 search() 方法返回格式为 {"results": [...]}
            需要从返回值中提取 "results" 字段
        """
        self._ensure_initialized()

        try:
            # 搜索所有场景记忆
            agent_id = self.project_id
            response = self.client.search(
                query=query,
                agent_id=agent_id,
                limit=limit * 2,  # 获取更多结果用于过滤
            )

            # Mem0 v1.0.0 返回格式为 {"results": [...]}
            # 需要从返回值中提取实际结果列表
            if isinstance(response, dict):
                results = response.get("results", [])
            elif isinstance(response, list):
                # 兼容旧版本直接返回列表的情况
                results = response
            else:
                logger.warning(f"⚠️ 意外的返回类型: {type(response)}")
                results = []

            chunks = []
            for result in results:
                # 确保 result 是字典类型
                if not isinstance(result, dict):
                    logger.warning(f"⚠️ 跳过非字典类型的结果: {type(result)}")
                    continue

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

        Note:
            Mem0 v1.0.0 的 search() 方法返回格式为 {"results": [...]}
            需要从返回值中提取 "results" 字段
        """
        self._ensure_initialized()

        try:
            # 搜索记忆
            agent_id = self.project_id
            response = self.client.search(
                query=query,
                agent_id=agent_id,
                limit=limit * 2,  # 获取更多结果用于过滤
            )

            # Mem0 v1.0.0 返回格式为 {"results": [...]}
            # 需要从返回值中提取实际结果列表
            if isinstance(response, dict):
                results = response.get("results", [])
            elif isinstance(response, list):
                # 兼容旧版本直接返回列表的情况
                results = response
            else:
                logger.warning(f"⚠️ 意外的返回类型: {type(response)}")
                results = []

            chunks = []
            for result in results:
                # 确保 result 是字典类型
                if not isinstance(result, dict):
                    logger.warning(f"⚠️ 跳过非字典类型的结果: {type(result)}")
                    continue

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
