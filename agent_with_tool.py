from openai import OpenAI
import os
import requests

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

tools = [
    {
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
    }
]

def get_weather(location: str) -> str:
    get_weather_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": location,
        "appid": "",
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

TOOL_REGISTEY = {
    "get-weather": get_weather
}

def execute_tool(name: str, params: object) -> str:
    func = TOOL_REGISTEY.get(name)
    if func is None:
        return f"未知工具: {name}"
    try:
        result = func(params)
        return result
    except Exception as error:
        return f"工具执行异常: {error}"