# EduAgent Prime 项目 AI 入口文档

本文档是项目 AI 助手的入口索引，覆盖需求、模块、架构、数据流、算法、安全与扩展规划。深入细节请见 .ai 目录内的专题文档。

## 项目整体需求概述
EduAgent Prime 是面向高职院校教学场景的课程资产管理与教学文档生成平台。核心目标是帮助教师管理课程基本信息、教材与课程目录，并通过 AI 生成授课计划与教案，最终输出标准化 Word 文档，同时提供对话式 AI 助手与历史记录管理。

## 功能模块划分
- 用户认证与账号管理
- 用户 AI 配置管理
- 课程管理
- 文档管理与文件上传下载
- 授课计划生成
- 教案生成
- AI 对话与历史记录
- 静态文件服务与模板渲染
- 系统配置与运维

## 技术栈说明
- 后端：FastAPI，SQLAlchemy，Alembic，Python 3.12，uv
- 前端：Umi Max，React 19，TypeScript，Ant Design
- 数据库：PostgreSQL 16（Docker Compose）
- AI：OpenAI 兼容 API（可配置 Base URL 与模型），支持流式输出
- 文档生成：docxtpl + Word 模板
- 文件存储：本地文件系统 `data/uploads`

## 核心业务逻辑描述
1. 用户登录后获得 JWT，前端保存到 `localStorage` 并在请求头注入。
2. 用户创建课程并维护课程目录与教材信息，课程为后续生成提供上下文。
3. 授课计划生成：根据课程目录与学时配置调用 AI 生成课表与任务列表，渲染 Word 模板并保存为文档。
4. 教案生成：仅支持系统生成的授课计划作为输入；上传授课计划不可用于 AI 生成与编辑。
5. AI 对话：用户消息入库，调用 AI 流式生成回复并持久化。

## 文档命名与文件规则
- 授课计划命名：`《课程名称》授课计划`。
- 教案命名：`(授课顺序+1)广东碧桂园职业学院教案（主页）-第(对应周数)周教案`。
- 生成与上传文件本地以内容 MD5 命名，数据库保存展示名称。
- 文档列表包含 `file_exists` 字段，用于标记文件不存在状态并限制下载。
- 同一课次教案或授课计划重复生成/上传时覆盖旧记录与旧文件。
- 上传文档仅用于下载与查看，不支持 AI 生成与编辑功能。

## 系统架构设计
系统为前后端分离架构。前端通过代理与后端 API 通信，后端统一 JWT 鉴权，数据库存储用户与课程数据，文件系统存储生成文档与上传文件。AI 相关能力通过 OpenAI 兼容接口访问。

## 数据流分析
- 登录与鉴权：`/api/auth/login` -> JWT -> 请求拦截器 -> 后端中间件验证。
- 课程与文档：课程 CRUD -> 文档 CRUD -> 文件系统与数据库双写。
- 授课计划：前端发起 SSE -> 后端生成计划 JSON -> 模板渲染 -> 文档入库 -> SSE 完成回传。
- 教案：前端发起 SSE -> 后端获取课程上下文与计划文档 -> AI 输出 JSON -> 模板渲染 -> 文档入库 -> SSE 完成回传。
- AI 对话：前端发起流式请求 -> AI 流式响应 -> 结果入库。

## 关键算法说明
- 学期自动计算：按当前月份计算学年与学期。
- 排课与授课计划：系统生成周次框架（第一周上课次数与不上课列表），AI 仅生成课次内容，必要时追加复习课；允许最后一周未排满（差额不超过 6）。
- 教案结构化生成：AI 按固定 JSON 结构输出，并按时长规则分配时间。
- 模板渲染：docxtpl 将 JSON 数据映射到 Word 模板。
- SSE 进度推送：后台按阶段推送生成进度。

## 性能要求
- 文件上传大小限制为 10MB，支持 `.doc` `.docx`。
- 生成类接口使用 SSE 保持连接，前端需处理流式进度。
- 建议在生产环境为数据库与文件目录配置持久化存储和备份策略。

## 安全需求
- JWT 认证为所有 API 的强制前置条件，未认证请求返回 401。
- 密码使用 bcrypt 哈希存储。
- Base URL 校验与模型配置防止错误调用。
- 文件上传限制类型与大小，防止高风险文件进入系统。

## 未来扩展规划
- 角色与权限管理（教师、教研、管理员）。
- 文档版本管理与审批流。
- 课程模板与共享能力落地（模型字段已预留）。
- 课程知识库向向量检索与多文档解析扩展。
- 多 AI 提供商与模型路由策略。

## 详细文档索引
- 需求与用例：`D:\Develop\Projects\BZYAgent\.ai\requirements\requirements.md`
- 架构设计：`D:\Develop\Projects\BZYAgent\.ai\architecture\system-architecture.md`
- 数据流分析：`D:\Develop\Projects\BZYAgent\.ai\architecture\data-flow.md`
- 技术选型：`D:\Develop\Projects\BZYAgent\.ai\architecture\tech-stack.md`
- API 规范：`D:\Develop\Projects\BZYAgent\.ai\api\api-spec.md`
- 数据模型：`D:\Develop\Projects\BZYAgent\.ai\api\data-models.md`
- 核心算法：`D:\Develop\Projects\BZYAgent\.ai\algorithms\lesson-plan-generation.md`
- 排课算法：`D:\Develop\Projects\BZYAgent\.ai\algorithms\teaching-plan-scheduling.md`
- 安全策略：`D:\Develop\Projects\BZYAgent\.ai\security\security.md`
- 性能要求：`D:\Develop\Projects\BZYAgent\.ai\requirements\performance.md`
- 测试策略：`D:\Develop\Projects\BZYAgent\.ai\testing\testing.md`
- 部署运维：`D:\Develop\Projects\BZYAgent\.ai\deployment\deployment.md`

## 已同步的最新改动（软著材料模块）
- 新增软著材料模块（独立项目）并深度集成前后端。
- 输出仅 ZIP：生成完成后通过下载接口获取，不展示输出目录路径。
- 生成流程为后台任务 + 前端长轮询进度（可关闭页面，后台继续生成）。
- 生成进度弹窗、超时提示、使用说明弹窗、生成模式区别说明已添加。
- 列表状态显示中文，并可点击状态打开进度弹窗。
- 有生成任务后隐藏“一键生成”，仅保留“重新生成”。
- 前端检测限流（Rate Limit）错误后弹窗提示用户更换接口/稍后再试，并提醒避免同时生成多个任务。
- 单容器部署：根目录 `Dockerfile` 负责构建前端并由后端提供静态资源；删除 `backend/Dockerfile`、`frontend/Dockerfile`。
