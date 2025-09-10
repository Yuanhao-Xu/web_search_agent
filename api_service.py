"""API服务层 - 基于轮次控制的简化版"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal
import json
import asyncio
from web_search_agent_0908 import WebSearchAgent

# ============================================
# 数据模型
# ============================================

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: str
    stream: bool = True
    max_rounds: int = 3
    tool_choice: Literal["auto", "required", "none"] = "auto"

class ChatResponse(BaseModel):
    """聊天响应模型"""
    success: bool
    answer: str
    session_id: str
    rounds_used: int

# ============================================
# API服务
# ============================================

app = FastAPI(title="Web Search Agent API", version="2.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 会话存储
sessions: Dict[str, WebSearchAgent] = {}

# DeepSeek API配置
API_KEY = "sk-f5889d58c6db4dd38ca78389a6c7a7e8"

# ============================================
# 辅助函数
# ============================================

def get_or_create_session(session_id: str, **kwargs) -> WebSearchAgent:
    """获取或创建会话"""
    if session_id not in sessions:
        # 注意：根据WebSearchAgent的实际构造函数参数调整
        sessions[session_id] = WebSearchAgent(
            api_key=API_KEY,
            max_rounds=kwargs.get('max_rounds', 3),  # 如果构造函数参数名不同，需要调整
            tool_choice=kwargs.get('tool_choice', 'auto'),
            stream=kwargs.get('stream', True)
        )
    return sessions[session_id]

async def stream_generator(agent: WebSearchAgent, message: str):
    """流式响应生成器"""
    try:
        async for chunk in agent.process_message_stream(message):
            # 只传输必要的事件类型
            if chunk["type"] in ["content", "tool_call", "tool_result", "error"]:
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        
        # 发送完成信号 - 使用 getattr 防止属性不存在
        rounds = getattr(agent, 'current_round', 0)
        yield f"data: {json.dumps({'type': 'done', 'rounds': rounds})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

# ============================================
# API端点
# ============================================

@app.get("/")
async def root():
    """根路径"""
    return {"name": "Web Search Agent API", "version": "2.0", "status": "running"}

@app.post("/chat")
async def chat(request: ChatRequest):
    """统一的聊天端点"""
    try:
        # 获取或创建会话
        agent = get_or_create_session(
            request.session_id,
            max_rounds=request.max_rounds,
            tool_choice=request.tool_choice,
            stream=request.stream
        )
        
        # 更新配置（使用 hasattr 检查方法是否存在）
        if hasattr(agent, 'max_rounds') and agent.max_rounds != request.max_rounds:
            if hasattr(agent, 'set_max_rounds'):
                agent.set_max_rounds(request.max_rounds)
            else:
                agent.max_rounds = request.max_rounds  # 直接设置属性
                
        if agent.tool_choice != request.tool_choice:
            agent.set_tool_choice(request.tool_choice)
        
        if request.stream:
            # 流式响应
            return StreamingResponse(
                stream_generator(agent, request.message),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            # 非流式响应
            answer = await agent.process_message(request.message)
            rounds = getattr(agent, 'current_round', 0)
            return ChatResponse(
                success=True,
                answer=answer,
                session_id=request.session_id,
                rounds_used=rounds
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """清除指定会话"""
    if session_id in sessions:
        sessions[session_id].reset_session()
        return {"success": True, "message": f"会话 {session_id} 已重置"}
    return {"success": False, "message": "会话不存在"}

@app.get("/sessions")
async def list_sessions():
    """列出所有活跃会话"""
    return {
        "total": len(sessions),
        "sessions": [
            {
                "id": sid,
                "max_rounds": getattr(agent, 'max_rounds', 3),
                "tool_choice": agent.tool_choice,
                "messages_count": len(agent.llm.conversation_history)
            }
            for sid, agent in sessions.items()
        ]
    }

@app.delete("/sessions")
async def clear_all_sessions():
    """清除所有会话"""
    count = len(sessions)
    sessions.clear()
    return {"success": True, "cleared": count}

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "active_sessions": len(sessions)
    }

# ============================================
# 启动服务
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)