# Harness 项目实施计划总览

基于 `AGENTS.md` 规范，将项目拆分为以下任务，按依赖顺序排列。

## 任务清单

| 序号 | 任务文件              | 描述                          | 预估复杂度 |
| ---- | --------------------- | ----------------------------- | ---------- |
| 1    | [task-01-project-init.md](./task-01-project-init.md)       | 项目初始化与基础配置          | 低         |
| 2    | [task-02-llm-client.md](./task-02-llm-client.md)           | LLM 客户端封装（Qwen3 接入）  | 中         |
| 3    | [task-03-prompt-templates.md](./task-03-prompt-templates.md)| Prompt 模板管理               | 低         |
| 4    | [task-04-conversation.md](./task-04-conversation.md)       | 多轮对话管理器                | 中         |
| 5    | [task-05-agents-generator.md](./task-05-agents-generator.md)| AGENTS.md 生成逻辑            | 中         |
| 6    | [task-06-plan-generator.md](./task-06-plan-generator.md)   | 计划生成与管理                | 中         |
| 7    | [task-07-jinja-templates.md](./task-07-jinja-templates.md) | Jinja2 模板文件编写           | 低         |
| 8    | [task-08-file-ops.md](./task-08-file-ops.md)               | 文件读写工具                  | 低         |
| 9    | [task-09-cli-main.md](./task-09-cli-main.md)               | CLI 主入口与命令定义          | 中         |
| 10   | [task-10-tests.md](./task-10-tests.md)                     | 单元测试与集成测试            | 中         |

## 依赖关系

```
task-01 (项目初始化)
  ├── task-02 (LLM客户端)
  │     └── task-03 (Prompt模板)
  ├── task-08 (文件工具)
  └── task-07 (Jinja模板)
        │
        ▼
task-04 (多轮对话) ──依赖──> task-02, task-03
        │
        ▼
task-05 (AGENTS生成) ──依赖──> task-04, task-07, task-08
        │
        ▼
task-06 (计划生成) ──依赖──> task-05, task-07, task-08
        │
        ▼
task-09 (CLI入口) ──依赖──> task-04, task-05, task-06
        │
        ▼
task-10 (测试) ──依赖──> 所有模块
```

## 里程碑

- **M1 基础搭建**：task-01 ~ task-03 完成，能调用 Qwen3 API
- **M2 核心功能**：task-04 ~ task-06 完成，对话+生成+计划全流程跑通
- **M3 CLI 交付**：task-07 ~ task-09 完成，终端可用
- **M4 质量保障**：task-10 完成，测试覆盖达标
