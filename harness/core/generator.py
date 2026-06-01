"""AGENTS.md 内容生成器模块。"""

import re

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from harness.core.exceptions import (
    GeneratorError,
    ValidationError,
)
from harness.llm.client import QwenClient
from harness.llm.prompts import (
    build_agents_generation_prompt,
)

console = Console()

# 生成内容中必须包含的章节关键词
_REQUIRED_SECTIONS: list[str] = [
    "项目背景",
    "技术栈",
    "代码规范",
]


class AgentsGenerator:
    """AGENTS.md 内容生成器。

    基于对话摘要调用 LLM 生成 Markdown 格式的 AGENTS.md，
    支持内容校验、用户反馈后重新生成与完全重新生成。

    Attributes:
        client: Qwen3 LLM 客户端实例。
    """

    def __init__(self, client: QwenClient) -> None:
        """初始化生成器。

        Args:
            client: Qwen3 客户端实例。
        """
        self.client = client

    def generate(self, conversation_summary: str) -> str:
        """根据对话摘要生成 AGENTS.md 内容。

        Args:
            conversation_summary: 对话摘要文本。

        Returns:
            生成的 AGENTS.md Markdown 内容。

        Raises:
            GeneratorError: LLM 调用失败或响应异常。
        """
        messages = build_agents_generation_prompt(
            conversation_summary
        )
        response = self.client.chat(messages)
        if isinstance(response, dict):
            response = response.get("content", "")
        content = self._extract_markdown(response)
        return content

    def regenerate(
        self,
        feedback: str,
        current_content: str,
    ) -> str:
        """根据用户反馈修改 AGENTS.md。

        将用户反馈与当前内容一起传给 LLM，获取修改后的版本。

        Args:
            feedback: 用户的修改意见。
            current_content: 当前 AGENTS.md 内容。

        Returns:
            修改后的 AGENTS.md 内容。

        Raises:
            GeneratorError: LLM 调用失败或响应异常。
        """
        user_prompt = (
            "请根据以下修改意见调整 AGENTS.md 内容。\n\n"
            f"修改意见：\n{feedback}\n\n"
            f"当前 AGENTS.md 内容：\n{current_content}\n\n"
            "请输出完整的修改后的 AGENTS.md（Markdown 格式）。"
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一名专业的技术文档编辑，"
                    "擅长根据反馈修改 Markdown 文档。"
                ),
            },
            {"role": "user", "content": user_prompt},
        ]
        response = self.client.chat(messages)
        if isinstance(response, dict):
            response = response.get("content", "")
        content = self._extract_markdown(response)
        return content

    def validate(self, content: str) -> list[str]:
        """校验生成的内容是否包含必要章节。

        Args:
            content: AGENTS.md Markdown 内容。

        Returns:
            缺失的章节名称列表，全部存在时返回空列表。
        """
        missing = [
            section
            for section in _REQUIRED_SECTIONS
            if section not in content
        ]
        return missing

    def validate_or_raise(self, content: str) -> None:
        """校验内容，缺失章节时抛出 ValidationError。

        Args:
            content: AGENTS.md Markdown 内容。

        Raises:
            ValidationError: 缺少必要章节。
        """
        missing = self.validate(content)
        if missing:
            raise ValidationError(
                f"生成的内容缺少以下章节: "
                f"{', '.join(missing)}"
            )

    def render_preview(self, content: str) -> None:
        """使用 Rich 在终端渲染 AGENTS.md 预览。

        Args:
            content: AGENTS.md Markdown 内容。
        """
        md = Markdown(content)
        console.print(
            Panel(
                md,
                title="AGENTS.md 预览",
                border_style="blue",
            )
        )

    @staticmethod
    def _extract_markdown(text: str) -> str:
        """从 LLM 响应中提取纯 Markdown 内容。

        去除可能的 ```markdown ... ``` 代码块包裹。

        Args:
            text: LLM 原始响应文本。

        Returns:
            提取后的 Markdown 内容。
        """
        # 匹配 ```markdown\n...\n``` 或 ```\n...\n```
        pattern = re.compile(
            r"^```(?:markdown|md)?\s*\n(.*?)\n```\s*$",
            re.DOTALL,
        )
        match = pattern.match(text.strip())
        if match:
            return match.group(1).strip()
        return text.strip()
