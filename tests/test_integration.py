"""task-10 集成测试 - 验证模块间协作。"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harness.core.conversation import (
    ConversationManager,
    ConversationPhase,
)
from harness.core.generator import AgentsGenerator
from harness.core.planner import Plan, PlanGenerator, TaskItem
from harness.utils.file_ops import FileOps


class TestConversationToGenerator:
    """对话 → AGENTS.md 生成器集成。"""

    def test_summary_feeds_generator(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """对话摘要可直接传给 AgentsGenerator。"""
        cm = ConversationManager(mock_llm_client)
        mock_llm_client.chat.return_value = (
            "AI 回复：好的，信息已收集完毕。"
        )
        cm.process_input("我想做一个 CLI 工具")
        summary = cm.get_conversation_summary()

        gen = AgentsGenerator(mock_llm_client)
        mock_llm_client.chat.return_value = (
            "# AGENTS.md\n\n"
            "## 项目背景\n\nCLI 工具\n\n"
            "## 技术栈\n\nPython\n\n"
            "## 代码规范\n\nPEP 8\n"
        )
        content = gen.generate(summary)

        assert "项目背景" in content
        assert "技术栈" in content
        mock_llm_client.chat.assert_called()

    def test_generator_validates_after_conversation(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """生成器校验对话后的生成内容。"""
        gen = AgentsGenerator(mock_llm_client)
        mock_llm_client.chat.return_value = (
            "# AGENTS.md\n\n"
            "## 项目背景\n\n背景\n\n"
            "## 技术栈\n\nPython\n\n"
            "## 代码规范\n\nPEP 8\n"
        )
        content = gen.generate("摘要")
        missing = gen.validate(content)
        assert missing == []


class TestGeneratorToPlanner:
    """AGENTS.md → 计划生成器集成。"""

    def test_agents_md_feeds_planner(
        self,
        mock_llm_client: MagicMock,
        mock_plan_json: str,
    ) -> None:
        """AGENTS.md 内容可直接传给 PlanGenerator。"""
        agents_md = (
            "# TestProject\n\n"
            "## 项目背景\n\n测试项目\n\n"
            "## 技术栈\n\nPython\n\n"
            "## 代码规范\n\nPEP 8\n"
        )

        planner = PlanGenerator(mock_llm_client)
        mock_llm_client.chat.return_value = mock_plan_json
        plan = planner.generate(agents_md)

        assert isinstance(plan, Plan)
        assert len(plan.tasks) == 2
        assert plan.project_name == "TestProject"

    def test_plan_render_and_save(
        self,
        mock_llm_client: MagicMock,
        mock_plan_json: str,
        tmp_path: Path,
    ) -> None:
        """计划渲染后可保存到文件系统。"""
        planner = PlanGenerator(mock_llm_client)
        mock_llm_client.chat.return_value = mock_plan_json
        plan = planner.generate("内容")

        written = planner.save_plan(plan, tmp_path / "plan")
        assert len(written) >= 3

        readme = (tmp_path / "plan" / "README.md").read_text(
            encoding="utf-8"
        )
        assert "TestProject" in readme


class TestEndToEndMock:
    """端到端模拟流程（对话→生成→计划→保存）。"""

    def test_full_pipeline_mock(
        self,
        mock_llm_client: MagicMock,
        mock_plan_json: str,
        tmp_path: Path,
    ) -> None:
        """完整流水线 mock 测试。"""
        # 阶段一：对话
        cm = ConversationManager(mock_llm_client)
        mock_llm_client.chat.return_value = "AI: 收到"
        cm.process_input("我的项目是 CLI 工具")
        summary = cm.get_conversation_summary()
        assert len(summary) > 0

        # 阶段二：生成 AGENTS.md
        gen = AgentsGenerator(mock_llm_client)
        agents_md = (
            "# CLI 工具\n\n"
            "## 项目背景\n\nCLI 工具\n\n"
            "## 技术栈\n\nPython\n\n"
            "## 代码规范\n\nPEP 8\n"
        )
        mock_llm_client.chat.return_value = agents_md
        content = gen.generate(summary)
        assert gen.validate(content) == []

        # 阶段三：生成计划
        planner = PlanGenerator(mock_llm_client)
        mock_llm_client.chat.return_value = mock_plan_json
        plan = planner.generate(content)
        assert len(plan.tasks) > 0

        # 阶段四：保存
        FileOps.write_file(
            tmp_path / "doc" / "AGENTS.md", content
        )
        written = planner.save_plan(
            plan, tmp_path / "doc" / "plan"
        )

        # 验证文件
        assert (tmp_path / "doc" / "AGENTS.md").exists()
        assert (
            tmp_path / "doc" / "plan" / "README.md"
        ).exists()
        assert len(written) >= 3


class TestSharedFixtures:
    """验证 conftest.py 共享 fixtures。"""

    def test_mock_settings_fixture(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """mock_settings fixture 可用。"""
        assert mock_settings.qwen_api_key.startswith(
            "sk-"
        )

    def test_mock_llm_client_fixture(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """mock_llm_client fixture 可用。"""
        result = mock_llm_client.chat([])
        assert result == "AI 模拟响应"

    def test_mock_plan_json_fixture(
        self,
        mock_plan_json: str,
    ) -> None:
        """mock_plan_json fixture 是有效 JSON。"""
        data = json.loads(mock_plan_json)
        assert "tasks" in data
        assert len(data["tasks"]) == 2

    def test_sample_agents_md_fixture(
        self,
        sample_agents_md: str,
    ) -> None:
        """sample_agents_md fixture 包含必要章节。"""
        assert "项目背景" in sample_agents_md
        assert "技术栈" in sample_agents_md
        assert "代码规范" in sample_agents_md
