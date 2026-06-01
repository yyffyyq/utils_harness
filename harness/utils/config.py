"""应用配置模块，从环境变量或 .env 文件加载配置。"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Harness 应用配置。

    通过环境变量（前缀 HARNESS_）或 .env 文件加载配置项。

    Attributes:
        qwen_api_key: Qwen3 API 密钥。
        qwen_base_url: Qwen3 API 兼容端点地址。
        model_name: 使用的模型名称。
        max_tokens: 单次请求最大 token 数。
        temperature: 生成温度，控制随机性。
    """

    qwen_api_key: str = ""
    qwen_base_url: str = (
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    model_name: str = "qwen3.7-max"
    max_tokens: int = 4096
    temperature: float = 0.7

    model_config = {
        "env_file": ".env",
        "env_prefix": "HARNESS_",
    }


def get_settings() -> Settings:
    """获取全局配置单例。

    Returns:
        Settings 实例。
    """
    return Settings()
