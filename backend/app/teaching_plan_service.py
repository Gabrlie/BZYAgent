"""
授课计划生成服务 - AI 生成 schedule
"""
import json
import math
from typing import Dict, Any, List, Optional
import openai



async def generate_schedule_frame(
    total_weeks: int,
    classes_per_week: int,
    actual_classes: int,
    skip_weeks: str,
    api_key: str,
    base_url: str,
    model: str
) -> List[Dict[str, int]]:
    """
    Step 1: 智能体 - 排课专家
    只负责生成周次安排 (Week Schedule)，处理复杂的周次跳过、节假日逻辑。
    返回: [{"order": 1, "week": 1}, {"order": 2, "week": 2}, ...]
    """
    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    prompt = f"""# Role
你是排课专家，负责计算每一节课所在的周次。

# Input
- 总周数: {total_weeks}
- 每周上课次数: {classes_per_week}
- 总共需要排多少次课: {actual_classes}
- **排课调整说明** (skip_weeks): {skip_weeks if skip_weeks else "无"}

# Rules
1. 默认情况下，课程按顺序填入每周。例如每周2次，则第1、2次课在第1周，第3、4次课在第2周。
2. **最高优先级**：必须严格执行"排课调整说明"。
   - 示例 "第3周周五开始" (每周5次): 前面周次空白。第1次课在第3周。
   - 示例 "第1周只上1次": 第1次课在第1周，第2次课在第2周（假设每周2次）。
   - 示例 "第8周国庆放假": 任何课都不能排在第8周，相关课程顺延到第9周。
3. 输出必须包含所有 {actual_classes} 次课的安排。

# Output Format
JSON 数组，每项包含 `order` (1..{actual_classes}) 和 `week`。
示例:
[
  {{"order": 1, "week": 1}},
  {{"order": 2, "week": 1}},
  ...
]
"""
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是由Python调用的排课计算引擎。只输出JSON数据。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2 # 低温度，保证逻辑严密
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except Exception as e:
        print(f"排课计算失败: {e}")
        # Fallback: 使用默认公式
        schedule = []
        current_order = 1
        for w in range(1, total_weeks + 1):
            for _ in range(classes_per_week):
                if current_order > actual_classes:
                    break
                schedule.append({"order": current_order, "week": w})
                current_order += 1
        return schedule


async def generate_teaching_plan_schedule(
    course_catalog: str,
    course_name: str,
    total_hours: int,
    theory_hours: int,
    practice_hours: int,
    hour_per_class: int,
    total_weeks: int,
    classes_per_week: int,
    final_review: bool,
    api_key: str,
    base_url: str,
    model: str = "gpt-4",
    skip_weeks: Optional[str] = None  # 新增参数：排课调整说明
) -> List[Dict[str, Any]]:
    """
    生成授课计划表
    
    Args:
        course_catalog: 课程目录
        course_name: 课程名称
        total_hours: 总学时
        theory_hours: 理论学时
        practice_hours: 实训学时
        hour_per_class: 单次学时
        total_weeks: 总周数
        classes_per_week: 每周上课次数
        final_review: 是否最后一次课为复习考核
        api_key: OpenAI API Key
        base_url: OpenAI Base URL
        model: 模型名称
        
    Returns:
        授课计划表（列表）
    """
    # 计算最大课次和实际课次
    max_classes = total_weeks * classes_per_week
    actual_classes = total_hours // hour_per_class  # 根据总学时计算实际课次
    classes_to_generate = actual_classes - 1 if final_review else actual_classes
    
    # 校验：仅保留基本校验，移除严格的课次差校验，交由 AI 处理
    if actual_classes > max_classes:
        raise ValueError(
            f"课程需要 {actual_classes} 次课（{total_hours} 学时），"
            f"但只有 {max_classes} 次课时间（{total_weeks} 周）。"
            f"请增加周数或每周上课次数。"
        )
    
    # 计算理论和实训的大致课次
    theory_classes_count = round(theory_hours / hour_per_class)
    practice_classes_count = actual_classes - theory_classes_count
    
    # Step 1: 调用排课智能体生成周次框架
    # ---------------------------------------------------------
    schedule_frame = await generate_schedule_frame(
        total_weeks=total_weeks,
        classes_per_week=classes_per_week,
        actual_classes=actual_classes,
        skip_weeks=skip_weeks,
        api_key=api_key,
        base_url=base_url,
        model=model
    )
    
    # 提取最后一次课的 Week 信息（用于复习课）
    last_class_frame = schedule_frame[-1] if schedule_frame else {"week": total_weeks, "order": actual_classes}

    # Step 2: 调用内容生成智能体
    # ---------------------------------------------------------
    # 调整生成数量
    classes_to_gen_content = actual_classes - 1 if final_review else actual_classes
    
    # 截取需要生成内容的 frame
    content_frame = schedule_frame[:classes_to_gen_content]
    
    # 构建 AI 提示词
    prompt = f"""# Role
你是广东碧桂园职业学院的资深教学管理人员。

# Task
根据已定的周次安排（Schedule Frame）和课程目录，填充教学内容。

# Input Data
- 课程名称：{course_name}
- 理论学时：{theory_hours}（约 {theory_classes_count} 次课）
- 实训学时：{practice_hours}（约 {practice_classes_count} 次课）
- **已定课表框架**：{json.dumps(content_frame, ensure_ascii=False)}

# 课程目录
{course_catalog}

# Rules
1. **严格遵守已定课表**：你必须严格按照 Input Data 中的 `week` 和 `order` 填充内容。不要修改周次。
2. **学时分配**：
   - 确保理论课约 {theory_classes_count} 次，实训课约 {practice_classes_count} 次。
   - **标题格式重要规则**：
     - 正确示例：`项目一：计算机基础` 或 `实训项目一：Word应用`
     - 错误示例：`[理论] 项目一：...` 或 `项目一：... [实训]`
     - **必须保留** `项目X：` 或 `实训项目X：` 前缀，以区分理论与实训。
     - **必须移除** 任何中括号标签（如 `[理论]`、`[实训]`）。
3. **内容生成**：
   - 根据 order 顺序和课程目录进度安排教学。
   - **Task 格式**：必须使用 "1. ", "2. ", "3. " 序号列表（不用 "任务1" 或 "1-1"）。
   - 每个项目内序号从 1 开始。
   - 多个任务点用 \\n 分隔。
4. **禁止事项**：
   - ❌ 绝对不要生成第 {actual_classes} 次课的"复习考核"内容！这部分由系统单独处理。

# Output Format
JSON 数组，结构如下：
[
  {{
    "week": 1, 
    "order": 1, 
    "title": "项目1：计算机基础（无需标签）", 
    "tasks": "1. 计算机组成原理\\n2. 操作系统安装", 
    "hour": {hour_per_class}
  }},
  ...
]
"""
    
    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你负责填充教学计划内容。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    content = response.choices[0].message.content.strip()
    
    # 提取 JSON
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    
    schedule = json.loads(content)
    
    # 如果需要，添加最后一次课（复习考核）
    if final_review:
        # 使用排课智能体算出的周次
        rv_week = last_class_frame["week"]
        rv_order = last_class_frame["order"]
        
        schedule.append({
            "week": rv_week,
            "order": rv_order,
            "title": "课程复习与考核",
            "tasks": "1. 期末知识复习\n2. 课程考核与讲评",
            "hour": hour_per_class
        })
    
    return schedule
