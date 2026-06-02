"""多轮对话管理器模块。

实现对话状态管理、上下文维护与终端交互，
协调用户输入、LLM 响应与流程控制。
支持双层记忆架构（滚动窗口摘要 + 结构化事实提取）。
"""

from enum import Enum

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from harness.core.exceptions import (
    ConversationError,
    ConversationMaxRoundsError,
)
from harness.core.memory import ConversationMemory
from harness.llm.client import QwenClient
from harness.llm.prompts import build_conversation_prompt

console = Console()


class ConversationPhase(Enum):
    """对话阶段枚举。

    Attributes:
        COLLECTING: 信息收集中，AI 引导用户描述项目信息。
        REVIEWING: 用户审阅 AGENTS.md 初稿。
        PLANNING: AI 正在生成实施计划。
        PLAN_REVIEWING: 用户审阅实施计划。
        COMPLETED: 全部流程完成。
    """

    COLLECTING = "collecting"
    REVIEWING = "reviewing"
    PLANNING = "planning"
    PLAN_REVIEWING = "plan_review"
    COMPLETED = "completed"


# 内置命令常量
CMD_GENERATE: str = "/generate"
CMD_QUIT: str = "/quit"
CMD_HELP: str = "/help"

# AI 响应中暗示信息已充足的关键词
_COMPLETION_KEYWORDS: list[str] = [
    "可以生成",
    "信息已经足够",
    "信息充足",
    "可以开始生成",
    "准备就绪",
]


class ConversationManager:
    """管理用户多轮对话的上下文与状态。

    通过 QwenClient 与 Qwen3 模型交互，引导用户完成项目信息收集，
    并在信息充足后触发生成 AGENTS.md 的流程。

    Attributes:
        client: Qwen3 LLM 客户端实例。
        max_rounds: 最大对话轮次（一轮 = 一次用户输入 + 一次 AI 响应）。
        phase: 当前对话阶段。
        history: 对话历史记录列表（不含 system prompt）。
        round_count: 当前已完成的对话轮次数。
    """

    def __init__(
        self,
        client: QwenClient,
        max_rounds: int = 15,
        window_size: int = 4,
        enable_facts: bool = True,
    ) -> None:
        """初始化对话管理器。

        Args:
            client: Qwen3 客户端实例。
            max_rounds: 最大对话轮次，超过后强制结束收集。
            window_size: 记忆滚动窗口大小（轮数）。
            enable_facts: 是否启用结构化事实提取。
        """
        self.client = client
        self.max_rounds = max_rounds
        self.phase: ConversationPhase = ConversationPhase.COLLECTING
        self.memory = ConversationMemory(
            client=client,
            window_size=window_size,
            enable_facts=enable_facts,
        )
        self.round_count: int = 0
        self._should_generate: bool = False
        self._should_quit: bool = False

    @property
    def history(self) -> list[dict[str, str]]:
        """对话历史记录（兼容旧接口，指向 memory.history）。"""
        return self.memory.history

    @property
    def should_generate(self) -> bool:
        """用户是否触发了 /generate 命令或 AI 建议生成。"""
        return self._should_generate

    @property
    def should_quit(self) -> bool:
        """用户是否触发了 /quit 命令。"""
        return self._should_quit

    def process_input(self, user_input: str) -> str:
        """处理用户输入并返回 AI 响应。

        支持内置命令：
        - ``/generate``: 强制进入生成阶段。
        - ``/quit``: 退出对话。
        - ``/help``: 显示帮助信息。

        Args:
            user_input: 用户输入的文本。

        Returns:
            AI 的文本响应；若为命令则返回命令提示信息。

        Raises:
            ConversationMaxRoundsError: 对话轮次已达上限。
            ConversationError: 对话状态异常。
        """
        stripped = user_input.strip()

        # ---- 内置命令处理 ----
        if stripped == CMD_QUIT:
            self._should_quit = True
            self.phase = ConversationPhase.COMPLETED
            return "已退出对话。"

        if stripped == CMD_HELP:
            return (
                "可用命令：\n"
                f"  {CMD_GENERATE}  - 强制生成 AGENTS.md\n"
                f"  {CMD_QUIT}      - 退出对话\n"
                f"  {CMD_HELP}      - 显示此帮助"
            )

        if stripped == CMD_GENERATE:
            self._should_generate = True
            self.phase = ConversationPhase.REVIEWING
            return "好的，即将基于当前对话生成 AGENTS.md。"

        # ---- 轮次检查 ----
        if self.round_count >= self.max_rounds:
            raise ConversationMaxRoundsError(
                f"对话轮次已达上限（{self.max_rounds}），"
                f"请输入 {CMD_GENERATE} 生成文档或 "
                f"{CMD_QUIT} 退出。"
            )

        # ---- 构建消息并调用 LLM ----
        messages = build_conversation_prompt(
            user_input=user_input,
            memory_messages=self.memory.get_messages_for_llm(user_input),
        )

        response_text = self.client.chat(messages)
        # chat() 返回 str（非 thinking 模式）
        if isinstance(response_text, dict):
            response_text = response_text.get("content", "")

        # ---- 更新记忆 ----
        self.memory.add_turn(user_input, response_text)
        self.round_count += 1

        # ---- 检测 AI 是否建议生成 ----
        if self._check_completion_signal(response_text):
            self._should_generate = True
            self.phase = ConversationPhase.REVIEWING

        return response_text

    def is_collection_complete(self) -> bool:
        """判断信息收集是否充分。

        满足以下任一条件即认为充分：
        1. 用户主动输入 ``/generate``
        2. AI 响应中包含完成关键词
        3. 对话轮次已达上限

        Returns:
            是否可以进入生成阶段。
        """
        return (
            self._should_generate
            or self.round_count >= self.max_rounds
        )

    def get_conversation_summary(self) -> str:
        """获取对话摘要，用于生成 AGENTS.md。

        使用双层记忆的分层摘要：早期摘要 + 结构化事实 + 近期对话全文。

        Returns:
            格式化的对话摘要字符串。

        Raises:
            ConversationError: 对话历史为空时抛出。
        """
        try:
            return self.memory.get_full_summary()
        except ValueError:
            raise ConversationError("对话历史为空，无法生成摘要。")

    def render_response(self, text: str) -> None:
        """使用 Rich 将 AI 响应渲染到终端。

        支持 Markdown 渲染，并以 Panel 包装美化输出。

        Args:
            text: 要渲染的文本内容。
        """
        try:
            md = Markdown(text)
            console.print(Panel(md, title="Harness", border_style="cyan"))
        except Exception:
            console.print(Panel(text, title="Harness", border_style="cyan"))

    def render_status(self) -> None:
        """在终端显示当前对话状态信息。"""
        status_parts = [
            f"阶段: [bold]{self.phase.value}[/bold]",
            f"轮次: {self.round_count}/{self.max_rounds}",
        ]
        if self._should_generate:
            status_parts.append("[green]✓ 可生成 AGENTS.md[/green]")
        console.print(
            " | ".join(status_parts),
            style="dim",
        )

    def _check_completion_signal(self, response: str) -> bool:
        """检测 AI 响应中是否包含信息充足的暗示。

        Args:
            response: AI 的响应文本。

        Returns:
            是否检测到完成信号。
        """
        return any(kw in response for kw in _COMPLETION_KEYWORDS)
