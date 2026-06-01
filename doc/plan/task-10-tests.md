# Task 10 - 单元测试与集成测试

## 目标

为核心模块编写测试用例，确保代码质量与覆盖率达标。

## 依赖

- 所有前置模块（task-01 ~ task-09）

## 交付物

- `tests/test_conversation.py` - 对话管理器测试
- `tests/test_generator.py` - AGENTS.md 生成器测试
- `tests/test_planner.py` - 计划生成器测试
- `tests/test_client.py` - LLM 客户端测试
- `tests/test_file_ops.py` - 文件操作测试
- `tests/conftest.py` - pytest fixtures

## 详细步骤

### 10.1 配置 pytest

在 `pyproject.toml` 中添加：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
```

### 10.2 编写 conftest.py

```python
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_settings():
    """模拟配置对象。"""
    ...

@pytest.fixture
def mock_llm_client():
    """模拟 LLM 客户端，避免真实 API 调用。"""
    ...
```

### 10.3 各模块测试要点

**test_client.py**
- 正常调用返回预期文本
- 流式调用逐块返回
- 重试机制正确触发（mock 前 2 次失败，第 3 次成功）
- 重试耗尽后抛出正确异常

**test_conversation.py**
- 对话状态切换正确
- 对话历史正确追加
- `/generate`、`/quit` 命令处理
- 最大轮次限制

**test_generator.py**
- 生成内容包含必要章节
- 修改流程正确调用 LLM
- Markdown 格式校验

**test_planner.py**
- 计划 JSON 解析正确
- TaskItem 数据完整
- 计划渲染 Markdown 格式正确

**test_file_ops.py**
- 目录创建
- 文件读写（含中文）
- 权限错误处理
- 批量写入

### 10.4 运行测试

```bash
pytest tests/ -v --tb=short
```

## 验收标准

- [x] 所有测试通过（`pytest` 无失败）- 180 passed
- [x] 核心模块覆盖率 >= 80%（实际 91%）
- [x] LLM 调用全部使用 mock
- [x] 测试可离线运行
- [x] conftest.py 共享 fixtures
- [x] 集成测试覆盖端到端流程
