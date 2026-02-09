# 教案生成算法说明

## 触发条件
- 课程存在授课计划文档 `doc_type = plan`。
- 用户已配置 AI API Key 与 Base URL。

## 处理流程
1. 校验课程与用户配置。
2. 读取授课计划文档内容并合并为输入文本。
3. 读取课程上下文，包含课程信息、教材、目录与相关文档。
4. 调用 AI 生成结构化 JSON。
5. 使用 Word 模板渲染教案文档。
6. 保存文档记录与文件地址。
7. 通过 SSE 推送进度与结果。

## AI 输出结构与约束
- 仅允许输出单一 JSON 对象。
- 关键字段包括 `project_name` `week` `sequence` `hours` `total_hours` `knowledge_goals` `ability_goals` `quality_goals` `teaching_content` `teaching_focus` `teaching_difficulty` `review_content` `review_time` `new_lessons` `assessment_content` `summary_content` `homework_content`。
- 时间分配规则
- `total_hours = hours * 40`
- `assessment_time = 10` 分钟
- `summary_content` 固定 5 分钟
- `review_time` 在 5 到 15 分钟之间
- `new_lessons` 的总和必须与剩余时间一致

## 异常与降级
- AI 无输出或格式错误时返回错误提示。
- 若输入不足，模型应返回占位内容。

## 关键实现位置
- AI 生成逻辑：`backend/app/ai_service.py`
- SSE 进度与存储：`backend/app/routers/lesson_plan_api.py`
- Word 渲染：`backend/app/docx_service.py`
