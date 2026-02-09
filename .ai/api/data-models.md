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
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

## 关系
- User 1..N Course
- User 1..N Message
- Course 1..N CourseDocument
