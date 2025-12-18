"""配置加载模块：从环境变量和 .env 文件加载配置。"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Try to load dotenv if available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass
class Config:
    """应用配置类。"""

    # Project settings
    project_name: str
    project_root: Path
    author: str = "Jamesenh"

    # Generation settings
    num_chapters: int = 1

    # Model settings
    model_provider: str = "openai"
    model_name: str = "gpt-4"
    model_base_url: Optional[str] = None
    model_api_key: Optional[str] = None

    # QA thresholds
    qa_blocker_max: int = 0  # Must be 0 to advance
    qa_major_max: int = 3
    max_revision_rounds: int = 3

    # Paths (derived from project_root)
    @property
    def chapters_dir(self) -> Path:
        return self.project_root / "chapters"

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def checkpoint_db(self) -> Path:
        return self.project_root / "workflow_checkpoints.db"

    @property
    def memory_db(self) -> Path:
        return self.data_dir / "novel.db"

    @property
    def retrieval_db(self) -> Path:
        return self.data_dir / "retrieval.db"


def load_config(project_name: Optional[str] = None) -> Config:
    """从环境变量加载配置。

    Args:
        project_name: 可选的项目名覆盖。如果未提供，则从 PROJECT_NAME 环境变量读取。

    Returns:
        填充完成的 Config 对象。

    Raises:
        ValueError: 如果未指定项目名。
    """
    name = project_name or os.getenv("PROJECT_NAME")
    if not name:
        raise ValueError(
            "Project name must be specified via --project or PROJECT_NAME env var"
        )

    # Determine project root relative to workspace
    workspace_root = Path(__file__).parent.parent
    project_root = workspace_root / "projects" / name

    return Config(
        project_name=name,
        project_root=project_root,
        author=os.getenv("AUTHOR", "Jamesenh"),
        num_chapters=int(os.getenv("NUM_CHAPTERS", "1")),
        model_provider=os.getenv("MODEL_PROVIDER", "openai"),
        model_name=os.getenv("MODEL_NAME", "gpt-4"),
        model_base_url=os.getenv("MODEL_BASE_URL"),
        model_api_key=os.getenv("MODEL_API_KEY"),
        qa_blocker_max=int(os.getenv("QA_BLOCKER_MAX", "0")),
        qa_major_max=int(os.getenv("QA_MAJOR_MAX", "3")),
        max_revision_rounds=int(os.getenv("MAX_REVISION_ROUNDS", "3")),
    )
