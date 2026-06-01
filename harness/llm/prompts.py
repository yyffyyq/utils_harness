"""Prompt 模板管理模块。

集中管理所有与 Qwen3 交互使用的 System Prompt 与消息构建函数，
便于维护与版本迭代。
"""

# ---------------------------------------------------------------------------
# System Prompt 定义（V1 版本）
# ---------------------------------------------------------------------------

CONVERSATION_SYSTEM_PROMPT_V1: str = """\
你是 Harness —— 一个专业的项目规划助手。

你的核心任务是通过多轮对话，引导用户逐步完善项目的 AGENTS.md 规范文件。
在对话过程中，你需要系统地收集以下信息：

1. **项目名称与背景**
   - 项目定位、目标用户、核心功能概述

2. **技术栈选型**
   - 编程语言、框架、数据库、第三方服务等
   - 技术选型的理由（可选）

3. **代码规范要求**
   - 命名规范（文件、类、函数、变量）
   - 代码风格（缩进、行宽、格式化器）
   - 文档字符串风格（Google / NumPy / Sphinx）
   - 类型注解要求

4. **项目结构**
   - 目录布局规划
   - 模块职责划分

5. **错误处理与日志**
   - 异常类层级设计
   - 日志记录策略

6. **测试规范**
   - 测试框架、覆盖率目标
   - Mock 策略

7. **Git 与协作规范**
   - 分支策略、提交信息格式
   - Code Review 要求

请按以下原则进行对话：
- 每次只询问 1–2 个主题，避免一次性提出过多问题
- 对用户的回答进行简要复述确认，再引导下一话题
- 若用户跳过某项，给出合理默认建议并询问是否接受
- 当信息足够时，主动告知用户"可以生成 AGENTS.md 了"
"""

AGENTS_GENERATION_PROMPT_V1: str = """\
你是一名技术文档专家。

请基于以下对话摘要，生成一份完整的 AGENTS.md 规范文件（Markdown 格式）。

要求：
- 使用中文撰写
- 包含以下章节（可根据项目实际情况调整）：
  1. 项目背景（核心工作流、目标用户）
  2. 技术栈（表格形式列出类别、技术、说明）
  3. 代码规范（目录结构、命名规范、代码风格、示例代码）
  4. 错误处理
  5. Git 规范
  6. 测试规范
- 代码示例使用 Python，包含类型注解与 docstring
- 确保内容准确、可执行，不留模糊占位符

对话摘要：
{conversation_summary}
"""

PLAN_GENERATION_PROMPT_V1: str = """\
你是一名资深软件项目经理。

请基于以下 AGENTS.md 内容，生成一份详细的实施计划。

**重要：请严格以 JSON 格式输出，不要包含任何其他文本。**

JSON 结构如下：
{{
  "project_name": "项目名称",
  "overview": "计划总览描述（1-2句话）",
  "tasks": [
    {{
      "id": "task-01",
      "title": "任务标题",
      "description": "任务详细描述",
      "dependencies": [],
      "deliverables": ["file1.py", "file2.py"],
      "steps": "### 1.1 步骤一\\n说明\\n### 1.2 步骤二\\n说明",
      "acceptance_criteria": ["标准1", "标准2"],
      "complexity": "低"
    }}
  ],
  "milestones": ["M1 里程碑描述", "M2 里程碑描述"]
}}

要求：
- 将计划拆分为多个 task（task-01、task-02 …）
- 每个 task 包含 id、title、description、dependencies、deliverables、steps、acceptance_criteria、complexity
- task 之间有清晰的依赖关系，按实现顺序编号
- steps 字段为 Markdown 格式文本，包含具体到文件名、函数签名的步骤
- acceptance_criteria 为可量化、可测试的标准列表
- complexity 取值为 "低"、"中" 或 "高"

AGENTS.md 内容：
{agents_md_content}
"""

# ---------------------------------------------------------------------------
# 当前使用版本别名
# ---------------------------------------------------------------------------

CONVERSATION_SYSTEM_PROMPT: str = CONVERSATION_SYSTEM_PROMPT_V1
AGENTS_GENERATION_PROMPT: str = AGENTS_GENERATION_PROMPT_V1
PLAN_GENERATION_PROMPT: str = PLAN_GENERATION_PROMPT_V1

# ---------------------------------------------------------------------------
# Prompt 构建函数
# ---------------------------------------------------------------------------


def build_conversation_prompt(
    user_input: str,
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """构建多轮对话的消息列表。

    将系统提示词、历史对话与当前用户输入组装为 OpenAI 格式的消息列表。

    Args:
        user_input: 用户当前输入的文本。
        history: 历史对话记录，每条包含 role 和 content。
            为 None 或空列表时表示对话刚开始。

    Returns:
        OpenAI 消息列表，格式为 [{"role": ..., "content": ...}, ...]。
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": CONVERSATION_SYSTEM_PROMPT},
    ]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": user_input})
    return messages


def build_agents_generation_prompt(
    conversation_summary: str,
) -> list[dict[str, str]]:
    """构建 AGENTS.md 生成的消息列表。

    Args:
        conversation_summary: 对话内容的摘要或完整记录，
            供模型理解项目背景并生成规范文档。

    Returns:
        OpenAI 消息列表，包含 system 提示与 user 请求。
    """
    user_content = AGENTS_GENERATION_PROMPT.format(
        conversation_summary=conversation_summary,
    )
    return [
        {
            "role": "system",
            "content": "你是一名专业的技术文档撰写专家，擅长输出结构清晰的 Markdown 规范文件。",
        },
        {"role": "user", "content": user_content},
    ]


def build_plan_generation_prompt(
    agents_md_content: str,
) -> list[dict[str, str]]:
    """构建计划生成的消息列表。

    Args:
        agents_md_content: AGENTS.md 文件的完整内容，
            供模型理解项目规范并生成实施计划。

    Returns:
        OpenAI 消息列表，包含 system 提示与 user 请求。
    """
    user_content = PLAN_GENERATION_PROMPT.format(
        agents_md_content=agents_md_content,
    )
    return [
        {
            "role": "system",
            "content": "你是一名资深软件项目经理，擅长将规范文档拆解为可执行的任务计划。",
        },
        {"role": "user", "content": user_content},
    ]
