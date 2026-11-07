from agent_with_skill import SKILL_REGISTZRY
from openai import OpenAI
import os
from agent_with_tool import execute_tool, validate_tool_args, execute_all_tools
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

def find_skills(content: str) -> list:
    prompt = f"""
    你是一个专业的skill调用工具，目前提供的skill如下:weather(天气获取),calendar(日历取消)
    用户输入：{content}
    请返回具体的skill名称组成的JSON字符串数组
    """
    messages = []
    messages.append({"role":"user", "content": prompt})

    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        stream=False
    )
    usage = response.usage
    tool_prompt_tokens = getattr(usage, 'prompt_tokens', 0)
    tool_completion_tokens = getattr(usage, 'completion_tokens', 0)
    tool_cache_hit_tokens = getattr(usage, 'prompt_cache_hit_tokens', 0)
    print(f"  [Token 统计 - 决定调用哪个skill的推理]")
    print(f"  第一轮(API请求->决定调skill):")
    print(f"      Prompt={tool_prompt_tokens} | Completion={tool_completion_tokens} | CacheHit={tool_cache_hit_tokens}")
    
    print(f"获取到的skill名称如下：{response.choices[0].message.content}")
    raw_response = response.choices[0].message.content.strip()
    if raw_response.startswith("```"):
        raw_response = raw_response.split("\n", 1)
        raw_response = raw_response.rsplit("```", 1)[0]
    try:
        skill_list = json.loads(raw_response)
        if isinstance(skill_list, list):
            return skill_list
        else:
            print("大模型返回的不是数组格式，返回空列表")
            return []
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}，返回空列表")
        return []

def loop_test(content: str, history:list = None) -> str:
    skill_names = find_skills(content)

    skill_funcs = []
    skill_instructions = []
    skill_tools = []
    for skill_name in skill_names:
        skill_func = SKILL_REGISTZRY.get(skill_name)
        skill_funcs.append(skill_func)
        skill_instruction = skill_func["instructions"]
        skill_instructions.append(skill_instruction)
        required_tools = skill_func.get("required_tools", [])
        print(f"required_tools{required_tools}")
        if required_tools:
            skill_tools.extend(required_tools)
    messages = []
    messages.append({"role": "system", "content": "\n\n".join(skill_instructions)})
    if history:
       for subHistroy in history:
           if isinstance(subHistroy, dict) and "role" in subHistroy and "content" in subHistroy:
                if subHistroy.get("content") is None:
                    continue
                messages.append(subHistroy)
    messages.append({"role": "user", "content": content})
    request_params = {
        "model": "deepseek-flash",
        "messages": messages,
        "stream": False
    }
    if skill_tools:
        print(f"👉 传给大模型的工具结构: {skill_tools}")
        request_params["tools"] = skill_tools
        request_params["tool_choice"] = "auto"
    response = client.chat.completions.create(**request_params)

    assistant_message = response.choices[0].message
    usage = response.usage
    tool_prompt_tokens = getattr(usage, 'prompt_tokens', 0)
    tool_completion_tokens = getattr(usage, 'completion_tokens', 0)
    tool_cache_hit_tokens = getattr(usage, 'prompt_cache_hit_tokens', 0)
    print(f"  [Token 统计 - 决定是否调用工具的推理]")
    print(f"  第二轮(API请求->决定调工具):")
    print(f"      Prompt={tool_prompt_tokens} | Completion={tool_completion_tokens} | CacheHit={tool_cache_hit_tokens}")
    tool_calls = assistant_message.tool_calls
    print(f"tool_calls{tool_calls}")
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
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, execute_all_tools(tool_calls))
            print(f"future{future}")
            results = future.result()
        for i, result in enumerate(results):
            sub_tool = {
                "role": "tool",
                "tool_call_id": tool_calls[i].id,
                "content": result
            }
            messages.append(sub_tool)
            history.append(sub_tool)
        # for tool_calls_item in tool_calls:
        #     tool_name = tool_calls_item.function.name
        #     tool_par = json.loads(tool_calls_item.function.arguments)
        #     transfer_tool_par = validate_tool_args(tool_name, tool_par)
        #     print(f"transfer_tool_par{transfer_tool_par}")
        #     result = execute_tool(tool_name, transfer_tool_par)
        #     sub_tool = {
        #         "role": "tool",
        #         "tool_call_id": tool_calls_item.id,
        #         "content": result
        #     }
        #     messages.append(sub_tool)
        #     history.append(sub_tool)
        tool_stream = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            stream=False
        )
        usage = tool_stream.usage
        tool_prompt_tokens = getattr(usage, 'prompt_tokens', 0)
        tool_completion_tokens = getattr(usage, 'completion_tokens', 0)
        tool_cache_hit_tokens = getattr(usage, 'prompt_cache_hit_tokens', 0)
        print(f"  [Token 统计 - 根据工具结果生成最终答案]")
        print(f"  第三轮(调工具-生成结果):")
        print(f"      Prompt={tool_prompt_tokens} | Completion={tool_completion_tokens} | CacheHit={tool_cache_hit_tokens}")
        return tool_stream.choices[0].message
    else:
        print("未检测到工具调用")
        return assistant_message
                                    
            

history = []

while True:
    user_input = input("\n你")
    if user_input.lower() in ['exit', 'quit']:
        break
    else:
        res = loop_test(user_input, history)
        print(f"调用skill的结果：{res}")