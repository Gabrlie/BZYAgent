"""
Word 文档模板渲染服务
基于 docxtpl 实现 Word 文档的模板填充和生成
"""
import hashlib
from typing import Any, Dict
from io import BytesIO
from pathlib import Path
from docxtpl import DocxTemplate

from .utils.paths import GENERATED_DIR, TEMPLATES_DIR, ensure_dir


TEMPLATE_DIR = TEMPLATES_DIR
OUTPUT_DIR = GENERATED_DIR


def _save_docx_with_md5(doc: DocxTemplate, output_dir: Path) -> str:
    """Save a docx to output_dir with md5 filename and return filename."""
    file_stream = BytesIO()
    doc.save(file_stream)
    content = file_stream.getvalue()
    md5_name = hashlib.md5(content).hexdigest()
    filename = f"{md5_name}.docx"
    output_path = output_dir / filename
    if not output_path.exists():
        output_path.write_bytes(content)
    return filename


def render_lesson_plan_docx(data: Dict[str, Any], course_id: int) -> str:
    """
    渲染教案 Word 文档并保存到文件系统
    
    Args:
        data: 教案数据（JSON 字典）
        course_id: 课程 ID
        
    Returns:
        生成的 Word 文件相对路径
    """
    template_path = TEMPLATE_DIR / "教案模板.docx"
    
    if not template_path.exists():
        raise FileNotFoundError(f"模板文件未找到: {template_path}")
    
    # 加载模板
    doc = DocxTemplate(str(template_path))
    
    # 填充数据
    doc.render(data)
    
    output_dir = ensure_dir(OUTPUT_DIR)
    output_filename = _save_docx_with_md5(doc, output_dir)

    # 返回相对路径
    return f"generated/{output_filename}"


def render_docx_template(template_name: str, data: Dict[str, Any], course_id: int) -> str:
    """
    通用 Word 模板渲染函数
    
    Args:
        template_name: 模板文件名（如 "教案模板.docx"）
        data: 数据字典
        course_id: 课程 ID
        
    Returns:
        生成的 Word 文件相对路径
    """
    template_path = TEMPLATE_DIR / template_name
    
    if not template_path.exists():
        raise FileNotFoundError(f"模板文件未找到: {template_path}")
    
    # 加载模板
    doc = DocxTemplate(str(template_path))
    
    # 填充数据
    doc.render(data)
    
    output_dir = ensure_dir(OUTPUT_DIR)
    output_filename = _save_docx_with_md5(doc, output_dir)

    # 返回相对路径
    return f"generated/{output_filename}"


def render_docx_to_bytes(template_name: str, data: Dict[str, Any]) -> bytes:
    """
    渲染 Word 文档并返回字节流（用于直接下载）
    
    Args:
        template_name: 模板文件名
        data: 数据字典
        
    Returns:
        Word 文档字节流
    """
    template_path = TEMPLATE_DIR / template_name
    
    if not template_path.exists():
        raise FileNotFoundError(f"模板文件未找到: {template_path}")
    
    # 加载模板
    doc = DocxTemplate(str(template_path))
    
    # 填充数据
    doc.render(data)
    
    # 保存到内存
    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream.getvalue()


def get_template_variables(template_name: str) -> list:
    """
    获取模板中的所有变量
    
    Args:
        template_name: 模板文件名
        
    Returns:
        变量名列表
    """
    template_path = TEMPLATE_DIR / template_name
    
    if not template_path.exists():
        raise FileNotFoundError(f"模板文件未找到: {template_path}")
    
    doc = DocxTemplate(str(template_path))
    
    # 获取所有变量
    try:
        return doc.get_undeclared_template_variables()
    except:
        # 如果获取失败，返回空列表
        return []
