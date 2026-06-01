"""计划生成与管理模块。"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from harness.core.exceptions import (
    PlanError,
    PlanParseError,
)
from harness.llm.client import QwenClient
from harness.llm.prompts import build_plan_generation_prompt
from harness.utils.file_ops import FileOps

console = Console()


@dataclass
class TaskItem:
    """单个任务项。

    Attributes:
        id: 任务 ID，如 ``task-01``。
        title: 任务标题，如 ``项目初始化``。
        description: 任务详细描述。
        dependencies: 依赖的其他任务 ID 列表。
        deliverables: 交付物文件路径列表。
        steps: 详细步骤（Markdown 文本）。
        acceptance_criteria: 验收标准列表。
        complexity: 预估复杂度（低 / 中 / 高）。
    """

    id: str
    title: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    steps: str = ""
    acceptance_criteria: list[str] = field(
        default_factory=list
    )
    complexity: str = "中"

    @property
    def filename(self) -> str:
        """生成任务文件名，如 ``task-01-project-init.md``。"""
        slug = re.sub(
            r"[^\w\u4e00-\u9fff]+",
            "-",
            self.title.lower(),
        ).strip("-")
        return f"{self.id}-{slug}.md" if slug else f"{self.id}.md"


@dataclass
class Plan:
    """实施计划。

    Attributes:
        project_name: 项目名称。
        overview: 计划总览描述。
        tasks: 任务列表。
        milestones: 里程碑列表。
    """

    project_name: str
    overview: str
    tasks: list[TaskItem] = field(default_factory=list)
    milestones: list[str] = field(default_factory=list)


class PlanGenerator:
    """实施计划生成器。

    基于 AGENTS.md 内容调用 LLM 生成结构化计划数据，
    支持渲染为 Markdown 并保存到文件系统。

    Attributes:
        client: Qwen3 LLM 客户端实例。
    """

    def __init__(self, client: QwenClient) -> None:
        """初始化计划生成器。

        Args:
            client: Qwen3 客户端实例。
        """
        self.client = client

    def generate(self, agents_md: str) -> Plan:
        """根据 AGENTS.md 内容生成实施计划。

        Args:
            agents_md: AGENTS.md 的完整 Markdown 内容。

        Returns:
            Plan 数据对象。

        Raises:
            PlanParseError: LLM 响应无法解析为计划数据。
            PlanError: 生成过程异常。
        """
        messages = build_plan_generation_prompt(agents_md)
        response = self.client.chat(messages)
        if isinstance(response, dict):
            response = response.get("content", "")
        return self._parse_plan(response)

    def refine(self, plan: Plan, feedback: str) -> Plan:
        """根据用户反馈调整计划。

        Args:
            plan: 当前计划对象。
            feedback: 用户的调整意见。

        Returns:
            调整后的 Plan 对象。

        Raises:
            PlanError: 生成过程异常。
        """
        plan_json = self._plan_to_json(plan)
        user_prompt = (
            "请根据以下调整意见修改实施计划。\n\n"
            f"调整意见：\n{feedback}\n\n"
            f"当前计划（JSON）：\n{plan_json}\n\n"
            "请输出完整的修改后的计划（JSON 格式）。"
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一名资深项目经理，"
                    "擅长根据反馈调整项目计划。"
                    "请输出 JSON 格式的计划。"
                ),
            },
            {"role": "user", "content": user_prompt},
        ]
        response = self.client.chat(messages)
        if isinstance(response, dict):
            response = response.get("content", "")
        return self._parse_plan(response)

    def render_plan(self, plan: Plan) -> str:
        """将计划总览渲染为 Markdown 文本。

        Args:
            plan: Plan 对象。

        Returns:
            计划总览的 Markdown 字符串。
        """
        lines: list[str] = [
            f"# {plan.project_name} 项目实施计划总览",
            "",
            plan.overview,
            "",
            "## 任务清单",
            "",
            "| 序号 | 任务文件 | 描述 | 预估复杂度 |",
            "| ---- | -------- | ---- | ---------- |",
        ]
        for i, task in enumerate(plan.tasks, 1):
            lines.append(
                f"| {i} | [{task.title}]"
                f"(./{task.filename}) "
                f"| {task.description} | {task.complexity} |"
            )

        lines.extend(["", "## 里程碑", ""])
        for ms in plan.milestones:
            lines.append(f"- {ms}")

        return "\n".join(lines)

    def render_task_file(self, task: TaskItem) -> str:
        """将单个任务渲染为 Markdown 文本。

        Args:
            task: TaskItem 对象。

        Returns:
            任务详情的 Markdown 字符串。
        """
        lines: list[str] = [
            f"# {task.id} - {task.title}",
            "",
            "## 目标",
            "",
            task.description,
            "",
            "## 依赖",
            "",
        ]
        if task.dependencies:
            for dep in task.dependencies:
                lines.append(f"- {dep}")
        else:
            lines.append("- 无")

        lines.extend(["", "## 交付物", ""])
        for item in task.deliverables:
            lines.append(f"- `{item}`")

        lines.extend(["", "## 详细步骤", "", task.steps])
        lines.extend(["", "## 验收标准", ""])
        for criterion in task.acceptance_criteria:
            lines.append(f"- [ ] {criterion}")

        return "\n".join(lines)

    def save_plan(
        self,
        plan: Plan,
        output_dir: Path,
    ) -> list[Path]:
        """将计划保存到文件系统。

        Args:
            plan: Plan 对象。
            output_dir: 输出目录路径（如 ``doc/plan/``）。

        Returns:
            已写入的文件路径列表。
        """
        readme = self.render_plan(plan)
        task_files: dict[str, str] = {}
        for task in plan.tasks:
            task_files[task.filename] = (
                self.render_task_file(task)
            )
        return FileOps.write_plan_files(
            output_dir, readme, task_files
        )

    def display_plan_table(self, plan: Plan) -> None:
        """在终端以表格形式展示计划总览。

        Args:
            plan: Plan 对象。
        """
        table = Table(
            title=f"{plan.project_name} 实施计划",
            show_lines=True,
        )
        table.add_column("序号", style="cyan", width=4)
        table.add_column("任务", style="bold")
        table.add_column("依赖", style="yellow")
        table.add_column("复杂度", style="magenta", width=6)

        for i, task in enumerate(plan.tasks, 1):
            deps = ", ".join(task.dependencies) or "-"
            table.add_row(
                str(i), task.title, deps, task.complexity
            )

        console.print(table)

    @staticmethod
    def _extract_json(text: str) -> str:
        """从 LLM 响应中提取 JSON 字符串。

        支持 ````json ... ``` `` 包裹和纯 JSON 两种格式。

        Args:
            text: LLM 响应文本。

        Returns:
            提取后的 JSON 字符串。
        """
        # 尝试匹配 ```json ... ``` 包裹
        pattern = re.compile(
            r"```(?:json)?\s*\n(.*?)\n```",
            re.DOTALL,
        )
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
        # 尝试直接提取 { ... } 或 [ ... ]
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = text.find(start_char)
            end = text.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                return text[start : end + 1]
        return text.strip()

    @staticmethod
    def _parse_plan(text: str) -> Plan:
        """将 LLM 响应解析为 Plan 对象。

        Args:
            text: LLM 响应文本（应包含 JSON）。

        Returns:
            解析后的 Plan 对象。

        Raises:
            PlanParseError: 解析失败时抛出。
        """
        json_str = PlanGenerator._extract_json(text)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise PlanParseError(
                f"无法解析 LLM 响应为 JSON: {exc}"
            ) from exc

        try:
            tasks = []
            for t in data.get("tasks", []):
                tasks.append(
                    TaskItem(
                        id=t["id"],
                        title=t["title"],
                        description=t.get(
                            "description", ""
                        ),
                        dependencies=t.get(
                            "dependencies", []
                        ),
                        deliverables=t.get(
                            "deliverables", []
                        ),
                        steps=t.get("steps", ""),
                        acceptance_criteria=t.get(
                            "acceptance_criteria", []
                        ),
                        complexity=t.get("complexity", "中"),
                    )
                )

            return Plan(
                project_name=data.get(
                    "project_name", "未命名项目"
                ),
                overview=data.get("overview", ""),
                tasks=tasks,
                milestones=data.get("milestones", []),
            )
        except (KeyError, TypeError) as exc:
            raise PlanParseError(
                f"计划 JSON 结构不正确: {exc}"
            ) from exc

    @staticmethod
    def _plan_to_json(plan: Plan) -> str:
        """将 Plan 对象序列化为 JSON 字符串。

        Args:
            plan: Plan 对象。

        Returns:
            格式化的 JSON 字符串。
        """
        data = {
            "project_name": plan.project_name,
            "overview": plan.overview,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "dependencies": t.dependencies,
                    "deliverables": t.deliverables,
                    "steps": t.steps,
                    "acceptance_criteria": (
                        t.acceptance_criteria
                    ),
                    "complexity": t.complexity,
                }
                for t in plan.tasks
            ],
            "milestones": plan.milestones,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
