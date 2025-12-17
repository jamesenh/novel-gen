"""
章节修订链
基于逻辑审查报告或一致性问题生成修订后的章节内容

核心功能：
- 根据审查报告中的问题，指导 LLM 修复章节
- 保持原有叙事结构和风格
- 针对性修复高严重性问题
- 兼容旧的一致性检测触发的修订流程

作者: jamesenh, 2025-12-17
开发者: jamesenh, 开发时间: 2025-12-16
"""
import json
from typing import Optional, List

from langchain_core.prompts import ChatPromptTemplate

from novelgen.llm import get_llm
from novelgen.models import (
    GeneratedChapter, GeneratedScene,
    LogicReviewReport, LogicReviewIssue,
    ChapterPlan, WorldSetting, CharactersConfig
)


REVISION_PROMPT = """你是一位专业的小说修订编辑。你的任务是根据逻辑审查报告，修订章节内容，修复其中的问题。

## 原章节信息

**章节编号**: {chapter_number}
**章节标题**: {chapter_title}

### 原章节内容

{original_content}

## 逻辑审查报告

**整体评分**: {overall_score}/100
**审查摘要**: {review_summary}

### 发现的问题

{issues_description}

## 章节计划（参考）

{chapter_plan_info}

## 世界观与角色（参考）

{world_and_characters_info}

---

## 修订要求

请根据以上审查报告中指出的问题，修订章节内容。修订时请注意：

1. **保持叙事连贯性**：不要大幅改变故事走向，只修复具体问题
2. **保持风格一致**：修订后的文字风格应与原文一致
3. **针对性修复**：重点关注 high 严重性的问题，medium 问题适度改进
4. **保持字数**：修订后的章节字数应与原章节相近（±10%）

请输出修订后的完整章节内容（以 JSON 格式）：

```json
{{
    "chapter_number": {chapter_number},
    "chapter_title": "章节标题",
    "scenes": [
        {{
            "scene_number": 1,
            "content": "场景内容...",
            "word_count": 1000
        }}
    ],
    "total_words": 3000
}}
```

请直接输出 JSON，不要包含其他解释。
"""


def _format_issues_description(issues: List[LogicReviewIssue]) -> str:
    """格式化问题描述"""
    if not issues:
        return "无明显问题"
    
    lines = []
    for i, issue in enumerate(issues, 1):
        severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue.severity, "⚪")
        lines.append(f"{i}. {severity_icon} [{issue.severity}] {issue.issue_type}")
        lines.append(f"   描述：{issue.description}")
        if issue.evidence:
            lines.append(f"   证据：{issue.evidence[:100]}...")
        if issue.fix_instructions:
            lines.append(f"   建议：{issue.fix_instructions}")
        lines.append("")
    
    return "\n".join(lines)


def _format_chapter_plan(plan: Optional[ChapterPlan]) -> str:
    """格式化章节计划信息"""
    if plan is None:
        return "（章节计划不可用）"
    
    lines = [
        f"**章节主题**: {plan.chapter_theme}",
        f"**章节目标**: {plan.chapter_goals}",
        "",
        "**场景列表**:"
    ]
    
    for scene in plan.scenes[:3]:  # 只显示前 3 个场景概要
        lines.append(f"  - 场景 {scene.scene_number}: {scene.scene_description[:50]}...")
    
    if len(plan.scenes) > 3:
        lines.append(f"  ... 共 {len(plan.scenes)} 个场景")
    
    return "\n".join(lines)


def _format_world_and_characters(
    world: Optional[WorldSetting],
    characters: Optional[CharactersConfig]
) -> str:
    """格式化世界观和角色信息"""
    lines = []
    
    if world:
        lines.append(f"**世界**: {world.world_name}")
        lines.append(f"**时代**: {world.time_period}")
        if world.power_system:
            lines.append(f"**力量体系**: {world.power_system}")
    
    if characters and characters.main_characters:
        lines.append("")
        lines.append("**主要角色**:")
        for char in characters.main_characters[:3]:
            lines.append(f"  - {char.name}: {char.role}")
    
    return "\n".join(lines) if lines else "（世界观与角色信息不可用）"


def generate_revised_chapter(
    original_chapter: GeneratedChapter,
    review_report: Optional[LogicReviewReport],
    chapter_plan: Optional[ChapterPlan] = None,
    world_setting: Optional[WorldSetting] = None,
    characters: Optional[CharactersConfig] = None,
    verbose: bool = False,
    llm_config: Optional[dict] = None
) -> GeneratedChapter:
    """生成修订后的章节

    Args:
        original_chapter: 原始章节
        review_report: 逻辑审查报告（可选，如果没有则只做轻微润色）
        chapter_plan: 章节计划（可选，用于参考）
        world_setting: 世界观设定（可选）
        characters: 角色配置（可选）
        verbose: 是否输出详细信息
        llm_config: LLM 配置

    Returns:
        修订后的章节
    """
    # 合并原章节内容
    original_content = "\n\n---\n\n".join([
        f"【场景 {scene.scene_number}】\n{scene.content}"
        for scene in original_chapter.scenes
    ])
    
    # 准备审查报告信息
    if review_report:
        overall_score = review_report.overall_score
        review_summary = review_report.summary
        issues_description = _format_issues_description(review_report.issues)
    else:
        overall_score = 80
        review_summary = "无明显问题，轻微润色"
        issues_description = "无明显问题"
    
    # 格式化参考信息
    chapter_plan_info = _format_chapter_plan(chapter_plan)
    world_and_characters_info = _format_world_and_characters(world_setting, characters)
    
    # 构建 prompt
    prompt = ChatPromptTemplate.from_template(REVISION_PROMPT)
    
    # 获取 LLM
    llm = get_llm(llm_config)
    
    # 调用 LLM
    chain = prompt | llm
    
    result = chain.invoke({
        "chapter_number": original_chapter.chapter_number,
        "chapter_title": original_chapter.chapter_title,
        "original_content": original_content,
        "overall_score": overall_score,
        "review_summary": review_summary,
        "issues_description": issues_description,
        "chapter_plan_info": chapter_plan_info,
        "world_and_characters_info": world_and_characters_info
    })
    
    # 解析结果
    response_text = result.content if hasattr(result, 'content') else str(result)
    
    # 提取 JSON
    import re
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response_text)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # 尝试直接解析
        json_str = response_text.strip()
    
    try:
        chapter_data = json.loads(json_str)
        
        # 构建 GeneratedChapter
        scenes = []
        for scene_data in chapter_data.get("scenes", []):
            scenes.append(GeneratedScene(
                scene_number=scene_data.get("scene_number", 1),
                content=scene_data.get("content", ""),
                word_count=scene_data.get("word_count", len(scene_data.get("content", "")))
            ))
        
        revised_chapter = GeneratedChapter(
            chapter_number=chapter_data.get("chapter_number", original_chapter.chapter_number),
            chapter_title=chapter_data.get("chapter_title", original_chapter.chapter_title),
            scenes=scenes,
            total_words=chapter_data.get("total_words", sum(s.word_count for s in scenes))
        )
        
        return revised_chapter
        
    except json.JSONDecodeError as e:
        if verbose:
            print(f"⚠️ JSON 解析失败，尝试降级处理: {e}")
        
        # 降级：将整个响应作为单一场景
        revised_chapter = GeneratedChapter(
            chapter_number=original_chapter.chapter_number,
            chapter_title=original_chapter.chapter_title,
            scenes=[GeneratedScene(
                scene_number=1,
                content=response_text,
                word_count=len(response_text)
            )],
            total_words=len(response_text)
        )
        
        return revised_chapter


# ============================================================================
# 兼容旧版：基于修订说明的修订函数
# 用于一致性检测触发的修订流程
# ============================================================================

SIMPLE_REVISION_PROMPT = """你是一位专业的小说修订编辑。你的任务是根据修订说明，修订章节内容。

## 原章节信息

**章节编号**: {chapter_number}
**章节标题**: {chapter_title}

### 原章节内容

{original_content}

## 修订说明

{revision_notes}

---

## 修订要求

请根据以上修订说明，修订章节内容。修订时请注意：

1. **保持叙事连贯性**：不要大幅改变故事走向，只修复具体问题
2. **保持风格一致**：修订后的文字风格应与原文一致
3. **针对性修复**：重点关注修订说明中指出的问题
4. **保持字数**：修订后的章节字数应与原章节相近（±10%）

请输出修订后的完整章节内容（以 JSON 格式）：

```json
{{
    "chapter_number": {chapter_number},
    "chapter_title": "章节标题",
    "scenes": [
        {{
            "scene_number": 1,
            "content": "场景内容...",
            "word_count": 1000
        }}
    ],
    "total_words": 3000
}}
```

请直接输出 JSON，不要包含其他解释。
"""


def revise_chapter(
    original_chapter: GeneratedChapter,
    revision_notes: str,
    verbose: bool = False,
    show_prompt: bool = False,
    llm_config: Optional[dict] = None
) -> GeneratedChapter:
    """修订章节（兼容旧接口）
    
    基于修订说明修订章节内容，用于一致性检测触发的修订流程。

    Args:
        original_chapter: 原始章节
        revision_notes: 修订说明
        verbose: 是否输出详细信息
        show_prompt: 是否显示 prompt
        llm_config: LLM 配置

    Returns:
        修订后的章节
    """
    # 合并原章节内容
    original_content = "\n\n---\n\n".join([
        f"【场景 {scene.scene_number}】\n{scene.content}"
        for scene in original_chapter.scenes
    ])
    
    # 构建 prompt
    prompt = ChatPromptTemplate.from_template(SIMPLE_REVISION_PROMPT)
    
    # 获取 LLM
    llm = get_llm(llm_config)
    
    # 调用 LLM
    chain = prompt | llm
    
    if show_prompt:
        print(f"\n[章节修订] Prompt:\n{SIMPLE_REVISION_PROMPT[:500]}...\n")
    
    result = chain.invoke({
        "chapter_number": original_chapter.chapter_number,
        "chapter_title": original_chapter.chapter_title,
        "original_content": original_content,
        "revision_notes": revision_notes
    })
    
    # 解析结果
    response_text = result.content if hasattr(result, 'content') else str(result)
    
    # 提取 JSON
    import re
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response_text)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        json_str = response_text.strip()
    
    try:
        chapter_data = json.loads(json_str)
        
        scenes = []
        for scene_data in chapter_data.get("scenes", []):
            scenes.append(GeneratedScene(
                scene_number=scene_data.get("scene_number", 1),
                content=scene_data.get("content", ""),
                word_count=scene_data.get("word_count", len(scene_data.get("content", "")))
            ))
        
        revised_chapter = GeneratedChapter(
            chapter_number=chapter_data.get("chapter_number", original_chapter.chapter_number),
            chapter_title=chapter_data.get("chapter_title", original_chapter.chapter_title),
            scenes=scenes,
            total_words=chapter_data.get("total_words", sum(s.word_count for s in scenes))
        )
        
        return revised_chapter
        
    except json.JSONDecodeError as e:
        if verbose:
            print(f"⚠️ JSON 解析失败，尝试降级处理: {e}")
        
        revised_chapter = GeneratedChapter(
            chapter_number=original_chapter.chapter_number,
            chapter_title=original_chapter.chapter_title,
            scenes=[GeneratedScene(
                scene_number=1,
                content=response_text,
                word_count=len(response_text)
            )],
            total_words=len(response_text)
        )
        
        return revised_chapter
