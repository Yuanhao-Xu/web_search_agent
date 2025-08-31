"""
通用LLM类 - 支持DeepSeek等OpenAI兼容API
支持多轮对话、Function Calling、流式/非流式输出
"""

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage
import os
from typing import List, Dict, Optional, Literal, Callable
import asyncio
import json

class LLM:
    """通用大模型类，支持OpenAI兼容的API（包括DeepSeek）
    
    Args:
        api_key (str): API密钥
        base_url (str): API基础URL
        model (str, optional): 模型名称，默认"deepseek-chat"
        tool_choice (str, optional): 工具选择模式，包括"auto", "required", "none"，默认"auto"
        temperature (float, optional): 温度，控制生成结果的随机性，默认0.7
        max_tokens (int, optional): 最大tokens，默认4096
        stream (bool, optional): 是否流式输出，默认False
    """

    def __init__(self,
                 api_key: str,
                 base_url: str,
                 model: str = "deepseek-chat",
                 tool_choice: Literal["auto", "required", "none"] = "auto",
                 temperature: float = 0.7,
                 max_tokens: int = 4096,
                 stream: bool = False):

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.tool_choice = tool_choice
        self.stream = stream
        
        # 存储对话历史，支持多轮对话
        self.conversation_history: List[Dict] = []

    def add_message(self, role: str, content: str):
        """添加消息到对话历史"""
        self.conversation_history.append({"role": role, "content": content})
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
    
    def get_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.conversation_history.copy()

    async def chat(self,
                   messages: Optional[List[Dict]] = None,
                   tools: Optional[List[Dict]] = None,
                   temperature: Optional[float] = None,
                   max_tokens: Optional[int] = None,
                   tool_choice: Optional[Literal["auto", "required", "none"]] = None,
                   stream: Optional[bool] = None,
                   use_history: bool = True) -> ChatCompletionMessage:
        """与模型进行交互对话

        Args:
            messages: 对话消息列表。如果为None且use_history=True，使用内部对话历史
            tools: 可用的工具列表（function schema格式）
            temperature: 温度参数
            max_tokens: 最大生成tokens
            tool_choice: 工具选择模式
            stream: 是否流式输出
            use_history: 是否使用内部对话历史

        Returns:
            ChatCompletionMessage: OpenAI格式的回复
        """
        try:
            # 决定使用的消息
            if messages is None and use_history:
                messages_to_use = self.conversation_history
            elif messages is not None:
                messages_to_use = messages
            else:
                raise ValueError("没有提供消息且未启用历史记录")
            
            # 构建请求参数
            request_params = {
                "model": self.model,
                "messages": messages_to_use,
                "temperature": self.temperature if temperature is None else temperature,
                "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
                "stream": self.stream if stream is None else stream,
            }
            
            # 处理工具调用
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = self.tool_choice if tool_choice is None else tool_choice

            # 调用API
            if not request_params["stream"]:
                # 非流式请求
                response = await self.client.chat.completions.create(**request_params)
                
                # 如果使用历史记录，添加到对话历史
                if use_history:
                    if response.choices[0].message.content:
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response.choices[0].message.content
                        })
                    if response.choices[0].message.tool_calls:
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tc.model_dump() for tc in response.choices[0].message.tool_calls]
                        })
                
                return response.choices[0].message
                
            else:
                # 流式请求
                response = await self.client.chat.completions.create(**request_params)
                collected_content = []
                collected_tool_calls = []
                current_tool_call = None
                
                async for chunk in response:
                    # 处理文本内容
                    if chunk.choices[0].delta.content:
                        chunk_content = chunk.choices[0].delta.content
                        collected_content.append(chunk_content)
                        print(chunk_content, end="", flush=True)
                    
                    # 处理工具调用
                    if chunk.choices[0].delta.tool_calls:
                        for tool_call in chunk.choices[0].delta.tool_calls:
                            if tool_call.index is not None:
                                if current_tool_call is None or tool_call.index != current_tool_call["index"]:
                                    if current_tool_call:
                                        collected_tool_calls.append(current_tool_call)
                                    current_tool_call = {
                                        "id": tool_call.id or "",
                                        "type": "function",
                                        "index": tool_call.index,
                                        "function": {
                                            "name": "",
                                            "arguments": ""
                                        }
                                    }
                            
                            if tool_call.function and tool_call.function.name:
                                current_tool_call["function"]["name"] = tool_call.function.name
                            
                            if tool_call.function and tool_call.function.arguments:
                                current_tool_call["function"]["arguments"] += tool_call.function.arguments
                
                # 添加最后一个工具调用
                if current_tool_call:
                    collected_tool_calls.append(current_tool_call)
                
                # 构建响应消息
                final_content = "".join(collected_content).strip() if collected_content else None
                
                # 如果使用历史记录，添加到对话历史
                if use_history:
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
                
                return ChatCompletionMessage(
                    role="assistant",
                    content=final_content,
                    tool_calls=collected_tool_calls if collected_tool_calls else None
                )

        except Exception as e:
            raise Exception(f"调用API失败: {str(e)}")
    
    async def chat_with_tools(self, 
                             user_input: str,
                             tools: List[Dict],
                             tool_functions: Dict[str, Callable],
                             system_prompt: Optional[str] = None,
                             stream: Optional[bool] = None,
                             temperature: Optional[float] = None,
                             max_tokens: Optional[int] = None) -> str:
        """带工具调用的完整对话流程，支持流式和非流式
        
        Args:
            user_input: 用户输入
            tools: 工具schema列表
            tool_functions: 工具名称到函数的映射字典
            system_prompt: 系统提示词
            stream: 是否流式输出（覆盖默认设置）
            temperature: 温度参数（覆盖默认设置）
            max_tokens: 最大tokens（覆盖默认设置）
            
        Returns:
            str: 最终回复
        """
        # 决定是否使用流式
        use_stream = self.stream if stream is None else stream
        
        # 添加系统提示（如果提供且历史为空）
        if system_prompt and not self.conversation_history:
            self.add_message("system", system_prompt)
        
        # 添加用户消息
        self.add_message("user", user_input)
        
        # 第一次调用：判断是否需要工具
        if not use_stream:
            # ========== 非流式处理 ==========
            print(f"[用户]: {user_input}\n")
            
            response = await self.chat(
                tools=tools,
                stream=False,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 如果有工具调用
            if response.tool_calls:
                print("[执行工具调用]:")
                
                # 执行所有工具
                for tool_call in response.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    
                    print(f"  - 工具: {func_name}")
                    print(f"    参数: {func_args}")
                    
                    if func_name in tool_functions:
                        # 执行工具函数
                        if asyncio.iscoroutinefunction(tool_functions[func_name]):
                            result = await tool_functions[func_name](**func_args)
                        else:
                            result = tool_functions[func_name](**func_args)
                        
                        # 添加工具结果到历史
                        self.conversation_history.append({
                            "role": "tool",
                            "content": str(result),
                            "tool_call_id": tool_call.id
                        })
                        print(f"    结果: {result[:100]}..." if len(str(result)) > 100 else f"    结果: {result}")
                    else:
                        print(f"    错误: 未找到工具 {func_name}")
                
                # 基于工具结果生成最终回复
                print("\n[助手]: ", end="")
                final_response = await self.chat(
                    tools=tools,
                    stream=False,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                print(final_response.content)
                return final_response.content
            else:
                # 不需要工具，直接返回
                print(f"[助手]: {response.content}")
                return response.content
                
        else:
            # ========== 流式处理 ==========
            print(f"[用户]: {user_input}\n")
            print("[助手]: ", end="")
            
            # 第一次流式调用
            first_response = await self.chat(
                tools=tools,
                stream=True,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 如果有工具调用
            if first_response.tool_calls:
                print("\n\n[执行工具调用]:")
                
                # 执行所有工具
                for tool_call in first_response.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    
                    print(f"  - 工具: {func_name}")
                    print(f"    参数: {func_args}")
                    
                    if func_name in tool_functions:
                        # 执行工具函数
                        if asyncio.iscoroutinefunction(tool_functions[func_name]):
                            result = await tool_functions[func_name](**func_args)
                        else:
                            result = tool_functions[func_name](**func_args)
                        
                        # 添加工具结果到历史
                        self.conversation_history.append({
                            "role": "tool",
                            "content": str(result),
                            "tool_call_id": tool_call.id
                        })
                        print(f"    结果: {result[:100]}..." if len(str(result)) > 100 else f"    结果: {result}")
                    else:
                        print(f"    错误: 未找到工具 {func_name}")
                
                # 基于工具结果生成最终回复（流式）
                print("\n[基于工具结果生成回答]: ")
                final_response = await self.chat(
                    tools=tools,
                    stream=True,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                print()  # 换行
                return final_response.content
            else:
                # 不需要工具，直接返回流式结果
                print()  # 换行
                return first_response.content


# ============================================
# 使用示例和测试
# ============================================

async def test_llm():
    """测试LLM类的各种功能"""
    
    # 初始化 - 支持DeepSeek
    llm = LLM(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",
        base_url="https://api.deepseek.com/v1",  # DeepSeek
        # base_url="https://api.openai.com/v1",  # OpenAI
        # base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 阿里云
        model="deepseek-chat",
        stream=False,  # 默认非流式
        temperature=0.7
    )
    
    print("="*60)
    print("测试1: Function Calling - 非流式")
    print("="*60)
    
    # 定义工具
    def get_weather(location: str) -> str:
        """获取天气（模拟）"""
        return f"{location}今天晴天，温度25°C"
    
    def calculate(expression: str) -> str:
        """计算数学表达式"""
        try:
            result = eval(expression, {"__builtins__": {}})
            return f"计算结果: {result}"
        except:
            return "计算错误"
    
    # 工具schema
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取指定地点的天气",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "地点名称"
                        }
                    },
                    "required": ["location"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "计算数学表达式",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
    ]
    
    # 工具映射
    tool_functions = {
        "get_weather": get_weather,
        "calculate": calculate
    }
    
    # 测试非流式工具调用
    llm.clear_history()
    result = await llm.chat_with_tools(
        user_input="北京天气怎么样？顺便帮我算一下 25*4+10",
        tools=tools,
        tool_functions=tool_functions,
        system_prompt="你是一个智能助手，可以查询天气和进行计算",
        stream=False  # 非流式
    )
    
    print("\n" + "="*60)
    print("测试2: Function Calling - 流式")
    print("="*60)
    
    # 测试流式工具调用
    llm.clear_history()
    result = await llm.chat_with_tools(
        user_input="上海的天气如何？计算一下100除以4",
        tools=tools,
        tool_functions=tool_functions,
        system_prompt="你是一个智能助手，可以查询天气和进行计算",
        stream=True  # 流式
    )
    
    print("\n" + "="*60)
    print("测试3: 普通对话 - 流式")
    print("="*60)
    
    # 测试不需要工具的情况
    llm.clear_history()
    result = await llm.chat_with_tools(
        user_input="介绍一下Python语言",
        tools=tools,
        tool_functions=tool_functions,
        system_prompt="你是一个编程专家",
        stream=True
    )

if __name__ == "__main__":
    asyncio.run(test_llm())