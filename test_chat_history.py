#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试聊天历史功能
"""

import sqlite3
import datetime

def test_database():
    """测试数据库表结构"""
    conn = sqlite3.connect('calendar_data.db')
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('chat_sessions', 'chat_messages')")
    tables = cursor.fetchall()
    print("数据库表:", [table[0] for table in tables])
    
    # 检查表结构
    if tables:
        cursor.execute("PRAGMA table_info(chat_sessions)")
        session_columns = cursor.fetchall()
        print("chat_sessions表结构:")
        for col in session_columns:
            print(f"  {col[1]} {col[2]}")
        
        cursor.execute("PRAGMA table_info(chat_messages)")
        message_columns = cursor.fetchall()
        print("chat_messages表结构:")
        for col in message_columns:
            print(f"  {col[1]} {col[2]}")
    
    conn.close()

def create_test_data():
    """创建测试数据"""
    conn = sqlite3.connect('calendar_data.db')
    cursor = conn.cursor()
    
    # 创建测试会话
    cursor.execute("""
        INSERT INTO chat_sessions (title, created_at, updated_at) 
        VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, ("测试对话1",))
    session_id = cursor.lastrowid
    
    # 创建测试消息
    test_messages = [
        ("user", "你好，请介绍一下Python"),
        ("assistant", "Python是一种高级编程语言，具有简洁的语法和强大的功能。"),
        ("user", "Python有什么特点？"),
        ("assistant", "Python的特点包括：\n1. 简洁易读的语法\n2. 丰富的标准库\n3. 跨平台兼容性\n4. 强大的第三方库生态")
    ]
    
    for role, content in test_messages:
        cursor.execute("""
            INSERT INTO chat_messages (session_id, role, content) 
            VALUES (?, ?, ?)
        """, (session_id, role, content))
    
    conn.commit()
    conn.close()
    print(f"创建了测试会话，ID: {session_id}")

if __name__ == "__main__":
    print("=== 测试聊天历史功能 ===")
    test_database()
    print("\n=== 创建测试数据 ===")
    create_test_data()
    print("\n测试完成！现在可以运行主程序查看聊天历史功能。") 