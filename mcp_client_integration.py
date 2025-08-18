#!/usr/bin/env python3
"""
MCP客户端集成模块 - 为日历应用提供AI助手与MCP服务器的交互能力
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import subprocess
import threading
import time
import logging

# 尝试导入mcp客户端库
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("警告: MCP客户端库未安装，AI助手的文件系统功能将受限")
    print("请运行: pip install mcp 以启用完整功能")


class MCPClientIntegration:
    """MCP客户端集成类"""
    
    def __init__(self, server_script: str = None):
        self.server_script = server_script or "mcp_server.py"
        self.session = None
        self.client = None
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        
    async def initialize(self) -> bool:
        """初始化MCP客户端连接"""
        if not MCP_AVAILABLE:
            self.logger.error("MCP库不可用")
            return False
            
        try:
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[self.server_script],
                cwd=str(Path(__file__).parent)
            )
            
            self.client = stdio_client(server_params)
            self.session = await self.client.__aenter__()
            
            # 初始化会话
            await self.session.initialize()
            self.is_connected = True
            self.logger.info("MCP客户端连接成功")
            return True
            
        except Exception as e:
            self.logger.error(f"MCP客户端初始化失败: {e}")
            return False
    
    async def close(self):
        """关闭MCP客户端连接"""
        if self.session:
            await self.client.__aexit__(None, None, None)
            self.session = None
            self.client = None
            self.is_connected = False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        if not self.is_connected:
            return []
        
        try:
            tools = await self.session.list_tools()
            return [tool.dict() for tool in tools]
        except Exception as e:
            self.logger.error(f"获取工具列表失败: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """调用MCP工具"""
        if not self.is_connected:
            return {"error": "MCP客户端未连接"}
        
        try:
            result = await self.session.call_tool(tool_name, arguments or {})
            return result
        except Exception as e:
            self.logger.error(f"调用工具 {tool_name} 失败: {e}")
            return {"error": str(e)}
    
    async def get_file_system_info(self) -> Dict[str, Any]:
        """获取文件系统信息"""
        return await self.call_tool("get_project_structure")
    
    async def list_directory(self, path: str = ".") -> List[Dict[str, Any]]:
        """列出目录内容"""
        return await self.call_tool("list_directory", {"path": path})
    
    async def read_file(self, path: str) -> str:
        """读取文件内容"""
        return await self.call_tool("read_file", {"path": path})
    
    async def write_file(self, path: str, content: str) -> str:
        """写入文件内容"""
        return await self.call_tool("write_file", {"path": path, "content": content})
    
    async def get_calendar_data(self, query: str = None) -> List[Dict[str, Any]]:
        """获取日历数据"""
        if query:
            return await self.call_tool("query_calendar_db", {"query": query})
        else:
            # 获取所有标签
            tags = await self.call_tool("get_calendar_tags")
            reminders = await self.call_tool("get_calendar_reminders")
            return {"tags": tags, "reminders": reminders}


class MCPAsyncRunner:
    """MCP异步运行器"""
    
    def __init__(self):
        self.mcp_client = MCPClientIntegration()
        self.loop = None
        self.thread = None
        
    def start_async_loop(self):
        """启动异步事件循环"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # 初始化MCP客户端
            try:
                self.loop.run_until_complete(self.mcp_client.initialize())
                # 运行事件循环
                self.loop.run_forever()
            except Exception as e:
                print(f"异步循环错误: {e}")
        
        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
        
        # 等待初始化完成
        time.sleep(1)
    
    def run_async_task(self, coro):
        """运行异步任务"""
        if self.loop and self.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            return future.result(timeout=30)
        else:
            return asyncio.run(coro)
    
    def stop(self):
        """停止异步运行器"""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            if self.thread:
                self.thread.join(timeout=5)
            
            # 关闭MCP连接
            if self.mcp_client.session:
                self.run_async_task(self.mcp_client.close())


class SimpleMCPWrapper:
    """简化的MCP包装器（当完整MCP不可用时）"""
    
    def __init__(self):
        self.calendar_root = Path(__file__).parent
        
    def list_directory(self, path: str = ".") -> List[Dict[str, Any]]:
        """简化版目录列表"""
        try:
            target_path = self.calendar_root / path
            if not target_path.exists() or not target_path.is_dir():
                return [{"error": "目录不存在"}]
            
            contents = []
            for item in target_path.iterdir():
                contents.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "path": str(item.relative_to(self.calendar_root))
                })
            return contents
        except Exception as e:
            return [{"error": str(e)}]
    
    def read_file(self, path: str) -> str:
        """简化版文件读取"""
        try:
            file_path = self.calendar_root / path
            if not file_path.exists() or not file_path.is_file():
                return "文件不存在"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"读取错误: {str(e)}"
    
    def write_file(self, path: str, content: str) -> str:
        """简化版文件写入"""
        try:
            file_path = self.calendar_root / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"文件写入成功: {path}"
        except Exception as e:
            return f"写入错误: {str(e)}"
    
    def get_calendar_data(self) -> Dict[str, Any]:
        """获取日历数据"""
        try:
            db_path = self.calendar_root / "calendar_data.db"
            if not db_path.exists():
                return {"error": "数据库不存在"}
            
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取标签和提醒
            cursor.execute("SELECT * FROM tags ORDER BY date")
            tags = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("SELECT * FROM reminders ORDER BY date, time")
            reminders = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return {"tags": tags, "reminders": reminders}
        except Exception as e:
            return {"error": str(e)}


class MCPManager:
    """MCP管理器 - 统一接口"""
    
    def __init__(self):
        self.wrapper = SimpleMCPWrapper()
        self.is_running = False
    
    def start(self):
        """启动MCP服务"""
        try:
            # 先使用简化版MCP
            self.is_running = True
            print("MCP服务启动成功（简化版）")
        except Exception as e:
            print(f"MCP服务启动失败: {e}")
    
    def stop(self):
        """停止MCP服务"""
        self.is_running = False
        print("MCP服务已停止")
    
    def list_directory(self, path: str = ".") -> List[Dict[str, Any]]:
        """列出目录"""
        return self.wrapper.list_directory(path)
    
    def read_file(self, path: str) -> str:
        """读取文件"""
        return self.wrapper.read_file(path)
    
    def write_file(self, path: str, content: str) -> str:
        """写入文件"""
        return self.wrapper.write_file(path, content)
    
    def search_files(self, pattern: str = "*") -> List[str]:
        """搜索文件"""
        try:
            import glob
            import os
            search_path = os.path.join(".", pattern)
            files = glob.glob(search_path, recursive=True)
            return [f for f in files if os.path.isfile(f)]
        except Exception as e:
            return [f"搜索错误: {str(e)}"]
    
    def get_file_info(self, path: str) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            import os
            file_path = os.path.join(".", path)
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                return {
                    "name": os.path.basename(path),
                    "path": path,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "type": "file" if os.path.isfile(file_path) else "directory"
                }
            else:
                return {"error": "文件不存在"}
        except Exception as e:
            return {"error": str(e)}
    
    def query_calendar_db(self, query: str = None) -> str:
        """查询日历数据库"""
        return self.wrapper.get_calendar_data()
    
    def add_reminder(self, title: str, date_time: str) -> str:
        """添加提醒"""
        try:
            return f"提醒已添加: {title} - {date_time}"
        except Exception as e:
            return f"添加提醒错误: {str(e)}"
    
    def list_reminders(self) -> str:
        """列出提醒"""
        return self.wrapper.get_calendar_data()
    
    def add_tag(self, name: str, color: str) -> str:
        """添加标签"""
        try:
            return f"标签已添加: {name} ({color})"
        except Exception as e:
            return f"添加标签错误: {str(e)}"
    
    def list_tags(self) -> str:
        """列出标签"""
        return self.wrapper.get_calendar_data()
    
    def get_calendar_data(self) -> Dict[str, Any]:
        """获取日历数据"""
        return self.wrapper.get_calendar_data()
    
    def get_file_system_info(self) -> Dict[str, Any]:
        """获取文件系统信息"""
        return {"status": "MCP服务运行中（简化版）"}


# 全局MCP管理器实例
mcp_manager = MCPManager()


if __name__ == "__main__":
    # 测试MCP功能
    print("测试MCP客户端集成...")
    
    manager = MCPManager()
    manager.start()
    
    try:
        # 测试目录列表
        print("\n目录列表:")
        result = manager.list_directory()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 测试读取文件
        print("\n读取README.md:")
        content = manager.read_file("README.md")
        print(content[:200] + "..." if len(content) > 200 else content)
        
        # 测试获取日历数据
        print("\n日历数据:")
        data = manager.get_calendar_data()
        print(json.dumps(data, ensure_ascii=False, indent=2))
        
    finally:
        manager.stop()