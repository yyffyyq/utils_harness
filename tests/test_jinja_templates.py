"""task-07 Jinja2 模板渲染测试。"""

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = (
    Path(__file__).resolve().parent.parent
    / "harness" / "templates"
)


@pytest.fixture
def env() -> Environment:
    """创建 Jinja2 环境。"""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
    )


class TestTemplateFilesExist:
    """验证模板文件存在。"""

    def test_agents_md_template_exists(self) -> None:
        """agents_md.j2 文件存在。"""
        assert (TEMPLATES_DIR / "agents_md.j2").exists()

    def test_plan_template_exists(self) -> None:
        """plan.j2 文件存在。"""
        assert (TEMPLATES_DIR / "plan.j2").exists()

    def test_plan_readme_template_exists(self) -> None:
        """plan_readme.j2 文件存在。"""
        assert (TEMPLATES_DIR / "plan_readme.j2").exists()


class TestAgentsMdTemplate:
    """agents_md.j2 渲染测试。"""

    def test_renders_project_name(
        self, env: Environment
    ) -> None:
        """渲染包含项目名称。"""
        tpl = env.get_template("agents_md.j2")
        result = tpl.render(
            project_name="MyProject",
            project_description="A test project",
            background="Background info",
            workflow=["Step 1", "Step 2"],
            tech_stack=[
                {
                    "category": "语言",
                    "name": "Python",
                    "description": "主语言",
                }
            ],
            code_standards="PEP 8",
        )
        assert "MyProject" in result
        assert "A test project" in result

    def test_renders_workflow_steps(
        self, env: Environment
    ) -> None:
        """渲染包含工作流步骤。"""
        tpl = env.get_template("agents_md.j2")
        result = tpl.render(
            project_name="P",
            project_description="D",
            background="B",
            workflow=["分析需求", "设计架构", "编码实现"],
            tech_stack=[],
            code_standards="CS",
        )
        assert "分析需求" in result
        assert "设计架构" in result
        assert "编码实现" in result

    def test_renders_tech_stack_table(
        self, env: Environment
    ) -> None:
        """渲染包含技术栈表格。"""
        tpl = env.get_template("agents_md.j2")
        result = tpl.render(
            project_name="P",
            project_description="D",
            background="B",
            workflow=[],
            tech_stack=[
                {
                    "category": "CLI 框架",
                    "name": "Typer",
                    "description": "命令解析",
                }
            ],
            code_standards="CS",
        )
        assert "CLI 框架" in result
        assert "Typer" in result

    def test_renders_optional_sections(
        self, env: Environment
    ) -> None:
        """可选章节（target_users/dependencies等）正确渲染。"""
        tpl = env.get_template("agents_md.j2")
        result = tpl.render(
            project_name="P",
            project_description="D",
            background="B",
            workflow=[],
            tech_stack=[],
            code_standards="CS",
            target_users=["开发者"],
            dependencies=["rich>=13.0"],
            error_handling="自定义异常",
            git_convention="feat/fix/docs",
            test_convention="pytest",
        )
        assert "开发者" in result
        assert "rich>=13.0" in result
        assert "自定义异常" in result


class TestPlanTemplate:
    """plan.j2 渲染测试。"""

    def test_renders_task_info(
        self, env: Environment
    ) -> None:
        """渲染包含任务 ID 和标题。"""
        tpl = env.get_template("plan.j2")
        result = tpl.render(
            task_id="task-01",
            task_title="项目初始化",
            description="搭建项目骨架",
            dependencies=["无"],
            deliverables=["pyproject.toml"],
            steps="### 1.1 创建目录",
            acceptance_criteria=[
                "pip install 可正常安装",
                "目录结构正确",
            ],
        )
        assert "task-01" in result
        assert "项目初始化" in result
        assert "pyproject.toml" in result

    def test_renders_acceptance_criteria(
        self, env: Environment
    ) -> None:
        """渲染包含验收标准 checkbox。"""
        tpl = env.get_template("plan.j2")
        result = tpl.render(
            task_id="task-02",
            task_title="LLM 客户端",
            description="封装 API",
            dependencies=["task-01"],
            deliverables=["client.py"],
            steps="步骤内容",
            acceptance_criteria=[
                "chat() 返回文本",
                "支持流式输出",
            ],
        )
        assert "- [ ] chat() 返回文本" in result
        assert "- [ ] 支持流式输出" in result

    def test_empty_dependencies_shows_none(
        self, env: Environment
    ) -> None:
        """空依赖列表时显示'无'。"""
        tpl = env.get_template("plan.j2")
        result = tpl.render(
            task_id="task-01",
            task_title="初始化",
            description="初始",
            dependencies=[],
            deliverables=["file.py"],
            steps="步骤",
            acceptance_criteria=["标准"],
        )
        assert "无" in result


class TestPlanReadmeTemplate:
    """plan_readme.j2 渲染测试。"""

    def test_renders_task_list(
        self, env: Environment
    ) -> None:
        """渲染包含任务清单表格。"""
        tpl = env.get_template("plan_readme.j2")
        result = tpl.render(
            project_name="Harness",
            overview="项目总览",
            tasks=[
                {
                    "title": "task-01 初始化",
                    "filename": "task-01.md",
                    "description": "项目初始化",
                    "complexity": "低",
                }
            ],
            dependency_graph="task-01 -> task-02",
            milestones=[
                {
                    "name": "M1",
                    "description": "基础搭建完成",
                }
            ],
        )
        assert "Harness" in result
        assert "task-01.md" in result
        assert "M1" in result

    def test_renders_milestones(
        self, env: Environment
    ) -> None:
        """渲染包含里程碑列表。"""
        tpl = env.get_template("plan_readme.j2")
        result = tpl.render(
            project_name="P",
            overview="O",
            tasks=[],
            dependency_graph="",
            milestones=[
                {"name": "M1", "description": "阶段一"},
                {"name": "M2", "description": "阶段二"},
            ],
        )
        assert "**M1**" in result
        assert "**M2**" in result
