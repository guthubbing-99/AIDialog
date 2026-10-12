# Please install OpenAI SDK first: `pip3 install openai`
import os
from openai import OpenAI, APIStatusError, APIConnectionError, APITimeoutError
import time
from collections import deque
import re
import random

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")

collectionMaxLength = 4

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

def summarize_history(summaryMessages: list) -> str:
    summary_lines = [f"{item['role']}:{item['content']}" for item in summaryMessages]
    fullText = '\n'.join(summary_lines)
    prompt = f"""
    你是一个对话记忆压缩器。请将以下对话历史提炼为一段简洁的摘要。
    要求：
    1. 提取核心事实、用户偏好和关键目标。
    2. 忽略寒暄、重复内容和无关紧要的细节。
    3. 以第三人称或客观视角描述（例如：“用户询问了...，助手解释了...”）。
    4. 尽量控制在 200 字以内。
    
    对话历史：
    {fullText}
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"摘要生成失败: {e}")
        return ""
    

def addMessage(message: str, history:list = None, long_term_history: str = None) -> str:
    messages = []

    sys_content = "You are a helpful assistant"
    if long_term_history and long_term_history.strip():
        sys_content += f"，历史摘要如下：{long_term_history}"
    messages.append({"role": "system", "content": sys_content})

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
                stream_options={"include_usage": True},
                reasoning_effort="low",
                extra_body={"thinking": {"type": "enabled"}}
            )
            fullText = ""
            cached_tokens = 0
            total_prompt_tokens = 0
            for chunk in stream:
                if (chunk.choices and chunk.choices[0].delta.content):
                    text = chunk.choices[0].delta.content
                    print(text, end='', flush=True)
                    fullText += text
                if hasattr(chunk, "usage") and chunk.usage:
                    total_prompt_tokens = getattr(chunk.usage, 'prompt_tokens', 0)
                    cached_tokens = getattr(chunk.usage, 'prompt_cache_hit_tokens', 0)
            if total_prompt_tokens > 0:
                hit_rate = (cached_tokens / total_prompt_tokens) * 100
                print(f"\n[Token 统计] 总 Prompt Tokens: {total_prompt_tokens} | 缓存命中 Tokens: {cached_tokens} | 命中率: {hit_rate:.2f}%")
            else:
                print("\n[Token 统计] 未获取到 Token 用量信息")
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
                return f"API业务错误{e.status_code}：{e.message}"
        except (APIConnectionError, APITimeoutError) as e:
            # 处理网络抖动，连接超时
            wait_time = min(2 ** times + random.uniform(0,1), 30)
            print(f"网络异常 ({type(e).__name__})，{wait_time:.2f}秒后重试...")
            time.sleep(wait_time)
            continue
        except Exception as e:
            return f"未知错误：{str(e)}"


last_history = deque(maxlen=collectionMaxLength)
middle_history = []
prompt_history = []

while True:
    user_input = input("\n你")
    if user_input.lower() in ['exit', 'quit']:
        break
    long_term_history = '\n'.join(prompt_history)
    responseText = addMessage(user_input, last_history, long_term_history)
    if len(last_history) >= collectionMaxLength:
        middle_history.append(last_history.popleft())
    last_history.append({"role": "user", "content": user_input})

    if len(last_history) >= collectionMaxLength:
        middle_history.append(last_history.popleft())
    clearResponseText = clean_markdown(responseText)
    last_history.append({"role": "assistant", "content": clearResponseText})

    if len(middle_history) >= collectionMaxLength:
        # 中期记忆提取关键字
        prompt = summarize_history(middle_history)
        print(prompt)
        middle_history.clear()
        prompt_history.append(prompt)
    
