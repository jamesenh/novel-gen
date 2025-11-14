"""
修订工具
用于修改和优化生成的内容
"""
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from novelgen.llm import get_llm


def create_revision_chain():
    """创建修订链"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的文本编辑。

你的任务：根据用户的修改意见，优化提供的文本。

注意事项：
1. 保持原文的核心内容和风格
2. 根据意见进行针对性修改
3. 不要改变故事的基本走向
4. 保持文本的连贯性"""),
        ("user", """原文：
{original_text}

修改意见：
{revision_notes}

请输出修改后的文本。""")
    ])
    
    llm = get_llm()
    chain = prompt | llm
    
    return chain


def revise_text(original_text: str, revision_notes: str) -> str:
    """
    修订文本
    
    Args:
        original_text: 原始文本
        revision_notes: 修改意见
        
    Returns:
        修订后的文本
    """
    chain = create_revision_chain()
    result = chain.invoke({
        "original_text": original_text,
        "revision_notes": revision_notes
    })
    
    if hasattr(result, 'content'):
        return result.content
    return str(result)


def revise_scene(scene_content: str, revision_notes: str) -> str:
    """
    修订场景文本
    
    Args:
        scene_content: 场景内容
        revision_notes: 修改意见
        
    Returns:
        修订后的场景内容
    """
    return revise_text(scene_content, revision_notes)

