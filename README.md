# Harness

AI 辅助项目规划工具 —— 通过终端多轮对话生成 `AGENTS.md` 与实施计划。

## 功能

- 终端多轮对话引导，收集项目信息
- 调用 Qwen3 大模型自动生成 `AGENTS.md`
- 基于 AGENTS.md 生成结构化实施计划（Plan）
- 一键保存到本地

## 快速开始

```bash
# 安装
pip install -e ".[dev]"

# 配置 API Key
export HARNESS_QWEN_API_KEY="your-api-key"

# 运行
harness init
```

## 技术栈

- Python 3.10+
- Typer + Rich（CLI 交互）
- OpenAI SDK（兼容 Qwen3 API）
- Pydantic Settings（配置管理）
- Jinja2（模板渲染）

## 项目结构

```
harness/
├── cli/          # CLI 入口
├── core/         # 核心业务逻辑
├── llm/          # LLM 调用封装
├── templates/    # Jinja2 模板
└── utils/        # 工具函数
```

## License

MIT
