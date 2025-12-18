"""`run` 启动前的背景资产 bootstrap。

目标（可用级 MVP）：
- 用户只提供简短提示词（prompt）
- 若 bible/outline 资产缺失，则自动扩写并生成：
  - world.json
  - characters.json
  - theme_conflict.json
  - outline.json
- 若资产已存在，则默认只加载复用（不静默覆写）

本模块实现“无外部依赖”的最小可用生成逻辑：
- 通过简单规则将 prompt 扩写为 requirements
- 用模板与少量启发式生成背景 JSON（可被后续检索/插件消费）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from app.schemas.base import add_metadata
from app.storage.artifact_store import ArtifactStore


@dataclass(frozen=True)
class BootstrapResult:
    """bootstrap 的结果（写入 state）。"""

    requirements: Dict[str, Any]
    world: Dict[str, Any]
    characters: Dict[str, Any]
    theme_conflict: Dict[str, Any]
    outline: Dict[str, Any]


def parse_prompt(prompt: str) -> Dict[str, Any]:
    """将用户简短 prompt 扩写为结构化 requirements（最小实现）。"""
    text = (prompt or "").strip()
    realms: list[str] = []
    if "三界" in text or "3界" in text:
        # 简单抽取括号内容中的分界
        if "(" in text and ")" in text:
            inside = text.split("(", 1)[1].split(")", 1)[0]
            realms = [
                p.strip() for p in inside.replace("，", ",").split(",") if p.strip()
            ]

    genre = "修仙" if "修仙" in text or "仙" in text else "架空"

    return {
        "prompt": text,
        "genre": genre,
        "realms": realms,
        "constraints": [
            "完全架空",
            "世界观自洽",
            "可持续扩写为长篇",
        ],
    }


def _default_world(requirements: Dict[str, Any]) -> Dict[str, Any]:
    realms = requirements.get("realms") or ["人界", "灵界", "魔界"]
    return {
        "name": "三界",
        "genre": requirements.get("genre", "架空"),
        "realms": [
            {"name": r, "overview": f"{r}的核心生态与势力结构。"} for r in realms
        ],
        "rules": [
            "修炼体系与资源获取遵循因果与代价原则。",
            "跨界通行需要代价或契机，且会引发势力博弈。",
        ],
        "magic_system": {
            "core": "以灵气/功法/心境为三轴的修炼体系。",
            "stages": ["炼体", "筑基", "金丹", "元婴", "化神"],
        },
        "factions": [
            {"name": "天衡盟", "realm": realms[0], "goal": "维持秩序与资源分配"},
            {"name": "幽烬宫", "realm": realms[-1], "goal": "打破封印，改写规则"},
        ],
    }


def _default_characters(requirements: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "protagonist": {
            "name": "林澈",
            "role": "主角",
            "traits": ["克制", "好奇", "不服输"],
            "wants": "变强并查清身世",
            "fear": "被命运利用成为工具",
            "secret": "体内封有跨界钥印",
        },
        "supporting": [
            {
                "name": "沈岚",
                "role": "同伴",
                "traits": ["冷静", "敏锐"],
                "wants": "复兴师门",
            },
            {
                "name": "墨阙",
                "role": "对手/亦敌亦友",
                "traits": ["骄傲", "果断"],
                "wants": "证明自己配得上天命",
            },
        ],
        "antagonist": {
            "name": "幽烬宫主",
            "role": "反派",
            "wants": "解除封印并统一三界",
            "methods": ["诱惑", "交易", "献祭"],
        },
    }


def _default_theme_conflict(requirements: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "theme": "自由与代价",
        "core_question": "获得力量是否必然失去自我？",
        "conflict": {
            "external": "三界势力争夺跨界资源与钥印",
            "internal": "主角在善恶与自我之间做选择",
        },
        "stakes": [
            "个人：主角的命运与自我完整性",
            "世界：三界的秩序与生灵存续",
        ],
    }


def _default_outline(requirements: Dict[str, Any], num_chapters: int) -> Dict[str, Any]:
    chapters = []
    for i in range(1, num_chapters + 1):
        chapters.append(
            {
                "chapter_id": i,
                "pov": "林澈",
                "goal": f"第{i}章：推进主线并获得关键线索",
                "conflict": "阻力来自势力博弈与自身短板",
                "turn": "一次意外揭开更大阴谋的一角",
                "threads": [f"T-{i:02d}"],
                "must_include": ["三界设定信息点", "角色动机推进"],
                "must_avoid": ["过早解释终极谜底"],
            }
        )
    return {
        "num_chapters": num_chapters,
        "chapters": chapters,
        "high_level_arc": [
            "开端：进入局",
            "发展：代价显现",
            "反转：真相逼近",
            "高潮：选择与决断",
        ],
    }


def ensure_background_assets(
    *,
    store: ArtifactStore,
    prompt: str,
    num_chapters: int,
    generator: str,
    allow_overwrite: bool = False,
) -> BootstrapResult:
    """确保背景资产存在；必要时基于 prompt 自动生成并写盘。"""
    requirements = parse_prompt(prompt) if prompt.strip() else {}

    world = store.read_world()
    characters = store.read_characters()
    theme_conflict = store.read_theme_conflict()
    outline = store.read_outline()

    missing_any = not world or not characters or not theme_conflict or not outline
    if missing_any and not prompt.strip():
        raise ValueError(
            "项目缺少背景资产（world/characters/theme_conflict/outline），且未提供 --prompt。"
        )

    if not world or allow_overwrite:
        world = add_metadata(_default_world(requirements), generator=generator)
        store.write_world(world)

    if not characters or allow_overwrite:
        characters = add_metadata(
            _default_characters(requirements), generator=generator
        )
        store.write_characters(characters)

    if not theme_conflict or allow_overwrite:
        theme_conflict = add_metadata(
            _default_theme_conflict(requirements), generator=generator
        )
        store.write_theme_conflict(theme_conflict)

    if not outline or allow_overwrite:
        outline = add_metadata(
            _default_outline(requirements, num_chapters), generator=generator
        )
        store.write_outline(outline)

    # 即使资产存在，也写入 requirements（用于后续检索与生成链路）
    if not requirements:
        requirements = {"prompt": prompt.strip()}

    return BootstrapResult(
        requirements=requirements,
        world=world,
        characters=characters,
        theme_conflict=theme_conflict,
        outline=outline,
    )
