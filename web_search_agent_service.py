"""
基于大模型基类的搜索智能体Web服务
使用FastAPI框架，提供RESTful API接口
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
import logging
import os
from datetime import datetime
import uvicorn

# 导入现有的模块
from llm import LLM
from main import tavily_search, tools
from config import (
    SERVICE_CONFIG, API_KEYS, LLM_CONFIG, 
    LOG_CONFIG, CORS_CONFIG, TOOL_CONFIG
)

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format=LOG_CONFIG["format"],
    handlers=[
        logging.FileHandler(LOG_CONFIG["file"], encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# 数据模型
# ============================================

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=2000)
    stream: bool = Field(False, description="是否流式输出")
    max_tool_calls: int = Field(5, description="最大工具调用次数", ge=1, le=10)
    system_prompt: Optional[str] = Field(None, description="自定义系统提示词", max_length=1000)

class ChatResponse(BaseModel):
    """聊天响应模型"""
    success: bool = Field(..., description="请求是否成功")
    message: str = Field(..., description="响应消息")
    tool_calls_count: int = Field(0, description="工具调用次数")
    response_time: float = Field(..., description="响应时间（秒）")
    timestamp: datetime = Field(..., description="响应时间戳")

class StreamChatResponse(BaseModel):
    """流式聊天响应模型"""
    success: bool = Field(..., description="请求是否成功")
    chunk: str = Field(..., description="响应片段")
    is_final: bool = Field(False, description="是否为最终片段")
    tool_calls_count: int = Field(0, description="工具调用次数")

class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    timestamp: datetime = Field(..., description="检查时间")
    version: str = Field(..., description="服务版本")
    model_info: Dict[str, Any] = Field(..., description="模型信息")

class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="搜索查询", min_length=1, max_length=500)
    max_results: int = Field(3, description="最大结果数", ge=1, le=10)

class SearchResponse(BaseModel):
    """搜索响应模型"""
    success: bool = Field(..., description="搜索是否成功")
    results: List[Dict[str, Any]] = Field(..., description="搜索结果")
    query: str = Field(..., description="搜索查询")
    total_results: int = Field(..., description="结果总数")

# ============================================
# 认证和安全
# ============================================

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证API密钥"""
    api_key = credentials.credentials
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API密钥",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return API_KEYS[api_key]

# ============================================
# 核心服务类
# ============================================

class SearchAgentService:
    """搜索智能体服务类"""
    
    def __init__(self):
        self.llm_instance = None
        self.tool_functions = {
            "tavily_search": tavily_search
        }
        self._initialize_llm()
    
    def _initialize_llm(self):
        """初始化大模型实例"""
        try:
            self.llm_instance = LLM(
                api_key=LLM_CONFIG["api_key"],
                base_url=LLM_CONFIG["base_url"],
                model=LLM_CONFIG["model"],
                temperature=LLM_CONFIG["temperature"],
                max_tokens=LLM_CONFIG["max_tokens"],
                stream=False  # 默认非流式，根据请求动态调整
            )
            logger.info("大模型实例初始化成功")
        except Exception as e:
            logger.error(f"大模型实例初始化失败: {str(e)}")
            raise
    
    async def chat_with_search(self, 
                              user_input: str, 
                              stream: bool = False,
                              max_tool_calls: int = 5,
                              system_prompt: Optional[str] = None) -> Any:
        """
        带搜索工具的聊天功能
        
        Args:
            user_input: 用户输入
            stream: 是否流式输出
            max_tool_calls: 最大工具调用次数
            system_prompt: 自定义系统提示词
            
        Returns:
            聊天响应结果
        """
        try:
            # 清空历史记录
            self.llm_instance.clear_history()
            
            # 设置流式模式
            self.llm_instance.stream = stream
            
            # 优化的系统提示词
            optimized_system_prompt = """你是一个智能助手。请遵循以下原则：

1. 首先判断问题类型：
   - 如果是常识性问题或你已知的信息，直接回答，无需搜索
   - 如果涉及最新信息、实时数据或你不确定的内容，使用搜索工具

2. 使用搜索工具时：
   - 每次搜索后评估：信息是否足够回答用户问题？
   - 如果信息充足，立即停止搜索并给出完整答案
   - 如果信息不足，继续搜索补充信息，但不要超过必要的次数

3. 回答要求：
   - 基于所有收集的信息，提供准确、全面、有条理的答案
   - 如果搜索结果不足，诚实告知用户并提供已知信息"""
            
            # 使用自定义系统提示或默认的
            final_system_prompt = system_prompt if system_prompt else optimized_system_prompt
            
            # 添加系统提示
            self.llm_instance.add_message("system", final_system_prompt)
            
            # 添加用户消息
            self.llm_instance.add_message("user", user_input)
            
            tool_call_count = 0
            final_answer_generated = False
            
            logger.info(f"开始处理用户问题: {user_input}")
            
            while tool_call_count < max_tool_calls and not final_answer_generated:
                logger.debug(f"第 {tool_call_count + 1} 轮对话")
                
                # 调用LLM
                response = await self.llm_instance.chat(
                    tools=tools,
                    stream=stream,
                    use_history=True,
                    tool_choice="auto"
                )
                
                # 检查是否有工具调用
                if response.tool_calls:
                    tool_call_count += 1
                    logger.info(f"执行第 {tool_call_count} 次工具调用")
                    
                    # 执行工具调用
                    for tool_call in response.tool_calls:
                        func_name = tool_call.function.name
                        func_args = tool_call.function.arguments
                        
                        logger.info(f"工具: {func_name}, 参数: {func_args}")
                        
                        if func_name in self.tool_functions:
                            # 解析参数
                            import json
                            try:
                                args_dict = json.loads(func_args)
                                result = await self.tool_functions[func_name](**args_dict)
                            except json.JSONDecodeError:
                                result = f"参数解析错误: {func_args}"
                            
                            # 添加工具结果
                            self.llm_instance.conversation_history.append({
                                "role": "tool",
                                "content": str(result),
                                "tool_call_id": tool_call.id
                            })
                            
                            logger.info(f"工具执行结果: {str(result)[:100]}...")
                    
                    # 评估是否需要继续搜索
                    if tool_call_count < max_tool_calls:
                        evaluation_prompt = """基于已获得的搜索结果，请评估：
1. 信息是否足够回答用户的问题？
2. 如果足够，请直接给出完整答案
3. 如果不足，请继续搜索补充信息"""
                        
                        self.llm_instance.add_message("system", evaluation_prompt)
                        continue
                        
                else:
                    # 没有工具调用，直接返回答案
                    if response.content:
                        logger.info("模型直接回答，无需工具调用")
                        final_answer_generated = True
                        return {
                            "content": response.content,
                            "tool_calls_count": tool_call_count,
                            "stream": stream
                        }
            
            # 确保生成最终答案
            if not final_answer_generated:
                logger.info(f"达到搜索上限 {max_tool_calls} 次，基于已有信息生成答案")
                
                # 添加总结指令
                self.llm_instance.add_message(
                    "system", 
                    "你已经完成了所有必要的搜索。现在请基于所有收集到的信息，为用户提供一个完整、准确的答案。"
                )
                
                # 生成最终回答
                final_response = await self.llm_instance.chat(
                    tools=None,  # 不再提供工具，强制生成答案
                    stream=stream,
                    use_history=True
                )
                
                return {
                    "content": final_response.content,
                    "tool_calls_count": tool_call_count,
                    "stream": stream
                }
                
        except Exception as e:
            logger.error(f"聊天过程中出现错误: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"聊天服务错误: {str(e)}"
            )
    
    async def direct_search(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """
        直接执行搜索
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            搜索结果
        """
        try:
            result = await tavily_search(query, max_results)
            return {
                "success": True,
                "results": [{"content": result}],
                "query": query,
                "total_results": 1
            }
        except Exception as e:
            logger.error(f"搜索过程中出现错误: {str(e)}")
            return {
                "success": False,
                "results": [],
                "query": query,
                "total_results": 0,
                "error": str(e)
            }

# ============================================
# FastAPI应用
# ============================================

# 创建FastAPI应用
app = FastAPI(
    title=SERVICE_CONFIG["title"],
    description=SERVICE_CONFIG["description"],
    version=SERVICE_CONFIG["version"],
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_CONFIG["allow_origins"],
    allow_credentials=CORS_CONFIG["allow_credentials"],
    allow_methods=CORS_CONFIG["allow_methods"],
    allow_headers=CORS_CONFIG["allow_headers"],
)

# 创建服务实例
search_service = SearchAgentService()

# ============================================
# API端点
# ============================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """根路径"""
    return {
        "message": "智能搜索助手API服务",
        "version": SERVICE_CONFIG["version"],
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    try:
        # 检查大模型连接
        model_info = {
            "model": LLM_CONFIG["model"],
            "base_url": LLM_CONFIG["base_url"],
            "status": "connected" if search_service.llm_instance else "disconnected"
        }
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            version=SERVICE_CONFIG["version"],
            model_info=model_info
        )
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务不可用"
        )

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    user: str = Depends(verify_api_key)
):
    """聊天端点（非流式）"""
    start_time = datetime.now()
    
    try:
        result = await search_service.chat_with_search(
            user_input=request.message,
            stream=False,
            max_tool_calls=request.max_tool_calls,
            system_prompt=request.system_prompt
        )
        
        response_time = (datetime.now() - start_time).total_seconds()
        
        return ChatResponse(
            success=True,
            message=result["content"],
            tool_calls_count=result["tool_calls_count"],
            response_time=response_time,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"聊天请求失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天失败: {str(e)}"
        )

@app.post("/chat/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    user: str = Depends(verify_api_key)
):
    """聊天端点（流式）"""
    try:
        result = await search_service.chat_with_search(
            user_input=request.message,
            stream=True,
            max_tool_calls=request.max_tool_calls,
            system_prompt=request.system_prompt
        )
        
        # 流式返回结果
        content = result["content"]
        tool_calls_count = result["tool_calls_count"]
        
        # 模拟流式输出（实际应该使用SSE或WebSocket）
        chunks = [content[i:i+100] for i in range(0, len(content), 100)]
        
        for i, chunk in enumerate(chunks):
            is_final = (i == len(chunks) - 1)
            yield StreamChatResponse(
                success=True,
                chunk=chunk,
                is_final=is_final,
                tool_calls_count=tool_calls_count
            ).model_dump_json() + "\n"
            
    except Exception as e:
        logger.error(f"流式聊天请求失败: {str(e)}")
        yield StreamChatResponse(
            success=False,
            chunk=f"错误: {str(e)}",
            is_final=True,
            tool_calls_count=0
        ).model_dump_json() + "\n"

@app.post("/search", response_model=SearchResponse)
async def search_endpoint(
    request: SearchRequest,
    user: str = Depends(verify_api_key)
):
    """直接搜索端点"""
    try:
        result = await search_service.direct_search(
            query=request.query,
            max_results=request.max_results
        )
        
        return SearchResponse(
            success=result["success"],
            results=result["results"],
            query=request.query,
            total_results=result["total_results"]
        )
        
    except Exception as e:
        logger.error(f"搜索请求失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {str(e)}"
        )

@app.get("/tools")
async def get_available_tools():
    """获取可用工具列表"""
    return {
        "tools": tools,
        "description": "当前可用的搜索工具"
    }

# ============================================
# 错误处理
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理器"""
    return {
        "success": False,
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.now().isoformat()
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理器"""
    logger.error(f"未处理的异常: {str(exc)}")
    return {
        "success": False,
        "error": "内部服务器错误",
        "status_code": 500,
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# 启动和运行
# ============================================

if __name__ == "__main__":
    logger.info(f"启动 {SERVICE_CONFIG['title']} v{SERVICE_CONFIG['version']}")
    logger.info(f"服务地址: http://{SERVICE_CONFIG['host']}:{SERVICE_CONFIG['port']}")
    logger.info(f"API文档: http://{SERVICE_CONFIG['host']}:{SERVICE_CONFIG['port']}/docs")
    
    uvicorn.run(
        "web_search_agent_service:app",
        host=SERVICE_CONFIG["host"],
        port=SERVICE_CONFIG["port"],
        reload=SERVICE_CONFIG["debug"],
        log_level="info"
    )
