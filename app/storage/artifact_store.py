"""资产存储 - 管理项目资产的持久化。

所有 I/O 都通过这层:
- 每种资产类型的标准路径
- 章节资产的原子捆绑写入（先写临时文件，再 rename 到位）
- 强制 UTF-8 编码
- 内容 + 记忆 + 报告的同步更新
"""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.schemas.base import add_metadata
from app.schemas.validation import (
    validate_chapter_memory,
    validate_consistency_reports,
    validate_issues_list,
)


class AtomicWriteError(Exception):
    """原子写入失败时抛出的异常。"""

    pass


class ArtifactStore:
    """管理项目的资产持久化。

    标准路径:
    - projects/<project>/settings.json
    - projects/<project>/world.json
    - projects/<project>/characters.json
    - projects/<project>/theme_conflict.json
    - projects/<project>/outline.json
    - projects/<project>/chapters/chapter_XXX_plan.json
    - projects/<project>/chapters/chapter_XXX.json
    - projects/<project>/consistency_reports.json
    - projects/<project>/chapter_memory.json
    - projects/<project>/data/novel.db
    """

    def __init__(self, project_root: Path):
        """初始化资产存储。

        Args:
            project_root: 项目目录路径 (projects/<name>/)。
        """
        self.project_root = Path(project_root)
        self.chapters_dir = self.project_root / "chapters"
        self.data_dir = self.project_root / "data"

    def project_exists(self) -> bool:
        """检查项目目录是否存在。"""
        return self.project_root.exists()

    def init_project(
        self,
        project_name: str,
        author: str = "",
    ) -> None:
        """初始化新项目，创建 settings.json。

        Args:
            project_name: 项目名称。
            author: 作者名称。
        """
        self.project_root.mkdir(parents=True, exist_ok=True)
        self.chapters_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)

        settings = add_metadata(
            {
                "project_name": project_name,
                "author": author,
                "created_at": datetime.now().isoformat(),
            }
        )
        self._write_json(self.project_root / "settings.json", settings)

    def write_chapter_bundle(
        self,
        chapter_id: int,
        plan: Dict[str, Any],
        content: Dict[str, Any],
        audit: Dict[str, Any],
    ) -> None:
        """将章节资产作为原子捆绑写入。

        使用临时目录写入所有文件，然后逐个 rename 到位。
        如果任何写入失败，确保不留下部分资产。

        写入:
        1. chapters/chapter_XXX_plan.json
        2. chapters/chapter_XXX.json
        3. 更新 consistency_reports.json
        4. 更新 chapter_memory.json

        如果 data/novel.db 存在，则标记为陈旧。

        Args:
            chapter_id: 章节编号（1 开始索引）。
            plan: 章节计划字典。
            content: 章节内容字典。
            audit: 审计结果字典。

        Raises:
            AtomicWriteError: 如果原子写入失败。
        """
        chapter_str = f"{chapter_id:03d}"

        # 定义所有要写入的文件
        plan_path = self.chapters_dir / f"chapter_{chapter_str}_plan.json"
        content_path = self.chapters_dir / f"chapter_{chapter_str}.json"
        reports_path = self.project_root / "consistency_reports.json"
        memory_path = self.project_root / "chapter_memory.json"

        # 幂等写盘：如果目标文件已存在且 revision_id 相同，则不重复写入。
        # 这用于支持 continue 时“重放 store 节点”不引入重复写盘漂移。
        revision_id = content.get("revision_id") or plan.get("revision_id")
        if revision_id and self._bundle_already_persisted(
            plan_path=plan_path,
            content_path=content_path,
            revision_id=str(revision_id),
        ):
            return

        # Validate audit issues before they can be persisted anywhere.
        issues_result = validate_issues_list(audit.get("issues", []))
        if not issues_result:
            raise ValueError(
                f"Audit issues validation failed: {issues_result.error_messages}"
            )

        # 准备更新后的 reports 和 memory 数据
        reports_data = self._prepare_consistency_reports(chapter_id, audit)
        memory_data = self._prepare_chapter_memory(chapter_id, content)

        # Validate derived files before writing; use validated dumps (adds defaults).
        reports_result = validate_consistency_reports(reports_data)
        if not reports_result:
            raise ValueError(
                f"consistency_reports.json validation failed: {reports_result.error_messages}"
            )

        memory_result = validate_chapter_memory(memory_data)
        if not memory_result:
            raise ValueError(
                f"chapter_memory.json validation failed: {memory_result.error_messages}"
            )

        # 收集所有要写入的文件
        files_to_write: List[Tuple[Path, Dict[str, Any]]] = [
            (plan_path, plan),
            (content_path, content),
            (reports_path, reports_result.data or reports_data),
            (memory_path, memory_result.data or memory_data),
        ]

        # 执行原子写入
        self._atomic_write_bundle(files_to_write)

        # Handle optional DB
        self._mark_db_stale_if_exists()

    def _bundle_already_persisted(
        self,
        plan_path: Path,
        content_path: Path,
        revision_id: str,
    ) -> bool:
        """判断某个章节 bundle 是否已以同一 revision_id 持久化完成。

        仅当 plan/content 两个文件都存在且 revision_id 相同才视为“已完成”。
        """
        if not (plan_path.exists() and content_path.exists()):
            return False

        try:
            plan = self._read_json(plan_path)
            content = self._read_json(content_path)
        except Exception:
            return False

        return (
            str(plan.get("revision_id", "")) == revision_id
            and str(content.get("revision_id", "")) == revision_id
        )

    def _atomic_write_bundle(self, files: List[Tuple[Path, Dict[str, Any]]]) -> None:
        """原子写入多个文件。

        先将所有文件写入临时目录，然后逐个 rename 到目标位置。
        如果任何操作失败，清理已写入的文件。

        Args:
            files: (目标路径, 数据) 元组列表。

        Raises:
            AtomicWriteError: 如果写入失败。
        """
        # 确保所有父目录存在
        for target_path, _ in files:
            target_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建临时目录（放在 project_root 下，避免跨文件系统导致“非原子 move”）
        self.project_root.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(
            tempfile.mkdtemp(prefix="novel_gen_atomic_", dir=str(self.project_root))
        )
        temp_files: List[Tuple[Path, Path]] = []  # (temp_path, target_path)
        completed_renames: List[Tuple[Path, Path]] = []  # 用于回滚

        try:
            # 第一阶段：写入临时文件
            for i, (target_path, data) in enumerate(files):
                temp_path = temp_dir / f"file_{i}.json"
                self._write_json(temp_path, data)
                temp_files.append((temp_path, target_path))

            # 第二阶段：原子 rename 到目标位置
            for temp_path, target_path in temp_files:
                # 如果目标存在，先备份
                backup_path = None
                if target_path.exists():
                    backup_path = temp_dir / f"backup_{target_path.name}"
                    shutil.copy2(target_path, backup_path)

                # 执行替换（同一文件系统上原子；可覆盖已有目标）
                os.replace(temp_path, target_path)
                completed_renames.append((target_path, backup_path))

        except Exception as e:
            # 回滚已完成的 rename
            for target_path, backup_path in reversed(completed_renames):
                try:
                    if backup_path and backup_path.exists():
                        os.replace(backup_path, target_path)
                    elif target_path.exists():
                        target_path.unlink()
                except Exception:
                    pass  # 尽力回滚

            raise AtomicWriteError(f"原子写入失败: {e}") from e

        finally:
            # 清理临时目录
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    def _prepare_consistency_reports(
        self,
        chapter_id: int,
        audit: Dict[str, Any],
    ) -> Dict[str, Any]:
        """准备更新后的 consistency_reports 数据。

        Args:
            chapter_id: 章节编号。
            audit: 审计结果字典。

        Returns:
            更新后的 reports 数据字典。
        """
        reports_path = self.project_root / "consistency_reports.json"
        reports = self._read_json(reports_path)

        if "chapters" not in reports:
            reports = add_metadata({"chapters": {}})

        reports["chapters"][str(chapter_id)] = {
            "chapter_id": chapter_id,
            "issues": audit.get("issues", []),
            "blocker_count": audit.get("blocker_count", 0),
            "major_count": audit.get("major_count", 0),
            "minor_count": audit.get("minor_count", 0),
            "updated_at": datetime.now().isoformat(),
            "major_over_threshold": audit.get("major_over_threshold", False),
            "qa_major_max": audit.get("qa_major_max"),
        }
        reports["updated_at"] = datetime.now().isoformat()

        return reports

    def _prepare_chapter_memory(
        self,
        chapter_id: int,
        content: Dict[str, Any],
    ) -> Dict[str, Any]:
        """准备更新后的 chapter_memory 数据。

        Args:
            chapter_id: 章节编号。
            content: 章节内容字典。

        Returns:
            更新后的 memory 数据字典。
        """
        memory_path = self.project_root / "chapter_memory.json"
        memory = self._read_json(memory_path)

        if "chapters" not in memory:
            memory = add_metadata({"chapters": {}})

        # Extract summary from content (stub - would use LLM in production)
        scenes = content.get("scenes", [])
        memory["chapters"][str(chapter_id)] = {
            "chapter_id": chapter_id,
            "title": content.get("title", f"第{chapter_id}章"),
            "scene_count": len(scenes),
            "word_count": content.get("word_count", 0),
            "updated_at": datetime.now().isoformat(),
        }
        memory["updated_at"] = datetime.now().isoformat()

        return memory

    def _write_json(self, path: Path, data: Dict[str, Any]) -> None:
        """使用 UTF-8 编码将 JSON 数据写入文件。

        Args:
            path: 文件路径。
            data: 要写入的数据。
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _read_json(self, path: Path) -> Dict[str, Any]:
        """从文件读取 JSON 数据。

        Args:
            path: 文件路径。

        Returns:
            解析后的 JSON 数据，如果文件不存在则返回空字典。
        """
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _mark_db_stale_if_exists(self) -> None:
        """如果 novel.db 存在则标记为陈旧。

        在数据库旁创建 .stale 标记文件，表示记忆/实体数据可能与资产不同步。
        """
        db_path = self.data_dir / "novel.db"
        if db_path.exists():
            stale_marker = self.data_dir / "novel.db.stale"
            stale_marker.write_text(
                f"Marked stale at {datetime.now().isoformat()}\n"
                "Memory chunks and entity snapshots may be out of sync.\n"
                "Run backfill to synchronize.",
                encoding="utf-8",
            )

    def read_settings(self) -> Dict[str, Any]:
        """读取项目设置。"""
        return self._read_json(self.project_root / "settings.json")

    def read_consistency_reports(self) -> Dict[str, Any]:
        """读取 consistency_reports.json。"""
        return self._read_json(self.project_root / "consistency_reports.json")

    def read_chapter_memory(self) -> Dict[str, Any]:
        """读取 chapter_memory.json。"""
        return self._read_json(self.project_root / "chapter_memory.json")

    def read_world(self) -> Dict[str, Any]:
        """读取 world.json。"""
        return self._read_json(self.project_root / "world.json")

    def read_characters(self) -> Dict[str, Any]:
        """读取 characters.json。"""
        return self._read_json(self.project_root / "characters.json")

    def read_theme_conflict(self) -> Dict[str, Any]:
        """读取 theme_conflict.json。"""
        return self._read_json(self.project_root / "theme_conflict.json")

    def read_outline(self) -> Dict[str, Any]:
        """读取 outline.json。"""
        return self._read_json(self.project_root / "outline.json")

    def write_world(self, data: Dict[str, Any]) -> None:
        """写入 world.json。"""
        self._write_json(self.project_root / "world.json", data)

    def write_characters(self, data: Dict[str, Any]) -> None:
        """写入 characters.json。"""
        self._write_json(self.project_root / "characters.json", data)

    def write_theme_conflict(self, data: Dict[str, Any]) -> None:
        """写入 theme_conflict.json。"""
        self._write_json(self.project_root / "theme_conflict.json", data)

    def write_outline(self, data: Dict[str, Any]) -> None:
        """写入 outline.json。"""
        self._write_json(self.project_root / "outline.json", data)

    def read_chapter_plan(self, chapter_id: int) -> Dict[str, Any]:
        """读取章节计划。"""
        path = self.chapters_dir / f"chapter_{chapter_id:03d}_plan.json"
        return self._read_json(path)

    def read_chapter_content(self, chapter_id: int) -> Dict[str, Any]:
        """读取章节内容。"""
        path = self.chapters_dir / f"chapter_{chapter_id:03d}.json"
        return self._read_json(path)
