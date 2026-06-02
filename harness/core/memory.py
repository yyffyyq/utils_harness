"""双层对话记忆管理器。

实现滚动窗口摘要 + 结构化事实提取，
将对话上下文 Token 从 O(N) 优化为 O(1)。
"""

import json
import re
from dataclasses import dataclass, field

from rich.console import Console

console = Console()


@dataclass
class ProjectFacts:
    """结构化项目事实记忆。

    从多轮对话中提取并维护的关键项目信息，
    用于注入 system prompt 和 AGENTS.md 生成。

    Attributes:
        project_name: 项目名称。
        background: 项目背景简述。
        tech_stack: 技术栈列表。
        code_standards: 代码规范描述。
        project_structure: 项目结构描述。
        testing_strategy: 测试策略。
        git_conventions: Git 规范。
        other_notes: 其他重要信息。
    """

    project_name: str = ""
    background: str = ""
    tech_stack: list[str] = field(default_factory=list)
    code_standards: str = ""
    project_structure: str = ""
    testing_strategy: str = ""
    git_conventions: str = ""
    other_notes: str = ""

    def is_empty(self) -> bool:
        """是否所有字段都为空。"""
        return not any(
            [
                self.project_name,
                self.background,
                self.tech_stack,
                self.code_standards,
                self.project_structure,
                self.testing_strategy,
                self.git_conventions,
                self.other_notes,
            ]
        )

    def to_prompt_text(self) -> str:
        """格式化为可注入 prompt 的文本。

        Returns:
            格式化的多行文本；所有字段为空时返回空字符串。
        """
        parts: list[str] = []
        if self.project_name:
            parts.append(f"项目名称: {self.project_name}")
        if self.background:
            parts.append(f"项目背景: {self.background}")
        if self.tech_stack:
            parts.append(f"技术栈: {', '.join(self.tech_stack)}")
        if self.code_standards:
            parts.append(f"代码规范: {self.code_standards}")
        if self.project_structure:
            parts.append(f"项目结构: {self.project_structure}")
        if self.testing_strategy:
            parts.append(f"测试策略: {self.testing_strategy}")
        if self.git_conventions:
            parts.append(f"Git规范: {self.git_conventions}")
        if self.other_notes:
            parts.append(f"其他: {self.other_notes}")
        return "\n".join(parts) if parts else ""

    def to_dict(self) -> dict[str, str | list[str]]:
        """转换为字典格式。"""
        return {
            "project_name": self.project_name,
            "background": self.background,
            "tech_stack": self.tech_stack,
            "code_standards": self.code_standards,
            "project_structure": self.project_structure,
            "testing_strategy": self.testing_strategy,
            "git_conventions": self.git_conventions,
            "other_notes": self.other_notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectFacts":
        """从字典创建 ProjectFacts 实例。

        Args:
            data: 包含字段值的字典，缺失字段使用默认值。

        Returns:
            ProjectFacts 实例。
        """
        return cls(
            project_name=data.get("project_name", ""),
            background=data.get("background", ""),
            tech_stack=data.get("tech_stack", []),
            code_standards=data.get("code_standards", ""),
            project_structure=data.get("project_structure", ""),
            testing_strategy=data.get("testing_strategy", ""),
            git_conventions=data.get("git_conventions", ""),
            other_notes=data.get("other_notes", ""),
        )


class ConversationMemory:
    """双层对话记忆管理器。

    第一层：滚动窗口 + 定期摘要
        保留最近 K 轮完整对话，旧对话压缩为摘要。

    第二层：结构化事实记忆
        维护 ProjectFacts，实时提取项目关键信息。

    Attributes:
        client: LLM 客户端实例。
        window_size: 滚动窗口大小（轮数）。
        enable_facts: 是否启用结构化事实提取。
        history: 完整历史记录（调试用）。
        recent: 窗口内的近期消息（发给 LLM）。
        summary: 早期对话的压缩摘要。
        facts: 结构化项目事实。
    """

    def __init__(
        self,
        client,
        window_size: int = 4,
        enable_facts: bool = True,
    ) -> None:
        """初始化记忆管理器。

        Args:
            client: Qwen3 LLM 客户端实例。
            window_size: 滚动窗口大小（保留最近 N 轮完整对话）。
            enable_facts: 是否启用结构化事实提取。
        """
        self.client = client
        self.window_size = window_size
        self.enable_facts = enable_facts
        self.history: list[dict[str, str]] = []
        self.recent: list[dict[str, str]] = []
        self.summary: str = ""
        self.facts = ProjectFacts()
        self._summary_count: int = 0

    @property
    def round_count(self) -> int:
        """历史中的总轮次数。"""
        return len(self.history) // 2

    def add_turn(self, user_msg: str, assistant_msg: str) -> None:
        """添加一轮对话并触发记忆更新。

        Args:
            user_msg: 用户消息。
            assistant_msg: AI 响应消息。
        """
        turn = [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ]
        self.history.extend(turn)
        self.recent.extend(turn)

        # 窗口溢出 → 压缩旧对话
        max_messages = self.window_size * 2
        while len(self.recent) > max_messages:
            old = self.recent[:2]
            self.recent = self.recent[2:]
            self._summarize_chunk(old)

        # 提取结构化事实
        if self.enable_facts:
            self._extract_facts(user_msg, assistant_msg)

    def get_messages_for_llm(self, user_input: str) -> list[dict[str, str]]:
        """构建发送给 LLM 的消息列表。

        组装顺序：摘要 → 结构化事实 → 近期对话 → 当前输入。

        Args:
            user_input: 当前用户输入。

        Returns:
            OpenAI 格式消息列表。
        """
        messages: list[dict[str, str]] = []

        # 1. 摘要注入
        if self.summary:
            messages.append(
                {
                    "role": "system",
                    "content": f"以下是之前对话的摘要：\n{self.summary}",
                }
            )

        # 2. 结构化事实注入
        facts_text = self.facts.to_prompt_text()
        if facts_text:
            messages.append(
                {
                    "role": "system",
                    "content": f"已确认的项目信息：\n{facts_text}",
                }
            )

        # 3. 近期完整对话
        messages.extend(self.recent)

        # 4. 当前用户输入
        messages.append({"role": "user", "content": user_input})
        return messages

    def get_full_summary(self) -> str:
        """获取用于 AGENTS.md 生成的完整摘要。

        组合早期摘要 + 结构化事实 + 近期对话全文。

        Returns:
            格式化的摘要文本。

        Raises:
            ValueError: 历史为空时抛出。
        """
        if not self.history:
            raise ValueError("对话历史为空，无法生成摘要。")

        parts: list[str] = []

        if self.summary:
            parts.append(f"【早期对话摘要】\n{self.summary}")

        if not self.facts.is_empty():
            parts.append(f"【项目信息】\n{self.facts.to_prompt_text()}")

        # 近期对话全文
        for msg in self.recent:
            role = "用户" if msg["role"] == "user" else "AI"
            parts.append(f"[{role}] {msg['content']}")

        return "\n\n".join(parts)

    def get_context_size_estimate(self) -> int:
        """估算当前上下文的字符数（用于性能监控）。

        Returns:
            摘要 + 事实 + 近期对话的总字符数。
        """
        total = len(self.summary)
        total += len(self.facts.to_prompt_text())
        total += sum(len(m.get("content", "")) for m in self.recent)
        return total

    def _summarize_chunk(self, chunk: list[dict[str, str]]) -> None:
        """调用 LLM 将一组消息压缩为摘要。

        Args:
            chunk: 要压缩的消息列表（通常为一轮对话的 2 条消息）。
        """
        from harness.llm.prompts import SUMMARIZE_CHUNK_PROMPT

        # 格式化 chunk 为文本
        chunk_lines: list[str] = []
        for msg in chunk:
            role = "用户" if msg["role"] == "user" else "AI"
            chunk_lines.append(f"[{role}] {msg['content']}")
        chunk_text = "\n".join(chunk_lines)

        # 如果有已有摘要，一并传入让 LLM 合并
        if self.summary:
            chunk_text = f"已有摘要：\n{self.summary}\n\n新对话：\n{chunk_text}"

        prompt = SUMMARIZE_CHUNK_PROMPT.format(chunk_text=chunk_text)

        try:
            messages = [{"role": "user", "content": prompt}]
            result = self.client.chat(messages)
            if isinstance(result, dict):
                result = result.get("content", "")
            self.summary = result.strip()
            self._summary_count += 1
        except Exception:
            # 摘要失败时降级：直接拼接关键内容
            self._fallback_summarize(chunk)

    def _fallback_summarize(self, chunk: list[dict[str, str]]) -> None:
        """LLM 摘要失败时的降级方案：直接截取拼接。

        Args:
            chunk: 要处理的消息列表。
        """
        for msg in chunk:
            content = msg["content"]
            # 截取前 100 字符
            snippet = content[:100] + "..." if len(content) > 100 else content
            role = "用户" if msg["role"] == "user" else "AI"
            line = f"[{role}] {snippet}"
            self.summary = f"{self.summary}\n{line}".strip() if self.summary else line

    def _extract_facts(self, user_msg: str, assistant_msg: str) -> None:
        """调用 LLM 从一轮对话中提取结构化事实。

        Args:
            user_msg: 用户消息。
            assistant_msg: AI 响应消息。
        """
        from harness.llm.prompts import EXTRACT_FACTS_PROMPT

        current_facts_text = (
            json.dumps(self.facts.to_dict(), ensure_ascii=False)
            if not self.facts.is_empty()
            else "（暂无）"
        )

        prompt = EXTRACT_FACTS_PROMPT.format(
            current_facts=current_facts_text,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
        )

        try:
            messages = [{"role": "user", "content": prompt}]
            result = self.client.chat(messages)
            if isinstance(result, dict):
                result = result.get("content", "")
            self._parse_and_update_facts(result)
        except Exception:
            # 提取失败时保留旧 facts 不变
            pass

    def _parse_and_update_facts(self, raw: str) -> None:
        """解析 LLM 返回的 JSON 并更新 facts。

        Args:
            raw: LLM 返回的原始文本（预期为 JSON）。
        """
        # 尝试提取 JSON 块
        text = raw.strip()

        # 尝试去除 ```json ... ``` 包裹
        json_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL
        )
        if json_match:
            text = json_match.group(1).strip()

        data = json.loads(text)
        if isinstance(data, dict):
            self.facts = ProjectFacts.from_dict(data)
