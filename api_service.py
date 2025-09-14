"""
Web Search Agent API 服务
支持流式/非流式对话，用户会话管理
"""

from fastapi import FastAPI, HTTPException
from fastapi.datastructures import Headers
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import json
import logging

from llm import LLM
from tools import tool_functions, tools

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# 数据模型定义
# ============================================

class ChatRequest(BaseModel):
    """聊天请求模型 - 复用LLM类参数命名"""
    user_id: str                          
    message: str                          
    stream: bool = False                  
    temperature: Optional[float] = None   
    max_tokens: Optional[int] = None     
    max_tool_rounds: int = 3             # 复用LLM类中的参数名

class ChatResponse(BaseModel):
    """非流式响应模型"""
    user_id: str
    content: str                          # 复用LLM中的content命名
    conversation_history: List[Dict]      # 完整消息历史
    status: str = "success"

# ============================================
# 应用初始化
# ============================================

app = FastAPI(title="Web Search Agent API")

# 用户会话存储
user_sessions: Dict[str, LLM] = {}

# LLM配置
LLM_CONFIG = {
    "api_key": "sk-f5889d58c6db4dd38ca78389a6c7a7e8",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat"
}

# ============================================
# 核心函数
# ============================================

def get_or_create_user_session(user_id: str) -> LLM:
    """获取或创建用户会话"""
    if user_id not in user_sessions:
        logger.info(f"Creating new session for user: {user_id}")
        user_sessions[user_id] = LLM(**LLM_CONFIG)
        # 添加系统提示词
        user_sessions[user_id].add_message(
            "system", 
            "你是一个智能搜索助手，可以搜索最新的互联网信息来回答问题。"
        )
    return user_sessions[user_id]

# ============================================
# API端点
# ============================================

@app.post("/chat")
async def chat(request: ChatRequest):
    """统一聊天端点"""
    try:
        llm = get_or_create_user_session(request.user_id)
        
        if request.stream:
            # 流式响应
            async def generate():
                try:
                    async for chunk in llm.chat_stream(
                        user_input=request.message,
                        tools=tools,
                        tool_functions=tool_functions,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                        max_tool_rounds=request.max_tool_rounds
                    ):
                        # 转换为SSE格式
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    
                    # 发送历史记录作为最后一个事件
                    yield f"data: {json.dumps({'type': 'history', 'data': llm.get_history()}, ensure_ascii=False)}\n\n"
                    
                except Exception as e:
                    logger.error(f"Stream error for user {request.user_id}: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
                    
            return StreamingResponse(generate(), media_type="text/event-stream")
        
        else:
            # 非流式响应
            content = await llm.chat_complete(
                user_input=request.message,
                tools=tools,
                tool_functions=tool_functions,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                max_tool_rounds=request.max_tool_rounds,
                verbose=True  # 开启详细日志
            )
            
            return ChatResponse(
                user_id=request.user_id,
                content=content,
                conversation_history=llm.get_history()
            )
            
    except Exception as e:
        logger.error(f"Chat error for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/{user_id}")
async def clear_history(user_id: str):
    """清除用户历史"""
    if user_id in user_sessions:
        user_sessions[user_id].clear_history()
        # 重新添加系统提示词
        user_sessions[user_id].add_message(
            "system", 
            "你是一个智能搜索助手，可以搜索最新的互联网信息来回答问题。"
        )
        logger.info(f"History cleared for user: {user_id}")
        return {"message": "History cleared", "user_id": user_id}
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/chat/{user_id}/history") 
async def get_history(user_id: str):
    """获取用户历史"""
    if user_id in user_sessions:
        history = user_sessions[user_id].get_history()
        return {
            "user_id": user_id,
            "history": history,
            "message_count": len(history)
        }
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/")
async def root():
    """API根路径"""
    return {
        "service": "Web Search Agent API",
        "version": "1.0.0",
        "endpoints": [
            {"method": "POST", "path": "/chat", "description": "聊天接口"},
            {"method": "GET", "path": "/chat/{user_id}/history", "description": "获取历史"},
            {"method": "DELETE", "path": "/chat/{user_id}", "description": "清除历史"}
        ]
    }

# ============================================
# 启动入口
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_service:app", host="0.0.0.0", port=8000, reload=True)



"""
## 命令行启动
uvicorn api_service:app --reload --host 0.0.0.0 --port 8000

## URL
URL: http://localhost:8000/chat

## Headers
非流式
Content-Type: application/json
流式
Content-Type: application/json
Accept: text/event-stream

## 请求体示例

{
    "user_id": "user123",
    "message": "今天的天气怎么样？",
    "stream": false,
    "temperature": 0.7,
    "max_tokens": 1000,
    "max_tool_rounds": 3
}

## 获取历史记录GET
URL: http://localhost:8000/chat/user123/history
Content-Type: application/json

## 清除历史记录DELETE
Content-Type: application/json
http://localhost:8000/chat/user123
"""