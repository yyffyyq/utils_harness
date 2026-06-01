# Task 05 - AGENTS.md 生成逻辑

## 目标

基于对话摘要，调用 LLM 生成 AGENTS.md 内容，并支持用户在终端中审阅与修改。

## 依赖

- task-04（多轮对话管理器）
- task-07（Jinja2 模板）
- task-08（文件操作工具）

## 交付物

- `core/generator.py` - AGENTS.md 生成器

## 详细步骤

### 5.1 实现 AgentsGenerator

```python
class AgentsGenerator:
    """AGENTS.md 内容生成器。"""

    def __init__(self, client: QwenClient) -> None:
        self.client = client

    def generate(self, conversation_summary: str) -> str:
        """根据对话摘要生成 AGENTS.md 内容。

        Args:
            conversation_summary: 对话摘要文本。

        Returns:
            生成的 AGENTS.md Markdown 内容。
        """

    def regenerate(self, feedback: str, current_content: str) -> str:
        """根据用户反馈修改 AGENTS.md。

        Args:
            feedback: 用户修改意见。
            current_content: 当前 AGENTS.md 内容。

        Returns:
            修改后的 AGENTS.md 内容。
        """
```

### 5.2 生成流程

1. 将对话摘要传入 LLM，使用 `AGENTS_GENERATION_PROMPT`
2. LLM 返回完整的 Markdown 格式 AGENTS.md
3. 解析响应，提取纯 Markdown 内容（去除可能的代码块包裹）
4. 返回给用户审阅

### 5.3 审阅与修改流程

1. 在终端中用 Rich 渲染生成的 Markdown
2. 用户选择：
   - `y` - 确认，进入计划生成阶段
   - `e` - 提供修改意见，AI 重新生成
   - `r` - 完全重新生成
   - `q` - 退出
3. 修改时，将用户反馈与当前内容一起传给 LLM

### 5.4 内容校验

- 检查生成的内容是否包含必要章节（项目背景、技术栈、代码规范）
- 检查 Markdown 格式是否正确
- 校验失败时提示用户并建议补充

## 验收标准

- [ ] 可根据对话摘要生成完整的 AGENTS.md
- [ ] 支持用户反馈后修改
- [ ] 支持完全重新生成
- [ ] 生成的内容包含项目背景、技术栈、代码规范三大章节
- [ ] Markdown 格式正确
