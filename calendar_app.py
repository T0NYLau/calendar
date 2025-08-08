import tkinter as tk
import calendar
import datetime
import sqlite3
import os
import sys
import threading
import json
import subprocess
import requests
from tkinter import ttk, messagebox, simpledialog

# 导入系统托盘相关库
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    print("警告: pystray或PIL库未安装，系统托盘功能将不可用")
    print("请运行: pip install pystray pillow 以启用系统托盘功能")

# 检查lunar.js文件是否存在
LUNAR_JS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lunar.js")
LUNAR_JS_AVAILABLE = os.path.exists(LUNAR_JS_PATH)

# 尝试导入lunar-python库，如果不可用则尝试使用lunar-javascript或降级模式
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
        print("或运行: python download_lunar.py 以启用lunar-javascript功能")


class CalendarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("日历应用 - 公历/农历查看器")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 使用标准Windows窗口样式（恢复系统标题栏）
        self.root.overrideredirect(False)  # 恢复系统标题栏
        self.root.attributes('-topmost', False)  # 不置顶
        
        # 设置窗口背景为深色（但不是纯黑）
        self.root.configure(bg="#2b2b2b")
        
        # 不再创建自定义标题栏，使用系统标准标题栏
        # 移除自定义标题栏相关代码
        # self.create_custom_title_bar()
        
        # 设置全局样式
        style = ttk.Style()
        style.theme_use('clam')  # 使用 'clam' 主题
        
        # 设置全局样式为深色主题
        style.configure('.', background='#2b2b2b', foreground='white')
        
        # 配置输入框样式
        style.configure("TEntry", fieldbackground="#3c3c3c", foreground="white")
        
        # 配置Spinbox样式
        style.configure("TSpinbox", fieldbackground="#3c3c3c", foreground="white")
        
        # 配置Combobox样式
        style.configure("TCombobox", fieldbackground="#3c3c3c", foreground="white")
        
        # 配置Treeview样式
        style.configure("Treeview", background="#3c3c3c", foreground="white", fieldbackground="#3c3c3c")
        style.map("Treeview", background=[('selected', '#4a4a4a')], foreground=[('selected', 'white')])
        
        # 配置Treeview头部样式
        style.configure("Treeview.Heading", background="#3c3c3c", foreground="white")
        
        # 设置窗口图标和系统托盘图标
        self.setup_tray_icon()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 移除窗口拖动绑定，使用系统标准窗口管理
        # self.bind_window_drag()
        
        # 设置当前日期
        self.current_date = datetime.datetime.now()
        self.selected_year = self.current_date.year
        self.selected_month = self.current_date.month
        self.selected_day = self.current_date.day
        
        # 创建数据库连接
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calendar_data.db")
        self.create_database()
        
        # 创建UI组件
        self.create_widgets()
        
        # 显示日历
        self.update_calendar()
        
        # 检查今日提醒
        self.check_reminders()
        
        # 设置定时检查提醒（每小时检查一次）
        self.schedule_reminder_check()
    
    def search_with_search1api(self, query):
        """使用Search1API进行联网搜索"""
        try:
            API_URL = "https://api.search1api.com/search"
            
            data = {
                "query": query,
                "search_service": "google",
                "max_results": 5,
                "crawl_results": 0,
                "image": False,
                "language": "zh",
                "time_range": "day"
            }
            
            headers = {
                "Content-Type": "application/json",
                'Authorization': 'Bearer 80FA665F-208A-47E1-98D5-D694DC6689BE'
            }
            
            print(f"正在搜索: {query}")
            response = requests.post(
                API_URL,
                headers=headers,
                json=data,
                timeout=15
            )
            
            if response.status_code == 200:
                results = response.json()
                print(f"搜索成功，找到 {len(results.get('results', []))} 个结果")
                return results
            else:
                print(f"Search1API请求失败: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.Timeout:
            print("搜索请求超时")
            return None
        except requests.exceptions.RequestException as e:
            print(f"网络请求错误: {str(e)}")
            return None
        except Exception as e:
            print(f"Search1API搜索出错: {str(e)}")
            return None
    
    def format_search_results(self, search_results):
        """格式化搜索结果"""
        if not search_results or "results" not in search_results:
            return "未找到相关结果。"
        
        formatted = ""
        for i, result in enumerate(search_results["results"][:10], 1):  # 限制显示前10个结果
            title = result.get("title", "无标题")
            url = result.get("url", "无链接")
            snippet = result.get("snippet", "无摘要")
            formatted += f"{i}. {title}\n   {url}\n   {snippet}\n\n"
        
        return formatted.strip()
    
    def create_database(self):
        """创建SQLite数据库和表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            date TEXT,
            tag TEXT,
            color TEXT DEFAULT '#1E90FF'
        )
        ''')
        
        # 添加提醒功能表，支持复杂的重复模式
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY,
            date TEXT,
            time TEXT,
            message TEXT,
            is_active INTEGER DEFAULT 1,
            repeat_type TEXT DEFAULT 'none',
            repeat_value TEXT DEFAULT NULL
        )
        ''')
        
        # 添加LLM配置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS llm_configs (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                base_uri TEXT,
                model_name TEXT,
                api_key TEXT,
                temperature REAL DEFAULT 0.7,
                is_default INTEGER DEFAULT 0
            )
        ''')
        
        # 添加聊天历史表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY,
            session_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_widgets(self):
        """创建UI组件"""
        # 创建主框架（从标题栏下方开始）
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 顶部控制区域
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        # 年份选择
        ttk.Label(control_frame, text="年份:").pack(side=tk.LEFT, padx=5)
        self.year_var = tk.StringVar(value=str(self.selected_year))
        year_spin = ttk.Spinbox(control_frame, from_=1900, to=2100, textvariable=self.year_var, width=6)
        year_spin.pack(side=tk.LEFT, padx=5)
        year_spin.bind("<Return>", lambda e: self.change_year())
        
        # 年份导航按钮
        ttk.Button(control_frame, text="◀", width=2, command=self.prev_year).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="▶", width=2, command=self.next_year).pack(side=tk.LEFT, padx=5)
        
        # 月份选择
        ttk.Label(control_frame, text="月份:").pack(side=tk.LEFT, padx=5)
        self.month_var = tk.StringVar(value=str(self.selected_month))
        month_spin = ttk.Spinbox(control_frame, from_=1, to=12, textvariable=self.month_var, width=4)
        month_spin.pack(side=tk.LEFT, padx=5)
        month_spin.bind("<Return>", lambda e: self.change_month())
        
        # 月份导航按钮
        ttk.Button(control_frame, text="◀", width=2, command=self.prev_month).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="▶", width=2, command=self.next_month).pack(side=tk.LEFT, padx=5)
        
        # 返回今天按钮
        ttk.Button(control_frame, text="今天", command=self.go_to_today).pack(side=tk.LEFT, padx=20)
        
        # 查看所有标签按钮
        ttk.Button(control_frame, text="查看所有标签", command=self.show_all_tags).pack(side=tk.RIGHT, padx=5)
        
        # 测试提醒按钮（调试用）
        ttk.Button(control_frame, text="测试提醒", command=self.test_reminders).pack(side=tk.RIGHT, padx=5)
        
        # LLM按钮
        ttk.Button(control_frame, text="AI助手", command=self.show_llm_dialog).pack(side=tk.RIGHT, padx=5)
        
        # 日历区域
        self.calendar_frame = ttk.Frame(main_frame)
        self.calendar_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 颜色映射：中文名称到十六进制代码
        self.color_map = {
            "蓝色": "#1E90FF",
            "红色": "#FF6347",
            "绿色": "#32CD32",
            "黄色": "#FFD700",
            "紫色": "#9370DB",
            "粉色": "#FF69B4"
        }
        
        # 反向映射：十六进制代码到中文名称
        self.reverse_color_map = {v: k for k, v in self.color_map.items()}
    
    def update_calendar(self):
        """更新日历显示"""
        # 清除现有日历
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()
        
        # 创建星期标题
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for i, day in enumerate(weekdays):
            label = ttk.Label(self.calendar_frame, text=day, anchor="center", width=10)
            label.grid(row=0, column=i, sticky="nsew", padx=1, pady=1)
            if i >= 5:  # 周末使用不同颜色
                label.configure(foreground="red")
        
        # 获取当月的日历
        cal = calendar.monthcalendar(self.selected_year, self.selected_month)
        
        # 获取当月所有标签
        month_tags = self.get_month_tags()
        
        # 填充日历
        for week_idx, week in enumerate(cal):
            for day_idx, day in enumerate(week):
                if day != 0:
                    # 创建日期框架
                    day_frame = ttk.Frame(self.calendar_frame, borderwidth=1, relief="solid")
                    day_frame.grid(row=week_idx+1, column=day_idx, sticky="nsew", padx=1, pady=1)
                    self.calendar_frame.grid_columnconfigure(day_idx, weight=1)
                    self.calendar_frame.grid_rowconfigure(week_idx+1, weight=1)
                    
                    # 日期字符串 (YYYY-MM-DD)
                    date_str = f"{self.selected_year}-{self.selected_month:02d}-{day:02d}"
                    
                    # 获取农历（如果可用）
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
                        lunar_text = ""
                    
                    # 日期标签
                    date_label = ttk.Label(day_frame, text=str(day), anchor="center")
                    date_label.pack(fill=tk.X)
                    
                    # 农历标签
                    lunar_label = ttk.Label(day_frame, text=lunar_text, anchor="center", font=("SimSun", 9))
                    lunar_label.pack(fill=tk.X)
                    
                    # 检查是否有标签，如果有则显示标记
                    if date_str in month_tags:
                        tag_color = month_tags[date_str]["color"]
                        tag_marker = ttk.Label(day_frame, text="●", anchor="center", 
                                             foreground=tag_color, font=("SimSun", 12))
                        tag_marker.pack(fill=tk.X)
                        
                        # 为标记添加点击事件，显示标签内容
                        tag_marker.bind("<Button-1>", lambda e, d=day, c=tag_color: self.show_tag_popup(d, c))
                    
                    # 设置点击事件
                    day_frame.bind("<Button-1>", lambda e, d=day: self.select_day(d))
                    date_label.bind("<Button-1>", lambda e, d=day: self.select_day(d))
                    lunar_label.bind("<Button-1>", lambda e, d=day: self.select_day(d))
                    
                    # 添加右键菜单，显示农历详细信息
                    if LUNAR_JS_AVAILABLE:
                        day_frame.bind("<Button-3>", lambda e, d=day: self.show_yi_ji_info(d))
                        date_label.bind("<Button-3>", lambda e, d=day: self.show_yi_ji_info(d))
                        lunar_label.bind("<Button-3>", lambda e, d=day: self.show_yi_ji_info(d))
                    
                    # 高亮当前选中的日期
                    if (day == self.selected_day and 
                        self.selected_month == self.current_date.month and 
                        self.selected_year == self.current_date.year):
                        day_frame.configure(style="Selected.TFrame")
    
    def get_month_tags(self):
        """获取当月所有标签"""
        month_tags = {}
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查询当月的所有标签
        month_start = f"{self.selected_year}-{self.selected_month:02d}-01"
        month_end = f"{self.selected_year}-{self.selected_month:02d}-31"
        cursor.execute("SELECT date, tag, color FROM tags WHERE date BETWEEN ? AND ?", 
                      (month_start, month_end))
        
        for row in cursor.fetchall():
            month_tags[row[0]] = {"tag": row[1], "color": row[2]}
        
        conn.close()
        return month_tags
    
    def select_day(self, day):
        """选择日期"""
        self.selected_day = day
        date_str = f"{self.selected_year}-{self.selected_month:02d}-{day:02d}"
        
        # 高亮选中的日期并更新日历
        self.update_calendar()
        
        # 检查是否有标签，如果有则显示标签编辑弹窗
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT tag, color FROM tags WHERE date = ?", (date_str,))
        result = cursor.fetchone()
        
        if result:
            self.show_tag_popup(day, result[1])
        else:
            # 如果没有标签，询问是否添加
            if messagebox.askyesno("添加标签", f"是否要为 {date_str} 添加标签？"):
                self.add_tag_dialog(date_str)
        
        conn.close()
    
    def show_yi_ji_info(self, day):
        """显示宜忌信息弹窗"""
        if not LUNAR_JS_AVAILABLE:
            messagebox.showinfo("提示", "此功能需要lunar-javascript支持，请运行download_lunar.py下载")
            return
        
        date_str = f"{self.selected_year}-{self.selected_month:02d}-{day:02d}"
        
        try:
            # 创建一个临时JS文件，一次性获取所有需要的农历信息
            temp_js = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_lunar_exec.js")
            with open(temp_js, "w", encoding="utf-8") as f:
                f.write("const lunar = require('./lunar.js');\n")
                f.write(f"const solar = lunar.Solar.fromYmd({self.selected_year}, {self.selected_month}, {day});\n")
                f.write("const lunarObj = solar.getLunar();\n")
                f.write("const result = {\n")
                f.write("  lunar_info: lunarObj.toFullString(),\n")
                f.write("  yi_ji: {\n")
                f.write("    yi: lunarObj.getDayYi(),\n")
                f.write("    ji: lunarObj.getDayJi()\n")
                f.write("  },\n")
                f.write("  animal: lunarObj.getAnimal(),\n")
                f.write("  xiu: lunarObj.getXiu(),\n")
                f.write("  zheng: lunarObj.getZheng(),\n")
                f.write("  xiu_luck: lunarObj.getXiuLuck(),\n")
                f.write("  peng_zu_gan: lunarObj.getPengZuGan(),\n")
                f.write("  peng_zu_zhi: lunarObj.getPengZuZhi(),\n")
                f.write("  day_position_xi: lunarObj.getDayPositionXi(),\n")
                f.write("  day_position_xi_desc: lunarObj.getDayPositionXiDesc(),\n")
                f.write("  day_position_yang_gui: lunarObj.getDayPositionYangGui(),\n")
                f.write("  day_position_yang_gui_desc: lunarObj.getDayPositionYangGuiDesc(),\n")
                f.write("  day_position_yin_gui: lunarObj.getDayPositionYinGui(),\n")
                f.write("  day_position_yin_gui_desc: lunarObj.getDayPositionYinGuiDesc(),\n")
                f.write("  day_position_fu: lunarObj.getDayPositionFu(),\n")
                f.write("  day_position_fu_desc: lunarObj.getDayPositionFuDesc(),\n")
                f.write("  day_position_cai: lunarObj.getDayPositionCai(),\n")
                f.write("  day_position_cai_desc: lunarObj.getDayPositionCaiDesc(),\n")
                f.write("  day_chong_desc: lunarObj.getDayChongDesc(),\n")
                f.write("  day_sha: lunarObj.getDaySha(),\n")
                f.write("  gong: lunarObj.getGong(),\n")
                f.write("  shou: lunarObj.getShou()\n")
                f.write("};\n")
                f.write("console.log(JSON.stringify(result));")
            
            # 执行JS文件
            result = subprocess.check_output(["node", temp_js], text=True, encoding="utf-8")
            
            # 删除临时文件
            os.remove(temp_js)
            
            # 解析JSON结果
            data = json.loads(result.strip())
            
            # 获取解析后的数据
            lunar_info = data["lunar_info"]
            yi_ji = data["yi_ji"]
            animal = data["animal"]
            xiu = data["xiu"]
            zheng = data["zheng"]
            xiu_luck = data.get("xiu_luck", "")
            peng_zu_gan = data.get("peng_zu_gan", "")
            peng_zu_zhi = data.get("peng_zu_zhi", "")
            day_position_xi = data.get("day_position_xi", "")
            day_position_xi_desc = data.get("day_position_xi_desc", "")
            day_position_yang_gui = data.get("day_position_yang_gui", "")
            day_position_yang_gui_desc = data.get("day_position_yang_gui_desc", "")
            day_position_yin_gui = data.get("day_position_yin_gui", "")
            day_position_yin_gui_desc = data.get("day_position_yin_gui_desc", "")
            day_position_fu = data.get("day_position_fu", "")
            day_position_fu_desc = data.get("day_position_fu_desc", "")
            day_position_cai = data.get("day_position_cai", "")
            day_position_cai_desc = data.get("day_position_cai_desc", "")
            day_chong_desc = data.get("day_chong_desc", "")
            day_sha = data.get("day_sha", "")
            gong = data.get("gong", "")
            shou = data.get("shou", "")
        
            # 创建弹窗
            popup = tk.Toplevel(self.root)
            popup.geometry("600x1000")
            popup.title(f"农历详细信息 - {date_str}")
            
            # 应用深色主题样式（但保留系统标准标题栏）
            self.configure_popup_style(popup)
            
            # 主框架
            main_frame = ttk.Frame(popup, padding=15, style='Dark.TFrame')
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 创建滚动框架
            canvas = tk.Canvas(main_frame, bg='black', highlightthickness=0)
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview, style='Dark.Vertical.TScrollbar')
            scrollable_frame = ttk.Frame(canvas, style='Dark.TFrame')
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # 日期信息区域
            date_frame = ttk.Frame(scrollable_frame, style='Dark.TFrame')
            date_frame.pack(fill=tk.X, pady=(0, 20))
            
            # 日期标题
            date_title = ttk.Label(date_frame, text="📅 日期信息", 
                                 font=("SimSun", 16, "bold"), foreground="#FFD700", style='Dark.TLabel')
            date_title.pack(anchor=tk.W, pady=(0, 10))
            
            # 日期信息网格
            date_info_frame = ttk.Frame(date_frame, style='Dark.TFrame')
            date_info_frame.pack(fill=tk.X)
            
            # 公历日期
            ttk.Label(date_info_frame, text="公历:", font=("SimSun", 12, "bold"), 
                     foreground="#87CEEB", style='Dark.TLabel').grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
            ttk.Label(date_info_frame, text=date_str, font=("SimSun", 12), 
                     style='Dark.TLabel').grid(row=0, column=1, sticky=tk.W, pady=5)
            
            # 农历日期 - 分解显示
            ttk.Label(date_info_frame, text="农历:", font=("SimSun", 12, "bold"), 
                     foreground="#FFB6C1", style='Dark.TLabel').grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
            
            # 解析农历信息
            lunar_parts = self.parse_lunar_info(lunar_info)
            
            # 农历详细信息框架
            lunar_detail_frame = ttk.Frame(date_info_frame, style='Dark.TFrame')
            lunar_detail_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
            
            # 显示农历年月日
            if lunar_parts.get('year'):
                ttk.Label(lunar_detail_frame, text=f"年: {lunar_parts['year']}", 
                         font=("SimSun", 11), foreground="#FFB6C1", style='Dark.TLabel').pack(anchor=tk.W, pady=1)
            
            if lunar_parts.get('month'):
                ttk.Label(lunar_detail_frame, text=f"月: {lunar_parts['month']}", 
                         font=("SimSun", 11), foreground="#FFB6C1", style='Dark.TLabel').pack(anchor=tk.W, pady=1)
            
            if lunar_parts.get('day'):
                ttk.Label(lunar_detail_frame, text=f"日: {lunar_parts['day']}", 
                         font=("SimSun", 11), foreground="#FFB6C1", style='Dark.TLabel').pack(anchor=tk.W, pady=1)
            
            if lunar_parts.get('hour'):
                ttk.Label(lunar_detail_frame, text=f"时: {lunar_parts['hour']}", 
                         font=("SimSun", 11), foreground="#FFB6C1", style='Dark.TLabel').pack(anchor=tk.W, pady=1)
            
            # 天干地支信息
            if lunar_parts.get('gan_zhi'):
                ttk.Label(lunar_detail_frame, text=f"天干地支: {lunar_parts['gan_zhi']}", 
                         font=("SimSun", 11), foreground="#DDA0DD", style='Dark.TLabel').pack(anchor=tk.W, pady=1)
            
            # 纳音信息
            if lunar_parts.get('na_yin'):
                ttk.Label(lunar_detail_frame, text=f"纳音: {lunar_parts['na_yin']}", 
                         font=("SimSun", 11), foreground="#98FB98", style='Dark.TLabel').pack(anchor=tk.W, pady=1)
            
            # 星期信息
            if lunar_parts.get('weekday'):
                ttk.Label(lunar_detail_frame, text=f"星期: {lunar_parts['weekday']}", 
                         font=("SimSun", 11), foreground="#F0E68C", style='Dark.TLabel').pack(anchor=tk.W, pady=1)
            
            # 如果解析失败，显示原始信息
            if lunar_parts.get('raw'):
                ttk.Label(lunar_detail_frame, text="原始信息:", 
                         font=("SimSun", 11, "bold"), foreground="#FFA500", style='Dark.TLabel').pack(anchor=tk.W, pady=(5, 1))
                ttk.Label(lunar_detail_frame, text=lunar_parts['raw'], 
                         font=("SimSun", 10), foreground="#FFA500", style='Dark.TLabel').pack(anchor=tk.W, pady=1)
            
            # 生肖星宿区域
            animal_frame = ttk.Frame(scrollable_frame, style='Dark.TFrame')
            animal_frame.pack(fill=tk.X, pady=(0, 20))
            
            # 生肖星宿标题
            animal_title = ttk.Label(animal_frame, text="🐾 生肖星宿", 
                                   font=("SimSun", 16, "bold"), foreground="#32CD32", style='Dark.TLabel')
            animal_title.pack(anchor=tk.W, pady=(0, 10))
            
            # 生肖星宿信息网格
            animal_info_frame = ttk.Frame(animal_frame, style='Dark.TFrame')
            animal_info_frame.pack(fill=tk.X)
            
            # 生肖
            ttk.Label(animal_info_frame, text="生肖:", font=("SimSun", 12, "bold"), 
                     foreground="#FFD700", style='Dark.TLabel').grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
            ttk.Label(animal_info_frame, text=animal, font=("SimSun", 12), 
                     style='Dark.TLabel').grid(row=0, column=1, sticky=tk.W, pady=5)
            
            # 星宿
            ttk.Label(animal_info_frame, text="星宿:", font=("SimSun", 12, "bold"), 
                     foreground="#9370DB", style='Dark.TLabel').grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
            ttk.Label(animal_info_frame, text=xiu, font=("SimSun", 12), 
                     style='Dark.TLabel').grid(row=1, column=1, sticky=tk.W, pady=5)
            
            # 值神（如果有）
            if zheng:
                ttk.Label(animal_info_frame, text="值神:", font=("SimSun", 12, "bold"), 
                         foreground="#FF6347", style='Dark.TLabel').grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=5)
                ttk.Label(animal_info_frame, text=zheng, font=("SimSun", 12), 
                         style='Dark.TLabel').grid(row=2, column=1, sticky=tk.W, pady=5)
            
            # 四象信息
            if gong and shou:
                ttk.Label(animal_info_frame, text="四象:", font=("SimSun", 12, "bold"), 
                         foreground="#4169E1", style='Dark.TLabel').grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=5)
                ttk.Label(animal_info_frame, text=f"{gong}方{shou}", font=("SimSun", 12), 
                         style='Dark.TLabel').grid(row=3, column=1, sticky=tk.W, pady=5)
            
            # 星宿详细信息
            if xiu_luck:
                ttk.Label(animal_info_frame, text="星宿详情:", font=("SimSun", 12, "bold"), 
                         foreground="#9370DB", style='Dark.TLabel').grid(row=4, column=0, sticky=tk.W, padx=(0, 10), pady=5)
                ttk.Label(animal_info_frame, text=f"{xiu}{zheng}{animal}({xiu_luck})", font=("SimSun", 12), 
                         style='Dark.TLabel').grid(row=4, column=1, sticky=tk.W, pady=5)
            
            # 彭祖百忌区域
            if peng_zu_gan and peng_zu_zhi:
                peng_zu_frame = ttk.Frame(scrollable_frame, style='Dark.TFrame')
                peng_zu_frame.pack(fill=tk.X, pady=(0, 20))
                
                # 彭祖百忌标题
                peng_zu_title = ttk.Label(peng_zu_frame, text="📜 彭祖百忌", 
                                        font=("SimSun", 16, "bold"), foreground="#FF8C00", style='Dark.TLabel')
                peng_zu_title.pack(anchor=tk.W, pady=(0, 10))
                
                # 彭祖百忌内容
                peng_zu_content_frame = ttk.Frame(peng_zu_frame, style='Dark.TFrame')
                peng_zu_content_frame.pack(fill=tk.X, padx=(20, 0))
                
                ttk.Label(peng_zu_content_frame, text=f"{peng_zu_gan} {peng_zu_zhi}", font=("SimSun", 11), 
                         foreground="#FFA500", style='Dark.TLabel').pack(anchor=tk.W, pady=2)
            
            # 方位信息区域
            if day_position_xi or day_position_yang_gui or day_position_yin_gui or day_position_fu or day_position_cai:
                direction_frame = ttk.Frame(scrollable_frame, style='Dark.TFrame')
                direction_frame.pack(fill=tk.X, pady=(0, 20))
                
                # 方位信息标题
                direction_title = ttk.Label(direction_frame, text="🧭 方位信息", 
                                          font=("SimSun", 16, "bold"), foreground="#00CED1", style='Dark.TLabel')
                direction_title.pack(anchor=tk.W, pady=(0, 10))
                
                # 方位信息网格
                direction_info_frame = ttk.Frame(direction_frame, style='Dark.TFrame')
                direction_info_frame.pack(fill=tk.X)
                
                row = 0
                if day_position_xi:
                    ttk.Label(direction_info_frame, text="喜神:", font=("SimSun", 11, "bold"), 
                             foreground="#FF69B4", style='Dark.TLabel').grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=3)
                    ttk.Label(direction_info_frame, text=f"{day_position_xi}({day_position_xi_desc})", font=("SimSun", 11), 
                             style='Dark.TLabel').grid(row=row, column=1, sticky=tk.W, pady=3)
                    row += 1
                
                if day_position_yang_gui:
                    ttk.Label(direction_info_frame, text="阳贵神:", font=("SimSun", 11, "bold"), 
                             foreground="#FFD700", style='Dark.TLabel').grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=3)
                    ttk.Label(direction_info_frame, text=f"{day_position_yang_gui}({day_position_yang_gui_desc})", font=("SimSun", 11), 
                             style='Dark.TLabel').grid(row=row, column=1, sticky=tk.W, pady=3)
                    row += 1
                
                if day_position_yin_gui:
                    ttk.Label(direction_info_frame, text="阴贵神:", font=("SimSun", 11, "bold"), 
                             foreground="#9370DB", style='Dark.TLabel').grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=3)
                    ttk.Label(direction_info_frame, text=f"{day_position_yin_gui}({day_position_yin_gui_desc})", font=("SimSun", 11), 
                             style='Dark.TLabel').grid(row=row, column=1, sticky=tk.W, pady=3)
                    row += 1
                
                if day_position_fu:
                    ttk.Label(direction_info_frame, text="福神:", font=("SimSun", 11, "bold"), 
                             foreground="#32CD32", style='Dark.TLabel').grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=3)
                    ttk.Label(direction_info_frame, text=f"{day_position_fu}({day_position_fu_desc})", font=("SimSun", 11), 
                             style='Dark.TLabel').grid(row=row, column=1, sticky=tk.W, pady=3)
                    row += 1
                
                if day_position_cai:
                    ttk.Label(direction_info_frame, text="财神:", font=("SimSun", 11, "bold"), 
                             foreground="#FF6347", style='Dark.TLabel').grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=3)
                    ttk.Label(direction_info_frame, text=f"{day_position_cai}({day_position_cai_desc})", font=("SimSun", 11), 
                             style='Dark.TLabel').grid(row=row, column=1, sticky=tk.W, pady=3)
                    row += 1
                
                # 冲煞信息
                if day_chong_desc or day_sha:
                    if day_chong_desc:
                        ttk.Label(direction_info_frame, text="冲:", font=("SimSun", 11, "bold"), 
                                 foreground="#FF4500", style='Dark.TLabel').grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=3)
                        ttk.Label(direction_info_frame, text=day_chong_desc, font=("SimSun", 11), 
                                 style='Dark.TLabel').grid(row=row, column=1, sticky=tk.W, pady=3)
                        row += 1
                    
                    if day_sha:
                        ttk.Label(direction_info_frame, text="煞:", font=("SimSun", 11, "bold"), 
                                 foreground="#DC143C", style='Dark.TLabel').grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=3)
                        ttk.Label(direction_info_frame, text=day_sha, font=("SimSun", 11), 
                                 style='Dark.TLabel').grid(row=row, column=1, sticky=tk.W, pady=3)
            
            # 宜忌区域
            yi_ji_frame = ttk.Frame(scrollable_frame, style='Dark.TFrame')
            yi_ji_frame.pack(fill=tk.X, pady=(0, 20))
            
            # 宜忌标题
            yi_ji_title = ttk.Label(yi_ji_frame, text="📋 今日宜忌", 
                                  font=("SimSun", 16, "bold"), foreground="#FF6B6B", style='Dark.TLabel')
            yi_ji_title.pack(anchor=tk.W, pady=(0, 10))
            
            # 宜忌内容框架
            yi_ji_content_frame = ttk.Frame(yi_ji_frame, style='Dark.TFrame')
            yi_ji_content_frame.pack(fill=tk.X)
            
            # 宜事项
            yi_frame = ttk.Frame(yi_ji_content_frame, style='Dark.TFrame')
            yi_frame.pack(fill=tk.X, pady=(0, 15))
            
            yi_label = ttk.Label(yi_frame, text="✅ 宜:", font=("SimSun", 14, "bold"), 
                               foreground="#32CD32", style='Dark.TLabel')
            yi_label.pack(anchor=tk.W, pady=(0, 5))
            
            # 宜事项内容
            yi_content_frame = ttk.Frame(yi_frame, style='Dark.TFrame')
            yi_content_frame.pack(fill=tk.X, padx=(20, 0))
            
            if yi_ji and 'yi' in yi_ji:
                yi_items = yi_ji['yi']
                if isinstance(yi_items, list):
                    if yi_items:
                        for i, item in enumerate(yi_items):
                            item_label = ttk.Label(yi_content_frame, text=f"• {item}", 
                                                font=("SimSun", 11), foreground="#90EE90", style='Dark.TLabel')
                            item_label.pack(anchor=tk.W, pady=2)
                    else:
                        ttk.Label(yi_content_frame, text="无", font=("SimSun", 11), 
                                foreground="#666666", style='Dark.TLabel').pack(anchor=tk.W, pady=2)
                elif yi_items:  # 如果是非空字符串
                    ttk.Label(yi_content_frame, text=f"• {yi_items}", font=("SimSun", 11), 
                            foreground="#90EE90", style='Dark.TLabel').pack(anchor=tk.W, pady=2)
                else:
                    ttk.Label(yi_content_frame, text="无", font=("SimSun", 11), 
                            foreground="#666666", style='Dark.TLabel').pack(anchor=tk.W, pady=2)
            else:
                ttk.Label(yi_content_frame, text="无", font=("SimSun", 11), 
                        foreground="#666666", style='Dark.TLabel').pack(anchor=tk.W, pady=2)
            
            # 忌事项
            ji_frame = ttk.Frame(yi_ji_content_frame, style='Dark.TFrame')
            ji_frame.pack(fill=tk.X)
            
            ji_label = ttk.Label(ji_frame, text="❌ 忌:", font=("SimSun", 14, "bold"), 
                               foreground="#FF6347", style='Dark.TLabel')
            ji_label.pack(anchor=tk.W, pady=(0, 5))
            
            # 忌事项内容
            ji_content_frame = ttk.Frame(ji_frame, style='Dark.TFrame')
            ji_content_frame.pack(fill=tk.X, padx=(20, 0))
            
            if yi_ji and 'ji' in yi_ji:
                ji_items = yi_ji['ji']
                if isinstance(ji_items, list):
                    if ji_items:
                        for i, item in enumerate(ji_items):
                            item_label = ttk.Label(ji_content_frame, text=f"• {item}", 
                                                font=("SimSun", 11), foreground="#FFB6C1", style='Dark.TLabel')
                            item_label.pack(anchor=tk.W, pady=2)
                    else:
                        ttk.Label(ji_content_frame, text="无", font=("SimSun", 11), 
                                foreground="#666666", style='Dark.TLabel').pack(anchor=tk.W, pady=2)
                elif ji_items:  # 如果是非空字符串
                    ttk.Label(ji_content_frame, text=f"• {ji_items}", font=("SimSun", 11), 
                            foreground="#FFB6C1", style='Dark.TLabel').pack(anchor=tk.W, pady=2)
                else:
                    ttk.Label(ji_content_frame, text="无", font=("SimSun", 11), 
                            foreground="#666666", style='Dark.TLabel').pack(anchor=tk.W, pady=2)
            else:
                ttk.Label(ji_content_frame, text="无", font=("SimSun", 11), 
                        foreground="#666666", style='Dark.TLabel').pack(anchor=tk.W, pady=2)
            
            # 布局滚动区域
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 绑定鼠标滚轮事件
            def _on_mousewheel(event):
                try:
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                except tk.TclError:
                    # canvas可能已被销毁，忽略错误
                    pass
            
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
            # 生成完整文本用于复制
            lunar_text = self.generate_lunar_info_text(
                date_str, lunar_info, animal, xiu, zheng, xiu_luck,
                peng_zu_gan, peng_zu_zhi, day_position_xi, day_position_xi_desc,
                day_position_yang_gui, day_position_yang_gui_desc,
                day_position_yin_gui, day_position_yin_gui_desc,
                day_position_fu, day_position_fu_desc,
                day_position_cai, day_position_cai_desc,
                day_chong_desc, day_sha, gong, shou, yi_ji
            )
            
            # 按钮区域
            button_frame = ttk.Frame(popup, style='Dark.TFrame')
            button_frame.pack(fill=tk.X, pady=10)
            
            def copy_lunar_info():
                if self.copy_lunar_info_to_clipboard(lunar_text):
                    messagebox.showinfo("成功", "农历信息已复制到剪贴板！")
                else:
                    messagebox.showerror("错误", "复制失败，请手动复制。")
            
            ttk.Button(button_frame, text="复制信息", command=copy_lunar_info, 
                      style='Dark.TButton').pack(side=tk.LEFT, padx=10)
            
            ttk.Button(button_frame, text="关闭", command=popup.destroy, 
                      style='Dark.TButton').pack(side=tk.RIGHT, padx=10)
            
            # 解绑鼠标滚轮事件
            def on_popup_close():
                canvas.unbind_all("<MouseWheel>")
                popup.destroy()
            
            popup.protocol("WM_DELETE_WINDOW", on_popup_close)
            
        except Exception as e:
            messagebox.showerror("错误", f"获取农历信息失败: {e}")
    
    def parse_lunar_info(self, lunar_info):
        """解析农历信息字符串，提取各个部分"""
        parts = {}
        
        try:
            # 示例格式: "二○二五年闰六月初七 乙巳(蛇)年 癸未(羊)月 辛丑(牛)日子(鼠)时 纳音[覆灯火 杨柳木 壁上土 霹雳火] 星期四"
            
            # 分割信息
            info_parts = lunar_info.split()
            
            # 先处理纳音信息（因为它可能包含空格）
            na_yin_start = lunar_info.find('纳音[')
            if na_yin_start != -1:
                na_yin_end = lunar_info.find(']', na_yin_start)
                if na_yin_end != -1:
                    na_yin_text = lunar_info[na_yin_start:na_yin_end+1]
                    parts['na_yin'] = na_yin_text
            
            for part in info_parts:
                # 提取年月日（不含天干地支的）
                if '年' in part and '(' not in part and '纳音' not in part and '星期' not in part:
                    parts['year'] = part
                elif '月' in part and '(' not in part and '纳音' not in part and '星期' not in part:
                    parts['month'] = part
                elif '日' in part and '(' not in part and '纳音' not in part and '星期' not in part:
                    parts['day'] = part
                elif '时' in part and '(' not in part and '纳音' not in part and '星期' not in part:
                    parts['hour'] = part
                
                # 提取天干地支信息
                elif '(' in part and ')' in part:
                    if '年' in part:
                        parts['year_gan_zhi'] = part
                    elif '月' in part:
                        parts['month_gan_zhi'] = part
                    elif '日' in part:
                        parts['day_gan_zhi'] = part
                    elif '时' in part:
                        parts['hour_gan_zhi'] = part
                
                # 提取星期信息
                elif '星期' in part:
                    parts['weekday'] = part
            
            # 组合天干地支信息
            gan_zhi_parts = []
            for key in ['year_gan_zhi', 'month_gan_zhi', 'day_gan_zhi', 'hour_gan_zhi']:
                if key in parts:
                    gan_zhi_parts.append(parts[key])
            
            if gan_zhi_parts:
                parts['gan_zhi'] = ' '.join(gan_zhi_parts)
            
            # 如果没有解析到具体信息，返回原始信息
            if not parts:
                parts['raw'] = lunar_info
                
        except Exception as e:
            # 如果解析失败，返回原始信息
            parts['raw'] = lunar_info
            print(f"解析农历信息时出错: {e}")
        
        return parts
    
    def copy_lunar_info_to_clipboard(self, lunar_data):
        """复制农历信息到剪贴板"""
        try:
            import pyperclip
        except ImportError:
            # 如果没有pyperclip，使用tkinter的剪贴板
            self.root.clipboard_clear()
            self.root.clipboard_append(lunar_data)
            self.root.update()
            return True
        
        try:
            pyperclip.copy(lunar_data)
            return True
        except Exception as e:
            print(f"复制到剪贴板失败: {e}")
            return False
    
    def generate_lunar_info_text(self, date_str, lunar_info, animal, xiu, zheng, xiu_luck, 
                                peng_zu_gan, peng_zu_zhi, day_position_xi, day_position_xi_desc,
                                day_position_yang_gui, day_position_yang_gui_desc,
                                day_position_yin_gui, day_position_yin_gui_desc,
                                day_position_fu, day_position_fu_desc,
                                day_position_cai, day_position_cai_desc,
                                day_chong_desc, day_sha, gong, shou, yi_ji):
        """生成完整的农历信息文本"""
        text_lines = []
        
        # 标题
        text_lines.append(f"农历详细信息 - {date_str}")
        text_lines.append("=" * 50)
        
        # 日期信息
        text_lines.append("📅 日期信息")
        text_lines.append(f"公历: {date_str}")
        text_lines.append(f"农历: {lunar_info}")
        text_lines.append("")
        
        # 生肖星宿信息
        text_lines.append("🐾 生肖星宿")
        text_lines.append(f"生肖: {animal}")
        text_lines.append(f"星宿: {xiu}")
        if zheng:
            text_lines.append(f"值神: {zheng}")
        if gong and shou:
            text_lines.append(f"四象: {gong}方{shou}")
        if xiu_luck:
            text_lines.append(f"星宿详情: {xiu}{zheng}{animal}({xiu_luck})")
        text_lines.append("")
        
        # 彭祖百忌
        if peng_zu_gan and peng_zu_zhi:
            text_lines.append("📜 彭祖百忌")
            text_lines.append(f"{peng_zu_gan} {peng_zu_zhi}")
            text_lines.append("")
        
        # 方位信息
        has_direction = any([day_position_xi, day_position_yang_gui, day_position_yin_gui, 
                           day_position_fu, day_position_cai])
        if has_direction:
            text_lines.append("🧭 方位信息")
            if day_position_xi:
                text_lines.append(f"喜神: {day_position_xi}({day_position_xi_desc})")
            if day_position_yang_gui:
                text_lines.append(f"阳贵神: {day_position_yang_gui}({day_position_yang_gui_desc})")
            if day_position_yin_gui:
                text_lines.append(f"阴贵神: {day_position_yin_gui}({day_position_yin_gui_desc})")
            if day_position_fu:
                text_lines.append(f"福神: {day_position_fu}({day_position_fu_desc})")
            if day_position_cai:
                text_lines.append(f"财神: {day_position_cai}({day_position_cai_desc})")
            if day_chong_desc:
                text_lines.append(f"冲: {day_chong_desc}")
            if day_sha:
                text_lines.append(f"煞: {day_sha}")
            text_lines.append("")
        
        # 宜忌信息
        text_lines.append("📋 今日宜忌")
        text_lines.append("✅ 宜:")
        if yi_ji and 'yi' in yi_ji:
            yi_items = yi_ji['yi']
            if isinstance(yi_items, list):
                if yi_items:
                    for item in yi_items:
                        text_lines.append(f"  • {item}")
                else:
                    text_lines.append("  无")
            elif yi_items:
                text_lines.append(f"  • {yi_items}")
            else:
                text_lines.append("  无")
        else:
            text_lines.append("  无")
        
        text_lines.append("❌ 忌:")
        if yi_ji and 'ji' in yi_ji:
            ji_items = yi_ji['ji']
            if isinstance(ji_items, list):
                if ji_items:
                    for item in ji_items:
                        text_lines.append(f"  • {item}")
                else:
                    text_lines.append("  无")
            elif ji_items:
                text_lines.append(f"  • {ji_items}")
            else:
                text_lines.append("  无")
        else:
            text_lines.append("  无")
        
        return "\n".join(text_lines)

    def show_tag_popup(self, day, color=None, tree_view=None):
        """显示标签弹窗"""
        date_str = f"{self.selected_year}-{self.selected_month:02d}-{day:02d}"
        self.selected_day = day
        
        # 获取标签内容
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT tag, color FROM tags WHERE date = ?", (date_str,))
        result = cursor.fetchone()
        
        # 检查reminders表中是否有repeat_type和repeat_value列
        cursor.execute("PRAGMA table_info(reminders)")
        columns = [column[1] for column in cursor.fetchall()]
        has_repeat_columns = 'repeat_type' in columns and 'repeat_value' in columns
        
        # 获取提醒信息，根据列是否存在构建不同的查询
        if has_repeat_columns:
            cursor.execute("SELECT time, message, repeat_type, repeat_value FROM reminders WHERE date = ? AND is_active = 1", (date_str,))
            reminder_result = cursor.fetchone()
        else:
            cursor.execute("SELECT time, message FROM reminders WHERE date = ? AND is_active = 1", (date_str,))
            # 如果查询结果不为空，添加默认的repeat_type和repeat_value值
            reminder_temp = cursor.fetchone()
            if reminder_temp:
                reminder_result = reminder_temp + ('none', None)
            else:
                reminder_result = None
        
        conn.close()
        
        if result:
            tag_text = result[0]
            tag_color = result[1]
            
            # 创建弹窗
            popup = tk.Toplevel(self.root)
            popup.geometry("500x450")  # 增加窗口大小以适应更多控件
            popup.title(f"标签 - {date_str}")
            
            # 应用深色主题样式（但保留系统标准标题栏）
            self.configure_popup_style(popup)
            
            # 标签内容显示
            content_frame = ttk.Frame(popup, padding=10, style='Dark.TFrame')
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(content_frame, text="日期:", style='Dark.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
            ttk.Label(content_frame, text=date_str, style='Dark.TLabel').grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            
            ttk.Label(content_frame, text="标签内容:", style='Dark.TLabel').grid(row=1, column=0, sticky=tk.NW, padx=5, pady=5)
            
            # 使用Text控件替代Entry，支持多行文本
            tag_text_frame = ttk.Frame(content_frame)
            tag_text_frame.grid(row=1, column=1, sticky=tk.NSEW, padx=5, pady=5)
            content_frame.grid_columnconfigure(1, weight=1)
            content_frame.grid_rowconfigure(1, weight=1)
            
            tag_text_widget = tk.Text(tag_text_frame, width=30, height=5, wrap=tk.WORD, bg='#222222', fg='white', insertbackground='white')
            tag_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            tag_text_widget.insert(tk.END, tag_text)
            
            # 添加滚动条
            text_scrollbar = ttk.Scrollbar(tag_text_frame, orient="vertical", command=tag_text_widget.yview, style='Dark.Vertical.TScrollbar')
            text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            tag_text_widget.configure(yscrollcommand=text_scrollbar.set)
            
            # 颜色选择
            ttk.Label(content_frame, text="颜色:", style='Dark.TLabel').grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
            color_var = tk.StringVar()
            
            # 如果存在对应的中文名称，则显示中文名称
            if tag_color in self.reverse_color_map:
                color_var.set(self.reverse_color_map[tag_color])
            else:
                color_var.set(tag_color)
            
            # 创建颜色选择框架
            color_frame = ttk.Frame(content_frame, style='Dark.TFrame')
            color_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
            
            # 创建颜色圆点按钮
            color_buttons = {}
            for i, (color_name, color_hex) in enumerate(self.color_map.items()):
                # 创建颜色圆点按钮
                color_btn = tk.Button(color_frame, width=3, height=1, bg=color_hex, 
                                    relief="flat", bd=0, cursor="hand2")
                color_btn.pack(side=tk.LEFT, padx=2)
                
                # 绑定点击事件
                def make_color_selector(color_name=color_name, color_hex=color_hex):
                    def select_color():
                        color_var.set(color_name)
                        # 更新所有按钮的边框
                        for btn in color_buttons.values():
                            btn.configure(relief="flat", bd=0)
                        # 高亮选中的按钮
                        color_buttons[color_name].configure(relief="solid", bd=2)
                    return select_color
                
                color_btn.configure(command=make_color_selector())
                color_buttons[color_name] = color_btn
                
                # 如果是当前选中的颜色，高亮显示
                if color_var.get() == color_name:
                    color_btn.configure(relief="solid", bd=2)
            
            # 提醒设置区域
            ttk.Label(content_frame, text="设置提醒:", style='Dark.TLabel').grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
            reminder_frame = ttk.Frame(content_frame, style='Dark.TFrame')
            reminder_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
            
            reminder_var = tk.BooleanVar(value=bool(reminder_result))
            reminder_check = ttk.Checkbutton(reminder_frame, text="启用提醒", variable=reminder_var)
            reminder_check.pack(side=tk.LEFT, padx=5)
            
            ttk.Label(reminder_frame, text="时间:").pack(side=tk.LEFT, padx=5)
            time_var = tk.StringVar(value=reminder_result[0] if reminder_result else "08:00")
            time_entry = ttk.Entry(reminder_frame, textvariable=time_var, width=8)
            time_entry.pack(side=tk.LEFT, padx=5)
            
            # 重复类型设置
            ttk.Label(content_frame, text="重复类型:", style='Dark.TLabel').grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
            repeat_frame = ttk.Frame(content_frame, style='Dark.TFrame')
            repeat_frame.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
            
            # 重复类型选项
            repeat_types = ["不重复", "每天", "每周", "每月", "每年(公历)", "每年(农历)"]
            repeat_type_var = tk.StringVar()
            
            # 设置默认值
            if reminder_result and reminder_result[2]:
                repeat_type_map = {
                    "none": "不重复",
                    "daily": "每天",
                    "weekly": "每周",
                    "monthly": "每月",
                    "yearly": "每年(公历)",
                    "lunar_yearly": "每年(农历)"
                }
                repeat_type_var.set(repeat_type_map.get(reminder_result[2], "不重复"))
            else:
                repeat_type_var.set("不重复")
            
            repeat_type_combo = ttk.Combobox(repeat_frame, textvariable=repeat_type_var, 
                                          values=repeat_types, width=12, state="readonly")
            repeat_type_combo.pack(side=tk.LEFT, padx=5)
            
            # 重复值设置框架
            repeat_value_frame = ttk.Frame(content_frame, style='Dark.TFrame')
            repeat_value_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
            
            # 重复值变量
            repeat_value_var = tk.StringVar()
            if reminder_result and reminder_result[3]:
                repeat_value_var.set(reminder_result[3])
            
            # 重复值标签和控件
            repeat_value_label = ttk.Label(repeat_value_frame, text="", style='Dark.TLabel')
            repeat_value_label.pack(side=tk.LEFT, padx=5)
            
            # 创建不同类型的重复值控件
            weekday_frame = ttk.Frame(repeat_value_frame, style='Dark.TFrame')
            weekday_var = tk.StringVar(value="1")
            weekday_values = [("周一", "1"), ("周二", "2"), ("周三", "3"), 
                            ("周四", "4"), ("周五", "5"), ("周六", "6"), ("周日", "0")]
            weekday_combo = ttk.Combobox(weekday_frame, textvariable=weekday_var, 
                                      values=[day[0] for day in weekday_values], width=8, state="readonly")
            weekday_combo.pack(side=tk.LEFT, padx=5)
            
            monthday_frame = ttk.Frame(repeat_value_frame, style='Dark.TFrame')
            monthday_var = tk.StringVar(value="1")
            monthday_values = [str(i) for i in range(1, 32)]
            monthday_combo = ttk.Combobox(monthday_frame, textvariable=monthday_var, 
                                       values=monthday_values, width=8, state="readonly")
            monthday_combo.pack(side=tk.LEFT, padx=5)
            
            # 初始化重复值控件
            def update_repeat_value_ui(*args):
                # 隐藏所有重复值控件
                weekday_frame.pack_forget()
                monthday_frame.pack_forget()
                
                repeat_type = repeat_type_var.get()
                if repeat_type == "每天":
                    repeat_value_label.config(text="每天重复")
                elif repeat_type == "每周":
                    repeat_value_label.config(text="选择星期几:")
                    weekday_frame.pack(side=tk.LEFT)
                    # 如果有已保存的值，设置为已保存的值
                    if reminder_result and reminder_result[2] == "weekly" and reminder_result[3]:
                        for day_name, day_value in weekday_values:
                            if day_value == reminder_result[3]:
                                weekday_var.set(day_name)
                                break
                elif repeat_type == "每月":
                    repeat_value_label.config(text="选择日期:")
                    monthday_frame.pack(side=tk.LEFT)
                    # 如果有已保存的值，设置为已保存的值
                    if reminder_result and reminder_result[2] == "monthly" and reminder_result[3]:
                        monthday_var.set(reminder_result[3])
                else:
                    repeat_value_label.config(text="")
            
            # 绑定重复类型变化事件
            repeat_type_var.trace("w", update_repeat_value_ui)
            
            # 初始化UI
            update_repeat_value_ui()
            
            # 按钮区域
            button_frame = ttk.Frame(content_frame, style='Dark.TFrame')
            button_frame.grid(row=6, column=0, columnspan=2, pady=10)
            
            def save_with_repeat():
                # 获取重复类型和值
                repeat_type = repeat_type_var.get()
                repeat_value = None
                
                # 重复类型映射
                repeat_type_map = {
                    "不重复": "none",
                    "每天": "daily",
                    "每周": "weekly",
                    "每月": "monthly",
                    "每年(公历)": "yearly",
                    "每年(农历)": "lunar_yearly"
                }
                
                db_repeat_type = repeat_type_map.get(repeat_type, "none")
                
                # 根据重复类型获取重复值
                if repeat_type == "每天":
                    # 对于每天重复，不需要特定的重复值
                    repeat_value = None
                elif repeat_type == "每周":
                    # 获取选中星期几的值
                    selected_day = weekday_var.get()
                    for day_name, day_value in weekday_values:
                        if day_name == selected_day:
                            repeat_value = day_value
                            break
                elif repeat_type == "每月":
                    repeat_value = monthday_var.get()
                elif repeat_type in ["每年(公历)", "每年(农历)"]:
                    # 对于年重复，使用月-日格式
                    repeat_value = f"{self.selected_month:02d}-{day:02d}"
                
                # 保存标签和提醒
                self.save_tag_and_reminder(popup, date_str, tag_text_widget, color_var.get(), 
                                         reminder_var.get(), time_var.get(), db_repeat_type, repeat_value,
                                         tree_view=tree_view)
            
            ttk.Button(button_frame, text="保存", command=save_with_repeat, style='Dark.TButton').pack(side=tk.LEFT, padx=5)
            
            ttk.Button(button_frame, text="删除", 
                      command=lambda: self.delete_tag_from_popup(popup, date_str, tree_view),
                      style='Dark.TButton').pack(side=tk.LEFT, padx=5)
            
            ttk.Button(button_frame, text="关闭", 
                      command=popup.destroy, style='Dark.TButton').pack(side=tk.LEFT, padx=5)
        else:
            # 如果没有标签，询问是否添加
            self.add_tag_dialog(date_str)
    
    def add_tag_dialog(self, date_str):
        """添加标签对话框"""
        # 解析日期字符串获取日期
        year, month, day = map(int, date_str.split("-"))
        
        # 创建弹窗
        popup = tk.Toplevel(self.root)
        popup.geometry("500x450")  # 增加窗口大小以适应更多控件
        popup.title(f"添加标签 - {date_str}")
        
        # 应用深色主题样式（但保留系统标准标题栏）
        self.configure_popup_style(popup)
        
        # 标签内容显示
        content_frame = ttk.Frame(popup, padding=10, style='Dark.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(content_frame, text="日期:", style='Dark.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Label(content_frame, text=date_str, style='Dark.TLabel').grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(content_frame, text="标签内容:", style='Dark.TLabel').grid(row=1, column=0, sticky=tk.NW, padx=5, pady=5)
        
        # 使用Text控件替代Entry，支持多行文本
        tag_text_frame = ttk.Frame(content_frame, style='Dark.TFrame')
        tag_text_frame.grid(row=1, column=1, sticky=tk.NSEW, padx=5, pady=5)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(1, weight=1)
        
        tag_text_widget = tk.Text(tag_text_frame, width=30, height=5, wrap=tk.WORD, bg='#222222', fg='white', insertbackground='white')
        tag_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        text_scrollbar = ttk.Scrollbar(tag_text_frame, orient="vertical", command=tag_text_widget.yview, style='Dark.Vertical.TScrollbar')
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tag_text_widget.configure(yscrollcommand=text_scrollbar.set)
        
        # 颜色选择
        ttk.Label(content_frame, text="颜色:", style='Dark.TLabel').grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        color_var = tk.StringVar(value="蓝色")
        
        # 创建颜色选择框架
        color_frame = ttk.Frame(content_frame, style='Dark.TFrame')
        color_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 创建颜色圆点按钮
        color_buttons = {}
        for i, (color_name, color_hex) in enumerate(self.color_map.items()):
            # 创建颜色圆点按钮
            color_btn = tk.Button(color_frame, width=3, height=1, bg=color_hex, 
                                relief="flat", bd=0, cursor="hand2")
            color_btn.pack(side=tk.LEFT, padx=2)
            
            # 绑定点击事件
            def make_color_selector(color_name=color_name, color_hex=color_hex):
                def select_color():
                    color_var.set(color_name)
                    # 更新所有按钮的边框
                    for btn in color_buttons.values():
                        btn.configure(relief="flat", bd=0)
                    # 高亮选中的按钮
                    color_buttons[color_name].configure(relief="solid", bd=2)
                return select_color
            
            color_btn.configure(command=make_color_selector())
            color_buttons[color_name] = color_btn
            
            # 如果是当前选中的颜色，高亮显示
            if color_var.get() == color_name:
                color_btn.configure(relief="solid", bd=2)
        
        # 提醒设置区域
        ttk.Label(content_frame, text="设置提醒:", style='Dark.TLabel').grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        reminder_frame = ttk.Frame(content_frame, style='Dark.TFrame')
        reminder_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        reminder_var = tk.BooleanVar(value=False)
        reminder_check = ttk.Checkbutton(reminder_frame, text="启用提醒", variable=reminder_var)
        reminder_check.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(reminder_frame, text="时间:").pack(side=tk.LEFT, padx=5)
        time_var = tk.StringVar(value="08:00")
        time_entry = ttk.Entry(reminder_frame, textvariable=time_var, width=8)
        time_entry.pack(side=tk.LEFT, padx=5)
        
        # 重复类型设置
        ttk.Label(content_frame, text="重复类型:", style='Dark.TLabel').grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        repeat_frame = ttk.Frame(content_frame, style='Dark.TFrame')
        repeat_frame.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 重复类型选项
        repeat_types = ["不重复", "每天", "每周", "每月", "每年(公历)", "每年(农历)"]
        repeat_type_var = tk.StringVar(value="不重复")
        
        repeat_type_combo = ttk.Combobox(repeat_frame, textvariable=repeat_type_var, 
                                      values=repeat_types, width=12, state="readonly")
        repeat_type_combo.pack(side=tk.LEFT, padx=5)
        
        # 重复值设置框架
        repeat_value_frame = ttk.Frame(content_frame, style='Dark.TFrame')
        repeat_value_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # 重复值标签和控件
        repeat_value_label = ttk.Label(repeat_value_frame, text="", style='Dark.TLabel')
        repeat_value_label.pack(side=tk.LEFT, padx=5)
        
        # 创建不同类型的重复值控件
        weekday_frame = ttk.Frame(repeat_value_frame, style='Dark.TFrame')
        weekday_var = tk.StringVar(value="周一")
        weekday_values = [("周一", "1"), ("周二", "2"), ("周三", "3"), 
                        ("周四", "4"), ("周五", "5"), ("周六", "6"), ("周日", "0")]
        weekday_combo = ttk.Combobox(weekday_frame, textvariable=weekday_var, 
                                  values=[day[0] for day in weekday_values], width=8, state="readonly")
        weekday_combo.pack(side=tk.LEFT, padx=5)
        
        monthday_frame = ttk.Frame(repeat_value_frame, style='Dark.TFrame')
        monthday_var = tk.StringVar(value=str(day))
        monthday_values = [str(i) for i in range(1, 32)]
        monthday_combo = ttk.Combobox(monthday_frame, textvariable=monthday_var, 
                                   values=monthday_values, width=8, state="readonly")
        monthday_combo.pack(side=tk.LEFT, padx=5)
        
        # 初始化重复值控件
        def update_repeat_value_ui(*args):
            # 隐藏所有重复值控件
            weekday_frame.pack_forget()
            monthday_frame.pack_forget()
            
            repeat_type = repeat_type_var.get()
            if repeat_type == "每天":
                repeat_value_label.config(text="每天重复")
            elif repeat_type == "每周":
                repeat_value_label.config(text="选择星期几:")
                weekday_frame.pack(side=tk.LEFT)
            elif repeat_type == "每月":
                repeat_value_label.config(text="选择日期:")
                monthday_frame.pack(side=tk.LEFT)
            else:
                repeat_value_label.config(text="")
        
        # 绑定重复类型变化事件
        repeat_type_var.trace("w", update_repeat_value_ui)
        
        # 初始化UI
        update_repeat_value_ui()
        
        # 按钮区域
        button_frame = ttk.Frame(content_frame, style='Dark.TFrame')
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)
        
        def save_with_repeat():
            # 获取重复类型和值
            repeat_type = repeat_type_var.get()
            repeat_value = None
            
            # 重复类型映射
            repeat_type_map = {
                "不重复": "none",
                "每天": "daily",
                "每周": "weekly",
                "每月": "monthly",
                "每年(公历)": "yearly",
                "每年(农历)": "lunar_yearly"
            }
            
            db_repeat_type = repeat_type_map.get(repeat_type, "none")
            
            # 根据重复类型获取重复值
            if repeat_type == "每天":
                # 对于每天重复，不需要特定的重复值
                repeat_value = None
            elif repeat_type == "每周":
                # 获取选中星期几的值
                selected_day = weekday_var.get()
                for day_name, day_value in weekday_values:
                    if day_name == selected_day:
                        repeat_value = day_value
                        break
            elif repeat_type == "每月":
                repeat_value = monthday_var.get()
            elif repeat_type in ["每年(公历)", "每年(农历)"]:
                # 对于年重复，使用月-日格式
                # 从date_str中解析月日
                year, month, day = map(int, date_str.split("-"))
                repeat_value = f"{month:02d}-{day:02d}"
            
            # 保存标签和提醒
            self.save_tag_and_reminder(popup, date_str, tag_text_widget, color_var.get(), 
                                     reminder_var.get(), time_var.get(), db_repeat_type, repeat_value)
        
        ttk.Button(button_frame, text="保存", command=save_with_repeat, style='Dark.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="取消", 
                  command=popup.destroy, style='Dark.TButton').pack(side=tk.LEFT, padx=5)
    
    def save_tag_from_popup(self, popup, date_str, tag_text_widget, color_name):
        """从弹窗保存标签"""
        # 从Text控件获取文本内容
        tag_text = tag_text_widget.get("1.0", tk.END).strip()
        
        # 如果标签内容为空，则不保存
        if not tag_text:
            messagebox.showwarning("警告", "标签内容不能为空！")
            return
        
        # 如果选择的是颜色名称，转换为十六进制代码
        if color_name in self.color_map:
            tag_color = self.color_map[color_name]
        else:
            # 如果直接输入了十六进制代码，则直接使用
            tag_color = color_name
        
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)  # 添加超时设置
            cursor = conn.cursor()
            
            # 检查是否已存在标签
            cursor.execute("SELECT id FROM tags WHERE date = ?", (date_str,))
            result = cursor.fetchone()
            
            if result:
                # 更新现有标签
                cursor.execute("UPDATE tags SET tag = ?, color = ? WHERE date = ?", 
                              (tag_text, tag_color, date_str))
            else:
                # 创建新标签
                cursor.execute("INSERT INTO tags (date, tag, color) VALUES (?, ?, ?)", 
                              (date_str, tag_text, tag_color))
            
            conn.commit()
            
            # 成功保存后再显示消息和销毁窗口
            messagebox.showinfo("成功", "标签已保存！")
            if popup and popup.winfo_exists():
                popup.destroy()
            self.update_calendar()
            
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"保存标签时出错: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
    
    def delete_tag_from_popup(self, popup, date_str, tree_view=None):
        """从弹窗删除标签"""
        if messagebox.askyesno("确认", "确定要删除此标签吗？"):
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)  # 添加超时设置
                cursor = conn.cursor()
                
                # 删除标签和相关提醒
                cursor.execute("DELETE FROM tags WHERE date = ?", (date_str,))
                cursor.execute("DELETE FROM reminders WHERE date = ?", (date_str,))
                
                conn.commit()
                
                messagebox.showinfo("成功", "标签已删除！")
                if popup and popup.winfo_exists():
                    popup.destroy()
                self.update_calendar()
                
                # 如果提供了树视图控件，刷新标签列表
                if tree_view is not None:
                    self.load_all_tags(tree_view)
                
            except sqlite3.Error as e:
                messagebox.showerror("数据库错误", f"删除标签时出错: {e}")
                if conn:
                    conn.rollback()
            finally:
                if conn:
                    conn.close()
    
    def save_tag_and_reminder(self, popup, date_str, tag_text_widget, color_name, has_reminder, reminder_time, repeat_type=None, repeat_value=None, tree_view=None):
        """保存标签和提醒"""
        # 先获取标签内容，防止在保存过程中组件被销毁
        tag_text = tag_text_widget.get("1.0", tk.END).strip()
        
        # 如果启用了提醒，先获取提醒消息
        reminder_message = ""
        if has_reminder:
            # 获取标签内容的前20个字符作为提醒消息
            if len(tag_text) > 20:
                reminder_message = tag_text[:20] + "..."
            else:
                reminder_message = tag_text
        
        # 保存标签
        try:
            self.save_tag_from_popup(popup, date_str, tag_text_widget, color_name)
        except Exception as e:
            messagebox.showerror("错误", f"保存标签时出错: {e}")
            return
        
        # 处理提醒
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)  # 添加超时设置
            cursor = conn.cursor()
            
            # 先删除现有提醒
            cursor.execute("DELETE FROM reminders WHERE date = ?", (date_str,))
            
            # 如果启用了提醒，则添加新提醒
            if has_reminder:
                # 验证时间格式
                try:
                    # 尝试解析时间格式
                    hour, minute = map(int, reminder_time.split(':'))
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError("时间格式不正确")
                    
                    # 如果没有指定重复类型，默认为不重复
                    if repeat_type is None:
                        repeat_type = "none"
                        repeat_value = None
                    
                    # 添加提醒，包含重复类型和值
                    cursor.execute("INSERT INTO reminders (date, time, message, is_active, repeat_type, repeat_value) VALUES (?, ?, ?, 1, ?, ?)", 
                                  (date_str, reminder_time, reminder_message, repeat_type, repeat_value))
                    
                except ValueError:
                    messagebox.showwarning("警告", "提醒时间格式不正确，应为HH:MM格式！")
            
            conn.commit()
            
            # 如果提供了树视图控件，刷新标签列表
            if tree_view is not None:
                self.load_all_tags(tree_view)
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"保存提醒时出错: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
    
    def show_all_tags(self):
        """显示所有标签"""
        # 创建弹窗
        popup = tk.Toplevel(self.root)
        popup.geometry("800x500")
        popup.title("所有标签")
        
        # 应用深色主题样式（但保留系统标准标题栏）
        self.configure_popup_style(popup)
        
        # 创建框架
        main_frame = ttk.Frame(popup, padding=10, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 搜索框架
        search_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        search_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(search_frame, text="搜索:", style='Dark.TLabel').pack(side=tk.LEFT, padx=5)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        # 搜索类型选择
        search_type_var = tk.StringVar(value="内容")
        ttk.Label(search_frame, text="搜索类型:", style='Dark.TLabel').pack(side=tk.LEFT, padx=5)
        search_type_combo = ttk.Combobox(search_frame, textvariable=search_type_var, 
                                      values=["内容", "日期", "颜色"], width=8, state="readonly")
        search_type_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(search_frame, text="搜索", style='Dark.TButton',
                  command=lambda: self.search_tags(tree, search_var.get(), search_type_var.get())
                  ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(search_frame, text="重置", style='Dark.TButton',
                  command=lambda: self.reset_tag_search(tree, search_var)
                  ).pack(side=tk.LEFT, padx=5)
        
        # 创建标签列表
        columns = ("日期", "标签内容", "颜色", "提醒")
        tree = ttk.Treeview(main_frame, columns=columns, show="headings")
        
        # 设置列标题
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        # 设置列宽
        tree.column("标签内容", width=400)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 加载所有标签
        self.load_all_tags(tree)
        
        # 添加双击事件，打开标签编辑
        tree.bind("<Double-1>", lambda e: self.edit_tag_from_list(tree))
        
        # 底部按钮
        button_frame = ttk.Frame(popup, style='Dark.TFrame')
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="关闭", command=popup.destroy, style='Dark.TButton').pack(side=tk.RIGHT, padx=10)
    
    def load_all_tags(self, tree):
        """加载所有标签到树视图"""
        # 清空现有数据
        for item in tree.get_children():
            tree.delete(item)
        
        # 获取所有标签
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查reminders表中是否有repeat_type和repeat_value列
        cursor.execute("PRAGMA table_info(reminders)")
        columns = [column[1] for column in cursor.fetchall()]
        has_repeat_columns = 'repeat_type' in columns and 'repeat_value' in columns
        
        # 根据列是否存在构建不同的SQL查询
        if has_repeat_columns:
            # 获取标签和提醒信息，包括重复类型
            cursor.execute("""
            SELECT t.date, t.tag, t.color, 
                   CASE WHEN r.id IS NULL THEN '无' ELSE r.time END as reminder_time,
                   r.repeat_type, r.repeat_value
            FROM tags t
            LEFT JOIN reminders r ON t.date = r.date AND r.is_active = 1
            ORDER BY t.date DESC
            """)
        else:
            # 如果没有重复列，使用简化的查询
            cursor.execute("""
            SELECT t.date, t.tag, t.color, 
                   CASE WHEN r.id IS NULL THEN '无' ELSE r.time END as reminder_time,
                   'none' as repeat_type, NULL as repeat_value
            FROM tags t
            LEFT JOIN reminders r ON t.date = r.date AND r.is_active = 1
            ORDER BY t.date DESC
            """)
        
        # 重复类型映射
        repeat_type_map = {
            "none": "不重复",
            "daily": "每天",
            "weekly": "每周",
            "monthly": "每月",
            "yearly": "每年(公历)",
            "lunar_yearly": "每年(农历)"
        }
        
        # 填充数据
        for row in cursor.fetchall():
            date_str = row[0]
            tag_text = row[1]
            tag_color = row[2]
            reminder_time = row[3]
            repeat_type = row[4] if row[4] else "none"
            repeat_value = row[5]
            
            # 如果标签内容有多行，只显示第一行
            # 如果第一行内容太长，截断显示
            first_line = tag_text.split('\n')[0] if '\n' in tag_text else tag_text
            if len(first_line) > 50:
                display_text = first_line[:50] + "..."
            else:
                display_text = first_line
            
            # 如果存在对应的中文名称，则显示中文名称
            if tag_color in self.reverse_color_map:
                color_name = self.reverse_color_map[tag_color]
            else:
                color_name = tag_color
            
            # 格式化提醒信息
            reminder_info = "无"
            if reminder_time != "无":
                reminder_info = f"{reminder_time} ({repeat_type_map.get(repeat_type, '不重复')})"
                
                # 添加重复值信息
                if repeat_type == "weekly" and repeat_value:
                    weekday_names = {"0": "周日", "1": "周一", "2": "周二", "3": "周三", 
                                    "4": "周四", "5": "周五", "6": "周六"}
                    reminder_info += f" {weekday_names.get(repeat_value, '')}"
                elif repeat_type == "monthly" and repeat_value:
                    reminder_info += f" {repeat_value}日"
                elif repeat_type in ["yearly", "lunar_yearly"] and repeat_value:
                    try:
                        month, day = repeat_value.split("-")
                        reminder_info += f" {month}月{day}日"
                    except:
                        pass
            
            tree.insert("", tk.END, values=(date_str, display_text, color_name, reminder_info))
        
        conn.close()
    
    def search_tags(self, tree, search_text, search_type):
        """搜索标签"""
        # 清空现有数据
        for item in tree.get_children():
            tree.delete(item)
        
        if not search_text.strip():
            self.load_all_tags(tree)
            return
        
        # 获取所有标签
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查reminders表中是否有repeat_type和repeat_value列
        cursor.execute("PRAGMA table_info(reminders)")
        columns = [column[1] for column in cursor.fetchall()]
        has_repeat_columns = 'repeat_type' in columns and 'repeat_value' in columns
        
        # 根据搜索类型构建查询
        if search_type == "内容":
            if has_repeat_columns:
                query = """
                SELECT t.date, t.tag, t.color, 
                       CASE WHEN r.id IS NULL THEN '无' ELSE r.time END as reminder_time,
                       r.repeat_type, r.repeat_value
                FROM tags t
                LEFT JOIN reminders r ON t.date = r.date AND r.is_active = 1
                WHERE t.tag LIKE ?
                ORDER BY t.date DESC
                """
            else:
                query = """
                SELECT t.date, t.tag, t.color, 
                       CASE WHEN r.id IS NULL THEN '无' ELSE r.time END as reminder_time,
                       'none' as repeat_type, NULL as repeat_value
                FROM tags t
                LEFT JOIN reminders r ON t.date = r.date AND r.is_active = 1
                WHERE t.tag LIKE ?
                ORDER BY t.date DESC
                """
            cursor.execute(query, (f"%{search_text}%",))
        elif search_type == "日期":
            if has_repeat_columns:
                query = """
                SELECT t.date, t.tag, t.color, 
                       CASE WHEN r.id IS NULL THEN '无' ELSE r.time END as reminder_time,
                       r.repeat_type, r.repeat_value
                FROM tags t
                LEFT JOIN reminders r ON t.date = r.date AND r.is_active = 1
                WHERE t.date LIKE ?
                ORDER BY t.date DESC
                """
            else:
                query = """
                SELECT t.date, t.tag, t.color, 
                       CASE WHEN r.id IS NULL THEN '无' ELSE r.time END as reminder_time,
                       'none' as repeat_type, NULL as repeat_value
                FROM tags t
                LEFT JOIN reminders r ON t.date = r.date AND r.is_active = 1
                WHERE t.date LIKE ?
                ORDER BY t.date DESC
                """
            cursor.execute(query, (f"%{search_text}%",))
        elif search_type == "颜色":
            # 先尝试查找颜色名称
            color_code = None
            for name, code in self.color_map.items():
                if search_text.lower() in name.lower():
                    color_code = code
                    break
            
            if not color_code:
                # 如果不是颜色名称，则直接使用输入的颜色代码
                color_code = search_text
            
            if has_repeat_columns:
                query = """
                SELECT t.date, t.tag, t.color, 
                       CASE WHEN r.id IS NULL THEN '无' ELSE r.time END as reminder_time,
                       r.repeat_type, r.repeat_value
                FROM tags t
                LEFT JOIN reminders r ON t.date = r.date AND r.is_active = 1
                WHERE t.color = ?
                ORDER BY t.date DESC
                """
            else:
                query = """
                SELECT t.date, t.tag, t.color, 
                       CASE WHEN r.id IS NULL THEN '无' ELSE r.time END as reminder_time,
                       'none' as repeat_type, NULL as repeat_value
                FROM tags t
                LEFT JOIN reminders r ON t.date = r.date AND r.is_active = 1
                WHERE t.color = ?
                ORDER BY t.date DESC
                """
            cursor.execute(query, (color_code,))
        else:
            # 如果没有找到颜色名称，尝试直接匹配颜色代码
            query = """
            SELECT t.date, t.tag, t.color, 
                   CASE WHEN r.id IS NULL THEN '无' ELSE r.time END as reminder_time
            FROM tags t
            LEFT JOIN reminders r ON t.date = r.date AND r.is_active = 1
            WHERE t.color LIKE ?
            ORDER BY t.date DESC
            """
            cursor.execute(query, (f"%{search_text}%",))
        
        # 填充数据
        for row in cursor.fetchall():
            date_str = row[0]
            tag_text = row[1]
            tag_color = row[2]
            reminder_time = row[3]
            
            # 如果标签内容太长，截断显示
            if len(tag_text) > 50:
                display_text = tag_text[:50] + "..."
            else:
                display_text = tag_text
            
            # 如果存在对应的中文名称，则显示中文名称
            if tag_color in self.reverse_color_map:
                color_name = self.reverse_color_map[tag_color]
            else:
                color_name = tag_color
            
            tree.insert("", tk.END, values=(date_str, display_text, color_name, reminder_time))
        
        conn.close()
    
    def reset_tag_search(self, tree, search_var):
        """重置标签搜索"""
        search_var.set("")
        self.load_all_tags(tree)
    
    def edit_tag_from_list(self, tree):
        """从列表编辑标签"""
        selected_item = tree.selection()
        if not selected_item:
            return
        
        # 获取选中项的值
        values = tree.item(selected_item[0], "values")
        date_str = values[0]
        
        # 解析日期
        year, month, day = map(int, date_str.split("-"))
        
        # 如果不是当前显示的月份，切换到对应月份
        if year != self.selected_year or month != self.selected_month:
            self.selected_year = year
            self.selected_month = month
            self.year_var.set(str(year))
            self.month_var.set(str(month))
            self.update_calendar()
        
        # 显示标签弹窗，并传递树视图控件以便在编辑完成后刷新列表
        self.show_tag_popup(day, tree_view=tree)
    
    def change_year(self):
        """更改年份"""
        try:
            year = int(self.year_var.get())
            if 1900 <= year <= 2100:
                self.selected_year = year
                self.update_calendar()
            else:
                messagebox.showwarning("警告", "年份必须在1900-2100之间！")
                self.year_var.set(str(self.selected_year))
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的年份！")
            self.year_var.set(str(self.selected_year))
    
    def change_month(self):
        """更改月份"""
        try:
            month = int(self.month_var.get())
            if 1 <= month <= 12:
                self.selected_month = month
                self.update_calendar()
            else:
                messagebox.showwarning("警告", "月份必须在1-12之间！")
                self.month_var.set(str(self.selected_month))
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的月份！")
            self.month_var.set(str(self.selected_month))
    
    def prev_year(self):
        """上一年"""
        self.selected_year -= 1
        self.year_var.set(str(self.selected_year))
        self.update_calendar()
    
    def next_year(self):
        """下一年"""
        self.selected_year += 1
        self.year_var.set(str(self.selected_year))
        self.update_calendar()
    
    def prev_month(self):
        """上一月"""
        if self.selected_month == 1:
            self.selected_month = 12
            self.selected_year -= 1
            self.year_var.set(str(self.selected_year))
        else:
            self.selected_month -= 1
        
        self.month_var.set(str(self.selected_month))
        self.update_calendar()
    
    def next_month(self):
        """下一月"""
        if self.selected_month == 12:
            self.selected_month = 1
            self.selected_year += 1
            self.year_var.set(str(self.selected_year))
        else:
            self.selected_month += 1
        
        self.month_var.set(str(self.selected_month))
        self.update_calendar()
    
    def go_to_today(self):
        """返回今天"""
        today = datetime.datetime.now()
        self.selected_year = today.year
        self.selected_month = today.month
        self.selected_day = today.day
        
        self.year_var.set(str(self.selected_year))
        self.month_var.set(str(self.selected_month))
        
        self.update_calendar()
        self.select_day(self.selected_day)
        
    def setup_tray_icon(self):
        """设置系统托盘图标"""
        if not TRAY_AVAILABLE:
            return
            
        # 创建一个简单的图标
        icon_image = self.create_tray_icon()
        
        # 创建托盘菜单
        menu = (
            pystray.MenuItem('显示', self.show_window, default=True),
            pystray.MenuItem('退出', self.quit_app)
        )
        
        # 创建系统托盘图标，并将show_window设为默认动作（双击）
        self.icon = pystray.Icon("calendar_app", icon_image, "日历应用", menu)
        self.icon.default_action = self.show_window
        
        # 在单独的线程中启动图标
        threading.Thread(target=self.icon.run, daemon=True).start()
    
    def create_tray_icon(self, width=64, height=64):
        """创建一个简单的日历图标"""
        # 创建一个白色背景的图像
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        dc = ImageDraw.Draw(image)
        
        # 绘制日历图标
        dc.rectangle(
            [(8, 8), (width-8, height-8)],
            fill=(30, 144, 255)
        )
        
        # 绘制日历顶部
        dc.rectangle(
            [(8, 8), (width-8, 20)],
            fill=(0, 0, 128)
        )
        
        # 绘制当前日期
        day = str(datetime.datetime.now().day)
        text_width = len(day) * 15
        text_x = (width - text_width) // 2 + 5
        dc.text((text_x, 25), day, fill=(255, 255, 255))
        
        return image
    
    def show_window(self, icon=None, item=None):
        """显示主窗口"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def on_close(self):
        """窗口关闭时最小化到托盘"""
        if TRAY_AVAILABLE:
            self.root.withdraw()  # 隐藏窗口而不是关闭
        else:
            self.quit_app()
    
    def quit_app(self, icon=None, item=None):
        """完全退出应用程序"""
        if TRAY_AVAILABLE and hasattr(self, 'icon'):
            self.icon.stop()
        self.root.destroy()
        sys.exit(0)
        
    def test_reminders(self):
        """测试提醒功能（调试用）"""
        print("=== 开始测试提醒功能 ===")
        self.check_reminders()
        print("=== 提醒功能测试完成 ===")
    
    def schedule_reminder_check(self):
        """设置定时检查提醒"""
        # 每分钟检查一次提醒，确保不会错过提醒时间
        self.root.after(60000, self.periodic_reminder_check)  # 60000毫秒 = 1分钟
    
    def periodic_reminder_check(self):
        """定期检查提醒的回调函数"""
        # 检查提醒
        self.check_reminders()
        # 重新安排下一次检查
        self.schedule_reminder_check()
    
    def check_reminders(self):
        """检查今天是否有需要提醒的事项，包括重复提醒"""
        # 获取当前时间
        now = datetime.datetime.now()
        today = now.date()
        today_str = today.strftime("%Y-%m-%d")
        current_time_str = now.strftime("%H:%M")
        
        # 获取今天是星期几 (0-6, 0是星期日)
        weekday = today.weekday()
        # 转换为与我们系统一致的格式 (0是星期日，1-6是星期一到星期六)
        if weekday == 6:
            weekday = 0
        else:
            weekday += 1
        weekday_str = str(weekday)
        
        # 获取今天是几号
        monthday_str = str(today.day)
        
        # 获取今天的月-日
        month_day_str = today.strftime("%m-%d")
        
        # 如果支持农历，获取今天的农历月-日
        lunar_month_day_str = ""
        if LUNAR_AVAILABLE:
            try:
                # 将datetime.date转换为datetime.datetime，提供默认时间
                today_datetime = datetime.datetime(today.year, today.month, today.day)
                solar = Solar.fromDate(today_datetime)
                lunar = Lunar.fromSolar(solar)
                lunar_month = lunar.getMonth()
                lunar_day = lunar.getDay()
                lunar_month_day_str = f"{lunar_month:02d}-{lunar_day:02d}"
            except Exception as e:
                print(f"农历转换错误: {e}")
        
        # 连接数据库查询提醒
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)  # 添加超时设置
            cursor = conn.cursor()
            
            # 查询所有活跃的提醒
            cursor.execute("""
            SELECT id, date, time, message, repeat_type, repeat_value 
            FROM reminders 
            WHERE is_active = 1
            """)
            
            reminders_to_show = []
            
            for row in cursor.fetchall():
                reminder_id, date_str, time_str, message, repeat_type, repeat_value = row
                
                should_remind = False
                date_to_display_in_reminder = date_str # 默认为原始提醒日期

                try:
                    # 将提醒的日期字符串（开始日期）转换为日期对象
                    reminder_start_date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    print(f"提醒ID {reminder_id} 的日期格式无效: {date_str}")
                    continue # 跳过此提醒

                # 提醒的开始日期必须是今天或过去
                if reminder_start_date_obj <= today:
                    if repeat_type == "none":
                        # 一次性提醒必须是今天
                        if date_str == today_str:
                            should_remind = True
                            date_to_display_in_reminder = today_str # 显示今天的日期
                    else: # 对于重复提醒
                        # 检查是否符合重复规则
                        if repeat_type == "daily":
                            should_remind = True
                            print(f"调试: 每天重复提醒 - 应该提醒")
                        elif repeat_type == "weekly" and repeat_value == weekday_str:
                            should_remind = True
                            print(f"调试: 每周重复提醒 - 应该提醒 (星期{weekday_str}, 重复值{repeat_value})")
                        elif repeat_type == "monthly" and repeat_value == monthday_str:
                            should_remind = True
                            print(f"调试: 每月重复提醒 - 应该提醒 (日期{monthday_str}, 重复值{repeat_value})")
                        elif repeat_type == "yearly" and repeat_value == month_day_str:
                            should_remind = True
                            print(f"调试: 每年重复提醒 - 应该提醒 (月日{month_day_str}, 重复值{repeat_value})")
                        elif repeat_type == "lunar_yearly" and LUNAR_AVAILABLE and repeat_value == lunar_month_day_str:
                            should_remind = True
                            print(f"调试: 农历年重复提醒 - 应该提醒 (农历月日{lunar_month_day_str}, 重复值{repeat_value})")
                        else:
                            print(f"调试: 重复提醒不匹配 - 类型:{repeat_type}, 重复值:{repeat_value}, 今天星期:{weekday_str}, 今天日期:{monthday_str}, 今天月日:{month_day_str}")
                        
                        if should_remind:
                            # 对于今天触发的重复提醒，显示今天的日期
                            date_to_display_in_reminder = today_str 
                
                # 检查时间是否到了提醒时间（允许5分钟的误差）
                if should_remind:
                    try:
                        reminder_time_obj = datetime.datetime.strptime(time_str, "%H:%M").time()
                        current_time_obj = now.time()
                        
                        # 计算时间差（分钟）
                        time_diff = abs((reminder_time_obj.hour * 60 + reminder_time_obj.minute) - 
                                      (current_time_obj.hour * 60 + current_time_obj.minute))
                        
                        # 如果时间差在5分钟内，显示提醒
                        if time_diff <= 5:
                            reminders_to_show.append({'id': reminder_id, 'time': time_str, 'message': message, 'date': date_to_display_in_reminder, 'repeat_type': repeat_type})
                    except ValueError:
                        print(f"提醒ID {reminder_id} 的时间格式无效: {time_str}")
                        continue
            
            # 如果有需要提醒的事项，显示提醒
            if reminders_to_show:
                self.show_reminders(reminders_to_show)
                
        except sqlite3.Error as e:
            print(f"检查提醒时出错: {e}")
        finally:
            if conn:
                conn.close()
    
    def show_reminders(self, reminders):
        """显示提醒对话框，并更新一次性提醒的状态"""
        # 创建提醒窗口
        reminder_window = tk.Toplevel(self.root)
        reminder_window.geometry("400x300")
        reminder_window.title("今日提醒")
        
        # 应用深色主题样式（但保留系统标准标题栏）
        self.configure_popup_style(reminder_window)
        
        # 创建提醒列表框架
        frame = ttk.Frame(reminder_window, padding=10, style='Dark.TFrame')
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建标题
        ttk.Label(frame, text="今天的提醒事项", font=("SimSun", 12, "bold"), style='Dark.TLabel').pack(pady=10)
        
        # 创建提醒列表
        reminder_frame = ttk.Frame(frame, style='Dark.TFrame')
        reminder_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(reminder_frame, style='Dark.Vertical.TScrollbar')
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建列表框
        reminder_list = tk.Listbox(reminder_frame, yscrollcommand=scrollbar.set, font=("SimSun", 10),
                                 bg='#222222', fg='white', selectbackground='#4a4a4a', selectforeground='white')
        reminder_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=reminder_list.yview)
        
        # 添加提醒项并处理一次性提醒
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            for reminder in reminders:
                reminder_list.insert(tk.END, f"{reminder['time']} - {reminder['message']} ({reminder['date']})")
                # 如果是一次性提醒，则将其标记为非活动
                if reminder['repeat_type'] == 'none':
                    cursor.execute("UPDATE reminders SET is_active = 0 WHERE id = ?", (reminder['id'],))
            conn.commit()
        except sqlite3.Error as e:
            print(f"更新提醒状态时出错: {e}")
        finally:
            if conn:
                conn.close()
        
        # 添加关闭按钮
        ttk.Button(frame, text="关闭", command=reminder_window.destroy, style='Dark.TButton').pack(pady=10)
        
        # 设置窗口在前台显示
        reminder_window.lift()
        reminder_window.focus_force()
        
        # 播放提示音
        reminder_window.bell()

    def show_llm_dialog(self):
        """显示LLM配置对话框"""
        # 创建弹窗
        popup = tk.Toplevel(self.root)
        popup.geometry("1500x800")  # 增大初始尺寸
        popup.minsize(600, 500)    # 设置最小尺寸
        popup.resizable(True, True)  # 允许调整大小
        popup.title("AI助手配置")
        
        # 应用深色主题样式（但保留系统标准标题栏）
        self.configure_popup_style(popup)
        
        # 主框架
        main_frame = ttk.Frame(popup, padding=15, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建选项卡
        notebook = ttk.Notebook(main_frame, style='Dark.TNotebook')
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 配置管理选项卡
        config_frame = ttk.Frame(notebook, style='Dark.TFrame')
        notebook.add(config_frame, text="配置管理")
        
        # 聊天选项卡
        chat_frame = ttk.Frame(notebook, style='Dark.TFrame')
        notebook.add(chat_frame, text="AI聊天")
        
        # 配置管理界面
        self.create_llm_config_ui(config_frame, popup)
        
        # 聊天界面
        self.create_llm_chat_ui(chat_frame, popup)

        # 添加右下角缩放控件
        resize_handle = tk.Frame(popup, cursor="size_nw_se", bg="#222222", width=16, height=16)
        resize_handle.place(relx=1.0, rely=1.0, anchor="se")

        def start_resize(event):
            resize_handle.start_x = event.x
            resize_handle.start_y = event.y
            resize_handle.start_width = popup.winfo_width()
            resize_handle.start_height = popup.winfo_height()

        def do_resize(event):
            dx = event.x - resize_handle.start_x
            dy = event.y - resize_handle.start_y
            new_width = max(popup.minsize()[0], resize_handle.start_width + dx)
            new_height = max(popup.minsize()[1], resize_handle.start_height + dy)
            popup.geometry(f"{new_width}x{new_height}")

        resize_handle.bind("<Button-1>", start_resize)
        resize_handle.bind("<B1-Motion>", do_resize)
    
    def create_llm_config_ui(self, parent, popup):
        """创建LLM配置管理界面"""
        # 配置列表框架
        list_frame = ttk.Frame(parent, style='Dark.TFrame')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 配置列表标题
        ttk.Label(list_frame, text="AI模型配置", font=("SimSun", 12, "bold"), 
                 style='Dark.TLabel').pack(anchor=tk.W, pady=(0, 10))
        
        # 创建配置列表
        columns = ("名称", "基础URI", "模型名称", "温度", "类型")
        self.config_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=6)
        
        # 设置列标题
        for col in columns:
            self.config_tree.heading(col, text=col)
            self.config_tree.column(col, width=100)
        self.config_tree.column("名称", width=120)
        self.config_tree.column("基础URI", width=150)
        
        # 添加滚动条
        config_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.config_tree.yview)
        self.config_tree.configure(yscrollcommand=config_scrollbar.set)
        
        # 布局
        self.config_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        config_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 加载配置列表
        self.load_llm_configs()
        
        # 配置操作按钮框架
        config_btn_frame = ttk.Frame(parent, style='Dark.TFrame')
        config_btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(config_btn_frame, text="添加配置", command=self.add_llm_config, 
                  style='Dark.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(config_btn_frame, text="编辑配置", command=self.edit_llm_config, 
                  style='Dark.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(config_btn_frame, text="删除配置", command=self.delete_llm_config, 
                  style='Dark.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(config_btn_frame, text="设为默认", command=self.set_default_llm_config, 
                  style='Dark.TButton').pack(side=tk.LEFT, padx=5)
    
    def create_llm_chat_ui(self, parent, popup):
        """创建LLM聊天界面"""
        # 创建左右分栏布局
        chat_paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL, style='Dark.TPanedwindow')
        chat_paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧历史对话面板
        history_frame = ttk.Frame(chat_paned, style='Dark.TFrame')
        chat_paned.add(history_frame, weight=1)
        
        # 历史对话标题和操作按钮
        history_header = ttk.Frame(history_frame, style='Dark.TFrame')
        history_header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(history_header, text="历史对话", font=("SimSun", 12, "bold"), 
                 style='Dark.TLabel').pack(side=tk.LEFT)
        
        # 历史对话操作按钮
        history_btn_frame = ttk.Frame(history_header, style='Dark.TFrame')
        history_btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(history_btn_frame, text="新建", command=self.new_chat_session, 
                  style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(history_btn_frame, text="删除", command=self.delete_selected_sessions, 
                  style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(history_btn_frame, text="清空", command=self.clear_all_sessions, 
                  style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        
        # 历史对话列表
        self.session_tree = ttk.Treeview(history_frame, columns=("时间",), show="tree headings", height=8, selectmode="extended")
        self.session_tree.heading("#0", text="对话标题")
        self.session_tree.heading("时间", text="更新时间")
        self.session_tree.column("#0", width=150)
        self.session_tree.column("时间", width=120)
        
        # 添加滚动条
        session_scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.session_tree.yview)
        self.session_tree.configure(yscrollcommand=session_scrollbar.set)
        
        self.session_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        session_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定双击事件加载对话
        self.session_tree.bind("<Double-1>", self.load_chat_session)
        
        # 绑定右键菜单
        self.session_tree.bind("<Button-3>", self.show_session_context_menu)
        
        # 右侧聊天区域
        chat_area_frame = ttk.Frame(chat_paned, style='Dark.TFrame')
        chat_paned.add(chat_area_frame, weight=3)
        
        # 聊天历史框架
        chat_history_frame = ttk.Frame(chat_area_frame, style='Dark.TFrame')
        chat_history_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 聊天历史标题
        title_frame = ttk.Frame(chat_history_frame, style='Dark.TFrame')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(title_frame, text="AI助手", font=("SimSun", 12, "bold"), 
                 style='Dark.TLabel').pack(side=tk.LEFT)
        

        
        # 聊天历史显示区域
        self.chat_text = tk.Text(chat_history_frame, wrap=tk.WORD, bg='#1a1a1a', fg='white', 
                                insertbackground='white', font=("SimSun", 10))
        chat_scrollbar = ttk.Scrollbar(chat_history_frame, orient="vertical", command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=chat_scrollbar.set)
        
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 输入框架
        input_frame = ttk.Frame(chat_area_frame, style='Dark.TFrame')
        input_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 输入框框架
        input_text_frame = ttk.Frame(input_frame, style='Dark.TFrame')
        input_text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 多行输入框
        self.input_text = tk.Text(input_text_frame, wrap=tk.WORD, bg='#222222', fg='white', 
                                 insertbackground='white', height=6, font=("SimSun", 10))
        input_scrollbar = ttk.Scrollbar(input_text_frame, orient="vertical", command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=input_scrollbar.set)
        
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        button_frame = ttk.Frame(input_frame, style='Dark.TFrame')
        button_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 发送按钮
        ttk.Button(button_frame, text="发送", command=self.send_llm_message, 
                  style='Dark.TButton').pack(pady=(0, 5))
        
        # 清空按钮
        ttk.Button(button_frame, text="清空", command=self.clear_input, 
                  style='Dark.TButton').pack()
        
        # 绑定回车键（换行）和Ctrl+Enter（发送）
        self.input_text.bind("<Return>", self.handle_return_key)
        self.input_text.bind("<Control-Return>", lambda e: self.send_llm_message())
        
        # 初始化聊天
        self.chat_text.insert(tk.END, "AI助手: 您好！我是您的AI助手，有什么可以帮助您的吗？\n\n", "system")
        self.chat_text.configure(state="disabled")
        
        # 聊天标签配置
        self.chat_text.tag_configure("user", background="#2d4a6b", foreground="white", 
                                   font=("SimSun", 10, "bold"))
        self.chat_text.tag_configure("ai", background="#2d6b4a", foreground="white", 
                                   font=("SimSun", 10))
        self.chat_text.tag_configure("system", background="#4a4a4a", foreground="white", 
                                   font=("SimSun", 10, "italic"))
        
        # 初始化变量
        self.current_session_id = None
        self.current_messages = []
        
        # 加载历史对话列表
        self.load_chat_sessions()
    
    def load_llm_configs(self):
        """加载LLM配置列表"""
        # 清空现有数据
        for item in self.config_tree.get_children():
            self.config_tree.delete(item)

        # 从数据库加载配置
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, base_uri, model_name, temperature, is_default FROM llm_configs ORDER BY is_default DESC, name")

        for row in cursor.fetchall():
            name, base_uri, model_name, temperature, is_default = row
            # 如果是默认配置，在名称前添加标记
            display_name = f"★ {name}" if is_default else name
            self.config_tree.insert("", tk.END, values=(display_name, base_uri, model_name, temperature, "标准"))

        conn.close()
    
    def add_llm_config(self):
        """添加LLM配置"""
        # 创建配置对话框
        config_dialog = tk.Toplevel(self.root)
        config_dialog.geometry("500x400")
        config_dialog.title("添加AI模型配置")
        
        # 应用深色主题样式（但保留系统标准标题栏）
        self.configure_popup_style(config_dialog)
        
        # 配置表单框架
        form_frame = ttk.Frame(config_dialog, padding=15, style='Dark.TFrame')
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # 配置名称
        ttk.Label(form_frame, text="配置名称:", style='Dark.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(form_frame, textvariable=name_var, width=40, style='Dark.TEntry')
        name_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 基础URI
        ttk.Label(form_frame, text="基础URI:", style='Dark.TLabel').grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        uri_var = tk.StringVar()
        uri_entry = ttk.Entry(form_frame, textvariable=uri_var, width=40, style='Dark.TEntry')
        uri_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        uri_entry.insert(0, "https://api.hdgsb.com/v1")
        
        # 模型名称
        ttk.Label(form_frame, text="模型名称:", style='Dark.TLabel').grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        model_var = tk.StringVar()
        model_entry = ttk.Entry(form_frame, textvariable=model_var, width=40, style='Dark.TEntry')
        model_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        model_entry.insert(0, "qwen3-coder-480b-a35b-instruct")
        
        # API密钥
        ttk.Label(form_frame, text="API密钥:", style='Dark.TLabel').grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        key_var = tk.StringVar()
        key_entry = ttk.Entry(form_frame, textvariable=key_var, width=40, style='Dark.TEntry', show="*")
        key_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 温度系数
        ttk.Label(form_frame, text="温度系数:", style='Dark.TLabel').grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        temp_var = tk.DoubleVar(value=0.7)
        temp_scale = ttk.Scale(form_frame, from_=0.0, to=2.0, variable=temp_var, orient=tk.HORIZONTAL, style='Dark.Horizontal.TScale')
        temp_scale.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        temp_label = ttk.Label(form_frame, text="0.7", style='Dark.TLabel')
        temp_label.grid(row=4, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 更新温度显示
        def update_temp_label(*args):
            temp_label.config(text=f"{temp_var.get():.1f}")
        temp_var.trace("w", update_temp_label)
        

        
        # 设为默认
        default_var = tk.BooleanVar()
        default_check = ttk.Checkbutton(form_frame, text="设为默认配置", variable=default_var, style='Dark.TCheckbutton')
        default_check.grid(row=7, column=1, sticky=tk.W, padx=5, pady=5)

        # 按钮框架
        button_frame = ttk.Frame(form_frame, style='Dark.TFrame')
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        def save_config():
            name = name_var.get().strip()
            uri = uri_var.get().strip()
            model = model_var.get().strip()
            key = key_var.get().strip()
            temp = temp_var.get()
            is_default = default_var.get()
            
            if not all([name, uri, model, key]):
                messagebox.showwarning("警告", "请填写所有必填字段！")
                return
            
            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                if is_default:
                    # 如果设为默认，先清除其他默认配置
                    cursor.execute("UPDATE llm_configs SET is_default = 0")
                
                cursor.execute("""
                INSERT INTO llm_configs (name, base_uri, model_name, api_key, temperature, is_default)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (name, uri, model, key, temp, 1 if is_default else 0))
                
                conn.commit()
                messagebox.showinfo("成功", "配置已保存！")
                config_dialog.destroy()
                self.load_llm_configs()
                
            except sqlite3.IntegrityError:
                messagebox.showerror("错误", "配置名称已存在！")
            except Exception as e:
                messagebox.showerror("错误", f"保存配置时出错: {e}")
            finally:
                conn.close()
        
        ttk.Button(button_frame, text="保存", command=save_config, style='Dark.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=config_dialog.destroy, style='Dark.TButton').pack(side=tk.LEFT, padx=5)
    
    def edit_llm_config(self):
        """编辑LLM配置"""
        selected_item = self.config_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择一个配置！")
            return
        
        # 获取选中的配置名称（去掉默认标记）
        values = self.config_tree.item(selected_item[0], "values")
        config_name = values[0].replace("★ ", "")
        
        # 从数据库获取配置详情
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT base_uri, model_name, api_key, temperature, is_default FROM llm_configs WHERE name = ?", (config_name,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            messagebox.showerror("错误", "配置不存在！")
            return
        
        base_uri, model_name, api_key, temperature, is_default = result
        
        # 创建编辑对话框
        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.geometry("500x400")
        edit_dialog.title(f"编辑配置 - {config_name}")
        
        # 应用深色主题样式（但保留系统标准标题栏）
        self.configure_popup_style(edit_dialog)
        
        # 配置表单框架
        form_frame = ttk.Frame(edit_dialog, padding=15, style='Dark.TFrame')
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # 配置名称（只读）
        ttk.Label(form_frame, text="配置名称:", style='Dark.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_label = ttk.Label(form_frame, text=config_name, style='Dark.TLabel')
        name_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 基础URI
        ttk.Label(form_frame, text="基础URI:", style='Dark.TLabel').grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        uri_var = tk.StringVar(value=base_uri)
        uri_entry = ttk.Entry(form_frame, textvariable=uri_var, width=40, style='Dark.TEntry')
        uri_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 模型名称
        ttk.Label(form_frame, text="模型名称:", style='Dark.TLabel').grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        model_var = tk.StringVar(value=model_name)
        model_entry = ttk.Entry(form_frame, textvariable=model_var, width=40, style='Dark.TEntry')
        model_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # API密钥
        ttk.Label(form_frame, text="API密钥:", style='Dark.TLabel').grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        key_var = tk.StringVar(value=api_key)
        key_entry = ttk.Entry(form_frame, textvariable=key_var, width=40, style='Dark.TEntry', show="*")
        key_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 温度系数
        ttk.Label(form_frame, text="温度系数:", style='Dark.TLabel').grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        temp_var = tk.DoubleVar(value=temperature)
        temp_scale = ttk.Scale(form_frame, from_=0.0, to=2.0, variable=temp_var, orient=tk.HORIZONTAL, style='Dark.Horizontal.TScale')
        temp_scale.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        temp_label = ttk.Label(form_frame, text=f"{temperature:.1f}", style='Dark.TLabel')
        temp_label.grid(row=4, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 更新温度显示
        def update_temp_label(*args):
            temp_label.config(text=f"{temp_var.get():.1f}")
        temp_var.trace("w", update_temp_label)
        
        # 设为默认
        default_var = tk.BooleanVar(value=bool(is_default))
        default_check = ttk.Checkbutton(form_frame, text="设为默认配置", variable=default_var, style='Dark.TCheckbutton')
        default_check.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(form_frame, style='Dark.TFrame')
        button_frame.grid(row=8, column=0, columnspan=2, pady=20)
        
        def save_config():
            uri = uri_var.get().strip()
            model = model_var.get().strip()
            key = key_var.get().strip()
            temp = temp_var.get()
            is_default = default_var.get()
            
            if not all([uri, model, key]):
                messagebox.showwarning("警告", "请填写所有必填字段！")
                return
            
            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                if is_default:
                    # 如果设为默认，先清除其他默认配置
                    cursor.execute("UPDATE llm_configs SET is_default = 0")
                
                cursor.execute("""
                UPDATE llm_configs SET base_uri = ?, model_name = ?, api_key = ?, temperature = ?, is_default = ?
                WHERE name = ?
                """, (uri, model, key, temp, 1 if is_default else 0, config_name))
                
                conn.commit()
                messagebox.showinfo("成功", "配置已更新！")
                edit_dialog.destroy()
                self.load_llm_configs()
                
            except Exception as e:
                messagebox.showerror("错误", f"更新配置时出错: {e}")
            finally:
                conn.close()
        
        ttk.Button(button_frame, text="保存", command=save_config, style='Dark.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=edit_dialog.destroy, style='Dark.TButton').pack(side=tk.LEFT, padx=5)
    
    def delete_llm_config(self):
        """删除LLM配置"""
        selected_item = self.config_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择一个配置！")
            return
        
        # 获取选中的配置名称（去掉默认标记）
        values = self.config_tree.item(selected_item[0], "values")
        config_name = values[0].replace("★ ", "")
        
        if messagebox.askyesno("确认", f"确定要删除配置 '{config_name}' 吗？"):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute("DELETE FROM llm_configs WHERE name = ?", (config_name,))
                conn.commit()
                messagebox.showinfo("成功", "配置已删除！")
                self.load_llm_configs()
            except Exception as e:
                messagebox.showerror("错误", f"删除配置时出错: {e}")
            finally:
                conn.close()
    
    def set_default_llm_config(self):
        """设置默认LLM配置"""
        selected_item = self.config_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择一个配置！")
            return
        
        # 获取选中的配置名称（去掉默认标记）
        values = self.config_tree.item(selected_item[0], "values")
        config_name = values[0].replace("★ ", "")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 清除所有默认配置
            cursor.execute("UPDATE llm_configs SET is_default = 0")
            # 设置选中的配置为默认
            cursor.execute("UPDATE llm_configs SET is_default = 1 WHERE name = ?", (config_name,))
            conn.commit()
            messagebox.showinfo("成功", f"已设置 '{config_name}' 为默认配置！")
            self.load_llm_configs()
        except Exception as e:
            messagebox.showerror("错误", f"设置默认配置时出错: {e}")
        finally:
            conn.close()
    
    def get_default_llm_config(self):
        """获取默认LLM配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, base_uri, model_name, api_key, temperature FROM llm_configs WHERE is_default = 1")
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'name': result[0],
                'base_uri': result[1],
                'model_name': result[2],
                'api_key': result[3],
                'temperature': result[4]
            }
        return None
    
    def handle_return_key(self, event):
        """处理回车键事件"""
        # 如果按下Shift+Enter，则换行
        if event.state & 0x1:  # Shift键被按下
            return None  # 允许默认的换行行为
        else:
            # 普通回车键，阻止默认行为，不换行
            return "break"
    
    def clear_input(self):
        """清空输入框"""
        self.input_text.delete("1.0", tk.END)
    
    def send_llm_message(self):
        """发送LLM消息"""
        message = self.input_text.get("1.0", tk.END).strip()
        if not message:
            return
        
        # 获取默认配置
        config = self.get_default_llm_config()
        if not config:
            messagebox.showwarning("警告", "请先配置AI模型！")
            return
        
        # 获取当前时间信息
        now = datetime.datetime.now()
        current_date = now.strftime("%Y年%m月%d日")
        current_time = now.strftime("%H:%M:%S")
        current_weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]
        
        # 获取农历信息（如果可用）
        lunar_info = ""
        if LUNAR_AVAILABLE:
            try:
                if LUNAR_PYTHON_AVAILABLE:
                    from lunar_python import Lunar, Solar
                    solar = Solar.fromYmd(now.year, now.month, now.day)
                    lunar = Lunar.fromSolar(solar)
                    lunar_month = lunar.getMonthInChinese()
                    lunar_day = lunar.getDayInChinese()
                    lunar_info = f"农历{lunar_month}月{lunar_day}"
                elif LUNAR_JS_AVAILABLE:
                    if hasattr(self, 'lunar_bridge'):
                        lunar_month = self.lunar_bridge.get_lunar_month(now.year, now.month, now.day)
                        lunar_day = self.lunar_bridge.get_lunar_day(now.year, now.month, now.day)
                        lunar_info = f"农历{lunar_month}月{lunar_day}"
            except Exception:
                lunar_info = ""
        
        # 构建包含时间信息的系统提示
        time_context = f"当前时间是：{current_date} {current_weekday} {current_time}"
        if lunar_info:
            time_context += f"，{lunar_info}"
        
        # 保存用户消息到数据库
        self.save_chat_message("user", message)
        
        # 显示用户消息
        self.chat_text.configure(state="normal")
        self.chat_text.insert(tk.END, f"您: {message}\n", "user")
        self.chat_text.configure(state="disabled")
        self.chat_text.see(tk.END)
        
        # 清空输入框
        self.input_text.delete("1.0", tk.END)
        
        # 显示等待消息
        self.chat_text.configure(state="normal")
        self.chat_text.insert(tk.END, "AI助手: ", "ai")
        self.chat_text.configure(state="disabled")
        self.chat_text.see(tk.END)
        
        # 在新线程中发送请求，包含时间上下文
        threading.Thread(target=self.call_llm_api_stream_with_time, args=(message, config, time_context), daemon=True).start()
    
    def call_llm_api_stream(self, message, config):
        """调用LLM API（流式）"""
        # 获取当前时间信息
        now = datetime.datetime.now()
        current_date = now.strftime("%Y年%m月%d日")
        current_time = now.strftime("%H:%M:%S")
        current_weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]
        
        # 获取农历信息（如果可用）
        lunar_info = ""
        if LUNAR_AVAILABLE:
            try:
                if LUNAR_PYTHON_AVAILABLE:
                    from lunar_python import Lunar, Solar
                    solar = Solar.fromYmd(now.year, now.month, now.day)
                    lunar = Lunar.fromSolar(solar)
                    lunar_month = lunar.getMonthInChinese()
                    lunar_day = lunar.getDayInChinese()
                    lunar_info = f"农历{lunar_month}月{lunar_day}"
                elif LUNAR_JS_AVAILABLE:
                    if hasattr(self, 'lunar_bridge'):
                        lunar_month = self.lunar_bridge.get_lunar_month(now.year, now.month, now.day)
                        lunar_day = self.lunar_bridge.get_lunar_day(now.year, now.month, now.day)
                        lunar_info = f"农历{lunar_month}月{lunar_day}"
            except Exception:
                lunar_info = ""
        
        # 构建包含时间信息的系统提示
        time_context = f"当前时间是：{current_date} {current_weekday} {current_time}"
        if lunar_info:
            time_context += f"，{lunar_info}"
        
        self.call_llm_api_stream_with_time(message, config, time_context)
    
    def call_llm_api_stream_with_time(self, message, config, time_context):
        """调用LLM API（流式，包含时间信息）"""
        try:
            # 检查是否是搜索请求 - 支持多种格式
            is_search_request = False
            search_query = None
            
            # 支持多种搜索前缀格式
            if message.startswith("搜索:"):
                is_search_request = True
                search_query = message[3:].strip()
            elif message.startswith("搜索") and len(message) > 2:
                is_search_request = True
                search_query = message[2:].strip()
            elif message.startswith("search:"):
                is_search_request = True
                search_query = message[7:].strip()
            elif message.startswith("search") and len(message) > 5:
                is_search_request = True
                search_query = message[5:].strip()
            
            print(f"原始消息: {message}")
            print(f"是否为搜索请求: {is_search_request}")
            
            if is_search_request and search_query:
                print(f"搜索查询: {search_query}")
                
                # 使用Search1API进行搜索
                search_results = self.search_with_search1api(search_query)
                
                if search_results:
                    # 格式化搜索结果
                    formatted_results = self.format_search_results(search_results)
                    print(f"搜索结果格式化完成，长度: {len(formatted_results)}")
                    # 将搜索结果添加到消息中
                    message = f"根据您的搜索请求\"{search_query}\"，我找到了以下信息:\n\n{formatted_results}"
                else:
                    print("搜索失败")
                    message = f"抱歉，搜索\"{search_query}\"时出现了问题，请稍后重试。"
            else:
                print("非搜索请求，使用普通模式")
            
            # 获取详细农历信息
            detailed_lunar = self.get_detailed_lunar_context()
            
            # 构建完整的时间上下文
            full_context = f"{time_context}\n\n{detailed_lunar}" if detailed_lunar else time_context
            
            # 构建请求URL
            url = f"{config['base_uri']}/chat/completions"
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json"
            }
            
            # 构建消息历史（包含时间信息和当前消息）
            messages = []
            
            # 添加系统消息，包含当前时间信息和详细农历信息
            messages.append({"role": "system", "content": f"{full_context}\n\n请基于以上时间信息和农历详情回答用户的问题。"})
            
            # 添加历史消息
            for msg in self.current_messages:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            # 构建请求体（支持流式）
            data = {
                "model": config['model_name'],
                "messages": messages,
                "temperature": config['temperature'],
                "stream": True
            }
            
            # 发送流式请求
            response = requests.post(url, headers=headers, json=data, timeout=30, stream=True)
            
            if response.status_code == 200:
                # 处理流式响应
                self.process_stream_response(response)
            else:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                self.root.after(0, self.update_chat_with_error, error_msg)
        except Exception as e:
            # 如果流式请求失败，尝试非流式请求
            try:
                self.root.after(0, self.fallback_to_non_stream_with_time, message, config, time_context)
            except Exception as fallback_error:
                error_msg = f"流式和非流式请求都失败: {str(e)}"
                self.root.after(0, self.update_chat_with_error, error_msg)
                
        except requests.exceptions.Timeout:
            error_msg = "请求超时，请检查网络连接"
            self.root.after(0, self.update_chat_with_error, error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            self.root.after(0, self.update_chat_with_error, error_msg)
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            self.root.after(0, self.update_chat_with_error, error_msg)
    
    def process_stream_response(self, response):
        """处理流式响应"""
        try:
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # 去掉 'data: ' 前缀
                        if data == '[DONE]':
                            # 流式响应结束
                            self.root.after(0, self.finish_stream_response)
                            break
                        else:
                            try:
                                import json
                                chunk = json.loads(data)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        content = delta['content']
                                        # 在主线程中更新UI
                                        self.root.after(0, self.append_stream_content, content)
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            error_msg = f"处理流式响应时出错: {str(e)}"
            self.root.after(0, self.update_chat_with_error, error_msg)
    
    def append_stream_content(self, content):
        """追加流式内容"""
        if not hasattr(self, 'stream_content'):
            self.stream_content = ""
        
        self.stream_content += content
        
        self.chat_text.configure(state="normal")
        self.chat_text.insert(tk.END, content, "ai")
        self.chat_text.configure(state="disabled")
        self.chat_text.see(tk.END)
    
    def finish_stream_response(self):
        """完成流式响应"""
        self.chat_text.configure(state="normal")
        self.chat_text.insert(tk.END, "\n\n")
        self.chat_text.configure(state="disabled")
        self.chat_text.see(tk.END)
        
        # 保存AI回复到数据库
        if hasattr(self, 'stream_content') and self.stream_content:
            self.save_chat_message("assistant", self.stream_content)
            self.stream_content = ""
    
    def fallback_to_non_stream(self, message, config):
        """回退到非流式请求"""
        # 获取当前时间信息
        now = datetime.datetime.now()
        current_date = now.strftime("%Y年%m月%d日")
        current_time = now.strftime("%H:%M:%S")
        current_weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]
        
        # 构建基本时间上下文
        time_context = f"当前时间是：{current_date} {current_weekday} {current_time}"
        
        # 获取详细农历信息
        detailed_lunar = self.get_detailed_lunar_context()
        
        # 构建完整的时间上下文
        full_context = f"{time_context}\n\n{detailed_lunar}" if detailed_lunar else time_context
        
        self.fallback_to_non_stream_with_time(message, config, full_context)
    
    def fallback_to_non_stream_with_time(self, message, config, time_context):
        """回退到非流式请求（包含时间信息）"""
        # 删除"AI助手: "消息
        self.chat_text.configure(state="normal")
        last_line_start = self.chat_text.index("end-2l linestart")
        last_line_end = self.chat_text.index("end-1l")
        self.chat_text.delete(last_line_start, last_line_end)
        
        # 显示回退消息
        self.chat_text.insert(tk.END, "AI助手: 正在使用备用模式...\n", "system")
        self.chat_text.configure(state="disabled")
        self.chat_text.see(tk.END)
        
        # 在新线程中发送非流式请求
        threading.Thread(target=self.call_llm_api_with_time, args=(message, config, time_context), daemon=True).start()
    
    def call_llm_api(self, message, config):
        """调用LLM API（非流式，备用）"""
        try:
            # 构建请求URL
            url = f"{config['base_uri']}/chat/completions"
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json"
            }
            
            # 构建消息历史（包含当前消息）
            messages = []
            for msg in self.current_messages:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            # 构建请求体
            data = {
                "model": config['model_name'],
                "messages": messages,
                "temperature": config['temperature']
            }
            
            # 发送请求
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    ai_message = result['choices'][0]['message']['content']
                    
                    # 在主线程中更新UI
                    self.root.after(0, self.update_chat_with_response, ai_message)
                else:
                    error_msg = "API返回格式错误"
                    self.root.after(0, self.update_chat_with_error, error_msg)
            else:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                self.root.after(0, self.update_chat_with_error, error_msg)
                
        except requests.exceptions.Timeout:
            error_msg = "请求超时，请检查网络连接"
            self.root.after(0, self.update_chat_with_error, error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            self.root.after(0, self.update_chat_with_error, error_msg)
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            self.root.after(0, self.update_chat_with_error, error_msg)
    
    def update_chat_with_response(self, ai_message):
        """更新聊天界面显示AI回复（非流式）"""
        self.chat_text.configure(state="normal")
        
        # 删除"AI助手: "消息
        last_line_start = self.chat_text.index("end-2l linestart")
        last_line_end = self.chat_text.index("end-1l")
        self.chat_text.delete(last_line_start, last_line_end)
        
        # 插入AI回复
        self.chat_text.insert(tk.END, f"AI助手: {ai_message}\n\n", "ai")
        self.chat_text.configure(state="disabled")
        self.chat_text.see(tk.END)
        
        # 保存AI回复到数据库
        self.save_chat_message("assistant", ai_message)
    
    def update_chat_with_error(self, error_msg):
        """更新聊天界面显示错误信息"""
        self.chat_text.configure(state="normal")
        
        # 删除"AI助手: "消息
        last_line_start = self.chat_text.index("end-2l linestart")
        last_line_end = self.chat_text.index("end-1l")
        self.chat_text.delete(last_line_start, last_line_end)
        
        # 插入错误信息
        self.chat_text.insert(tk.END, f"AI助手: 抱歉，出现了错误: {error_msg}\n\n", "system")
        self.chat_text.configure(state="disabled")
        self.chat_text.see(tk.END)
    
    def get_detailed_lunar_context(self):
        """获取详细的农历信息上下文"""
        try:
            if not LUNAR_JS_AVAILABLE:
                return ""
            
            # 获取当前日期
            from datetime import datetime
            now = datetime.now()
            year = now.year
            month = now.month
            day = now.day
            
            # 创建临时JS文件获取完整农历信息
            temp_js = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_lunar_context.js")
            with open(temp_js, "w", encoding="utf-8") as f:
                f.write("const lunar = require('./lunar.js');\n")
                f.write(f"const solar = lunar.Solar.fromYmd({year}, {month}, {day});\n")
                f.write("const lunarObj = solar.getLunar();\n")
                f.write("const result = {\n")
                f.write("  lunar_info: lunarObj.toFullString(),\n")
                f.write("  yi_ji: {\n")
                f.write("    yi: lunarObj.getDayYi(),\n")
                f.write("    ji: lunarObj.getDayJi()\n")
                f.write("  },\n")
                f.write("  animal: lunarObj.getAnimal(),\n")
                f.write("  xiu: lunarObj.getXiu(),\n")
                f.write("  zheng: lunarObj.getZheng(),\n")
                f.write("  xiu_luck: lunarObj.getXiuLuck(),\n")
                f.write("  peng_zu_gan: lunarObj.getPengZuGan(),\n")
                f.write("  peng_zu_zhi: lunarObj.getPengZuZhi(),\n")
                f.write("  day_position_xi: lunarObj.getDayPositionXi(),\n")
                f.write("  day_position_xi_desc: lunarObj.getDayPositionXiDesc(),\n")
                f.write("  day_position_yang_gui: lunarObj.getDayPositionYangGui(),\n")
                f.write("  day_position_yang_gui_desc: lunarObj.getDayPositionYangGuiDesc(),\n")
                f.write("  day_position_yin_gui: lunarObj.getDayPositionYinGui(),\n")
                f.write("  day_position_yin_gui_desc: lunarObj.getDayPositionYinGuiDesc(),\n")
                f.write("  day_position_fu: lunarObj.getDayPositionFu(),\n")
                f.write("  day_position_fu_desc: lunarObj.getDayPositionFuDesc(),\n")
                f.write("  day_position_cai: lunarObj.getDayPositionCai(),\n")
                f.write("  day_position_cai_desc: lunarObj.getDayPositionCaiDesc(),\n")
                f.write("  day_chong_desc: lunarObj.getDayChongDesc(),\n")
                f.write("  day_sha: lunarObj.getDaySha(),\n")
                f.write("  gong: lunarObj.getGong(),\n")
                f.write("  shou: lunarObj.getShou()\n")
                f.write("};\n")
                f.write("console.log(JSON.stringify(result));")
            
            # 执行JS文件
            result = subprocess.check_output(["node", temp_js], text=True, encoding="utf-8")
            
            # 删除临时文件
            os.remove(temp_js)
            
            # 解析JSON结果
            data = json.loads(result.strip())
            
            # 使用现有的generate_lunar_info_text方法格式生成文本
            date_str = f"{year}-{month:02d}-{day:02d}"
            lunar_text = self.generate_lunar_info_text(
                date_str, data["lunar_info"], data["animal"], data["xiu"], 
                data.get("zheng", ""), data.get("xiu_luck", ""),
                data.get("peng_zu_gan", ""), data.get("peng_zu_zhi", ""),
                data.get("day_position_xi", ""), data.get("day_position_xi_desc", ""),
                data.get("day_position_yang_gui", ""), data.get("day_position_yang_gui_desc", ""),
                data.get("day_position_yin_gui", ""), data.get("day_position_yin_gui_desc", ""),
                data.get("day_position_fu", ""), data.get("day_position_fu_desc", ""),
                data.get("day_position_cai", ""), data.get("day_position_cai_desc", ""),
                data.get("day_chong_desc", ""), data.get("day_sha", ""),
                data.get("gong", ""), data.get("shou", ""), data["yi_ji"]
            )
            
            return lunar_text
            
        except Exception as e:
            print(f"获取详细农历信息时出错: {e}")
            return ""

    def call_llm_api_with_time(self, message, config, time_context):
        """非流式API调用（包含时间信息）"""
        try:
            # 获取详细农历信息
            detailed_lunar = self.get_detailed_lunar_context()
            
            # 构建完整的时间上下文
            full_context = f"{time_context}\n\n{detailed_lunar}" if detailed_lunar else time_context
            
            # 构建请求URL
            url = f"{config['base_uri']}/chat/completions"
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json"
            }
            
            # 构建消息历史（包含当前消息和时间信息）
            messages = []
            # 添加时间信息的系统消息
            messages.append({"role": "system", "content": f"{full_context}\n\n请基于以上时间信息和农历详情回答用户的问题。"})
            
            # 添加历史消息
            for msg in self.current_messages:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            # 构建请求体
            data = {
                "model": config['model_name'],
                "messages": messages,
                "temperature": config['temperature']
            }
            
            # 发送请求
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    ai_message = result['choices'][0]['message']['content']
                    
                    # 在主线程中更新UI
                    self.root.after(0, self.update_chat_with_response, ai_message)
                else:
                    error_msg = "API返回格式错误"
                    self.root.after(0, self.update_chat_with_error, error_msg)
            else:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                self.root.after(0, self.update_chat_with_error, error_msg)
                
        except requests.exceptions.Timeout:
            error_msg = "请求超时，请检查网络连接"
            self.root.after(0, self.update_chat_with_error, error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            self.root.after(0, self.update_chat_with_error, error_msg)
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            self.root.after(0, self.update_chat_with_error, error_msg)


    
    def show_reminder_popup(self, reminder_id, reminder_time, reminder_message):
        """显示提醒弹窗"""
        popup = tk.Toplevel(self.root)
        popup.geometry("400x200")
        popup.attributes("-topmost", True)  # 置顶显示
        popup.title(f"提醒 - {reminder_time}")
        
        # 应用深色主题样式（但保留系统标准标题栏）
        self.configure_popup_style(popup)
        
        # 提醒内容显示
        content_frame = ttk.Frame(popup, padding=10, style='Dark.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(content_frame, text=f"时间: {reminder_time}", font=("SimSun", 12, "bold"), style='Dark.TLabel').pack(pady=10)
        
        message_frame = ttk.Frame(content_frame, style='Dark.TFrame')
        message_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        message_text = tk.Text(message_frame, wrap=tk.WORD, height=5, width=40,
                             bg='#222222', fg='white', insertbackground='white')
        message_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        message_text.insert(tk.END, reminder_message)
        message_text.configure(state="disabled")  # 设置为只读
        
        # 滚动条
        scrollbar = ttk.Scrollbar(message_frame, orient="vertical", command=message_text.yview, style='Dark.Vertical.TScrollbar')
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        message_text.configure(yscrollcommand=scrollbar.set)
        
        # 按钮区域
        button_frame = ttk.Frame(popup, style='Dark.TFrame')
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="确定", command=popup.destroy, style='Dark.TButton').pack(side=tk.RIGHT, padx=10)

    def configure_popup_style(self, popup):
        """配置弹窗的黑底白字样式"""
        popup.configure(bg='black')
        
        # 配置所有子组件的样式
        style = ttk.Style()
        
        # 创建弹窗专用的暗色主题样式
        try:
            style.theme_use('clam')
        except:
            pass
            
        # 配置各种组件的暗色样式
        style.configure('Dark.TFrame', background='black')
        style.configure('Dark.TLabel', background='black', foreground='white')
        style.configure('Dark.TButton', background='#333333', foreground='white')
        style.configure('Dark.TEntry', fieldbackground='#222222', foreground='white', insertcolor='white')
        style.configure('Dark.TText', background='#222222', foreground='white', insertbackground='white')
        style.configure('Dark.TCombobox', fieldbackground='#222222', foreground='white', 
                       background='#333333', selectbackground='#555555')
        style.configure('Dark.TCheckbutton', background='black', foreground='white')
        style.configure('Dark.TRadiobutton', background='black', foreground='white')
        
        # 配置Treeview的暗色样式
        style.configure('Dark.Treeview', background='#222222', foreground='white', 
                       fieldbackground='#222222')
        style.map('Dark.Treeview', background=[('selected', '#4a4a4a')], 
                 foreground=[('selected', 'white')])
        
        # 配置Treeview头部的暗色样式
        style.configure('Dark.Treeview.Heading', background='#333333', foreground='white')
        
        # 配置滚动条的暗色样式
        style.configure('Dark.Vertical.TScrollbar', background='#333333', 
                       troughcolor='#111111', arrowcolor='white')
        style.configure('Dark.Horizontal.TScrollbar', background='#333333', 
                       troughcolor='#111111', arrowcolor='white')
        
        # 配置Notebook的暗色样式
        style.configure('Dark.TNotebook', background='black', borderwidth=0)
        style.configure('Dark.TNotebook.Tab', background='#333333', foreground='white', 
                       padding=[10, 5], borderwidth=1)
        style.map('Dark.TNotebook.Tab', 
                 background=[('selected', '#555555'), ('active', '#444444')],
                 foreground=[('selected', 'white'), ('active', 'white')])
        
        # 配置Scale的暗色样式
        style.configure('Dark.Horizontal.TScale', background='black', 
                       troughcolor='#333333', slidercolor='#666666')

    def create_custom_popup_title_bar(self, popup, title):
        """已废弃：创建自定义黑底白字标题栏 - 现在使用系统标准标题栏"""
        # 使用系统标准标题栏，不再创建自定义标题栏
        popup.title(title)  # 设置标准窗口标题
        # 不再调用overrideredirect，保持系统标准窗口样式
        return None

    def show_custom_message(self, title, message, message_type="info"):
        """显示消息对话框 - 使用系统标准窗口"""
        popup = tk.Toplevel(self.root)
        popup.title(title)  # 使用系统标准标题
        popup.geometry("400x200")
        popup.resizable(False, False)
        
        # 不再创建自定义标题栏
        # self.create_custom_popup_title_bar(popup, title)
        
        # 应用深色主题样式（但保留系统标准标题栏）
        self.configure_popup_style(popup)
        
        # 主框架
        main_frame = ttk.Frame(popup, padding=20, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 消息图标
        icon_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        icon_frame.pack(pady=(0, 10))
        
        # 根据消息类型设置图标和颜色
        icon_text = "ℹ"
        icon_color = "#0078d4"  # 蓝色
        
        if message_type == "warning":
            icon_text = "⚠"
            icon_color = "#ff8c00"  # 橙色
        elif message_type == "error":
            icon_text = "✕"
            icon_color = "#e81123"  # 红色
        elif message_type == "question":
            icon_text = "?"
            icon_color = "#0078d4"  # 蓝色
        
        icon_label = ttk.Label(icon_frame, text=icon_text, font=("Arial", 24), 
                             foreground=icon_color, style='Dark.TLabel')
        icon_label.pack()
        
        # 消息内容
        message_label = ttk.Label(main_frame, text=message, font=("SimSun", 11), 
                                wraplength=350, justify="center", style='Dark.TLabel')
        message_label.pack(pady=(0, 20))
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        button_frame.pack()
        
        def on_ok():
            popup.destroy()
            return True
        
        def on_cancel():
            popup.destroy()
            return False
        
        if message_type == "question":
            # 确认对话框
            ttk.Button(button_frame, text="是", command=lambda: [popup.destroy(), setattr(popup, 'result', True)], 
                     style='Dark.TButton').pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="否", command=lambda: [popup.destroy(), setattr(popup, 'result', False)], 
                     style='Dark.TButton').pack(side=tk.LEFT, padx=5)
        else:
            # 信息对话框
            ttk.Button(button_frame, text="确定", command=lambda: [popup.destroy(), setattr(popup, 'result', True)], 
                     style='Dark.TButton').pack()
        
        # 居中显示
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() - popup.winfo_width()) // 2
        y = (popup.winfo_screenheight() - popup.winfo_height()) // 2
        popup.geometry(f"+{x}+{y}")
        
        popup.focus_set()
        popup.grab_set()
        popup.wait_window()
        
        return getattr(popup, 'result', True)

    def create_custom_title_bar(self):
        """已废弃：创建自定义标题栏 - 现在使用系统标准标题栏"""
        # 此方法已废弃，使用系统标准标题栏
        pass

    def bind_window_drag(self):
        """已废弃：绑定窗口拖动功能 - 现在使用系统标准窗口管理"""
        # 此方法已废弃，使用系统标准窗口管理
        pass

    def start_move(self, event):
        """已废弃：开始移动窗口"""
        # 此方法已废弃
        pass

    def stop_move(self, event):
        """已废弃：停止移动窗口"""
        # 此方法已废弃
        pass

    def do_move(self, event):
        """已废弃：执行窗口移动"""
        # 此方法已废弃
        pass

    def minimize_window(self):
        """最小化窗口 - 使用系统标准最小化"""
        # 使用系统标准最小化功能
        self.root.iconify()

    def toggle_maximize(self):
        """切换最大化/还原窗口 - 使用系统标准功能"""
        # 使用系统标准最大化/还原功能
        if self.root.state() == 'zoomed':
            self.root.state('normal')
        else:
            self.root.state('zoomed')

    def on_hover(self, event, button, is_close=False):
        """已废弃：按钮悬停效果 - 不再使用自定义按钮"""
        # 此方法已废弃
        pass

    def on_leave(self, event, button):
        """已废弃：按钮离开效果 - 不再使用自定义按钮"""
        # 此方法已废弃
        pass

    # 历史对话管理方法
    def new_chat_session(self):
        """新建聊天会话"""
        self.current_session_id = None
        self.current_messages = []
        
        # 清空聊天区域
        self.chat_text.configure(state="normal")
        self.chat_text.delete("1.0", tk.END)
        self.chat_text.insert(tk.END, "AI助手: 您好！我是您的AI助手，有什么可以帮助您的吗？\n\n", "system")
        self.chat_text.configure(state="disabled")
        
        # 清空输入框
        self.input_text.delete("1.0", tk.END)
        
        # 取消选中状态
        self.session_tree.selection_remove(self.session_tree.selection())
    


    def load_chat_sessions(self):
        """加载历史对话列表"""
        # 清空现有数据
        for item in self.session_tree.get_children():
            self.session_tree.delete(item)
        
        # 从数据库加载会话
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, updated_at 
            FROM chat_sessions 
            ORDER BY updated_at DESC
        """)
        
        for row in cursor.fetchall():
            session_id, title, updated_at = row
            # 格式化时间
            try:
                dt = datetime.datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%m-%d %H:%M")
            except:
                formatted_time = updated_at[:16] if len(updated_at) > 16 else updated_at
            
            self.session_tree.insert("", tk.END, text=title, values=(formatted_time,), tags=(session_id,))
        
        conn.close()
    
    def load_chat_session(self, event):
        """加载选中的聊天会话"""
        selection = self.session_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        session_id = self.session_tree.item(item, "tags")[0]
        
        # 从数据库加载会话消息
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content 
            FROM chat_messages 
            WHERE session_id = ? 
            ORDER BY timestamp
        """, (session_id,))
        
        messages = cursor.fetchall()
        conn.close()
        
        # 更新当前会话
        self.current_session_id = session_id
        self.current_messages = [{"role": role, "content": content} for role, content in messages]
        
        # 显示消息
        self.chat_text.configure(state="normal")
        self.chat_text.delete("1.0", tk.END)
        
        for msg in messages:
            role, content = msg
            if role == "user":
                self.chat_text.insert(tk.END, f"您: {content}\n", "user")
            elif role == "assistant":
                self.chat_text.insert(tk.END, f"AI助手: {content}\n", "ai")
        
        self.chat_text.configure(state="disabled")
        self.chat_text.see(tk.END)
    
    def save_chat_message(self, role, content):
        """保存聊天消息到数据库"""
        if not self.current_session_id:
            # 创建新会话
            title = content[:20] + "..." if len(content) > 20 else content
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_sessions (title, created_at, updated_at) 
                VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (title,))
            self.current_session_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # 刷新会话列表
            self.load_chat_sessions()
        
        # 保存消息
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_messages (session_id, role, content) 
            VALUES (?, ?, ?)
        """, (self.current_session_id, role, content))
        
        # 更新会话时间
        cursor.execute("""
            UPDATE chat_sessions 
            SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (self.current_session_id,))
        
        conn.commit()
        conn.close()
        
        # 更新当前消息列表
        self.current_messages.append({"role": role, "content": content})
    
    def delete_selected_sessions(self):
        """删除选中的会话"""
        selection = self.session_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的对话！")
            return
        
        if messagebox.askyesno("确认删除", f"确定要删除选中的 {len(selection)} 个对话吗？"):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for item in selection:
                session_id = self.session_tree.item(item, "tags")[0]
                cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
                
                # 如果删除的是当前会话，清空当前会话
                if session_id == self.current_session_id:
                    self.current_session_id = None
                    self.current_messages = []
            
            conn.commit()
            conn.close()
            
            # 刷新会话列表
            self.load_chat_sessions()
            
            # 如果当前会话被删除，清空聊天区域
            if self.current_session_id is None:
                self.chat_text.configure(state="normal")
                self.chat_text.delete("1.0", tk.END)
                self.chat_text.insert(tk.END, "AI助手: 您好！我是您的AI助手，有什么可以帮助您的吗？\n\n", "system")
                self.chat_text.configure(state="disabled")
    
    def clear_all_sessions(self):
        """清空所有会话"""
        if messagebox.askyesno("确认清空", "确定要清空所有历史对话吗？此操作不可恢复！"):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_sessions")
            conn.commit()
            conn.close()
            
            # 清空当前会话
            self.current_session_id = None
            self.current_messages = []
            
            # 刷新会话列表
            self.load_chat_sessions()
            
            # 清空聊天区域
            self.chat_text.configure(state="normal")
            self.chat_text.delete("1.0", tk.END)
            self.chat_text.insert(tk.END, "AI助手: 您好！我是您的AI助手，有什么可以帮助您的吗？\n\n", "system")
            self.chat_text.configure(state="disabled")



    def create_tooltip(self, widget, text):
        """创建工具提示 - 使用系统标准工具提示"""
        def on_enter(event):
            self.tooltip = tk.Toplevel()
            # 不再使用wm_overrideredirect，让系统管理工具提示窗口
            # self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            
            # 设置工具提示样式
            self.tooltip.configure(bg="#333333")
            label = tk.Label(self.tooltip, text=text, background="#333333", 
                           foreground="white", relief="solid", borderwidth=1,
                           font=("SimSun", 9))
            label.pack()
            
            # 确保工具提示不会获得焦点
            self.tooltip.wm_transient(self.root)
            self.tooltip.wm_attributes('-topmost', True)

        def on_leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                del self.tooltip

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def show_session_context_menu(self, event):
        """显示会话上下文菜单"""
        item = self.session_tree.identify_row(event.y)
        if item:
            # 选中右键点击的项目
            self.session_tree.selection_set(item)
            
            menu = tk.Menu(self.root, tearoff=0, bg='#333333', fg='white', activebackground='#555555', activeforeground='white')
            menu.add_command(label="编辑标题", command=lambda: self.edit_chat_session(item))
            menu.add_separator()
            menu.add_command(label="删除对话", command=lambda: self.delete_chat_session(item))
            menu.post(event.x_root, event.y_root)

    def edit_chat_session(self, selected_item):
        """编辑选中的聊天会话标题"""
        selection = self.session_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        session_id = self.session_tree.item(item, "tags")[0]
        current_title = self.session_tree.item(item, "text")
        
        # 创建编辑对话框
        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.geometry("400x150")
        edit_dialog.title("编辑对话标题")
        
        # 创建自定义标题栏
        self.create_custom_popup_title_bar(edit_dialog, "编辑对话标题")
        
        # 应用黑底白字样式
        self.configure_popup_style(edit_dialog)
        
        # 主框架
        main_frame = ttk.Frame(edit_dialog, padding=20, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题输入
        ttk.Label(main_frame, text="对话标题:", style='Dark.TLabel').pack(anchor=tk.W, pady=(0, 5))
        title_var = tk.StringVar(value=current_title)
        title_entry = ttk.Entry(main_frame, textvariable=title_var, width=50, style='Dark.TEntry')
        title_entry.pack(fill=tk.X, pady=(0, 20))
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        btn_frame.pack(fill=tk.X)
        
        def save_title():
            new_title = title_var.get().strip()
            if new_title:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE chat_sessions SET title = ? WHERE id = ?", (new_title, session_id))
                conn.commit()
                conn.close()
                
                # 刷新会话列表
                self.load_chat_sessions()
                edit_dialog.destroy()
        
        ttk.Button(btn_frame, text="保存", command=save_title, style='Dark.TButton').pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="取消", command=edit_dialog.destroy, style='Dark.TButton').pack(side=tk.RIGHT)
        
        # 聚焦到输入框
        title_entry.focus_set()
        title_entry.bind("<Return>", lambda e: save_title())

    def delete_chat_session(self, selected_item):
        """删除选中的聊天会话"""
        session_id = self.session_tree.item(selected_item, "tags")[0]
        
        if messagebox.askyesno("确认删除", "确定要删除这个对话吗？"):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            
            # 如果删除的是当前会话，清空当前会话
            if session_id == self.current_session_id:
                self.current_session_id = None
                self.current_messages = []
            
            conn.commit()
            conn.close()
            
            # 刷新会话列表
            self.load_chat_sessions()
            
            # 如果当前会话被删除，清空聊天区域
            if self.current_session_id is None:
                self.chat_text.configure(state="normal")
                self.chat_text.delete("1.0", tk.END)
                self.chat_text.insert(tk.END, "AI助手: 您好！我是您的AI助手，有什么可以帮助您的吗？\n\n", "system")
                self.chat_text.configure(state="disabled")

# 全局锁文件路径
LOCK_FILE_PATH = os.path.join(os.path.expanduser("./"), ".calendar_app.lock")

def is_already_running():
    """检查应用是否已在运行"""
    if not os.path.exists(LOCK_FILE_PATH):
        return False
    
    try:
        # 读取锁文件中的进程ID
        with open(LOCK_FILE_PATH, "r") as f:
            pid_str = f.read().strip()
        
        if not pid_str:
            # 锁文件为空，视为无效
            os.remove(LOCK_FILE_PATH)
            return False
            
        lock_pid = int(pid_str)
        
        # 检查进程是否存在
        if os.name == 'nt':  # Windows
            try:
                import psutil
                if psutil.pid_exists(lock_pid):
                    return True
                else:
                    # 进程不存在，清理锁文件
                    os.remove(LOCK_FILE_PATH)
                    return False
            except ImportError:
                # 如果没有psutil，使用更简单的检查
                try:
                    os.kill(lock_pid, 0)  # 发送0信号检查进程
                    return True
                except (ProcessLookupError, OSError):
                    # 进程不存在，清理锁文件
                    os.remove(LOCK_FILE_PATH)
                    return False
        else:  # Unix/Linux/Mac
            try:
                os.kill(lock_pid, 0)  # 发送0信号检查进程
                return True
            except (ProcessLookupError, OSError):
                # 进程不存在，清理锁文件
                os.remove(LOCK_FILE_PATH)
                return False
                
    except (ValueError, IOError, OSError):
        # 读取文件失败或格式错误，清理锁文件
        try:
            os.remove(LOCK_FILE_PATH)
        except:
            pass
        return False

def create_lock_file():
    """创建锁文件"""
    try:
        with open(LOCK_FILE_PATH, "w") as f:
            f.write(str(os.getpid()))
        return True
    except IOError:
        return False

def remove_lock_file():
    """移除锁文件"""
    try:
        if os.path.exists(LOCK_FILE_PATH):
            os.remove(LOCK_FILE_PATH)
    except IOError:
        pass

if __name__ == "__main__":
    if is_already_running():
        messagebox.showinfo("提示", "日历应用已在运行中。")
        sys.exit(0)
    
    if not create_lock_file():
        messagebox.showerror("错误", "无法创建锁文件，应用可能无法正常启动或防止多开。")
        sys.exit(1)

    root = tk.Tk()
    app = CalendarApp(root)
    
    # 创建自定义样式
    style = ttk.Style()
    style.configure("Selected.TFrame", background="#4f4f4f")
    
    # 启动提醒检查
    app.check_reminders()
    
    # 确保在程序退出时移除锁文件
    import atexit
    atexit.register(remove_lock_file)
    
    root.mainloop()