# Please install OpenAI SDK first: `pip3 install openai`
import os
from openai import OpenAI, APIStatusError, APIConnectionError, APITimeoutError
import time
from collections import deque
import re

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")

collectionMaxLength = 3

# 循环询问

# 将上次得到的response.choices[0].message.content插入到这次对话内容中

#直接在终端上运行可对话

def clean_markdown(text: str) -> str:
    if not text:
        return ""
    # 去除代码块
    text = re.sub(r'```[\s\S]*?```', '[已省略代码块]', text)
    # 去除行内代码
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # 去除加粗**或者*
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)

    # 去除标题符号
    text = re.sub(r'^#+\s?', '', text, flags=re.MULTILINE)
    # 去除表格符号
    text = re.sub(r'\|', '', text)
    # 压缩多余换行符
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()

def addMessage(message: str, history:list = None) -> str:
    messages = []

    messages.append(
        {"role": "system", "content": "You are a helpful assistant"}
    )

    if (history is not None):
        for item in history:
            messages.append(item)

    messages.append({"role": "user", "content": message})

    
    retry_times = 3
    for times in range(retry_times):
        try:
            stream = client.chat.completions.create(
                model="deepseek-flash",
                messages=messages,
                stream=True,
                reasoning_effort="low",
                extra_body={"thinking": {"type": "enabled"}}
            )
            fullText = ""
            for chunk in stream:
                if (chunk.choices and chunk.choices[0].delta.content):
                    text = chunk.choices[0].delta.content
                    print(text, end='', flush=True)
                    fullText += text
                if chunk.usage:
                    print(f"Prompt Tokens: {chunk.usage.prompt_tokens}")
            return fullText
        except APIStatusError as e:
            if e.status_code == 400:
                return "请求体格式错误，请根据错误信息提示修改请求体"
            if e.status_code == 401:
                return "API 密钥无效或已过期，请检查环境变量配置。"
            if e.status_code == 402:
                return "账号余额不足，请确认账户余额"
            if e.status_code == 422:
                return "请求体参数错误，请根据错误信息提示修改相关参数"
            if e.status_code == 429:
                # 请求速率达到上限
                time.sleep(3)
                continue
            elif e.status_code >= 500:
                # 500/503 服务端繁忙或故障，同样重试
                time.sleep(3)
                continue
            else:
                return "API业务错误{e.status_code}：{e.message}"
        except (APIConnectionError, APITimeoutError) as e:
            # 处理网络抖动，连接超时
            wait_time = min(2 ** times + random.uniform(0,1), 30)
            print(f"网络异常 ({type(e).__name__})，{wait_time:.2f}秒后重试...")
            time.sleep(wait_time)
            continue
        except Exception as e:
            return "未知错误：{str(e)}"


last_history = deque(maxlen=collectionMaxLength)
middle_history = deque(maxlen=collectionMaxLength+1)

while True:
    user_input = input("\n你")
    if user_input.lower() in ['exit', 'quit']:
        break
    responseText = addMessage(user_input, last_history)
    if len(last_history) >= collectionMaxLength:
        middle_history.append(last_history[0])
    last_history.append({"role": "user", "content": user_input})

    if len(last_history) >= collectionMaxLength:
        middle_history.append(last_history[0])
    clearResponseText = clean_markdown(responseText)
    last_history.append({"role": "assistant", "content": clearResponseText})

    if len(middle_history) >= collectionMaxLength:
        # 中期记忆提取关键字
        history_lines = [f"{item['role']}:{item['content']}" for item in middle_history]
        fullText = ';'.join(history_lines)
        summary_prompt_template = """
        请总结下边的历史聊天内容。
        要求：
        1.保留用户长期信息
        2.保留用户目标
        3.保留重要事实
        4.删除寒暄内容
        5.删除重复内容
        6.输出简洁摘要
        7.需要区分role
        历史聊天：
        {history}
        """
        final_format = summary_prompt_template.format(history=fullText)
        print('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
        print(final_format)
    
