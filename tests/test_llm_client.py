"""task-02 LLM 客户端单元测试。"""

from unittest.mock import MagicMock, patch

import pytest

from harness.core.exceptions import (
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseError,
)
from harness.llm.client import QwenClient
from harness.utils.config import Settings


@pytest.fixture
def settings() -> Settings:
    """创建测试用配置实例。"""
    return Settings(
        qwen_api_key="test-api-key",
        qwen_base_url="https://test.example.com/v1",
        model_name="qwen3.6-plus",
        max_tokens=100,
        temperature=0.7,
    )


@pytest.fixture
def client(settings: Settings) -> QwenClient:
    """创建测试用客户端实例。"""
    return QwenClient(settings)


def _make_message(content: str) -> list[dict]:
    """构造单条用户消息。"""
    return [{"role": "user", "content": content}]


class TestQwenClientImport:
    """验证模块导入。"""

    def test_import_qwen_client(self) -> None:
        """QwenClient 可从 harness.llm 导入。"""
        from harness.llm import QwenClient as QC

        assert QC is QwenClient

    def test_client_has_max_retries(self, client: QwenClient) -> None:
        """客户端配置了 3 次最大重试。"""
        assert client.MAX_RETRIES == 3
        assert client.RETRY_DELAYS == [1, 2, 4]


class TestChatMethod:
    """chat() 方法测试（使用 mock）。"""

    @patch("harness.llm.client.time.sleep")
    def test_chat_returns_text(
        self, mock_sleep: MagicMock, client: QwenClient
    ) -> None:
        """普通调用返回字符串文本。"""
        mock_message = MagicMock()
        mock_message.content = "你好！"
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_message)]

        client.client.chat.completions.create = MagicMock(
            return_value=mock_response
        )

        result = client.chat(_make_message("你好"))
        assert isinstance(result, str)
        assert result == "你好！"

    @patch("harness.llm.client.time.sleep")
    def test_chat_with_enable_thinking_returns_dict(
        self, mock_sleep: MagicMock, client: QwenClient
    ) -> None:
        """enable_thinking=True 时返回包含 reasoning 和 content 的字典。"""
        mock_message = MagicMock()
        mock_message.content = "最终答案"
        mock_message.reasoning_content = "让我想想..."
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_message)]

        client.client.chat.completions.create = MagicMock(
            return_value=mock_response
        )

        result = client.chat(
            _make_message("分析这个问题"),
            enable_thinking=True,
        )
        assert isinstance(result, dict)
        assert result["content"] == "最终答案"
        assert result["reasoning"] == "让我想想..."

    @patch("harness.llm.client.time.sleep")
    def test_chat_with_enable_thinking_no_reasoning(
        self, mock_sleep: MagicMock, client: QwenClient
    ) -> None:
        """enable_thinking=True 但无 reasoning_content 时，reasoning 为空串。"""
        mock_message = MagicMock(spec=["content"])
        mock_message.content = "答案"
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_message)]

        client.client.chat.completions.create = MagicMock(
            return_value=mock_response
        )

        result = client.chat(
            _make_message("问题"),
            enable_thinking=True,
        )
        assert isinstance(result, dict)
        assert result["content"] == "答案"
        assert result["reasoning"] == ""

    @patch("harness.llm.client.time.sleep")
    def test_chat_empty_choices_raises(
        self, mock_sleep: MagicMock, client: QwenClient
    ) -> None:
        """模型返回空 choices 时抛出 LLMResponseError。"""
        mock_response = MagicMock()
        mock_response.choices = []

        client.client.chat.completions.create = MagicMock(
            return_value=mock_response
        )

        with pytest.raises(LLMResponseError, match="候选结果"):
            client.chat(_make_message("测试"))

    @patch("harness.llm.client.time.sleep")
    def test_chat_empty_content_raises(
        self, mock_sleep: MagicMock, client: QwenClient
    ) -> None:
        """模型返回空 content 时抛出 LLMResponseError。"""
        mock_message = MagicMock()
        mock_message.content = ""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_message)]

        client.client.chat.completions.create = MagicMock(
            return_value=mock_response
        )

        with pytest.raises(LLMResponseError, match="内容为空"):
            client.chat(_make_message("测试"))

    @patch("harness.llm.client.time.sleep")
    def test_chat_passes_enable_thinking_extra_body(
        self, mock_sleep: MagicMock, client: QwenClient
    ) -> None:
        """enable_thinking=True 时传递 extra_body 参数。"""
        mock_message = MagicMock()
        mock_message.content = "ok"
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_message)]

        mock_create = MagicMock(return_value=mock_response)
        client.client.chat.completions.create = mock_create

        client.chat(_make_message("问题"), enable_thinking=True)

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["extra_body"] == {"enable_thinking": True}

    @patch("harness.llm.client.time.sleep")
    def test_chat_no_extra_body_when_thinking_disabled(
        self, mock_sleep: MagicMock, client: QwenClient
    ) -> None:
        """enable_thinking=False 时不传递 extra_body。"""
        mock_message = MagicMock()
        mock_message.content = "ok"
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_message)]

        mock_create = MagicMock(return_value=mock_response)
        client.client.chat.completions.create = mock_create

        client.chat(_make_message("问题"), enable_thinking=False)

        call_kwargs = mock_create.call_args[1]
        assert "extra_body" not in call_kwargs


class TestRetryMechanism:
    """重试机制测试。"""

    @patch("harness.llm.client.time.sleep")
    def test_retry_on_connection_error(
        self, mock_sleep: MagicMock, client: QwenClient
    ) -> None:
        """连接失败时重试 3 次后抛出 LLMConnectionError。"""
        from openai import APIConnectionError

        client.client.chat.completions.create = MagicMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with pytest.raises(LLMConnectionError):
            client.chat(_make_message("测试"))

        assert client.client.chat.completions.create.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    @patch("harness.llm.client.time.sleep")
    def test_retry_on_rate_limit_error(
        self, mock_sleep: MagicMock, client: QwenClient
    ) -> None:
        """频率超限时重试 3 次后抛出 LLMRateLimitError。"""
        from openai import RateLimitError

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        client.client.chat.completions.create = MagicMock(
            side_effect=RateLimitError(
                "rate limit",
                response=mock_response,
                body=None,
            )
        )

        with pytest.raises(LLMRateLimitError):
            client.chat(_make_message("测试"))

        assert client.client.chat.completions.create.call_count == 3

    @patch("harness.llm.client.time.sleep")
    def test_retry_succeeds_on_second_attempt(
        self, mock_sleep: MagicMock, client: QwenClient
    ) -> None:
        """第一次失败、第二次成功时正常返回结果。"""
        from openai import APIConnectionError

        mock_message = MagicMock()
        mock_message.content = "成功了"
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_message)]

        client.client.chat.completions.create = MagicMock(
            side_effect=[
                APIConnectionError(request=MagicMock()),
                mock_response,
            ]
        )

        result = client.chat(_make_message("测试"))
        assert result == "成功了"
        assert client.client.chat.completions.create.call_count == 2
        mock_sleep.assert_called_once_with(1)


class TestChatStreamMethod:
    """chat_stream() 流式调用测试。"""

    def test_stream_yields_content_chunks(
        self, client: QwenClient
    ) -> None:
        """流式调用逐块 yield 文本内容。"""
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "你好"

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = "世界"

        chunk3 = MagicMock()
        chunk3.choices = []  # 空 choices 应被跳过

        client.client.chat.completions.create = MagicMock(
            return_value=iter([chunk1, chunk2, chunk3])
        )

        result = list(client.chat_stream(_make_message("测试")))
        assert result == ["你好", "世界"]

    def test_stream_raises_on_connection_error(
        self, client: QwenClient
    ) -> None:
        """流式调用连接失败时抛出 LLMConnectionError。"""
        from openai import APIConnectionError

        client.client.chat.completions.create = MagicMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with pytest.raises(LLMConnectionError):
            list(client.chat_stream(_make_message("测试")))

    def test_stream_raises_on_rate_limit(
        self, client: QwenClient
    ) -> None:
        """流式调用频率超限时抛出 LLMRateLimitError。"""
        from openai import RateLimitError

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        client.client.chat.completions.create = MagicMock(
            side_effect=RateLimitError(
                "rate limit",
                response=mock_response,
                body=None,
            )
        )

        with pytest.raises(LLMRateLimitError):
            list(client.chat_stream(_make_message("测试")))

    def test_stream_passes_enable_thinking(
        self, client: QwenClient
    ) -> None:
        """流式调用 enable_thinking=True 时传递 extra_body。"""
        client.client.chat.completions.create = MagicMock(
            return_value=iter([])
        )

        list(client.chat_stream(
            _make_message("测试"),
            enable_thinking=True,
        ))

        call_kwargs = client.client.chat.completions.create.call_args[1]
        assert call_kwargs["stream"] is True
        assert call_kwargs["extra_body"] == {"enable_thinking": True}
