#!/usr/bin/env python3
"""
MCP服务器实现 - 为日历应用提供文件系统访问能力
基于Model Context Protocol (MCP) 实现AI助手与本地文件系统的交互
"""

import os
import json
import sqlite3
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

# 创建MCP服务器实例
mcp = FastMCP("CalendarApp Filesystem Server")

# 获取日历应用根目录
CALENDAR_ROOT = Path(__file__).parent.absolute()
DB_PATH = CALENDAR_ROOT / "calendar_data.db"


@mcp.tool()
async def list_directory(path: str = ".") -> List[Dict[str, Any]]:
    """
    列出指定目录的内容
    
    Args:
        path: 目录路径（相对于日历应用根目录）
    
    Returns:
        文件和目录信息的列表
    """
    try:
        target_path = CALENDAR_ROOT / path
        
        if not target_path.exists():
            return [{"error": f"路径不存在: {path}"}]
        
        if not target_path.is_dir():
            return [{"error": f"路径不是目录: {path}"}]
        
        contents = []
        for item in target_path.iterdir():
            item_info = {
                "name": item.name,
                "path": str(item.relative_to(CALENDAR_ROOT)),
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
                "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
            }
            contents.append(item_info)
        
        return contents
    
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def read_file(path: str) -> str:
    """
    读取文件内容
    
    Args:
        path: 文件路径（相对于日历应用根目录）
    
    Returns:
        文件内容
    """
    try:
        file_path = CALENDAR_ROOT / path
        
        if not file_path.exists():
            return f"文件不存在: {path}"
        
        if not file_path.is_file():
            return f"路径不是文件: {path}"
        
        # 检查文件大小，避免读取过大文件
        if file_path.stat().st_size > 1024 * 1024:  # 1MB限制
            return f"文件过大，无法读取: {path}"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
            return content
    
    except Exception as e:
        return f"读取文件错误: {str(e)}"


@mcp.tool()
async def write_file(path: str, content: str, create_dirs: bool = True) -> str:
    """
    写入文件内容
    
    Args:
        path: 文件路径（相对于日历应用根目录）
        content: 要写入的内容
        create_dirs: 是否自动创建目录
    
    Returns:
        操作结果
    """
    try:
        file_path = CALENDAR_ROOT / path
        
        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"文件写入成功: {path}"
    
    except Exception as e:
        return f"写入文件错误: {str(e)}"


@mcp.tool()
async def create_directory(path: str, parents: bool = True) -> str:
    """
    创建目录
    
    Args:
        path: 目录路径（相对于日历应用根目录）
        parents: 是否创建父目录
    
    Returns:
        操作结果
    """
    try:
        dir_path = CALENDAR_ROOT / path
        dir_path.mkdir(parents=parents, exist_ok=True)
        return f"目录创建成功: {path}"
    
    except Exception as e:
        return f"创建目录错误: {str(e)}"


@mcp.tool()
async def delete_file(path: str) -> str:
    """
    删除文件或目录
    
    Args:
        path: 文件或目录路径（相对于日历应用根目录）
    
    Returns:
        操作结果
    """
    try:
        target_path = CALENDAR_ROOT / path
        
        if not target_path.exists():
            return f"路径不存在: {path}"
        
        if target_path.is_dir():
            import shutil
            shutil.rmtree(target_path)
            return f"目录删除成功: {path}"
        else:
            target_path.unlink()
            return f"文件删除成功: {path}"
    
    except Exception as e:
        return f"删除错误: {str(e)}"


@mcp.tool()
async def get_file_info(path: str) -> Dict[str, Any]:
    """
    获取文件或目录的详细信息
    
    Args:
        path: 文件或目录路径
    
    Returns:
        文件信息字典
    """
    try:
        target_path = CALENDAR_ROOT / path
        
        if not target_path.exists():
            return {"error": f"路径不存在: {path}"}
        
        stat = target_path.stat()
        info = {
            "name": target_path.name,
            "path": str(target_path.relative_to(CALENDAR_ROOT)),
            "type": "directory" if target_path.is_dir() else "file",
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "absolute_path": str(target_path)
        }
        
        return info
    
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def search_files(pattern: str, directory: str = ".") -> List[Dict[str, Any]]:
    """
    搜索文件（支持通配符）
    
    Args:
        pattern: 搜索模式（如 *.py, *.txt）
        directory: 搜索目录（相对于日历应用根目录）
    
    Returns:
        匹配的文件列表
    """
    try:
        import glob
        
        search_path = CALENDAR_ROOT / directory
        pattern_path = search_path / pattern
        
        matches = glob.glob(str(pattern_path), recursive=True)
        
        results = []
        for match in matches:
            file_path = Path(match)
            if file_path.is_file():
                stat = file_path.stat()
                results.append({
                    "name": file_path.name,
                    "path": str(file_path.relative_to(CALENDAR_ROOT)),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return results
    
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def query_calendar_db(query: str) -> List[Dict[str, Any]]:
    """
    查询日历应用数据库
    
    Args:
        query: SQL查询语句
    
    Returns:
        查询结果
    """
    try:
        if not DB_PATH.exists():
            return [{"error": "数据库文件不存在"}]
        
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(query)
        
        # 处理SELECT查询
        if query.strip().upper().startswith('SELECT'):
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
        else:
            conn.commit()
            results = [{"message": f"影响了 {cursor.rowcount} 行"}]
        
        conn.close()
        return results
    
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def get_calendar_tags(date: str = None) -> List[Dict[str, Any]]:
    """
    获取日历标签信息
    
    Args:
        date: 指定日期（格式：YYYY-MM-DD），如果为None则获取所有标签
    
    Returns:
        标签信息列表
    """
    try:
        if not DB_PATH.exists():
            return [{"error": "数据库文件不存在"}]
        
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if date:
            cursor.execute("SELECT * FROM tags WHERE date = ?", (date,))
        else:
            cursor.execute("SELECT * FROM tags ORDER BY date")
        
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
        
        conn.close()
        return results
    
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def get_calendar_reminders(date: str = None) -> List[Dict[str, Any]]:
    """
    获取提醒信息
    
    Args:
        date: 指定日期（格式：YYYY-MM-DD），如果为None则获取所有提醒
    
    Returns:
        提醒信息列表
    """
    try:
        if not DB_PATH.exists():
            return [{"error": "数据库文件不存在"}]
        
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if date:
            cursor.execute("SELECT * FROM reminders WHERE date = ?", (date,))
        else:
            cursor.execute("SELECT * FROM reminders ORDER BY date, time")
        
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
        
        conn.close()
        return results
    
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def get_project_structure() -> Dict[str, Any]:
    """
    获取项目结构概览
    
    Returns:
        项目结构信息
    """
    try:
        structure = {
            "root_path": str(CALENDAR_ROOT),
            "directories": [],
            "python_files": [],
            "data_files": [],
            "config_files": []
        }
        
        for item in CALENDAR_ROOT.rglob("*"):
            if item.is_file():
                rel_path = str(item.relative_to(CALENDAR_ROOT))
                file_info = {
                    "path": rel_path,
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                }
                
                if item.suffix == '.py':
                    structure["python_files"].append(file_info)
                elif item.suffix in ['.db', '.json', '.txt', '.md']:
                    structure["data_files"].append(file_info)
                elif item.suffix in ['.ico', '.vbs', '.spec']:
                    structure["config_files"].append(file_info)
            elif item.is_dir() and item != CALENDAR_ROOT:
                rel_path = str(item.relative_to(CALENDAR_ROOT))
                structure["directories"].append(rel_path)
        
        return structure
    
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # 运行MCP服务器
    mcp.run(transport="stdio")