from openai import OpenAI
import os
import requests
from pydantic import BaseModel, Field
from pydantic import ValidationError
import subprocess

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")

class WeatherParameters(BaseModel):
    location: str = Field(..., description="城市名称，比如杭州上海等")

class CalendarCancelParameters(BaseModel):
    event_title: str = Field(..., description="日程名称，比如去杭州等")

weather_tool = {
    "type": "function",
    "function": {
        "name": "get-weather",
        "description": """a tool to get weather. if the user's input contains obvious types or
        phonetic errors(e.g., '杭巷' instead of '杭州'),please automatically corrent the city name 
        before calling this tools.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "the city of get weather",
                },
            },
            "required": ["location"]
        }
    },
},

cancel_calendar_event_tool = {
    "type": "function",
    "function": {
        "name": "cancel_calendar_event",
        "description": "a tool to cancel calendar event with eventTitle",
        "parameters": {
            "type": "object",
            "properties": {
                "event_title": {
                    "type": "string",
                    "description": "the cancel calendar event title",
                },
            },
            "required": ["event_title"]
        }
    },
}

tools = [
    weather_tool,
    cancel_calendar_event_tool
]

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

TOOL_REGISTEY = {
    "get-weather": get_weather,
    "cancel_calendar_event": cancel_calendar_event
}

TOOL_SCHEMAS = {
    "get-weather": WeatherParameters,
    "cancel_calendar_event": CalendarCancelParameters
}

def validate_tool_args(tool_name: str, params: dict) -> dict:
    model = TOOL_SCHEMAS.get(tool_name)
    if model is None:
        raise ValueError(f"未知工具：{tool_name}")
    try:
        # pydantic会自动做类型转换和校验
        validated = model(**params)
        return validated.model_dump() # 返回清洗后的标准参数
    except ValidationError as e:
        error_details = []
        for error in e.errors():
            error_details.append(f"字段 '{error['loc'][0]}': '{error['msg']}' 收到的值：{error.get('input')}")
        raise ValueError(f"工具：{tool_name}参数校验失败：\n" + "\n".join(error_details))

def execute_tool(name: str, params: object) -> str:
    func = TOOL_REGISTEY.get(name)
    if func is None:
        return f"未知工具: {name}"
    try:
        result = func(params)
        return result
    except Exception as error:
        return f"工具执行异常: {error}"