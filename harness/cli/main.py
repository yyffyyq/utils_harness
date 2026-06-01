"""Harness CLI 主入口。"""

import typer

app = typer.Typer(
    name="harness",
    help="Harness - AI 辅助项目规划工具",
    add_completion=False,
)


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
    typer.echo(f"Harness init - output: {output_dir}")
    typer.echo("功能开发中，敬请期待。")


if __name__ == "__main__":
    app()
