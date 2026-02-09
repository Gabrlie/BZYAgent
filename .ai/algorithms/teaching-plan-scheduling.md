# 授课计划排课与生成算法说明

## 输入参数
- `total_weeks` 总周数
- `classes_per_week` 每周上课次数
- `hour_per_class` 单次学时
- `total_hours` 课程总学时
- `practice_hours` 实训学时
- `final_review` 是否最后一次课为复习考核
- `skip_weeks` 排课调整说明

## 核心计算
- 最大课次 `max_classes = total_weeks * classes_per_week`
- 实际课次 `actual_classes = floor(total_hours / hour_per_class)`
- 理论课次 `theory_classes_count = round(theory_hours / hour_per_class)`
- 实训课次 `practice_classes_count = actual_classes - theory_classes_count`

## 生成流程
1. 调用排课智能体生成周次框架 `[{ order, week }]`。
2. 若生成失败，按顺序回退到默认排课公式。
3. 根据课程目录与周次框架调用 AI 生成每次课的标题与任务列表。
4. 若 `final_review = true`，追加最后一次课为“课程复习与考核”。

## 关键实现位置
- 排课与内容生成：`backend/app/teaching_plan_service.py`
- SSE 与模板渲染：`backend/app/routers/teaching_plan_api.py`
