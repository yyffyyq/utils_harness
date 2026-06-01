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


class TestPhaseAgents:
    """_phase_agents 阶段测试。"""

    @patch("harness.cli.main.AgentsGenerator")
    @patch("harness.cli.main.typer.prompt")
    def test_confirm_save(
        self,
        mock_prompt: MagicMock,
        mock_gen_cls: MagicMock,
    ) -> None:
        """选择 y 保存返回内容。"""
        mock_gen = MagicMock()
        mock_gen_cls.return_value = mock_gen
        mock_gen.generate.return_value = "# AGENTS.md"
        mock_gen.validate.return_value = []
        mock_prompt.return_value = "y"

        from harness.cli.main import _phase_agents

        result = _phase_agents(MagicMock(), "摘要")
        assert result == "# AGENTS.md"

    @patch("harness.cli.main.AgentsGenerator")
    @patch("harness.cli.main.typer.prompt")
    def test_quit_returns_none(
        self,
        mock_prompt: MagicMock,
        mock_gen_cls: MagicMock,
    ) -> None:
        """选择 q 退出返回 None。"""
        mock_gen = MagicMock()
        mock_gen_cls.return_value = mock_gen
        mock_gen.generate.return_value = "# AGENTS.md"
        mock_gen.validate.return_value = []
        mock_prompt.return_value = "q"

        from harness.cli.main import _phase_agents

        result = _phase_agents(MagicMock(), "摘要")
        assert result is None

    @patch("harness.cli.main.AgentsGenerator")
    @patch("harness.cli.main.typer.prompt")
    def test_edit_then_save(
        self,
        mock_prompt: MagicMock,
        mock_gen_cls: MagicMock,
    ) -> None:
        """选择 e 修改后 y 保存。"""
        mock_gen = MagicMock()
        mock_gen_cls.return_value = mock_gen
        mock_gen.generate.return_value = "# V1"
        mock_gen.regenerate.return_value = "# V2"
        mock_gen.validate.return_value = []
        mock_prompt.side_effect = ["e", "修改意见", "y"]

        from harness.cli.main import _phase_agents

        result = _phase_agents(MagicMock(), "摘要")
        assert result == "# V2"

    @patch("harness.cli.main.AgentsGenerator")
    @patch("harness.cli.main.typer.prompt")
    def test_generate_error_returns_none(
        self,
        mock_prompt: MagicMock,
        mock_gen_cls: MagicMock,
    ) -> None:
        """生成失败返回 None。"""
        from harness.core.exceptions import GeneratorError

        mock_gen = MagicMock()
        mock_gen_cls.return_value = mock_gen
        mock_gen.generate.side_effect = GeneratorError(
            "LLM 失败"
        )

        from harness.cli.main import _phase_agents

        result = _phase_agents(MagicMock(), "摘要")
        assert result is None

    @patch("harness.cli.main.AgentsGenerator")
    @patch("harness.cli.main.typer.prompt")
    def test_missing_sections_warning(
        self,
        mock_prompt: MagicMock,
        mock_gen_cls: MagicMock,
    ) -> None:
        """缺失章节显示警告但仍可保存。"""
        mock_gen = MagicMock()
        mock_gen_cls.return_value = mock_gen
        mock_gen.generate.return_value = "# 内容"
        mock_gen.validate.return_value = ["技术栈"]
        mock_prompt.return_value = "y"

        from harness.cli.main import _phase_agents

        result = _phase_agents(MagicMock(), "摘要")
        assert result == "# 内容"


class TestPhasePlan:
    """_phase_plan 阶段测试。"""

    @patch("harness.cli.main.PlanGenerator")
    @patch("harness.cli.main.typer.prompt")
    def test_confirm_plan(
        self,
        mock_prompt: MagicMock,
        mock_planner_cls: MagicMock,
    ) -> None:
        """选择 y 确认计划。"""
        mock_planner = MagicMock()
        mock_planner_cls.return_value = mock_planner
        mock_plan = MagicMock()
        mock_planner.generate.return_value = mock_plan
        mock_prompt.return_value = "y"

        from harness.cli.main import _phase_plan

        plan, planner = _phase_plan(
            MagicMock(), "# AGENTS"
        )
        assert plan is mock_plan
        assert planner is mock_planner

    @patch("harness.cli.main.PlanGenerator")
    @patch("harness.cli.main.typer.prompt")
    def test_quit_returns_none(
        self,
        mock_prompt: MagicMock,
        mock_planner_cls: MagicMock,
    ) -> None:
        """选择 q 退出返回 (None, None)。"""
        mock_planner = MagicMock()
        mock_planner_cls.return_value = mock_planner
        mock_planner.generate.return_value = MagicMock()
        mock_prompt.return_value = "q"

        from harness.cli.main import _phase_plan

        plan, planner = _phase_plan(
            MagicMock(), "# AGENTS"
        )
        assert plan is None
        assert planner is None

    @patch("harness.cli.main.PlanGenerator")
    @patch("harness.cli.main.typer.prompt")
    def test_plan_error_returns_none(
        self,
        mock_prompt: MagicMock,
        mock_planner_cls: MagicMock,
    ) -> None:
        """计划生成失败返回 (None, None)。"""
        from harness.core.exceptions import PlanError

        mock_planner = MagicMock()
        mock_planner_cls.return_value = mock_planner
        mock_planner.generate.side_effect = PlanError(
            "解析失败"
        )

        from harness.cli.main import _phase_plan

        plan, planner = _phase_plan(
            MagicMock(), "# AGENTS"
        )
        assert plan is None
        assert planner is None


class TestPhaseSave:
    """_phase_save 阶段测试。"""

    @patch("harness.cli.main.FileOps")
    def test_save_success(
        self,
        mock_fileops: MagicMock,
        tmp_path: Path,
    ) -> None:
        """成功保存文件。"""
        mock_planner = MagicMock()
        mock_planner.save_plan.return_value = [
            tmp_path / "plan" / "README.md"
        ]
        mock_plan = MagicMock()

        from harness.cli.main import _phase_save

        _phase_save(
            str(tmp_path),
            "# AGENTS.md",
            mock_plan,
            mock_planner,
        )
        mock_fileops.write_file.assert_called_once()
        mock_planner.save_plan.assert_called_once()

    @patch("harness.cli.main.FileOps")
    def test_save_failure_prints_content(
        self,
        mock_fileops: MagicMock,
        tmp_path: Path,
    ) -> None:
        """写入失败时打印内容到终端。"""
        mock_fileops.write_file.side_effect = (
            PermissionError("无权限")
        )

        from harness.cli.main import _phase_save

        # 不应抛出异常
        _phase_save(
            str(tmp_path),
            "# AGENTS 内容",
            MagicMock(),
            MagicMock(),
        )


class TestPhaseConversationExtra:
    """_phase_conversation 额外测试。"""

    @patch("harness.cli.main.ConversationManager")
    @patch("harness.cli.main.typer.prompt")
    def test_empty_input_skipped(
        self,
        mock_prompt: MagicMock,
        mock_cm_cls: MagicMock,
    ) -> None:
        """空输入被跳过。"""
        mock_cm = MagicMock()
        mock_cm_cls.return_value = mock_cm
        mock_cm.should_quit = True
        mock_cm.is_collection_complete.return_value = False
        mock_cm.process_input.return_value = "退出"
        mock_prompt.side_effect = ["", "/quit"]

        from harness.cli.main import _phase_conversation

        result = _phase_conversation(MagicMock())
        assert result is None

    @patch("harness.cli.main.ConversationManager")
    @patch("harness.cli.main.typer.prompt")
    def test_keyboard_interrupt(
        self,
        mock_prompt: MagicMock,
        mock_cm_cls: MagicMock,
    ) -> None:
        """Ctrl+C 返回 None。"""
        mock_cm_cls.return_value = MagicMock()
        mock_prompt.side_effect = KeyboardInterrupt

        from harness.cli.main import _phase_conversation

        result = _phase_conversation(MagicMock())
        assert result is None

    @patch("harness.cli.main.ConversationManager")
    @patch("harness.cli.main.typer.prompt")
    def test_max_rounds_returns_summary(
        self,
        mock_prompt: MagicMock,
        mock_cm_cls: MagicMock,
    ) -> None:
        """达到最大轮次返回摘要。"""
        from harness.core.exceptions import (
            ConversationMaxRoundsError,
        )

        mock_cm = MagicMock()
        mock_cm_cls.return_value = mock_cm
        mock_cm.process_input.side_effect = (
            ConversationMaxRoundsError("轮次已满")
        )
        mock_cm.get_conversation_summary.return_value = (
            "轮次摘要"
        )
        mock_prompt.return_value = "你好"

        from harness.cli.main import _phase_conversation

        result = _phase_conversation(MagicMock())
        assert result == "轮次摘要"
