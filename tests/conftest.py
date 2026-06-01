"""pytest 共享 fixtures。

提供所有测试模块共用的 mock 对象与测试数据。
"""

import json
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_settings() -> MagicMock:
    """模拟配置对象。"""
    s = MagicMock()
    s.qwen_api_key = "sk-b63b3cf928d74b46a396fa050b9cb772"
    s.qwen_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    s.model_name = "qwen3.6-plus"
    s.temperature = 0.7
    s.max_tokens = 4096
    return s


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """模拟 LLM 客户端，避免真实 API 调用。"""
    client = MagicMock()
    client.chat.return_value = "AI 模拟响应"
    return client


@pytest.fixture
def mock_plan_json() -> str:
    """有效的计划 JSON 字符串。"""
    return json.dumps(
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
def sample_agents_md() -> str:
    """示例 AGENTS.md 内容。"""
    return (
        "# TestProject\n\n"
        "## 项目背景\n\n"
        "这是一个测试项目。\n\n"
        "## 技术栈\n\n"
        "| 类别 | 技术选型 | 说明 |\n"
        "| ---- | -------- | ---- |\n"
        "| 语言 | Python | 主语言 |\n\n"
        "## 代码规范\n\n"
        "遵循 PEP 8 规范。\n"
    )
