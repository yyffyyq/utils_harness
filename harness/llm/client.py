"""Qwen3 LLM 客户端封装。"""

import time
from collections.abc import Iterator

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam
from rich.console import Console

from harness.core.exceptions import (
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseError,
)
from harness.utils.config import Settings

console = Console()


class QwenClient:
    """Qwen3 LLM 客户端封装。

    通过 OpenAI 兼容接口调用 Qwen3 模型，支持普通调用与流式调用，
    内置 3 次重试机制（间隔 1s、2s、4s）。

    Attributes:
        MAX_RETRIES: 最大重试次数。
        RETRY_DELAYS: 每次重试的等待秒数列表。
    """

    MAX_RETRIES: int = 3
    RETRY_DELAYS: list[int] = [1, 2, 4]

    def __init__(self, settings: Settings) -> None:
        """初始化 QwenClient。

        Args:
            settings: 应用配置实例，包含 API Key、Base URL 等。
        """
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            timeout=120.0,
        )

    def chat(
        self,
        messages: list[ChatCompletionMessageParam],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        enable_thinking: bool = False,
    ) -> dict[str, str] | str:
        """发送对话请求并返回文本响应。

        Args:
            messages: 对话消息列表，每条包含 role 和 content。
            temperature: 生成温度，为 None 时使用配置默认值。
            max_tokens: 最大 token 数，为 None 时使用配置默认值。
            enable_thinking: 是否启用 Qwen3 深度思考模式。

        Returns:
            enable_thinking=False 时返回纯文本字符串；
            enable_thinking=True 时返回字典，包含：
                - "reasoning": 思考过程内容
                - "content": 实际回答内容

        Raises:
            LLMResponseError: 模型返回空内容或格式异常。
            LLMConnectionError: 重试耗尽后仍无法连接。
            LLMRateLimitError: 调用频率超限且重试失败。
        """
        return self._call_with_retry(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_thinking=enable_thinking,
        )

    def chat_stream(
        self,
        messages: list[ChatCompletionMessageParam],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        enable_thinking: bool = False,
    ) -> Iterator[str]:
        """发送对话请求并以流式返回文本。

        Args:
            messages: 对话消息列表，每条包含 role 和 content。
            temperature: 生成温度，为 None 时使用配置默认值。
            max_tokens: 最大 token 数，为 None 时使用配置默认值。
            enable_thinking: 是否启用 Qwen3 深度思考模式。

        Yields:
            模型逐步生成的文本片段。

        Raises:
            LLMResponseError: 模型返回异常。
            LLMConnectionError: 连接失败。
            LLMRateLimitError: 调用频率超限。
        """
        resolved_temp = (
            temperature if temperature is not None
            else self.settings.temperature
        )
        resolved_max_tokens = (
            max_tokens if max_tokens is not None
            else self.settings.max_tokens
        )

        extra_body: dict | None = (
            {"enable_thinking": True} if enable_thinking else None
        )

        try:
            stream = self.client.chat.completions.create(
                model=self.settings.model_name,
                messages=messages,
                temperature=resolved_temp,
                max_tokens=resolved_max_tokens,
                stream=True,
                **(
                    {"extra_body": extra_body}
                    if extra_body else {}
                ),
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    yield content
        except (APIConnectionError, APITimeoutError) as exc:
            raise LLMConnectionError(
                f"LLM 连接失败: {exc}"
            ) from exc
        except RateLimitError as exc:
            raise LLMRateLimitError(
                f"LLM 调用频率超限: {exc}"
            ) from exc
        except LLMResponseError:
            raise
        except Exception as exc:
            raise LLMResponseError(
                f"LLM 流式响应异常: {exc}"
            ) from exc

    def _call_with_retry(
        self,
        messages: list[ChatCompletionMessageParam],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        enable_thinking: bool = False,
    ) -> dict[str, str] | str:
        """带重试的 API 调用。

        最多重试 MAX_RETRIES 次，每次等待 RETRY_DELAYS 中对应秒数。

        Args:
            messages: 对话消息列表。
            temperature: 生成温度。
            max_tokens: 最大 token 数。
            enable_thinking: 是否启用深度思考。

        Returns:
            enable_thinking=False 时返回纯文本字符串；
            enable_thinking=True 时返回字典，包含 reasoning 和 content。

        Raises:
            LLMConnectionError: 重试耗尽后仍无法连接。
            LLMRateLimitError: 调用频率超限且重试失败。
            LLMResponseError: 模型返回空内容或格式异常。
        """
        resolved_temp = (
            temperature if temperature is not None
            else self.settings.temperature
        )
        resolved_max_tokens = (
            max_tokens if max_tokens is not None
            else self.settings.max_tokens
        )

        extra_body: dict | None = (
            {"enable_thinking": True} if enable_thinking else None
        )

        last_exception: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=self.settings.model_name,
                    messages=messages,
                    temperature=resolved_temp,
                    max_tokens=resolved_max_tokens,
                    **(
                        {"extra_body": extra_body}
                        if extra_body else {}
                    ),
                )

                if not response.choices:
                    raise LLMResponseError("模型未返回任何候选结果。")

                message = response.choices[0].message
                content = getattr(message, "content", None)

                if not content:
                    raise LLMResponseError("模型返回内容为空。")

                if enable_thinking:
                    reasoning = getattr(
                        message, "reasoning_content", None
                    ) or ""
                    return {
                        "reasoning": reasoning,
                        "content": content,
                    }

                return content

            except (APIConnectionError, APITimeoutError) as exc:
                last_exception = LLMConnectionError(
                    f"LLM 连接失败（第 {attempt + 1} 次）: {exc}"
                )
                console.print(
                    f"[yellow]⚠ 连接失败，"
                    f"{self.RETRY_DELAYS[attempt]}s 后重试"
                    f"（{attempt + 1}/{self.MAX_RETRIES}）[/yellow]"
                )
            except RateLimitError as exc:
                last_exception = LLMRateLimitError(
                    f"LLM 调用频率超限（第 {attempt + 1} 次）: {exc}"
                )
                console.print(
                    f"[yellow]⚠ 频率超限，"
                    f"{self.RETRY_DELAYS[attempt]}s 后重试"
                    f"（{attempt + 1}/{self.MAX_RETRIES}）[/yellow]"
                )
            except LLMResponseError as exc:
                last_exception = exc
                console.print(
                    f"[yellow]⚠ 响应异常: {exc}，"
                    f"{self.RETRY_DELAYS[attempt]}s 后重试"
                    f"（{attempt + 1}/{self.MAX_RETRIES}）[/yellow]"
                )
            except Exception as exc:
                last_exception = LLMResponseError(
                    f"未知错误（第 {attempt + 1} 次）: {exc}"
                )
                console.print(
                    f"[yellow]⚠ 未知错误: {exc}，"
                    f"{self.RETRY_DELAYS[attempt]}s 后重试"
                    f"（{attempt + 1}/{self.MAX_RETRIES}）[/yellow]"
                )

            if attempt < self.MAX_RETRIES - 1:
                time.sleep(self.RETRY_DELAYS[attempt])

        # 重试全部耗尽，抛出最后捕获的异常
        if isinstance(last_exception, LLMRateLimitError):
            raise last_exception
        if isinstance(last_exception, LLMConnectionError):
            raise last_exception
        raise LLMResponseError(
            f"重试 {self.MAX_RETRIES} 次后仍失败: {last_exception}"
        )
