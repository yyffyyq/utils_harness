"""task-05 AGENTS.md 生成器单元测试。"""

from unittest.mock import MagicMock, patch

import pytest

from harness.core.exceptions import (
    GeneratorError,
    ValidationError,
)
from harness.core.generator import AgentsGenerator


SAMPLE_AGENTS_MD = """\
# MyProject - 测试项目

## 项目背景

这是一个 CLI 工具项目。

## 技术栈

| 类别 | 技术选型 | 说明 |
| ---- | -------- | ---- |
| 语言 | Python 3.10+ | 主开发语言 |

## 代码规范

遵循 PEP 8 规范。
"""


@pytest.fixture
def mock_client() -> MagicMock:
    """创建 mock QwenClient。"""
    client = MagicMock()
    client.chat.return_value = SAMPLE_AGENTS_MD
    return client


@pytest.fixture
def generator(mock_client: MagicMock) -> AgentsGenerator:
    """创建测试用生成器。"""
    return AgentsGenerator(client=mock_client)


class TestGenerate:
    """generate() 方法测试。"""

    def test_returns_markdown_content(
        self,
        generator: AgentsGenerator,
        mock_client: MagicMock,
    ) -> None:
        """正常返回 Markdown 内容。"""
        result = generator.generate("项目对话摘要")
        assert "项目背景" in result
        assert "技术栈" in result
        assert "代码规范" in result

    def test_calls_llm_with_correct_messages(
        self,
        generator: AgentsGenerator,
        mock_client: MagicMock,
    ) -> None:
        """使用正确的消息列表调用 LLM。"""
        generator.generate("对话摘要")
        mock_client.chat.assert_called_once()
        messages = mock_client.chat.call_args[0][0]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "对话摘要" in messages[1]["content"]

    def test_handles_dict_response(
        self,
        generator: AgentsGenerator,
        mock_client: MagicMock,
    ) -> None:
        """处理 thinking 模式的 dict 响应。"""
        mock_client.chat.return_value = {
            "reasoning": "分析中...",
            "content": SAMPLE_AGENTS_MD,
        }
        result = generator.generate("摘要")
        assert "项目背景" in result

    def test_extracts_markdown_from_code_block(
        self,
        generator: AgentsGenerator,
        mock_client: MagicMock,
    ) -> None:
        """从 ```markdown ... ``` 包裹中提取内容。"""
        wrapped = f"```markdown\n{SAMPLE_AGENTS_MD}\n```"
        mock_client.chat.return_value = wrapped
        result = generator.generate("摘要")
        assert result.startswith("# MyProject")
        assert "```" not in result

    def test_extracts_from_plain_code_block(
        self,
        generator: AgentsGenerator,
        mock_client: MagicMock,
    ) -> None:
        """从 ``` ... ``` 包裹中提取内容。"""
        wrapped = f"```\n{SAMPLE_AGENTS_MD}\n```"
        mock_client.chat.return_value = wrapped
        result = generator.generate("摘要")
        assert result.startswith("# MyProject")


class TestRegenerate:
    """regenerate() 方法测试。"""

    def test_passes_feedback_and_content(
        self,
        generator: AgentsGenerator,
        mock_client: MagicMock,
    ) -> None:
        """将用户反馈与当前内容传给 LLM。"""
        updated = SAMPLE_AGENTS_MD.replace(
            "测试项目", "修改后项目"
        )
        mock_client.chat.return_value = updated
        result = generator.regenerate(
            "修改项目名称",
            SAMPLE_AGENTS_MD,
        )
        mock_client.chat.assert_called_once()
        messages = mock_client.chat.call_args[0][0]
        user_content = messages[1]["content"]
        assert "修改项目名称" in user_content
        assert SAMPLE_AGENTS_MD in user_content

    def test_returns_modified_content(
        self,
        generator: AgentsGenerator,
        mock_client: MagicMock,
    ) -> None:
        """返回修改后的内容。"""
        updated = "# Updated\n\n## 项目背景\n## 技术栈\n## 代码规范"
        mock_client.chat.return_value = updated
        result = generator.regenerate("加标题", "旧内容")
        assert "Updated" in result


class TestValidate:
    """validate() 方法测试。"""

    def test_all_sections_present(
        self, generator: AgentsGenerator
    ) -> None:
        """包含所有章节时返回空列表。"""
        missing = generator.validate(SAMPLE_AGENTS_MD)
        assert missing == []

    def test_missing_section(
        self, generator: AgentsGenerator
    ) -> None:
        """缺少章节时返回缺失列表。"""
        content = "# 项目\n\n## 项目背景\n\n描述"
        missing = generator.validate(content)
        assert "技术栈" in missing
        assert "代码规范" in missing

    def test_empty_content(
        self, generator: AgentsGenerator
    ) -> None:
        """空内容时所有章节缺失。"""
        missing = generator.validate("")
        assert len(missing) == 3


class TestValidateOrRaise:
    """validate_or_raise() 方法测试。"""

    def test_valid_content_no_error(
        self, generator: AgentsGenerator
    ) -> None:
        """有效内容不抛异常。"""
        generator.validate_or_raise(SAMPLE_AGENTS_MD)

    def test_invalid_content_raises(
        self, generator: AgentsGenerator
    ) -> None:
        """缺少章节时抛出 ValidationError。"""
        with pytest.raises(ValidationError, match="缺少"):
            generator.validate_or_raise("# 仅标题")


class TestExtractMarkdown:
    """_extract_markdown() 静态方法测试。"""

    def test_plain_text_unchanged(self) -> None:
        """纯文本原样返回。"""
        text = "# Hello\n\nWorld"
        assert AgentsGenerator._extract_markdown(text) == text

    def test_strips_code_block_markdown(self) -> None:
        """去除 ```markdown 包裹。"""
        text = "```markdown\n# Content\n```"
        assert (
            AgentsGenerator._extract_markdown(text)
            == "# Content"
        )

    def test_strips_code_block_md(self) -> None:
        """去除 ```md 包裹。"""
        text = "```md\n# Content\n```"
        assert (
            AgentsGenerator._extract_markdown(text)
            == "# Content"
        )

    def test_strips_plain_code_block(self) -> None:
        """去除 ``` 包裹。"""
        text = "```\n# Content\n```"
        assert (
            AgentsGenerator._extract_markdown(text)
            == "# Content"
        )

    def test_strips_whitespace(self) -> None:
        """去除首尾空白。"""
        text = "  \n# Hello\n  "
        assert (
            AgentsGenerator._extract_markdown(text)
            == "# Hello"
        )


class TestRenderPreview:
    """render_preview() 渲染测试。"""

    @patch("harness.core.generator.console")
    def test_calls_console_print(
        self,
        mock_console: MagicMock,
        generator: AgentsGenerator,
    ) -> None:
        """render_preview 调用 console.print。"""
        generator.render_preview(SAMPLE_AGENTS_MD)
        mock_console.print.assert_called_once()


class TestModuleExports:
    """模块导出验证。"""

    def test_import_from_core(self) -> None:
        """AgentsGenerator 可从 harness.core 导入。"""
        from harness.core import AgentsGenerator as AG

        assert AG is AgentsGenerator

    def test_import_exceptions(self) -> None:
        """生成相关异常可导入。"""
        from harness.core.exceptions import (
            GeneratorError,
            ValidationError,
        )

        assert issubclass(ValidationError, GeneratorError)
