import subprocess
import sys
import json

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

    def run(self):
        initialize = self.send_request("initialize")
        print(f"初始化结果：{initialize}")

        tools_list = self.send_request("tools/list")
        print(f"工具列表：{tools_list}")

        tools_call = self.send_request("tools/call", {
            "name": "cancel_calendar_event",
            "arguments": {"event_title": "去爬山"}
        })
        print(f"工具结果：{tools_call}")

        self.progress.terminate()


if __name__ == "__main__":
    client = SimpleMCPClient([sys.executable, "mcp_server.py"])
    client.run()


