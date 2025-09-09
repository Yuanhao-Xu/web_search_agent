"""Web搜索Agent API服务 - 完整流式支持"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, AsyncGenerator, List, Dict, Any
import json

from web_search_agent_0908 import WebSearchAgent

# ============================================
# 数据模型
# ============================================

class ChatRequest(BaseModel):
   """聊天请求"""
   session_id: str = Field(..., description="会话标识符")
   message: str = Field(..., description="用户问题")
   tool_choice: str = Field("auto", description="工具选择模式: none/auto/required")
   max_tool_calls: int = Field(3, ge=0, le=10, description="最大工具调用次数")
   stream: bool = Field(True, description="是否流式输出")
   reset_session: bool = Field(False, description="是否重置会话历史")
   include_history: bool = Field(True, description="是否返回完整历史")
   include_tool_details: bool = Field(True, description="是否返回工具调用详情")

class ConversationStats(BaseModel):
   """对话统计"""
   total_turns: int
   user_messages: int
   assistant_messages: int
   tool_calls_total: int
   tool_calls_current: int

class ToolCall(BaseModel):
   """工具调用详情"""
   tool_name: str
   query: str

class Message(BaseModel):
   """消息"""
   role: str
   content: str
   tool_calls: Optional[List[ToolCall]] = None

class ChatResponse(BaseModel):
   """聊天响应"""
   success: bool
   final_answer: str
   session_id: str
   conversation_stats: ConversationStats
   session_created: bool
   conversation_history: Optional[List[Message]] = None
   tool_results: Optional[List[ToolCall]] = None

# ============================================
# API服务
# ============================================

app = FastAPI(title="Web搜索Agent API")
sessions: Dict[str, WebSearchAgent] = {}

def get_api_key(authorization: str = Header(...)) -> str:
   """提取API密钥"""
   if not authorization.startswith("Bearer "):
       raise HTTPException(401, "Invalid authorization")
   return authorization[7:]

def get_or_create_session(request: ChatRequest, api_key: str):
   """获取或创建会话"""
   session_id = request.session_id
   session_existed = session_id in sessions
   
   # 重置会话（如果需要）
   if request.reset_session:
       if session_id in sessions:
           del sessions[session_id]
       session_existed = False
   
   # 获取或创建会话
   session = sessions.get(session_id)
   if not session:
       session = WebSearchAgent(
           api_key=api_key,
           tool_choice=request.tool_choice,
           max_tool_calls=request.max_tool_calls
       )
       sessions[session_id] = session
   
   return session, session_existed

def _build_conversation_stats(session) -> ConversationStats:
   """构建对话统计"""
   history = session.llm.get_history()
   user_messages = len([msg for msg in history if msg["role"] == "user"])
   assistant_messages = len([msg for msg in history if msg["role"] == "assistant"])
   tool_calls_total = len([msg for msg in history if msg["role"] == "tool"])
   
   return ConversationStats(
       total_turns=len(history),
       user_messages=user_messages,
       assistant_messages=assistant_messages,
       tool_calls_total=tool_calls_total,
       tool_calls_current=session.tool_call_count
   )

def _build_conversation_history(session) -> List[Message]:
   """构建对话历史"""
   history = session.llm.get_history()
   messages = []
   
   for msg in history:
       # 处理content字段，确保不为None
       content = msg.get("content")
       if content is None:
           if msg["role"] == "tool":
               content = "<Tool Result>"
           elif msg.get("tool_calls"):
               content = "<Tool Call>"
           else:
               content = ""
       
       # 处理tool_calls字段
       tool_calls = None
       if msg.get("tool_calls") and isinstance(msg["tool_calls"], list):
           tool_calls = []
           for tc in msg["tool_calls"]:
               try:
                   args = json.loads(tc["function"]["arguments"])
                   query = args.get("query", "")
               except (json.JSONDecodeError, KeyError):
                   query = ""
               
               tool_calls.append(ToolCall(
                   tool_name=tc["function"]["name"],
                   query=query
               ))
       
       messages.append(Message(
           role=msg["role"],
           content=content,
           tool_calls=tool_calls
       ))
   
   return messages

async def stream_chat(request: ChatRequest, api_key: str) -> AsyncGenerator[str, None]:
   """SSE流式响应"""
   try:
       session, session_existed = get_or_create_session(request, api_key)
       
       # 发送会话信息
       yield f"data: {json.dumps({'type': 'session', 'id': request.session_id, 'created': not session_existed})}\n\n"
       
       # 流式处理消息
       async for chunk in session.process_message_stream(request.message):
           yield f"data: {json.dumps({'type': chunk['type'], 'data': chunk['data']})}\n\n"
   
   except Exception as e:
       yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

@app.post("/chat")
async def chat(request: ChatRequest, api_key: str = Header(..., alias="Authorization")):
   """统一聊天接口 - 自动处理流式/非流式"""
   api_key = get_api_key(api_key)
   
   if request.stream:
       return StreamingResponse(
           stream_chat(request, api_key),
           media_type="text/event-stream",
           headers={"Cache-Control": "no-cache"}
       )
   else:
       # 非流式：直接使用WebSearchAgent的非流式方法
       session, session_existed = get_or_create_session(request, api_key)
       
       # 直接调用非流式方法
       final_answer = await session.process_message(request.message)
       
       # 构建响应
       conversation_stats = _build_conversation_stats(session)
       conversation_history = _build_conversation_history(session) if request.include_history else None
       
       return ChatResponse(
           success=True,
           final_answer=final_answer,
           session_id=request.session_id,
           conversation_stats=conversation_stats,
           session_created=not session_existed,
           conversation_history=conversation_history,
           tool_results=None  # 非流式模式下不提供工具详情
       )

@app.get("/session/{session_id}/history")
async def get_history(session_id: str):
   """获取会话历史"""
   session = sessions.get(session_id)
   if not session:
       raise HTTPException(404, "Session not found")
   
   conversation_history = _build_conversation_history(session)
   conversation_stats = _build_conversation_stats(session)
   
   return {
       "success": True,
       "session_id": session_id,
       "conversation_stats": conversation_stats,
       "conversation_history": conversation_history
   }

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
   """删除会话"""
   if session_id not in sessions:
       raise HTTPException(404, "Session not found")
   
   del sessions[session_id]
   return {"success": True, "message": "Session deleted", "session_id": session_id}

if __name__ == "__main__":
   import uvicorn
   uvicorn.run(app, host="0.0.0.0", port=8000)