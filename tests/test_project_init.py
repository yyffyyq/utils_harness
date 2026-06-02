"""task-01 项目初始化验收测试。"""

import importlib


class TestProjectStructure:
    """验证项目目录结构与模块可导入性。"""

    def test_import_harness_package(self) -> None:
        """harness 包可正常导入。"""
        import harness

        assert harness.__version__ == "0.1.0"

    def test_import_settings(self) -> None:
        """Settings 类可正常导入。"""
        from harness.utils.config import Settings

        settings = Settings()
        # .env 存在时 api_key 会被实际值覆盖，仅验证类型为 str
        assert isinstance(settings.qwen_api_key, str)
        assert "dashscope" in settings.qwen_base_url
        assert settings.model_name == "qwen3.7-max"
        assert settings.max_tokens == 4096
        assert settings.temperature == 0.7

    def test_get_settings(self) -> None:
        """get_settings 工厂函数返回 Settings 实例。"""
        from harness.utils.config import Settings, get_settings

        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_import_cli_app(self) -> None:
        """CLI Typer app 可正常导入。"""
        from harness.cli.main import app

        assert app is not None

    def test_import_exceptions(self) -> None:
        """自定义异常类可正常导入。"""
        from harness.core.exceptions import (
            HarnessError,
            LLMConnectionError,
            LLMRateLimitError,
            LLMResponseError,
        )

        assert issubclass(LLMConnectionError, HarnessError)
        assert issubclass(LLMResponseError, HarnessError)
        assert issubclass(LLMRateLimitError, HarnessError)

    def test_import_core_package(self) -> None:
        """core 包可正常导入。"""
        mod = importlib.import_module("harness.core")
        assert mod is not None

    def test_import_llm_package(self) -> None:
        """llm 包可正常导入。"""
        mod = importlib.import_module("harness.llm")
        assert mod is not None

    def test_import_utils_package(self) -> None:
        """utils 包可正常导入。"""
        mod = importlib.import_module("harness.utils")
        assert mod is not None
