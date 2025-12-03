"""
配置管理
管理LLM配置、API密钥等

更新: 2025-11-25 - 简化配置，移除独立的 SQLite 和 VectorStore 相关配置
"""
import os
from typing import Optional, Dict, Literal, TYPE_CHECKING
from pydantic import BaseModel, Field
from dotenv import load_dotenv

if TYPE_CHECKING:
    from novelgen.models import Mem0Config


# 在模块导入阶段自动加载默认的 .env 文件，支持 .env.local 优先级
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _env_filename in (".env.local", ".env"):
    _env_path = os.path.join(_PROJECT_ROOT, _env_filename)
    if os.path.exists(_env_path):
        # override=False 避免覆盖已经存在的环境变量（如 shell 中显式设置）
        load_dotenv(_env_path, override=True)


class EmbeddingConfig(BaseModel):
    """Embedding模型配置"""
    model_name: Optional[str] = Field(default=None, description="Embedding模型名称")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="API基础URL")
    dimensions: Optional[int] = Field(default=None, description="向量维度（某些模型支持）")
    chunk_size: int = Field(default=500, description="文本分块大小")
    chunk_overlap: int = Field(default=50, description="文本分块重叠大小")

    def __init__(self, **data):
        super().__init__(**data)
        
        # 从环境变量读取配置（环境变量优先级高于传入参数）
        # 如果参数未提供，尝试从环境变量读取
        # 注意：OPENAI_API_BASE 已废弃，请使用 OPENAI_BASE_URL 或 EMBEDDING_BASE_URL
        if self.api_key is None:
            self.api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
        if self.base_url is None:
            self.base_url = os.getenv("EMBEDDING_BASE_URL") or os.getenv("OPENAI_BASE_URL")

        # 兼容已废弃的 OPENAI_API_BASE（显示警告）
        if self.base_url is None and os.getenv("OPENAI_API_BASE"):
            import warnings
            warnings.warn("OPENAI_API_BASE 已废弃，请使用 OPENAI_BASE_URL 或 EMBEDDING_BASE_URL")
            self.base_url = os.getenv("OPENAI_API_BASE")
        
        # model_name 特殊处理：优先使用环境变量，如果都没有则使用默认值
        env_model = os.getenv("EMBEDDING_MODEL_NAME")
        if env_model:
            self.model_name = env_model
        elif self.model_name is None:
            self.model_name = "text-embedding-3-small"
        
        # 读取可选配置
        if self.dimensions is None and os.getenv("EMBEDDING_DIMENSIONS"):
            self.dimensions = int(os.getenv("EMBEDDING_DIMENSIONS"))
        if os.getenv("EMBEDDING_CHUNK_SIZE"):
            self.chunk_size = int(os.getenv("EMBEDDING_CHUNK_SIZE"))
        if os.getenv("EMBEDDING_CHUNK_OVERLAP"):
            self.chunk_overlap = int(os.getenv("EMBEDDING_CHUNK_OVERLAP"))


class LLMConfig(BaseModel):
    """LLM配置"""
    chain_name: Optional[str] = Field(default=None, description="链名称，用于读取链特定的环境变量")
    model_name: Optional[str] = Field(default=None, description="模型名称")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, description="最大token数")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="API基础URL")
    use_structured_output: bool = Field(default=True, description="是否使用结构化输出模式（with_structured_output）")

    def __init__(self, **data):
        super().__init__(**data)

        # 从环境变量读取通用配置
        if self.api_key is None:
            self.api_key = os.getenv("OPENAI_API_KEY")
        if self.base_url is None:
            self.base_url = os.getenv("OPENAI_API_BASE")

        # 如果提供了链名称，读取链特定的环境变量
        if self.chain_name:
            # 模型名称
            chain_model_env = f"{self.chain_name.upper()}_MODEL_NAME"
            if os.getenv(chain_model_env):
                self.model_name = os.getenv(chain_model_env)

            # 最大token数
            chain_max_tokens_env = f"{self.chain_name.upper()}_MAX_TOKENS"
            if os.getenv(chain_max_tokens_env):
                self.max_tokens = int(os.getenv(chain_max_tokens_env))

            # 温度参数
            chain_temp_env = f"{self.chain_name.upper()}_TEMPERATURE"
            if os.getenv(chain_temp_env):
                self.temperature = float(os.getenv(chain_temp_env))

            # API基础URL（支持不同模型供应商）
            chain_base_url_env = f"{self.chain_name.upper()}_BASE_URL"
            if os.getenv(chain_base_url_env):
                self.base_url = os.getenv(chain_base_url_env)

            # API密钥（支持不同模型供应商）
            chain_api_key_env = f"{self.chain_name.upper()}_API_KEY"
            if os.getenv(chain_api_key_env):
                self.api_key = os.getenv(chain_api_key_env)

        # 读取通用环境变量作为 fallback
        if self.model_name is None:
            self.model_name = os.getenv("OPENAI_MODEL_NAME")
        if self.temperature is None:
            self.temperature = os.getenv("TEMPERATURE")
        if self.max_tokens is None:
            self.max_tokens = os.getenv("MAX_TOKENS")

        # 设置链特定的默认值（如果环境变量未设置）
        if self.chain_name:
            default_configs = {
                "world_chain": {"model_name": "gpt-4o-mini", "max_tokens": 1000},
                "theme_conflict_chain": {"model_name": "gpt-3.5-turbo", "max_tokens": 500},
                "characters_chain": {"model_name": "gpt-4o-mini", "max_tokens": 2000},
                "outline_chain": {"model_name": "gpt-4o-mini", "max_tokens": 3000},
                "chapters_plan_chain": {"model_name": "gpt-3.5-turbo", "max_tokens": 1000},
                "scene_text_chain": {"model_name": "gpt-4", "max_tokens": 8000},
                "chapter_memory_chain": {"model_name": "gpt-4o-mini", "max_tokens": 2000},
                "consistency_chain": {"model_name": "gpt-4o-mini", "max_tokens": 4000},
                "revision_chain": {"model_name": "gpt-4o-mini", "max_tokens": 8000},
                "memory_context_chain": {"model_name": "gpt-4o-mini", "max_tokens": 1000}
            }

            if self.chain_name in default_configs:
                config = default_configs[self.chain_name]
                self.model_name = self.model_name or config["model_name"]
                self.max_tokens = self.max_tokens or config["max_tokens"]


class ChainConfig(BaseModel):
    """链配置"""
    chain_name: Optional[str] = Field(default=None, description="链名称")
    llm_config: LLMConfig = Field(default_factory=LLMConfig, description="LLM配置")

    def __init__(self, **data):
        """
        初始化链配置

        Args:
            **data: 配置参数
        """
        chain_name = data.get("chain_name")

        # 如果提供了chain_name但没有提供llm_config，创建带chain_name的LLMConfig
        if chain_name and "llm_config" not in data:
            data["llm_config"] = LLMConfig(chain_name=chain_name)

        super().__init__(**data)


class ProjectConfig(BaseModel):
    """项目配置

    注意：
    - 使用 Mem0 作为唯一的记忆层，必须启用 Mem0（设置 MEM0_ENABLED=true）
    - Mem0 内部使用 ChromaDB 存储向量，路径由 vector_store_dir 配置
    """

    project_dir: str = Field(description="项目目录")
    author: str = Field(default="Jamesenh", description="作者名称")
    memory_context_chapters: int = Field(default=3, description="构建章节上下文时参考的最近章节数量")
    revision_policy: Literal["none", "auto_apply", "manual_confirm"] = Field(
        default="none",
        description="章节修订策略：none(不修订), auto_apply(自动应用), manual_confirm(人工确认)"
    )
    vector_store_dir: Optional[str] = Field(
        default=None,
        description="Mem0 内部 ChromaDB 存储目录，默认使用 project_dir/data/vectors。",
    )
    world_variants_count: int = Field(
        default=3,
        description="世界观候选生成数量（2-5），通过 WORLD_VARIANTS_COUNT 环境变量配置"
    )

    def __init__(self, **data):
        # 从环境变量读取 revision_policy（如果未在参数中提供）
        if "revision_policy" not in data:
            env_policy = os.getenv("NOVELGEN_REVISION_POLICY", "none")
            if env_policy in ("none", "auto_apply", "manual_confirm"):
                data["revision_policy"] = env_policy

        # 从环境变量读取向量存储目录（如果未在参数中提供）
        if "vector_store_dir" not in data:
            env_vector_dir = os.getenv("NOVELGEN_VECTOR_STORE_DIR")
            if env_vector_dir:
                data["vector_store_dir"] = env_vector_dir

        # 从环境变量读取世界观候选数量（如果未在参数中提供）
        if "world_variants_count" not in data:
            env_variants_count = os.getenv("WORLD_VARIANTS_COUNT")
            if env_variants_count:
                try:
                    count = int(env_variants_count)
                    # 限制在 2-5 范围内，超出范围使用边界值
                    data["world_variants_count"] = max(2, min(5, count))
                except ValueError:
                    pass  # 无效值，使用默认值 3

        super().__init__(**data)
        
        # 初始化 Mem0 配置（在 super().__init__ 之后，确保 get_vector_store_dir() 可用）
        if self.mem0_config is None:
            mem0_enabled = os.getenv("MEM0_ENABLED", "false").lower() in ("true", "1", "yes", "on")
            if mem0_enabled:
                from novelgen.models import Mem0Config

                # 读取重试相关的环境变量
                request_timeout = int(os.getenv("MEM0_REQUEST_TIMEOUT", "30"))
                max_retries = int(os.getenv("MEM0_MAX_RETRIES", "3"))
                retry_backoff_factor = float(os.getenv("MEM0_RETRY_BACKOFF_FACTOR", "2.0"))
                
                # 读取 LLM 相关的环境变量（温度默认 0.0 以获得更稳定的 JSON 输出）
                llm_temperature = float(os.getenv("MEM0_LLM_TEMPERATURE", "0.0"))
                llm_max_tokens = int(os.getenv("MEM0_LLM_MAX_TOKENS", "2000"))
                
                # 读取并行处理相关的环境变量
                parallel_workers = int(os.getenv("MEM0_PARALLEL_WORKERS", "5"))

                self.mem0_config = Mem0Config(
                    enabled=True,
                    chroma_path=self.get_vector_store_dir(),
                    api_key=os.getenv("MEM0_API_KEY"),
                    # Mem0 LLM 配置（用于记忆处理）
                    # 优先使用 MEM0_LLM_* 环境变量，否则使用通用配置
                    llm_model_name=os.getenv("MEM0_LLM_MODEL_NAME") or os.getenv("OPENAI_MODEL_NAME"),
                    llm_api_key=os.getenv("MEM0_LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
                    llm_base_url=os.getenv("MEM0_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE"),
                    llm_temperature=llm_temperature,
                    llm_max_tokens=llm_max_tokens,
                    # 重试配置
                    request_timeout=request_timeout,
                    max_retries=max_retries,
                    retry_backoff_factor=retry_backoff_factor,
                    # 并行处理配置
                    parallel_workers=parallel_workers,
                )

    # 各个链的配置，设置不同的chain_name
    world_chain_config: ChainConfig = Field(
        default_factory=lambda: ChainConfig(chain_name="world_chain"),
        description="世界观生成链配置"
    )
    theme_conflict_chain_config: ChainConfig = Field(
        default_factory=lambda: ChainConfig(chain_name="theme_conflict_chain"),
        description="主题冲突生成链配置"
    )
    characters_chain_config: ChainConfig = Field(
        default_factory=lambda: ChainConfig(chain_name="characters_chain"),
        description="角色生成链配置"
    )
    outline_chain_config: ChainConfig = Field(
        default_factory=lambda: ChainConfig(chain_name="outline_chain"),
        description="大纲生成链配置"
    )
    chapters_plan_chain_config: ChainConfig = Field(
        default_factory=lambda: ChainConfig(chain_name="chapters_plan_chain"),
        description="章节规划链配置"
    )
    scene_text_chain_config: ChainConfig = Field(
        default_factory=lambda: ChainConfig(chain_name="scene_text_chain"),
        description="场景文本生成链配置"
    )
    chapter_memory_chain_config: ChainConfig = Field(
        default_factory=lambda: ChainConfig(chain_name="chapter_memory_chain"),
        description="章节记忆生成链配置"
    )
    consistency_chain_config: ChainConfig = Field(
        default_factory=lambda: ChainConfig(chain_name="consistency_chain"),
        description="章节一致性检测链配置"
    )
    revision_chain_config: ChainConfig = Field(
        default_factory=lambda: ChainConfig(chain_name="revision_chain"),
        description="章节修订链配置"
    )
    memory_context_chain_config: ChainConfig = Field(
        default_factory=lambda: ChainConfig(chain_name="memory_context_chain"),
        description="记忆上下文检索链配置"
    )
    embedding_config: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="Embedding模型配置"
    )
    mem0_config: Optional["Mem0Config"] = Field(
        default=None,
        description="Mem0 配置（必需，设置 MEM0_ENABLED=true 启用）"
    )

    @property
    def world_file(self) -> str:
        return os.path.join(self.project_dir, "world.json")

    @property
    def world_variants_file(self) -> str:
        """世界观候选文件路径"""
        return os.path.join(self.project_dir, "world_variants.json")

    @property
    def theme_conflict_file(self) -> str:
        return os.path.join(self.project_dir, "theme_conflict.json")

    @property
    def theme_conflict_variants_file(self) -> str:
        """主题冲突候选文件路径"""
        return os.path.join(self.project_dir, "theme_conflict_variants.json")

    @property
    def characters_file(self) -> str:
        return os.path.join(self.project_dir, "characters.json")

    @property
    def outline_file(self) -> str:
        return os.path.join(self.project_dir, "outline.json")

    @property
    def chapters_dir(self) -> str:
        return os.path.join(self.project_dir, "chapters")

    @property
    def chapter_memory_file(self) -> str:
        return os.path.join(self.project_dir, "chapter_memory.json")

    @property
    def consistency_report_file(self) -> str:
        return os.path.join(self.project_dir, "consistency_reports.json")

    def get_vector_store_dir(self) -> str:
        """获取向量存储目录路径（用于 Mem0 内部 ChromaDB）
        
        如果未设置则返回默认路径 project_dir/data/vectors
        """
        if self.vector_store_dir:
            # 如果是绝对路径，直接返回
            if os.path.isabs(self.vector_store_dir):
                return self.vector_store_dir
            # 如果是相对路径，相对于 project_dir
            return os.path.join(self.project_dir, self.vector_store_dir)
        # 默认使用 project_dir/data/vectors
        return os.path.join(self.project_dir, "data", "vectors")


# 解决前向引用：在所有类定义完成后，导入 Mem0Config 并重建 ProjectConfig 模型
# 这样 Pydantic 就可以正确解析 mem0_config 字段的类型
try:
    from novelgen.models import Mem0Config
    ProjectConfig.model_rebuild()
except ImportError:
    # 如果 models.py 还未定义 Mem0Config（如在测试环境），忽略错误
    pass
