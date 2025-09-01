"""
FastAPI搜索智能体服务
封装LLM和Tavily搜索工具为REST API服务
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import asyncio
import uvicorn
import hashlib
import time
from datetime import datetime
import json

# 导入现有模块
from llm import LLM
from main import tavily_search, tools, optimized_multi_round_chat

# ============================================
# 数据模型
# ============================================

class ChatRequest(BaseModel):
    """聊天请求模型"""
    query: str = Field(..., description="用户查询内容")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    max_tool_calls: Optional[int] = Field(5, description="最大工具调用次数")
    stream: Optional[bool] = Field(False, description="是否流式输出")
    temperature: Optional[float] = Field(0.7, description="温度参数")
    max_tokens: Optional[int] = Field(4096, description="最大tokens")

class ChatResponse(BaseModel):
    """聊天响应模型"""
    answer: str = Field(..., description="智能体回答")
    tool_calls: Optional[List[Dict]] = Field(None, description="工具调用记录")
    timestamp: str = Field(..., description="响应时间戳")
    duration: float = Field(..., description="处理耗时(秒)")

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    service: str = "Search Agent API"
    timestamp: str

# ============================================
# API密钥验证
# ============================================

# 简单的API密钥存储（生产环境应使用数据库）
API_KEYS = {
    "test_key_123": {"name": "测试用户", "created": "2025-01-01"},
    "dev_key_456": {"name": "开发用户", "created": "2025-01-01"}
}

# 安全验证
security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证API密钥"""
    token = credentials.credentials
    
    # 简单验证（生产环境应加密存储和比对）
    if token not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return API_KEYS[token]

# ============================================
# FastAPI应用
# ============================================

app = FastAPI(
    title="Search Agent API",
    description="基于LLM和Tavily的智能搜索代理服务",
    version="1.0.0"
)

# 全局LLM实例（可考虑使用连接池）
llm_instance = None

@app.on_event("startup")
async def startup_event():
    """启动时初始化LLM实例"""
    global llm_instance
    llm_instance = LLM(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        stream=False,
        temperature=0.7,
        max_tokens=4096
    )
    print("✅ LLM实例初始化成功")

# ============================================
# API端点
# ============================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        service="Search Agent API",
        timestamp=datetime.now().isoformat()
    )

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    user_info: dict = Depends(verify_api_key)
):
    """
    智能聊天端点，支持搜索工具调用
    
    需要Bearer Token认证
    """
    start_time = time.time()
    
    try:
        # 工具函数映射
        tool_functions = {
            "tavily_search": tavily_search
        }
        
        # 记录工具调用
        tool_call_records = []
        
        # 自定义回调来记录工具调用
        original_search = tool_functions["tavily_search"]
        async def search_with_logging(*args, **kwargs):
            result = await original_search(*args, **kwargs)
            tool_call_records.append({
                "tool": "tavily_search",
                "args": kwargs,
                "timestamp": datetime.now().isoformat()
            })
            return result
        
        tool_functions["tavily_search"] = search_with_logging
        
        # 执行智能对话
        result = await optimized_multi_round_chat(
            llm_instance=llm_instance,
            user_input=request.query,
            tools=tools,
            tool_functions=tool_functions,
            system_prompt=request.system_prompt,
            max_tool_calls=request.max_tool_calls
        )
        
        # 计算耗时
        duration = time.time() - start_time
        
        return ChatResponse(
            answer=result,
            tool_calls=tool_call_records if tool_call_records else None,
            timestamp=datetime.now().isoformat(),
            duration=round(duration, 2)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求时出错: {str(e)}"
        )

@app.post("/search", response_model=Dict)
async def search_endpoint(
    query: str,
    max_results: int = 3,
    user_info: dict = Depends(verify_api_key)
):
    """
    直接搜索端点，仅调用Tavily搜索
    
    需要Bearer Token认证
    """
    try:
        result = await tavily_search(query, max_results)
        return {
            "query": query,
            "results": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {str(e)}"
        )

# ============================================
# 测试代码
# ============================================

async def test_api():
    """API测试函数"""
    import httpx
    
    base_url = "http://localhost:8000"
    headers = {"Authorization": "Bearer test_key_123"}
    
    async with httpx.AsyncClient() as client:
        print("="*60)
        print("API测试开始")
        print("="*60)
        
        # 1. 健康检查
        print("\n1. 测试健康检查...")
        response = await client.get(f"{base_url}/health")
        print(f"状态: {response.status_code}")
        print(f"响应: {response.json()}")
        
        # 2. 测试认证失败
        print("\n2. 测试无效认证...")
        try:
            response = await client.post(
                f"{base_url}/chat",
                json={"query": "测试"},
                headers={"Authorization": "Bearer invalid_key"}
            )
        except httpx.HTTPStatusError:
            print("✅ 认证失败测试通过")
        
        # 3. 测试普通问题（不需要搜索）
        print("\n3. 测试普通问题...")
        response = await client.post(
            f"{base_url}/chat",
            json={
                "query": "Python是什么编程语言？",
                "max_tool_calls": 3
            },
            headers=headers
        )
        print(f"状态: {response.status_code}")
        result = response.json()
        print(f"回答: {result['answer'][:200]}...")
        print(f"工具调用: {result.get('tool_calls', '无')}")
        
        # 4. 测试需要搜索的问题
        print("\n4. 测试搜索问题...")
        response = await client.post(
            f"{base_url}/chat",
            json={
                "query": "今天上海的天气怎么样？",
                "max_tool_calls": 3
            },
            headers=headers
        )
        result = response.json()
        print(f"回答: {result['answer'][:200]}...")
        print(f"工具调用数: {len(result.get('tool_calls', []))}")
        
        # 5. 测试直接搜索
        print("\n5. 测试直接搜索...")
        response = await client.post(
            f"{base_url}/search?query=Python最新版本&max_results=2",
            headers=headers
        )
        result = response.json()
        print(f"搜索结果预览: {result['results'][:200]}...")
        
        print("\n" + "="*60)
        print("✅ 所有测试完成")
        print("="*60)

# ============================================
# 启动服务
# ============================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 运行测试
        print("运行API测试...")
        asyncio.run(test_api())
    else:
        # 启动服务
        print("启动FastAPI服务...")
        print("文档地址: http://localhost:8000/docs")
        print("测试命令: python api_service.py test")
        print("-"*40)
        print("测试API密钥:")
        print("  - test_key_123")
        print("  - dev_key_456")
        print("-"*40)
        
        uvicorn.run(
            "api_service:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )