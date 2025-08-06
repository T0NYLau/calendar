#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Search1API搜索功能的独立脚本
运行此脚本来验证API是否正常工作
"""

import requests
import json

def test_search1api():
    """测试Search1API搜索功能"""
    print("正在测试Search1API搜索功能...")
    
    try:
        API_URL = "https://api.search1api.com/search"
        
        # 测试查询
        test_queries = [
            "今天广州市黄埔区天气",
            "最新科技新闻",
            "人工智能发展"
        ]
        
        for query in test_queries:
            print(f"\n测试查询: {query}")
            
            data = {
                "query": query,
                "search_service": "google",
                "max_results": 3,
                "crawl_results": 0,
                "image": False,
                "language": "zh",
                "time_range": "day"
            }
            
            headers = {
                "Content-Type": "application/json",
                'Authorization': 'Bearer 80FA665F-208A-47E1-98D5-D694DC6689BE'
            }
            
            try:
                response = requests.post(
                    API_URL,
                    headers=headers,
                    json=data,
                    timeout=10
                )
                
                print(f"状态码: {response.status_code}")
                
                if response.status_code == 200:
                    results = response.json()
                    print(f"成功获取 {len(results.get('results', []))} 个结果")
                    
                    # 打印前2个结果
                    for i, result in enumerate(results.get('results', [])[:2]):
                        print(f"  {i+1}. {result.get('title', '无标题')}")
                        print(f"     {result.get('link', '无链接')}")
                else:
                    print(f"请求失败: {response.text}")
                    
            except requests.exceptions.Timeout:
                print("请求超时")
            except requests.exceptions.RequestException as e:
                print(f"网络错误: {e}")
            except Exception as e:
                print(f"其他错误: {e}")
                
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    test_search1api()
    print("\n测试完成！")