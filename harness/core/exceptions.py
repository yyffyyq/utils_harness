"""Harness 自定义异常类。"""


class HarnessError(Exception):
    """Harness 基础异常。"""


class LLMConnectionError(HarnessError):
    """LLM 连接失败。"""


class LLMResponseError(HarnessError):
    """LLM 响应异常（空内容、格式错误等）。"""


class LLMRateLimitError(HarnessError):
    """LLM 调用频率超限。"""
