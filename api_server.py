"""Web搜索Agent FastAPI服务"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid
import json
import asyncio
from datetime import datetime

from agent_session import AgentSession, SessionManager, ToolMode

# ============================================
# 数据模型定义
# ============================================

class ToolModeEnum(str, Enum):
    """工具模式枚举"""
    never = "never"
    auto = "auto"
    always = "always"

class SessionConfig(BaseModel):
    """会话配置"""
    api_key: str = Field(..., description="DeepSeek API密钥")
    tool_mode: ToolModeEnum = Field(default=ToolModeEnum.auto, description="工具调用模式")
    max_tool_calls: int = Field(default=3, ge=1, le=10, description="最大工具调用次数")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数")
    max_tokens: int = Field(default=4096, ge=100, le=8192, description="最大tokens")
    stream: bool = Field(default=True, description="是否流式输出")

class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    config: SessionConfig
    session_id: Optional[str] = Field(default=None, description="会话ID，不提供则自动生成")

class ChatRequest(BaseModel):
    """聊天请求"""
    session_id: str = Field(..., description="会话ID")
    message: str = Field(..., description="用户消息")
    stream: Optional[bool] = Field(default=None, description="是否流式输出(覆盖会话默认设置)")

class UpdateSessionRequest(BaseModel):
    """更新会话配置请求"""
    session_id: str = Field(..., description="会话ID")
    tool_mode: Optional[ToolModeEnum] = None
    max_tool_calls: Optional[int] = Field(default=None, ge=1, le=10)
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    stream: Optional[bool] = None

class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    created_at: str
    message_count: int
    tool_mode: str
    max_tool_calls: int
    stream: bool
    active: bool

# ============================================
# 增强的会话管理器
# ============================================

class EnhancedSessionManager(SessionManager):
    """增强的会话管理器，添加更多管理功能"""
    
    def __init__(self):
        super().__init__()
        self.session_metadata: Dict[str, Dict] = {}
    
    def create_session(self, session_id: str, api_key: str, **kwargs) -> AgentSession:
        """创建会话并记录元数据"""
        # 转换工具模式
        if 'tool_mode' in kwargs and isinstance(kwargs['tool_mode'], str):
            kwargs['tool_mode'] = ToolMode(kwargs['tool_mode'])
        
        session = super().create_session(session_id, api_key, **kwargs)
        
        # 记录元数据
        self.session_metadata[session_id] = {
            "created_at": datetime.now().isoformat(),
            "message_count": 0,
            "last_activity": datetime.now().isoformat()
        }
        
        return session
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        metadata = self.session_metadata.get(session_id, {})
        
        return SessionInfo(
            session_id=session_id,
            created_at=metadata.get("created_at", ""),
            message_count=metadata.get("message_count", 0),
            tool_mode=session.tool_mode.value,
            max_tool_calls=session.max_tool_calls,
            stream=session.llm.stream,
            active=session.session_active
        )
    
    def list_sessions(self) -> List[SessionInfo]:
        """列出所有会话"""
        sessions = []
        for session_id in self.sessions:
            info = self.get_session_info(session_id)
            if info:
                sessions.append(info)
        return sessions
    
    async def process_message(self, session_id: str, message: str, stream: Optional[bool] = None) -> Dict[str, Any]:
        """处理消息并更新元数据"""
        session = self.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 临时设置流式模式（如果指定）
        original_stream = session.llm.stream
        if stream is not None:
            session.llm.stream = stream
        
        try:
            # 处理消息
            response = await session.process_message(message)
            
            # 更新元数据
            if session_id in self.session_metadata:
                self.session_metadata[session_id]["message_count"] += 1
                self.session_metadata[session_id]["last_activity"] = datetime.now().isoformat()
            
            return {
                "success": True,
                "response": response,
                "session_id": session_id,
                "tool_calls": session.tool_call_count,
                "timestamp": datetime.now().isoformat()
            }
        finally:
            # 恢复原始流式设置
            session.llm.stream = original_stream

# ============================================
# FastAPI应用
# ============================================

app = FastAPI(
    title="Web搜索Agent API",
    description="基于DeepSeek和Tavily的智能搜索助手API",
    version="1.0.0"
)

# CORS配置（为前端开发准备）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局会话管理器
session_manager = EnhancedSessionManager()

# ============================================
# 会话管理接口
# ============================================

@app.post("/api/sessions/create", response_model=Dict[str, Any])
async def create_session(request: CreateSessionRequest):
    """创建新的聊天会话"""
    try:
        # 生成或使用提供的会话ID
        session_id = request.session_id or str(uuid.uuid4())
        
        # 检查会话是否已存在
        if session_manager.get_session(session_id):
            raise HTTPException(status_code=400, detail="会话ID已存在")
        
        # 创建会话
        config = request.config.dict()
        api_key = config.pop('api_key')
        
        session_manager.create_session(
            session_id=session_id,
            api_key=api_key,
            **config
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "会话创建成功",
            "config": config
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """获取会话信息"""
    info = session_manager.get_session_info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="会话不存在")
    return info

@app.get("/api/sessions", response_model=List[SessionInfo])
async def list_sessions():
    """列出所有会话"""
    return session_manager.list_sessions()

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    if not session_manager.delete_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True, "message": "会话已删除"}

@app.post("/api/sessions/{session_id}/reset")
async def reset_session(session_id: str):
    """重置会话（清空历史）"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    session.reset_session()
    
    # 重置消息计数
    if session_id in session_manager.session_metadata:
        session_manager.session_metadata[session_id]["message_count"] = 0
    
    return {"success": True, "message": "会话已重置"}

# ============================================
# 聊天接口
# ============================================

@app.post("/api/chat", response_model=Dict[str, Any])
async def chat(request: ChatRequest):
    """发送消息并获取回复（非流式）"""
    try:
        result = await session_manager.process_message(
            session_id=request.session_id,
            message=request.message,
            stream=False  # 强制非流式
        )
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/api/chat/stream")
async def chat_stream(websocket: WebSocket):
    """WebSocket流式聊天接口"""
    await websocket.accept()
    session_id = None
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            
            message_type = data.get("type")
            
            if message_type == "init":
                # 初始化连接
                session_id = data.get("session_id")
                if not session_manager.get_session(session_id):
                    await websocket.send_json({
                        "type": "error",
                        "message": "会话不存在"
                    })
                    break
                
                await websocket.send_json({
                    "type": "init_success",
                    "session_id": session_id
                })
            
            elif message_type == "message":
                # 处理聊天消息
                if not session_id:
                    await websocket.send_json({
                        "type": "error",
                        "message": "未初始化会话"
                    })
                    continue
                
                message = data.get("message", "")
                
                # 获取会话
                session = session_manager.get_session(session_id)
                if not session:
                    await websocket.send_json({
                        "type": "error",
                        "message": "会话已失效"
                    })
                    break
                
                # 设置为流式输出
                session.llm.stream = True
                
                # 发送开始标记
                await websocket.send_json({
                    "type": "start",
                    "timestamp": datetime.now().isoformat()
                })
                
                # 处理消息（这里需要自定义流式处理）
                try:
                    response = await session.process_message(message)
                    
                    # 发送完成的响应
                    await websocket.send_json({
                        "type": "complete",
                        "response": response,
                        "tool_calls": session.tool_call_count,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # 更新元数据
                    if session_id in session_manager.session_metadata:
                        session_manager.session_metadata[session_id]["message_count"] += 1
                        session_manager.session_metadata[session_id]["last_activity"] = datetime.now().isoformat()
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
    
    except WebSocketDisconnect:
        print(f"WebSocket断开连接: {session_id}")
    except Exception as e:
        print(f"WebSocket错误: {e}")

# ============================================
# 配置管理接口
# ============================================

@app.patch("/api/sessions/update")
async def update_session(request: UpdateSessionRequest):
    """更新会话配置"""
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    updates = {}
    
    if request.tool_mode is not None:
        session.set_tool_mode(ToolMode(request.tool_mode))
        updates["tool_mode"] = request.tool_mode
    
    if request.max_tool_calls is not None:
        session.set_max_tool_calls(request.max_tool_calls)
        updates["max_tool_calls"] = request.max_tool_calls
    
    if request.temperature is not None:
        session.llm.temperature = request.temperature
        updates["temperature"] = request.temperature
    
    if request.stream is not None:
        session.set_stream_mode(request.stream)
        updates["stream"] = request.stream
    
    return {
        "success": True,
        "message": "配置已更新",
        "updates": updates
    }

@app.get("/api/sessions/{session_id}/history")
async def get_history(session_id: str, limit: Optional[int] = None):
    """获取会话历史"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    history = session.llm.get_history()
    
    # 处理历史记录（简化工具调用和长内容）
    processed_history = []
    for msg in history[-limit:] if limit else history:
        processed_msg = {
            "role": msg["role"],
            "timestamp": msg.get("timestamp", "")
        }
        
        if msg["role"] == "tool":
            processed_msg["content"] = "<搜索结果>"
            processed_msg["summary"] = True
        elif msg.get("tool_calls"):
            processed_msg["content"] = "<调用工具>"
            processed_msg["tool_calls"] = len(msg["tool_calls"])
        else:
            content = msg.get("content", "")
            if len(content) > 500:
                processed_msg["content"] = content[:500] + "..."
                processed_msg["truncated"] = True
            else:
                processed_msg["content"] = content
        
        processed_history.append(processed_msg)
    
    return {
        "session_id": session_id,
        "history": processed_history,
        "total_messages": len(history)
    }

# ============================================
# 健康检查和元信息
# ============================================

@app.get("/")
async def root():
    """API根路径"""
    return {
        "name": "Web搜索Agent API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "sessions": "/api/sessions",
            "chat": "/api/chat"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "active_sessions": len(session_manager.sessions),
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# 启动服务
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )