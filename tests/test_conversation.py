"""task-04 多轮对话管理器单元测试。"""

from unittest.mock import MagicMock, patch

import pytest

from harness.core.conversation import (
    CMD_GENERATE,
    CMD_HELP,
    CMD_QUIT,
    ConversationManager,
    ConversationPhase,
)
from harness.core.exceptions import (
    ConversationError,
    ConversationMaxRoundsError,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """创建 mock QwenClient。"""
    client = MagicMock()
    client.chat.return_value = "你好！请介绍一下你的项目名称和背景。"
    return client


@pytest.fixture
def manager(mock_client: MagicMock) -> ConversationManager:
    """创建测试用对话管理器（最大 3 轮）。"""
    return ConversationManager(client=mock_client, max_rounds=3)


class TestConversationPhase:
    """ConversationPhase 枚举测试。"""

    def test_phase_values(self) -> None:
        """所有阶段值正确。"""
        assert ConversationPhase.COLLECTING.value == "collecting"
        assert ConversationPhase.REVIEWING.value == "reviewing"
        assert ConversationPhase.PLANNING.value == "planning"
        assert ConversationPhase.PLAN_REVIEWING.value == "plan_review"
        assert ConversationPhase.COMPLETED.value == "completed"

    def test_phase_count(self) -> None:
        """枚举共 5 个阶段。"""
        assert len(ConversationPhase) == 5


class TestConversationManagerInit:
    """ConversationManager 初始化测试。"""

    def test_initial_state(self, manager: ConversationManager) -> None:
        """初始状态为 COLLECTING，历史为空。"""
        assert manager.phase == ConversationPhase.COLLECTING
        assert manager.history == []
        assert manager.round_count == 0
        assert manager.max_rounds == 3
        assert not manager.should_generate
        assert not manager.should_quit

    def test_default_max_rounds(self, mock_client: MagicMock) -> None:
        """默认最大轮次为 15。"""
        mgr = ConversationManager(client=mock_client)
        assert mgr.max_rounds == 15


class TestProcessInput:
    """process_input() 方法测试。"""

    def test_normal_input_returns_ai_response(
        self,
        manager: ConversationManager,
        mock_client: MagicMock,
    ) -> None:
        """普通输入返回 AI 响应文本。"""
        mock_client.chat.return_value = "收到！请描述技术栈。"
        result = manager.process_input("我的项目是一个 CLI 工具")
        assert result == "收到！请描述技术栈。"

    def test_normal_input_updates_history(
        self,
        manager: ConversationManager,
        mock_client: MagicMock,
    ) -> None:
        """普通输入后历史记录正确更新。"""
        mock_client.chat.return_value = "AI 响应"
        manager.process_input("用户输入")
        assert len(manager.history) == 2
        assert manager.history[0] == {
            "role": "user",
            "content": "用户输入",
        }
        assert manager.history[1] == {
            "role": "assistant",
            "content": "AI 响应",
        }

    def test_normal_input_increments_round(
        self,
        manager: ConversationManager,
        mock_client: MagicMock,
    ) -> None:
        """普通输入后轮次计数加 1。"""
        mock_client.chat.return_value = "ok"
        manager.process_input("输入 1")
        assert manager.round_count == 1

    def test_multi_round_context_coherent(
        self,
        manager: ConversationManager,
        mock_client: MagicMock,
    ) -> None:
        """多轮对话上下文连贯，近期对话包含前一轮内容。"""
        # 使用 return_value 避免记忆模块额外调用导致 StopIteration
        mock_client.chat.return_value = "AI 响应"

        manager.process_input("输入 1")
        manager.process_input("输入 2")

        # 找到包含 "输入 2" 的主对话调用（排除事实提取调用）
        main_calls = [
            c for c in mock_client.chat.call_args_list
            if any(
                m.get("content") == "输入 2"
                for m in c[0][0]
                if isinstance(m, dict)
            )
        ]
        assert len(main_calls) >= 1
        messages = main_calls[-1][0][0]
        # 验证近期对话中包含第一轮内容
        contents = [m.get("content", "") for m in messages]
        assert "输入 1" in contents
        assert "输入 2" in contents

    def test_max_rounds_raises(
        self,
        manager: ConversationManager,
        mock_client: MagicMock,
    ) -> None:
        """超过最大轮次后抛出 ConversationMaxRoundsError。"""
        mock_client.chat.return_value = "ok"
        manager.process_input("1")
        manager.process_input("2")
        manager.process_input("3")

        with pytest.raises(ConversationMaxRoundsError, match="上限"):
            manager.process_input("4")

    def test_handles_dict_response_from_thinking(
        self,
        manager: ConversationManager,
        mock_client: MagicMock,
    ) -> None:
        """当 client.chat 返回 dict（thinking 模式）时提取 content。"""
        mock_client.chat.return_value = {
            "reasoning": "思考过程",
            "content": "实际回答",
        }
        result = manager.process_input("测试")
        assert result == "实际回答"


class TestCommands:
    """/generate、/quit、/help 命令测试。"""

    def test_quit_command(
        self, manager: ConversationManager
    ) -> None:
        """/quit 设置 should_quit 并切换到 COMPLETED 阶段。"""
        result = manager.process_input("/quit")
        assert manager.should_quit
        assert manager.phase == ConversationPhase.COMPLETED
        assert "退出" in result

    def test_quit_command_case_sensitive(
        self,
        manager: ConversationManager,
        mock_client: MagicMock,
    ) -> None:
        """/quit 前后有空格时也能识别（strip 处理）。"""
        mock_client.chat.return_value = "ok"
        # 带空格
        result = manager.process_input("  /quit  ")
        assert manager.should_quit
        assert "退出" in result

    def test_generate_command(
        self, manager: ConversationManager
    ) -> None:
        """/generate 设置 should_generate 并切换到 REVIEWING。"""
        result = manager.process_input("/generate")
        assert manager.should_generate
        assert manager.phase == ConversationPhase.REVIEWING
        assert "生成" in result

    def test_help_command(
        self, manager: ConversationManager
    ) -> None:
        """/help 返回帮助信息，不增加轮次。"""
        result = manager.process_input("/help")
        assert "/generate" in result
        assert "/quit" in result
        assert manager.round_count == 0

    def test_commands_dont_add_to_history(
        self, manager: ConversationManager
    ) -> None:
        """命令输入不追加到对话历史。"""
        manager.process_input("/help")
        manager.process_input("/quit")
        assert manager.history == []

    def test_generate_does_not_call_llm(
        self,
        manager: ConversationManager,
        mock_client: MagicMock,
    ) -> None:
        """/generate 不调用 LLM。"""
        manager.process_input("/generate")
        mock_client.chat.assert_not_called()


class TestCompletionDetection:
    """AI 响应中的完成信号检测测试。"""

    def test_detects_completion_signal(
        self,
        manager: ConversationManager,
        mock_client: MagicMock,
    ) -> None:
        """AI 响应包含'可以生成'时自动设置 should_generate。"""
        mock_client.chat.return_value = "信息已经足够了，可以生成 AGENTS.md 了。"
        manager.process_input("项目信息完毕")
        assert manager.should_generate
        assert manager.phase == ConversationPhase.REVIEWING

    def test_no_completion_signal(
        self,
        manager: ConversationManager,
        mock_client: MagicMock,
    ) -> None:
        """AI 响应无完成关键词时保持 COLLECTING。"""
        mock_client.chat.return_value = "请继续描述你的测试规范。"
        manager.process_input("用 pytest")
        assert not manager.should_generate
        assert manager.phase == ConversationPhase.COLLECTING


class TestIsCollectionComplete:
    """is_collection_complete() 方法测试。"""

    def test_false_initially(self, manager: ConversationManager) -> None:
        """初始状态返回 False。"""
        assert not manager.is_collection_complete()

    def test_true_after_generate_command(
        self, manager: ConversationManager
    ) -> None:
        """/generate 后返回 True。"""
        manager.process_input("/generate")
        assert manager.is_collection_complete()

    def test_true_at_max_rounds(
        self,
        manager: ConversationManager,
        mock_client: MagicMock,
    ) -> None:
        """达到最大轮次后返回 True。"""
        mock_client.chat.return_value = "ok"
        manager.process_input("1")
        manager.process_input("2")
        manager.process_input("3")
        assert manager.is_collection_complete()


class TestGetConversationSummary:
    """get_conversation_summary() 方法测试。"""

    def test_raises_when_empty(self, manager: ConversationManager) -> None:
        """历史为空时抛出 ConversationError。"""
        with pytest.raises(ConversationError, match="为空"):
            manager.get_conversation_summary()

    def test_returns_formatted_summary(
        self,
        manager: ConversationManager,
        mock_client: MagicMock,
    ) -> None:
        """返回包含用户和 AI 内容的格式化摘要。"""
        mock_client.chat.return_value = "AI 回答"
        manager.process_input("用户问题")

        summary = manager.get_conversation_summary()
        assert "[用户]" in summary
        assert "[AI]" in summary
        assert "用户问题" in summary
        assert "AI 回答" in summary

    def test_multi_round_summary(
        self,
        manager: ConversationManager,
        mock_client: MagicMock,
    ) -> None:
        """多轮对话摘要包含所有内容。"""
        mock_client.chat.return_value = "AI 回答"
        manager.process_input("问题 1")
        manager.process_input("问题 2")

        summary = manager.get_conversation_summary()
        assert "问题 1" in summary
        assert "问题 2" in summary
        assert "AI 回答" in summary


class TestRenderMethods:
    """render_response() / render_status() 渲染测试。"""

    @patch("harness.core.conversation.console")
    def test_render_response_calls_console(
        self,
        mock_console: MagicMock,
        manager: ConversationManager,
    ) -> None:
        """render_response 调用 console.print。"""
        manager.render_response("**Hello**")
        mock_console.print.assert_called_once()

    @patch("harness.core.conversation.console")
    def test_render_status_shows_phase(
        self,
        mock_console: MagicMock,
        manager: ConversationManager,
    ) -> None:
        """render_status 显示当前阶段和轮次。"""
        manager.render_status()
        call_args = mock_console.print.call_args[0][0]
        assert "collecting" in call_args
        assert "0/3" in call_args


class TestModuleExports:
    """验证 core 模块导出完整性。"""

    def test_import_from_core(self) -> None:
        """ConversationManager 和 ConversationPhase 可从 harness.core 导入。"""
        from harness.core import ConversationManager as CM
        from harness.core import ConversationPhase as CP

        assert CM is ConversationManager
        assert CP is ConversationPhase

    def test_import_exceptions(self) -> None:
        """对话异常类可从 core.exceptions 导入。"""
        from harness.core.exceptions import (
            ConversationError,
            ConversationMaxRoundsError,
        )

        assert issubclass(ConversationMaxRoundsError, ConversationError)
