# 系统架构设计

## 架构概览
系统采用前后端分离开发模式，生产部署为单容器运行。后端负责 API 与前端静态资源托管，处理业务逻辑、数据库读写、文件存储与 AI 调用，并通过 Word 模板渲染生成文档。

```mermaid
flowchart LR
  FE["Frontend (Umi Max / React)"] -->|"HTTPS / API"| BE["Backend (FastAPI + Static)"]
  FE -->|"SSE Progress"| BE
  FE -->|"Long Polling"| BE
  BE -->|"ORM"| DB["PostgreSQL"]
  BE -->|"File IO"| FS["Data / Templates"]
  BE -->|"OpenAI Compatible API"| AI["AI Provider"]
```

## 组件职责
前端职责：课程管理、文档管理、生成流程交互界面与进度展示。
后端职责：统一鉴权、业务逻辑处理、AI 调用、文档渲染、软著材料生成与文件管理。
数据库职责：存储用户、课程、文档、聊天历史与软著任务。
文件系统职责：保存上传文件、生成文档与软著材料 ZIP。

## 部署拓扑
```mermaid
flowchart TB
  Client["Browser"] --> API["FastAPI Service (Static + API)"]
  API --> DB["PostgreSQL (Docker)"]
  API --> FS["Local Filesystem (data/)"]
  API --> AI["OpenAI Compatible API"]
```

## 运行时交互
- 认证与鉴权由后端中间件统一处理，支持 Header 与 Query Token。
- 文档生成使用 SSE，前端以 EventSource 订阅进度事件。
- 生成文档存储于 `data/uploads` 并通过静态路由访问。
- 软著材料生成使用后台任务，前端通过长轮询查询进度并下载 ZIP。
