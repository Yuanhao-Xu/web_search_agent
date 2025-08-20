# Web Search Agent 简单演示

这是一个简单的网络搜索代理演示项目，使用 DeepSeek AI 和 Tavily 搜索服务。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置 API 密钥

您有三种方式配置 API 密钥：

### 方式1：使用 .env 文件（推荐）

1. 将 `env_example.txt` 重命名为 `.env`
2. 编辑 `.env` 文件，填入您的实际 API 密钥：
   ```
   DEEPSEEK_API_KEY=your_actual_deepseek_key
   TAVILY_API_KEY=your_actual_tavily_key
   ```

### 方式2：使用配置文件

编辑 `config.py` 文件，填入您的实际 API 密钥。

### 方式3：设置环境变量

在命令行中设置：
```bash
# Windows CMD
set DEEPSEEK_API_KEY=your_api_key_here
set TAVILY_API_KEY=your_api_key_here

# Windows PowerShell
$env:DEEPSEEK_API_KEY="your_api_key_here"
$env:TAVILY_API_KEY="your_api_key_here"
```

## 获取 API 密钥

### DeepSeek API 密钥
- 访问 [DeepSeek 平台](https://platform.deepseek.com/) 获取 API 密钥

### Tavily API 密钥
- 访问 [Tavily](https://tavily.com/) 获取搜索 API 密钥

## 运行项目

配置好 API 密钥后，运行：

```bash
python main_v1.py
```

## 功能说明

- 使用 Tavily 搜索获取相关信息
- 使用 DeepSeek AI 生成回答
- 支持异步操作，提高性能
- 自动加载 .env 文件中的环境变量

## 注意事项

- 请确保您的 API 密钥有效且有足够的配额
- `.env` 文件包含敏感信息，不要提交到版本控制系统
- 建议将 `.env` 添加到 `.gitignore` 文件中
- 代码会按以下优先级查找 API 密钥：
  1. 配置文件 (config.py)
  2. 环境变量 (.env 文件或系统环境变量)
