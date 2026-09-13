# Please install OpenAI SDK first: `pip3 install openai`
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")

# 循环询问

# 将上次得到的response.choices[0].message.content插入到这次对话内容中

#直接在终端上运行可对话

def addMessage(message: str, history:[] = None) -> str:
    messages = []

    messages.append(
        {"role": "system", "content": "You are a helpful assistant"}
    )

    if (history is not None):
        for item in history:
            messages.append(item)

    messages.append({"role": "user", "content": message})

    

    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        stream=False,
        reasoning_effort="low",
        extra_body={"thinking": {"type": "enabled"}}
    )

    return response.choices[0].message.content


last_history = []

while True:
    user_input = input("\n你")
    if user_input.lower() in ['exit', 'quit']:
        break
    responseText = addMessage(user_input, last_history)
    last_history.append({"role": "user", "content": user_input})
    last_history.append({"role": "system", "content": responseText})

    print(responseText)
    
