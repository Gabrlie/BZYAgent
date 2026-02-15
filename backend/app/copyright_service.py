"""
软著材料生成服务
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import asyncio
import json as json_lib

import openai

from .database import SessionLocal
from .models import CopyrightJob, CopyrightProject, User
from .utils.paths import (
    COPYRIGHT_PROJECTS_DIR,
    COPYRIGHT_ZIPS_DIR,
    ensure_dir,
)

logger = logging.getLogger(__name__)

VENDOR_DIR = Path(__file__).resolve().parent / "vendor" / "ai_copyright"
VENDOR_PROMPTS_DIR = VENDOR_DIR / "system_prompts"

PROMPT_FILES = {
    "framework": "01-软著框架系统提示词.md",
    "page_list": "02-页面规划系统提示词.md",
    "ui_design": "03-界面设计系统提示词.md",
    "frontend": "04-网页代码生成系统提示词.md",
    "database": "05-数据库代码生成系统提示词.md",
    "backend": "06-后端代码生成系统提示词.md",
    "user_manual": "07-用户手册系统提示词.md",
    "application_form": "08-软件著作权登记信息表系统提示词.md",
}


def normalize_base_url(base_url: str) -> str:
    if not base_url:
        return base_url
    trimmed = base_url.strip().rstrip("/")
    if trimmed.endswith("/v1"):
        return trimmed
    return f"{trimmed}/v1"


def _collect_error_text(error: Exception) -> str:
    parts: List[str] = [str(error), repr(error)]
    body = getattr(error, "body", None)
    if body is not None:
        if isinstance(body, (dict, list)):
            parts.append(json.dumps(body, ensure_ascii=False))
        else:
            parts.append(str(body))
    return " ".join(part for part in parts if part).strip()


def is_rate_limit_error(error: Exception) -> bool:
    if hasattr(openai, "RateLimitError") and isinstance(error, openai.RateLimitError):
        return True
    status_code = getattr(error, "status_code", None)
    if status_code == 429:
        return True
    response = getattr(error, "response", None)
    if response is not None and getattr(response, "status_code", None) == 429:
        return True
    message = _collect_error_text(error).lower()
    if "rate limit" in message or "too many requests" in message or "429" in message:
        return True
    return False


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def render_prompt(template: str, variables: Dict[str, str]) -> str:
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


def truncate_text(text: str, max_chars: int = 12000) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n\n[内容过长，已截断]"


def sync_directory(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            sync_directory(item, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def reset_generated_dirs(project_dir: Path) -> None:
    for folder in ["process_docs", "output_docs", "output_sourcecode"]:
        target = project_dir / folder
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
    for sub in ["front", "backend", "db"]:
        (project_dir / "output_sourcecode" / sub).mkdir(parents=True, exist_ok=True)


def prepare_project_workspace(project_id: int) -> Path:
    project_dir = ensure_dir(COPYRIGHT_PROJECTS_DIR / str(project_id))
    (project_dir / "requires_docs").mkdir(parents=True, exist_ok=True)
    (project_dir / "specs_docs").mkdir(parents=True, exist_ok=True)
    (project_dir / "system_prompts").mkdir(parents=True, exist_ok=True)
    (project_dir / "scripts").mkdir(parents=True, exist_ok=True)

    sync_directory(VENDOR_DIR / "specs_docs", project_dir / "specs_docs")
    sync_directory(VENDOR_DIR / "system_prompts", project_dir / "system_prompts")
    sync_directory(VENDOR_DIR / "requires_docs", project_dir / "requires_docs")
    sync_directory(VENDOR_DIR / "scripts", project_dir / "scripts")

    for filename in ["工作流程.md", "执行计划.md"]:
        src = VENDOR_DIR / filename
        if src.exists():
            shutil.copy2(src, project_dir / filename)

    reset_generated_dirs(project_dir)
    return project_dir


def write_project_documents(
    project_dir: Path,
    system_name: str,
    domain: Optional[str],
    description: Optional[str],
    requirements_text: str,
    ui_description: Optional[str],
    tech_description: Optional[str],
    include_ui_desc: bool,
    include_tech_desc: bool,
) -> Tuple[Path, Path, Path]:
    requirements_path = project_dir / "requires_docs" / "需求文档.md"
    header_lines = [f"# {system_name} 需求文档"]
    if domain:
        header_lines.append(f"\n**所属领域**：{domain}")
    if description:
        header_lines.append(f"\n**系统简介**：{description}")
    header_lines.append("\n## 需求描述\n")
    requirements_body = "\n".join(header_lines) + requirements_text.strip() + "\n"
    requirements_path.write_text(requirements_body, encoding="utf-8")

    ui_path = project_dir / "requires_docs" / "UI设计规范.md"
    if include_ui_desc:
        content = ui_description.strip() if ui_description else "请补充 UI 设计规范描述。\n"
        ui_path.write_text(content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8")

    tech_path = project_dir / "requires_docs" / "技术栈说明文档.md"
    if include_tech_desc:
        content = tech_description.strip() if tech_description else "请补充技术栈说明。\n"
        tech_path.write_text(content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8")

    return requirements_path, ui_path, tech_path


def build_project_config(
    project_dir: Path,
    system_name: str,
    software_abbr: str,
    generation_mode: str,
    include_ui_desc: bool,
    include_tech_desc: bool,
) -> Dict[str, str]:
    config_path = VENDOR_DIR / "ai-copyright-config.json"
    base_config = json.loads(_read_text(config_path))

    tech_stack_path = (
        "requires_docs/技术栈说明文档.md"
        if include_tech_desc
        else "specs_docs/tech_stack_specs/技术栈说明文档_默认.md"
    )
    ui_design_spec = (
        "requires_docs/UI设计规范.md"
        if include_ui_desc
        else "specs_docs/ui_design_specs/01-UI设计规范_默认_Corporate.md"
    )

    base_config.update(
        {
            "front": "React",
            "backend": "Python FastAPI",
            "title": system_name,
            "short_title": software_abbr or system_name,
            "requirements_description": "requires_docs/需求文档.md",
            "dev_tech_stack": tech_stack_path,
            "ui_design_spec": ui_design_spec,
            "ui_design_style": "corporate",
            "generation_mode": generation_mode,
            "framework_design": f"process_docs/{system_name}_框架设计文档.md",
            "page_list": "process_docs/页面规划.md",
            "ui_design": "process_docs/界面设计方案.md",
            "database_schema": "output_sourcecode/db/database_schema.sql",
            "copyright_application": "output_docs/软件著作权登记信息表.md",
        }
    )

    target_path = project_dir / "ai-copyright-config.json"
    target_path.write_text(json.dumps(base_config, ensure_ascii=False, indent=2), encoding="utf-8")
    return base_config


async def run_prompt(
    client: openai.AsyncOpenAI,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.7,
) -> str:
    last_error: Optional[Exception] = None
    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            if not response.choices:
                return ""
            content = response.choices[0].message.content or ""
            return content.strip()
        except Exception as exc:
            last_error = exc
            if is_rate_limit_error(exc):
                raise RuntimeError(
                    "已触发接口限流（Rate Limit）。请稍后再试或更换接口提供商。"
                    "建议避免同时发起多个生成任务。"
                )
            message = str(exc)
            if isinstance(exc, json_lib.JSONDecodeError) or "Expecting value" in message:
                logger.warning("AI 响应解析失败，尝试重试。")
            if attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            break
    if last_error:
        message = str(last_error)
        if isinstance(last_error, json_lib.JSONDecodeError) or "Expecting value" in message:
            raise RuntimeError(
                "AI 服务响应异常（返回空内容或非 JSON）。请检查 Base URL、模型名与网络连通性，并确认服务支持 OpenAI 兼容接口。"
            )
    raise RuntimeError(f"AI 调用失败：{last_error}")


def parse_file_blocks(content: str) -> Dict[str, str]:
    files: Dict[str, str] = {}
    current_path: Optional[str] = None
    buffer: List[str] = []
    pattern = re.compile(r"^###\s*(?:FILE|文件)\s*[:：]\s*(.+)$", re.IGNORECASE)

    for line in content.splitlines():
        match = pattern.match(line.strip())
        if match:
            if current_path:
                files[current_path] = "\n".join(buffer).strip("\n")
            current_path = match.group(1).strip()
            buffer = []
        else:
            buffer.append(line)
    if current_path:
        files[current_path] = "\n".join(buffer).strip("\n")
    return files


def safe_write_files(root_dir: Path, file_map: Dict[str, str]) -> List[Path]:
    written: List[Path] = []
    for raw_path, content in file_map.items():
        relative_path = Path(raw_path.strip().lstrip("/"))
        if relative_path.is_absolute() or ".." in relative_path.parts:
            continue
        target_path = root_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content.strip() + "\n", encoding="utf-8")
        written.append(target_path)
    return written


async def extract_framework_insights(
    client: openai.AsyncOpenAI,
    framework_doc: str,
    model: str,
) -> Tuple[str, str]:
    prompt = f"""请从以下框架设计文档中提取：
1) 功能模块清单（列表）
2) 核心创新点（列表）

要求仅输出 JSON，对象字段为 module_list 和 innovation_points，均为字符串数组。

框架设计文档：
{truncate_text(framework_doc, 10000)}
"""
    content = await run_prompt(client, "你擅长结构化抽取软件文档信息。", prompt, model, temperature=0.2)
    try:
        data = json.loads(content)
        module_list = data.get("module_list") or []
        innovation_points = data.get("innovation_points") or []
        module_text = "\n".join(f"- {item}" for item in module_list) if module_list else ""
        innovation_text = "\n".join(f"- {item}" for item in innovation_points) if innovation_points else ""
        return module_text, innovation_text
    except Exception:
        logger.warning("解析框架文档抽取结果失败，使用全文作为占位。")
        return "", ""


async def extract_page_items(
    client: openai.AsyncOpenAI,
    page_plan_doc: str,
    model: str,
) -> List[Dict[str, str]]:
    prompt = f"""请从以下页面规划文档中提取页面清单，输出 JSON 数组。
每个元素包含：name（页面名称）、path（页面路径）、file（建议文件名，如 dashboard.html）、description（页面功能描述，50字以内）。

页面规划文档：
{truncate_text(page_plan_doc, 10000)}
"""
    content = await run_prompt(client, "你擅长从文档中提取页面结构。", prompt, model, temperature=0.2)
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return [
                {
                    "name": str(item.get("name", "页面")),
                    "path": str(item.get("path", "/")),
                    "file": str(item.get("file", "index.html")),
                    "description": str(item.get("description", "")),
                }
                for item in data
                if isinstance(item, dict)
            ]
    except Exception:
        logger.warning("解析页面清单失败，使用默认页面。")
    return [
        {"name": "仪表盘", "path": "/dashboard", "file": "dashboard.html", "description": "系统总览与关键指标展示。"},
        {"name": "项目管理", "path": "/projects", "file": "projects.html", "description": "软著项目的创建、编辑与查看。"},
        {"name": "生成中心", "path": "/generate", "file": "generate.html", "description": "一键生成软著材料与进度管理。"},
        {"name": "系统设置", "path": "/settings", "file": "settings.html", "description": "系统配置与用户权限管理。"},
        {"name": "帮助中心", "path": "/help", "file": "help.html", "description": "使用说明与常见问题。"},
    ]


def create_fallback_frontend_files(
    project_dir: Path,
    system_name: str,
    pages: List[Dict[str, str]],
) -> None:
    base_css = """
body { font-family: "Noto Sans SC", sans-serif; margin: 0; background: #f5f7fb; color: #1f2a44; }
.layout { display: flex; min-height: 100vh; }
.sidebar { width: 240px; background: #1f2937; color: #fff; padding: 24px; }
.content { flex: 1; padding: 32px; }
.card { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08); }
"""
    for page in pages:
        filename = page.get("file") or "index.html"
        title = page.get("name") or "页面"
        description = page.get("description") or "页面功能描述待补充。"
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} - {system_name}</title>
  <link href="https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
  <link href="https://lf6-cdn-tos.bytecdntp.com/cdn/expire-100-M/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
  <style>{base_css}</style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <h1 class="text-2xl font-bold mb-6">{system_name}</h1>
      <nav class="space-y-2">
        <div class="text-sm opacity-80">导航菜单</div>
        <div class="text-lg">{title}</div>
      </nav>
    </aside>
    <main class="content">
      <div class="card">
        <h2 class="text-2xl font-semibold mb-4">{title}</h2>
        <p class="text-gray-600 mb-4">{description}</p>
        <div class="grid grid-cols-2 gap-4">
          <div class="p-4 bg-blue-50 rounded-lg">AI功能入口</div>
          <div class="p-4 bg-green-50 rounded-lg">业务数据概览</div>
        </div>
      </div>
    </main>
  </div>
</body>
</html>
"""
        target_path = project_dir / "output_sourcecode" / "front" / filename
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(html, encoding="utf-8")


def create_fallback_backend_files(project_dir: Path, system_name: str) -> None:
    target_path = project_dir / "output_sourcecode" / "backend" / "app.py"
    content = f"""\"\"\"
{system_name} 后端示例代码
\"\"\"
from fastapi import FastAPI

app = FastAPI(title=\"{system_name}\")


@app.get(\"/health\")
def health_check():
    return {{\"status\": \"ok\"}}


@app.get(\"/modules\")
def list_modules():
    return {{\"modules\": [\"用户管理\", \"AI生成\", \"文档管理\"]}}
"""
    target_path.write_text(content, encoding="utf-8")


def create_fallback_database_files(project_dir: Path, system_name: str) -> None:
    target_path = project_dir / "output_sourcecode" / "db" / "database_schema.sql"
    content = f"""/*
* 数据库表结构定义脚本
* 项目：{system_name}
* 创建日期：{datetime.now().strftime('%Y-%m-%d')}
*/

CREATE TABLE sys_users (
  id BIGSERIAL PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_generation_jobs (
  id BIGSERIAL PRIMARY KEY,
  job_type VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL,
  payload TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
    target_path.write_text(content, encoding="utf-8")


def zip_project(project_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(project_dir))


def update_job_state(
    db,
    job: CopyrightJob,
    *,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    message: Optional[str] = None,
    progress: Optional[int] = None,
    error: Optional[str] = None,
    output_zip_path: Optional[str] = None,
) -> None:
    if status is not None:
        job.status = status
    if stage is not None:
        job.stage = stage
    if message is not None:
        job.message = message
    if progress is not None:
        job.progress = progress
    if error is not None:
        job.error = error
    if output_zip_path is not None:
        job.output_zip_path = output_zip_path
    db.commit()
    db.refresh(job)


async def run_copyright_generation(job_id: int, project_id: int, user_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.query(CopyrightJob).filter(CopyrightJob.id == job_id).first()
        project = db.query(CopyrightProject).filter(
            CopyrightProject.id == project_id, CopyrightProject.user_id == user_id
        ).first()
        user = db.query(User).filter(User.id == user_id).first()

        if not job or not project or not user:
            return

        if not user.ai_api_key or not user.ai_base_url:
            update_job_state(
                db,
                job,
                status="failed",
                stage="error",
                message="请先配置 AI",
                error="未配置 AI",
                progress=0,
            )
            return

        if not project.requirements_text or not project.requirements_text.strip():
            update_job_state(
                db,
                job,
                status="failed",
                stage="error",
                message="需求文档不能为空",
                error="需求文档不能为空",
                progress=0,
            )
            return

        update_job_state(
            db,
            job,
            status="running",
            stage="preparing",
            message="准备项目环境...",
            progress=5,
        )

        project_dir = prepare_project_workspace(project.id)
        requirements_path, ui_path, tech_path = write_project_documents(
            project_dir=project_dir,
            system_name=project.system_name or project.name,
            domain=project.domain,
            description=project.description,
            requirements_text=project.requirements_text,
            ui_description=project.ui_description,
            tech_description=project.tech_description,
            include_ui_desc=project.include_ui_desc,
            include_tech_desc=project.include_tech_desc,
        )

        generation_mode = (
            project.generation_mode.lower()
            if project.generation_mode and project.generation_mode.lower() in {"fast", "full"}
            else "fast"
        )
        config = build_project_config(
            project_dir=project_dir,
            system_name=project.system_name or project.name,
            software_abbr=project.software_abbr or project.name,
            generation_mode=generation_mode,
            include_ui_desc=project.include_ui_desc,
            include_tech_desc=project.include_tech_desc,
        )

        variables = {
            "front": config.get("front"),
            "backend": config.get("backend"),
            "title": config.get("title"),
            "short_title": config.get("short_title"),
            "requirements_description": config.get("requirements_description"),
            "dev_tech_stack": config.get("dev_tech_stack"),
            "ui_design_spec": config.get("ui_design_spec"),
            "ui_design_style": config.get("ui_design_style"),
            "generation_mode": config.get("generation_mode"),
            "page_count_fast": config.get("page_count_fast"),
            "page_count_full": config.get("page_count_full"),
            "api_count_min": config.get("api_count_min"),
            "api_count_max": config.get("api_count_max"),
            "framework_design": config.get("framework_design"),
            "page_list": config.get("page_list"),
            "ui_design": config.get("ui_design"),
            "database_schema": config.get("database_schema"),
            "copyright_application": config.get("copyright_application"),
            "module_list": "",
            "innovation_points": "",
        }

        base_url = normalize_base_url(user.ai_base_url)
        client = openai.AsyncOpenAI(api_key=user.ai_api_key, base_url=base_url)
        model = user.ai_model_name or "gpt-4"

        update_job_state(
            db,
            job,
            stage="generating",
            message="生成框架设计文档...",
            progress=15,
        )
        framework_prompt = render_prompt(
            (VENDOR_PROMPTS_DIR / PROMPT_FILES["framework"]).read_text(encoding="utf-8"),
            variables,
        )
        framework_user = f"""需求文档内容：
{truncate_text(project.requirements_text, 12000)}

技术栈说明：
{truncate_text(tech_path.read_text(encoding="utf-8") if tech_path.exists() else "", 4000)}
"""
        framework_doc = await run_prompt(client, framework_prompt, framework_user, model)
        framework_path = project_dir / config.get("framework_design")
        framework_path.write_text(framework_doc + "\n", encoding="utf-8")

        module_list, innovation_points = await extract_framework_insights(
            client, framework_doc, model
        )
        variables["module_list"] = module_list
        variables["innovation_points"] = innovation_points

        update_job_state(
            db,
            job,
            stage="generating",
            message="生成页面规划文档...",
            progress=30,
        )
        page_prompt = render_prompt(
            (VENDOR_PROMPTS_DIR / PROMPT_FILES["page_list"]).read_text(encoding="utf-8"),
            variables,
        )
        page_user = f"""框架设计文档：
{truncate_text(framework_doc, 12000)}
"""
        page_doc = await run_prompt(client, page_prompt, page_user, model)
        page_path = project_dir / config.get("page_list")
        page_path.write_text(page_doc + "\n", encoding="utf-8")

        pages = await extract_page_items(client, page_doc, model)

        update_job_state(
            db,
            job,
            stage="generating",
            message="生成界面设计方案...",
            progress=45,
        )
        ui_prompt = render_prompt(
            (VENDOR_PROMPTS_DIR / PROMPT_FILES["ui_design"]).read_text(encoding="utf-8"),
            variables,
        )
        ui_spec_content = ""
        if ui_path.exists() and project.include_ui_desc:
            ui_spec_content = ui_path.read_text(encoding="utf-8")
        ui_user = f"""页面规划文档：
{truncate_text(page_doc, 12000)}

框架设计文档：
{truncate_text(framework_doc, 6000)}

UI设计规范：
{truncate_text(ui_spec_content, 4000)}
"""
        ui_doc = await run_prompt(client, ui_prompt, ui_user, model)
        ui_path_out = project_dir / config.get("ui_design")
        ui_path_out.write_text(ui_doc + "\n", encoding="utf-8")

        update_job_state(
            db,
            job,
            stage="generating",
            message="生成前端源码...",
            progress=55,
        )
        frontend_prompt = render_prompt(
            (VENDOR_PROMPTS_DIR / PROMPT_FILES["frontend"]).read_text(encoding="utf-8"),
            variables,
        )
        page_list_hint = json.dumps(pages, ensure_ascii=False, indent=2)
        frontend_user = f"""请根据以下页面清单和设计方案生成前端代码。
页面清单(JSON)：
{page_list_hint}

界面设计方案：
{truncate_text(ui_doc, 8000)}

输出格式要求：
使用多文件格式输出，每个文件以行首 `### FILE: output_sourcecode/front/文件名` 标记。
示例：
### FILE: output_sourcecode/front/dashboard.html
<html>...</html>
"""
        frontend_output = await run_prompt(client, frontend_prompt, frontend_user, model)
        frontend_files = parse_file_blocks(frontend_output)
        if frontend_files:
            written = safe_write_files(project_dir, frontend_files)
            html_written = [path for path in written if path.suffix.lower() == ".html"]
            if not html_written:
                create_fallback_frontend_files(project_dir, config.get("title"), pages)
        else:
            create_fallback_frontend_files(project_dir, config.get("title"), pages)

        update_job_state(
            db,
            job,
            stage="generating",
            message="生成数据库脚本...",
            progress=65,
        )
        db_prompt = render_prompt(
            (VENDOR_PROMPTS_DIR / PROMPT_FILES["database"]).read_text(encoding="utf-8"),
            variables,
        )
        db_user = f"""框架设计文档：
{truncate_text(framework_doc, 8000)}

页面规划：
{truncate_text(page_doc, 8000)}

界面设计：
{truncate_text(ui_doc, 4000)}

输出格式要求：
使用多文件格式输出，每个文件以行首 `### FILE: output_sourcecode/db/文件名` 标记。
"""
        db_output = await run_prompt(client, db_prompt, db_user, model)
        db_files = parse_file_blocks(db_output)
        if db_files:
            safe_write_files(project_dir, db_files)
        else:
            create_fallback_database_files(project_dir, config.get("title"))

        update_job_state(
            db,
            job,
            stage="generating",
            message="生成后端源码...",
            progress=75,
        )
        backend_prompt = render_prompt(
            (VENDOR_PROMPTS_DIR / PROMPT_FILES["backend"]).read_text(encoding="utf-8"),
            variables,
        )
        backend_user = f"""框架设计文档：
{truncate_text(framework_doc, 8000)}

页面规划：
{truncate_text(page_doc, 8000)}

数据库设计：
{truncate_text((project_dir / config.get('database_schema')).read_text(encoding='utf-8') if (project_dir / config.get('database_schema')).exists() else '', 6000)}

输出格式要求：
使用多文件格式输出，每个文件以行首 `### FILE: output_sourcecode/backend/文件名` 标记。
"""
        backend_output = await run_prompt(client, backend_prompt, backend_user, model)
        backend_files = parse_file_blocks(backend_output)
        if backend_files:
            safe_write_files(project_dir, backend_files)
        else:
            create_fallback_backend_files(project_dir, config.get("title"))

        update_job_state(
            db,
            job,
            stage="generating",
            message="生成用户手册...",
            progress=82,
        )
        manual_prompt = render_prompt(
            (VENDOR_PROMPTS_DIR / PROMPT_FILES["user_manual"]).read_text(encoding="utf-8"),
            variables,
        )
        manual_user = f"""需求文档：
{truncate_text(project.requirements_text, 8000)}

框架设计：
{truncate_text(framework_doc, 6000)}

页面规划：
{truncate_text(page_doc, 6000)}

界面设计：
{truncate_text(ui_doc, 6000)}
"""
        manual_doc = await run_prompt(client, manual_prompt, manual_user, model)
        manual_path = project_dir / "output_docs" / "用户手册.txt"
        manual_path.write_text(manual_doc + "\n", encoding="utf-8")

        update_job_state(
            db,
            job,
            stage="generating",
            message="生成登记信息表...",
            progress=88,
        )
        form_prompt = render_prompt(
            (VENDOR_PROMPTS_DIR / PROMPT_FILES["application_form"]).read_text(encoding="utf-8"),
            variables,
        )
        form_user = f"""需求文档：
{truncate_text(project.requirements_text, 6000)}

框架设计：
{truncate_text(framework_doc, 6000)}
"""
        form_doc = await run_prompt(client, form_prompt, form_user, model)
        form_path = project_dir / "output_docs" / "软件著作权登记信息表.md"
        form_path.write_text(form_doc + "\n", encoding="utf-8")

        update_job_state(
            db,
            job,
            stage="rendering",
            message="整理源代码文档...",
            progress=92,
        )
        merge_script = project_dir / "scripts" / "generators" / "merge_all_simple.py"
        result = subprocess.run(
            [sys.executable, str(merge_script)],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "源代码合并失败")

        update_job_state(
            db,
            job,
            stage="saving",
            message="打包 ZIP 文件...",
            progress=96,
        )
        zip_name = f"{project.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
        zip_path = COPYRIGHT_ZIPS_DIR / str(project.id) / zip_name
        zip_project(project_dir, zip_path)

        update_job_state(
            db,
            job,
            status="completed",
            stage="completed",
            message="软著材料生成完成",
            progress=100,
            output_zip_path=str(zip_path),
        )
    except Exception as exc:
        if db:
            job = db.query(CopyrightJob).filter(CopyrightJob.id == job_id).first()
            if job:
                error_message = str(exc)
                if is_rate_limit_error(exc):
                    error_message = (
                        "已触发接口限流（Rate Limit）。请稍后再试或更换接口提供商。"
                        "建议避免同时发起多个生成任务。"
                    )
                update_job_state(
                    db,
                    job,
                    status="failed",
                    stage="error",
                    message=f"生成失败：{error_message}",
                    error=error_message,
                    progress=0,
                )
    finally:
        db.close()
