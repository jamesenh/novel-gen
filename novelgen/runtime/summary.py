"""
摘要生成器
用于生成章节摘要，供后续场景参考
"""
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from novelgen.llm import get_llm
from novelgen.models import GeneratedScene


def create_summary_chain(verbose: bool = False, show_prompt: bool = True):
    """创建摘要生成链"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的文本摘要专家。

你的任务：为提供的场景文本生成简洁的摘要。

注意事项：
1. 摘要要抓住关键信息
2. 长度控制在100-200字
3. 保留重要的情节转折点
4. 不要包含细节描写"""),
        ("user", "请为以下场景生成摘要：\n\n{scene_content}")
    ])
    
    llm = get_llm(verbose=verbose, show_prompt=show_prompt)
    chain = prompt | llm
    
    return chain


def summarize_scene(scene: GeneratedScene, verbose: bool = False, show_prompt: bool = True) -> str:
    """
    生成场景摘要
    
    Args:
        scene: 生成的场景对象
        verbose: 是否输出详细日志
        show_prompt: verbose 模式下是否显示完整提示词
        
    Returns:
        摘要文本
    """
    chain = create_summary_chain(verbose=verbose, show_prompt=show_prompt)
    result = chain.invoke({"scene_content": scene.content})
    
    if hasattr(result, 'content'):
        return result.content
    return str(result)


def summarize_scenes(scenes: List[GeneratedScene], verbose: bool = False, show_prompt: bool = True) -> str:
    """
    生成多个场景的联合摘要
    
    Args:
        scenes: 场景列表
        verbose: 是否输出详细日志
        show_prompt: verbose 模式下是否显示完整提示词
        
    Returns:
        联合摘要
    """
    summaries = []
    for scene in scenes:
        summary = summarize_scene(scene, verbose=verbose, show_prompt=show_prompt)
        summaries.append(f"场景{scene.scene_number}: {summary}")
    
    return "\n".join(summaries)

