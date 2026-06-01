# Task 01 - 项目初始化与基础配置

## 目标

搭建 Harness 项目骨架，配置开发环境与依赖管理。

## 交付物

- `pyproject.toml` 项目配置文件
- 完整的目录结构（所有 `__init__.py`）
- `.gitignore` 文件
- 虚拟环境与依赖安装

## 详细步骤

### 1.1 创建项目目录结构

```
harness/
├── cli/
│   └── __init__.py
├── core/
│   └── __init__.py
├── llm/
│   └── __init__.py
├── templates/
├── utils/
│   └── __init__.py
├── tests/
│   └── __init__.py
└── pyproject.toml
```

### 1.2 编写 pyproject.toml

- 使用 `[project]` 标准格式
- 声明所有核心依赖：
  - `typer>=0.9.0`
  - `rich>=13.0.0`
  - `openai>=1.0.0`
  - `pydantic>=2.0.0`
  - `pydantic-settings>=2.0.0`
  - `jinja2>=3.1.0`
- 声明开发依赖：
  - `pytest>=7.0.0`
  - `pytest-mock>=3.10.0`
  - `black`（代码格式化）
  - `ruff`（代码检查）
- 配置入口点：`harness = "cli.main:app"`

### 1.3 配置 .gitignore

- Python 标准忽略（`__pycache__`、`.pyc`、`.venv`）
- IDE 忽略（`.idea`、`.vscode`）
- 环境变量文件 `.env`

### 1.4 编写配置加载模块

文件：`utils/config.py`

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，从环境变量或 .env 文件加载。"""

    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model_name: str = "qwen3-235b-a22b"
    max_tokens: int = 4096
    temperature: float = 0.7

    model_config = {"env_file": ".env", "env_prefix": "HARNESS_"}
```

## 验收标准

- [x] `pip install -e .` 可正常安装
- [x] `from harness.utils.config import Settings` 可正常导入
- [x] 所有目录和 `__init__.py` 已就位
- [x] `.gitignore` 覆盖常见忽略项
- [x] 8 个单元测试全部通过（pytest 0.75s）
