# Web搜索智能体服务

基于您的大模型基类和主程序，封装而成的Web搜索智能体服务。使用FastAPI框架提供RESTful API接口，支持智能搜索、多轮对话和工具调用。

## 🚀 功能特性

- **智能搜索**: 基于Tavily搜索工具的智能网络搜索
- **多轮对话**: 支持上下文记忆的多轮对话
- **工具调用**: 自动判断是否需要搜索，智能调用工具
- **流式输出**: 支持流式和非流式两种输出模式
- **API认证**: Bearer Token认证机制
- **健康检查**: 服务状态监控
- **完整测试**: 包含全面的测试代码

## 📁 文件结构

```
web_search_agent/
├── web_search_agent_service.py  # 主服务文件
├── test_service.py              # 测试代码
├── requirements.txt             # 依赖包列表
├── start_service.bat           # Windows启动脚本
├── start_service.sh            # Linux/Mac启动脚本
├── run_tests.bat               # Windows测试脚本
├── run_tests.sh                # Linux/Mac测试脚本
├── README_Service.md           # 服务说明文档
├── llm.py                      # 大模型基类（原文件）
└── main.py                     # 主程序（原文件）
```

## 🛠️ 安装和配置

### 1. 环境要求

- Python 3.8+
- 网络连接（用于Tavily搜索）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置API密钥

在 `web_search_agent_service.py` 中配置：

```python
# API密钥配置
API_KEYS = {
    "sk-test-key-1": "user1",
    "sk-test-key-2": "user2",
    "sk-admin-key": "admin"
}

# 大模型配置
LLM_CONFIG = {
    "api_key": "your-deepseek-api-key",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 4096
}
```

## 🚀 启动服务

### Windows
```cmd
start_service.bat
```

### Linux/Mac
```bash
chmod +x start_service.sh
./start_service.sh
```

### 手动启动
```bash
python web_search_agent_service.py
```

服务启动后，访问：
- 服务地址: http://localhost:8000
- API文档: http://localhost:8000/docs
- 交互式文档: http://localhost:8000/redoc

## 📚 API接口

### 1. 健康检查
```http
GET /health
```

### 2. 聊天接口（非流式）
```http
POST /chat
Authorization: Bearer sk-test-key-1
Content-Type: application/json

{
    "message": "今天北京的天气怎么样？",
    "stream": false,
    "max_tool_calls": 3,
    "system_prompt": "你是一个天气专家"
}
```

### 3. 聊天接口（流式）
```http
POST /chat/stream
Authorization: Bearer sk-test-key-1
Content-Type: application/json

{
    "message": "介绍一下人工智能的发展历史",
    "stream": true,
    "max_tool_calls": 2
}
```

### 4. 直接搜索
```http
POST /search
Authorization: Bearer sk-test-key-1
Content-Type: application/json

{
    "query": "Python编程语言",
    "max_results": 3
}
```

### 5. 获取可用工具
```http
GET /tools
```

## 🧪 运行测试

### Windows
```cmd
run_tests.bat
```

### Linux/Mac
```bash
chmod +x run_tests.sh
./run_tests.sh
```

### 手动测试
```bash
python test_service.py
```

## 📊 测试用例

测试程序包含以下测试用例：

1. **健康检查测试** - 验证服务状态
2. **根端点测试** - 验证基础API
3. **工具端点测试** - 验证工具可用性
4. **认证测试** - 验证API密钥验证
5. **直接搜索测试** - 验证搜索功能
6. **聊天测试-常识问题** - 验证无需搜索的问题
7. **聊天测试-需要搜索的问题** - 验证需要搜索的问题
8. **流式聊天测试** - 验证流式输出
9. **自定义系统提示测试** - 验证自定义提示词

## 🔐 认证机制

服务使用Bearer Token认证：

```python
headers = {
    "Authorization": "Bearer sk-test-key-1",
    "Content-Type": "application/json"
}
```

预配置的测试密钥：
- `sk-test-key-1` → `user1`
- `sk-test-key-2` → `user2`
- `sk-admin-key` → `admin`

## ⚙️ 配置选项

### 服务配置
```python
SERVICE_CONFIG = {
    "title": "智能搜索助手API",
    "description": "基于大模型的智能搜索和问答服务",
    "version": "1.0.0",
    "host": "0.0.0.0",
    "port": 8000,
    "debug": True
}
```

### 大模型配置
```python
LLM_CONFIG = {
    "api_key": "your-api-key",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 4096
}
```

## 🔧 自定义和扩展

### 添加新工具

1. 在 `main.py` 中定义新工具函数
2. 在 `tools` 列表中添加工具schema
3. 在 `SearchAgentService.tool_functions` 中注册工具

### 修改系统提示词

在 `SearchAgentService.chat_with_search` 方法中修改 `optimized_system_prompt`。

### 添加新的API端点

在 `web_search_agent_service.py` 中添加新的路由函数。

## 🐛 故障排除

### 常见问题

1. **服务启动失败**
   - 检查端口8000是否被占用
   - 检查Python环境和依赖包

2. **API调用失败**
   - 检查API密钥是否正确
   - 检查服务是否正在运行

3. **搜索功能异常**
   - 检查网络连接
   - 检查Tavily API密钥

4. **大模型调用失败**
   - 检查DeepSeek API密钥
   - 检查网络连接

### 日志查看

服务运行时会输出详细日志，包括：
- 服务启动信息
- API调用记录
- 工具执行日志
- 错误信息

## 📈 性能优化

### 建议配置

1. **调整max_tool_calls**: 根据问题复杂度设置合适的工具调用次数
2. **使用流式输出**: 对于长回答，使用流式输出提升用户体验
3. **缓存机制**: 对于重复问题，可以实现结果缓存

### 监控指标

- 响应时间
- 工具调用次数
- 成功率
- 错误率

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进服务！

## 📄 许可证

本项目基于您现有的代码，请遵循相应的许可证条款。

## 📞 支持

如有问题，请：
1. 查看本文档
2. 检查日志输出
3. 运行测试程序
4. 提交Issue描述问题
