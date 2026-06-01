"""task-06 计划生成器单元测试。"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harness.core.exceptions import PlanError, PlanParseError
from harness.core.planner import (
    Plan,
    PlanGenerator,
    TaskItem,
)


SAMPLE_PLAN_JSON = json.dumps(
    {
        "project_name": "TestProject",
        "overview": "测试项目实施计划",
        "tasks": [
            {
                "id": "task-01",
                "title": "项目初始化",
                "description": "搭建项目骨架",
                "dependencies": [],
                "deliverables": ["pyproject.toml"],
                "steps": "### 1.1 创建目录",
                "acceptance_criteria": [
                    "pip install 成功"
                ],
                "complexity": "低",
            },
            {
                "id": "task-02",
                "title": "LLM 客户端",
                "description": "封装 API 调用",
                "dependencies": ["task-01"],
                "deliverables": ["client.py"],
                "steps": "### 2.1 实现客户端",
                "acceptance_criteria": [
                    "chat() 返回文本"
                ],
                "complexity": "中",
            },
        ],
        "milestones": [
            "M1 基础搭建完成",
            "M2 核心功能完成",
        ],
    },
    ensure_ascii=False,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """创建 mock QwenClient。"""
    client = MagicMock()
    client.chat.return_value = SAMPLE_PLAN_JSON
    return client


@pytest.fixture
def generator(mock_client: MagicMock) -> PlanGenerator:
    """创建测试用计划生成器。"""
    return PlanGenerator(client=mock_client)


@pytest.fixture
def sample_plan() -> Plan:
    """创建示例 Plan 对象。"""
    return Plan(
        project_name="TestProject",
        overview="测试计划",
        tasks=[
            TaskItem(
                id="task-01",
                title="项目初始化",
                description="搭建骨架",
                dependencies=[],
                deliverables=["pyproject.toml"],
                steps="### 1.1 创建目录",
                acceptance_criteria=["pip install 成功"],
                complexity="低",
            ),
            TaskItem(
                id="task-02",
                title="LLM 客户端",
                description="封装 API",
                dependencies=["task-01"],
                deliverables=["client.py"],
                steps="### 2.1 实现",
                acceptance_criteria=["chat() 返回文本"],
                complexity="中",
            ),
        ],
        milestones=["M1 基础完成", "M2 核心完成"],
    )


class TestTaskItem:
    """TaskItem 数据类测试。"""

    def test_filename_generation(self) -> None:
        """filename 属性正确生成。"""
        task = TaskItem(
            id="task-01",
            title="项目初始化",
            description="desc",
        )
        # 中文 title 被 slug 化
        assert task.filename.startswith("task-01-")
        assert task.filename.endswith(".md")

    def test_filename_english(self) -> None:
        """英文 title 的 filename。"""
        task = TaskItem(
            id="task-02",
            title="LLM Client",
            description="desc",
        )
        assert task.filename == "task-02-llm-client.md"

    def test_default_values(self) -> None:
        """默认值正确。"""
        task = TaskItem(
            id="task-01",
            title="T",
            description="D",
        )
        assert task.dependencies == []
        assert task.deliverables == []
        assert task.complexity == "中"
        assert task.acceptance_criteria == []

    def test_custom_values(self) -> None:
        """自定义值正确存储。"""
        task = TaskItem(
            id="task-03",
            title="模板",
            description="Jinja2 模板",
            dependencies=["task-01"],
            deliverables=["plan.j2"],
            complexity="低",
        )
        assert task.dependencies == ["task-01"]
        assert task.complexity == "低"


class TestPlan:
    """Plan 数据类测试。"""

    def test_plan_creation(self, sample_plan: Plan) -> None:
        """Plan 对象正确创建。"""
        assert sample_plan.project_name == "TestProject"
        assert len(sample_plan.tasks) == 2
        assert len(sample_plan.milestones) == 2

    def test_plan_defaults(self) -> None:
        """Plan 默认值。"""
        plan = Plan(project_name="P", overview="O")
        assert plan.tasks == []
        assert plan.milestones == []


class TestGenerate:
    """generate() 方法测试。"""

    def test_returns_plan_object(
        self,
        generator: PlanGenerator,
        mock_client: MagicMock,
    ) -> None:
        """正常返回 Plan 对象。"""
        plan = generator.generate("# AGENTS.md 内容")
        assert isinstance(plan, Plan)
        assert plan.project_name == "TestProject"
        assert len(plan.tasks) == 2

    def test_tasks_parsed_correctly(
        self,
        generator: PlanGenerator,
    ) -> None:
        """任务列表正确解析。"""
        plan = generator.generate("内容")
        task1 = plan.tasks[0]
        assert task1.id == "task-01"
        assert task1.title == "项目初始化"
        assert task1.complexity == "低"

        task2 = plan.tasks[1]
        assert task2.dependencies == ["task-01"]

    def test_calls_llm_with_correct_messages(
        self,
        generator: PlanGenerator,
        mock_client: MagicMock,
    ) -> None:
        """使用正确的消息调用 LLM。"""
        generator.generate("AGENTS.md 内容")
        mock_client.chat.assert_called_once()
        messages = mock_client.chat.call_args[0][0]
        assert messages[0]["role"] == "system"
        assert "AGENTS.md 内容" in messages[1]["content"]

    def test_handles_json_in_code_block(
        self,
        generator: PlanGenerator,
        mock_client: MagicMock,
    ) -> None:
        """处理 ```json ... ``` 包裹。"""
        wrapped = f"```json\n{SAMPLE_PLAN_JSON}\n```"
        mock_client.chat.return_value = wrapped
        plan = generator.generate("内容")
        assert isinstance(plan, Plan)

    def test_handles_dict_response(
        self,
        generator: PlanGenerator,
        mock_client: MagicMock,
    ) -> None:
        """处理 thinking 模式 dict 响应。"""
        mock_client.chat.return_value = {
            "reasoning": "分析...",
            "content": SAMPLE_PLAN_JSON,
        }
        plan = generator.generate("内容")
        assert isinstance(plan, Plan)

    def test_invalid_json_raises(
        self,
        generator: PlanGenerator,
        mock_client: MagicMock,
    ) -> None:
        """无效 JSON 抛出 PlanParseError。"""
        mock_client.chat.return_value = "这不是 JSON"
        with pytest.raises(PlanParseError, match="JSON"):
            generator.generate("内容")

    def test_missing_tasks_key_raises(
        self,
        generator: PlanGenerator,
        mock_client: MagicMock,
    ) -> None:
        """缺少 tasks 中必填字段时抛出 PlanParseError。"""
        bad_json = json.dumps(
            {
                "project_name": "P",
                "overview": "O",
                "tasks": [{"id": "task-01"}],  # 缺 title
            }
        )
        mock_client.chat.return_value = bad_json
        with pytest.raises(PlanParseError, match="结构"):
            generator.generate("内容")


class TestRefine:
    """refine() 方法测试。"""

    def test_returns_refined_plan(
        self,
        generator: PlanGenerator,
        mock_client: MagicMock,
        sample_plan: Plan,
    ) -> None:
        """返回调整后的 Plan。"""
        plan = generator.refine(sample_plan, "增加一个任务")
        mock_client.chat.assert_called_once()
        messages = mock_client.chat.call_args[0][0]
        assert "增加一个任务" in messages[1]["content"]
        assert isinstance(plan, Plan)


class TestRenderPlan:
    """render_plan() 方法测试。"""

    def test_renders_markdown(
        self,
        generator: PlanGenerator,
        sample_plan: Plan,
    ) -> None:
        """渲染为包含表格的 Markdown。"""
        md = generator.render_plan(sample_plan)
        assert "TestProject" in md
        assert "项目初始化" in md
        assert "LLM 客户端" in md
        assert "M1 基础完成" in md

    def test_renders_task_table(
        self,
        generator: PlanGenerator,
        sample_plan: Plan,
    ) -> None:
        """渲染包含 Markdown 表格。"""
        md = generator.render_plan(sample_plan)
        assert "| 序号 |" in md
        assert "| 1 |" in md


class TestRenderTaskFile:
    """render_task_file() 方法测试。"""

    def test_renders_task_content(
        self, generator: PlanGenerator
    ) -> None:
        """渲染包含任务各部分。"""
        task = TaskItem(
            id="task-01",
            title="初始化",
            description="搭建骨架",
            dependencies=["无"],
            deliverables=["pyproject.toml"],
            steps="### 1.1 创建目录",
            acceptance_criteria=["安装成功"],
            complexity="低",
        )
        md = generator.render_task_file(task)
        assert "task-01 - 初始化" in md
        assert "搭建骨架" in md
        assert "pyproject.toml" in md
        assert "### 1.1 创建目录" in md
        assert "- [ ] 安装成功" in md

    def test_no_dependencies(
        self, generator: PlanGenerator
    ) -> None:
        """无依赖时显示'无'。"""
        task = TaskItem(
            id="task-01",
            title="初始化",
            description="desc",
            dependencies=[],
        )
        md = generator.render_task_file(task)
        assert "无" in md


class TestSavePlan:
    """save_plan() 方法测试。"""

    def test_saves_files(
        self,
        generator: PlanGenerator,
        sample_plan: Plan,
        tmp_path: Path,
    ) -> None:
        """保存生成 README + task 文件。"""
        output = tmp_path / "plan"
        result = generator.save_plan(sample_plan, output)
        assert (output / "README.md").exists()
        # 2 个 task 文件
        assert len(result) == 3


class TestExtractJson:
    """_extract_json() 静态方法测试。"""

    def test_plain_json(self) -> None:
        """纯 JSON 直接提取。"""
        text = '{"key": "value"}'
        assert PlanGenerator._extract_json(text) == text

    def test_json_in_code_block(self) -> None:
        """从 ```json 中提取。"""
        text = '```json\n{"a": 1}\n```'
        assert PlanGenerator._extract_json(text) == '{"a": 1}'

    def test_json_with_surrounding_text(self) -> None:
        """从文本中提取 JSON 部分。"""
        text = '以下是计划：\n{"a": 1}\n完毕'
        assert PlanGenerator._extract_json(text) == '{"a": 1}'

    def test_no_json_returns_stripped(self) -> None:
        """无 JSON 时返回 strip 文本。"""
        text = "  no json here  "
        assert (
            PlanGenerator._extract_json(text)
            == "no json here"
        )


class TestModuleExports:
    """模块导出验证。"""

    def test_import_from_core(self) -> None:
        """Plan/TaskItem/PlanGenerator 可从 core 导入。"""
        from harness.core import (
            Plan as P,
            PlanGenerator as PG,
            TaskItem as TI,
        )

        assert P is Plan
        assert PG is PlanGenerator
        assert TI is TaskItem

    def test_import_exceptions(self) -> None:
        """计划相关异常可导入。"""
        from harness.core.exceptions import (
            PlanError,
            PlanParseError,
        )

        assert issubclass(PlanParseError, PlanError)
