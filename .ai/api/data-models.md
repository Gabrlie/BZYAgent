# 数据模型定义

## User
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键 |
| `username` | string | 用户名，唯一 |
| `hashed_password` | string | bcrypt 哈希后的密码 |
| `created_at` | datetime | 创建时间 |
| `ai_api_key` | string | AI API Key（可为空） |
| `ai_base_url` | string | AI Base URL（可为空） |
| `ai_model_name` | string | 模型名称，默认 `gpt-3.5-turbo` |

## Message
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键 |
| `user_id` | int | 关联用户 |
| `role` | string | `user` 或 `assistant` |
| `content` | text | 消息内容 |
| `created_at` | datetime | 创建时间 |

## Course
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键 |
| `user_id` | int | 归属用户 |
| `name` | string | 课程名称 |
| `semester` | string | 学期文本，默认自动计算 |
| `class_name` | string | 授课班级 |
| `total_hours` | int | 总学时 |
| `practice_hours` | int | 实训学时 |
| `course_type` | string | 课程类型 A/B/C |
| `textbook_isbn` | string | 教材 ISBN |
| `textbook_name` | string | 教材名称 |
| `textbook_image` | string | 教材图片 URL |
| `textbook_publisher` | string | 教材出版社（可选） |
| `textbook_link` | string | 教材链接（可选） |
| `course_catalog` | text | 课程目录（可选） |
| `parent_course_id` | int | 课程副本关系（预留） |
| `is_template` | bool | 是否模板（预留） |
| `share_key` | string | 分享密钥（预留） |
| `share_enabled` | bool | 是否启用分享（预留） |
| `share_expires_at` | datetime | 分享过期时间（预留） |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

## CourseDocument
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键 |
| `course_id` | int | 关联课程 |
| `doc_type` | string | `standard` `plan` `info` `lesson` `courseware` `lesson_plan` |
| `title` | string | 文档标题 |
| `content` | text | 文档内容或结构化 JSON |
| `file_url` | string | 文件下载 URL |
| `lesson_number` | int | 课次编号（可选） |
| `file_exists` | bool | 文件是否存在（响应字段） |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

## CopyrightProject
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键 |
| `user_id` | int | 归属用户 |
| `name` | string | 项目名称 |
| `domain` | string | 领域 |
| `system_name` | string | 软件名称 |
| `software_abbr` | string | 软件简称 |
| `description` | text | 系统简介 |
| `output_type` | string | 输出类型（当前仅 ZIP） |
| `generation_mode` | string | `fast` 或 `full` |
| `include_sourcecode` | bool | 是否包含源代码 |
| `include_ui_desc` | bool | 是否包含 UI 说明 |
| `include_tech_desc` | bool | 是否包含技术栈说明 |
| `requirements_text` | text | 需求文档内容 |
| `ui_description` | text | UI 说明 |
| `tech_description` | text | 技术栈说明 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

## CopyrightJob
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键 |
| `project_id` | int | 关联软著项目 |
| `status` | string | `queued` `running` `completed` `failed` |
| `stage` | string | 阶段标识（preparing/generating/rendering/saving/completed/error） |
| `message` | string | 进度说明 |
| `progress` | int | 进度百分比 |
| `error` | text | 错误信息 |
| `output_zip_path` | string | ZIP 文件路径 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

## 关系
- User 1..N Course
- User 1..N Message
- Course 1..N CourseDocument
- User 1..N CopyrightProject
- CopyrightProject 1..N CopyrightJob
