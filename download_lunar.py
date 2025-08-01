import requests
import os

def download_lunar_js():
    """从GitHub下载lunar.js文件"""
    print("正在从GitHub下载lunar.js文件...")
    url = "https://raw.githubusercontent.com/6tail/lunar-javascript/master/lunar.js"
    response = requests.get(url)
    if response.status_code == 200:
        with open("lunar.js", "wb") as f:
            f.write(response.content)
        print("下载完成！")
        return True
    else:
        print(f"下载失败，状态码: {response.status_code}")
        return False

def update_requirements():
    """更新requirements.txt文件"""
    with open("requirements.txt", "r", encoding="utf-8") as f:
        content = f.read()
    
    if "requests" not in content:
        with open("requirements.txt", "a", encoding="utf-8") as f:
            f.write("\nrequests>=2.25.0\n")
        print("已更新requirements.txt，添加了requests库")

def create_lunar_js_integration():
    """创建lunar_js_integration.py文件，用于集成lunar.js到Python"""
    content = '''
# lunar_js_integration.py
# 此文件用于将lunar.js集成到Python中

import os
import subprocess
import json
import datetime

class LunarJSBridge:
    """连接Python和lunar.js的桥接类"""
    
    def __init__(self):
        self.js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lunar.js")
        if not os.path.exists(self.js_path):
            raise FileNotFoundError(f"找不到lunar.js文件，请先运行download_lunar.py下载")
    
    def _execute_js(self, js_code):
        """执行JavaScript代码并返回结果"""
        # 使用Node.js执行JavaScript代码
        try:
            # 创建临时JS文件
            temp_js = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_lunar_exec.js")
            with open(temp_js, "w", encoding="utf-8") as f:
                f.write(f"const lunar = require('./lunar.js');\n")
                f.write(f"console.log(JSON.stringify({js_code}));")
            
            # 执行JS文件
            result = subprocess.check_output(["node", temp_js], text=True)
            
            # 删除临时文件
            os.remove(temp_js)
            
            # 解析JSON结果
            return json.loads(result.strip())
        except subprocess.CalledProcessError as e:
            print(f"执行JavaScript代码时出错: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"解析JavaScript结果时出错: {e}")
            return None
    
    def get_lunar_info(self, year, month, day):
        """获取指定日期的农历信息"""
        js_code = f"lunar.Lunar.fromYmd({year}, {month}, {day}).toFullString()"
        return self._execute_js(js_code)
    
    def get_lunar_month(self, year, month, day):
        """获取农历月份"""
        js_code = f"lunar.Lunar.fromYmd({year}, {month}, {day}).getMonthInChinese()"
        return self._execute_js(js_code)
    
    def get_lunar_day(self, year, month, day):
        """获取农历日期"""
        js_code = f"lunar.Lunar.fromYmd({year}, {month}, {day}).getDayInChinese()"
        return self._execute_js(js_code)
    
    def get_lunar_year(self, year, month, day):
        """获取农历年份"""
        js_code = f"lunar.Lunar.fromYmd({year}, {month}, {day}).getYearInChinese()"
        return self._execute_js(js_code)
    
    def get_lunar_festivals(self, year, month, day):
        """获取农历节日"""
        js_code = f"lunar.Lunar.fromYmd({year}, {month}, {day}).getFestivals()"
        return self._execute_js(js_code)
    
    def get_solar_festivals(self, year, month, day):
        """获取公历节日"""
        js_code = f"lunar.Solar.fromYmd({year}, {month}, {day}).getFestivals()"
        return self._execute_js(js_code)
    
    def get_jie_qi(self, year, month, day):
        """获取节气"""
        js_code = f"lunar.Lunar.fromYmd({year}, {month}, {day}).getJieQi()"
        return self._execute_js(js_code)
    
    def get_yi_ji(self, year, month, day):
        """获取宜忌"""
        js_code = f"{{\"yi\": lunar.Lunar.fromYmd({year}, {month}, {day}).getDayYi(), \"ji\": lunar.Lunar.fromYmd({year}, {month}, {day}).getDayJi()}}"
        return self._execute_js(js_code)
    
    def get_xiu(self, year, month, day):
        """获取星宿"""
        js_code = f"lunar.Lunar.fromYmd({year}, {month}, {day}).getXiu()"
        return self._execute_js(js_code)
    
    def get_zheng(self, year, month, day):
        """获取值神"""
        js_code = f"lunar.Lunar.fromYmd({year}, {month}, {day}).getZheng()"
        return self._execute_js(js_code)
    
    def get_animal(self, year, month, day):
        """获取生肖"""
        js_code = f"lunar.Lunar.fromYmd({year}, {month}, {day}).getAnimal()"
        return self._execute_js(js_code)
    
    def get_gong(self, year, month, day):
        """获取宫"""
        js_code = f"lunar.Lunar.fromYmd({year}, {month}, {day}).getGong()"
        return self._execute_js(js_code)
    
    def get_shou(self, year, month, day):
        """获取神兽"""
        js_code = f"lunar.Lunar.fromYmd({year}, {month}, {day}).getShou()"
        return self._execute_js(js_code)

# 测试代码
if __name__ == "__main__":
    try:
        bridge = LunarJSBridge()
        today = datetime.datetime.now()
        lunar_info = bridge.get_lunar_info(today.year, today.month, today.day)
        print(f"今日农历: {lunar_info}")
        
        yi_ji = bridge.get_yi_ji(today.year, today.month, today.day)
        print(f"今日宜: {yi_ji['yi']}")
        print(f"今日忌: {yi_ji['ji']}")
        
        animal = bridge.get_animal(today.year, today.month, today.day)
        print(f"生肖: {animal}")
    except Exception as e:
        print(f"测试时出错: {e}")
'''
    
    with open("lunar_js_integration.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("已创建lunar_js_integration.py文件")

def create_calendar_app_update():
    """创建calendar_app_update.py文件，用于更新calendar_app.py"""
    content = '''
# calendar_app_update.py
# 此文件用于更新calendar_app.py，集成lunar-javascript功能

import os
import re

def update_calendar_app():
    """更新calendar_app.py文件，集成lunar-javascript功能"""
    # 读取原始文件
    with open("calendar_app.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 备份原始文件
    with open("calendar_app.py.bak", "w", encoding="utf-8") as f:
        f.write(content)
    print("已备份原始calendar_app.py文件为calendar_app.py.bak")
    
    # 添加lunar_js_integration导入
    import_pattern = r"import os\nfrom tkinter import ttk, messagebox, simpledialog"
    new_import = "import os\nfrom tkinter import ttk, messagebox, simpledialog\n\n# 导入lunar-javascript集成模块\ntry:\n    from lunar_js_integration import LunarJSBridge\n    LUNAR_JS_AVAILABLE = True\nexcept ImportError:\n    LUNAR_JS_AVAILABLE = False\n    print(\"警告: lunar-javascript集成模块未找到，将使用lunar-python或降级模式\")\n"
    content = re.sub(import_pattern, new_import, content)
    
    # 修改LUNAR_AVAILABLE检查
    lunar_check_pattern = r"# 尝试导入lunar-python库，如果不可用则使用降级模式\ntry:\n    from lunar_python import Lunar, Solar\n    LUNAR_AVAILABLE = True\nexcept ImportError:\n    LUNAR_AVAILABLE = False\n    print\(\"警告: lunar-python库未安装，将只显示公历日期\"\)\n    print\(\"请运行: pip install lunar-python 以启用农历功能\"\)"
    new_lunar_check = "# 尝试导入lunar-python库，如果不可用则尝试使用lunar-javascript或降级模式\ntry:\n    from lunar_python import Lunar, Solar\n    LUNAR_PYTHON_AVAILABLE = True\n    LUNAR_AVAILABLE = True\nexcept ImportError:\n    LUNAR_PYTHON_AVAILABLE = False\n    LUNAR_AVAILABLE = LUNAR_JS_AVAILABLE\n    if not LUNAR_AVAILABLE:\n        print(\"警告: lunar-python库和lunar-javascript都未安装，将只显示公历日期\")\n        print(\"请运行: pip install lunar-python 以启用农历功能\")\n        print(\"或运行: python download_lunar.py 以启用lunar-javascript功能\")"
    content = re.sub(lunar_check_pattern, new_lunar_check, content)
    
    # 修改update_calendar方法中的农历获取部分
    lunar_update_pattern = r"# 获取农历（如果可用）\n                    if LUNAR_AVAILABLE:\n                        try:\n                            solar = Solar\.fromYmd\(self\.selected_year, self\.selected_month, day\)\n                            lunar = Lunar\.fromSolar\(solar\)\n                            lunar_day = lunar\.getDayInChinese\(\)\n                            \n                            # 始终显示农历月份和日期\n                            lunar_month = lunar\.getMonthInChinese\(\)\n                            lunar_text = f\"{lunar_month}月{lunar_day}\"\n                        except Exception as e:\n                            lunar_text = \"\"\n                            print\(f\"农历转换错误: {e}\"\)\n                    else:\n                        lunar_text = \"\""
    new_lunar_update = "# 获取农历（如果可用）\n                    if LUNAR_AVAILABLE:\n                        try:\n                            if LUNAR_PYTHON_AVAILABLE:\n                                solar = Solar.fromYmd(self.selected_year, self.selected_month, day)\n                                lunar = Lunar.fromSolar(solar)\n                                lunar_day = lunar.getDayInChinese()\n                                \n                                # 始终显示农历月份和日期\n                                lunar_month = lunar.getMonthInChinese()\n                                lunar_text = f\"{lunar_month}月{lunar_day}\"\n                            elif LUNAR_JS_AVAILABLE:\n                                # 使用lunar-javascript获取农历信息\n                                try:\n                                    if not hasattr(self, 'lunar_bridge'):\n                                        self.lunar_bridge = LunarJSBridge()\n                                    \n                                    lunar_month = self.lunar_bridge.get_lunar_month(self.selected_year, self.selected_month, day)\n                                    lunar_day = self.lunar_bridge.get_lunar_day(self.selected_year, self.selected_month, day)\n                                    lunar_text = f\"{lunar_month}月{lunar_day}\"\n                                    \n                                    # 获取节日、节气等信息\n                                    festivals = []\n                                    lunar_festivals = self.lunar_bridge.get_lunar_festivals(self.selected_year, self.selected_month, day)\n                                    if lunar_festivals and isinstance(lunar_festivals, list) and len(lunar_festivals) > 0:\n                                        festivals.extend(lunar_festivals)\n                                    \n                                    solar_festivals = self.lunar_bridge.get_solar_festivals(self.selected_year, self.selected_month, day)\n                                    if solar_festivals and isinstance(solar_festivals, list) and len(solar_festivals) > 0:\n                                        festivals.extend(solar_festivals)\n                                    \n                                    jie_qi = self.lunar_bridge.get_jie_qi(self.selected_year, self.selected_month, day)\n                                    if jie_qi and jie_qi != \"\":\n                                        festivals.append(jie_qi)\n                                    \n                                    # 如果有节日或节气，添加到日期框中\n                                    if festivals:\n                                        lunar_text += \" \" + \",\".join(festivals)\n                                except Exception as e:\n                                    print(f\"lunar-javascript转换错误: {e}\")\n                        except Exception as e:\n                            lunar_text = \"\"\n                            print(f\"农历转换错误: {e}\")\n                    else:\n                        lunar_text = \"\""
    content = re.sub(lunar_update_pattern, new_lunar_update, content)
    
    # 添加显示宜忌信息的方法
    show_tag_popup_pattern = r"def show_tag_popup\(self, day, color=None\):\n        \"\"\"显示标签弹窗\"\"\""
    new_method = "def show_yi_ji_info(self, day):\n        \"\"\"显示宜忌信息弹窗\"\"\"\n        if not LUNAR_JS_AVAILABLE:\n            messagebox.showinfo(\"提示\", \"此功能需要lunar-javascript支持，请运行download_lunar.py下载\")\n            return\n        \n        date_str = f\"{self.selected_year}-{self.selected_month:02d}-{day:02d}\"\n        \n        try:\n            if not hasattr(self, 'lunar_bridge'):\n                self.lunar_bridge = LunarJSBridge()\n            \n            yi_ji = self.lunar_bridge.get_yi_ji(self.selected_year, self.selected_month, day)\n            animal = self.lunar_bridge.get_animal(self.selected_year, self.selected_month, day)\n            xiu = self.lunar_bridge.get_xiu(self.selected_year, self.selected_month, day)\n            zheng = self.lunar_bridge.get_zheng(self.selected_year, self.selected_month, day)\n            lunar_info = self.lunar_bridge.get_lunar_info(self.selected_year, self.selected_month, day)\n            \n            # 创建弹窗\n            popup = tk.Toplevel(self.root)\n            popup.title(f\"农历详细信息 - {date_str}\")\n            popup.geometry(\"600x500\")\n            popup.transient(self.root)\n            popup.grab_set()\n            \n            # 信息显示框架\n            main_frame = ttk.Frame(popup, padding=10)\n            main_frame.pack(fill=tk.BOTH, expand=True)\n            \n            # 使用Text控件显示信息，支持滚动\n            info_frame = ttk.Frame(main_frame)\n            info_frame.pack(fill=tk.BOTH, expand=True, pady=10)\n            \n            info_text = tk.Text(info_frame, wrap=tk.WORD, width=70, height=25)\n            info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)\n            \n            scrollbar = ttk.Scrollbar(info_frame, orient=\"vertical\", command=info_text.yview)\n            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)\n            info_text.configure(yscrollcommand=scrollbar.set)\n            \n            # 插入信息\n            info_text.insert(tk.END, f\"日期: {date_str}\\n\")\n            info_text.insert(tk.END, f\"农历: {lunar_info}\\n\\n\")\n            \n            info_text.insert(tk.END, f\"生肖: {animal}\\n\")\n            info_text.insert(tk.END, f\"星宿: {xiu}\\n\")\n            if zheng:\n                info_text.insert(tk.END, f\"值神: {zheng}\\n\")\n            \n            info_text.insert(tk.END, \"\\n宜:\\n\")\n            if yi_ji and 'yi' in yi_ji and yi_ji['yi']:\n                for item in yi_ji['yi']:\n                    info_text.insert(tk.END, f\"  {item}\\n\")\n            else:\n                info_text.insert(tk.END, \"  无\\n\")\n            \n            info_text.insert(tk.END, \"\\n忌:\\n\")\n            if yi_ji and 'ji' in yi_ji and yi_ji['ji']:\n                for item in yi_ji['ji']:\n                    info_text.insert(tk.END, f\"  {item}\\n\")\n            else:\n                info_text.insert(tk.END, \"  无\\n\")\n            \n            # 设置只读\n            info_text.configure(state=\"disabled\")\n            \n            # 关闭按钮\n            ttk.Button(main_frame, text=\"关闭\", command=popup.destroy).pack(pady=10)\n            \n        except Exception as e:\n            messagebox.showerror(\"错误\", f\"获取农历信息失败: {e}\")\n    \n    def show_tag_popup(self, day, color=None):\n        \"\"\"显示标签弹窗\"\"\""
    content = re.sub(show_tag_popup_pattern, new_method, content)
    
    # 修改日历日期点击事件，添加右键菜单
    day_click_pattern = r"# 设置点击事件\n                    day_frame\.bind\(\"<Button-1>\", lambda e, d=day: self\.select_day\(d\)\)\n                    date_label\.bind\(\"<Button-1>\", lambda e, d=day: self\.select_day\(d\)\)\n                    lunar_label\.bind\(\"<Button-1>\", lambda e, d=day: self\.select_day\(d\)\)"
    new_day_click = "# 设置点击事件\n                    day_frame.bind(\"<Button-1>\", lambda e, d=day: self.select_day(d))\n                    date_label.bind(\"<Button-1>\", lambda e, d=day: self.select_day(d))\n                    lunar_label.bind(\"<Button-1>\", lambda e, d=day: self.select_day(d))\n                    \n                    # 添加右键菜单，显示农历详细信息\n                    if LUNAR_JS_AVAILABLE:\n                        day_frame.bind(\"<Button-3>\", lambda e, d=day: self.show_yi_ji_info(d))\n                        date_label.bind(\"<Button-3>\", lambda e, d=day: self.show_yi_ji_info(d))\n                        lunar_label.bind(\"<Button-3>\", lambda e, d=day: self.show_yi_ji_info(d))"
    content = re.sub(day_click_pattern, new_day_click, content)
    
    # 写入更新后的文件
    with open("calendar_app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("已更新calendar_app.py文件，集成了lunar-javascript功能")

if __name__ == "__main__":
    update_calendar_app()
'''
    
    with open("calendar_app_update.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("已创建calendar_app_update.py文件")

if __name__ == "__main__":
    # 下载lunar.js
    if download_lunar_js():
        # 更新requirements.txt
        update_requirements()
        # 创建集成文件
        create_lunar_js_integration()
        # 创建更新脚本
        create_calendar_app_update()
        
        print("\n所有文件已准备就绪！")
        print("请按照以下步骤操作：")
        print("1. 运行 'pip install -r requirements.txt' 安装依赖")
        print("2. 确保已安装Node.js（用于执行JavaScript）")
        print("3. 运行 'python calendar_app_update.py' 更新日历应用")
        print("4. 运行 'python calendar_app.py' 启动更新后的日历应用")
        print("\n提示：右键点击日历中的日期可以查看详细的农历信息、宜忌等内容")
    else:
        print("下载失败，请检查网络连接后重试")