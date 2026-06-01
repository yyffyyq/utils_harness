# Task 03 - Prompt 模板管理

## 目标

集中管理所有与 Qwen3 交互使用的 Prompt 模板，便于维护与迭代。

## 依赖

- task-02（LLM 客户端）

## 交付物

- `llm/prompts.py` - Prompt 模板定义

## 详细步骤

### 3.1 定义 System Prompt

为不同场景定义系统提示词：

```python
# 对话引导 Prompt - 用于多轮对话阶段
CONVERSATION_SYSTEM_PROMPT = """你是一个专业的项目规划助手。
你的任务是通过对话引导用户完善项目的 AGENTS.md 文件。
你需要收集以下信息：
1. 项目名称与背景
2. 技术栈选型
3. 代码规范要求
...
"""

# AGENTS.md 生成 Prompt
AGENTS_GENERATION_PROMPT = """基于以下对话内容，生成完整的 AGENTS.md 文件..."""

# 计划生成 Prompt
PLAN_GENERATION_PROMPT = """基于以下 AGENTS.md 内容，生成详细的实施计划..."""
```

### 3.2 定义 Prompt 构建函数

```python
def build_conversation_prompt(user_input: str, history: list[dict]) -> list[dict]:
    """构建多轮对话的消息列表。"""

def build_agents_generation_prompt(conversation_summary: str) -> list[dict]:
    """构建 AGENTS.md 生成的消息列表。"""

def build_plan_generation_prompt(agents_md_content: str) -> list[dict]:
    """构建计划生成的消息列表。"""
```

### 3.3 Prompt 版本管理

- 使用常量命名区分不同版本（如 `CONVERSATION_SYSTEM_PROMPT_V1`）
- 当前使用的版本通过变量别名引用

## 验收标准

- [x] 所有 Prompt 集中在 `llm/prompts.py` 中
- [x] Prompt 构建函数可正确组装消息列表
- [x] 无硬编码的 Prompt 散落在其他模块中
- [x] 20 个单元测试全部通过（pytest 4.85s）
