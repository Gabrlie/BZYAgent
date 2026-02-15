# API 接口规范

## 认证与用户
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/auth/login` | 登录并获取 JWT |
| `GET` | `/api/auth/me` | 获取当前用户信息 |
| `POST` | `/api/auth/change-password` | 修改密码 |
| `PUT` | `/api/auth/username` | 修改用户名 |
| `PUT` | `/api/auth/settings` | 更新 AI 配置 |
| `POST` | `/api/auth/models` | 获取可用模型列表 |

## AI 对话
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/chat/send` | 发送消息并流式返回 |
| `GET` | `/api/chat/history` | 获取聊天历史 |
| `DELETE` | `/api/chat/clear` | 清空历史 |

## 课程管理
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/courses` | 创建课程 |
| `GET` | `/api/courses` | 获取课程列表 |
| `GET` | `/api/courses/{course_id}` | 获取课程详情与文档 |
| `PUT` | `/api/courses/{course_id}` | 更新课程 |
| `DELETE` | `/api/courses/{course_id}` | 删除课程 |

## 仪表盘
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/dashboard/summary` | 获取仪表盘统计摘要 |

## 文档管理
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/courses/{course_id}/documents` | 创建文档记录 |
| `POST` | `/api/courses/{course_id}/documents/upload` | 上传文档文件 |
| `GET` | `/api/courses/{course_id}/documents` | 获取课程文档列表 |
| `GET` | `/api/courses/{course_id}/documents/type/{doc_type}` | 获取指定类型文档 |
| `GET` | `/api/documents/{document_id}` | 获取文档详情 |
| `GET` | `/api/documents/{document_id}/download` | 下载文档（带正确文件名） |
| `PUT` | `/api/documents/{document_id}` | 更新文档 |
| `DELETE` | `/api/documents/{document_id}` | 删除文档 |
| `GET` | `/api/documents/files/{course_id}/{filename}` | 下载文档文件 |

## 授课计划与教案生成
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/courses/{course_id}/generate-teaching-plan/stream` | 授课计划生成 SSE |
| `GET` | `/api/courses/{course_id}/teaching-plans` | 授课计划列表 |
| `GET` 或 `POST` | `/api/courses/{course_id}/generate-lesson-plan/stream` | 教案生成 SSE |
| `GET` | `/api/courses/{course_id}/lesson-plans` | 教案列表 |

## 软著材料
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/copyright/projects` | 创建软著项目 |
| `GET` | `/api/copyright/projects` | 软著项目列表 |
| `GET` | `/api/copyright/projects/{project_id}` | 软著项目详情 |
| `PUT` | `/api/copyright/projects/{project_id}` | 更新软著项目 |
| `POST` | `/api/copyright/projects/{project_id}/requirements` | 更新需求文档/说明 |
| `POST` | `/api/copyright/projects/{project_id}/generate` | 触发后台生成任务 |
| `GET` | `/api/copyright/projects/{project_id}/jobs/latest` | 获取最新任务（支持长轮询） |
| `GET` | `/api/copyright/projects/{project_id}/download` | 下载 ZIP |

## 关键请求参数
- 授课计划生成
- `teacher_name` 授课教师
- `total_weeks` 总周数
- `hour_per_class` 单次学时
- `classes_per_week` 每周次数
- `final_review` 最后一课是否复习考核
- `first_week_classes` 第一周上课次数
- `skip_slots` 不上课的周次与课次列表（JSON）

- 教案生成
- `sequence` 授课顺序

- 文档上传
- `doc_type` 文档类型
- `lesson_number` 教案上传必须指定课次
- 上传文件仅支持 `.doc` `.docx`

## 响应与错误处理
- 成功响应通常为 JSON 对象或数组。
- 失败响应遵循 FastAPI 的 `detail` 字段提示。
- SSE 响应为 `text/event-stream`，数据体为 JSON 字符串。
- 文档相关响应包含 `file_exists` 字段用于标记本地文件是否存在。
- 软著材料生成使用后台任务与长轮询，不使用 SSE。
