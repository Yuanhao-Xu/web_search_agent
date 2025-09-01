"""
Web搜索智能体服务配置文件
"""

import os
from typing import List

# 服务配置
SERVICE_CONFIG = {
    "title": "智能搜索助手API",
    "description": "基于大模型的智能搜索和问答服务",
    "version": "1.0.0",
    "host": os.getenv("SERVICE_HOST", "0.0.0.0"),
    "port": int(os.getenv("SERVICE_PORT", "8000")),
    "debug": os.getenv("SERVICE_DEBUG", "true").lower() == "true"
}

# API密钥配置
API_KEYS = {
    os.getenv("API_KEY_1", "sk-test-key-1"): "user1",
    os.getenv("API_KEY_2", "sk-test-key-2"): "user2",
    os.getenv("API_KEY_ADMIN", "sk-admin-key"): "admin"
}

# 大模型配置
LLM_CONFIG = {
    "api_key": os.getenv("DEEPSEEK_API_KEY", "sk-f5889d58c6db4dd38ca78389a6c7a7e8"),
    "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    "temperature": float(os.getenv("DEEPSEEK_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("DEEPSEEK_MAX_TOKENS", "4096"))
}

# Tavily搜索配置
TAVILY_CONFIG = {
    "api_key": os.getenv("TAVILY_API_KEY", "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")
}

# 日志配置
LOG_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "file": os.getenv("LOG_FILE", "service.log"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}

# CORS配置
CORS_CONFIG = {
    "allow_origins": os.getenv("CORS_ORIGINS", "*").split(","),
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"]
}

# 限流配置
RATE_LIMIT_CONFIG = {
    "max_requests_per_minute": int(os.getenv("MAX_REQUESTS_PER_MINUTE", "100"))
}

# 工具配置
TOOL_CONFIG = {
    "max_tool_calls": 5,
    "default_max_results": 3
}

# 测试配置
TEST_CONFIG = {
    "base_url": "http://localhost:8000",
    "api_key": "sk-test-key-1",
    "timeout": 30
}
