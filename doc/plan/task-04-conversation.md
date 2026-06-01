# Task 04 - 多轮对话管理器

## 目标

实现多轮对话的状态管理，协调用户输入、LLM 响应与上下文维护。

## 依赖

- task-02（LLM 客户端）
- task-03（Prompt 模板）

## 交付物

- `core/conversation.py` - 多轮对话管理器

## 详细步骤

### 4.1 定义对话状态枚举

```python
from enum import Enum

class ConversationPhase(Enum):
    """对话阶段。"""
    COLLECTING = "collecting"      # 信息收集中
    REVIEWING = "reviewing"        # 用户审阅 AGENTS.md
    PLANNING = "planning"          # 生成计划中
    PLAN_REVIEWING = "plan_review" # 用户审阅计划
    COMPLETED = "completed"        # 完成
```

### 4.2 实现 ConversationManager

```python
class ConversationManager:
    """管理用户多轮对话的上下文与状态。"""

    def __init__(self, client: QwenClient, max_rounds: int = 15) -> None:
        self.client = client
        self.max_rounds = max_rounds
        self.phase = ConversationPhase.COLLECTING
        self.history: list[dict[str, str]] = []
        self.collected_info: dict[str, str] = {}

    def process_input(self, user_input: str) -> str:
        """处理用户输入，返回 AI 响应。"""

    def is_collection_complete(self) -> bool:
        """判断信息收集是否充分。"""

    def get_conversation_summary(self) -> str:
        """获取对话摘要，用于生成 AGENTS.md。"""
```

### 4.3 对话流程控制

- 每轮对话追加到 `history` 列表
- AI 通过 System Prompt 引导用户补充信息
- 当 AI 判断信息充足时，提示用户是否进入生成阶段
- 支持用户主动输入 `/generate` 提前触发生成
- 支持用户输入 `/quit` 退出对话

### 4.4 终端交互集成

- 使用 Rich 美化 AI 输出（Markdown 渲染）
- 使用 Typer 的 prompt 获取用户输入
- 显示当前对话轮次与进度提示

## 验收标准

- [x] 多轮对话可正常进行，上下文连贯
- [x] 对话阶段状态切换正确
- [x] `/generate` 和 `/quit` 命令正常工作
- [x] 对话历史正确维护
- [x] 28 个单元测试全部通过（总计 72 passed / 11.80s）
