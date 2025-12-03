"""
世界观生成链
根据用户输入生成小说世界观设定

更新: 2025-12-02 - 添加多候选生成模式和 AI 扩写功能
"""
import json
import os
from datetime import datetime
from typing import Optional, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from pydantic import BaseModel, Field

from novelgen.models import WorldSetting, WorldVariant, WorldVariantsResult
from novelgen.llm import get_llm
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_world_chain(verbose: bool = False, llm_config=None, show_prompt: bool = True):
    """创建世界观生成链"""
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
    base_parser = PydanticOutputParser[WorldSetting](pydantic_object=WorldSetting)
    parser = LLMJsonRepairOutputParser[WorldSetting](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的小说世界观设计师。

你的任务：
1. 根据用户提供的简要描述，完整构建一个自洽的小说世界观
2. 给出足够支持后续链路的关键细节

输入说明：
- 用户会提供世界的基本设定（如类型、风格、关键元素等）
- 所有输入均为JSON文本，保持字段含义不变

输出格式（JSON schema）：
{format_instructions}

注意事项：
1. 世界观要自洽、有逻辑
2. 细节要丰富，但不冗余
3. 要为后续的故事发展留出空间
4. 严格按照JSON格式输出，不要使用Markdown包裹
5. 文本内容中如需强调词语，使用「」、（）或将英文双引号写成\"，禁止出现未转义的英文双引号"""),
        ("user", "{user_input}")
    ])

    chain = prompt | llm | parser

    return chain


def generate_world(user_input: str, verbose: bool = False, llm_config=None, show_prompt: bool = True) -> WorldSetting:
    """
    生成世界观

    Args:
        user_input: 用户输入的世界设定描述
        verbose: 是否输出详细日志（提示词、时间、token）
        llm_config: LLM配置
        show_prompt: verbose 模式下是否显示完整提示词

    Returns:
        WorldSetting对象
    """
    chain = create_world_chain(verbose=verbose, llm_config=llm_config, show_prompt=show_prompt)
    parser = PydanticOutputParser[WorldSetting](pydantic_object=WorldSetting)

    result = chain.invoke({
        "user_input": user_input,
        "format_instructions": parser.get_format_instructions()
    })

    return result


# ==================== 多候选生成模式 ====================


class _WorldVariantsOutput(BaseModel):
    """内部模型：用于解析 LLM 输出的多候选结果"""
    variants: List[WorldVariant] = Field(description="世界观候选列表")


def expand_world_prompt(
    brief_prompt: str,
    verbose: bool = False,
    llm_config=None,
    show_prompt: bool = True
) -> str:
    """
    将简短提示扩展为详细的世界观描述
    
    Args:
        brief_prompt: 用户的简短提示（如「修仙世界」「赛博朋克都市」）
        verbose: 是否输出详细日志
        llm_config: LLM 配置
        show_prompt: verbose 模式下是否显示完整提示词
    
    Returns:
        扩展后的详细描述（200-500字）
    """
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的小说世界观设计师。

你的任务：
将用户提供的简短世界观提示扩展为详细的世界描述（200-500字）。

扩写要求：
1. 保留用户提示中的所有特定要求和关键词
2. 补充以下维度的具体设定：
   - 时代背景和地理环境
   - 社会制度和组织结构
   - 力量体系或科技水平
   - 文化习俗和特色元素
3. 描述要具体生动，但留有创作空间
4. 使用中文，风格流畅自然

注意：直接输出扩写后的描述文本，不要包含任何解释或前缀。"""),
        ("user", "{brief_prompt}")
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    result = chain.invoke({"brief_prompt": brief_prompt})
    return result.strip()


def generate_world_variants(
    user_input: str,
    num_variants: Optional[int] = None,
    expand: bool = False,
    verbose: bool = False,
    llm_config=None,
    show_prompt: bool = True
) -> WorldVariantsResult:
    """
    根据简短提示生成多个风格各异的世界观候选
    
    Args:
        user_input: 用户输入的简短提示（如「修仙世界」）
        num_variants: 候选数量（2-5），未指定时从 ProjectConfig 读取默认值
        expand: 是否先将简短提示扩写为详细描述
        verbose: 是否输出详细日志
        llm_config: LLM 配置
        show_prompt: verbose 模式下是否显示完整提示词
    
    Returns:
        WorldVariantsResult 包含多个候选的结果
    """
    # 确定候选数量
    if num_variants is None:
        # 从环境变量读取默认值，范围限制在 2-5
        env_count = os.getenv("WORLD_VARIANTS_COUNT", "3")
        try:
            num_variants = max(2, min(5, int(env_count)))
        except ValueError:
            num_variants = 3
    else:
        # 参数指定的数量也要验证范围
        num_variants = max(2, min(5, num_variants))
    
    # 可选：扩写简短提示
    expanded_prompt = None
    generation_input = user_input
    if expand:
        expanded_prompt = expand_world_prompt(
            user_input, 
            verbose=verbose, 
            llm_config=llm_config, 
            show_prompt=show_prompt
        )
        generation_input = expanded_prompt
    
    # 创建 LLM 和解析器
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
    base_parser = PydanticOutputParser[_WorldVariantsOutput](pydantic_object=_WorldVariantsOutput)
    parser = LLMJsonRepairOutputParser[_WorldVariantsOutput](parser=base_parser, llm=llm)
    
    # 获取单个 WorldSetting 的格式说明用于嵌套
    world_parser = PydanticOutputParser[WorldSetting](pydantic_object=WorldSetting)
    world_format = world_parser.get_format_instructions()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的小说世界观设计师。

你的任务：
根据用户提供的世界观描述，生成 {num_variants} 个风格各异的世界观候选方案。

多样化要求：
各候选必须在以下维度体现明显差异：
- 时代背景（古代/现代/未来）
- 社会结构（门派/家族/国家/公司）
- 力量体系（传统/创新/混合）
- 整体风格（严肃/轻松/黑暗/热血）

输出格式（JSON）：
{{
  "variants": [
    {{
      "variant_id": "variant_1",
      "style_tag": "风格标签（如「古典仙侠」「都市修真」）",
      "brief_description": "50-100字的简要描述，概括这个世界的特色",
      "world_setting": <WorldSetting对象>
    }},
    ...
  ]
}}

WorldSetting 对象格式：
{world_format}

注意事项：
1. 每个候选的 variant_id 必须唯一（variant_1, variant_2, ...）
2. style_tag 要简洁有力，能够一眼区分不同风格
3. brief_description 要突出该候选的独特卖点
4. 严格按照 JSON 格式输出，不要使用 Markdown 包裹
5. 文本内容中如需强调词语，使用「」、（）或将英文双引号写成 \"，禁止出现未转义的英文双引号"""),
        ("user", "{user_input}")
    ])
    
    chain = prompt | llm | parser
    
    result = chain.invoke({
        "user_input": generation_input,
        "num_variants": num_variants,
        "world_format": world_format
    })
    
    # 构建返回结果
    return WorldVariantsResult(
        original_prompt=user_input,
        expanded_prompt=expanded_prompt,
        variants=result.variants,
        generated_at=datetime.now().isoformat()
    )


def select_world_variant(
    variants_result: WorldVariantsResult,
    variant_id: str,
    project_dir: Optional[str] = None
) -> WorldSetting:
    """
    从候选中选择一个世界观
    
    Args:
        variants_result: 多候选生成结果
        variant_id: 要选择的候选 ID（如 "variant_2"）
        project_dir: 项目目录，如提供则保存到 world.json
    
    Returns:
        选中的 WorldSetting 对象
    
    Raises:
        ValueError: 如果 variant_id 不存在
    """
    # 查找对应的候选
    selected = None
    for variant in variants_result.variants:
        if variant.variant_id == variant_id:
            selected = variant
            break
    
    if selected is None:
        available_ids = [v.variant_id for v in variants_result.variants]
        raise ValueError(f"候选 ID '{variant_id}' 不存在，可用的 ID: {available_ids}")
    
    # 如果提供了项目目录，保存到 world.json
    if project_dir:
        world_file = os.path.join(project_dir, "world.json")
        os.makedirs(project_dir, exist_ok=True)
        with open(world_file, 'w', encoding='utf-8') as f:
            json.dump(selected.world_setting.model_dump(), f, ensure_ascii=False, indent=2)
    
    return selected.world_setting


def save_world_variants(
    variants_result: WorldVariantsResult,
    project_dir: str
) -> str:
    """
    保存世界观候选到文件，供稍后选择
    
    Args:
        variants_result: 多候选生成结果
        project_dir: 项目目录
    
    Returns:
        保存的文件路径
    """
    variants_file = os.path.join(project_dir, "world_variants.json")
    os.makedirs(project_dir, exist_ok=True)
    
    with open(variants_file, 'w', encoding='utf-8') as f:
        json.dump(variants_result.model_dump(), f, ensure_ascii=False, indent=2)
    
    return variants_file


def load_world_variants(project_dir: str) -> Optional[WorldVariantsResult]:
    """
    从文件加载已保存的世界观候选
    
    Args:
        project_dir: 项目目录
    
    Returns:
        WorldVariantsResult 或 None（如果文件不存在）
    """
    variants_file = os.path.join(project_dir, "world_variants.json")
    
    if not os.path.exists(variants_file):
        return None
    
    with open(variants_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return WorldVariantsResult.model_validate(data)

