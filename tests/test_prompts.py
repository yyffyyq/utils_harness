"""task-03 Prompt 模板单元测试。"""

from harness.llm.prompts import (
    AGENTS_GENERATION_PROMPT,
    AGENTS_GENERATION_PROMPT_V1,
    CONVERSATION_SYSTEM_PROMPT,
    CONVERSATION_SYSTEM_PROMPT_V1,
    PLAN_GENERATION_PROMPT,
    PLAN_GENERATION_PROMPT_V1,
    build_agents_generation_prompt,
    build_conversation_prompt,
    build_plan_generation_prompt,
)


class TestPromptConstants:
    """验证 Prompt 常量定义与版本别名。"""

    def test_conversation_prompt_v1_not_empty(self) -> None:
        """CONVERSATION_SYSTEM_PROMPT_V1 内容不为空。"""
        assert CONVERSATION_SYSTEM_PROMPT_V1
        assert isinstance(CONVERSATION_SYSTEM_PROMPT_V1, str)

    def test_agents_generation_prompt_v1_not_empty(self) -> None:
        """AGENTS_GENERATION_PROMPT_V1 内容不为空。"""
        assert AGENTS_GENERATION_PROMPT_V1
        assert isinstance(AGENTS_GENERATION_PROMPT_V1, str)

    def test_plan_generation_prompt_v1_not_empty(self) -> None:
        """PLAN_GENERATION_PROMPT_V1 内容不为空。"""
        assert PLAN_GENERATION_PROMPT_V1
        assert isinstance(PLAN_GENERATION_PROMPT_V1, str)

    def test_version_aliases_match_v1(self) -> None:
        """当前版本别名与 V1 内容一致。"""
        assert CONVERSATION_SYSTEM_PROMPT == CONVERSATION_SYSTEM_PROMPT_V1
        assert AGENTS_GENERATION_PROMPT == AGENTS_GENERATION_PROMPT_V1
        assert PLAN_GENERATION_PROMPT == PLAN_GENERATION_PROMPT_V1

    def test_conversation_prompt_contains_key_topics(self) -> None:
        """对话 Prompt 包含关键收集主题。"""
        prompt = CONVERSATION_SYSTEM_PROMPT
        assert "项目名称" in prompt or "项目背景" in prompt
        assert "技术栈" in prompt
        assert "代码规范" in prompt
        assert "测试" in prompt

    def test_agents_prompt_has_placeholder(self) -> None:
        """AGENTS 生成 Prompt 包含对话摘要占位符。"""
        assert "{conversation_summary}" in AGENTS_GENERATION_PROMPT

    def test_plan_prompt_has_placeholder(self) -> None:
        """计划生成 Prompt 包含 AGENTS.md 内容占位符。"""
        assert "{agents_md_content}" in PLAN_GENERATION_PROMPT


class TestBuildConversationPrompt:
    """build_conversation_prompt() 函数测试。"""

    def test_first_message_no_history(self) -> None:
        """首次对话（无历史）返回 system + user 两条消息。"""
        messages = build_conversation_prompt("你好")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == CONVERSATION_SYSTEM_PROMPT
        assert messages[1] == {"role": "user", "content": "你好"}

    def test_with_empty_history(self) -> None:
        """传入空列表时效果与无历史相同。"""
        messages = build_conversation_prompt("你好", history=[])
        assert len(messages) == 2
        assert messages[1] == {"role": "user", "content": "你好"}

    def test_with_none_history(self) -> None:
        """传入 None 历史时正常返回。"""
        messages = build_conversation_prompt("你好", history=None)
        assert len(messages) == 2

    def test_with_history(self) -> None:
        """传入历史记录时，消息列表包含 system + history + user。"""
        history = [
            {"role": "user", "content": "我要做一个 Web 应用"},
            {"role": "assistant", "content": "好的，请问技术栈是什么？"},
        ]
        messages = build_conversation_prompt("用 FastAPI + React", history=history)

        # system(1) + history(2) + user(1) = 4
        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[1] == {"role": "user", "content": "我要做一个 Web 应用"}
        assert messages[2] == {
            "role": "assistant",
            "content": "好的，请问技术栈是什么？",
        }
        assert messages[3] == {"role": "user", "content": "用 FastAPI + React"}

    def test_message_order(self) -> None:
        """消息顺序：system 始终在最前，user 输入在最后。"""
        history = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "user", "content": "c"},
            {"role": "assistant", "content": "d"},
        ]
        messages = build_conversation_prompt("e", history=history)
        assert messages[0]["role"] == "system"
        assert messages[-1] == {"role": "user", "content": "e"}

    def test_returns_new_list(self) -> None:
        """每次调用返回新列表，不污染传入的 history。"""
        history = [{"role": "user", "content": "hi"}]
        messages = build_conversation_prompt("new", history=history)
        assert len(history) == 1  # 原列表未被修改
        assert len(messages) == 3


class TestBuildAgentsGenerationPrompt:
    """build_agents_generation_prompt() 函数测试。"""

    def test_returns_system_and_user(self) -> None:
        """返回 system + user 两条消息。"""
        messages = build_agents_generation_prompt("项目摘要内容")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_summary_embedded_in_user_content(self) -> None:
        """对话摘要被正确插入到 user 消息内容中。"""
        summary = "用户要做一个电商平台，使用 Django + PostgreSQL"
        messages = build_agents_generation_prompt(summary)
        user_content = messages[1]["content"]
        assert summary in user_content

    def test_system_prompt_mentions_agents_md(self) -> None:
        """system 消息角色为技术文档专家。"""
        messages = build_agents_generation_prompt("摘要")
        assert "技术文档" in messages[0]["content"]


class TestBuildPlanGenerationPrompt:
    """build_plan_generation_prompt() 函数测试。"""

    def test_returns_system_and_user(self) -> None:
        """返回 system + user 两条消息。"""
        messages = build_plan_generation_prompt("# AGENTS.md 内容")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_agents_md_embedded_in_user_content(self) -> None:
        """AGENTS.md 内容被正确插入到 user 消息中。"""
        agents_content = "# 项目规范\n技术栈：Python 3.10+"
        messages = build_plan_generation_prompt(agents_content)
        user_content = messages[1]["content"]
        assert agents_content in user_content

    def test_system_prompt_mentions_plan(self) -> None:
        """system 消息提及项目经理角色。"""
        messages = build_plan_generation_prompt("内容")
        assert "项目经理" in messages[0]["content"]


class TestPromptModuleExports:
    """验证 llm 模块导出完整性。"""

    def test_import_from_llm_module(self) -> None:
        """所有 prompt 函数和常量可从 harness.llm 导入。"""
        from harness.llm import (
            AGENTS_GENERATION_PROMPT as agp,
            CONVERSATION_SYSTEM_PROMPT as csp,
            PLAN_GENERATION_PROMPT as pgp,
            build_agents_generation_prompt as bagp,
            build_conversation_prompt as bcp,
            build_plan_generation_prompt as bpgp,
        )

        assert csp == CONVERSATION_SYSTEM_PROMPT
        assert agp == AGENTS_GENERATION_PROMPT
        assert pgp == PLAN_GENERATION_PROMPT
        assert callable(bcp)
        assert callable(bagp)
        assert callable(bpgp)
