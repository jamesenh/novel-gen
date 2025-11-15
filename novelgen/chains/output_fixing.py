"""
自定义的LLM JSON修复解析器

参考LangChain官方文档中“LLM powered retries (OutputFixingParser)”的思路，
在当前版本缺少该类的情况下，提供等价功能：当解析失败时，利用同一个LLM
根据错误信息和JSON schema对输出进行修复，直至返回可解析结果或超出重试次数。
"""
from __future__ import annotations

from typing import Generic, TypeVar

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import BaseOutputParser, StrOutputParser
from langchain_core.outputs import Generation
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import ConfigDict, PrivateAttr

T = TypeVar("T")


class LLMJsonRepairOutputParser(BaseOutputParser[T], Generic[T]):
    """在解析失败时自动调用LLM修复输出的解析器。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    _base_parser: BaseOutputParser[T] = PrivateAttr()
    _max_retries: int = PrivateAttr(default=2)
    _format_instructions: str = PrivateAttr(default="")
    _fix_prompt: ChatPromptTemplate = PrivateAttr()
    _fix_chain: Runnable = PrivateAttr()

    def __init__(
        self,
        parser: BaseOutputParser[T],
        llm: BaseLanguageModel,
        max_retries: int = 2,
    ) -> None:
        super().__init__()

        format_instructions = ""
        if hasattr(parser, "get_format_instructions"):
            try:
                format_instructions = parser.get_format_instructions()
            except Exception:  # pragma: no cover - 仅用于容错
                format_instructions = ""

        self._base_parser = parser
        self._max_retries = max_retries
        self._format_instructions = format_instructions
        self._fix_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是JSON修复专家。请只返回符合指定schema的有效JSON，"
                    "不得添加解释或多余文本。",
                ),
                (
                    "user",
                    """请根据以下信息修复模型输出：

【原始输出】
{bad_output}

【错误信息】
{error_message}

【JSON格式要求】
{format_instructions}

要求：
1. 仅返回JSON，不能包含Markdown或额外文字
2. 保留语义但修复结构/转义问题
3. 如需使用引号，请确保正确转义（例如把内嵌英文引号写成\\"或使用「」）
""",
                ),
            ]
        )
        # 追加 StrOutputParser 以确保拿到纯字符串结果
        self._fix_chain = self._fix_prompt | llm | StrOutputParser()

    def _repair_text(self, text: str, error_message: str) -> str:
        """调用LLM修复JSON字符串。"""
        return self._fix_chain.invoke(
            {
                "bad_output": text,
                "error_message": error_message,
                "format_instructions": self._format_instructions,
            }
        )

    def parse_result(self, result: list[Generation], *, partial: bool = False) -> T:
        """优先尝试基础解析器，失败则触发修复逻辑。"""
        try:
            return self._base_parser.parse_result(result, partial=partial)
        except Exception as error:  # 捕获所有解析异常
            last_text = (
                error.llm_output  # type: ignore[attr-defined]
                if isinstance(error, OutputParserException)
                and getattr(error, "llm_output", None)
                else result[0].text
            )
            final_error = error
            for _ in range(self._max_retries):
                fixed_text = self._repair_text(last_text, str(final_error))
                try:
                    return self._base_parser.parse_result(
                        [Generation(text=fixed_text)],
                        partial=partial,
                    )
                except Exception as retry_error:
                    last_text = (
                        retry_error.llm_output  # type: ignore[attr-defined]
                        if isinstance(retry_error, OutputParserException)
                        and getattr(retry_error, "llm_output", None)
                        else fixed_text
                    )
                    final_error = retry_error
            # 超过最大重试次数，抛出原始异常
            raise final_error

    def parse(self, text: str) -> T:
        """直接委托给基础解析器。"""
        return self._base_parser.parse(text)

