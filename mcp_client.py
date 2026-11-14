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

    def transfer_to_json(self, content, tools_schema: list) -> list:
        prompt = f"""
        你是一个强大的AI agent。当用户提出包含多个步骤或存在条件依赖的任务时，你必须先输出一个JSON格式的依赖任务。
        JSON格式要求：
        [
            {{
                "step_id": "step1",
                "tool_name": "get_weather",
                "arguments": {{"location": "杭州"}},
                "depends_on": []  
            }},
            {{
                "step_id": "step2",
                "tool_name": "cancel_calendar_event",
                "arguments": {{"event_title": "爬山"}},
                "depends_on": ["step1"]  
            }}
        ]
        用户输入：
        {content}
        并且你的JSON格式中的方法tool_name必须等于下方 name 字段，禁止修改字符：
        {tools_schema}
        注意：depends_on 数组为空表示该步骤可以立即执行；如果包含其他 step_id，则必须等待该步骤执行完毕后再执行。
        """
        messages = []
        messages.append({"role":"user", "content": prompt})
        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            stream=False
        )
        print(f"获取到的JSON列表如下：{response.choices[0].message.content}")
        raw_response = response.choices[0].message.content.strip()
        if raw_response.startswith("```"):
                raw_response = raw_response.split("\n", 1)
                raw_response = raw_response.rsplit("```", 1)[0]
        try:
            json_list = json.loads(raw_response)
            if isinstance(json_list, list):
                return json_list
            else:
                print("大模型返回的不是数组格式，返回空列表")
                return []
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}，返回空列表")
            return []

    def run(self, content: str):
        initialize = self.send_request("initialize")
        print(f"初始化结果：{initialize}")

        tools_list = self.send_request("tools/list")
        print(f"工具列表：{tools_list}")

        tools_schema = tools_list["result"]["tools"]
        json_list = self.transfer_to_json(content, tools_schema)
        step_results = {}
        remaining_steps = { step["step_id"]: step for step in json_list }
        while remaining_steps:
            ready_to_run = []
            for (step_id, step) in remaining_steps.items():
                depends = step.get("depends_on", [])
                if all(depend in step_results for depend in depends):
                    ready_to_run.append(step)
            if not ready_to_run and remaining_steps:
                # 死锁保护：如果还有步骤没执行，但没有步骤可以运行，说明有循环依赖
                return {"error": "检测到循环依赖或依赖缺失"}

            for step in ready_to_run:
                step_id = step["step_id"]
                del remaining_steps[step_id]
                step_tool_name = step["tool_name"]
                step_arguments = step["arguments"]
                tools_call = self.send_request("tools/call", {
                    "name": step_tool_name,
                    "arguments": step_arguments
                })
                print(f"step:{step},工具结果：{tools_call}")
                if tools_call["result"]:
                    text = tools_call["result"]["content"][0]["text"]
                else:
                    text = tools_call["error"]["message"]
                step_results[step_id] = text
        messages = []
        summary_prompt = f"以下是任务执行的结果：{json.dumps(step_results, ensure_ascii=False)}\n请根据结果，用自然语言向用户给出最终回复。"
        messages.append({"role": "system", "content": "you are a helpful aiAgent"})
        messages.append({"role":"user", "content":summary_prompt})
        request_params = {
            "model": "deepseek-flash",
            "messages": messages,
            "stream": False
        }
        response = client.chat.completions.create(**request_params)
        assistant_message = response.choices[0].message
        print(f"最终结果：{assistant_message}")


if __name__ == "__main__":
    cli = SimpleMCPClient([sys.executable, "mcp_server.py"])
    try:
        while True:
            user_input = input("\n你")
            if user_input.lower() in ['exit', 'quit']:
                break
            else:
                cli.run(user_input)
    finally:
        cli.progress.terminate()
    


