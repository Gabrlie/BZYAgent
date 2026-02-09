"""
AI 服务模块 - 调用 OpenAI API
"""
from typing import AsyncGenerator
import openai
import logging
import traceback
import json

logger = logging.getLogger(__name__)


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
    documents: str,
    course_context: str,
    api_key: str,
    base_url: str,
    model: str = "gpt-4"
) -> dict:
    """
    生成教案的结构化内容
    
    Args:
        sequence: 授课顺序
        documents: 文档内容
        course_context: 课程上下文信息
        api_key: OpenAI API Key
        base_url: OpenAI Base URL
        model: 模型名称
        
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
2. **文档内容 (documents)**: 
{documents}

# Course Context (课程上下文)
{course_context}

# Constraints & Rules (生成规则)
请严格遵守以下约束，任何违反都将导致任务失败：

## 1. 格式要求
* **输出格式**：必须且只输出一个标准的 JSON 对象。不要包含 Markdown 代码块标记（如 ```json```），不要包含任何解释性文字或多余输出。
* **Key 值命名**：必须严格使用指定的英文 Key：project_name, week, sequence, hours, total_hours, knowledge_goals, ability_goals, quality_goals, teaching_content, teaching_focus, teaching_difficulty, review_content, review_time, new_lessons, assessment_content, summary_content, homework_content。

## 2. 内容质量规则
* **教学目标 (goals)**：`knowledge_goals`、`ability_goals`、`quality_goals` 三部分。
  * 每部分必须包含至少 3 行内容。
  * 每行必须以 (1)(2)(3) 序号开头。
  * 每行内容不少于 20 字。
* **教学内容 (teaching_content)**：这是宏观的教学内容概述。
  * 必须包含至少 2 段。
  * 每段不少于 50 字。
* **重难点 (focus & difficulty)**：包含 `teaching_focus`（重点）和 `teaching_difficulty`（难点）。
  * 每部分至少包含 2 行。
  * 每行以 (1)(2) 序号开头，且每行不少于 20 字。
* **复习及新课导入 (review_content)**：
  * 严格使用第一人称（如"我们"、"大家"、"我"），并使用客观书面化语言。
  * 严禁出现主观臆断（例如"大家应该还记得"、"我认为你们已经掌握"之类），应直接陈述事实或逻辑关系。
  * 结构要求包含以下三项：
    1. 回顾上节课核心知识点（客观陈述，不带感情色彩）。
    2. 引入本周新课（基于逻辑递进或项目需要引入）。
    3. 阐述本节课教学目标。
  * 每一项内容不少于 30 字。
* **课堂小结 (summary_content)**：
  * 严格使用第一人称客观书面语（如"我们"）。
  * 必须按以下序号分段书写（不要使用其他格式）：
    1. 总结本课程重难点，如[具体知识点]、[具体技能点]等。
    2. 强调相关注意事项，如[具体易错点]、[规范要求]等。
    3. 说明通过何种方式（如提问、练习、巡视等）检测教学目标达成情况，并指出发现的问题将如何在下次课加以修正（不要主观断定学生已经掌握）。
  * 每点内容不少于 30 字。
* **作业布置 (homework_content)**：
  * 要求尽量简洁、易做、适合高职学生。
  * 数量为 1~2 份即可。

## 3. 时间计算逻辑（核心）
你必须在 JSON 中自动计算时间分配：
* **总时长 (分钟)** = `hours` * 40（输出 numeric 类型）。
* **固定扣除**：
  * 考核评价 (`assessment_time`) = 10 分钟（固定）。
  * 课堂小结 (`summary_content` 对应时间) = 5 分钟（固定）。
* **动态分配**：
  * 复习导入 (`review_time`)：在 5 到 15 分钟之间灵活设置（整数分钟）。
  * **新课教学 (new_lessons)**：剩余的所有时间必须全部分配给 new_lessons 列表中的各任务点。
* **校验**：必须满足等式： review_time + sum(new_lessons.time) + assessment_time + 5 == total_hours。
  * 若无法精确匹配，请按比例调整 new_lessons 中每项的 time（向下取整后适当分配余数），并在 JSON 中新增键 `adjustment_note`（简短说明调整原因，英文或中文均可，最多 40 字）。

## 4. 新课教学列表 (new_lessons)
* 这是一个列表（List），包含 3 到 5 个任务字典。
* 每个字典必须包含 `content` 和 `time` 两个字段。
* `content` 必须包含"任务名称"和"教师活动"两部分内容。
* 每个 `time` 为整数分钟。

## 5. 额外要求
* 如果 documents 为空或信息不足，仍必须返回结构完整的 JSON，但所有文字字段填写为："Insufficient input: please provide more details."。
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
    
    # 尝试提取 JSON（如果 AI 返回了 markdown 代码块）
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    
    return json.loads(content)
