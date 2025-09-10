"""
通用LLM类 - 支持DeepSeek等OpenAI兼容API
支持多轮对话、Function Calling、流式/非流式输出
重构版本：减少代码重复，统一逻辑处理
"""

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage
from typing import List, Dict, Optional, Literal, Callable, AsyncGenerator, Any, Union
import asyncio
import json

class LLM:
    """通用大模型类，支持OpenAI兼容的API（包括DeepSeek）
    
    重构优化：
    - 统一消息准备和参数构建逻辑
    - 抽取工具执行公共代码
    - 简化流式/非流式处理流程
    """

    def __init__(self,
                 api_key: str,
                 base_url: str,
                 model: str = "deepseek-chat",
                 tool_choice: Literal["auto", "required", "none"] = "auto",
                 temperature: float = 1,
                 max_tokens: int = 4096):
        
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.tool_choice = tool_choice
        self.conversation_history: List[Dict] = []

    # ============================================
    # 基础方法
    # ============================================
    
    def add_message(self, role: str, content: str, tool_call_id: Optional[str] = None):
        """添加消息到对话历史"""
        msg = {"role": role, "content": content}
        if tool_call_id:
            msg["tool_call_id"] = tool_call_id
        self.conversation_history.append(msg)
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
    
    def get_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.conversation_history.copy()

    # ============================================
    # 内部辅助方法 - 抽取公共逻辑
    # ============================================
    
    def _prepare_messages(self, 
                         messages: Optional[List[Dict]] = None,
                         system_prompt: Optional[str] = None,
                         user_input: Optional[str] = None,
                         use_history: bool = True) -> List[Dict]:
        """准备消息列表 - 统一处理消息、系统提示和历史"""
        
        # 如果需要添加系统提示且历史为空
        if system_prompt and not self.conversation_history and use_history:
            self.add_message("system", system_prompt)
        
        # 如果有用户输入，添加到历史
        if user_input and use_history:
            self.add_message("user", user_input)
        
        # 确定要使用的消息
        if messages is not None:
            messages_to_use = messages
            if use_history:
                for msg in messages:
                    if msg not in self.conversation_history:
                        self.conversation_history.append(msg)
        elif use_history:
            messages_to_use = self.conversation_history
        else:
            raise ValueError("没有提供消息且未启用历史记录")
        
        return messages_to_use
    
    def _build_request_params(self,
                            messages: List[Dict],
                            tools: Optional[List[Dict]] = None,
                            temperature: Optional[float] = None,
                            max_tokens: Optional[int] = None,
                            tool_choice: Optional[Literal["auto", "required", "none"]] = None,
                            stream: bool = False) -> Dict:
        """构建API请求参数 - 统一参数处理逻辑"""
        
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
            "stream": stream
        }
        
        if tools:
            params["tools"] = tools
            params["tool_choice"] = self.tool_choice if tool_choice is None else tool_choice
        
        return params
    
    def _update_history_with_response(self, message: ChatCompletionMessage):
        """更新历史记录 - 处理助手回复"""
        if message.content:
            self.conversation_history.append({
                "role": "assistant",
                "content": message.content
            })
        
        if message.tool_calls:
            self.conversation_history.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [tc.model_dump() for tc in message.tool_calls]
            })
    
    async def _execute_tool(self,
                          tool_call: Dict,
                          tool_functions: Dict[str, Callable]) -> tuple[str, str]:
        """执行单个工具调用 - 统一工具执行逻辑"""
        
        func_name = tool_call["function"]["name"]
        func_args = json.loads(tool_call["function"]["arguments"])
        
        if func_name in tool_functions:
            # 判断是否为异步函数并执行
            if asyncio.iscoroutinefunction(tool_functions[func_name]):
                result = await tool_functions[func_name](**func_args)
            else:
                result = tool_functions[func_name](**func_args)
            
            return func_name, str(result)
        else:
            error_msg = f"未找到工具: {func_name}"
            return func_name, error_msg
    
    # ============================================
    # 核心对话方法 - 非流式
    # ============================================
    
    async def chat_complete(self,
                          messages: Optional[List[Dict]] = None,
                          user_input: Optional[str] = None,
                          tools: Optional[List[Dict]] = None,
                          tool_functions: Optional[Dict[str, Callable]] = None,
                          system_prompt: Optional[str] = None,
                          temperature: Optional[float] = None,
                          max_tokens: Optional[int] = None,
                          tool_choice: Optional[Literal["auto", "required", "none"]] = None,
                          use_history: bool = True,
                          verbose: bool = False) -> Union[str, ChatCompletionMessage]:
        """
        完整对话 - 非流式版本
        
        Args:
            messages: 对话消息列表
            user_input: 用户输入（便捷参数）
            tools: 工具schema列表
            tool_functions: 工具函数映射
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大tokens
            tool_choice: 工具选择模式
            use_history: 是否使用历史
            verbose: 是否打印详细信息
            
        Returns:
            str: 如果有工具调用，返回最终文本回复
            ChatCompletionMessage: 如果无工具调用，返回原始消息对象
        """
        
        # 准备消息
        messages_to_use = self._prepare_messages(
            messages, system_prompt, user_input, use_history
        )
        
        # 构建请求参数
        request_params = self._build_request_params(
            messages_to_use, tools, temperature, max_tokens, tool_choice, stream=False
        )
        
        # 第一次调用
        response = await self.client.chat.completions.create(**request_params)
        message = response.choices[0].message
        
        # 更新历史
        if use_history:
            self._update_history_with_response(message)
        
        # 如果没有工具调用，直接返回
        if not message.tool_calls or not tool_functions:
            if verbose and message.content:
                print(f"[助手]: {message.content}")
            return message
        
        # 执行工具调用
        if verbose:
            print("[执行工具调用]:")
        
        for tool_call in message.tool_calls:
            func_name, result = await self._execute_tool(
                tool_call.model_dump(), tool_functions
            )
            
            if verbose:
                print(f"  - 工具: {func_name}")
                print(f"    结果: {result[:100]}..." if len(result) > 100 else f"    结果: {result}")
            
            # 添加工具结果到历史
            self.add_message("tool", result, tool_call_id=tool_call.id)
        
        # 基于工具结果生成最终回复
        final_response = await self.client.chat.completions.create(
            **self._build_request_params(
                self.conversation_history, tools, temperature, max_tokens, tool_choice, stream=False
            )
        )
        
        final_message = final_response.choices[0].message
        
        # 更新历史
        if use_history:
            self._update_history_with_response(final_message)
        
        if verbose and final_message.content:
            print(f"[最终回答]: {final_message.content}")
        
        return final_message.content or ""
    
    # ============================================
    # 核心对话方法 - 流式
    # ============================================
    
    async def chat_stream(self,
                         messages: Optional[List[Dict]] = None,
                         user_input: Optional[str] = None,
                         tools: Optional[List[Dict]] = None,
                         tool_functions: Optional[Dict[str, Callable]] = None,
                         system_prompt: Optional[str] = None,
                         temperature: Optional[float] = None,
                         max_tokens: Optional[int] = None,
                         tool_choice: Optional[Literal["auto", "required", "none"]] = None,
                         use_history: bool = True) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式对话 - 返回异步生成器
        
        Yields:
            Dict: 包含type和data的事件字典
                - {"type": "content", "data": str} - 文本内容块
                - {"type": "tool_call_delta", "data": dict} - 工具调用增量
                - {"type": "tool_call_complete", "data": dict} - 完整的工具调用
                - {"type": "tool_executing", "data": dict} - 工具执行中
                - {"type": "tool_result", "data": dict} - 工具执行结果
                - {"type": "final_answer_start", "data": {}} - 开始最终回答
                - {"type": "done", "data": dict} - 流式结束
        """
        
        # 准备消息
        messages_to_use = self._prepare_messages(
            messages, system_prompt, user_input, use_history
        )
        
        # 第一次流式调用
        tool_calls_to_execute = []
        first_content_chunks = []
        
        async for chunk in self._stream_core(messages_to_use, tools, temperature, max_tokens, tool_choice, use_history):
            if chunk["type"] == "content":
                first_content_chunks.append(chunk["data"])
                yield chunk
            elif chunk["type"] == "tool_call_complete":
                tool_calls_to_execute.append(chunk["data"])
            elif chunk["type"] == "done":
                # 第一轮完成，检查是否需要执行工具
                if tool_calls_to_execute and tool_functions:
                    # 执行工具
                    yield {"type": "tool_execution_start", "data": {}}
                    
                    for tool_call in tool_calls_to_execute:
                        func_name = tool_call["function"]["name"]
                        func_args = json.loads(tool_call["function"]["arguments"])
                        
                        yield {
                            "type": "tool_executing",
                            "data": {"name": func_name, "arguments": func_args}
                        }
                        
                        func_name, result = await self._execute_tool(tool_call, tool_functions)
                        
                        # 添加结果到历史
                        self.add_message("tool", result, tool_call_id=tool_call["id"])
                        
                        yield {
                            "type": "tool_result",
                            "data": {"name": func_name, "result": result[:500]}
                        }
                    
                    # 生成最终回答
                    yield {"type": "final_answer_start", "data": {}}
                    
                    async for final_chunk in self._stream_core(
                        self.conversation_history, tools, temperature, max_tokens, tool_choice, use_history
                    ):
                        if final_chunk["type"] in ["content", "done"]:
                            yield final_chunk
                else:
                    # 无工具调用，直接结束
                    yield chunk
    
    async def _stream_core(self,
                          messages: List[Dict],
                          tools: Optional[List[Dict]] = None,
                          temperature: Optional[float] = None,
                          max_tokens: Optional[int] = None,
                          tool_choice: Optional[Literal["auto", "required", "none"]] = None,
                          use_history: bool = True) -> AsyncGenerator[Dict[str, Any], None]:
        """流式调用核心逻辑 - 处理单次流式响应"""
        
        # 构建请求参数
        request_params = self._build_request_params(
            messages, tools, temperature, max_tokens, tool_choice, stream=True
        )
        
        # 流式请求
        response = await self.client.chat.completions.create(**request_params)
        
        # 收集内容用于历史记录
        collected_content = []
        collected_tool_calls = []
        current_tool_call = None
        
        async for chunk in response:
            delta = chunk.choices[0].delta
            
            # 处理文本内容
            if delta.content:
                collected_content.append(delta.content)
                yield {"type": "content", "data": delta.content}
            
            # 处理工具调用
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    if tool_call.index is not None:
                        if current_tool_call is None or tool_call.index != current_tool_call["index"]:
                            if current_tool_call:
                                collected_tool_calls.append(current_tool_call)
                                yield {"type": "tool_call_complete", "data": current_tool_call}
                            
                            current_tool_call = {
                                "id": tool_call.id or "",
                                "type": "function",
                                "index": tool_call.index,
                                "function": {"name": "", "arguments": ""}
                            }
                    
                    if tool_call.function and tool_call.function.name:
                        current_tool_call["function"]["name"] = tool_call.function.name
                    
                    if tool_call.function and tool_call.function.arguments:
                        current_tool_call["function"]["arguments"] += tool_call.function.arguments
                        yield {
                            "type": "tool_call_delta",
                            "data": {
                                "index": current_tool_call["index"],
                                "arguments_delta": tool_call.function.arguments
                            }
                        }
        
        # 处理最后一个工具调用
        if current_tool_call:
            collected_tool_calls.append(current_tool_call)
            yield {"type": "tool_call_complete", "data": current_tool_call}
        
        # 更新历史
        if use_history:
            final_content = "".join(collected_content).strip() if collected_content else None
            if final_content:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": final_content
                })
            if collected_tool_calls:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": collected_tool_calls
                })
        
        # 发送完成信号
        yield {
            "type": "done",
            "data": {
                "content": "".join(collected_content).strip() if collected_content else None,
                "tool_calls": collected_tool_calls if collected_tool_calls else None
            }
        }
    
    # ============================================
    # 向后兼容的别名方法
    # ============================================
    
    async def chat(self, **kwargs) -> ChatCompletionMessage:
        """向后兼容的非流式对话方法"""
        return await self.chat_complete(**kwargs)
    
    async def chat_with_tools(self, user_input: str, tools: List[Dict], 
                             tool_functions: Dict[str, Callable], **kwargs) -> str:
        """向后兼容的工具对话方法"""
        kwargs['verbose'] = True  # 保持原有的打印行为
        result = await self.chat_complete(
            user_input=user_input,
            tools=tools,
            tool_functions=tool_functions,
            **kwargs
        )
        return result.content if hasattr(result, 'content') else result


# ============================================
# 使用示例和测试
# ============================================

async def test_llm():
    """测试重构后的LLM类"""
    
    # 初始化
    llm = LLM(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        temperature=0.7
    )
    
    print("="*60)
    print("测试1: 非流式对话")
    print("="*60)
    
    response = await llm.chat_complete(
        user_input="介绍一下Python的优点",
        verbose=True
    )
    
    print("\n" + "="*60)
    print("测试2: 流式对话")
    print("="*60)
    
    llm.clear_history()
    print("[用户]: 讲个短故事")
    print("[助手]: ", end="")
    
    async for chunk in llm.chat_stream(user_input="讲个短故事"):
        if chunk["type"] == "content":
            print(chunk["data"], end="", flush=True)
        elif chunk["type"] == "done":
            print("\n")
    
    print("="*60)
    print("测试3: 带工具的流式对话")
    print("="*60)
    
    # 定义工具
    def get_weather(location: str) -> str:
        """获取天气（模拟）"""
        return f"{location}今天晴天，温度25°C"
    
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定地点的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "地点名称"}
                },
                "required": ["location"]
            }
        }
    }]
    
    tool_functions = {"get_weather": get_weather}
    
    llm.clear_history()
    print("[用户]: 北京天气怎么样？")
    
    async for chunk in llm.chat_stream(
        user_input="北京天气怎么样？",
        tools=tools,
        tool_functions=tool_functions,
        system_prompt="你是一个智能助手，可以查询天气"
    ):
        if chunk["type"] == "content":
            print(chunk["data"], end="", flush=True)
        elif chunk["type"] == "tool_executing":
            print(f"\n[执行工具]: {chunk['data']['name']}")
        elif chunk["type"] == "tool_result":
            print(f"[工具结果]: {chunk['data']['result']}")
        elif chunk["type"] == "final_answer_start":
            print("[基于工具结果生成回答]: ", end="")
        elif chunk["type"] == "done":
            print("\n")
    
    print("="*60)
    print("测试4: 带工具的非流式对话")
    print("="*60)
    
    llm.clear_history()
    response = await llm.chat_complete(
        user_input="上海天气如何？",
        tools=tools,
        tool_functions=tool_functions,
        system_prompt="你是一个智能助手，可以查询天气",
        verbose=True
    )
    print(f"最终回复: {response}")

if __name__ == "__main__":
    asyncio.run(test_llm())