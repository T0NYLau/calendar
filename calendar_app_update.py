
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
    new_import = '''import os
from tkinter import ttk, messagebox, simpledialog

# 导入lunar-javascript集成模块
try:
    from lunar_js_integration import LunarJSBridge
    LUNAR_JS_AVAILABLE = True
except ImportError:
    LUNAR_JS_AVAILABLE = False
    print("警告: lunar-javascript集成模块未找到，将使用lunar-python或降级模式")
'''
    content = re.sub(import_pattern, new_import, content)
    
    # 修改LUNAR_AVAILABLE检查
    lunar_check_pattern = r"# 尝试导入lunar-python库，如果不可用则使用降级模式\ntry:\n    from lunar_python import Lunar, Solar\n    LUNAR_AVAILABLE = True\nexcept ImportError:\n    LUNAR_AVAILABLE = False\n    print\(\"警告: lunar-python库未安装，将只显示公历日期\"\)\n    print\(\"请运行: pip install lunar-python 以启用农历功能\"\)"
    new_lunar_check = '''# 尝试导入lunar-python库，如果不可用则尝试使用lunar-javascript或降级模式
try:
    from lunar_python import Lunar, Solar
    LUNAR_PYTHON_AVAILABLE = True
    LUNAR_AVAILABLE = True
except ImportError:
    LUNAR_PYTHON_AVAILABLE = False
    LUNAR_AVAILABLE = LUNAR_JS_AVAILABLE
    if not LUNAR_AVAILABLE:
        print("警告: lunar-python库和lunar-javascript都未安装，将只显示公历日期")
        print("请运行: pip install lunar-python 以启用农历功能")
        print("或运行: python download_lunar.py 以启用lunar-javascript功能")'''
    content = re.sub(lunar_check_pattern, new_lunar_check, content)
    
    # 修改update_calendar方法中的农历获取部分
    lunar_update_pattern = r"# 获取农历（如果可用）\n                    if LUNAR_AVAILABLE:\n                        try:\n                            solar = Solar\.fromYmd\(self\.selected_year, self\.selected_month, day\)\n                            lunar = Lunar\.fromSolar\(solar\)\n                            lunar_day = lunar\.getDayInChinese\(\)\n                            \n                            # 始终显示农历月份和日期\n                            lunar_month = lunar\.getMonthInChinese\(\)\n                            lunar_text = f\"{lunar_month}月{lunar_day}\"\n                        except Exception as e:\n                            lunar_text = \"\"\n                            print\(f\"农历转换错误: {e}\"\)\n                    else:\n                        lunar_text = \"\""
    new_lunar_update = '''# 获取农历（如果可用）
                    if LUNAR_AVAILABLE:
                        try:
                            if LUNAR_PYTHON_AVAILABLE:
                                solar = Solar.fromYmd(self.selected_year, self.selected_month, day)
                                lunar = Lunar.fromSolar(solar)
                                lunar_day = lunar.getDayInChinese()
                                
                                # 始终显示农历月份和日期
                                lunar_month = lunar.getMonthInChinese()
                                lunar_text = f"{lunar_month}月{lunar_day}"
                            elif LUNAR_JS_AVAILABLE:
                                # 使用lunar-javascript获取农历信息
                                try:
                                    if not hasattr(self, 'lunar_bridge'):
                                        self.lunar_bridge = LunarJSBridge()
                                    
                                    lunar_month = self.lunar_bridge.get_lunar_month(self.selected_year, self.selected_month, day)
                                    lunar_day = self.lunar_bridge.get_lunar_day(self.selected_year, self.selected_month, day)
                                    lunar_text = f"{lunar_month}月{lunar_day}"
                                    
                                    # 获取节日、节气等信息
                                    festivals = []
                                    lunar_festivals = self.lunar_bridge.get_lunar_festivals(self.selected_year, self.selected_month, day)
                                    if lunar_festivals and isinstance(lunar_festivals, list) and len(lunar_festivals) > 0:
                                        festivals.extend(lunar_festivals)
                                    
                                    solar_festivals = self.lunar_bridge.get_solar_festivals(self.selected_year, self.selected_month, day)
                                    if solar_festivals and isinstance(solar_festivals, list) and len(solar_festivals) > 0:
                                        festivals.extend(solar_festivals)
                                    
                                    jie_qi = self.lunar_bridge.get_jie_qi(self.selected_year, self.selected_month, day)
                                    if jie_qi and jie_qi != "":
                                        festivals.append(jie_qi)
                                    
                                    # 如果有节日或节气，添加到日期框中
                                    if festivals:
                                        lunar_text += " " + ",".join(festivals)
                                except Exception as e:
                                    print(f"lunar-javascript转换错误: {e}")
                        except Exception as e:
                            lunar_text = ""
                            print(f"农历转换错误: {e}")
                    else:
                        lunar_text = ""'''
    content = re.sub(lunar_update_pattern, new_lunar_update, content)
    
    # 添加显示宜忌信息的方法
    show_tag_popup_pattern = r"def show_tag_popup\(self, day, color=None\):\n        \"\"\"显示标签弹窗\"\"\""
    new_method = '''def show_yi_ji_info(self, day):
        """显示宜忌信息弹窗"""
        if not LUNAR_JS_AVAILABLE:
            messagebox.showinfo("提示", "此功能需要lunar-javascript支持，请运行download_lunar.py下载")
            return
        
        date_str = f"{self.selected_year}-{self.selected_month:02d}-{day:02d}"
        
        try:
            if not hasattr(self, 'lunar_bridge'):
                self.lunar_bridge = LunarJSBridge()
            
            yi_ji = self.lunar_bridge.get_yi_ji(self.selected_year, self.selected_month, day)
            animal = self.lunar_bridge.get_animal(self.selected_year, self.selected_month, day)
            xiu = self.lunar_bridge.get_xiu(self.selected_year, self.selected_month, day)
            zheng = self.lunar_bridge.get_zheng(self.selected_year, self.selected_month, day)
            lunar_info = self.lunar_bridge.get_lunar_info(self.selected_year, self.selected_month, day)
            
            # 创建弹窗
            popup = tk.Toplevel(self.root)
            popup.title(f"农历详细信息 - {date_str}")
            popup.geometry("600x500")
            popup.transient(self.root)
            popup.grab_set()
            
            # 信息显示框架
            main_frame = ttk.Frame(popup, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 使用Text控件显示信息，支持滚动
            info_frame = ttk.Frame(main_frame)
            info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            info_text = tk.Text(info_frame, wrap=tk.WORD, width=70, height=25)
            info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            scrollbar = ttk.Scrollbar(info_frame, orient="vertical", command=info_text.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            info_text.configure(yscrollcommand=scrollbar.set)
            
            # 插入信息
            info_text.insert(tk.END, f"日期: {date_str}\n")
            info_text.insert(tk.END, f"农历: {lunar_info}\n\n")
            
            info_text.insert(tk.END, f"生肖: {animal}\n")
            info_text.insert(tk.END, f"星宿: {xiu}\n")
            if zheng:
                info_text.insert(tk.END, f"值神: {zheng}\n")
            
            info_text.insert(tk.END, "\n宜:\n")
            if yi_ji and 'yi' in yi_ji and yi_ji['yi']:
                for item in yi_ji['yi']:
                    info_text.insert(tk.END, f"  {item}\n")
            else:
                info_text.insert(tk.END, "  无\n")
            
            info_text.insert(tk.END, "\n忌:\n")
            if yi_ji and 'ji' in yi_ji and yi_ji['ji']:
                for item in yi_ji['ji']:
                    info_text.insert(tk.END, f"  {item}\n")
            else:
                info_text.insert(tk.END, "  无\n")
            
            # 设置只读
            info_text.configure(state="disabled")
            
            # 关闭按钮
            ttk.Button(main_frame, text="关闭", command=popup.destroy).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("错误", f"获取农历信息失败: {e}")
    
    def show_tag_popup(self, day, color=None):
        """显示标签弹窗"""'''
    content = re.sub(show_tag_popup_pattern, new_method, content)
    
    # 修改日历日期点击事件，添加右键菜单
    day_click_pattern = r"# 设置点击事件\n                    day_frame\.bind\(\"<Button-1>\", lambda e, d=day: self\.select_day\(d\)\)\n                    date_label\.bind\(\"<Button-1>\", lambda e, d=day: self\.select_day\(d\)\)\n                    lunar_label\.bind\(\"<Button-1>\", lambda e, d=day: self\.select_day\(d\)\)"
    new_day_click = '''# 设置点击事件
                    day_frame.bind("<Button-1>", lambda e, d=day: self.select_day(d))
                    date_label.bind("<Button-1>", lambda e, d=day: self.select_day(d))
                    lunar_label.bind("<Button-1>", lambda e, d=day: self.select_day(d))
                    
                    # 添加右键菜单，显示农历详细信息
                    if LUNAR_JS_AVAILABLE:
                        day_frame.bind("<Button-3>", lambda e, d=day: self.show_yi_ji_info(d))
                        date_label.bind("<Button-3>", lambda e, d=day: self.show_yi_ji_info(d))
                        lunar_label.bind("<Button-3>", lambda e, d=day: self.show_yi_ji_info(d))'''
    content = re.sub(day_click_pattern, new_day_click, content)
    
    # 写入更新后的文件
    with open("calendar_app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("已更新calendar_app.py文件，集成了lunar-javascript功能")

if __name__ == "__main__":
    update_calendar_app()
