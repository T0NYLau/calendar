
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
        js_code = f'{{"yi": lunar.Lunar.fromYmd({year}, {month}, {day}).getDayYi(), "ji": lunar.Lunar.fromYmd({year}, {month}, {day}).getDayJi()}}'
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
