# Task 02 - LLM 客户端封装（Qwen3 接入）

## 目标

封装 Qwen3 的 API 调用，提供统一的 LLM 交互接口，支持流式输出与错误重试。

## 依赖

- task-01（项目初始化）

## 交付物

- `llm/client.py` - Qwen3 API 客户端
- `core/exceptions.py` - 自定义异常类

## 详细步骤

### 2.1 定义自定义异常

文件：`core/exceptions.py`

```python
class HarnessError(Exception):
    """Harness 基础异常。"""


class LLMConnectionError(HarnessError):
    """LLM 连接失败。"""


class LLMResponseError(HarnessError):
    """LLM 响应异常（空内容、格式错误等）。"""


class LLMRateLimitError(HarnessError):
    """LLM 调用频率超限。"""
```

### 2.2 实现 LLM 客户端

文件：`llm/client.py`

核心功能：
- 使用 `openai` SDK，通过 OpenAI 兼容接口调用 Qwen3
- 支持普通调用与流式调用
- 内置 3 次重试机制（间隔 1s、2s、4s）
- 统一的错误处理与日志输出

```python
import time
from openai import OpenAI
from utils.config import Settings

class QwenClient:
    """Qwen3 LLM 客户端封装。"""

    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
        )

    def chat(self, messages: list[dict], ...) -> str:
        """发送对话请求并返回文本响应。"""

    def chat_stream(self, messages: list[dict], ...) -> Iterator[str]:
        """发送对话请求并以流式返回文本。"""

    def _call_with_retry(self, messages, ...) -> str:
        """带重试的 API 调用。"""
```

### 2.3 支持 enable_thinking 参数

Qwen3 模型支持深度思考模式，客户端需支持传递 `extra_body={"enable_thinking": True}` 参数，并在响应中处理思考内容（`reasoning_content`）与实际回答的分离。

## 验收标准

- [ ] `QwenClient.chat()` 可正常返回文本
- [ ] `QwenClient.chat_stream()` 可流式输出
- [ ] API 失败时自动重试 3 次
- [ ] 重试耗尽后抛出对应自定义异常
- [ ] 支持 `enable_thinking` 参数
