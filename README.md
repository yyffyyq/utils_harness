# Harness

> AI 辅助项目规划工具 —— 通过终端多轮对话生成 `AGENTS.md` 规范文件与实施计划。

Harness 利用 Qwen3 大模型，通过自然语言对话的方式引导你完善项目描述，自动生成标准化的 AGENTS.md 文档，并基于文档内容拆解出可执行的实施计划。

## ✨ 功能特性

- **多轮对话引导** — AI 主动提问，逐步收集项目背景、技术栈、代码规范等信息
- **AGENTS.md 自动生成** — 基于对话内容生成包含项目背景、技术栈、代码规范的规范文档
- **实施计划自动拆解** — 将 AGENTS.md 拆解为多个可执行任务，明确依赖关系与验收标准
- **双层记忆优化** — 滚动窗口摘要 + 结构化事实提取，上下文 Token O(1) 恒定
- **终端美化输出** — Rich 渲染 Markdown、表格、Spinner 加载动画
- **审阅与修改** — 生成内容支持终端预览、用户反馈修改、重新生成
- **一键保存** — AGENTS.md 与计划文件批量保存到本地

## 🚀 快速开始

### 1. 安装

```bash
# 克隆项目
git clone https://github.com/yyffyyq/utils_harness.git
cd utils_harness

# 安装（含开发依赖）
pip install -e ".[dev]"
```

### 2. 配置 API Key

Harness 使用 Qwen3 大模型，需要配置 API Key。

**方式一：环境变量**

```bash
# Linux / macOS
export HARNESS_QWEN_API_KEY="your-api-key"

# Windows PowerShell
$env:HARNESS_QWEN_API_KEY = "your-api-key"
```

**方式二：.env 文件（推荐）**

在项目根目录创建 `.env` 文件：

```ini
HARNESS_QWEN_API_KEY=your-api-key
```

> Qwen3 API Key 可在 [阿里云 DashScope](https://dashscope.console.aliyun.com/) 获取。

### 3. 运行

```bash
# 安装后可直接使用命令行
harness

# 或指定输出目录
harness -o ./my-project

# 也可以用 Python 模块方式运行
python -m harness.cli.main -o ./my-project
```

## 📖 使用手册

### 启动对话

运行 `harness` 后，你会看到欢迎面板：

```
╭───────────────────── 欢迎 ─────────────────────╮
│ Harness - AI 辅助项目规划工具                     │
│                                                  │
│ 通过对话生成 AGENTS.md 规范文件与实施计划。       │
│                                                  │
│ 可用命令：                                       │
│   /generate  - 强制生成 AGENTS.md                │
│   /help      - 显示帮助                          │
│   /quit      - 退出对话                          │
╰──────────────────────────────────────────────────╯
```

### 对话阶段

在 `你:` 提示符后描述你的项目信息，AI 会逐步引导你补充：

```
你: 我想做一个个人博客项目，用于展示技术文章
[AI] 好的，请问您计划使用什么技术栈？...

你: 技术栈用 Vue3 + Vite + TypeScript
[AI] 收到，代码规范方面有什么要求吗？...

你: ESLint + Prettier，组件用 PascalCase
[AI] 信息已收集完毕，可以生成 AGENTS.md 了。
```

**建议提供的信息：**

| 类别 | 示例 |
|------|------|
| 项目名称与背景 | "个人博客，展示技术文章和作品" |
| 技术栈 | "Vue3 + Vite + TypeScript" |
| 代码规范 | "ESLint + Prettier，PascalCase 组件" |
| 项目结构 | "src/views, src/components, src/assets" |
| 核心功能 | "文章列表、详情页、暗色主题" |
| 测试与 Git | "Vitest 测试，feat(scope) 提交" |

### 对话命令

在对话过程中可以使用以下命令：

| 命令 | 说明 |
|------|------|
| `/generate` | 强制结束对话，进入 AGENTS.md 生成阶段 |
| `/help` | 显示可用命令帮助 |
| `/quit` | 退出对话，不生成任何文件 |

> **提示：** 当 AI 回复中提到"信息已充足"或"可以生成"时，直接输入 `/generate` 即可。

### 审阅 AGENTS.md

AI 生成 AGENTS.md 后会展示预览，你可以选择：

| 输入 | 操作 |
|------|------|
| `y` | 确认内容，进入计划生成阶段 |
| `e` | 提供修改意见（如"加上部署说明"），AI 修改后重新展示 |
| `r` | 完全重新生成 |
| `q` | 退出，不继续 |

### 审阅实施计划

AGENTS.md 确认后，AI 会基于内容生成实施计划，以表格展示：

```
┌─────────── Harness辅助规划工具 实施计划 ───────────┐
│ 序号 │ 任务          │ 依赖      │ 复杂度 │       │
│   1  │ 项目初始化     │ -         │ 低     │       │
│   2  │ 路由配置       │ task-01   │ 中     │       │
│   3  │ 页面组件开发   │ task-02   │ 高     │       │
│   ...│               │           │        │       │
└────────────────────────────────────────────────────┘
```

同样选择 `y` 确认保存，或 `e` / `r` / `q` 进行调整。

### 保存文件

确认后，文件自动保存到输出目录：

```
my-project/
└── doc/
    ├── AGENTS.md          # 项目规范文档
    └── plan/
        ├── README.md      # 计划总览
        ├── task-01-xxx.md # 任务详情
        ├── task-02-xxx.md
        └── ...
```

## 🏗️ 技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.10+ | 主开发语言 |
| CLI | Typer + Rich | 命令解析 + 终端美化 |
| LLM | OpenAI SDK | 兼容 Qwen3 API |
| 配置 | Pydantic Settings | 环境变量 / .env 管理 |
| 模板 | Jinja2 | Markdown 模板渲染 |
| 测试 | pytest + pytest-mock | 单元测试 + 集成测试 |

## 📁 项目结构

```
harness/
├── cli/
│   ├── __init__.py
│   └── main.py           # Typer CLI 主入口
├── core/
│   ├── __init__.py
│   ├── conversation.py   # 多轮对话管理器
│   ├── generator.py      # AGENTS.md 生成器
│   ├── planner.py        # 实施计划生成器
│   └── exceptions.py     # 自定义异常
├── llm/
│   ├── __init__.py
│   ├── client.py         # Qwen3 API 客户端
│   └── prompts.py        # Prompt 模板管理
├── templates/
│   ├── agents_md.j2      # AGENTS.md 模板
│   ├── plan.j2           # 任务计划模板
│   └── plan_readme.j2    # 计划总览模板
└── utils/
    ├── __init__.py
    ├── config.py          # 配置加载
    └── file_ops.py        # 文件操作工具
```

## 🔧 配置参数

通过环境变量（前缀 `HARNESS_`）或 `.env` 文件配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HARNESS_QWEN_API_KEY` | `""` | Qwen3 API 密钥（必填） |
| `HARNESS_QWEN_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | API 端点 |
| `HARNESS_MODEL_NAME` | `qwen3.6-plus` | 模型名称 |
| `HARNESS_MAX_TOKENS` | `4096` | 单次最大 token 数 |
| `HARNESS_TEMPERATURE` | `0.7` | 生成温度 |

## 🧪 测试

```bash
# 运行全部测试
pytest

# 带覆盖率
pytest --cov=harness --cov-report=term-missing

# 运行特定模块
pytest tests/test_cli.py -v
```

当前测试状态：**180 个测试，覆盖率 91%**

## 📄 License

MIT
