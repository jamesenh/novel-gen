"""Schema 校验工具。

在持久化前提供校验，确保资产在写入磁盘前满足 schema 要求。
"""

from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError

from .artifacts import (
    ChapterMemoryFile,
    ChapterReportEntry,
    ConsistencyReportsFile,
)
from .chapter import ChapterContent, ChapterPlan
from .context_pack import ContextPack
from .issues import AuditReport, Issue


class ValidationResult:
    """Schema 校验尝试的结果。"""

    def __init__(
        self,
        valid: bool,
        data: Optional[Dict[str, Any]] = None,
        errors: Optional[list] = None,
    ):
        self.valid = valid
        self.data = data
        self.errors = errors or []

    def __bool__(self) -> bool:
        return self.valid

    @property
    def error_messages(self) -> list[str]:
        """获取人类可读的错误消息。"""
        return [
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in self.errors
        ]


def validate_artifact(
    data: Dict[str, Any],
    schema: Type[BaseModel],
) -> ValidationResult:
    """根据 schema 校验资产。

    Args:
        data: 要校验的资产数据。
        schema: 用于校验的 Pydantic 模型。

    Returns:
        包含 valid 标志和任何错误的 ValidationResult。
    """
    try:
        validated = schema.model_validate(data)
        return ValidationResult(valid=True, data=validated.model_dump())
    except ValidationError as e:
        return ValidationResult(valid=False, errors=e.errors())


def validate_chapter_plan(data: Dict[str, Any]) -> ValidationResult:
    """校验章节计划资产。"""
    return validate_artifact(data, ChapterPlan)


def validate_chapter_content(data: Dict[str, Any]) -> ValidationResult:
    """校验章节内容资产。"""
    return validate_artifact(data, ChapterContent)


def validate_audit_report(data: Dict[str, Any]) -> ValidationResult:
    """校验审计报告资产。"""
    return validate_artifact(data, AuditReport)


def validate_consistency_reports(data: Dict[str, Any]) -> ValidationResult:
    """校验 consistency_reports.json 文件。"""
    return validate_artifact(data, ConsistencyReportsFile)


def validate_chapter_memory(data: Dict[str, Any]) -> ValidationResult:
    """校验 chapter_memory.json 文件。"""
    return validate_artifact(data, ChapterMemoryFile)


def validate_issues_list(issues: List[Dict[str, Any]]) -> ValidationResult:
    """校验问题列表（插件输出）。

    Args:
        issues: 问题字典列表。

    Returns:
        ValidationResult，如果任何问题无效则包含所有错误。
    """
    all_errors: List[Dict[str, Any]] = []

    for i, issue_data in enumerate(issues):
        try:
            Issue.model_validate(issue_data)
        except ValidationError as e:
            # 为每个错误添加问题索引前缀
            for error in e.errors():
                prefixed_error = {
                    **error,
                    "loc": (f"issues[{i}]",) + tuple(error.get("loc", ())),
                }
                all_errors.append(prefixed_error)

    if all_errors:
        return ValidationResult(valid=False, errors=all_errors)

    return ValidationResult(valid=True, data={"issues": issues})


def validate_context_pack(data: Dict[str, Any]) -> ValidationResult:
    """校验 context_pack 结构。"""
    return validate_artifact(data, ContextPack)


# Registry mapping artifact types to schemas
ARTIFACT_SCHEMAS: Dict[str, Type[BaseModel]] = {
    "chapter_plan": ChapterPlan,
    "chapter_content": ChapterContent,
    "audit_report": AuditReport,
    "issue": Issue,
    "consistency_reports": ConsistencyReportsFile,
    "chapter_memory": ChapterMemoryFile,
    "chapter_report_entry": ChapterReportEntry,
    "context_pack": ContextPack,
}


def validate_by_type(
    data: Dict[str, Any],
    artifact_type: str,
) -> ValidationResult:
    """按类型名称校验资产。

    Args:
        data: 要校验的资产数据。
        artifact_type: ARTIFACT_SCHEMAS 中的类型键。

    Returns:
        包含 valid 标志和任何错误的 ValidationResult。

    Raises:
        ValueError: 如果 artifact_type 未知。
    """
    schema = ARTIFACT_SCHEMAS.get(artifact_type)
    if not schema:
        raise ValueError(f"Unknown artifact type: {artifact_type}")
    return validate_artifact(data, schema)
