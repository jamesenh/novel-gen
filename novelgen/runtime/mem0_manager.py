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
更新: 2025-11-28 - 添加 Mem0 内部警告抑制功能，避免 UPDATE 事件的警告输出干扰日志
更新: 2025-11-30 - 添加 close() 方法和退出调试日志，帮助定位程序卡顿问题
"""
import logging
import uuid
import re
import time
import sys
import io
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED, wait, FIRST_COMPLETED
from contextlib import contextmanager
from typing import List, Dict, Optional, Any, TYPE_CHECKING, TypeVar, Callable, Generator, Tuple
from datetime import datetime

from novelgen.models import Mem0Config, UserPreference, EntityStateSnapshot, StoryMemoryChunk

if TYPE_CHECKING:
    from novelgen.config import EmbeddingConfig
else:
    EmbeddingConfig = Any

logger = logging.getLogger(__name__)

# 抑制 Mem0 内部的非致命错误日志（如 JSON 解析失败等）
# 这些错误不影响主流程，但会干扰用户日志
# 可通过环境变量 MEM0_LOG_LEVEL 控制（默认 WARNING）
import os as _os
_mem0_log_level = _os.getenv("MEM0_LOG_LEVEL", "WARNING").upper()
logging.getLogger("mem0").setLevel(getattr(logging, _mem0_log_level, logging.WARNING))

# 类型变量，用于泛型函数返回值
T = TypeVar('T')

# ==================== 全局停止事件（用于响应 Ctrl+C） ====================
# 更新: 2025-11-29 - 添加优雅停止支持，允许中断并行任务

_shutdown_event = threading.Event()


def request_shutdown():
    """请求停止所有并行任务
    
    在收到 Ctrl+C 信号时调用，通知所有工作线程停止。
    """
    _shutdown_event.set()
    logger.info("⚠️ 收到停止请求，正在通知工作线程...")


def reset_shutdown():
    """重置停止标志
    
    在每次工作流运行开始时调用，确保上次的停止状态不会影响新的运行。
    """
    _shutdown_event.clear()


def is_shutdown_requested() -> bool:
    """检查是否请求停止
    
    工作线程应定期调用此函数检查是否需要提前退出。
    
    Returns:
        bool: 如果请求停止返回 True
    """
    return _shutdown_event.is_set()


def _filter_none_values(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """过滤掉 metadata 中的 None 值
    
    ChromaDB 不接受 None 值作为 metadata，会导致保存失败。
    此函数移除所有值为 None 的键值对。
    
    Args:
        metadata: 原始 metadata 字典
        
    Returns:
        过滤后的 metadata 字典（不包含 None 值）
    """
    return {k: v for k, v in metadata.items() if v is not None}


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


@contextmanager
def _suppress_mem0_internal_warnings() -> Generator[io.StringIO, None, None]:
    """抑制 Mem0 内部的警告输出
    
    Mem0 库在处理记忆更新（UPDATE 事件）时会通过 print() 输出警告信息，
    如 "Error processing memory action: {...}, Error: '37'"。
    这些警告是 Mem0 内部的非致命性问题，不影响主流程。
    
    此上下文管理器临时捕获这些输出，避免干扰用户日志。
    
    Yields:
        StringIO: 捕获的输出内容（可用于调试）
    
    Example:
        with _suppress_mem0_internal_warnings() as captured:
            mem0_client.add(...)
        # 如需调试，可检查 captured.getvalue()
    """
    captured_output = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    # 创建一个过滤器，只抑制 Mem0 内部警告
    class Mem0WarningFilter:
        """过滤 Mem0 内部警告，其他输出正常显示"""
        
        def __init__(self, original_stream: Any, capture_buffer: io.StringIO):
            self.original = original_stream
            self.capture = capture_buffer
        
        def write(self, message: str) -> int:
            # 检查是否为 Mem0 内部警告
            if "Error processing memory action" in message:
                # 捕获但不显示，记录到 debug 日志
                self.capture.write(message)
                logger.debug(f"[Mem0 内部警告已抑制] {message.strip()}")
                return len(message)
            # 其他输出正常显示
            return self.original.write(message)
        
        def flush(self) -> None:
            self.original.flush()
        
        def __getattr__(self, name: str) -> Any:
            return getattr(self.original, name)
    
    try:
        sys.stdout = Mem0WarningFilter(old_stdout, captured_output)  # type: ignore
        sys.stderr = Mem0WarningFilter(old_stderr, captured_output)  # type: ignore
        yield captured_output
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


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
        
        # 并行处理配置
        self.parallel_workers = config.parallel_workers
        
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
            # 中文事实提取提示词，确保 Mem0 的 LLM 输出中文
            chinese_fact_extraction_prompt = """
请从以下内容中提取关键事实，必须使用中文输出。
提取规则：
1. 保留角色名称、性格特点、背景信息
2. 保留状态变化和关键事件
3. 输出格式为 JSON: {"facts": ["事实1", "事实2", ...]}

输入示例：
Input: [character] 艾瑞克·索恩 (章节 1): 意识开始稀释，左眼半透明并流动星轨光流
Output: {"facts": ["艾瑞克·索恩意识开始稀释", "左眼半透明并流动星轨光流"]}

Input: Hi, how are you?
Output: {"facts": []}

请用中文提取以下内容的事实：
"""
            
            mem0_config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": self.config.collection_name,
                        "path": self.config.chroma_path,
                    }
                },
                "embedder": embedder_config,
                "custom_fact_extraction_prompt": chinese_fact_extraction_prompt,
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

        # 定义添加操作（用于重试机制，使用警告抑制器避免 Mem0 内部 UPDATE 警告）
        def add_preference_to_mem0() -> bool:
            with _suppress_mem0_internal_warnings():
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
        story_timeline: Optional[str] = None,
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
            story_timeline: 故事时间线（可选，如 "T+0 天"、"T+7 天"）

        Returns:
            bool: 是否成功添加（如果重试全部失败返回 False）
        """
        self._ensure_initialized()

        agent_id = f"{self.project_id}_{entity_id}"

        # 构造记忆文本（包含故事时间线）
        location_info = ""
        if chapter_index is not None:
            location_info = f" (章节 {chapter_index}"
            if scene_index is not None:
                location_info += f", 场景 {scene_index}"
            if story_timeline:
                location_info += f", 时间线: {story_timeline}"
            location_info += ")"

        memory_text = f"[{entity_type}] {entity_id}{location_info}: {state_description}"

        # 添加元数据（过滤 None 值，避免 ChromaDB 保存失败）
        metadata = _filter_none_values({
            "entity_id": entity_id,
            "entity_type": entity_type,
            "project_id": self.project_id,
            "chapter_index": chapter_index,
            "scene_index": scene_index,
            "story_timeline": story_timeline,
            "timestamp": datetime.now().isoformat(),
        })

        # 定义添加操作（用于重试机制，使用警告抑制器避免 Mem0 内部 UPDATE 警告）
        def add_state_to_mem0() -> bool:
            with _suppress_mem0_internal_warnings():
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
    
    def _add_single_chunk(
        self,
        chunk_index: int,
        chunk_text: str,
        total_chunks: int,
        chapter_index: int,
        scene_index: int,
        content_type: str,
        print_lock: threading.Lock
    ) -> Tuple[int, Optional[StoryMemoryChunk]]:
        """并行处理单个文本块的保存
        
        Args:
            chunk_index: 块索引（从 0 开始）
            chunk_text: 块文本内容
            total_chunks: 总块数
            chapter_index: 章节索引
            scene_index: 场景索引
            content_type: 内容类型
            print_lock: 线程锁，用于同步输出
            
        Returns:
            (chunk_index, StoryMemoryChunk 或 None)
        
        更新: 2025-11-29 - 添加停止检查，支持 Ctrl+C 中断
        """
        # 检查是否请求停止（响应 Ctrl+C）
        if is_shutdown_requested():
            with print_lock:
                print(f"      ⏹️ 块 {chunk_index + 1}/{total_chunks} 跳过（收到停止信号）")
            return (chunk_index, None)
        
        chunk_id = str(uuid.uuid4())
        
        # 开始日志
        with print_lock:
            print(f"      📦 块 {chunk_index + 1}/{total_chunks} 开始保存...")
        
        start_time = time.time()
        
        # 构造记忆文本
        memory_text = f"[{content_type}] 章节{chapter_index}-场景{scene_index} (块{chunk_index + 1}): {chunk_text}"
        
        # 添加元数据
        metadata = {
            "chunk_id": chunk_id,
            "project_id": self.project_id,
            "chapter_index": chapter_index,
            "scene_index": scene_index,
            "content_type": content_type,
            "chunk_index": chunk_index,
            "timestamp": datetime.now().isoformat(),
        }
        
        # 使用 agent_id 作为场景记忆的标识
        scene_agent_id = f"{self.project_id}_scene_content"
        
        # 定义添加操作
        def add_chunk_to_mem0() -> bool:
            with _suppress_mem0_internal_warnings():
                self.client.add(
                    messages=[{"role": "assistant", "content": memory_text}],
                    agent_id=scene_agent_id,
                    metadata=metadata,
                )
            return True
        
        # 使用重试机制执行添加操作
        operation_name = f"add_scene_chunk_{chapter_index}_{scene_index}_{chunk_index}"
        result = self._execute_with_retry(
            operation=add_chunk_to_mem0,
            operation_name=operation_name,
            graceful_degradation=True
        )
        
        elapsed = time.time() - start_time
        
        if result is None:
            # 失败日志
            with print_lock:
                print(f"      ❌ 块 {chunk_index + 1}/{total_chunks} 保存失败 ({elapsed:.1f}s)")
            return (chunk_index, None)
        
        # 成功日志
        with print_lock:
            print(f"      ✅ 块 {chunk_index + 1}/{total_chunks} 保存完成 ({elapsed:.1f}s)")
        
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
        
        return (chunk_index, chunk)
    
    def add_scene_content(
        self,
        content: str,
        chapter_index: int,
        scene_index: int,
        content_type: str = "scene"
    ) -> List[StoryMemoryChunk]:
        """添加场景内容到 Mem0（并行处理）

        会自动分块并使用多线程并行存储到 Mem0 向量库中。
        如果遇到超时错误，会自动重试（使用指数退避策略）。
        启用优雅降级：即使保存失败，也不会中断场景生成流程。
        
        支持 Ctrl+C 中断：收到停止信号后会取消未完成的任务并尽快退出。

        Args:
            content: 场景文本内容
            chapter_index: 章节索引
            scene_index: 场景索引
            content_type: 内容类型（scene, dialogue, description）

        Returns:
            创建的记忆块列表（如果保存失败或被中断则返回空列表或部分列表）
        
        更新: 2025-11-29 - 添加 Ctrl+C 中断支持
        """
        self._ensure_initialized()

        # 分块
        text_chunks = self._chunk_text(content)
        
        if not text_chunks:
            return []
        
        # 检查是否已请求停止
        if is_shutdown_requested():
            print(f"      ⏹️ 跳过场景保存（收到停止信号）")
            return []
        
        print(f"      🚀 开始并行保存 {len(text_chunks)} 个块 (并行度: {self.parallel_workers})...")
        
        # 用于同步输出的线程锁
        print_lock = threading.Lock()
        results: List[Tuple[int, Optional[StoryMemoryChunk]]] = []
        interrupted = False
        
        # 使用线程池并行处理
        try:
            with ThreadPoolExecutor(max_workers=self.parallel_workers) as executor:
                futures = {
                    executor.submit(
                        self._add_single_chunk,
                        i, chunk_text, len(text_chunks),
                        chapter_index, scene_index, content_type, print_lock
                    ): i for i, chunk_text in enumerate(text_chunks)
                }
                
                pending = set(futures.keys())
                
                # 使用超时轮询，允许检查中断信号
                while pending:
                    # 检查是否请求停止
                    if is_shutdown_requested():
                        print(f"      ⏹️ 收到停止信号，取消剩余 {len(pending)} 个任务...")
                        interrupted = True
                        # 取消所有未完成的 futures
                        for f in pending:
                            f.cancel()
                        break
                    
                    # 等待任务完成，设置超时以便定期检查中断信号
                    done, pending = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
                    
                    for future in done:
                        try:
                            result = future.result()
                            results.append(result)
                        except Exception as e:
                            chunk_idx = futures[future]
                            logger.error(f"块 {chunk_idx + 1} 处理异常: {e}")
                            results.append((chunk_idx, None))
                            
        except KeyboardInterrupt:
            # 捕获 KeyboardInterrupt，设置停止标志
            request_shutdown()
            interrupted = True
            print(f"      ⏹️ 收到中断信号，正在停止...")
        
        # 统计结果
        memory_chunks = [r[1] for r in results if r[1] is not None]
        failed_chunks = len(text_chunks) - len(memory_chunks)
        
        # 按 chunk_index 排序
        memory_chunks.sort(key=lambda x: x.chapter_index * 1000 + (x.scene_index or 0))

        # 记录最终结果
        if interrupted:
            logger.warning(
                f"⏹️ 场景内容存储被中断: 章节{chapter_index}-场景{scene_index}, "
                f"已完成 {len(memory_chunks)}/{len(text_chunks)} 个块"
            )
        elif failed_chunks > 0:
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
        scene_index: Optional[int] = None,
        limit: int = 10
    ) -> List[StoryMemoryChunk]:
        """搜索场景内容

        Args:
            query: 查询关键词
            chapter_index: 可选的章节索引过滤
            scene_index: 可选的场景索引过滤
            limit: 返回结果数量上限

        Returns:
            相关记忆块列表

        Note:
            场景内容使用 run_id 存储（格式：{project_id}_scene_{chapter}_{scene}）
            搜索时需要使用对应的 run_id，或者不指定 id 进行全局搜索
        """
        self._ensure_initialized()

        try:
            # 场景内容使用统一的 agent_id 存储（{project_id}_scene_content）
            # 搜索时使用相同的 agent_id，通过 metadata 进行章节/场景过滤
            scene_agent_id = f"{self.project_id}_scene_content"
            response = self.client.search(
                query=query,
                agent_id=scene_agent_id,
                limit=limit * 3,  # 获取更多结果用于 metadata 过滤
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
                
                # 场景过滤
                if scene_index is not None and metadata.get("scene_index") != scene_index:
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
    
    def delete_chapter_memory(self, chapter_index: int) -> int:
        """删除指定章节的所有记忆
        
        Args:
            chapter_index: 章节索引
        
        Returns:
            删除的记忆数量
        """
        return self.delete_memories_by_filter(chapter_index_gte=chapter_index, chapter_index_lte=chapter_index)
    
    def get_all_memories(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """获取所有场景记忆（用于过滤删除）
        
        Args:
            limit: 返回结果数量上限
            
        Returns:
            所有场景记忆列表
        """
        self._ensure_initialized()
        
        try:
            scene_agent_id = f"{self.project_id}_scene_content"
            response = self.client.get_all(agent_id=scene_agent_id, limit=limit)
            
            # Mem0 v1.0.0 返回格式为 {"results": [...]}
            if isinstance(response, dict):
                results = response.get("results", [])
            elif isinstance(response, list):
                results = response
            else:
                logger.warning(f"⚠️ 意外的返回类型: {type(response)}")
                results = []
            
            logger.info(f"✅ 获取到 {len(results)} 条场景记忆")
            return results
            
        except Exception as e:
            logger.error(f"❌ 获取所有记忆失败: {e}")
            raise
    
    def delete_memories_by_filter(
        self,
        chapter_index_gte: Optional[int] = None,
        chapter_index_lte: Optional[int] = None,
        scene_index_gte: Optional[int] = None,
        target_chapter_for_scene: Optional[int] = None,
    ) -> int:
        """根据过滤条件删除记忆
        
        Args:
            chapter_index_gte: 章节号 >= 此值（删除此章节及之后的记忆）
            chapter_index_lte: 章节号 <= 此值（配合 gte 使用可限定范围）
            scene_index_gte: 场景号 >= 此值（需配合 target_chapter_for_scene 使用）
            target_chapter_for_scene: 场景过滤针对的章节号
        
        Returns:
            删除的记忆数量
        
        实现逻辑：
        1. 使用 get_all 获取所有场景记忆
        2. 遍历 results，按 metadata 中的 chapter_index/scene_index 过滤
        3. 对匹配的记忆调用 client.delete(memory_id) 逐个删除
        """
        self._ensure_initialized()
        
        deleted_count = 0
        
        try:
            # 获取所有场景记忆
            all_memories = self.get_all_memories(limit=5000)
            
            memories_to_delete = []
            
            for memory in all_memories:
                if not isinstance(memory, dict):
                    continue
                
                metadata = memory.get("metadata", {})
                memory_id = memory.get("id")
                
                if not memory_id:
                    continue
                
                mem_chapter = metadata.get("chapter_index")
                mem_scene = metadata.get("scene_index")
                
                # 章节过滤
                should_delete = False
                
                if chapter_index_gte is not None:
                    if mem_chapter is not None and mem_chapter >= chapter_index_gte:
                        # 检查是否有上限
                        if chapter_index_lte is not None:
                            if mem_chapter <= chapter_index_lte:
                                should_delete = True
                        else:
                            should_delete = True
                        
                        # 如果指定了场景过滤，检查是否需要更精细的过滤
                        if scene_index_gte is not None and target_chapter_for_scene is not None:
                            if mem_chapter == target_chapter_for_scene:
                                # 在目标章节中，只删除 >= scene_index_gte 的场景
                                if mem_scene is not None and mem_scene < scene_index_gte:
                                    should_delete = False
                
                if should_delete:
                    memories_to_delete.append(memory_id)
            
            # 批量删除
            logger.info(f"🗑️ 准备删除 {len(memories_to_delete)} 条场景记忆...")
            
            for memory_id in memories_to_delete:
                try:
                    self.client.delete(memory_id)
                    deleted_count += 1
                except Exception as del_err:
                    logger.warning(f"⚠️ 删除记忆 {memory_id} 失败: {del_err}")
            
            logger.info(f"✅ 已删除 {deleted_count} 条场景记忆")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ 批量删除记忆失败: {e}")
            raise
    
    def delete_entity_states_after_chapter(self, chapter_index: int, character_names: Optional[List[str]] = None) -> int:
        """删除指定章节之后的所有实体状态
        
        Args:
            chapter_index: 章节索引（删除 >= 此值的实体状态）
            character_names: 角色名称列表（可选，如果不提供则尝试删除所有已知角色的状态）
        
        Returns:
            删除的状态数量
        """
        self._ensure_initialized()
        
        deleted_count = 0
        
        try:
            # 如果没有提供角色名称，尝试从项目中获取
            if character_names is None:
                # 这里我们尝试获取一些常见的实体类型
                # 实际实现中可能需要从配置或文件中读取
                logger.warning("未提供角色名称列表，将尝试清理场景内容记忆")
                return self.delete_memories_by_filter(chapter_index_gte=chapter_index)
            
            for name in character_names:
                try:
                    agent_id = f"{self.project_id}_{name}"
                    response = self.client.get_all(agent_id=agent_id, limit=1000)
                    
                    # 提取结果
                    if isinstance(response, dict):
                        results = response.get("results", [])
                    elif isinstance(response, list):
                        results = response
                    else:
                        results = []
                    
                    # 过滤并删除
                    for memory in results:
                        if not isinstance(memory, dict):
                            continue
                        
                        metadata = memory.get("metadata", {})
                        memory_id = memory.get("id")
                        mem_chapter = metadata.get("chapter_index")
                        
                        if memory_id and mem_chapter is not None and mem_chapter >= chapter_index:
                            try:
                                self.client.delete(memory_id)
                                deleted_count += 1
                            except Exception as del_err:
                                logger.warning(f"⚠️ 删除实体状态 {memory_id} 失败: {del_err}")
                                
                except Exception as entity_err:
                    logger.warning(f"⚠️ 处理角色 {name} 的状态失败: {entity_err}")
            
            logger.info(f"✅ 已删除 {deleted_count} 条实体状态")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ 删除实体状态失败: {e}")
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

    def close(self, timeout: float = 5.0):
        """关闭 Mem0 客户端，释放资源
        
        在程序退出前调用，确保：
        1. ChromaDB 数据持久化
        2. ChromaDB 客户端正确关闭
        3. 后台线程终止
        4. HTTP 连接池关闭
        
        如果清理超时，强制退出以避免程序卡顿。
        
        Args:
            timeout: 超时时间（秒），默认 5 秒
        
        开发者: jamesenh, 开发时间: 2025-11-30
        更新: 2025-11-30 - 添加超时保护机制，防止程序卡顿
        """
        import signal
        
        # 调试模式
        debug_exit = _os.getenv("NOVELGEN_DEBUG", "0") == "1"
        
        def _debug(msg: str):
            if debug_exit:
                import time as _time
                timestamp = _time.strftime("%H:%M:%S")
                print(f"[{timestamp}] 🔍 [mem0_manager] {msg}")
        
        _debug(f"close() 开始 (timeout={timeout}s)")
        
        if not self._initialized or self.client is None:
            _debug("客户端未初始化，无需关闭")
            return
        
        # 超时处理器
        cleanup_timed_out = False
        
        def timeout_handler(signum, frame):
            nonlocal cleanup_timed_out
            cleanup_timed_out = True
            _debug(f"⚠️ 清理超时 ({timeout}s)，强制退出")
            print(f"⚠️ Mem0 清理超时 ({timeout}s)，强制退出")
            # 强制退出进程
            _os._exit(0)
        
        # 设置超时（仅在 Unix 系统上有效）
        old_handler = None
        try:
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout))
            _debug(f"已设置 {timeout}s 超时保护")
        except (AttributeError, ValueError):
            # Windows 不支持 SIGALRM
            _debug("当前系统不支持 SIGALRM，跳过超时保护")
        
        try:
            # 尝试关闭 Mem0 客户端内部的 ChromaDB
            _debug("尝试关闭 ChromaDB 客户端...")
            
            # Mem0 的 Memory 对象可能有 vector_store 属性
            if hasattr(self.client, 'vector_store'):
                vs = self.client.vector_store
                _debug(f"找到 vector_store: {type(vs)}")
                
                # 尝试持久化数据
                if hasattr(vs, 'persist'):
                    _debug("调用 vector_store.persist()...")
                    try:
                        vs.persist()
                        _debug("vector_store.persist() 完成")
                    except Exception as pe:
                        _debug(f"persist() 失败: {pe}")
                
                # ChromaDB 客户端可能有 _client 属性
                if hasattr(vs, '_client'):
                    chroma_client = vs._client
                    _debug(f"找到 ChromaDB 客户端: {type(chroma_client)}")
                    
                    # 尝试调用 close 或 reset
                    if hasattr(chroma_client, 'close'):
                        _debug("调用 chroma_client.close()...")
                        try:
                            chroma_client.close()
                            _debug("ChromaDB 客户端已关闭")
                        except Exception as ce:
                            _debug(f"close() 失败: {ce}")
                    elif hasattr(chroma_client, '_identifier_to_system'):
                        # PersistentClient 可能需要清理
                        _debug("尝试清理 PersistentClient...")
                        # 不主动 reset，只是确保不阻塞
            
            # 清理 Mem0 客户端引用
            self.client = None
            self._initialized = False
            _debug("Mem0 客户端引用已清理")
            
        except Exception as e:
            _debug(f"关闭 Mem0 客户端时出错: {e}")
            logger.warning(f"关闭 Mem0 客户端时出错: {e}")
        finally:
            # 取消超时
            try:
                if old_handler is not None:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                    _debug("超时保护已取消")
            except (AttributeError, ValueError):
                pass
        
        _debug("close() 完成")
