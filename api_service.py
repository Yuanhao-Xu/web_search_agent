"""Web搜索Agent API服务 - 完整流式支持"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, AsyncGenerator, List, Dict, Any
import json
import uuid
from datetime import datetime

from web_search_agent_0908 import SessionManager, ToolMode

# ============================================
# 数据模型
# ============================================

class ChatRequest(BaseModel):
   """聊天请求"""
   session_id: str = Field(..., description="会话标识符，用于多轮对话")
   message: str = Field(..., description="用户问题")
   tool_mode: str = Field("auto", description="工具调用模式: never/auto/always")
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
   result_count: int
   execution_time: float

class Message(BaseModel):
   """消息"""
   role: str
   content: str
   timestamp: str
   message_id: str
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
session_manager = SessionManager()

def get_api_key(authorization: str = Header(...)) -> str:
   """提取API密钥"""
   if not authorization.startswith("Bearer "):
       raise HTTPException(401, "Invalid authorization")
   return authorization[7:]

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
   
   for i, msg in enumerate(history):
       message_id = f"msg_{i+1:03d}"
       timestamp = datetime.now().isoformat() + "Z"
       
       # 处理content字段，确保不为None
       content = msg.get("content")
       if content is None:
           if msg["role"] == "tool":
               content = "<工具执行结果>"
           elif msg.get("tool_calls"):
               content = "<工具调用>"
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
                   query=query,
                   result_count=1,
                   execution_time=0.5
               ))
       
       messages.append(Message(
           role=msg["role"],
           content=content,
           timestamp=timestamp,
           message_id=message_id,
           tool_calls=tool_calls
       ))
   
   return messages

async def stream_chat(request: ChatRequest, api_key: str) -> AsyncGenerator[str, None]:
   """SSE流式响应 - 完整事件支持"""
   try:
       session_id = request.session_id
       session_existed = session_manager.get_session(session_id) is not None
       
       # 重置会话（如果需要）
       if request.reset_session:
           session_manager.delete_session(session_id)
           session_existed = False
       
       # 获取或创建会话
       session = session_manager.get_session(session_id)
       if not session:
           session = session_manager.create_session(
               session_id, api_key,
               tool_mode=ToolMode(request.tool_mode),
               max_tool_calls=request.max_tool_calls
           )
       
       # 发送会话信息
       yield f"data: {json.dumps({'type': 'session', 'id': session_id, 'created': not session_existed})}\n\n"
       
       # 流式处理消息
       async for chunk in session.process_message_stream(request.message):
           if chunk["type"] == "assistant_content":
               yield f"data: {json.dumps({'type': 'text', 'data': chunk['data']})}\n\n"
           
           elif chunk["type"] == "tool_execution_start":
               yield f"data: {json.dumps({'type': 'tool_start', 'data': chunk['data']})}\n\n"
           
           elif chunk["type"] == "tool_executing":
               yield f"data: {json.dumps({'type': 'tool_executing', 'data': chunk['data']})}\n\n"
           
           elif chunk["type"] == "tool_result":
               yield f"data: {json.dumps({'type': 'tool_result', 'data': chunk['data']})}\n\n"
           
           elif chunk["type"] == "tool_error":
               yield f"data: {json.dumps({'type': 'tool_error', 'data': chunk['data']})}\n\n"
           
           elif chunk["type"] == "tool_limit_reached":
               yield f"data: {json.dumps({'type': 'tool_limit', 'data': chunk['data']})}\n\n"
           
           elif chunk["type"] == "final_answer_start":
               yield f"data: {json.dumps({'type': 'final_start', 'data': chunk['data']})}\n\n"
           
           elif chunk["type"] == "system_message":
               yield f"data: {json.dumps({'type': 'system', 'data': chunk['data']})}\n\n"
           
           elif chunk["type"] == "complete":
               yield f"data: {json.dumps({'type': 'done', 'data': chunk['data']})}\n\n"
           
           elif chunk["type"] == "error":
               yield f"data: {json.dumps({'type': 'error', 'data': chunk['data']})}\n\n"
   
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
       # 非流式：收集流式输出
       session_id = request.session_id
       session_existed = session_manager.get_session(session_id) is not None
       
       # 重置会话（如果需要）
       if request.reset_session:
           session_manager.delete_session(session_id)
           session_existed = False
       
       # 获取或创建会话
       session = session_manager.get_session(session_id)
       if not session:
           session = session_manager.create_session(
               session_id, api_key,
               tool_mode=ToolMode(request.tool_mode),
               max_tool_calls=request.max_tool_calls
           )
       
       # 收集完整的流式输出
       full_content = []
       tool_results = []
       
       async for chunk in session.process_message_stream(request.message):
           if chunk["type"] == "assistant_content":
               full_content.append(chunk["data"])
           elif chunk["type"] == "tool_result" and request.include_tool_details:
               tool_results.append(ToolCall(
                   tool_name=chunk["data"]["name"],
                   query=chunk["data"].get("query", ""),
                   result_count=1,
                   execution_time=0.5
               ))
           elif chunk["type"] == "complete":
               break
       
       # 构建响应
       conversation_stats = _build_conversation_stats(session)
       conversation_history = _build_conversation_history(session) if request.include_history else None
       
       return ChatResponse(
           success=True,
           final_answer="".join(full_content),
           session_id=session_id,
           conversation_stats=conversation_stats,
           session_created=not session_existed,
           conversation_history=conversation_history,
           tool_results=tool_results if request.include_tool_details else None
       )

@app.get("/session/{session_id}/history")
async def get_history(session_id: str):
   """获取会话历史"""
   session = session_manager.get_session(session_id)
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
   if not session_manager.delete_session(session_id):
       raise HTTPException(404, "Session not found")
   return {"success": True, "message": "Session deleted", "session_id": session_id}

if __name__ == "__main__":
   import uvicorn
   uvicorn.run(app, host="0.0.0.0", port=8000)