from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage
from typing import List, Dict, Optional, Literal, Callable, AsyncGenerator, Any, Union
import asyncio
import json

class LLM:
    """通用大模型类，支持OpenAI兼容的API（包括DeepSeek）
    
    优化：
        1. 优化历史消息记录结构：规范角色和字段json
        2. 优化信息传入逻辑：有状态对话：记录状态→清空状态
        3. 去掉冗杂方法，使用add_message统一管理流式和非流式，在api层统一管理sys_prompt
        4. 优化递归逻辑，使用递归深度控制工具执行次数（流式/非流式）
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
    # 0913 标准化消息历史结构：4个角色以及每个角色内部可以存在的字段
    def add_message(self, 
                    role: str, 
                    content: Optional[str] = None,
                    tool_calls: Optional[List[Dict]] = None,
                    tool_call_id: Optional[str] = None):
        """
        添加消息到对话历史
        
        Args:
            role: 角色 (system/user/assistant/tool)
            content: 消息内容
            tool_calls: 工具调用列表 (仅assistant角色使用)
            tool_call_id: 工具调用ID (仅tool角色使用)
        """
        if role == "assistant":
            # Assistant消息：content始终存在（可为None），tool_calls可选
            msg = {
                "role": "assistant",
                "content": content  # 可以是None或字符串
            }
            if tool_calls:
                msg["tool_calls"] = tool_calls
                
        elif role == "tool":
            # Tool消息：必须有content和tool_call_id
            if content is None or not tool_call_id:
                raise ValueError("Tool消息必须包含content和tool_call_id")
            msg = {
                "role": "tool",
                "content": content,
                "tool_call_id": tool_call_id
            }
            
        elif role in ["system", "user"]:
            # System/User消息：必须有content
            if content is None:
                raise ValueError(f"{role}消息必须包含content")
            msg = {
                "role": role, 
                "content": content
            }
        else:
            raise ValueError(f"未知的角色类型: {role}")
        
        self.conversation_history.append(msg)
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
    
    def get_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.conversation_history.copy()

    # ============================================
    # 公共逻辑 - 1.请求参数构建 2.工具执行 
    # ============================================
      
    def _build_request_params(self,
                            tools: Optional[List[Dict]] = None,
                            temperature: Optional[float] = None,
                            max_tokens: Optional[int] = None,
                            tool_choice: Optional[Literal["auto", "required", "none"]] = None,
                            stream: bool = False) -> Dict:
        """构建API请求参数 - 简化版"""
        
        params = {
            "model": self.model,
            "messages": self.conversation_history,  # 直接使用历史
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
            "stream": stream
        }
        
        if tools:
            params["tools"] = tools
            params["tool_choice"] = self.tool_choice if tool_choice is None else tool_choice
        
        return params

    async def _execute_tool(self,
                          tool_call: Dict,
                          tool_functions: Dict[str, Callable]) -> tuple[str, str]:
        """执行单个工具调用 - 统一工具执行逻辑
        
        处理assistant角色返回的tool_call，执行对应的工具函数并返回结果。
        
        Args:
            tool_call (Dict): 工具调用信息，格式如下：
                {
                    "function": {
                        "name": str,        # 要调用的函数名称
                        "arguments": str    # JSON格式的参数字符串
                    }
                }
                
                示例：
                {
                    "function": {
                        "name": "search_web",
                        "arguments": '{"query": "Python教程", "max_results": 5}'
                    }
                }
            
            tool_functions (Dict[str, Callable]): 可用的工具函数映射表
                键为函数名称，值为对应的可调用函数对象。
                
                格式：
                {
                    "函数名称": 函数对象,
                    ...
                }
                
                示例：
                {
                    "search_web": search_web_func,
                    "calculate": calculate_func
                }
        
        Returns:
            tuple[str, str]: 返回元组 (函数名称, 执行结果)
                - 函数名称: 被执行的函数名
                - 执行结果: 函数执行的结果字符串，或错误信息
        
        Note:
            - 自动处理同步和异步函数的执行
            - 如果函数不存在，返回错误信息而不抛出异常
        """
        
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
                        user_input: Optional[str] = None,
                        tools: Optional[List[Dict]] = None, # tool_schemas
                        tool_functions: Optional[Dict[str, Callable]] = None, # 工具映射表
                        temperature: Optional[float] = None,
                        max_tokens: Optional[int] = None,
                        tool_choice: Optional[Literal["auto", "required", "none"]] = None,
                        verbose: bool = False,
                        max_tool_rounds: int = 3,
                        _current_round: int = 0) -> str:
        """
        支持多轮工具调用和总结引导的对话方法
        
        Args:
            user_input: 用户输入（可选）
            tools: 工具schema列表
            tool_functions: 工具函数映射
            temperature: 温度参数
            max_tokens: 最大tokens
            tool_choice: 工具选择模式
            verbose: 是否打印详细信息
            max_tool_rounds: 最大工具调用轮数（默认3轮）
            _current_round: 内部参数，当前递归轮数
            
        Returns:
            str: 模型的文本回复
        """
        
        # 只在有用户输入时添加（第一轮）
        if user_input:
            self.add_message("user", user_input)
        
        # 确保有消息可发送
        if not self.conversation_history:
            raise ValueError("对话历史为空，无法进行对话")
        
        # 判断是否达到最大轮数
        if _current_round >= max_tool_rounds:
            # 达到上限，准备生成最终总结
            tool_choice = "none"
            
            # 内部配置的总结引导提示
            summary_prompt = (
                "基于上述所有工具调用的结果，请综合分析并用自然、友好的语言回答用户的问题。"
                "确保：1) 直接回答用户的原始问题 2) 包含所有相关信息 3) 语言简洁清晰。"
                "不要提及工具调用的过程，直接给出答案。"
            )
            
            # 添加总结引导提示
            self.add_message("user", summary_prompt)
            if verbose:
                print(f"[系统]: 达到最大工具调用轮数({max_tool_rounds})，添加总结引导...")
        
        # 构建请求参数
        request_params = self._build_request_params(
            tools=tools, 
            temperature=temperature, 
            max_tokens=max_tokens, 
            tool_choice=tool_choice, 
            stream=False
        )
        
        # API调用
        response = await self.client.chat.completions.create(**request_params)
        message = response.choices[0].message
        
        # 提取工具调用（如果有）
        tool_calls = None
        # tools = [{工具1},{工具2（如有）},...]
        if message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        
        # 添加助手回复到历史
        self.add_message("assistant", message.content, tool_calls)
        
        # 如果没有工具调用，直接返回（递归终止条件）
        if not tool_calls or not tool_functions:
            if verbose:
                if message.content:
                    print(f"[助手]: {message.content}")
                if _current_round > 0:
                    print(f"[系统]: 完成，共进行了 {_current_round} 轮工具调用")
            
            return message.content or ""
        
        # 执行工具调用
        if verbose:
            print(f"[执行工具调用 - 第{_current_round + 1}轮]:")
        
        for tool_call in message.tool_calls:
            # 执行工具
            func_name, result = await self._execute_tool(
                tool_call.model_dump(), # Pydantic → 用于将模型实例转换为字典格式
                tool_functions
            )
            
            if verbose:
                print(f"  - 工具: {func_name}")
                result_display = result[:100] + "..." if len(result) > 100 else result
                print(f"    结果: {result_display}")
            
            # 添加工具结果到历史
            self.add_message("tool", content=result, tool_call_id=tool_call.id)
        
        # 递归调用，增加轮数计数
        final_response = await self.chat_complete(
            user_input=None,
            tools=tools,
            tool_functions=tool_functions,
            temperature=temperature,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            verbose=verbose,
            max_tool_rounds=max_tool_rounds,
            _current_round=_current_round + 1
        )
        
        return final_response
    
    # ============================================
    # 核心对话方法 - 流式
    # ============================================
    
    async def chat_stream(self,
                        user_input: Optional[str] = None,
                        tools: Optional[List[Dict]] = None,
                        tool_functions: Optional[Dict[str, Callable]] = None,
                        temperature: Optional[float] = None,
                        max_tokens: Optional[int] = None,
                        tool_choice: Optional[Literal["auto", "required", "none"]] = None,
                        max_tool_rounds: int = 3,
                        _current_round: int = 0) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式对话 - 支持多轮工具调用
        
        Args:
            user_input: 用户输入（可选）
            tools: 工具schema列表
            tool_functions: 工具函数映射
            temperature: 温度参数
            max_tokens: 最大tokens
            tool_choice: 工具选择模式
            max_tool_rounds: 最大工具调用轮数
            _current_round: 内部参数，当前递归轮数
            
        Yields:
            Dict: 包含type和data的事件字典
        """
        
        # 只在有用户输入时添加（第一轮）
        if user_input:
            self.add_message("user", user_input)
        
        # 确保有消息可发送
        if not self.conversation_history:
            raise ValueError("对话历史为空，无法进行对话")
        
        # 判断是否达到最大轮数
        if _current_round >= max_tool_rounds:
            tool_choice = "none"
            
            # 添加总结引导提示
            summary_prompt = (
                "基于上述所有工具调用的结果，请综合分析并用自然、友好的语言回答用户的问题。"
                "确保：1) 直接回答用户的原始问题 2) 包含所有相关信息 3) 语言简洁清晰。"
                "不要提及工具调用的过程，直接给出答案。"
            )
            self.add_message("user", summary_prompt)
            
            yield {"type": "system_info", "data": f"达到最大工具调用轮数({max_tool_rounds})，生成最终答案..."}
        
        # 流式调用核心逻辑
        tool_calls_to_execute = []
        content_chunks = []
        
        async for chunk in self._stream_core(
            tools=tools, # tool_schemas
            temperature=temperature,
            max_tokens=max_tokens,
            tool_choice=tool_choice
        ):
            if chunk["type"] == "content":
                content_chunks.append(chunk["data"])
                yield chunk
            elif chunk["type"] == "tool_call_complete":
                tool_calls_to_execute.append(chunk["data"])
            elif chunk["type"] == "done":
                # 判断是否需要执行工具
                # 每一次递归（self._stream_core）都会产生done事件，done后执行工具更新历史消息，继续递归
                if tool_calls_to_execute and tool_functions:
                    # 执行工具调用
                    yield {"type": "tool_execution_start", "data": {"round": _current_round + 1}}
                    
                    for tool_call in tool_calls_to_execute:
                        func_name = tool_call["function"]["name"]
                        func_args = json.loads(tool_call["function"]["arguments"])
                        
                        yield {
                            "type": "tool_executing",
                            "data": {"name": func_name, "arguments": func_args}
                        }
                        
                        # 执行工具
                        _, result = await self._execute_tool(tool_call, tool_functions)
                        
                        # 添加工具结果到历史
                        self.add_message("tool", content=result, tool_call_id=tool_call["id"])
                        
                        yield {
                            "type": "tool_result",
                            "data": {"name": func_name, "result": result[:500]}
                        }
                    
                    # 递归调用继续生成
                    yield {"type": "continue_generation", "data": {"round": _current_round + 1}}
                    
                    async for next_chunk in self.chat_stream(
                        user_input=None,  # 不再添加用户输入
                        tools=tools,
                        tool_functions=tool_functions,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        tool_choice=tool_choice,
                        max_tool_rounds=max_tool_rounds,
                        _current_round=_current_round + 1
                    ):
                        yield next_chunk
                else:
                    # 无工具调用，流式结束
                    yield chunk
    
    async def _stream_core(self,
                        tools: Optional[List[Dict]] = None,
                        temperature: Optional[float] = None,
                        max_tokens: Optional[int] = None,
                        tool_choice: Optional[Literal["auto", "required", "none"]] = None
                        ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式调用核心逻辑 - 处理单次流式响应
        修改点：
        1. 移除了messages和use_history参数
        2. 直接使用self.conversation_history
        """
        
        # 构建请求参数 - 直接使用历史
        request_params = self._build_request_params(
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            stream=True
        )
        
        # 流式请求
        response = await self.client.chat.completions.create(**request_params)
        
        # 收集内容用于历史记录
        collected_content = []
        collected_tool_calls = []
        current_tool_call = None
        
        # 累计文本内容 + 累计工具参数
        async for chunk in response:
            delta = chunk.choices[0].delta
            
            # 处理文本内容
            if delta.content:
                collected_content.append(delta.content)
                yield {"type": "content", "data": delta.content}
            
            # 处理工具调用
            # 是否有工具调用
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    # 检查index是否存在
                    if tool_call.index is not None:
                        # 判断是否是新工具
                        if current_tool_call is None or tool_call.index != current_tool_call["index"]:
                            # 是新工具，保存上一个工具
                            if current_tool_call:
                                # 保存上一个工具调用（只保留标准字段）
                                standard_call = {
                                    "id": current_tool_call["id"],
                                    "type": current_tool_call["type"],
                                    "function": current_tool_call["function"]
                                }
                                collected_tool_calls.append(standard_call)
                                yield {"type": "tool_call_complete", "data": standard_call}
                            
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
            standard_call = {
                "id": current_tool_call["id"],
                "type": current_tool_call["type"],
                "function": current_tool_call["function"]
            }
            collected_tool_calls.append(standard_call)
            yield {"type": "tool_call_complete", "data": standard_call}
        
        # 更新历史 - 使用add_message统一处理
        final_content = "".join(collected_content).strip() if collected_content else None
        
        if collected_tool_calls or final_content:
            self.add_message(
                "assistant",
                content=final_content,
                tool_calls=collected_tool_calls if collected_tool_calls else None
            )
        
        # 发送完成信号
        yield {
            "type": "done",
            "data": {
                "content": final_content,
                "tool_calls": collected_tool_calls if collected_tool_calls else None
            }
        }

##############################################




# ============================================
# 标准的history_conversation结构
# ============================================

# # 1. System消息
# {
#     "role": "system",
#     "content": "系统指令文本"  # 必需
# }

# # 2. User消息
# {
#     "role": "user",
#     "content": "用户输入文本"  # 必需
# }

# # 3. Assistant消息 - 普通回复
# {
#     "role": "assistant",
#     "content": "助手回复文本"  # 必需
# }

# # 4. Assistant消息 - 工具调用
# {
#     "role": "assistant",
#     "content": None,  # 可以为None或包含文本
#     "tool_calls": [   # 工具调用数组
#         {
#             "id": "唯一标识符",
#             "type": "function",
#             "function": {
#                 "name": "函数名",
#                 "arguments": "JSON字符串格式的参数"
#             }
#         }
#     ]
# }

# # 5. Tool消息
# {
#     "role": "tool",
#     "content": "工具执行结果文本",  # 必需
#     "tool_call_id": "对应的调用id"  # 必需，关联到assistant的tool_calls
# }



# ============================================
# SSE 事件类型汇总
# ============================================

# 1. content - 文本内容片段
# 含义：模型生成的文本内容，逐字/逐词流式输出
# 触发时机：当模型生成普通文本回复时代码位置：
# 2. tool_call_delta - 工具参数增量
# 含义：工具调用参数的流式片段
# 触发时机：当模型决定调用工具，并逐步生成参数时代码位置：
# 3. tool_call_complete - 工具调用完成
# 含义：一个完整的工具调用信息已经收集完毕
# 触发时机：当一个工具的所有参数都接收完成时代码位置：
# 4. done - 单轮完成信号
# 含义：当前这一轮的流式输出已经完成
# 触发时机：每次 API 调用的流式响应结束时代码位置：
# 5. system_info - 系统信息
# 含义：系统级别的提示信息
# 触发时机：达到最大工具调用轮数时代码位置：
# 6. tool_execution_start - 工具执行开始
# 含义：开始执行工具调用
# 触发时机：准备执行收集到的工具调用时代码位置：
# 7. tool_executing - 正在执行工具
# 含义：具体某个工具正在执行
# 触发时机：在执行具体工具函数之前代码位置：
# 8. tool_result - 工具执行结果
# 含义：工具执行完成，返回结果
# 触发时机：工具函数执行完毕后代码位置：
# 9. continue_generation - 继续生成
# 含义：工具执行完成，继续生成下一轮回复
# 触发时机：完成工具调用后，准备递归调用生成最终答案代码位置：
# 10. history - 完整对话历史（api层）
# 含义：发送完整的对话历史记录
# 触发时机：在所有流式内容发送完成后，作为最后一个事件发送