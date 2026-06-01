"""Harness 自定义异常类。"""


class HarnessError(Exception):
    """Harness 基础异常。"""


class LLMConnectionError(HarnessError):
    """LLM 连接失败。"""


class LLMResponseError(HarnessError):
    """LLM 响应异常（空内容、格式错误等）。"""


class LLMRateLimitError(HarnessError):
    """LLM 调用频率超限。"""


class ConversationError(HarnessError):
    """对话管理器异常。"""


class ConversationMaxRoundsError(ConversationError):
    """对话轮次已达上限。"""


class GeneratorError(HarnessError):
    """AGENTS.md / 计划生成异常。"""


class ValidationError(GeneratorError):
    """生成内容校验失败。"""


class PlanError(HarnessError):
    """计划生成与管理异常。"""


class PlanParseError(PlanError):
    """LLM 返回的计划数据解析失败。"""
