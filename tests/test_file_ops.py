"""task-08 文件操作工具单元测试。"""

from pathlib import Path

import pytest

from harness.utils.file_ops import FileOps


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """提供临时目录。"""
    return tmp_path


class TestEnsureDirectory:
    """ensure_directory() 测试。"""

    def test_creates_directory(self, tmp_dir: Path) -> None:
        """目录不存在时自动创建。"""
        target = tmp_dir / "a" / "b" / "c"
        FileOps.ensure_directory(target)
        assert target.is_dir()

    def test_existing_directory_no_error(
        self, tmp_dir: Path
    ) -> None:
        """目录已存在时不报错。"""
        target = tmp_dir / "existing"
        target.mkdir()
        FileOps.ensure_directory(target)
        assert target.is_dir()

    def test_path_is_file_raises(
        self, tmp_dir: Path
    ) -> None:
        """路径是文件而非目录时抛出 FileExistsError。"""
        target = tmp_dir / "file.txt"
        target.write_text("hi", encoding="utf-8")
        with pytest.raises(FileExistsError):
            FileOps.ensure_directory(target)


class TestWriteFile:
    """write_file() 测试。"""

    def test_writes_content(self, tmp_dir: Path) -> None:
        """正常写入文件内容。"""
        target = tmp_dir / "test.md"
        FileOps.write_file(target, "# Hello")
        assert target.read_text(encoding="utf-8") == "# Hello"

    def test_auto_creates_parent_dirs(
        self, tmp_dir: Path
    ) -> None:
        """自动创建不存在的父目录。"""
        target = tmp_dir / "deep" / "nested" / "file.md"
        FileOps.write_file(target, "content")
        assert target.exists()

    def test_chinese_content(
        self, tmp_dir: Path
    ) -> None:
        """支持中文内容写入。"""
        target = tmp_dir / "cn.md"
        content = "# 项目背景\n\n这是一个中文测试。"
        FileOps.write_file(target, content)
        assert target.read_text(encoding="utf-8") == content

    def test_overwrites_existing(
        self, tmp_dir: Path
    ) -> None:
        """已存在的文件会被覆盖。"""
        target = tmp_dir / "overwrite.md"
        target.write_text("old", encoding="utf-8")
        FileOps.write_file(target, "new")
        assert target.read_text(encoding="utf-8") == "new"


class TestReadFile:
    """read_file() 测试。"""

    def test_reads_content(self, tmp_dir: Path) -> None:
        """正常读取文件内容。"""
        target = tmp_dir / "read.md"
        target.write_text("# Test", encoding="utf-8")
        assert FileOps.read_file(target) == "# Test"

    def test_reads_chinese(
        self, tmp_dir: Path
    ) -> None:
        """正确读取中文内容。"""
        target = tmp_dir / "cn.md"
        content = "中文内容测试"
        target.write_text(content, encoding="utf-8")
        assert FileOps.read_file(target) == content

    def test_not_found_raises(
        self, tmp_dir: Path
    ) -> None:
        """文件不存在时抛出 FileNotFoundError。"""
        target = tmp_dir / "missing.md"
        with pytest.raises(FileNotFoundError, match="不存在"):
            FileOps.read_file(target)


class TestWritePlanFiles:
    """write_plan_files() 测试。"""

    def test_writes_readme_and_tasks(
        self, tmp_dir: Path
    ) -> None:
        """正确写入 README.md 和 task 文件。"""
        plan_dir = tmp_dir / "plan"
        tasks = {
            "task-01-init.md": "# Task 01",
            "task-02-llm.md": "# Task 02",
        }
        result = FileOps.write_plan_files(
            plan_dir, "# Plan README", tasks
        )
        assert (plan_dir / "README.md").exists()
        assert (plan_dir / "task-01-init.md").exists()
        assert (plan_dir / "task-02-llm.md").exists()
        assert len(result) == 3  # README + 2 tasks

    def test_empty_tasks_only_readme(
        self, tmp_dir: Path
    ) -> None:
        """无 task 文件时只写入 README。"""
        plan_dir = tmp_dir / "plan"
        result = FileOps.write_plan_files(
            plan_dir, "# README", {}
        )
        assert len(result) == 1
        assert (plan_dir / "README.md").exists()

    def test_content_correct(
        self, tmp_dir: Path
    ) -> None:
        """写入内容正确。"""
        plan_dir = tmp_dir / "plan"
        tasks = {"task-01.md": "# Task 01 Content"}
        FileOps.write_plan_files(
            plan_dir, "# My Plan", tasks
        )
        assert (
            (plan_dir / "README.md").read_text(
                encoding="utf-8"
            )
            == "# My Plan"
        )
        assert (
            (plan_dir / "task-01.md").read_text(
                encoding="utf-8"
            )
            == "# Task 01 Content"
        )


class TestFileExists:
    """file_exists() 测试。"""

    def test_existing_file(self, tmp_dir: Path) -> None:
        """存在的文件返回 True。"""
        target = tmp_dir / "exists.md"
        target.write_text("x", encoding="utf-8")
        assert FileOps.file_exists(target) is True

    def test_nonexistent_file(
        self, tmp_dir: Path
    ) -> None:
        """不存在的文件返回 False。"""
        assert FileOps.file_exists(tmp_dir / "no.md") is False

    def test_directory_returns_false(
        self, tmp_dir: Path
    ) -> None:
        """目录路径返回 False。"""
        assert FileOps.file_exists(tmp_dir) is False
