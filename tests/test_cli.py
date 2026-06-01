"""task-09 CLI 主入口单元测试。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from harness.cli.main import app, _check_api_key


runner = CliRunner()


@pytest.fixture
def mock_settings_with_key() -> MagicMock:
    """有 API Key 的配置。"""
    s = MagicMock()
    s.qwen_api_key = "sk-test-12345678"
    s.qwen_base_url = "https://example.com/v1"
    s.model_name = "test-model"
    s.temperature = 0.7
    s.max_tokens = 4096
    return s


@pytest.fixture
def mock_settings_no_key() -> MagicMock:
    """无 API Key 的配置。"""
    s = MagicMock()
    s.qwen_api_key = ""
    return s


class TestCheckApiKey:
    """API Key 检查测试。"""

    def test_valid_key_returns_true(
        self,
        mock_settings_with_key: MagicMock,
    ) -> None:
        """有效 Key 返回 True。"""
        assert _check_api_key(mock_settings_with_key) is True

    def test_empty_key_returns_false(
        self,
        mock_settings_no_key: MagicMock,
    ) -> None:
        """空 Key 返回 False。"""
        assert _check_api_key(mock_settings_no_key) is False


class TestInitCommandNoKey:
    """init 命令 - 无 API Key 场景。"""

    @patch("harness.cli.main.Settings")
    def test_exits_when_no_api_key(
        self,
        mock_settings_cls: MagicMock,
        mock_settings_no_key: MagicMock,
    ) -> None:
        """无 API Key 时退出码为 1。"""
        mock_settings_cls.return_value = (
            mock_settings_no_key
        )
        result = runner.invoke(app, [])
        assert result.exit_code == 1


class TestInitCommandWithKey:
    """init 命令 - 有 API Key 的完整流程。"""

    @patch("harness.cli.main._phase_save")
    @patch("harness.cli.main._phase_plan")
    @patch("harness.cli.main._phase_agents")
    @patch("harness.cli.main._phase_conversation")
    @patch("harness.cli.main.QwenClient")
    @patch("harness.cli.main.Settings")
    def test_full_flow_success(
        self,
        mock_settings_cls: MagicMock,
        mock_client_cls: MagicMock,
        mock_conversation: MagicMock,
        mock_agents: MagicMock,
        mock_plan: MagicMock,
        mock_save: MagicMock,
        mock_settings_with_key: MagicMock,
    ) -> None:
        """完整流程成功。"""
        mock_settings_cls.return_value = (
            mock_settings_with_key
        )
        mock_conversation.return_value = "对话摘要"
        mock_agents.return_value = "# AGENTS.md 内容"
        mock_plan_inst = MagicMock()
        mock_plan.return_value = (
            MagicMock(),
            mock_plan_inst,
        )
        mock_save.return_value = None

        result = runner.invoke(app, [])
        assert result.exit_code == 0

        mock_conversation.assert_called_once()
        mock_agents.assert_called_once()
        mock_plan.assert_called_once()
        mock_save.assert_called_once()

    @patch("harness.cli.main._phase_conversation")
    @patch("harness.cli.main.QwenClient")
    @patch("harness.cli.main.Settings")
    def test_quit_during_conversation(
        self,
        mock_settings_cls: MagicMock,
        mock_client_cls: MagicMock,
        mock_conversation: MagicMock,
        mock_settings_with_key: MagicMock,
    ) -> None:
        """对话阶段退出。"""
        mock_settings_cls.return_value = (
            mock_settings_with_key
        )
        mock_conversation.return_value = None

        result = runner.invoke(app, [])
        assert result.exit_code == 0

    @patch("harness.cli.main._phase_agents")
    @patch("harness.cli.main._phase_conversation")
    @patch("harness.cli.main.QwenClient")
    @patch("harness.cli.main.Settings")
    def test_quit_during_agents(
        self,
        mock_settings_cls: MagicMock,
        mock_client_cls: MagicMock,
        mock_conversation: MagicMock,
        mock_agents: MagicMock,
        mock_settings_with_key: MagicMock,
    ) -> None:
        """AGENTS.md 阶段退出。"""
        mock_settings_cls.return_value = (
            mock_settings_with_key
        )
        mock_conversation.return_value = "摘要"
        mock_agents.return_value = None

        result = runner.invoke(app, [])
        assert result.exit_code == 0

    @patch("harness.cli.main._phase_plan")
    @patch("harness.cli.main._phase_agents")
    @patch("harness.cli.main._phase_conversation")
    @patch("harness.cli.main.QwenClient")
    @patch("harness.cli.main.Settings")
    def test_quit_during_plan(
        self,
        mock_settings_cls: MagicMock,
        mock_client_cls: MagicMock,
        mock_conversation: MagicMock,
        mock_agents: MagicMock,
        mock_plan: MagicMock,
        mock_settings_with_key: MagicMock,
    ) -> None:
        """计划阶段退出。"""
        mock_settings_cls.return_value = (
            mock_settings_with_key
        )
        mock_conversation.return_value = "摘要"
        mock_agents.return_value = "# AGENTS.md"
        mock_plan.return_value = (None, None)

        result = runner.invoke(app, [])
        assert result.exit_code == 0

    @patch("harness.cli.main.Settings")
    def test_custom_output_dir(
        self,
        mock_settings_cls: MagicMock,
        mock_settings_no_key: MagicMock,
    ) -> None:
        """自定义输出目录参数传递。"""
        mock_settings_cls.return_value = (
            mock_settings_no_key
        )
        result = runner.invoke(
            app, ["-o", "/tmp/test"]
        )
        # 无 Key 时退出
        assert result.exit_code == 1


class TestPhaseFunctions:
    """各阶段函数单元测试。"""

    @patch("harness.cli.main.ConversationManager")
    @patch("harness.cli.main.typer.prompt")
    def test_conversation_quit(
        self,
        mock_prompt: MagicMock,
        mock_cm_cls: MagicMock,
    ) -> None:
        """对话阶段 /quit 返回 None。"""
        mock_cm = MagicMock()
        mock_cm_cls.return_value = mock_cm
        mock_cm.process_input.return_value = "已退出对话。"
        mock_cm.should_quit = True
        mock_cm.should_generate = False
        mock_cm.is_collection_complete.return_value = False
        mock_prompt.side_effect = ["/quit"]

        from harness.cli.main import _phase_conversation

        result = _phase_conversation(MagicMock())
        assert result is None

    @patch("harness.cli.main.ConversationManager")
    @patch("harness.cli.main.typer.prompt")
    def test_conversation_completes(
        self,
        mock_prompt: MagicMock,
        mock_cm_cls: MagicMock,
    ) -> None:
        """对话完成后返回摘要。"""
        mock_cm = MagicMock()
        mock_cm_cls.return_value = mock_cm
        mock_cm.process_input.return_value = "AI 回复"
        mock_cm.should_quit = False
        mock_cm.should_generate = True
        mock_cm.is_collection_complete.return_value = True
        mock_cm.get_conversation_summary.return_value = (
            "对话摘要内容"
        )
        mock_prompt.side_effect = ["你好"]

        from harness.cli.main import _phase_conversation

        result = _phase_conversation(MagicMock())
        assert result == "对话摘要内容"


class TestModuleExports:
    """模块导出验证。"""

    def test_import_app(self) -> None:
        """app 可从 cli.main 导入。"""
        from harness.cli.main import app as a

        assert a is not None

    def test_import_cli_module(self) -> None:
        """cli 模块可导入。"""
        import harness.cli.main

        assert hasattr(harness.cli.main, "init")

    def test_import_phase_functions(self) -> None:
        """阶段函数可导入。"""
        from harness.cli.main import (
            _phase_conversation,
            _phase_agents,
            _phase_plan,
            _phase_save,
        )

        assert callable(_phase_conversation)
        assert callable(_phase_agents)
        assert callable(_phase_plan)
        assert callable(_phase_save)
