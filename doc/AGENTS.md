# AGENTS.md - Harness 辅助规划工具

## 项目背景

Harness 是一个命令行辅助规划工具，旨在帮助开发者通过**自然语言对话**的方式，逐步完善并生成项目的 `AGENTS.md` 规范文件。在用户确认 `AGENTS.md` 内容后，AI 将基于该文件自动生成实施计划（Plan），并保存到项目中。

### 核心工作流

1. 用户启动工具，进入终端多轮对话模式
2. AI 通过提问引导用户描述项目背景、技术栈、代码规范等信息
3. AI 根据对话内容生成 `AGENTS.md` 初稿，用户在终端中预览并确认/修改
4. 用户确认后，AI 基于 `AGENTS.md` 内容生成实施计划
5. 用户确认计划后，工具将 `AGENTS.md` 和 `plan/` 文件夹（含 Markdown 计划文件）保存到指定目录

### 目标用户

- 需要快速搭建项目规范的开发者和团队
- 希望通过 AI 辅助完成项目规划文档的技术负责人

---

## 技术栈

| 类别         | 技术选型                          | 说明                                    |
| ------------ | --------------------------------- | --------------------------------------- |
| 语言         | Python 3.10+                      | 主开发语言                              |
| CLI 框架     | [Rich](https://github.com/Textualize/rich) + [Typer](https://github.com/tiangolo/typer) | Rich 负责终端美化输出，Typer 负责命令解析 |
| LLM 调用     | OpenAI SDK (兼容 Qwen3 API)       | 通过 OpenAI 兼容接口调用 Qwen3 模型     |
| 模型         | Qwen3                             | 阿里云通义千问，用于对话生成与计划推理   |
| 配置管理     | Pydantic Settings                 | 管理 API Key、模型参数等配置             |
| 模板引擎     | Jinja2                            | 用于 AGENTS.md 和计划文件的模板渲染      |
| 文件操作     | pathlib (标准库)                   | 文件和目录的读写操作                     |
| 测试         | pytest                            | 单元测试与集成测试                       |

### 依赖清单（核心）

```
typer>=0.9.0
rich>=13.0.0
openai>=1.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
jinja2>=3.1.0
```

---

## 代码规范

### 项目结构

```
harness/
├── cli/                  # CLI 入口与命令定义
│   ├── __init__.py
│   └── main.py           # Typer 应用主入口
├── core/                 # 核心业务逻辑
│   ├── __init__.py
│   ├── conversation.py   # 多轮对话管理
│   ├── generator.py      # AGENTS.md 生成逻辑
│   └── planner.py        # 计划生成与管理
├── llm/                  # LLM 调用封装
│   ├── __init__.py
│   ├── client.py         # Qwen3 API 客户端
│   └── prompts.py        # Prompt 模板管理
├── templates/            # Jinja2 模板文件
│   ├── agents_md.j2      # AGENTS.md 模板
│   └── plan.j2           # 计划文件模板
├── utils/                # 工具函数
│   ├── __init__.py
│   ├── config.py         # 配置加载
│   └── file_ops.py       # 文件读写操作
├── tests/                # 测试
│   ├── test_conversation.py
│   ├── test_generator.py
│   └── test_planner.py
├── pyproject.toml        # 项目配置与依赖
└── README.md
```

### 命名规范

- **文件名**：小写 + 下划线（snake_case），如 `conversation.py`
- **类名**：大驼峰（PascalCase），如 `ConversationManager`
- **函数/变量名**：小写 + 下划线（snake_case），如 `generate_agents_md`
- **常量**：全大写 + 下划线，如 `MAX_RETRY_COUNT`
- **模块级私有**：单下划线前缀，如 `_internal_helper`

### 代码风格

- 遵循 **PEP 8** 规范
- 使用 **type hints** 标注所有函数参数和返回值类型
- 使用 **docstring**（Google 风格）描述所有公开函数和类
- 单行不超过 **88 字符**（兼容 Black 格式化器）
- 使用 **f-string** 进行字符串格式化

### 示例

```python
from pathlib import Path

from rich.console import Console

console = Console()


class ConversationManager:
    """管理用户多轮对话的上下文与状态。"""

    def __init__(self, max_rounds: int = 10) -> None:
        self.max_rounds = max_rounds
        self.history: list[dict[str, str]] = []

    def add_message(self, role: str, content: str) -> None:
        """添加一条对话消息。

        Args:
            role: 消息角色，'user' 或 'assistant'。
            content: 消息内容。
        """
        self.history.append({"role": role, "content": content})

    def is_complete(self) -> bool:
        """判断对话是否已完成所有轮次。"""
        return len(self.history) >= self.max_rounds * 2
```

### 错误处理

- 使用自定义异常类，继承自 `Exception`，统一放在 `core/exceptions.py`
- LLM 调用失败时进行 **3 次重试**，间隔递增（1s, 2s, 4s）
- 所有用户输入进行基础校验，给出友好的终端提示
- 文件写入前检查目标目录权限，失败时明确提示

### Git 规范

- 分支命名：`feat/xxx`、`fix/xxx`、`docs/xxx`
- 提交信息格式：`<type>(<scope>): <description>`
  - 例：`feat(cli): add init command for project setup`
- 每个功能一个 PR，附简要说明

### 测试规范

- 核心模块（`core/`、`llm/`）覆盖率不低于 **80%**
- 使用 `pytest` + `pytest-mock` 进行单元测试
- LLM 调用使用 mock，避免测试依赖真实 API
- 测试文件与源文件同名，前缀 `test_`
