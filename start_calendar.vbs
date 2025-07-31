' 无窗口启动日历应用程序的VBS脚本
Option Explicit

Dim WshShell, fso, currentDir, pythonExe, calendarApp

' 创建Shell对象
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 获取当前脚本所在目录
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)


' 安装依赖包
WshShell.Run "pip install -r """ & currentDir & "\requirements.txt"" -q", 0, True
WshShell.Run "pip install pystray pillow -q", 0, True

' 启动应用程序（隐藏窗口）
WshShell.Run "pythonw """ & currentDir & "\calendar_app.py""", 0, False

' 释放对象
Set WshShell = Nothing
Set fso = Nothing