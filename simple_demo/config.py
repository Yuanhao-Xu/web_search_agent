# API配置
# 请将以下值替换为您的实际API密钥

DEEPSEEK_API_KEY = "your_deepseek_api_key_here"
TAVILY_API_KEY = "your_tavily_api_key_here"

# 或者从环境变量读取（如果设置了的话）
import os

if os.getenv("DEEPSEEK_API_KEY"):
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    
if os.getenv("TAVILY_API_KEY"):
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
