"""
NovelGen CLI 工具
统一的命令行接口，用于管理小说生成流程

开发者: Jamesenh
开发时间: 2025-11-29
更新: 2025-11-29 - 添加 SIGINT 信号处理，支持 Ctrl+C 优雅退出
更新: 2025-11-30 - 添加退出调试日志，帮助定位程序卡顿问题
"""
import os
import sys
import json
import signal
import time
import atexit
import threading
from typing import Optional, Annotated
from enum import Enum

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint

# ==================== 调试模式开关 ====================
# 设置环境变量 NOVELGEN_DEBUG=1 启用详细退出调试日志
DEBUG_EXIT = os.getenv("NOVELGEN_DEBUG", "0") == "1"


def _debug_log(msg: str):
    """输出调试日志（仅在 DEBUG_EXIT=True 时）"""
    if DEBUG_EXIT:
        timestamp = time.strftime("%H:%M:%S")
        thread_name = threading.current_thread().name
        rprint(f"[dim][{timestamp}][{thread_name}] 🔍 {msg}[/dim]")


def _list_active_threads():
    """列出所有活动线程（调试用）"""
    if not DEBUG_EXIT:
        return
    threads = threading.enumerate()
    rprint(f"[dim]📋 活动线程数: {len(threads)}[/dim]")
    for t in threads:
        daemon_flag = " (daemon)" if t.daemon else ""
        rprint(f"[dim]   - {t.name}{daemon_flag}[/dim]")


def _atexit_handler():
    """atexit 钩子 - 程序退出时调用"""
    _debug_log("atexit 钩子被调用")
    _list_active_threads()
    _debug_log("开始 atexit 清理...")


# 注册 atexit 钩子
atexit.register(_atexit_handler)

# 初始化 Typer 应用
app = typer.Typer(
    name="ng",
    help="NovelGen - AI 中文小说生成工具",
    add_completion=False,
    rich_markup_mode="rich"
)

# Rich console 用于美化输出
console = Console()

# 项目基础目录
PROJECTS_DIR = "projects"

# 全局标志：中断计数器（支持二次 Ctrl+C 强制退出）
_sigint_count = 0


def _handle_sigint(signum, frame):
    """处理 Ctrl+C 信号
    
    第一次：设置停止标志，允许优雅退出
    第二次：强制抛出 KeyboardInterrupt 立即退出
    """
    global _sigint_count
    _sigint_count += 1
    
    # 延迟导入，避免循环依赖
    try:
        from novelgen.runtime.mem0_manager import request_shutdown
        request_shutdown()
    except ImportError:
        pass
    
    if _sigint_count == 1:
        # 第一次中断：优雅停止
        rprint("\n[yellow]⚠️ 收到中断信号，正在优雅停止...[/yellow]")
        rprint("[dim]（再次按 Ctrl+C 强制退出）[/dim]")
    elif _sigint_count >= 2:
        # 第二次中断：强制退出
        rprint("\n[red]⚠️ 再次收到中断信号，强制退出[/red]")
        raise KeyboardInterrupt("用户强制中断")


def _reset_interrupt_state():
    """重置中断状态（每次运行开始时调用）"""
    global _sigint_count
    _sigint_count = 0
    
    # 重置 Mem0 停止标志
    try:
        from novelgen.runtime.mem0_manager import reset_shutdown
        reset_shutdown()
    except ImportError:
        pass


class StopStep(str, Enum):
    """工作流停止步骤"""
    world = "world_creation"
    theme = "theme_conflict_creation"
    characters = "character_creation"
    outline = "outline_creation"
    chapters_plan = "chapter_planning"


def get_project_dir(project_name: str) -> str:
    """获取项目目录路径"""
    return os.path.join(PROJECTS_DIR, project_name)


def project_exists(project_name: str) -> bool:
    """检查项目是否存在"""
    project_dir = get_project_dir(project_name)
    settings_file = os.path.join(project_dir, "settings.json")
    return os.path.exists(settings_file)


def load_json_file(filepath: str):
    """加载 JSON 文件"""
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(filepath: str, data: dict):
    """保存 JSON 文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.command()
def init(
    project_name: Annotated[str, typer.Argument(help="项目名称")],
    chapters: Annotated[int, typer.Option("--chapters", "-c", help="初始章节数")] = 3,
):
    """
    交互式创建新项目
    
    创建项目目录和 settings.json 配置文件
    """
    project_dir = get_project_dir(project_name)
    settings_file = os.path.join(project_dir, "settings.json")
    
    # 检查项目是否已存在
    if os.path.exists(settings_file):
        rprint(f"[yellow]⚠️  项目 '{project_name}' 已存在[/yellow]")
        overwrite = Confirm.ask("是否覆盖现有配置？", default=False)
        if not overwrite:
            rprint("[dim]已取消[/dim]")
            raise typer.Exit()
    
    rprint(f"\n[bold cyan]📝 创建新项目: {project_name}[/bold cyan]\n")
    
    # 交互式输入世界观描述（使用 Rich Prompt 替代 typer.prompt，更好地支持中文输入）
    rprint("[bold]请输入世界观描述[/bold]")
    rprint("[dim]（描述你想要的小说世界背景，包括时代、地点、社会制度等）[/dim]")
    world_description = Prompt.ask("世界观")
    
    # 交互式输入主题描述（可选）
    rprint("\n[bold]请输入主题描述（可选）[/bold]")
    rprint("[dim]（描述故事的核心主题和冲突，直接回车跳过）[/dim]")
    theme_description = Prompt.ask("主题", default="")
    
    # 创建项目目录
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(os.path.join(project_dir, "chapters"), exist_ok=True)
    
    # 创建 settings.json
    settings_data = {
        "project_name": project_name,
        "author": "Jamesenh",
        "world_description": world_description,
        "theme_description": theme_description,
        "initial_chapters": chapters,
        "max_chapters": max(chapters * 3, 50)
    }
    
    save_json_file(settings_file, settings_data)
    
    rprint(f"\n[green]✅ 项目创建成功！[/green]")
    rprint(f"   📁 项目目录: {project_dir}")
    rprint(f"   📄 配置文件: {settings_file}")
    rprint(f"   📖 初始章节: {chapters} 章")
    rprint(f"\n[dim]运行 'ng run {project_name}' 开始生成小说[/dim]")


@app.command()
def run(
    project_name: Annotated[str, typer.Argument(help="项目名称")],
    stop_at: Annotated[Optional[StopStep], typer.Option("--stop-at", "-s", help="停止在指定步骤")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="详细输出模式")] = False,
    no_prompt: Annotated[bool, typer.Option("--no-prompt", help="verbose 模式下不显示完整提示词")] = False,
):
    """
    运行小说生成工作流
    
    执行完整的小说生成流程，或停止在指定步骤
    """
    # 检查项目是否存在
    if not project_exists(project_name):
        rprint(f"[red]❌ 项目 '{project_name}' 不存在[/red]")
        rprint(f"[dim]请先运行 'ng init {project_name}' 创建项目[/dim]")
        raise typer.Exit(1)
    
    # 重置中断状态（每次运行开始时重置）
    _reset_interrupt_state()
    
    rprint(f"\n[bold cyan]🚀 运行项目: {project_name}[/bold cyan]\n")
    
    # 导入 orchestrator（延迟导入避免启动时加载所有依赖）
    from novelgen.runtime.orchestrator import NovelOrchestrator
    
    orchestrator = None
    try:
        _debug_log("开始创建编排器...")
        start_time = time.time()
        
        # 创建编排器
        orchestrator = NovelOrchestrator(
            project_name=project_name,
            verbose=verbose,
            show_prompt=not no_prompt
        )
        
        _debug_log(f"编排器创建完成，耗时 {time.time() - start_time:.2f}s")
        
        # 确定停止节点
        stop_node = stop_at.value if stop_at else None
        
        # 运行工作流
        _debug_log("开始运行工作流...")
        workflow_start = time.time()
        final_state = orchestrator.run_workflow(stop_at=stop_node)
        _debug_log(f"工作流执行完成，耗时 {time.time() - workflow_start:.2f}s")
        
        # 显示完成信息
        rprint("\n" + "=" * 60)
        rprint("[green]✅ 工作流执行完成！[/green]")
        rprint("=" * 60)
        
        current_step = final_state.get('current_step', '未知')
        completed_steps = final_state.get('completed_steps', [])
        
        rprint(f"当前步骤: {current_step}")
        rprint(f"已完成: {', '.join(completed_steps) if completed_steps else '无'}")
        
        failed_steps = final_state.get('failed_steps', [])
        if failed_steps:
            rprint(f"[yellow]⚠️  失败步骤: {', '.join(failed_steps)}[/yellow]")
            for step, error in final_state.get('error_messages', {}).items():
                rprint(f"  - {step}: {error}")
        
        # 导出章节
        _debug_log("开始导出章节...")
        rprint("\n[bold]💾 导出章节...[/bold]")
        orchestrator.export_all_chapters()
        _debug_log("导出章节完成")
        
    except KeyboardInterrupt:
        rprint(f"\n[yellow]⚠️ 工作流已中断[/yellow]")
        rprint(f"[dim]使用 'ng resume {project_name}' 从断点恢复[/dim]")
        _debug_log("KeyboardInterrupt 捕获，准备退出...")
        raise typer.Exit(130)  # 130 = 128 + SIGINT(2)
    except Exception as e:
        rprint(f"\n[red]❌ 工作流执行失败: {e}[/red]")
        _debug_log(f"异常捕获: {type(e).__name__}: {e}")
        raise typer.Exit(1)
    finally:
        # 清理资源
        _debug_log("进入 finally 块，开始清理资源...")
        _list_active_threads()
        
        if orchestrator is not None:
            _debug_log("调用 orchestrator.cleanup()...")
            cleanup_start = time.time()
            orchestrator.cleanup()
            _debug_log(f"cleanup() 完成，耗时 {time.time() - cleanup_start:.2f}s")
        
        _debug_log("finally 块完成")
        _list_active_threads()


@app.command()
def resume(
    project_name: Annotated[str, typer.Argument(help="项目名称")],
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="详细输出模式")] = False,
    no_prompt: Annotated[bool, typer.Option("--no-prompt", help="verbose 模式下不显示完整提示词")] = False,
):
    """
    从检查点恢复工作流
    
    从上次中断的位置继续执行
    """
    # 检查项目是否存在
    if not project_exists(project_name):
        rprint(f"[red]❌ 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)
    
    # 重置中断状态（每次运行开始时重置）
    _reset_interrupt_state()
    
    rprint(f"\n[bold cyan]🔄 恢复项目: {project_name}[/bold cyan]\n")
    
    from novelgen.runtime.orchestrator import NovelOrchestrator
    
    orchestrator = None
    try:
        _debug_log("开始创建编排器（resume）...")
        start_time = time.time()
        
        orchestrator = NovelOrchestrator(
            project_name=project_name,
            verbose=verbose,
            show_prompt=not no_prompt
        )
        
        _debug_log(f"编排器创建完成，耗时 {time.time() - start_time:.2f}s")
        _debug_log("开始恢复工作流...")
        workflow_start = time.time()
        
        final_state = orchestrator.resume_workflow()
        
        _debug_log(f"工作流恢复完成，耗时 {time.time() - workflow_start:.2f}s")
        
        rprint("\n[green]✅ 工作流恢复完成！[/green]")
        
        # 处理返回值可能是 dict 或 Pydantic 对象
        if final_state is not None:
            if hasattr(final_state, 'current_step'):
                current_step = final_state.current_step
            elif isinstance(final_state, dict):
                current_step = final_state.get('current_step', '未知')
            else:
                current_step = '未知'
            rprint(f"当前步骤: {current_step}")
        
        # 导出章节
        _debug_log("开始导出章节...")
        rprint("\n[bold]💾 导出章节...[/bold]")
        orchestrator.export_all_chapters()
        _debug_log("导出章节完成")
        
    except KeyboardInterrupt:
        rprint(f"\n[yellow]⚠️ 工作流已中断[/yellow]")
        rprint(f"[dim]已生成的内容已保存，使用 'ng resume {project_name}' 再次恢复[/dim]")
        _debug_log("KeyboardInterrupt 捕获（resume），准备退出...")
        raise typer.Exit(130)
    except Exception as e:
        rprint(f"\n[red]❌ 恢复失败: {e}[/red]")
        _debug_log(f"异常捕获（resume）: {type(e).__name__}: {e}")
        raise typer.Exit(1)
    finally:
        # 清理资源
        _debug_log("进入 finally 块（resume），开始清理资源...")
        _list_active_threads()
        
        if orchestrator is not None:
            _debug_log("调用 orchestrator.cleanup()...")
            cleanup_start = time.time()
            orchestrator.cleanup()
            _debug_log(f"cleanup() 完成，耗时 {time.time() - cleanup_start:.2f}s")
        
        _debug_log("finally 块完成（resume）")
        _list_active_threads()


@app.command()
def export(
    project_name: Annotated[str, typer.Argument(help="项目名称")],
    chapter: Annotated[Optional[int], typer.Option("--chapter", "-c", help="导出指定章节（不指定则导出全部）")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="输出文件路径")] = None,
):
    """
    导出章节为 txt 文件
    
    导出单个章节或整本小说
    """
    # 检查项目是否存在
    if not project_exists(project_name):
        rprint(f"[red]❌ 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)
    
    from novelgen.runtime.orchestrator import NovelOrchestrator
    
    try:
        orchestrator = NovelOrchestrator(project_name=project_name)
        
        if chapter is not None:
            # 导出单个章节
            rprint(f"\n[bold]📖 导出第 {chapter} 章...[/bold]")
            orchestrator.export_chapter(chapter, output_path=output)
            rprint(f"[green]✅ 第 {chapter} 章导出成功[/green]")
        else:
            # 导出全部章节
            rprint(f"\n[bold]📚 导出全部章节...[/bold]")
            orchestrator.export_all_chapters(output_path=output)
            rprint(f"[green]✅ 全部章节导出成功[/green]")
            
    except ValueError as e:
        rprint(f"[red]❌ 导出失败: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]❌ 导出失败: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    project_name: Annotated[str, typer.Argument(help="项目名称")],
):
    """
    查看项目状态
    
    显示项目的生成进度、章节信息和记忆状态
    """
    project_dir = get_project_dir(project_name)
    
    # 检查项目目录是否存在（兼容没有 settings.json 的旧项目）
    if not os.path.exists(project_dir):
        rprint(f"[red]❌ 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)
    
    # 加载各种配置文件
    settings = load_json_file(os.path.join(project_dir, "settings.json"))
    world = load_json_file(os.path.join(project_dir, "world.json"))
    theme_conflict = load_json_file(os.path.join(project_dir, "theme_conflict.json"))
    characters = load_json_file(os.path.join(project_dir, "characters.json"))
    outline = load_json_file(os.path.join(project_dir, "outline.json"))
    chapter_memory = load_json_file(os.path.join(project_dir, "chapter_memory.json"))
    
    # 项目标题
    console.print(Panel(f"📁 项目: [bold]{project_name}[/bold]", expand=False))
    
    # 生成步骤状态
    rprint("\n[bold]📋 生成步骤:[/bold]")
    
    steps = [
        ("世界观", "world.json", world is not None),
        ("主题冲突", "theme_conflict.json", theme_conflict is not None),
        ("角色设定", "characters.json", characters is not None),
        ("小说大纲", "outline.json", outline is not None),
    ]
    
    for name, filename, completed in steps:
        status_icon = "[green]✅[/green]" if completed else "[dim]⬜[/dim]"
        extra_info = ""
        if name == "小说大纲" and outline:
            chapter_count = len(outline.get("chapters", []))
            extra_info = f" ({chapter_count} 章)"
        rprint(f"  {status_icon} {name:<10} {filename}{extra_info}")
    
    # 章节计划状态
    chapters_dir = os.path.join(project_dir, "chapters")
    if outline:
        total_chapters = len(outline.get("chapters", []))
        plan_files = [f for f in os.listdir(chapters_dir) if f.endswith("_plan.json")] if os.path.exists(chapters_dir) else []
        plan_count = len(plan_files)
        plan_status = "[green]✅[/green]" if plan_count >= total_chapters else "[yellow]🔄[/yellow]"
        rprint(f"  {plan_status} 章节计划    {plan_count}/{total_chapters} 完成")
    
    # 章节生成进度
    if outline and os.path.exists(chapters_dir):
        rprint(f"\n[bold]📖 章节生成进度:[/bold]")
        
        chapters_info = outline.get("chapters", [])
        chapter_files = {}
        
        # 扫描已生成的章节文件
        for filename in os.listdir(chapters_dir):
            if filename.startswith("chapter_") and filename.endswith(".json") and "_plan" not in filename and "_revision" not in filename:
                try:
                    # 从文件名提取章节号：chapter_001.json -> 001 -> 1
                    base_name = filename.replace(".json", "")  # chapter_001
                    chapter_num = int(base_name.split("_")[1])  # 001 -> 1
                    chapter_files[chapter_num] = load_json_file(os.path.join(chapters_dir, filename))
                except (ValueError, IndexError):
                    pass
        
        generated_count = len(chapter_files)
        total_chapters = len(chapters_info)
        
        rprint(f"  已生成 [bold]{generated_count}/{total_chapters}[/bold] 章\n")
        
        # 创建章节表格
        table = Table(show_header=True, header_style="bold")
        table.add_column("章节", style="cyan", width=6)
        table.add_column("标题", width=20)
        table.add_column("场景数", justify="center", width=8)
        table.add_column("字数", justify="right", width=10)
        table.add_column("状态", justify="center", width=8)
        
        for ch_info in chapters_info:
            ch_num = ch_info.get("chapter_number", 0)
            ch_title = ch_info.get("chapter_title", "未知")[:18]
            
            if ch_num in chapter_files:
                ch_data = chapter_files[ch_num]
                scenes_count = len(ch_data.get("scenes", []))
                word_count = ch_data.get("total_words", 0)
                status_text = "[green]✅[/green]"
                table.add_row(
                    f"第{ch_num}章",
                    ch_title,
                    str(scenes_count),
                    f"{word_count:,}",
                    status_text
                )
            else:
                table.add_row(
                    f"第{ch_num}章",
                    ch_title,
                    "-",
                    "-",
                    "[dim]待生成[/dim]"
                )
        
        console.print(table)
        
        # 计算总字数
        total_words = sum(ch.get("total_words", 0) for ch in chapter_files.values())
        if total_words > 0:
            rprint(f"\n  [bold]总字数:[/bold] {total_words:,} 字")
    
    # 记忆状态
    rprint(f"\n[bold]🧠 记忆状态:[/bold]")
    
    memory_count = len(chapter_memory) if chapter_memory else 0
    rprint(f"  章节记忆: {memory_count} 条")
    
    # 尝试获取 Mem0 实体数量
    try:
        from novelgen.config import ProjectConfig
        config = ProjectConfig(project_dir=project_dir)
        if config.mem0_config and config.mem0_config.enabled:
            from novelgen.runtime.mem0_manager import Mem0Manager
            mem0_manager = Mem0Manager(
                config=config.mem0_config,
                project_id=project_name,
                embedding_config=config.embedding_config
            )
            # 获取所有记忆数量
            all_memories = mem0_manager.get_all_memories(limit=1000)
            rprint(f"  Mem0 实体: {len(all_memories)} 条")
    except Exception:
        rprint(f"  Mem0 实体: [dim]未启用或无法获取[/dim]")
    
    # 待处理修订
    rprint(f"\n[bold]⚠️  待处理修订:[/bold]")
    
    pending_revisions = []
    if os.path.exists(chapters_dir):
        for filename in os.listdir(chapters_dir):
            if filename.endswith("_revision.json"):
                revision_data = load_json_file(os.path.join(chapters_dir, filename))
                if revision_data and revision_data.get("status") == "pending":
                    pending_revisions.append(revision_data.get("chapter_number", "?"))
    
    if pending_revisions:
        rprint(f"  第 {', '.join(map(str, pending_revisions))} 章待确认")
    else:
        rprint(f"  [green]无[/green]")


class RollbackStep(str, Enum):
    """可回滚的步骤"""
    world = "world"
    theme_conflict = "theme_conflict"
    characters = "characters"
    outline = "outline"
    chapters_plan = "chapters_plan"


@app.command()
def state(
    project_name: Annotated[str, typer.Argument(help="项目名称")],
):
    """
    查看项目详细状态和可回滚点
    
    显示项目生成进度，包括步骤完成情况、章节状态、场景生成状态，
    以及可以回滚到的节点列表。
    """
    project_dir = get_project_dir(project_name)
    
    # 检查项目目录是否存在
    if not os.path.exists(project_dir):
        rprint(f"[red]❌ 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)
    
    from novelgen.runtime.orchestrator import NovelOrchestrator
    
    try:
        # 创建编排器（静默模式）
        orchestrator = NovelOrchestrator(project_name=project_name, verbose=False)
        project_state = orchestrator.get_project_state()
    except Exception as e:
        rprint(f"[red]❌ 获取项目状态失败: {e}[/red]")
        raise typer.Exit(1)
    
    # 项目标题
    console.print(Panel(f"📁 项目: [bold]{project_name}[/bold]", expand=False))
    
    # 生成步骤状态
    rprint("\n[bold]📋 生成步骤:[/bold]")
    
    steps_info = [
        ("世界观", "world", project_state["steps"].get("world", {}).get("exists", False)),
        ("主题冲突", "theme_conflict", project_state["steps"].get("theme_conflict", {}).get("exists", False)),
        ("角色设定", "characters", project_state["steps"].get("characters", {}).get("exists", False)),
        ("小说大纲", "outline", project_state["steps"].get("outline", {}).get("exists", False)),
    ]
    
    for name, key, completed in steps_info:
        status_icon = "[green]✅[/green]" if completed else "[dim]⬜[/dim]"
        extra_info = ""
        if key == "outline" and completed:
            chapter_count = project_state["steps"]["outline"].get("chapters", 0)
            extra_info = f" ({chapter_count} 章)"
        rprint(f"  {status_icon} {name:<10} {project_state['steps'].get(key, {}).get('file', '')}{extra_info}")
    
    # 章节生成状态
    chapters = project_state.get("chapters", {})
    if chapters:
        rprint(f"\n[bold]📖 章节生成状态:[/bold]")
        
        # 创建章节表格
        table = Table(show_header=True, header_style="bold")
        table.add_column("章节", style="cyan", width=8)
        table.add_column("计划", justify="center", width=6)
        table.add_column("场景进度", width=16)
        table.add_column("字数", justify="right", width=10)
        table.add_column("状态", justify="center", width=10)
        
        for ch_num in sorted(chapters.keys()):
            ch_info = chapters[ch_num]
            has_plan = ch_info.get("plan", False)
            plan_scenes = ch_info.get("plan_scenes", 0)
            generated_scenes = ch_info.get("scenes", [])
            is_complete = ch_info.get("complete", False)
            word_count = ch_info.get("word_count", 0)
            
            # 计划状态
            plan_text = "[green]✓[/green]" if has_plan else "[dim]-[/dim]"
            
            # 场景进度
            if is_complete:
                scene_text = f"[green]{len(generated_scenes)}/{plan_scenes}[/green]"
            elif generated_scenes:
                scene_text = f"[yellow]{len(generated_scenes)}/{plan_scenes}[/yellow]"
            else:
                scene_text = f"[dim]0/{plan_scenes}[/dim]"
            
            # 状态
            if is_complete:
                status_text = "[green]✅ 完成[/green]"
            elif generated_scenes:
                status_text = "[yellow]🔄 进行中[/yellow]"
            elif has_plan:
                status_text = "[dim]⬜ 待生成[/dim]"
            else:
                status_text = "[dim]⬜ 待计划[/dim]"
            
            # 字数
            word_text = f"{word_count:,}" if word_count > 0 else "-"
            
            table.add_row(
                f"第{ch_num}章",
                plan_text,
                scene_text,
                word_text,
                status_text
            )
        
        console.print(table)
        
        # 统计信息
        completed_count = sum(1 for ch in chapters.values() if ch.get("complete", False))
        in_progress_count = sum(1 for ch in chapters.values() if ch.get("scenes") and not ch.get("complete", False))
        total_words = sum(ch.get("word_count", 0) for ch in chapters.values())
        
        rprint(f"\n  已完成: [bold]{completed_count}[/bold] 章 | 进行中: [bold]{in_progress_count}[/bold] 章 | 总字数: [bold]{total_words:,}[/bold] 字")
    
    # 检查点状态
    checkpoint_exists = project_state.get("checkpoint_exists", False)
    rprint(f"\n[bold]💾 LangGraph 检查点:[/bold] {'[green]存在[/green]' if checkpoint_exists else '[dim]不存在[/dim]'}")
    
    # 可回滚点建议
    rprint(f"\n[bold]🎯 可回滚到:[/bold]")
    
    rollback_suggestions = []
    
    # 步骤级回滚建议
    if project_state["steps"].get("outline", {}).get("exists", False):
        rollback_suggestions.append(f"  ng rollback {project_name} --step outline")
    if project_state["steps"].get("characters", {}).get("exists", False):
        rollback_suggestions.append(f"  ng rollback {project_name} --step characters")
    
    # 章节级回滚建议
    if chapters:
        # 找到第一个未完成的章节
        first_incomplete_chapter = None
        for ch_num in sorted(chapters.keys()):
            ch_info = chapters[ch_num]
            if ch_info.get("complete", False):
                continue
            
            first_incomplete_chapter = ch_num
            # 这个章节未完成，可以回滚到这里
            if ch_info.get("scenes"):
                # 有部分场景，可以回滚到最后一个场景
                last_scene = max(ch_info["scenes"])
                rollback_suggestions.append(f"  ng rollback {project_name} --chapter {ch_num} --scene {last_scene}")
            rollback_suggestions.append(f"  ng rollback {project_name} --chapter {ch_num}")
            break
        
        # 找到最后一个完成的章节+1（如果和上面的建议不重复）
        completed_chapters = [ch for ch, info in chapters.items() if info.get("complete", False)]
        if completed_chapters:
            next_chapter = max(completed_chapters) + 1
            # 避免重复建议
            if next_chapter <= max(chapters.keys()) and next_chapter != first_incomplete_chapter:
                rollback_suggestions.append(f"  ng rollback {project_name} --chapter {next_chapter}")
    
    if rollback_suggestions:
        for suggestion in rollback_suggestions[:5]:  # 最多显示5个建议
            rprint(f"[dim]{suggestion}[/dim]")
    else:
        rprint("  [dim]项目为空，无需回滚[/dim]")


@app.command()
def rollback(
    project_name: Annotated[str, typer.Argument(help="项目名称")],
    step: Annotated[Optional[RollbackStep], typer.Option("--step", "-s", help="回滚到指定步骤之前")] = None,
    chapter: Annotated[Optional[int], typer.Option("--chapter", "-c", help="回滚到指定章节之前")] = None,
    scene: Annotated[Optional[int], typer.Option("--scene", help="回滚到指定场景之前（需配合 --chapter 使用）")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="跳过确认直接执行")] = False,
):
    """
    回滚项目状态到指定点
    
    删除指定点之后的所有生成内容，包括文件和 Mem0 记忆。
    回滚后 LangGraph 检查点数据库会被清除，下次运行会从文件状态重建。
    
    示例:
      ng rollback demo_020 --step outline      # 回滚到大纲之前
      ng rollback demo_020 --chapter 5         # 回滚到第5章之前
      ng rollback demo_020 --chapter 3 --scene 2  # 回滚到第3章第2场景之前
    """
    project_dir = get_project_dir(project_name)
    
    # 检查项目目录是否存在
    if not os.path.exists(project_dir):
        rprint(f"[red]❌ 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)
    
    # 参数验证
    if step is not None and chapter is not None:
        rprint("[red]❌ --step 和 --chapter 不能同时指定[/red]")
        raise typer.Exit(1)
    
    if scene is not None and chapter is None:
        rprint("[red]❌ --scene 必须配合 --chapter 使用[/red]")
        raise typer.Exit(1)
    
    if step is None and chapter is None:
        rprint("[red]❌ 必须指定 --step 或 --chapter[/red]")
        rprint(f"[dim]使用 'ng state {project_name}' 查看可回滚点[/dim]")
        raise typer.Exit(1)
    
    # 构建回滚描述
    if step is not None:
        target_desc = f"步骤 '{step.value}' 之前"
    elif scene is not None:
        target_desc = f"第 {chapter} 章第 {scene} 场景之前"
    else:
        target_desc = f"第 {chapter} 章之前"
    
    # 确认回滚
    if not force:
        rprint(f"\n[bold yellow]⚠️  即将回滚项目 '{project_name}' 到 {target_desc}[/bold yellow]")
        rprint("[yellow]此操作将删除以下内容：[/yellow]")
        rprint("  - 目标点之后的所有生成文件")
        rprint("  - 相关的章节记忆和一致性报告")
        rprint("  - Mem0 中对应的场景记忆")
        rprint("  - LangGraph 检查点数据库")
        rprint("\n[bold red]此操作不可撤销！[/bold red]")
        
        confirm = Confirm.ask("确定要继续吗？", default=False)
        if not confirm:
            rprint("[dim]已取消[/dim]")
            raise typer.Exit()
    
    from novelgen.runtime.orchestrator import NovelOrchestrator
    
    try:
        rprint(f"\n[bold cyan]🔄 回滚项目: {project_name}[/bold cyan]")
        
        # 创建编排器
        orchestrator = NovelOrchestrator(project_name=project_name, verbose=False)
        
        # 执行回滚
        if step is not None:
            result = orchestrator.rollback_to_step(step.value)
        elif scene is not None:
            result = orchestrator.rollback_to_scene(chapter, scene)
        else:
            result = orchestrator.rollback_to_chapter(chapter)
        
        # 显示结果
        rprint("\n" + "=" * 60)
        rprint("[green]✅ 回滚完成！[/green]")
        rprint("=" * 60)
        
        deleted_files = result.get("deleted_files", [])
        deleted_memories = result.get("deleted_memories", 0)
        
        rprint(f"  删除文件: {len(deleted_files)} 个")
        rprint(f"  删除记忆: {deleted_memories} 条")
        
        rprint(f"\n[dim]使用 'ng resume {project_name}' 从断点继续生成[/dim]")
        
    except Exception as e:
        rprint(f"\n[red]❌ 回滚失败: {e}[/red]")
        raise typer.Exit(1)


@app.callback()
def main():
    """
    NovelGen - AI 中文小说生成工具
    
    使用 LangChain + LangGraph 构建的智能小说生成系统
    """
    # 注册 Ctrl+C 信号处理器
    signal.signal(signal.SIGINT, _handle_sigint)


if __name__ == "__main__":
    app()

