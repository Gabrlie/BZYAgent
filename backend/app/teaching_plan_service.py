"""
授课计划生成服务 - 系统排课 + AI 生成内容
"""
import json
from typing import Dict, Any, List, Optional
import openai


def _get_week_class_limit(week: int, first_week_classes: int, classes_per_week: int) -> int:
    if week == 1:
        return first_week_classes
    return classes_per_week


def build_schedule_frame(
    total_weeks: int,
    classes_per_week: int,
    actual_classes: int,
    first_week_classes: int,
    skip_slots: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, int]]:
    """
    系统排课规则：
    - 第 1 周上 first_week_classes 次课
    - 其余周按 classes_per_week 次课
    - skip_slots 指定哪一周哪一次不上课
    - 依次填充，直到排满 actual_classes 次课
    返回: [{"order": 1, "week": 1}, ...]
    """
    if total_weeks < 1 or classes_per_week < 1:
        return []

    classes_per_week = max(1, min(7, classes_per_week))
    first_week_classes = max(1, min(classes_per_week, first_week_classes))

    skip_set = set()
    for item in skip_slots or []:
        try:
            week = int(item.get('week'))
            class_index = item.get('class') or item.get('class_index') or item.get('session')
            class_index = int(class_index)
        except Exception:
            continue
        week_limit = _get_week_class_limit(week, first_week_classes, classes_per_week)
        if 1 <= week <= total_weeks and 1 <= class_index <= week_limit:
            skip_set.add((week, class_index))

    schedule: List[Dict[str, int]] = []
    for week in range(1, total_weeks + 1):
        week_limit = _get_week_class_limit(week, first_week_classes, classes_per_week)
        for class_index in range(1, week_limit + 1):
            if (week, class_index) in skip_set:
                continue
            schedule.append({"order": len(schedule) + 1, "week": week})
            if len(schedule) >= actual_classes:
                return schedule
    return schedule


def count_available_slots(
    total_weeks: int,
    classes_per_week: int,
    first_week_classes: int,
    skip_slots: Optional[List[Dict[str, Any]]] = None,
) -> int:
    if total_weeks < 1 or classes_per_week < 1:
        return 0

    classes_per_week = max(1, min(7, classes_per_week))
    first_week_classes = max(1, min(classes_per_week, first_week_classes))

    skip_set = set()
    for item in skip_slots or []:
        try:
            week = int(item.get('week'))
            class_index = item.get('class') or item.get('class_index') or item.get('session')
            class_index = int(class_index)
        except Exception:
            continue
        week_limit = _get_week_class_limit(week, first_week_classes, classes_per_week)
        if 1 <= week <= total_weeks and 1 <= class_index <= week_limit:
            skip_set.add((week, class_index))

    available_slots = 0
    for week in range(1, total_weeks + 1):
        week_limit = _get_week_class_limit(week, first_week_classes, classes_per_week)
        for class_index in range(1, week_limit + 1):
            if (week, class_index) in skip_set:
                continue
            available_slots += 1
    return available_slots


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
    first_week_classes: int = 1,
    skip_slots: Optional[List[Dict[str, Any]]] = None,
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
        first_week_classes: 第一周上课次数
        skip_slots: 不上课的周次与次序列表

    Returns:
        授课计划表（列表）
    """
    # 计算最大课次和实际课次
    max_classes = total_weeks * classes_per_week
    actual_classes = total_hours // hour_per_class  # 根据总学时计算实际课次
    # 校验：仅保留基本校验
    if actual_classes > max_classes:
        raise ValueError(
            f"课程需要 {actual_classes} 次课（{total_hours} 学时），"
            f"但只有 {max_classes} 次课时间（{total_weeks} 周）。"
            f"请增加周数或每周上课次数。"
        )

    # 计算理论和实训的大致课次
    theory_classes_count = round(theory_hours / hour_per_class)
    practice_classes_count = actual_classes - theory_classes_count

    # Step 1: 系统生成周次框架
    # ---------------------------------------------------------
    available_slots = count_available_slots(
        total_weeks=total_weeks,
        classes_per_week=classes_per_week,
        first_week_classes=first_week_classes,
        skip_slots=skip_slots,
    )
    diff = available_slots - actual_classes
    if diff < 0:
        raise ValueError(
            f"排课参数不匹配：需要 {actual_classes} 次课，但可用课次为 {available_slots} 次。"
            "请调整第一周上课次数、每周上课次数或不上课设置。"
        )
    if diff > 6:
        raise ValueError(
            f"排课参数差额过大：需要 {actual_classes} 次课，但可用课次为 {available_slots} 次。"
            "差额不能超过 6 次，请调整参数。"
        )

    schedule_frame = build_schedule_frame(
        total_weeks=total_weeks,
        classes_per_week=classes_per_week,
        actual_classes=actual_classes,
        first_week_classes=first_week_classes,
        skip_slots=skip_slots,
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
   - 多个任务点用 \n 分隔。
4. **禁止事项**：
   - ❌ 绝对不要生成第 {actual_classes} 次课的"复习考核"内容！这部分由系统单独处理。

# Output Format
JSON 数组，结构如下：
[
  {{
    "week": 1,
    "order": 1,
    "title": "项目1：计算机基础（无需标签）",
    "tasks": "1. 计算机组成原理\n2. 操作系统安装",
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
        # 使用系统算出的周次
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
