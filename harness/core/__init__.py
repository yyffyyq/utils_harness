"""核心业务逻辑模块。"""

# 延迟导入避免循环依赖:
#   llm.__init__ → llm.client → core.exceptions
#   core.__init__ → core.conversation → llm.client (循环!)
# 改为通过 from harness.core import ... 按需导入


def __getattr__(name: str):  # type: ignore[misc]
    """按需导入，避免循环依赖。"""
    if name in (
        "ConversationManager",
        "ConversationPhase",
    ):
        from .conversation import (
            ConversationManager,
            ConversationPhase,
        )

        return (
            ConversationManager
            if name == "ConversationManager"
            else ConversationPhase
        )
    if name == "AgentsGenerator":
        from .generator import AgentsGenerator

        return AgentsGenerator
    if name in ("PlanGenerator", "Plan", "TaskItem"):
        from . import planner

        return getattr(planner, name)
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )


__all__ = [
    "ConversationManager",
    "ConversationPhase",
    "AgentsGenerator",
    "PlanGenerator",
    "Plan",
    "TaskItem",
]