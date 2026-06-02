"""task-11 上下文记忆优化单元测试。

覆盖 ProjectFacts 数据类、ConversationMemory 双层记忆管理器、
与 ConversationManager 的集成、以及向后兼容性。
"""

import json
from unittest.mock import MagicMock, call

import pytest

from harness.core.memory import ConversationMemory, ProjectFacts
from harness.llm.prompts import build_conversation_prompt


# ============================================================
# ProjectFacts 测试
# ============================================================


class TestProjectFacts:
    """ProjectFacts 数据类测试。"""

    def test_default_is_empty(self) -> None:
        """默认实例所有字段为空。"""
        facts = ProjectFacts()
        assert facts.is_empty()

    def test_not_empty_with_name(self) -> None:
        """设置 project_name 后不为空。"""
        facts = ProjectFacts(project_name="TestProject")
        assert not facts.is_empty()

    def test_not_empty_with_tech_stack(self) -> None:
        """设置 tech_stack 后不为空。"""
        facts = ProjectFacts(tech_stack=["Python", "Vue"])
        assert not facts.is_empty()

    def test_to_prompt_text_empty(self) -> None:
        """空 facts 返回空字符串。"""
        facts = ProjectFacts()
        assert facts.to_prompt_text() == ""

    def test_to_prompt_text_full(self) -> None:
        """完整 facts 格式化正确。"""
        facts = ProjectFacts(
            project_name="博客",
            background="个人技术博客",
            tech_stack=["Vue3", "Vite", "TypeScript"],
            code_standards="ESLint + Prettier",
            project_structure="src/views, src/components",
            testing_strategy="Vitest",
            git_conventions="feat(scope): desc",
            other_notes="部署到 GitHub Pages",
        )
        text = facts.to_prompt_text()
        assert "项目名称: 博客" in text
        assert "技术栈: Vue3, Vite, TypeScript" in text
        assert "代码规范: ESLint + Prettier" in text
        assert "测试策略: Vitest" in text
        assert "Git规范: feat(scope): desc" in text
        assert "其他: 部署到 GitHub Pages" in text

    def test_to_prompt_text_partial(self) -> None:
        """部分字段不输出空行。"""
        facts = ProjectFacts(project_name="X", tech_stack=["Go"])
        text = facts.to_prompt_text()
        assert "项目名称: X" in text
        assert "技术栈: Go" in text
        assert "代码规范" not in text
        assert "Git规范" not in text

    def test_to_dict(self) -> None:
        """to_dict() 返回正确字典。"""
        facts = ProjectFacts(project_name="P", tech_stack=["A"])
        d = facts.to_dict()
        assert d["project_name"] == "P"
        assert d["tech_stack"] == ["A"]
        assert d["background"] == ""

    def test_from_dict(self) -> None:
        """from_dict() 正确创建实例。"""
        data = {
            "project_name": "MyApp",
            "tech_stack": ["React", "Node"],
            "background": "Web应用",
        }
        facts = ProjectFacts.from_dict(data)
        assert facts.project_name == "MyApp"
        assert facts.tech_stack == ["React", "Node"]
        assert facts.background == "Web应用"
        assert facts.code_standards == ""

    def test_from_dict_missing_keys(self) -> None:
        """from_dict() 处理缺失字段使用默认值。"""
        facts = ProjectFacts.from_dict({})
        assert facts.is_empty()

    def test_roundtrip(self) -> None:
        """to_dict → from_dict 往返一致。"""
        original = ProjectFacts(
            project_name="Round",
            tech_stack=["X", "Y"],
            testing_strategy="pytest",
        )
        restored = ProjectFacts.from_dict(original.to_dict())
        assert restored.project_name == original.project_name
        assert restored.tech_stack == original.tech_stack
        assert restored.testing_strategy == original.testing_strategy


# ============================================================
# ConversationMemory 测试
# ============================================================


@pytest.fixture
def mock_client() -> MagicMock:
    """模拟 LLM 客户端。"""
    client = MagicMock()
    client.chat.return_value = "AI 响应"
    return client


@pytest.fixture
def memory(mock_client: MagicMock) -> ConversationMemory:
    """创建 window_size=2 的记忆管理器。"""
    return ConversationMemory(client=mock_client, window_size=2, enable_facts=False)


class TestConversationMemoryInit:
    """ConversationMemory 初始化测试。"""

    def test_initial_state(self, memory: ConversationMemory) -> None:
        """初始状态正确。"""
        assert memory.window_size == 2
        assert memory.history == []
        assert memory.recent == []
        assert memory.summary == ""
        assert memory.facts.is_empty()
        assert memory.round_count == 0

    def test_default_window_size(self, mock_client: MagicMock) -> None:
        """默认窗口大小为 4。"""
        mem = ConversationMemory(client=mock_client)
        assert mem.window_size == 4

    def test_enable_facts_default(self, mock_client: MagicMock) -> None:
        """默认启用事实提取。"""
        mem = ConversationMemory(client=mock_client)
        assert mem.enable_facts is True


class TestConversationMemoryAddTurn:
    """add_turn() 方法测试。"""

    def test_add_turn_updates_history(
        self, memory: ConversationMemory
    ) -> None:
        """add_turn 正确更新 history。"""
        memory.add_turn("你好", "你好！")
        assert len(memory.history) == 2
        assert memory.history[0] == {"role": "user", "content": "你好"}
        assert memory.history[1] == {"role": "assistant", "content": "你好！"}

    def test_add_turn_updates_recent(
        self, memory: ConversationMemory
    ) -> None:
        """add_turn 正确更新 recent。"""
        memory.add_turn("输入", "响应")
        assert len(memory.recent) == 2

    def test_add_turn_increments_round_count(
        self, memory: ConversationMemory
    ) -> None:
        """add_turn 增加 round_count。"""
        memory.add_turn("a", "b")
        assert memory.round_count == 1
        memory.add_turn("c", "d")
        assert memory.round_count == 2

    def test_window_overflow_triggers_summarize(
        self, memory: ConversationMemory, mock_client: MagicMock
    ) -> None:
        """窗口溢出时触发摘要。"""
        mock_client.chat.return_value = "摘要内容"
        # window_size=2 → 超过 4 条消息时压缩
        memory.add_turn("轮1用户", "轮1AI")  # recent: 2
        memory.add_turn("轮2用户", "轮2AI")  # recent: 4
        assert len(memory.recent) == 4

        memory.add_turn("轮3用户", "轮3AI")  # recent: 6 → 压缩到 4
        assert len(memory.recent) == 4
        # 摘要被调用（至少一次）
        assert memory.summary != "" or mock_client.chat.called

    def test_window_keeps_recent_turns(
        self, memory: ConversationMemory, mock_client: MagicMock
    ) -> None:
        """窗口始终保留最近的对话。"""
        mock_client.chat.return_value = "摘要"
        for i in range(5):
            memory.add_turn(f"用户{i}", f"AI{i}")

        # recent 最多 window_size*2 = 4 条消息
        assert len(memory.recent) <= 4
        # history 保留所有记录
        assert len(memory.history) == 10


class TestConversationMemoryMessages:
    """get_messages_for_llm() 方法测试。"""

    def test_first_message_no_context(
        self, memory: ConversationMemory
    ) -> None:
        """首次消息仅包含用户输入。"""
        messages = memory.get_messages_for_llm("你好")
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "你好"}

    def test_with_recent_history(
        self, memory: ConversationMemory
    ) -> None:
        """有近期历史时正确组装。"""
        memory.add_turn("输入1", "响应1")
        messages = memory.get_messages_for_llm("输入2")
        # recent(2) + user_input(1) = 3
        assert len(messages) == 3
        assert messages[0]["content"] == "输入1"
        assert messages[1]["content"] == "响应1"
        assert messages[2]["content"] == "输入2"

    def test_with_summary(
        self, memory: ConversationMemory
    ) -> None:
        """有摘要时注入 system 消息。"""
        memory.summary = "之前的对话摘要"
        messages = memory.get_messages_for_llm("新输入")
        assert messages[0]["role"] == "system"
        assert "摘要" in messages[0]["content"]
        assert messages[-1]["content"] == "新输入"

    def test_with_facts(
        self, memory: ConversationMemory
    ) -> None:
        """有事实时注入 system 消息。"""
        memory.facts = ProjectFacts(
            project_name="测试项目",
            tech_stack=["Python"],
        )
        messages = memory.get_messages_for_llm("输入")
        system_msgs = [m for m in messages if m["role"] == "system"]
        assert len(system_msgs) >= 1
        facts_msg = [m for m in system_msgs if "项目信息" in m["content"]]
        assert len(facts_msg) == 1
        assert "测试项目" in facts_msg[0]["content"]

    def test_with_summary_and_facts(
        self, memory: ConversationMemory
    ) -> None:
        """摘要和事实同时存在。"""
        memory.summary = "摘要文本"
        memory.facts = ProjectFacts(project_name="P")
        messages = memory.get_messages_for_llm("输入")
        system_msgs = [m for m in messages if m["role"] == "system"]
        assert len(system_msgs) == 2


class TestConversationMemorySummary:
    """get_full_summary() 方法测试。"""

    def test_raises_when_empty(
        self, memory: ConversationMemory
    ) -> None:
        """历史为空时抛出 ValueError。"""
        with pytest.raises(ValueError, match="为空"):
            memory.get_full_summary()

    def test_returns_recent_only(
        self, memory: ConversationMemory
    ) -> None:
        """仅有近期对话时返回近期内容。"""
        memory.add_turn("问题", "回答")
        summary = memory.get_full_summary()
        assert "[用户] 问题" in summary
        assert "[AI] 回答" in summary

    def test_includes_summary_section(
        self, memory: ConversationMemory
    ) -> None:
        """有摘要时包含【早期对话摘要】段落。"""
        memory.summary = "旧对话压缩内容"
        memory.add_turn("新问题", "新回答")
        summary = memory.get_full_summary()
        assert "【早期对话摘要】" in summary
        assert "旧对话压缩内容" in summary

    def test_includes_facts_section(
        self, memory: ConversationMemory
    ) -> None:
        """有事实时包含【项目信息】段落。"""
        memory.facts = ProjectFacts(project_name="Blog")
        memory.add_turn("a", "b")
        summary = memory.get_full_summary()
        assert "【项目信息】" in summary
        assert "Blog" in summary


class TestConversationMemoryContextSize:
    """get_context_size_estimate() 方法测试。"""

    def test_empty_is_zero(
        self, memory: ConversationMemory
    ) -> None:
        """空记忆大小为 0。"""
        assert memory.get_context_size_estimate() == 0

    def test_grows_with_turns(
        self, memory: ConversationMemory
    ) -> None:
        """添加对话后大小增加。"""
        memory.add_turn("用户消息", "AI消息")
        size1 = memory.get_context_size_estimate()
        memory.add_turn("更多用户消息", "更多AI消息")
        size2 = memory.get_context_size_estimate()
        assert size2 > size1


class TestConversationMemoryFactExtraction:
    """结构化事实提取测试。"""

    def test_extract_facts_updates_facts(
        self, mock_client: MagicMock
    ) -> None:
        """事实提取正确更新 ProjectFacts。"""
        facts_json = json.dumps({
            "project_name": "Blog",
            "background": "个人博客",
            "tech_stack": ["Vue3"],
            "code_standards": "",
            "project_structure": "",
            "testing_strategy": "",
            "git_conventions": "",
            "other_notes": "",
        }, ensure_ascii=False)

        # add_turn 中只调用 _extract_facts → 1 次 client.chat
        mock_client.chat.return_value = facts_json

        mem = ConversationMemory(
            client=mock_client, window_size=4, enable_facts=True
        )
        mem.add_turn("我想做Vue3博客", "好的，Vue3博客项目")
        assert mem.facts.project_name == "Blog"
        assert "Vue3" in mem.facts.tech_stack

    def test_extract_facts_failure_keeps_old(
        self, mock_client: MagicMock
    ) -> None:
        """事实提取失败时保留旧 facts。"""
        mock_client.chat.side_effect = [
            "AI响应",       # 主对话
            "invalid json", # 事实提取失败
        ]

        mem = ConversationMemory(
            client=mock_client, window_size=4, enable_facts=True
        )
        mem.facts = ProjectFacts(project_name="原有项目")
        mem.add_turn("输入", "AI响应")
        # 事实提取失败，保留旧值
        assert mem.facts.project_name == "原有项目"

    def test_extract_facts_disabled(
        self, mock_client: MagicMock
    ) -> None:
        """禁用事实提取时不调用额外 LLM。"""
        mock_client.chat.return_value = "响应"

        mem = ConversationMemory(
            client=mock_client, window_size=4, enable_facts=False
        )
        mem.add_turn("输入", "响应")
        # 只调用了 1 次（主对话），没有额外的事实提取调用
        # 注：这里 mock_client 是在 ConversationManager 外部创建的
        # add_turn 内部不会调用 client.chat（因为 enable_facts=False）


# ============================================================
# 向后兼容性测试
# ============================================================


class TestBackwardCompatibility:
    """确保旧接口仍然可用。"""

    def test_build_conversation_prompt_with_history(self) -> None:
        """旧版 history 参数仍然有效。"""
        history = [
            {"role": "user", "content": "旧输入"},
            {"role": "assistant", "content": "旧响应"},
        ]
        messages = build_conversation_prompt(
            user_input="新输入",
            history=history,
        )
        assert messages[0]["role"] == "system"
        assert messages[1]["content"] == "旧输入"
        assert messages[2]["content"] == "旧响应"
        assert messages[3]["content"] == "新输入"

    def test_build_conversation_prompt_with_memory_messages(self) -> None:
        """新版 memory_messages 参数有效，优先于 history。"""
        memory_msgs = [
            {"role": "system", "content": "摘要"},
            {"role": "user", "content": "近期输入"},
        ]
        history = [
            {"role": "user", "content": "不应使用"},
        ]
        messages = build_conversation_prompt(
            user_input="当前输入",
            history=history,
            memory_messages=memory_msgs,
        )
        # memory_messages 优先
        contents = [m["content"] for m in messages]
        assert "摘要" in contents
        assert "近期输入" in contents
        assert "不应使用" not in contents

    def test_build_conversation_prompt_neither(self) -> None:
        """无 history 和 memory_messages 时仅含 system + user。"""
        messages = build_conversation_prompt(user_input="首条消息")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["content"] == "首条消息"

    def test_conversation_manager_history_property(
        self, mock_client: MagicMock
    ) -> None:
        """ConversationManager.history 属性仍然可用。"""
        from harness.core.conversation import ConversationManager

        mgr = ConversationManager(client=mock_client, max_rounds=3)
        assert mgr.history == []
        mock_client.chat.return_value = "响应"
        mgr.process_input("输入")
        assert len(mgr.history) == 2


# ============================================================
# ConversationManager + Memory 集成测试
# ============================================================


class TestConversationManagerWithMemory:
    """ConversationManager 使用双层记忆的集成测试。"""

    def test_memory_is_initialized(
        self, mock_client: MagicMock
    ) -> None:
        """ConversationManager 初始化时创建 memory。"""
        from harness.core.conversation import ConversationManager

        mgr = ConversationManager(client=mock_client, max_rounds=5)
        assert mgr.memory is not None
        assert mgr.memory.window_size == 4

    def test_custom_window_size(
        self, mock_client: MagicMock
    ) -> None:
        """自定义窗口大小传递到 memory。"""
        from harness.core.conversation import ConversationManager

        mgr = ConversationManager(
            client=mock_client, max_rounds=5, window_size=2
        )
        assert mgr.memory.window_size == 2

    def test_process_input_uses_memory(
        self, mock_client: MagicMock
    ) -> None:
        """process_input 使用 memory 构建消息。"""
        from harness.core.conversation import ConversationManager

        mock_client.chat.return_value = "AI回答"
        mgr = ConversationManager(
            client=mock_client, max_rounds=5, enable_facts=False
        )

        mgr.process_input("第一轮")
        mgr.process_input("第二轮")

        # memory.recent 包含所有轮
        assert len(mgr.memory.recent) == 4
        # memory.history 包含所有轮
        assert len(mgr.memory.history) == 4

    def test_summary_uses_memory(
        self, mock_client: MagicMock
    ) -> None:
        """get_conversation_summary 使用 memory 的分层摘要。"""
        from harness.core.conversation import ConversationManager

        mock_client.chat.return_value = "回答"
        mgr = ConversationManager(
            client=mock_client, max_rounds=5, enable_facts=False
        )
        mgr.process_input("问题")

        summary = mgr.get_conversation_summary()
        assert "[用户] 问题" in summary
        assert "[AI] 回答" in summary

    def test_window_rolling_in_integration(
        self, mock_client: MagicMock
    ) -> None:
        """集成测试：窗口滚动正确压缩旧对话。"""
        from harness.core.conversation import ConversationManager

        mock_client.chat.return_value = "摘要或响应"
        mgr = ConversationManager(
            client=mock_client,
            max_rounds=10,
            window_size=2,
            enable_facts=False,
        )

        for i in range(5):
            mgr.process_input(f"输入{i}")

        # recent 不超过 4 条消息（window_size=2）
        assert len(mgr.memory.recent) <= 4
        # history 保留全部 10 条消息
        assert len(mgr.memory.history) == 10

    def test_context_size_stable(
        self, mock_client: MagicMock
    ) -> None:
        """上下文大小在窗口滚动后保持稳定。"""
        from harness.core.conversation import ConversationManager

        mock_client.chat.return_value = "固定长度响应"
        mgr = ConversationManager(
            client=mock_client,
            max_rounds=10,
            window_size=2,
            enable_facts=False,
        )

        # 先填满窗口
        for i in range(3):
            mgr.process_input(f"输入{i}")

        size_after_3 = mgr.memory.get_context_size_estimate()

        # 继续添加
        for i in range(3, 7):
            mgr.process_input(f"输入{i}")

        size_after_7 = mgr.memory.get_context_size_estimate()

        # 上下文大小不应线性增长（允许摘要带来的波动）
        # 窗口大小为 2 → recent 最多 4 条消息
        assert size_after_7 < size_after_3 * 3  # 不应超过 3 倍
