"""
AI 服务模块 - 调用 OpenAI API
"""
from typing import AsyncGenerator, Any, Dict, Optional, Tuple
import openai
import logging
import traceback
import json

from .utils.plan_params import build_plan_params_from_schedule

logger = logging.getLogger(__name__)


def _strip_json_code_block(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    return content


async def chat_completion_stream(
    messages: list,
    api_key: str,
    base_url: str,
    model: str
) -> AsyncGenerator[str, None]:
    """
    流式调用 AI API
    
    Args:
        messages: 消息历史列表 [{"role": "user", "content": "..."}, ...]
        api_key: AI API Key
        base_url: AI API Base URL
        model: 模型名称
        
    Yields:
        str: 流式返回的文本片段
    """
    logger.info(f"开始调用 AI API")
    logger.info(f"  Model: {model}")
    logger.info(f"  Base URL: {base_url}")
    logger.info(f"  API Key: {api_key[:10]}..." if api_key else "  API Key: None")
    logger.info(f"  消息数量: {len(messages)}")
    
    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    try:
        logger.info("正在创建流式请求...")
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        
        logger.info("开始接收流式响应...")
        has_content = False
        chunk_count = 0
        
        async for chunk in stream:
            chunk_count += 1
            
            # 详细记录每个 chunk
            logger.debug(f"收到 chunk #{chunk_count}:")
            logger.debug(f"  chunk.choices: {chunk.choices}")
            
            if chunk.choices:
                logger.debug(f"  choices[0].delta: {chunk.choices[0].delta}")
                logger.debug(f"  delta.content: {chunk.choices[0].delta.content}")
                logger.debug(f"  finish_reason: {chunk.choices[0].finish_reason}")
            
            if chunk.choices and chunk.choices[0].delta.content:
                has_content = True
                content = chunk.choices[0].delta.content
                logger.info(f"✅ 收到内容 chunk #{chunk_count}: {content[:50]}...")
                yield content
            else:
                logger.debug(f"⚠️ Chunk #{chunk_count} 没有内容")
        
        logger.info(f"流式响应完成，共收到 {chunk_count} 个 chunk，有内容: {has_content}")
        
        if not has_content:
            logger.warning("AI 返回内容为空")
            yield "⚠️ AI 没有返回任何内容\n\n可能的原因：\n1. API Key 无效或过期\n2. Base URL 配置错误\n3. 模型名称不支持\n4. API 配额不足"
            
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logger.error(f"AI 调用失败: {error_type}: {error_msg}")
        logger.error(f"完整错误:\n{traceback.format_exc()}")
        
        yield f"\n\n❌ 调用失败\n"
        yield f"错误类型: {error_type}\n"
        yield f"错误信息: {error_msg}\n\n"
        yield "请检查：\n"
        yield f"1. Base URL: {base_url}\n"
        yield f"2. 模型名称: {model}\n"
        yield "3. API Key 是否有效\n"
        yield f"\\n\\n❌ 调用失败\\n"
        yield f"错误类型: {error_type}\\n"
        yield f"错误信息: {error_msg}\\n\\n"
        yield "请检查：\\n"
        yield f"1. Base URL: {base_url}\\n"
        yield f"2. 模型名称: {model}\\n"
        yield "3. API Key 是否有效\\n"


async def generate_lesson_plan_content(
    sequence: int,
    plan_item: Optional[Dict[str, Any]],
    system_fields: Optional[Dict[str, Any]],
    document_full_text: str,
    course_context: str,
    api_key: str,
    base_url: str,
    model: str = "gpt-4",
    strict_mode: bool = True,
) -> dict:
    """
    生成教案的结构化内容
    
    Args:
        sequence: 授课顺序
        plan_item: 授课计划条目
        system_fields: 系统计算字段
        document_full_text: 授课计划全文
        course_context: 课程上下文信息
        api_key: OpenAI API Key
        base_url: OpenAI Base URL
        model: 模型名称
        strict_mode: 是否启用系统字段严格校验
        
    Returns:
        结构化的教案数据（字典）
    """
    # 构建提示词（使用用户提供的完整提示词）
    prompt = f"""# Role
你是一位广东碧桂园职业学院的资深专业课教师，擅长进行课程设计和教案编写。你非常熟悉职业教育的教学规范，能根据"授课计划"生成高质量、符合逻辑的教案数据。

# Task
请根据我提供的【基础信息】，按照【生成规则】，生成一份用于自动化教案生成的 JSON 数据。

# Input Data (基础信息)
1. **授课顺序 (Sequence)**: {sequence}
2. **授课计划全文 (Plan Full Content)**:
{document_full_text}
"""

    if system_fields is not None:
        prompt += f"""
3. **系统计算字段 (System Fields)**: {json.dumps(system_fields, ensure_ascii=False)}
"""

    if plan_item is not None:
        prompt += f"""
4. **授课计划条目 (Plan Item)**: {json.dumps(plan_item, ensure_ascii=False)}
"""

    prompt += f"""

# Course Context (课程上下文)
{course_context}

# Constraints & Rules (生成规则)
请严格遵守以下约束，任何违反都将导致任务失败：

## 1. 格式要求
* **输出格式**：必须且只输出一个标准的 JSON 对象。不要包含 Markdown 代码块标记（如 ```json```），不要包含任何解释性文字或多余输出。
* **Key 值命名**：必须严格使用指定的英文 Key：project_name, week, sequence, hours, total_hours, knowledge_goals, ability_goals, quality_goals, teaching_content, teaching_focus, teaching_difficulty, review_content, review_time, new_lessons, assessment_content, summary_content, homework_content。
"""

    if strict_mode:
        prompt += """
* **系统字段必须复用**：`project_name`, `week`, `sequence`, `hours`, `total_hours` 必须与 System Fields 完全一致，不允许改写或重新计算。
* **授课计划条目为唯一依据**：`project_name` 必须完全等于 Plan Item 的 `title`，教学内容与新课教学需围绕 `tasks` 展开。
"""
    else:
        prompt += """
* **字段推断要求**：未提供 System Fields 与 Plan Item 时，`sequence` 必须等于输入的授课顺序，其余 `project_name`、`week`、`hours`、`total_hours` 请结合授课计划全文合理推断并保持一致性。
"""

    prompt += """

## 2. 内容质量规则
* **教学目标 (goals)**：`knowledge_goals`、`ability_goals`、`quality_goals` 三部分。
  * 每部分必须包含至少 3 行内容。
  * 每行必须以 (1)(2)(3) 序号开头。
  * 每行内容不少于 20 字。
  * 每行末尾必须以换行符结束，字段整体必须以换行符结尾。
* **教学内容 (teaching_content)**：这是宏观的教学内容概述。
  * 必须包含至少 2 段。
  * 每段不少于 50 字。
* **重难点 (focus & difficulty)**：包含 `teaching_focus`（重点）和 `teaching_difficulty`（难点）。
  * 每部分至少包含 2 行。
  * 每行以 (1)(2) 序号开头，且每行不少于 20 字。
  * 每行末尾必须以换行符结束，字段整体必须以换行符结尾。
* **复习及新课导入 (review_content)**：
  * 严格使用第一人称（如"我们"、"大家"、"我"），并使用客观书面化语言。
  * 严禁出现主观臆断（例如"大家应该还记得"、"我认为你们已经掌握"之类），应直接陈述事实或逻辑关系。
  * 结构要求包含以下三项：
    1. 回顾上节课核心知识点（客观陈述，不带感情色彩）。
    2. 引入本周新课（基于逻辑递进或项目需要引入）。
    3. 阐述本节课教学目标。
  * 每一项内容不少于 30 字。
  * 每行末尾必须以换行符结束，字段整体必须以换行符结尾。
* **课堂小结 (summary_content)**：
  * 严格使用第一人称客观书面语（如"我们"）。
  * 必须按以下序号分段书写（不要使用其他格式）：
    1. 总结本课程重难点，如[具体知识点]、[具体技能点]等。
    2. 强调相关注意事项，如[具体易错点]、[规范要求]等。
    3. 说明通过何种方式（如提问、练习、巡视等）检测教学目标达成情况，并指出发现的问题将如何在下次课加以修正（不要主观断定学生已经掌握）。
  * 每点内容不少于 30 字。
  * 每行末尾必须以换行符结束，字段整体必须以换行符结尾。
* **作业布置 (homework_content)**：
  * 要求尽量简洁、易做、适合高职学生。
  * 数量为 1~2 份即可。
  * 每行末尾必须以换行符结束，字段整体必须以换行符结尾。

## 3. 时间计算逻辑（核心）
你必须在 JSON 中自动计算时间分配：
* **总时长 (分钟)** = `hours` * 40（系统校验，不需要输出为字段）。
* **固定扣除**：
  * 考核评价 (`assessment_time`) = 10 分钟（固定）。
  * 课堂小结 (`summary_content` 对应时间) = 5 分钟（固定）。
* **动态分配**：
  * 复习导入 (`review_time`)：在 5 到 15 分钟之间灵活设置（整数分钟）。
  * **新课教学 (new_lessons)**：剩余的所有时间必须全部分配给 new_lessons 列表中的各任务点。
* **校验**：必须满足等式： review_time + sum(new_lessons.time) + assessment_time + 5 == hours * 40。

## 4. 新课教学列表 (new_lessons)
* 这是一个列表（List），包含 3 到 5 个任务字典。
* 每个字典必须包含 `content` 和 `time` 两个字段。
* `content` 必须包含"任务名称"和"教师活动"两部分内容。
* 每个 `time` 为整数分钟。

## 5. 额外要求
* 如果输入信息不足，仍必须返回结构完整的 JSON，但所有文字字段填写为："Insufficient input: please provide more details."。
* 严格遵守上述所有约束，任何违反都视为任务失败。

请直接返回 JSON，不要包含任何额外的文字说明。
"""
    
    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一位广东碧桂园职业学院的资深专业课教师，擅长进行课程设计和教案编写。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    content = response.choices[0].message.content.strip()
    content = _strip_json_code_block(content)
    return json.loads(content)


def validate_time_allocation(lesson_plan_data: Dict[str, Any], hours: int) -> Tuple[bool, str]:
    if not isinstance(hours, int) or hours <= 0:
        return False, "无效的学时参数"
    total_minutes = hours * 40
    review_time = lesson_plan_data.get("review_time")
    new_lessons = lesson_plan_data.get("new_lessons")
    if not isinstance(review_time, int) or not (5 <= review_time <= 15):
        return False, "review_time 不在 5-15 分钟范围内"
    if not isinstance(new_lessons, list) or not (3 <= len(new_lessons) <= 5):
        return False, "new_lessons 数量不符合 3-5 项要求"
    new_sum = 0
    for item in new_lessons:
        if not isinstance(item, dict):
            return False, "new_lessons 存在非对象项"
        time_value = item.get("time")
        if not isinstance(time_value, int) or time_value <= 0:
            return False, "new_lessons.time 必须为正整数"
        new_sum += time_value
    if review_time + new_sum + 10 + 5 != total_minutes:
        return False, "时间分配总和不匹配"
    return True, "ok"


async def regenerate_time_allocation(
    lesson_plan_data: Dict[str, Any],
    hours: int,
    api_key: str,
    base_url: str,
    model: str = "gpt-4",
) -> Dict[str, Any]:
    total_minutes = hours * 40
    new_lessons = lesson_plan_data.get("new_lessons") or []
    new_lessons_payload = [
        {"content": item.get("content", "")} for item in new_lessons if isinstance(item, dict)
    ]

    prompt = f"""# Role
你是一名教学教案时间分配审校员。

# Task
仅重新生成时间分配计划，不修改任何教学内容。

# Input
- 本次学时: {hours}
- 总时长(分钟): {total_minutes}
- 固定扣除: 考核评价 10 分钟，课堂小结 5 分钟
- 新课教学内容列表: {json.dumps(new_lessons_payload, ensure_ascii=False)}

# Rules
1. review_time 必须为 5-15 之间的整数分钟。
2. new_lessons 列表必须与输入长度一致，content 不可修改，只能填写 time。
3. time 为正整数，且满足：review_time + sum(time) + 10 + 5 == {total_minutes}。

# Output Format
只输出 JSON 对象，结构如下：
{{
  "review_time": 10,
  "new_lessons": [
    {{"content": "...", "time": 20}}
  ]
}}
"""

    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你只负责时间分配校正。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    content = response.choices[0].message.content.strip()
    content = _strip_json_code_block(content)
    return json.loads(content)


async def parse_teaching_plan_params(
    extracted_text: str,
    course_total_hours: Optional[int],
    api_key: str,
    base_url: str,
    model: str = "gpt-4",
) -> Dict[str, Any]:
    prompt = f"""# Role
你是一名教学计划数据整理员。

# Task
从授课计划文本中提取课次参数，生成结构化 JSON。

# Input
课程总学时（可用于推断单次学时）：{course_total_hours if course_total_hours is not None else "未知"}
授课计划文本：
{extracted_text}

# Output Format
只输出 JSON 对象，结构如下：
{{
  "schedule": [
    {{"week": 1, "order": 1, "title": "项目一：...", "tasks": "1. ...\\n2. ...", "hour": 4}}
  ],
  "hour_per_class": 4
}}

# Rules
1. schedule 为完整课次列表，包含理论/实训/复习考核等所有课次。
2. week 与 order 必须为整数；title 与 tasks 尽量从文本中保留。
3. 若文本未标注学时，可先为空；但需要尽量推断 hour_per_class。
4. 输出必须为标准 JSON，不要包含额外说明或 Markdown。
"""

    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你擅长结构化提取授课计划参数。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    content = response.choices[0].message.content.strip()
    content = _strip_json_code_block(content)
    data = json.loads(content)

    if not isinstance(data, dict):
        raise ValueError("解析结果不是 JSON 对象")
    schedule = data.get("schedule")
    if not isinstance(schedule, list) or not schedule:
        raise ValueError("未提取到课次列表")

    hour_per_class = data.get("hour_per_class")
    if not isinstance(hour_per_class, int) or hour_per_class <= 0:
        if isinstance(course_total_hours, int) and course_total_hours > 0:
            hour_per_class = max(1, round(course_total_hours / len(schedule)))
        else:
            hour_per_class = None

    return build_plan_params_from_schedule(
        schedule,
        hour_per_class=hour_per_class,
    )
