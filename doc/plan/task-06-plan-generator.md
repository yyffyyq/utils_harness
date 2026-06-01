# Task 06 - 计划生成与管理

## 目标

基于确认后的 AGENTS.md，调用 LLM 生成结构化的实施计划，并支持用户审阅与保存。

## 依赖

- task-05（AGENTS.md 生成器）
- task-07（Jinja2 模板）
- task-08（文件操作工具）

## 交付物

- `core/planner.py` - 计划生成与管理模块

## 详细步骤

### 6.1 定义计划数据结构

```python
from dataclasses import dataclass, field


@dataclass
class TaskItem:
    """单个任务项。"""
    id: str
    title: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    complexity: str = "中"  # 低 / 中 / 高


@dataclass
class Plan:
    """实施计划。"""
    project_name: str
    overview: str
    tasks: list[TaskItem]
    milestones: list[str]
```

### 6.2 实现 PlanGenerator

```python
class PlanGenerator:
    """实施计划生成器。"""

    def __init__(self, client: QwenClient) -> None:
        self.client = client

    def generate(self, agents_md: str) -> Plan:
        """根据 AGENTS.md 内容生成实施计划。

        Args:
            agents_md: AGENTS.md 的完整内容。

        Returns:
            Plan 数据对象。
        """

    def refine(self, plan: Plan, feedback: str) -> Plan:
        """根据用户反馈调整计划。"""

    def render_plan(self, plan: Plan) -> str:
        """将计划渲染为 Markdown 文本。"""
```

### 6.3 计划生成流程

1. 将 AGENTS.md 内容传入 LLM
2. LLM 返回 JSON 格式的计划数据
3. 解析 JSON，构建 `Plan` 对象
4. 为每个 TaskItem 生成独立的 Markdown 文件内容
5. 生成 plan 目录的 README.md（总览）

### 6.4 计划审阅流程

1. 终端展示计划总览（表格形式）
2. 用户选择：
   - `y` - 确认，执行保存
   - `e` - 提供调整意见，AI 修改计划
   - `r` - 重新生成计划
   - `q` - 退出（不保存）
3. 确认后调用 `FileOps` 写入 `plan/` 目录

### 6.5 计划文件输出

```
plan/
├── README.md          # 计划总览
├── task-01-xxx.md     # 各任务详情
├── task-02-xxx.md
└── ...
```

## 验收标准

- [x] 可根据 AGENTS.md 生成完整的任务列表
- [x] 每个任务包含 id、标题、描述、依赖、复杂度
- [x] 支持用户反馈后调整计划
- [x] 可渲染为 Markdown 并输出到文件
- [x] 25 个单元测试全部通过（总计 145 passed / 11.66s）
