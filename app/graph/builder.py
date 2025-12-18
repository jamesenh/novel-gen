"""图构建器 - 组装 LangGraph 工作流。

工作流实现:
1. 章节循环: plan -> write -> audit -> (revise loop) -> store -> next
2. Blocker 门禁: blocker > 0 强制修订; blocker == 0 推进
3. 修订上限: 达到最大轮次触发人工审核
"""

from functools import partial

from langgraph.graph import END, StateGraph

from app.config import Config
from app.generation.providers import GenerationProviders
from app.generation.template_providers import (
    TemplatePatcher,
    TemplatePlanner,
    TemplateWriter,
)
from app.graph.nodes.apply_patch import apply_patch
from app.graph.nodes.audit_chapter import audit_chapter
from app.graph.nodes.build_context_pack import build_context_pack
from app.graph.nodes.plan_chapter import plan_chapter
from app.graph.nodes.store_artifacts import store_artifacts
from app.graph.nodes.write_chapter import write_chapter
from app.graph.routing import (
    advance_chapter,
    mark_complete,
    mark_human_review,
    should_continue_chapters,
    should_revise,
)
from app.graph.state import State
from app.storage.langgraph_sqlite_checkpointer import SqliteCheckpointer


def build_graph(config: Config, *, providers: GenerationProviders | None = None):
    """构建并编译章节生成工作流图。

    图结构::

        plan_chapter
             |
             v
        write_chapter
             |
             v
        audit_chapter
             |
             v
        [should_revise?]
           /    |    \\
      revise  store  human_review
         |      |         |
         v      v         v
       audit  [next?]    END
              /    \\
         next_ch  complete
            |        |
            v        v
          plan      END

    Args:
        config: 应用配置。

    Returns:
        准备好用于调用的已编译 StateGraph。
    """
    # Create graph with State type
    graph = StateGraph(State)

    providers = providers or GenerationProviders(
        planner=TemplatePlanner(),
        writer=TemplateWriter(),
        patcher=TemplatePatcher(),
    )

    # Bind config to store_artifacts
    store_with_config = partial(store_artifacts, app_config=config)
    context_pack_with_config = partial(build_context_pack, app_config=config)
    plan_with_provider = partial(plan_chapter, planner=providers.planner)
    write_with_provider = partial(write_chapter, writer=providers.writer)
    patch_with_provider = partial(apply_patch, patcher=providers.patcher)

    # Add nodes
    graph.add_node("build_context_pack", context_pack_with_config)
    graph.add_node("plan_chapter", plan_with_provider)
    graph.add_node("write_chapter", write_with_provider)
    graph.add_node("audit_chapter", audit_chapter)
    graph.add_node("apply_patch", patch_with_provider)
    graph.add_node("store_artifacts", store_with_config)
    graph.add_node("advance_chapter", advance_chapter)
    graph.add_node("mark_human_review", mark_human_review)
    graph.add_node("mark_complete", mark_complete)

    # Set entry point
    graph.set_entry_point("build_context_pack")

    # Linear flow: context_pack -> plan -> write -> audit
    graph.add_edge("build_context_pack", "plan_chapter")
    graph.add_edge("plan_chapter", "write_chapter")
    graph.add_edge("write_chapter", "audit_chapter")

    # Conditional: audit result routing
    graph.add_conditional_edges(
        "audit_chapter",
        should_revise,
        {
            "revise": "apply_patch",
            "store": "store_artifacts",
            "human_review": "mark_human_review",
        },
    )

    # Revision loop: patch -> audit
    graph.add_edge("apply_patch", "audit_chapter")

    # Human review -> END
    graph.add_edge("mark_human_review", END)

    # After store: check if more chapters
    graph.add_conditional_edges(
        "store_artifacts",
        should_continue_chapters,
        {
            "next_chapter": "advance_chapter",
            "complete": "mark_complete",
        },
    )

    # Next chapter -> context_pack
    graph.add_edge("advance_chapter", "build_context_pack")

    # Complete -> END
    graph.add_edge("mark_complete", END)

    checkpointer = SqliteCheckpointer(config.checkpoint_db)
    return graph.compile(checkpointer=checkpointer)
