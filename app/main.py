#!/usr/bin/env python3
"""Novel-Gen v2 命令行入口。

用法:
    python -m app.main init --project <name>
    python -m app.main run --project <name> --chapters <n>
    python -m app.main continue --project <name>
"""

import argparse
import sys

from app.bootstrap.bootstrap import ensure_background_assets
from app.config import Config, load_config
from app.graph.builder import build_graph
from app.graph.run_config import build_thread_config
from app.graph.state import create_initial_state
from app.retrieval.index import search
from app.storage.artifact_store import ArtifactStore


def cmd_init(args: argparse.Namespace, config: Config) -> int:
    """初始化新项目，创建 settings.json。"""
    store = ArtifactStore(config.project_root)
    if store.project_exists():
        print(
            f"Project '{config.project_name}' already exists at {config.project_root}"
        )
        return 1

    store.init_project(
        project_name=config.project_name,
        author=config.author,
    )
    print(f"Initialized project '{config.project_name}' at {config.project_root}")
    return 0


def cmd_run(args: argparse.Namespace, config: Config) -> int:
    """从头运行生成工作流。"""
    store = ArtifactStore(config.project_root)
    if not store.project_exists():
        print(f"Project '{config.project_name}' not found. Run 'init' first.")
        return 1

    num_chapters = args.chapters or config.num_chapters
    prompt = args.prompt or ""

    state = create_initial_state(
        project_name=config.project_name,
        num_chapters=num_chapters,
        prompt=prompt,
        max_revision_rounds=config.max_revision_rounds,
        qa_blocker_max=config.qa_blocker_max,
        qa_major_max=config.qa_major_max,
    )

    print(
        f"Starting generation for '{config.project_name}', {num_chapters} chapter(s)..."
    )

    # Bootstrap: 生成/加载背景资产（world/characters/theme_conflict/outline）
    generator = f"novel-gen-v2/{state['run_id']}/{state['revision_id']}"
    print("[BOOTSTRAP] Parsing prompt -> requirements")

    world_path = config.project_root / "world.json"
    characters_path = config.project_root / "characters.json"
    theme_conflict_path = config.project_root / "theme_conflict.json"
    outline_path = config.project_root / "outline.json"

    for p, label in [
        (world_path, "world.json"),
        (characters_path, "characters.json"),
        (theme_conflict_path, "theme_conflict.json"),
        (outline_path, "outline.json"),
    ]:
        if p.exists():
            print(f"[BOOTSTRAP] {label} exists -> loading")
        else:
            print(f"[BOOTSTRAP] {label} missing -> generating")

    try:
        bootstrap = ensure_background_assets(
            store=store,
            prompt=prompt,
            num_chapters=num_chapters,
            generator=generator,
            allow_overwrite=False,
        )
    except ValueError as e:
        print(f"[ERROR] {e}")
        return 1

    state["requirements"] = bootstrap.requirements
    state["world"] = bootstrap.world
    state["characters"] = bootstrap.characters
    state["theme_conflict"] = bootstrap.theme_conflict
    state["outline"] = bootstrap.outline

    graph = build_graph(config)

    # Execute the graph
    final_state = graph.invoke(state, build_thread_config(config.project_name))

    # Check final status
    if final_state.get("needs_human_review"):
        print(f"[WARN] Chapter {final_state['current_chapter']} needs human review.")
        return 2

    print("[OK] Generation completed successfully.")
    return 0


def cmd_continue(args: argparse.Namespace, config: Config) -> int:
    """从检查点继续运行。"""
    store = ArtifactStore(config.project_root)
    if not store.project_exists():
        print(f"Project '{config.project_name}' not found. Run 'init' first.")
        return 1

    graph = build_graph(config)
    thread_cfg = build_thread_config(config.project_name)

    snapshot = graph.get_state(thread_cfg)
    if snapshot.created_at is None and snapshot.metadata is None:
        print(
            f"No checkpoint found for project '{config.project_name}'. Run 'run' first."
        )
        return 1

    if not snapshot.next:
        print("[OK] Nothing to continue (already at END).")
        return 0

    print(f"Continuing generation for '{config.project_name}' from checkpoint...")
    final_state = graph.invoke(None, thread_cfg)

    if final_state.get("needs_human_review"):
        print(f"[WARN] Chapter {final_state['current_chapter']} needs human review.")
        return 2

    print("[OK] Generation completed successfully.")
    return 0


def cmd_ask(args: argparse.Namespace, config: Config) -> int:
    """检索项目资产并给出综合回答（无向量库，关键词检索）。"""
    store = ArtifactStore(config.project_root)
    if not store.project_exists():
        print(f"Project '{config.project_name}' not found. Run 'init' first.")
        return 1

    question = (args.question or "").strip()
    if not question:
        print("[ERROR] --question 不能为空")
        return 1

    hits = search(
        config.project_root,
        config.retrieval_db,
        query=question,
        top_k=int(args.top_k or 8),
    )

    if not hits:
        print("未命中任何来源。")
        return 0

    print("综合回答（基于检索到的项目文档摘录）：")
    for i, h in enumerate(hits, start=1):
        excerpt = (h.excerpt or "").replace("\n", " ").strip()
        print(f"{i}. [{h.doc_type}] {excerpt}")

    print("\nSources:")
    for h in hits:
        print(f"- {h.source_path} ({h.source_id})")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="novel-gen",
        description="Novel-Gen v2: Workflow-first novel generation",
    )
    parser.add_argument(
        "--project",
        "-p",
        help="Project name (overrides PROJECT_NAME env var)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.set_defaults(func=cmd_init)

    # run
    run_parser = subparsers.add_parser("run", help="Run the generation workflow")
    run_parser.add_argument(
        "--chapters", "-c", type=int, help="Number of chapters to generate"
    )
    run_parser.add_argument("--prompt", help="Initial prompt for generation")
    run_parser.set_defaults(func=cmd_run)

    # continue
    continue_parser = subparsers.add_parser("continue", help="Continue from checkpoint")
    continue_parser.set_defaults(func=cmd_continue)

    # ask
    ask_parser = subparsers.add_parser("ask", help="Ask questions over project assets")
    ask_parser.add_argument("--question", required=True, help="Question to ask")
    ask_parser.add_argument("--top-k", type=int, default=8, help="Max number of hits")
    ask_parser.set_defaults(func=cmd_ask)

    args = parser.parse_args()

    # Load config with optional project override
    config = load_config(project_name=args.project)

    return args.func(args, config)


if __name__ == "__main__":
    sys.exit(main())
