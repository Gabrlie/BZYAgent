"""
Word 文档模板渲染服务
基于 docxtpl 实现 Word 文档的模板填充和生成
"""
import time
from typing import Any, Dict
from io import BytesIO
from pathlib import Path
from docxtpl import DocxTemplate

from .utils.paths import GENERATED_DIR, TEMPLATES_DIR, ensure_dir


TEMPLATE_DIR = TEMPLATES_DIR
OUTPUT_DIR = GENERATED_DIR


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
    
    # 生成输出文件名
    timestamp = int(time.time())
    output_filename = f"lesson_plan_{course_id}_{timestamp}.docx"
    output_dir = ensure_dir(OUTPUT_DIR)
    output_path = output_dir / output_filename
    
    # 保存文档
    doc.save(str(output_path))
    
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
    
    # 生成输出文件名
    timestamp = int(time.time())
    base_name = Path(template_name).stem
    output_filename = f"{base_name}_{course_id}_{timestamp}.docx"
    output_dir = ensure_dir(OUTPUT_DIR)
    output_path = output_dir / output_filename
    
    # 保存文档
    doc.save(str(output_path))
    
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
