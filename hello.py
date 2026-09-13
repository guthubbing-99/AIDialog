import anthropic

    # 1. D1-2：裸 SDK 多轮对话 + SSE + SQLite 落库 + 缓存断点 + 指标日志 → 先验证"连续几轮缓存命中、第 N 轮 miss 的成本差"；
    # 2. D3-4：加滚动摘要（Haiku）+ token 阈值触发 + 溢出兜底 → 跑"第 3 轮埋信息、第 20 轮问"的测试看压缩失真；
    # 3. D5+：按需加 长期记忆 / 代码执行沙箱 / RAG / iOS 客户端。
    # export ANTHROPIC_API_KEY="sk-ant-你复制的key"
client = anthropic.Anthropic()

response = client.messages.create(
  model="claude-sonnet-5",
  max_tokens=1024,
  system="你是一个编程助手",
  messages=[
    {"role": "user",
    "content": "用python写一个快排"
    },
  ],
)
print(response.content[0].text);