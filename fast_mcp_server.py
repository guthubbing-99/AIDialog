#from mcp.server.fastmcp import FastMCP
from fastmcp import FastMCP
import requests
import subprocess

mcp = FastMCP("My-Awesome-Agent-Server")

@mcp.tool()
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

@mcp.tool()
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

if __name__ == "__main__":
    mcp.run()