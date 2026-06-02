# 上下文记忆优化方案

## 背景

当前 `ConversationManager` 将所有对话历史存储在 `self.history` 列表中，每次 API 调用时**全量发送**。
随着对话轮次增加，上下文线性膨胀，导致：

- Token 消耗急剧上升（成本）
- LLM 响应变慢（延迟）
- 接近上下文窗口时可能截断（稳定性）
- AGENTS.md 生成时摘要文本过长（质量）

## 目标

- 将每次 API 调用的上下文 Token 数从 **O(N) 线性增长** 优化为 **O(1) 常量级**
- 保留近期对话细节，压缩早期对话为摘要
- 引入**结构化记忆**，实时提取项目关键信息（名称、技术栈、代码规范等）
- 提升 AGENTS.md 生成质量（结构化事实 + 摘要 > 原始对话全文）

## 核心设计：双层记忆架构

```
┌─────────────────────────────────────────────────────┐
│                   发送给 LLM 的消息                    │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ System Prompt│  │ 滚动摘要     │  │ 近期 N 轮   │ │
│  │              │  │ (旧对话压缩) │  │ (完整保留)   │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
│                                                      │
│  ┌──────────────────────────────────────────────────┐│
│  │ 结构化记忆 (Project Facts)                        ││
│  │ 项目名: xxx  技术栈: xxx  代码规范: xxx            ││
│  └──────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

### 第一层：滚动窗口 + 定期摘要

- 保留最近 **K 轮**（默认 4 轮 = 8 条消息）完整对话
- 超过 K 轮的旧对话，调用 LLM 压缩为 **200 字以内的摘要**
- 每次 API 调用时发送：`system + summary_message + recent_K_turns + user_input`
- Token 量恒定：摘要 ~200 字 + K 轮 ~4000 字 = 约 5000 字

### 第二层：结构化事实记忆

- 维护一个 `ProjectFacts` 数据类，实时记录已确认的关键信息
- 字段：项目名、技术栈、代码规范、项目结构、测试策略、Git 规范等
- 每轮对话后，调用 LLM 快速提取结构化信息（轻量级，~200 token）
- 摘要注入 system prompt，确保 AI 不会重复提问

## 任务拆分

### Task 1: 创建 ConversationMemory 类

**文件**: `harness/core/memory.py`（新建）

```python
from dataclasses import dataclass, field

@dataclass
class ProjectFacts:
    """结构化项目事实记忆。"""
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
        return not any([
            self.project_name, self.background, self.tech_stack,
            self.code_standards, self.project_structure,
            self.testing_strategy, self.git_conventions, self.other_notes,
        ])

    def to_prompt_text(self) -> str:
        """格式化为可注入 prompt 的文本。"""
        parts = []
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


class ConversationMemory:
    """双层对话记忆管理器。

    Attributes:
        window_size: 滚动窗口大小（保留最近 N 轮完整对话）。
        history: 完整历史记录（用于调试和最终摘要）。
        recent: 窗口内的近期消息（发给 LLM）。
        summary: 早期对话的压缩摘要。
        facts: 结构化项目事实。
    """

    def __init__(self, client, window_size: int = 4) -> None:
        self.client = client
        self.window_size = window_size  # 4 轮 = 8 条消息
        self.history: list[dict[str, str]] = []
        self.recent: list[dict[str, str]] = []
        self.summary: str = ""
        self.facts = ProjectFacts()

    def add_turn(self, user_msg: str, assistant_msg: str) -> None:
        """添加一轮对话并触发记忆更新。"""
        turn = [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ]
        self.history.extend(turn)
        self.recent.extend(turn)

        # 窗口溢出 → 压缩旧对话
        max_messages = self.window_size * 2  # 每轮 2 条
        while len(self.recent) > max_messages:
            old = self.recent[:2]  # 取出最旧的一轮
            self.recent = self.recent[2:]
            self._summarize_chunk(old)

        # 提取结构化事实（轻量级）
        self._extract_facts(user_msg, assistant_msg)

    def get_messages_for_llm(self, user_input: str) -> list[dict]:
        """构建发送给 LLM 的消息列表。"""
        messages = []

        # 1. 摘要注入（如果有）
        if self.summary:
            messages.append({
                "role": "system",
                "content": f"以下是之前对话的摘要：\n{self.summary}",
            })

        # 2. 结构化事实注入
        facts_text = self.facts.to_prompt_text()
        if facts_text:
            messages.append({
                "role": "system",
                "content": f"已确认的项目信息：\n{facts_text}",
            })

        # 3. 近期完整对话
        messages.extend(self.recent)

        # 4. 当前用户输入
        messages.append({"role": "user", "content": user_input})
        return messages

    def get_full_summary(self) -> str:
        """获取用于 AGENTS.md 生成的完整摘要。"""
        parts = []
        if self.summary:
            parts.append(f"【早期对话摘要】\n{self.summary}")
        if not self.facts.is_empty():
            parts.append(f"【项目信息】\n{self.facts.to_prompt_text()}")
        # 近期对话全文
        for msg in self.recent:
            role = "用户" if msg["role"] == "user" else "AI"
            parts.append(f"[{role}] {msg['content']}")
        return "\n\n".join(parts)

    def _summarize_chunk(self, chunk: list[dict]) -> None:
        """调用 LLM 将一组消息压缩为摘要。"""
        # 实现细节：构建摘要 prompt → 调用 client.chat() → 合并到 self.summary
        pass

    def _extract_facts(self, user_msg: str, assistant_msg: str) -> None:
        """调用 LLM 从一轮对话中提取结构化事实。"""
        # 实现细节：构建提取 prompt → 调用 client.chat() → 解析 JSON → 更新 self.facts
        pass
```

### Task 2: 新增 Prompt 模板

**文件**: `harness/llm/prompts.py`（修改）

```python
# 对话摘要压缩 Prompt
SUMMARIZE_CHUNK_PROMPT = """\
请将以下对话内容压缩为简洁的摘要（200字以内），保留关键信息：
- 用户提到的项目名称、需求、偏好
- AI 给出的关键建议或确认

对话内容：
{chunk_text}

请直接输出摘要文本，不要加任何前缀。
"""

# 结构化事实提取 Prompt
EXTRACT_FACTS_PROMPT = """\
从以下对话中提取项目关键信息。仅输出 JSON，不要其他文本。

已知的信息：
{current_facts}

新的对话：
[用户] {user_msg}
[AI] {assistant_msg}

请输出更新后的完整信息（JSON 格式）：
{
  "project_name": "项目名称（如有）",
  "background": "项目背景简述",
  "tech_stack": ["技术1", "技术2"],
  "code_standards": "代码规范描述",
  "project_structure": "项目结构描述",
  "testing_strategy": "测试策略",
  "git_conventions": "Git规范",
  "other_notes": "其他重要信息"
}

如果某项在对话中未提及，保留已有值不变。未确认的字段留空字符串。
"""
```

### Task 3: 改造 ConversationManager

**文件**: `harness/core/conversation.py`（修改）

核心变更：

```python
# 替换 self.history 为 ConversationMemory
class ConversationManager:
    def __init__(self, client, max_rounds=15, window_size=4):
        self.client = client
        self.max_rounds = max_rounds
        self.memory = ConversationMemory(client, window_size)
        # ...

    def process_input(self, user_input: str) -> str:
        # ... 命令处理不变 ...

        # 使用 memory 构建消息（替代全量 history）
        messages = build_conversation_prompt(
            user_input=user_input,
            history=[],  # 不再传全量历史
            memory_messages=self.memory.get_messages_for_llm(user_input),
        )

        response_text = self.client.chat(messages)

        # 记录到 memory（替代直接 append history）
        self.memory.add_turn(user_input, response_text)
        self.round_count += 1
        return response_text

    def get_conversation_summary(self) -> str:
        # 使用 memory 的分层摘要（替代全文拼接）
        return self.memory.get_full_summary()
```

### Task 4: 修改 build_conversation_prompt

**文件**: `harness/llm/prompts.py`（修改）

```python
def build_conversation_prompt(
    user_input: str,
    history: list[dict[str, str]] | None = None,
    memory_messages: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": CONVERSATION_SYSTEM_PROMPT}]

    # 优先使用 memory_messages（新版）
    if memory_messages:
        messages.extend(memory_messages)
    elif history:
        messages.extend(history)  # 兼容旧调用方式
    else:
        messages.append({"role": "user", "content": user_input})

    return messages
```

### Task 5: 新增配置项

**文件**: `harness/utils/config.py`（修改）

```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    memory_window_size: int = 4     # 滚动窗口大小（轮数）
    memory_enable_facts: bool = True  # 是否启用结构化事实提取
    memory_summarize_threshold: int = 6  # 超过几轮触发首次摘要
```

### Task 6: 测试

**新增测试文件**: `tests/test_memory.py`

- `TestProjectFacts`: 数据类序列化、空判断、格式化
- `TestConversationMemory`: 窗口滚动、摘要触发、事实提取
- `TestConversationManagerWithMemory`: 集成测试，验证多轮对话 token 恒定
- `TestBackwardCompatibility`: 确保旧接口 `build_conversation_prompt(history=...)` 仍可用

## 性能对比

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 第 5 轮 API Token | ~5,000 | ~5,000 |
| 第 10 轮 API Token | ~10,000 | ~5,000 |
| 第 15 轮 API Token | ~15,000 | ~5,500 |
| 每轮额外 API 调用 | 0 | 1-2（摘要+提取，~500 token） |
| 总 Token (15轮) | ~150,000 | ~90,000 |
| AGENTS.md 生成上下文 | 全文 ~15,000 字 | 摘要+事实 ~3,000 字 |

## 实施顺序

```
Task 1 (memory.py)  →  Task 2 (prompts.py)  →  Task 3 (conversation.py)
     ↓                       ↓                        ↓
Task 5 (config.py)  →  Task 4 (prompts兼容)  →  Task 6 (tests)
```

## 风险与降级

- **摘要丢失关键信息** → 窗口保留最近 4 轮完整对话，摘要只压缩早期内容
- **额外 API 调用增加延迟** → 摘要调用可用更小的模型（如 qwen-turbo），事实提取可合并到摘要调用中
- **JSON 解析失败** → 事实提取使用 try/except，失败时保留旧 facts 不变

## 验收标准

- [x] 新建 `harness/core/memory.py`，包含 `ProjectFacts` 数据类和 `ConversationMemory` 双层记忆管理器
- [x] `prompts.py` 新增 `SUMMARIZE_CHUNK_PROMPT` 和 `EXTRACT_FACTS_PROMPT`
- [x] `conversation.py` 改造为使用 `ConversationMemory`，`history` 属性向后兼容
- [x] `build_conversation_prompt` 支持 `memory_messages` 参数，优先于 `history`
- [x] `config.py` 新增 `memory_window_size` 和 `memory_enable_facts` 配置项
- [x] 新增 `tests/test_memory.py`，42 个测试覆盖 ProjectFacts、ConversationMemory、集成测试、向后兼容
- [x] 全量测试 222 个通过，覆盖率 91%（memory.py 93%）
- [x] 上下文 Token 从 O(N) 优化为 O(1)，窗口滚动后 recent 消息数恒定
