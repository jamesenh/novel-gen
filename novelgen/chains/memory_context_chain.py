"""
记忆上下文检索链
根据场景计划智能检索相关的历史记忆和实体状态
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from novelgen.models import (
    ScenePlan,
    CharactersConfig,
    SceneMemoryContext,
    EntityStateSnapshot,
    StoryMemoryChunk,
    MemoryRetrievalAnalysis,
)
from novelgen.config import LLMConfig
from novelgen.llm import get_llm
from novelgen.runtime.db import DatabaseManager
from novelgen.runtime.vector_store import VectorStoreManager
from novelgen.runtime.memory_tools import (
    search_story_memory_tool,
    get_entity_states_for_characters,
    get_recent_timeline_tool,
)
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


logger = logging.getLogger(__name__)


def create_memory_context_chain(
    verbose: bool = False,
    llm_config: Optional[LLMConfig] = None,
):
    """创建记忆上下文检索链

    Args:
        verbose: 是否输出详细日志
        llm_config: LLM配置，如果为None则使用默认配置

    Returns:
        可直接调用的链对象，输出为 MemoryRetrievalAnalysis Pydantic 对象
    """
    if llm_config is None:
        llm_config = LLMConfig(chain_name="memory_context_chain")

    llm = get_llm(config=llm_config, verbose=verbose)
    base_parser = PydanticOutputParser[MemoryRetrievalAnalysis](
        pydantic_object=MemoryRetrievalAnalysis
    )
    parser = LLMJsonRepairOutputParser[MemoryRetrievalAnalysis](
        parser=base_parser,
        llm=llm,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """你是一个小说记忆检索分析助手。你的任务是根据即将生成的场景计划，分析需要检索的相关记忆和角色状态。

【你的任务】
1. 理解场景的核心内容（地点、角色、动作、目的）
2. 识别需要查询状态的关键实体（主要是角色）
3. 生成2-5个搜索关键词，用于向量检索相关历史记忆

【输出格式（JSON schema）】
{format_instructions}

【注意事项】
- search_queries应该是语义化的短语，描述需要检索的情节或事件
- key_entities应该是出场的主要角色名称
- 如果场景很简单，可以只生成1-2个查询关键词
- 必须严格按JSON格式输出，不要使用Markdown包裹""",
            ),
            (
                "user",
                """请分析以下场景计划，生成记忆检索查询：

场景编号：{scene_number}
场景类型：{scene_type}
场景地点：{location}
出场角色：{characters}
场景目的：{purpose}
关键动作：{key_actions}
强度等级：{intensity}""",
            ),
        ]
    )

    chain = prompt | llm | parser
    return chain


def retrieve_scene_memory_context(
    scene_plan: ScenePlan,
    characters_config: CharactersConfig,
    project_id: str,
    chapter_index: int,
    scene_index: int,
    db_manager: DatabaseManager,
    vector_manager: VectorStoreManager,
    llm_config: Optional[LLMConfig] = None,
    output_dir: Optional[str] = None
) -> SceneMemoryContext:
    """
    检索场景的记忆上下文
    
    Args:
        scene_plan: 场景计划
        characters_config: 角色配置
        project_id: 项目ID
        chapter_index: 章节索引
        scene_index: 场景索引
        db_manager: 数据库管理器
        vector_manager: 向量存储管理器
        llm_config: LLM配置，可选
        output_dir: 输出目录，如果提供则将结果写入JSON文件
        
    Returns:
        SceneMemoryContext对象
    """
    logger.info(f"开始为场景 {chapter_index}-{scene_index} 检索记忆上下文")
    
    # 初始化结果
    entity_states = []
    relevant_memories = []
    timeline_context = None
    
    try:
        # 第一步：使用LLM分析场景需求（结构化输出）
        chain = create_memory_context_chain(verbose=False, llm_config=llm_config)
        parser = PydanticOutputParser[MemoryRetrievalAnalysis](
            pydantic_object=MemoryRetrievalAnalysis
        )

        analysis: MemoryRetrievalAnalysis = chain.invoke(
            {
                "scene_number": scene_plan.scene_number,
                "scene_type": scene_plan.scene_type,
                "location": scene_plan.location,
                "characters": ", ".join(scene_plan.characters),
                "purpose": scene_plan.purpose,
                "key_actions": "\n".join(
                    f"- {action}" for action in scene_plan.key_actions
                ),
                "intensity": scene_plan.intensity,
                "format_instructions": parser.get_format_instructions(),
            }
        )

        # 从结构化结果中提取搜索关键词和关键实体，保持与规范一致
        search_queries = analysis.search_queries or [scene_plan.purpose]
        key_entities = analysis.key_entities or scene_plan.characters
        logger.info(
            f"LLM分析结果 - 搜索关键词: {search_queries}, 关键实体: {key_entities}"
        )
        
        # 第二步：检索相关记忆
        if search_queries:
            for query in search_queries:
                chunks = search_story_memory_tool(
                    db_manager=db_manager,
                    vector_manager=vector_manager,
                    project_id=project_id,
                    query=query,
                    entities=key_entities if key_entities else None,
                    top_k=5  # 每个查询返回5个
                )
                relevant_memories.extend(chunks)
            
            # 去重（基于chunk_id）
            seen_ids = set()
            unique_memories = []
            for chunk in relevant_memories:
                if chunk.chunk_id not in seen_ids:
                    seen_ids.add(chunk.chunk_id)
                    unique_memories.append(chunk)
            relevant_memories = unique_memories[:10]  # 最多保留10个
            logger.info(f"检索到 {len(relevant_memories)} 个相关记忆块")
        
        # 第三步：获取角色状态
        if scene_plan.characters:
            entity_states = get_entity_states_for_characters(
                db_manager=db_manager,
                project_id=project_id,
                character_names=scene_plan.characters,
                chapter_index=chapter_index,
                scene_index=scene_index
            )
            logger.info(f"获取到 {len(entity_states)} 个角色状态")
        
        # 第四步：获取时间线上下文（可选）
        timeline_snapshots = get_recent_timeline_tool(
            db_manager=db_manager,
            project_id=project_id,
            chapter_index=chapter_index,
            context_window=1,
            scene_index=scene_index
        )
        if timeline_snapshots:
            # 聚合时间线信息
            timeline_context = {
                "total_snapshots": len(timeline_snapshots),
                "entities_tracked": len(set(s.entity_id for s in timeline_snapshots)),
                "chapter_range": f"{chapter_index-1} to {chapter_index+1}"
            }
            logger.info(f"获取到时间线上下文: {timeline_context}")
        
    except Exception as e:
        logger.warning(f"记忆检索过程出现错误，但将继续执行: {e}")
        # 继续执行，使用已检索到的部分结果
    
    # 创建SceneMemoryContext对象
    context = SceneMemoryContext(
        project_id=project_id,
        chapter_index=chapter_index,
        scene_index=scene_index,
        entity_states=entity_states,
        relevant_memories=relevant_memories,
        timeline_context=timeline_context,
        retrieval_timestamp=datetime.now()
    )
    
    # 如果提供了输出目录，写入JSON文件
    if output_dir:
        try:
            output_path = Path(output_dir) / f"scene_{chapter_index}_{scene_index}_memory.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(context.model_dump(mode="json"), f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"记忆上下文已写入: {output_path}")
        except Exception as e:
            logger.warning(f"写入记忆上下文JSON文件失败，但不影响主流程: {e}")
    
    logger.info(f"场景 {chapter_index}-{scene_index} 的记忆上下文检索完成")
    return context
