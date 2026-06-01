"""文件与目录操作工具模块。"""

from pathlib import Path

from rich.console import Console
from rich.progress import Progress

console = Console()


class FileOps:
    """文件与目录操作工具集。

    提供安全的文件创建、写入、读取及批量写入功能，
    自动处理目录创建与权限校验。
    """

    @staticmethod
    def ensure_directory(path: Path) -> None:
        """确保目录存在，不存在则创建。

        Args:
            path: 目标目录路径。

        Raises:
            PermissionError: 无写入权限时抛出。
        """
        if path.exists() and not path.is_dir():
            raise FileExistsError(
                f"路径已存在且不是目录: {path}"
            )
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def write_file(path: Path, content: str) -> None:
        """将内容写入文件，自动创建父目录。

        Args:
            path: 目标文件路径。
            content: 文件内容（支持中文）。

        Raises:
            PermissionError: 无写入权限时抛出。
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        console.print(f"[green]✓ 已写入:[/green] {path}")

    @staticmethod
    def read_file(path: Path) -> str:
        """读取文件内容。

        Args:
            path: 文件路径。

        Returns:
            文件内容字符串。

        Raises:
            FileNotFoundError: 文件不存在时抛出。
        """
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def write_plan_files(
        plan_dir: Path,
        readme_content: str,
        task_files: dict[str, str],
    ) -> list[Path]:
        """批量写入计划文件（README + 各 task 文件）。

        Args:
            plan_dir: plan 目录路径。
            readme_content: README.md 内容。
            task_files: 文件名 → 内容的映射，
                如 ``{"task-01-xxx.md": "# Task 01 ..."}``。

        Returns:
            已写入文件的路径列表。

        Raises:
            PermissionError: 无写入权限时抛出。
        """
        plan_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []

        # 写入 README.md
        readme_path = plan_dir / "README.md"
        readme_path.write_text(readme_content, encoding="utf-8")
        written.append(readme_path)

        # 批量写入 task 文件（带进度条）
        if task_files:
            with Progress(
                console=console,
                transient=True,
            ) as progress:
                task_id = progress.add_task(
                    "写入计划文件...",
                    total=len(task_files),
                )
                for filename, content in task_files.items():
                    file_path = plan_dir / filename
                    file_path.write_text(
                        content, encoding="utf-8"
                    )
                    written.append(file_path)
                    progress.advance(task_id)

        console.print(
            f"[green]✓ 已写入 {len(written)} 个文件到 "
            f"{plan_dir}[/green]"
        )
        return written

    @staticmethod
    def file_exists(path: Path) -> bool:
        """检查文件是否存在。

        Args:
            path: 文件路径。

        Returns:
            文件是否存在。
        """
        return path.exists() and path.is_file()
