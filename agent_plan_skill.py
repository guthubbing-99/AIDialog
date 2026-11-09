from agent_with_skill import SKILL_REGISTRY
from openai import OpenAI
import os
from agent_with_tool import execute_tool, validate_tool_args, execute_all_tools,execute_all_tools_parallel
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from typing import Tuple

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

def transfer_to_json(content: str) -> list:
    prompt = f"""
    你是一个强大的AI agent。当用户提出包含多个步骤或存在条件依赖的任务时，你必须先输出一个JSON格式的依赖任务。
    JSON格式要求：
    [
        {{
            "step_id": "step1",
            "tool_name": "get-weather",
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

def run_step(step, step_results) -> Tuple[str, str]:
    # 返回step_id和result
    step_id = step["step_id"]
    step_tool_name = step["tool_name"]
    step_arguments = step["arguments"]
    step_depends_on = step.get("depends_on", [])

    for depend in step_depends_on:
        if depend not in step_results:
            return (step_id, f"依赖步骤 {depend} 未执行或执行失败")
    result = execute_tool(step_tool_name, step_arguments)
    return (step_id, result)

def execute_dag_plan(content: str) -> dict:
    json_list = transfer_to_json(content)
    step_results = {}
    with ThreadPoolExecutor() as executor:
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

            new_futures = {}
            # 并行执行所有准备好的设备
            for step in ready_to_run:
                step_id = step["step_id"]
                del remaining_steps[step_id]
                future = executor.submit(run_step, step, step_results)
                new_futures[future] = step_id
            # 等待这一批并行任务完成
            if new_futures:
                wait(new_futures, return_when=ALL_COMPLETED)
                for future in new_futures:
                    step_id, result = future.result()
                    step_results[step_id] = result
    return step_results

def loop_test(content: str, history:list = None) -> str:
    step_results = execute_dag_plan(content)
    messages = []
    result = " ".join(step_results.values())
    messages.append({"role": "system", "content": "you are a helpful aiAgent"})
    if history:
       for subHistroy in history:
           if isinstance(subHistroy, dict) and "role" in subHistroy and "content" in subHistroy:
                if subHistroy.get("content") is None:
                    continue
                messages.append(subHistroy)
    messages.append({"role":"user", "content":result})
    request_params = {
        "model": "deepseek-flash",
        "messages": messages,
        "stream": False
    }
    response = client.chat.completions.create(**request_params)
    assistant_message = response.choices[0].message
    return assistant_message

history = []

while True:
    user_input = input("\n你")
    if user_input.lower() in ['exit', 'quit']:
        break
    else:
        res = loop_test(user_input, history)
        print(f"调用skill的结果：{res}")