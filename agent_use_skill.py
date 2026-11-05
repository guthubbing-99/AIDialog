from agent_with_skill import SKILL_REGISTZRY
from openai import OpenAI
import os
from agent_with_tool import tools, execute_tool, validate_tool_args
import json

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

def find_skill(content: str) -> str:
    prompt = f"""
    你是一个专业的skill调用工具，目前提供的skill如下:weather(天气获取),calendar(日历取消)
    用户输入：{content}
    请返回具体的skill名称
    """
    messages = []
    messages.append({"role":"user", "content": prompt})

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=False
    )
    print(f"获取到的skill名称如下：{response.choices[0].message.content}")
    return response.choices[0].message.content.strip()

def loop_test(content: str, history:list = None) -> str:
    skill_name = find_skill(content)
    skill_func = SKILL_REGISTZRY.get(skill_name)
    messages = []
    if skill_func:
        skill_instructions = skill_func["instructions"]
        skill_tool = skill_func["required_tools"]
    else:
        skill_instructions = "you are a helpful assistant"
        skill_tool = []
    messages.append({"role": "system", "content": skill_instructions})
    if history:
       for subHistroy in history:
           if isinstance(subHistroy, dict) and "role" in subHistroy and "content" in subHistroy:
                if subHistroy.get("content") is None:
                    continue
                print(f"history是{subHistroy}")
                messages.append(subHistroy)
    print(f"content是{content}")
    messages.append({"role": "user", "content": content})
    print(f"messages是{messages}")
    request_params = {
        "model": "deepseek-flash",
        "messages": messages,
        "stream": False
    }
    if skill_tool:
        request_params["tools"] = skill_tool
        request_params["tool_choice"] = "auto"
    response = client.chat.completions.create(**request_params)
    assistant_message = response.choices[0].message
    tool_calls = assistant_message.tool_calls
    if tool_calls:
        clean_assistant_message = {
            "role": "assistant",
            "content": assistant_message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in tool_calls
            ]
        }
        history.append(clean_assistant_message)
        messages.append(clean_assistant_message)
        # 工具调用
        for tool_calls_item in tool_calls:
            tool_name = tool_calls_item.function.name
            tool_par = json.loads(tool_calls_item.function.arguments)
            transfer_tool_par = validate_tool_args(tool_name, tool_par)
            result = execute_tool(tool_name, transfer_tool_par)
            sub_tool = {
                "role": "tool",
                "tool_call_id": tool_calls_item.id,
                "content": result
            }
            print(f"sub_tool{sub_tool}")
            print(f"history{history}")
            messages.append(sub_tool)
            history.append(sub_tool)
        tool_stream = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            stream=False
        )
        return tool_stream.choices[0].message
    else:
        return assistant_message
                                    
            

history = []

while True:
    user_input = input("\n你")
    if user_input.lower() in ['exit', 'quit']:
        break
    else:
        res = loop_test(user_input, history)
        print(f"调用skill的结果：{res}")