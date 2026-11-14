import subprocess
import requests
import sys
import json

def get_weather(location: str) -> str:
    get_weather_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": location,
        "appid": "54e90e94c7a25855183495d1fb768f0f",
        "units": "metric",
        "lang": "zh_cn",
    }
    try: 
        response = requests.get(get_weather_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        humidity = data["main"]["humidity"]
        return f"{location} 当前天气：{desc}，气温 {temp}°C，湿度 {humidity}%"
    except Exception as error:
        return f"获取天气异常：{error}"

def cancel_calendar_event(event_title: str) -> str:
    try:
        path = "./calendar_control.scpt"
        result = subprocess.run(
            ["osascript", path, "cancel_by_title", event_title],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"AppleScript 执行失败: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "取消日程超时"
    except Exception as e:
        return f"操作系统异常：{e}"

def handle_request(request):
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"serverInfo": {"name": "My-MCP-Server", "version": "1.0.0"}}}
    elif method == "tools/list":
        tools = [
            {
                "name": "get_weather",
                "description": "get weather",
                "inputSchema": {
                    "type": "object",
                    "properties": {"location": {"type": "str"}},
                    "required": ["location"]
                }
            },
            {
                "name": "cancel_calendar_event",
                "description": "del calendar event",
                "inputSchema": {
                    "type": "object",
                    "properties": {"event_title": {"type": "str"}},
                    "required": ["event_title"]
                }
            },
        ]
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}
    elif method == "tools/call":
        if params.get("name") == "get_weather":
            location = params["arguments"]["location"]
            result = get_weather(location)
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": result}]}}
        elif params.get("name") == "cancel_calendar_event":
            event_title = params["arguments"]["event_title"]
            result = cancel_calendar_event(event_title)
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": result}]}}
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"content": {"code": -1, "message": "未知方法"}}}
    else:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"content": {"code": -1, "message": "未知方法"}}}

if __name__ == "__main__":
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            request = json.loads(line)
            result = handle_request(request)
            sys.stdout.write(json.dumps(result) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err = {"jsonrpc": "2.0", "error": {"code": -1, "message": str(e)}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()