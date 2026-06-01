"""Harness CLI 主入口。

使用 Typer 实现命令行入口，串联所有核心模块：
ConversationManager → AgentsGenerator → PlanGenerator → FileOps
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live

from harness.core.exceptions import (
    ConversationMaxRoundsError,
    GeneratorError,
    HarnessError,
    PlanError,
)
from harness.utils.config import Settings
from harness.utils.file_ops import FileOps
from harness.llm.client import QwenClient
from harness.core.conversation import ConversationManager
from harness.core.generator import AgentsGenerator
from harness.core.planner import PlanGenerator

app = typer.Typer(
    name="harness",
    help="Harness - AI 辅助项目规划工具",
    add_completion=False,
)

console = Console()

# 欢迎面板
_WELCOME_BANNER: str = """\
[bold cyan]Harness[/bold cyan] - AI 辅助项目规划工具

通过对话生成 [green]AGENTS.md[/green] 规范文件与实施计划。

[bold]可用命令：[/bold]
  [cyan]/generate[/cyan]  - 强制生成 AGENTS.md
  [cyan]/help[/cyan]      - 显示帮助
  [cyan]/quit[/cyan]      - 退出对话
"""


def _check_api_key(settings: Settings) -> bool:
    """检查 API Key 是否已配置。

    Args:
        settings: 应用配置。

    Returns:
        API Key 是否有效（非空）。
    """
    if not settings.qwen_api_key:
        console.print(
            Panel(
                "未配置 Qwen API Key！\n\n"
                "请设置环境变量：\n"
                "  [cyan]export HARNESS_QWEN_API_KEY="
                "your-api-key[/cyan]\n\n"
                "或在项目根目录创建 [green].env[/green]"
                " 文件：\n"
                "  [cyan]HARNESS_QWEN_API_KEY="
                "your-api-key[/cyan]",
                title="配置错误",
                border_style="red",
            )
        )
        return False
    return True


def _phase_conversation(client: QwenClient) -> str | None:
    """阶段一：多轮对话收集信息。

    Args:
        client: LLM 客户端。

    Returns:
        对话摘要字符串；用户退出时返回 None。
    """
    cm = ConversationManager(client)
    console.print(
        Panel(
            Markdown(_WELCOME_BANNER),
            border_style="cyan",
            title="欢迎",
        )
    )

    while True:
        try:
            user_input = typer.prompt(
                typer.style("你", fg=typer.colors.GREEN)
            )
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]已中断对话[/yellow]")
            return None

        if not user_input.strip():
            continue

        try:
            response = cm.process_input(user_input)
        except ConversationMaxRoundsError as exc:
            console.print(
                f"[yellow]{exc}[/yellow]"
            )
            summary = cm.get_conversation_summary()
            return summary
        except HarnessError as exc:
            console.print(
                f"[red]对话异常: {exc}[/red]"
            )
            continue

        cm.render_response(response)
        cm.render_status()

        if cm.should_quit:
            console.print(
                "[dim]已退出对话，未生成文档。[/dim]"
            )
            return None

        if cm.is_collection_complete():
            console.print(
                "\n[green]信息收集完毕，"
                "准备生成 AGENTS.md...[/green]"
            )
            summary = cm.get_conversation_summary()
            return summary


def _phase_agents(
    client: QwenClient,
    summary: str,
) -> str | None:
    """阶段二：生成并审阅 AGENTS.md。

    Args:
        client: LLM 客户端。
        summary: 对话摘要。

    Returns:
        确认后的 AGENTS.md 内容；用户退出时返回 None。
    """
    gen = AgentsGenerator(client)

    console.print()
    with Live(
        Spinner("dots", text="正在生成 AGENTS.md..."),
        console=console,
        transient=True,
    ):
        try:
            content = gen.generate(summary)
        except GeneratorError as exc:
            console.print(
                f"[red]生成失败: {exc}[/red]"
            )
            return None

    gen.render_preview(content)
    missing = gen.validate(content)
    if missing:
        console.print(
            f"[yellow]⚠ 缺少章节: "
            f"{', '.join(missing)}[/yellow]"
        )

    # 审阅循环
    while True:
        choice = typer.prompt(
            "确认？[y]保存 / [e]修改 / "
            "[r]重新生成 / [q]退出",
            default="y",
        ).strip().lower()

        if choice == "y":
            return content
        elif choice == "e":
            feedback = typer.prompt("修改意见")
            with Live(
                Spinner(
                    "dots",
                    text="正在修改...",
                ),
                console=console,
                transient=True,
            ):
                try:
                    content = gen.regenerate(
                        feedback, content
                    )
                except GeneratorError as exc:
                    console.print(
                        f"[red]修改失败: {exc}[/red]"
                    )
                    continue
            gen.render_preview(content)
        elif choice == "r":
            with Live(
                Spinner(
                    "dots",
                    text="正在重新生成...",
                ),
                console=console,
                transient=True,
            ):
                try:
                    content = gen.generate(summary)
                except GeneratorError as exc:
                    console.print(
                        f"[red]生成失败: {exc}[/red]"
                    )
                    continue
            gen.render_preview(content)
        elif choice == "q":
            console.print("[dim]已取消。[/dim]")
            return None
        else:
            console.print(
                "[yellow]请输入 y/e/r/q[/yellow]"
            )


def _phase_plan(
    client: QwenClient,
    agents_md: str,
) -> tuple:
    """阶段三：生成并审阅实施计划。

    Args:
        client: LLM 客户端。
        agents_md: AGENTS.md 内容。

    Returns:
        (Plan 对象, PlanGenerator) 元组；
        用户退出时返回 (None, None)。
    """
    planner = PlanGenerator(client)

    console.print()
    with Live(
        Spinner("dots", text="正在生成实施计划..."),
        console=console,
        transient=True,
    ):
        try:
            plan = planner.generate(agents_md)
        except PlanError as exc:
            console.print(
                f"[red]计划生成失败: {exc}[/red]"
            )
            return None, None

    planner.display_plan_table(plan)

    # 审阅循环
    while True:
        choice = typer.prompt(
            "确认计划？[y]保存 / [e]修改 / "
            "[r]重新生成 / [q]退出",
            default="y",
        ).strip().lower()

        if choice == "y":
            return plan, planner
        elif choice == "e":
            feedback = typer.prompt("调整意见")
            with Live(
                Spinner(
                    "dots",
                    text="正在调整计划...",
                ),
                console=console,
                transient=True,
            ):
                try:
                    plan = planner.refine(plan, feedback)
                except PlanError as exc:
                    console.print(
                        f"[red]调整失败: {exc}[/red]"
                    )
                    continue
            planner.display_plan_table(plan)
        elif choice == "r":
            with Live(
                Spinner(
                    "dots",
                    text="正在重新生成计划...",
                ),
                console=console,
                transient=True,
            ):
                try:
                    plan = planner.generate(agents_md)
                except PlanError as exc:
                    console.print(
                        f"[red]生成失败: {exc}[/red]"
                    )
                    continue
            planner.display_plan_table(plan)
        elif choice == "q":
            console.print("[dim]已取消。[/dim]")
            return None, None
        else:
            console.print(
                "[yellow]请输入 y/e/r/q[/yellow]"
            )


def _phase_save(
    output_dir: str,
    agents_md: str,
    plan,
    planner: PlanGenerator,
) -> None:
    """阶段四：保存所有文件。

    Args:
        output_dir: 输出根目录。
        agents_md: AGENTS.md 内容。
        plan: Plan 对象。
        planner: PlanGenerator 实例。
    """
    root = Path(output_dir)

    console.print()
    console.print("[bold]正在保存文件...[/bold]")

    try:
        # 保存 AGENTS.md
        FileOps.write_file(
            root / "doc" / "AGENTS.md",
            agents_md,
        )

        # 保存计划文件
        plan_dir = root / "doc" / "plan"
        written = planner.save_plan(plan, plan_dir)

        console.print(
            Panel(
                f"[green]✓ AGENTS.md[/green]\n"
                f"[green]✓ {len(written)} 个计划"
                f"文件[/green]\n\n"
                f"输出目录: [cyan]{root / 'doc'}[/cyan]",
                title="保存完成",
                border_style="green",
            )
        )
    except (OSError, PermissionError) as exc:
        console.print(f"[red]文件写入失败: {exc}[/red]")
        console.print(
            "[yellow]以下为生成的内容，"
            "请手动保存：[/yellow]"
        )
        console.print(agents_md)


@app.command()
def init(
    output_dir: str = typer.Option(
        ".",
        "--output",
        "-o",
        help="输出目录路径",
    ),
) -> None:
    """启动 Harness，通过对话生成 AGENTS.md 和实施计划。"""
    settings = Settings()

    # 检查 API Key
    if not _check_api_key(settings):
        raise typer.Exit(code=1)

    console.print(
        f"[dim]模型: {settings.model_name}  "
        f"API: {settings.qwen_base_url}[/dim]"
    )

    client = QwenClient(settings)

    # 阶段一：多轮对话
    summary = _phase_conversation(client)
    if summary is None:
        raise typer.Exit(code=0)

    # 阶段二：生成 AGENTS.md
    agents_md = _phase_agents(client, summary)
    if agents_md is None:
        raise typer.Exit(code=0)

    # 阶段三：生成实施计划
    plan, planner = _phase_plan(client, agents_md)
    if plan is None:
        raise typer.Exit(code=0)

    # 阶段四：保存文件
    _phase_save(output_dir, agents_md, plan, planner)

    console.print(
        "\n[bold green]Harness 完成！[/bold green]"
    )


if __name__ == "__main__":
    app()
