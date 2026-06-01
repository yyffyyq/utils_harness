"""最小化 LLM API 调用测试 —— 在命令行直接运行。

用法:
    python test_api.py
"""

from harness.utils.config import Settings
from harness.llm.client import QwenClient

settings = Settings()
print(f"模型: {settings.model_name}")
print(f"API:  {settings.qwen_base_url}")
print(f"Key:  {settings.qwen_api_key[:8]}...{settings.qwen_api_key[-4:]}")
print("-" * 50)

client = QwenClient(settings)

# --- 测试 1: 普通调用 ---
print("\n[测试 1] 普通 chat() 调用:")
response = client.chat(
    [{"role": "user", "content": "用一句话介绍你自己"}]
)
print(f"回复: {response}")

# --- 测试 2: 流式调用 ---
print("\n[测试 2] 流式 chat_stream() 调用:")
print("回复: ", end="", flush=True)
for chunk in client.chat_stream(
    [{"role": "user", "content": "Python 有哪些优点？列出 3 点，每点一句话。"}]
):
    print(chunk, end="", flush=True)
print()

# --- 测试 3: enable_thinking ---
print("\n[测试 3] enable_thinking=True 深度思考调用:")
result = client.chat(
    [{"role": "user", "content": "1+1等于几？"}],
    enable_thinking=True,
    max_tokens=512,
)
if isinstance(result, dict):
    print(f"思考过程: {result.get('reasoning', '(无)')[:200]}...")
    print(f"最终回答: {result['content']}")
else:
    print(f"回复: {result}")

print("\n✅ 全部 API 测试完成!")
