import subprocess
import sys
import json
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

class SimpleMCPClient:
    def __init__(self, server_cmd):
        self.progress = subprocess.Popen(
            server_cmd,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.req_id = 0

    def send_request(self, method, params=None):
        # 发送 JSON-RPC 请求并获取响应
        self.req_id += 1
        request = {"jsonrpc": "2.0", "id": self.req_id, "method": method, "params": params or {}}
        # 写入Server的stdin
        self.progress.stdin.write(json.dumps(request) + "\n")
        self.progress.stdin.flush()
        # 从Server的stdout中读结果
        response_result = self.progress.stdout.readline()
        return json.loads(response_result)

    def send_notifications(self, method, params=None):
        request = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        self.progress.stdin.write(json.dumps(request) + "\n")
        self.progress.stdin.flush()

    def run(self, content: str):
        if not hasattr(self, "tools_schema"):
            initialize = self.send_request("initialize")
            print(f"初始化结果：{initialize}")

            self.send_notifications("notifications/initialized")

            tools_list = self.send_request("tools/list")
            print(f"工具列表：{tools_list}")
            tools_schema = tools_list["result"]["tools"]

        messages = [{
            "role": "system",
            "content": """你是一个超级 AI Agent，采用ReAct模式解决问题。\n
            每次回复必须严格遵循以下格式之一：\n
            1.需要调用工具时，只输出JSON，{\"tool_name\": \"工具名\", \"arguments\": {\"参数名\": \"参数值\"}}\n""}
            2.任务完成或不需要调用工具时，直接输出最终的自然语言回复。\n
            不要输出任何多余思考过程或解释，直接输出JSON或者最终答复
            """
        },
        {"role": "user", "content": content}]
        max_rounds = 10
        for round_num in range(max_rounds):
            response = client.chat.completions.create(
                model="deepseek-flash",
                messages=messages,
                stream=False
            )
            aiassistant_message = response.choices[0].message.content.strip()
            if not aiassistant_message.startswith("{"):
                print(f"\n✅ 任务完成，最终回复: {aiassistant_message}")
                return aiassistant_message
            try:
                action = json.loads(aiassistant_message)
                tool_name = action["tool_name"]
                tool_args = action["arguments"]
            except Exception as e:
                observation = "JSON解析失败，请重新输出正确的JSON格式"
                messages.append({"role":"assistant", "content": aiassistant_message})
                messages.append({"role":"user", "content": observation})
                continue
            tools_call = self.send_request("tools/call", {
                "name": tool_name,
                "arguments": tool_args
            })
            print(f"工具结果：{tools_call}")
            if "result" in tools_call:
                text = tools_call["result"]["content"][0]["text"]
            else:
                text = tools_call["error"].get('message')
            messages.append({"role":"assistant", "content": aiassistant_message})
            messages.append({"role":"user", "content": text})
        return "达到最大循环次数，任务未能完成。"

if __name__ == "__main__":
    cli = SimpleMCPClient([sys.executable, "fast_mcp_server.py"])
    try:
        while True:
            user_input = input("\n你")
            if user_input.lower() in ['exit', 'quit']:
                break
            else:
                cli.run(user_input)
    finally:
        cli.progress.terminate()