# Task 09 - CLI 主入口与命令定义

## 目标

使用 Typer 实现 CLI 主入口，串联所有核心模块，提供完整的终端交互体验。

## 依赖

- task-04（多轮对话管理器）
- task-05（AGENTS.md 生成器）
- task-06（计划生成器）
- task-08（文件操作工具）

## 交付物

- `cli/main.py` - Typer 应用主入口

## 详细步骤

### 9.1 定义 CLI 命令

```python
import typer
from rich.console import Console

app = typer.Typer(
    name="harness",
    help="Harness - AI 辅助项目规划工具",
    add_completion=False,
)

console = Console()


@app.command()
def init(
    output_dir: str = typer.Option(
        ".", "--output", "-o", help="输出目录路径"
    ),
) -> None:
    """启动 Harness，通过对话生成 AGENTS.md 和实施计划。"""
    ...
```

### 9.2 主流程编排

`init` 命令执行流程：

```
1. 加载配置（Settings）
   ├── 检查 API Key 是否配置
   └── 未配置则提示用户设置环境变量

2. 进入多轮对话（ConversationManager）
   ├── 循环获取用户输入
   ├── 调用 LLM 获取 AI 响应
   └── 直到信息收集完毕或用户退出

3. 生成 AGENTS.md（AgentsGenerator）
   ├── 调用 LLM 生成初稿
   ├── Rich 渲染展示
   └── 用户确认/修改循环

4. 生成实施计划（PlanGenerator）
   ├── 调用 LLM 生成计划
   ├── Rich 表格展示
   └── 用户确认/修改循环

5. 保存文件（FileOps）
   ├── 写入 AGENTS.md
   ├── 创建 plan/ 目录
   └── 写入各计划文件

6. 完成提示
```

### 9.3 终端交互细节

- 启动时展示欢迎信息与使用说明
- 对话中用 Rich Panel 区分用户输入与 AI 响应
- 生成阶段展示 Spinner 加载动画
- 保存完成后展示文件清单与路径

### 9.4 错误处理

- API Key 未配置：提示设置 `HARNESS_QWEN_API_KEY` 环境变量
- LLM 调用失败：展示友好错误信息，提供重试选项
- 文件写入失败：展示具体错误，不丢失已生成内容（打印到终端）

## 验收标准

- [x] `harness init` 命令可正常启动
- [x] 完整流程可跑通（对话 → 生成 → 计划 → 保存）
- [x] 各阶段终端输出美观、信息清晰
- [x] 错误场景均有友好处理
- [x] 13 个单元测试全部通过（总计 158 passed / 11.85s）
