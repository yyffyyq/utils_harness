# Task 08 - 文件读写工具

## 目标

封装文件与目录的读写操作，提供安全的文件创建、写入与校验功能。

## 依赖

- task-01（项目初始化）

## 交付物

- `utils/file_ops.py` - 文件操作工具模块

## 详细步骤

### 8.1 实现 FileOps 类

```python
from pathlib import Path


class FileOps:
    """文件与目录操作工具。"""

    @staticmethod
    def ensure_directory(path: Path) -> None:
        """确保目录存在，不存在则创建。

        Args:
            path: 目录路径。

        Raises:
            PermissionError: 无写入权限时抛出。
        """

    @staticmethod
    def write_file(path: Path, content: str) -> None:
        """将内容写入文件，自动创建父目录。

        Args:
            path: 文件路径。
            content: 文件内容。
        """

    @staticmethod
    def read_file(path: Path) -> str:
        """读取文件内容。

        Args:
            path: 文件路径。

        Returns:
            文件内容字符串。
        """

    @staticmethod
    def write_plan_files(
        plan_dir: Path,
        readme_content: str,
        task_files: dict[str, str],
    ) -> None:
        """批量写入计划文件。

        Args:
            plan_dir: plan 目录路径。
            readme_content: README.md 内容。
            task_files: 文件名到内容的映射。
        """
```

### 8.2 权限与安全检查

- 写入前检查目标路径是否可写
- 文件已存在时提示用户确认覆盖
- 路径中包含非法字符时给出明确错误

### 8.3 输出确认

- 文件写入成功后，用 Rich 打印成功信息（含文件路径）
- 批量写入时显示进度条

## 验收标准

- [ ] 目录自动创建功能正常
- [ ] 文件读写正确（支持中文内容）
- [ ] 权限检查有效，无权限时友好提示
- [ ] 批量写入功能可用
