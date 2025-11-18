"""
配置管理
管理LLM配置、API密钥等
"""
import os
from typing import Optional, Dict, Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv


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
        if self.api_key is None:
            self.api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
        if self.base_url is None:
            self.base_url = os.getenv("EMBEDDING_BASE_URL") or os.getenv("OPENAI_API_BASE")
        
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
    - 持久化相关行为可以通过 ProjectConfig 字段或环境变量控制；
    - 默认情况下会启用数据持久化和向量存储，并将数据写入 project_dir/data 下。
    """

    project_dir: str = Field(description="项目目录")
    author: str = Field(default="Jamesenh", description="作者名称")
    memory_context_chapters: int = Field(default=3, description="构建章节上下文时参考的最近章节数量")
    revision_policy: Literal["none", "auto_apply", "manual_confirm"] = Field(
        default="none",
        description="章节修订策略：none(不修订), auto_apply(自动应用), manual_confirm(人工确认)"
    )
    persistence_enabled: bool = Field(
        default=True,
        description="是否启用数据持久化。可通过环境变量 NOVELGEN_PERSISTENCE_ENABLED 控制。",
    )
    vector_store_enabled: bool = Field(
        default=True,
        description="是否启用向量存储。可通过环境变量 NOVELGEN_VECTOR_STORE_ENABLED 控制。",
    )
    db_path: Optional[str] = Field(
        default=None,
        description="数据库文件路径，可以是绝对路径或相对于 project_dir 的相对路径；默认使用 project_dir/data/novel.db。",
    )
    vector_store_dir: Optional[str] = Field(
        default=None,
        description="向量存储持久化目录，可以是绝对路径或相对于 project_dir 的相对路径；默认使用 project_dir/data/vectors。",
    )

    def __init__(self, **data):
        # 从环境变量读取 revision_policy（如果未在参数中提供）
        if "revision_policy" not in data:
            env_policy = os.getenv("NOVELGEN_REVISION_POLICY", "none")
            if env_policy in ("none", "auto_apply", "manual_confirm"):
                data["revision_policy"] = env_policy

        # 从环境变量读取持久化开关（如果未在参数中提供）
        if "persistence_enabled" not in data:
            env_persistence = os.getenv("NOVELGEN_PERSISTENCE_ENABLED", "true")
            data["persistence_enabled"] = env_persistence.lower() in ("true", "1", "yes", "on")

        if "vector_store_enabled" not in data:
            env_vector = os.getenv("NOVELGEN_VECTOR_STORE_ENABLED", "true")
            data["vector_store_enabled"] = env_vector.lower() in ("true", "1", "yes", "on")

        # 从环境变量读取数据库路径和向量存储目录（如果未在参数中提供）
        if "db_path" not in data:
            env_db_path = os.getenv("NOVELGEN_DB_PATH")
            if env_db_path:
                data["db_path"] = env_db_path

        if "vector_store_dir" not in data:
            env_vector_dir = os.getenv("NOVELGEN_VECTOR_STORE_DIR")
            if env_vector_dir:
                data["vector_store_dir"] = env_vector_dir

        super().__init__(**data)

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

    @property
    def world_file(self) -> str:
        return os.path.join(self.project_dir, "world.json")

    @property
    def theme_conflict_file(self) -> str:
        return os.path.join(self.project_dir, "theme_conflict.json")

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

    def get_db_path(self) -> str:
        """获取数据库文件路径，如果未设置则返回默认路径"""
        if self.db_path:
            # 如果是绝对路径，直接返回
            if os.path.isabs(self.db_path):
                return self.db_path
            # 如果是相对路径，相对于 project_dir
            return os.path.join(self.project_dir, self.db_path)
        # 默认使用 project_dir/data/novel.db
        return os.path.join(self.project_dir, "data", "novel.db")

    def get_vector_store_dir(self) -> str:
        """获取向量存储目录路径，如果未设置则返回默认路径"""
        if self.vector_store_dir:
            # 如果是绝对路径，直接返回
            if os.path.isabs(self.vector_store_dir):
                return self.vector_store_dir
            # 如果是相对路径，相对于 project_dir
            return os.path.join(self.project_dir, self.vector_store_dir)
        # 默认使用 project_dir/data/vectors
        return os.path.join(self.project_dir, "data", "vectors")
