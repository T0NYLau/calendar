# AI助手功能使用说明

## 功能概述

日历应用现已集成AI助手功能，支持接入各种LLM模型，包括您提供的API配置。

## 配置说明

### 基础URI设置
- **界面填写**：`https://api.hdgsb.com/v1`
- **实际请求**：`https://api.hdgsb.com/v1/chat/completions`
- **说明**：界面中只需填写基础URI，系统会自动拼接 `/chat/completions` 路径

### 配置参数
- **配置名称**：自定义名称，用于区分不同配置
- **基础URI**：API服务的基础地址
- **模型名称**：如 `qwen3-coder-480b-a35b-instruct`
- **API密钥**：您的API密钥，如 `sk-cgGZf8w2Aa9O3LjETVv`
- **温度系数**：控制AI回复的随机性（0.0-2.0）

## 使用步骤

### 1. 启动应用
```bash
python calendar_app.py
```

### 2. 打开AI助手
- 点击主界面右上角的 **"AI助手"** 按钮
- 弹出配置对话框，包含两个选项卡

### 3. 配置AI模型
在 **"配置管理"** 选项卡中：

#### 添加新配置
1. 点击 **"添加配置"** 按钮
2. 填写配置信息：
   - **配置名称**：如 "默认AI助手"
   - **基础URI**：`https://api.hdgsb.com/v1`
   - **模型名称**：`qwen3-coder-480b-a35b-instruct`
   - **API密钥**：您的API密钥
   - **温度系数**：建议0.7
   - **设为默认配置**：勾选此项
3. 点击 **"保存"** 按钮

#### 管理配置
- **编辑配置**：选择配置后点击"编辑配置"
- **删除配置**：选择配置后点击"删除配置"
- **设为默认**：选择配置后点击"设为默认"

### 4. 开始对话
在 **"AI聊天"** 选项卡中：

1. 在输入框中输入您的问题
2. 支持多行输入：
   - **Shift+Enter**：换行
   - **Enter**：发送消息
   - **Ctrl+Enter**：发送消息
3. 点击 **"发送"** 按钮或按Enter键发送
4. 点击 **"清空"** 按钮清空输入框
5. 等待AI回复
6. 继续对话


# 日历应用AI助手搜索功能使用说明

## 功能说明
AI助手现已集成联网搜索功能，可以通过Search1API获取实时信息。

## 触发方式
支持多种搜索前缀格式：
- **中文搜索**：以"搜索"开头，如"搜索今天广州天气"
- **英文搜索**：以"search"开头，如"search weather in Guangzhou today"
- **带冒号格式**：支持"搜索:"或"search:"前缀

## 使用示例
- 搜索今天广州天气
- 搜索最新科技新闻
- 搜索2024年奥运会
- search latest stock market news
- 搜索:Python编程教程

## 注意事项
1. **必须包含搜索前缀**：消息必须以"搜索"或"search"开头
2. **网络要求**：需要稳定的互联网连接
3. **结果限制**：每次返回最多10条相关结果
4. **响应时间**：搜索可能需要3-5秒完成

## 故障排除
如果搜索功能无法正常工作：
1. 检查网络连接是否正常
2. 确认消息以"搜索"或"search"开头
3. 查看终端输出中的调试信息
4. 尝试使用测试脚本：python test_search.py

## 技术细节
- **API提供商**：Search1API
- **搜索服务**：Google搜索集成
- **结果格式**：标题、URL、摘要
- **超时设置**：10秒
- **结果限制**：最多10条




# 免费搜索API推荐

## 1. Brave Search API  
- **特点**：Google 级质量、无广告、支持 JSON + 摘要片段  
- **免费额度**：每月 2 000 次查询（QPS 5）  
- **申请**：https://api.search.brave.com/app/dashboard → Sign up → 生成 key  
- **curl 示例**  
```bash
curl -H "X-Subscription-Token: YOUR_BRAVE_API_KEY" \
     "https://api.search.brave.com/res/v1/web/search?q=gpt-4o+release+date&count=10"
```
- **返回字段**：`title, url, description, age, language` 等

---

## 2. Bing Web Search v7（Microsoft Azure 认知服务）  
- **特点**：微软自家 Bing 索引，支持安全搜索、mkt 地域限制  
- **免费额度**：F0 层每月 3 000 次（QPS 3）  
- **申请**：Azure Portal → 创建「Bing Search v7」资源 → 选 F0 → 拿 Key  
- **curl 示例**  
```bash
curl "https://api.bing.microsoft.com/v7.0/search?q=quantum+computer+news&mkt=en-US" \
     -H "Ocp-Apim-Subscription-Key: YOUR_BING_KEY"
```

## 3. Jina.ai Reader Search  
- **特点**：标榜「给 LLM 用的搜索引擎」，直接返回纯净 Markdown；支持中文  
- **免费额度**：无需注册，默认 200 req/day；注册后可申请 10 000 req/day  
- **curl 示例**  
```bash
curl "https://s.jina.ai/q=上海天气怎么样"
```
## 4. You.com API（自建索引+实时抓取）  
- **免费额度**：每月 1 000 次（需邮件申请 developer key）  
- **申请**：https://platform.you.com → Join Waitlist → 收到 key  
- **curl 示例**  
```bash
curl "https://api.ydc-index.io/search?query=2024+eclipse+path" \
     -H "X-API-Key: YOUR_YDC_KEY"
```

---

## 5. Tavily Search（专为 RAG 设计）  
- **特点**：返回「question_focused_snippet」，可直接喂给 LLM  
- **免费额度**：每月 1 000 次（注册即送）  
- **申请**：https://tavily.com → Dashboard → 生成 key  
- **curl 示例**  
```bash
curl -X POST https://api.tavily.com/search \
     -H "Content-Type: application/json" \
     -d '{"api_key":"YOUR_TAVILY_KEY","query":"OpenAI o1 model release","max_results":3}'
```

---