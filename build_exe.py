#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstaller打包脚本
用于将日历应用打包成Windows可执行文件
"""

import os
import sys
import PyInstaller.__main__
import shutil
from pathlib import Path

def build_exe():
    """构建Windows可执行文件"""
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 主程序文件
    main_script = os.path.join(current_dir, "calendar_app.py")
    
    # Python模块文件（需要包含在打包中）
    python_modules = [
        "calendar_app_update.py",
        "download_lunar.py",
        "lunar_js_integration.py",
    ]
    
    # 数据文件
    data_files = [
        ("lunar.js", "."),
        ("calendar_data.db", "."),
    ]
    
    # 检查并创建数据文件
    lunar_js_path = os.path.join(current_dir, "lunar.js")
    if not os.path.exists(lunar_js_path):
        print("警告: lunar.js 不存在，农历功能可能无法使用")
        print("请运行 download_lunar.py 下载 lunar.js")
        download_script = os.path.join(current_dir, "download_lunar.py")
        if os.path.exists(download_script):
            print(f"或者先运行: python {download_script}")
    
    # 构建PyInstaller命令参数
    args = [
        main_script,
        '--name=CalendarApp',
        '--onefile',
        '--windowed',
        '--noconfirm',
        '--clean',
        
        # 包含数据文件
        '--add-data=lunar.js;.',
        '--add-data=calendar_data.db;.',
        
        # 包含Python模块文件
        '--add-data=calendar_app_update.py;.',
        '--add-data=download_lunar.py;.',
        '--add-data=lunar_js_integration.py;.',
        
        # 包含隐藏导入
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=PIL.ImageDraw',
        '--hidden-import=pystray',
        '--hidden-import=requests',
        '--hidden-import=lunar_python',
        '--hidden-import=lunar_js_integration',
        
        # 图标
        '--icon=NONE',
        
        # 优化
        '--optimize=2',
        
        # 输出目录
        '--distpath=./dist',
        '--workpath=./build',
        '--specpath=./',
    ]
    
    # 打印打包信息
    print("开始打包日历应用...")
    print(f"主程序: {main_script}")
    print(f"输出目录: {os.path.join(current_dir, 'dist')}")
    
    try:
        # 执行打包
        PyInstaller.__main__.run(args)
        
        # 复制其他必要文件到dist目录
        dist_dir = os.path.join(current_dir, "dist")
        
        # 复制文档文件
        for file in ["README.md", "LLM使用说明.md"]:
            src = os.path.join(current_dir, file)
            if os.path.exists(src):
                dst = os.path.join(dist_dir, file)
                shutil.copy2(src, dst)
                print(f"已复制: {file}")
        
        # 复制Python模块文件（作为源码参考）
        python_files = ["calendar_app_update.py", "download_lunar.py", "lunar_js_integration.py"]
        for file in python_files:
            src = os.path.join(current_dir, file)
            if os.path.exists(src):
                dst = os.path.join(dist_dir, file)
                shutil.copy2(src, dst)
                print(f"已复制: {file}")
        
        # 复制requirements.txt（方便用户查看依赖）
        req_file = "requirements.txt"
        src = os.path.join(current_dir, req_file)
        if os.path.exists(src):
            dst = os.path.join(dist_dir, req_file)
            shutil.copy2(src, dst)
            print(f"已复制: {req_file}")
        
        print("\n打包完成！")
        print(f"可执行文件位置: {os.path.join(dist_dir, 'CalendarApp.exe')}")
        
        # 创建启动脚本
        create_start_script(dist_dir)
        
    except Exception as e:
        print(f"打包失败: {str(e)}")
        return False
    
    return True

def create_start_script(dist_dir):
    """创建启动脚本"""
    
    # 创建批处理启动脚本
    bat_content = """@echo off
echo 正在启动日历应用...
cd /d "%~dp0"
start CalendarApp.exe
"""
    
    bat_path = os.path.join(dist_dir, "启动日历应用.bat")
    with open(bat_path, 'w', encoding='gbk') as f:
        f.write(bat_content)
    
    print(f"已创建启动脚本: {bat_path}")

if __name__ == "__main__":
    build_exe()