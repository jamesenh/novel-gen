"""
配置管理
管理LLM配置、API密钥等
"""
import os
from typing import Optional
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM配置"""
    model_name: Optional[str] = Field(default=None, description="模型名称")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, description="最大token数")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="API基础URL")
    
    def __init__(self, **data):
        super().__init__(**data)
        # 从环境变量读取API密钥
        if self.api_key is None:
            self.api_key = os.getenv("OPENAI_API_KEY")
        if self.base_url is None:
            self.base_url = os.getenv("OPENAI_API_BASE")
        if self.model_name is None:
            self.model_name = os.getenv("OPENAI_MODEL_NAME")
        if self.temperature is None:
            self.temperature = os.getenv("TEMPERATURE")
        if self.max_tokens is None:
            self.max_tokens = os.getenv("MAX_TOKENS")


class ProjectConfig(BaseModel):
    """项目配置"""
    project_dir: str = Field(description="项目目录")
    author: str = Field(default="Jamesenh", description="作者名称")
    
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

