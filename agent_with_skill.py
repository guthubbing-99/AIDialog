from agent_with_tool import weather_tool, cancel_calendar_event_tool

wheather_skill = {
    "name": "weather_skill",
    "description": "处理所有与天气、气温、穿衣建议相关的问题",
    "required_tools": weather_tool,
    "instructions": """你是一个专业的天气助手。
    1. 提取用户输入中的城市名称，如果存在明显的错别字（如“杭巷”），请自动纠正为正确的城市名。
    2. 调用 `get-weather` 工具获取天气数据。
    3. 用简洁、口语化的方式向用户汇报天气情况。
    4. 绝对不要回答任何与天气无关的问题。"""
}

cancel_calendar_skill = {
    "name": "calendar_skill",
    "description": "处理与本地日历日程相关的查询、修改和取消操作",
    "required_tools": cancel_calendar_event_tool,
    "instructions": """你是一个严谨的日程管理助手。
    1. 提取用户想要取消的日程标题关键字。
    2. 在执行删除前，必须用文字向用户确认：“您确定要取消包含‘XXX’的日程吗？”
    3. 获得用户明确同意后，再调用 `cancel_calendar_event` 工具。
    4. 根据工具的返回结果，告知用户操作是否成功。"""
}

SKILL_REGISTZRY = {
    "weather": wheather_skill,
    "calendar": cancel_calendar_skill
}