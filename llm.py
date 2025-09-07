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

        # 异步openai（AsyncOpenAI）用于支持异步API调用，可以在不阻塞主线程的情况下并发处理多个请求，提高程序的并发能力和响应速度，特别适合需要同时处理大量LLM请求或与其他异步操作（如网络IO、数据库等）协作的场景。
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
        # 这里使用.copy()而不是直接返回self.conversation_history，是为了防止外部代码直接修改内部的对话历史数据。
        # 如果直接返回self.conversation_history，外部拿到的是同一个列表对象，外部对其增删改会影响到LLM实例内部的历史记录，可能导致不可预期的bug。
        # 使用.copy()返回一个浅拷贝，外部即使修改返回的列表，也不会影响到原始的conversation_history，保证了数据的封装性和安全性。
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
            # 三种情况 1. 没有提供消息且未启用历史记录 2. 提供了消息 3. 提供了消息且启用历史记录
            # 这里判断 messages 是否为 None 且 use_history 为 True，是为了决定本次请求要用什么消息内容：
            # - 如果 messages 为空且 use_history=True，说明用户希望直接用历史对话作为上下文（多轮对话场景）。
            # - 如果 messages 不为空，则优先使用传入的 messages（如临时自定义上下文）。
            # - 否则两者都不满足，既没有传入消息，也不打算用历史，无法生成有效请求，抛出异常。
            # 如果用户希望在接受历史消息的同时传入新消息→先用 get_history() 拿到历史，再把新消息 append 进去，作为 messages 传入。
            if messages is None and use_history:
                messages_to_use = self.conversation_history
            elif messages is not None:
                messages_to_use = messages
            else:
                # raise 是 Python 用于主动抛出异常的关键字。当检测到错误或不符合预期的情况时，可以用 raise 抛出异常（如 ValueError），中断流程并交由上层处理。
                # 如果想保存异常信息，可以用 try...except 捕获异常，并将异常对象保存到日志文件、数据库或变量中。例如：
                # try:
                #     raise ValueError("没有提供消息且未启用历史记录")
                # except Exception as e:
                #     with open("error.log", "a", encoding="utf-8") as f:
                #         f.write(str(e) + "\n")
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
            # tools: Optional[List[Dict]] = None
            # 当 tools 为 None、空列表 []、空字符串 ""、0、False 等“假值”时，if tools 判断为 False，不会进入分支。
            # 当 tools 为非空列表（如有 function schema 的工具），if tools 判断为 True，会进入分支。
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = self.tool_choice if tool_choice is None else tool_choice
            # 调用API
            if not request_params["stream"]:
                # 非流式请求
                response = await self.client.chat.completions.create(**request_params)
                # 这里是调用 self.client.chat.completions.create 方法，并将 request_params 字典中的所有键值对作为关键字参数传递给该方法。
                # **request_params 是 Python 的“字典解包”语法，可以把一个字典的每个键值对都当作独立的参数传递给函数。
                # 例如，如果 request_params = {"model": "xxx", "messages": [...]}
                # 那么 create(model="xxx", messages=[...]) 效果等同于 create(**request_params)
                
                # 如果使用历史记录，添加到对话历史
                if use_history:
                    # response 是 OpenAI 格式的返回对象，结构大致如下：
                    # response.choices[0].message 代表本次回复的消息对象
                    # 其中 message.content 是助手回复的文本内容（如 "你好，有什么可以帮您？"）
                    # message.tool_calls 是工具调用的列表（如有 function call，则为列表，否则为 None）
                    # 这里取到的 response.choices[0].message.content 就是本次助手回复的文本
                    # response.choices[0].message.tool_calls 是本次回复涉及的工具调用（如有）

                    if response.choices[0].message.content:
                        # 这里是将助手的回复内容添加到对话历史（conversation_history）中，而不是 message 变量本身。
                        # 原因：message 只是本次API返回的单条消息对象，而 conversation_history 记录了整个对话的历史（包括用户和助手的所有消息），
                        # 这样下次调用时可以带上完整历史，实现多轮对话记忆。
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response.choices[0].message.content
                        })
                    if response.choices[0].message.tool_calls:
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": None, # 降噪，更稳的因果链：把“意图”与“最终答复”严格拆分
                            # tc 是工具调用对象（如 OpenAI 的 ToolCall 对象），它有 model_dump() 方法用于将对象序列化为字典。
                            # 这里遍历 response.choices[0].message.tool_calls，每个 tc 都调用 model_dump()，得到标准字典结构。
                            
                            # response: ChatCompletion 对象（Pydantic 模型）
                            # response.choices: List[ChatCompletionChoice] —— 多个候选回复
                            # response.choices[0].message: ChatCompletionMessage —— 单条消息
                            # response.choices[0].message.tool_calls: List[ChatCompletionMessageToolCall] —— 工具调用列表
                            # 单个 tool_call: ChatCompletionMessageToolCall —— 包含 id, type, function
                            # tool_call.function: FunctionCall 对象 —— 包含 name, arguments(JSON 字符串)
                            "tool_calls": [tc.model_dump() for tc in response.choices[0].message.tool_calls]
                        })
                
                return response.choices[0].message
                # choices 是一个列表，通常情况下只包含一个对象（即 choices[0]），因为默认情况下模型只生成一个回复（n=1）。
                # 但如果在请求参数中设置 n>1（如 n=2），则 choices 会包含多个回复对象（如 choices[0]、choices[1]），
                # 每个对象代表模型生成的一个不同的回复。大多数应用场景下只用第一个回复（choices[0]）。
                # 非流式响应体实例
                #{
                #     "id": "0d4dcf71-59f3-4c96-a215-3af00ea46499",
                #     "object": "chat.completion",
                #     "created": 1756739467,
                #     "model": "deepseek-chat",
                #     "choices": [
                #         {
                #             "index": 0,
                #             "message": {
                #                 "role": "assistant",
                #                 "content": "我来帮您查询今天北京的天气。",
                #                 "tool_calls": [
                #                     {
                #                         "index": 0,
                #                         "id": "call_00_TD9qtJbJmOkgertc0XM1niwd",
                #                         "type": "function",
                #                         "function": {
                #                             "name": "get_weather",
                #                             "arguments": "{\"location\": \"北京\"}"
                #                         }
                #                     }
                #                 ]
                #             },
                #             "logprobs": null,
                #             "finish_reason": "tool_calls"
                #         }
                #     ],
                #     "usage": {
                #         "prompt_tokens": 180,
                #         "completion_tokens": 22,
                #         "total_tokens": 202,
                #         "prompt_tokens_details": {
                #             "cached_tokens": 128
                #         },
                #         "prompt_cache_hit_tokens": 128,
                #         "prompt_cache_miss_tokens": 52
                #     },
                #     "system_fingerprint": "fp_feb633d1f5_prod0820_fp8_kvcache"
                # }
            else:
                # 流式请求
                response = await self.client.chat.completions.create(**request_params)
                # await 用于异步编程，表示在此处“等待”一个异步操作完成（如网络请求、IO等），但不会阻塞整个线程。
                # 在这里，await self.client.chat.completions.create(**request_params) 表示异步地向 LLM 服务发送请求并等待其响应。
                # 这样可以在等待响应期间让事件循环去处理其他任务，提高程序的并发性能和响应速度。
                collected_content = []
                collected_tool_calls = []
                current_tool_call = None
                # response 是一个异步生成器（async generator），其每次迭代会返回一个 chunk（通常是 OpenAI/DeepSeek 等 LLM SDK 中的 StreamChunk 或类似对象）。
                # 在流式调用时，模型会边生成边返回内容，每次循环会处理当前已生成的部分（如 delta.content 或 delta.tool_calls），
                # 直到模型全部生成完毕，async for 循环才会结束。也就是说，循环体会多次被执行，每次处理一小段新生成的数据。
                async for chunk in response:
                    # 处理文本内容
                    if chunk.choices[0].delta.content:
                        """
                        触发条件：模型正在生成普通文本回复
                        处理逻辑：
                        1. 提取文本片段
                        2. 添加到收集器（用于最终拼接）
                        3. 立即显示（实现实时效果）
                        """
                        chunk_content = chunk.choices[0].delta.content
                        collected_content.append(chunk_content)
                        print(chunk_content, end="", flush=True)
                    
                    # 处理工具调用
                    if chunk.choices[0].delta.tool_calls:
                        """
                        触发条件：模型需要调用工具（Function Calling）
                        处理逻辑：需要处理多层嵌套的复杂情况
                        """
                        for tool_call in chunk.choices[0].delta.tool_calls:
                            if tool_call.index is not None:
                                """
                                tool_call.index 的作用：
                                - 当模型需要调用多个工具时，用index区分(0,1,2...)
                                - 同一个工具的信息可能分散在多个chunk中
                                - 通过index判断是否开始了新的工具调用
                                """
                
                                if current_tool_call is None or tool_call.index != current_tool_call["index"]:
                                    """
                                    触发条件：
                                    1. current_tool_call is None: 第一次遇到工具调用
                                    2. tool_call.index != current_tool_call["index"]: 遇到了新的工具(index变了)
                    
                                    处理逻辑：保存前一个完整工具，开始组装新工具
                                    """
                                    if current_tool_call:
                                        # 保存已完整的工具调用
                                        collected_tool_calls.append(current_tool_call)
                                    current_tool_call = {
                                        # “or” 在这里的作用是：如果 tool_call.id 为 None 或空值，则使用空字符串 "" 作为默认值，避免出现 None。
                                        # 这样可以保证 "id" 字段始终有值，便于后续处理。
                                        "id": tool_call.id or "",
                                        "type": "function",
                                        "index": tool_call.index,
                                        "function": {
                                            "name": "",      # 将在后续chunk中填充
                                            "arguments": ""  # 将逐步拼接
                                        }
                                    }
                            
                            if tool_call.function and tool_call.function.name:
                                current_tool_call["function"]["name"] = tool_call.function.name
                                """
                                通常函数名在第一个相关chunk中完整给出
                                直接覆盖赋值（不是拼接）
                                """
                            if tool_call.function and tool_call.function.arguments:
                                current_tool_call["function"]["arguments"] += tool_call.function.arguments
                                """
                                函数参数(JSON字符串)可能分多个chunk传输
                                例如：
                                chunk1: '{"location":'
                                chunk2: '"北京"}'
                                需要逐步拼接成完整JSON
                                """
                                """
                                这里处理工具调用的具体逻辑如下：
                                在流式响应的每个 chunk 中，模型可能会返回 tool_calls（即工具调用的增量信息）。
                                1. 遍历 chunk.choices[0].delta.tool_calls（可能有多个工具调用）。
                                2. 如果 tool_call.index 发生变化，说明是一个新的工具调用，先把上一个 current_tool_call 存入 collected_tool_calls，然后新建 current_tool_call。
                                3. 对于每个 tool_call，提取其 id、type、index，并初始化 function 字段（包含 name 和 arguments）。
                                4. 如果 tool_call.function.name 存在，则更新 current_tool_call["function"]["name"]。
                                5. 如果 tool_call.function.arguments 存在，则将其追加到 current_tool_call["function"]["arguments"]（因为 arguments 可能是分多次增量返回的）。
                                这样可以完整地收集和拼接每个工具调用的所有参数，最终在循环结束后，将最后一个工具调用加入 collected_tool_calls。
                                添加最后一个工具调用                                          
                                """

                if current_tool_call:
                    collected_tool_calls.append(current_tool_call)
                # 拼接完成后的 current_tool_call 示例：
                # {
                #     "id": "tool_calls_1",
                #     "type": "function",
                #     "index": 1,
                #     "function": {
                #         "name": "get_weather",
                #         "arguments": "{\"city\": \"北京\", \"date\": \"2024-06-01\"}"
                #     }
                # }
                # 其中 "arguments" 字段为多次增量拼接后的完整参数字符串。
                # 构建响应消息
                final_content = "".join(collected_content).strip() if collected_content else None
                # 这段代码只是把流式响应过程中收集到的所有文本内容片段（collected_content）拼接成一个完整的字符串，得到最终的文本回复内容 final_content。
                # 它不包含工具调用的内容，只负责整理和输出文本部分。如果没有收集到任何内容，则 final_content 为 None。
                """
                判断逻辑：
                - collected_content有内容：拼接所有片段并去除首尾空格
                - collected_content为空：设为None
                """
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
                        """
                        工具映射
                        self.tool_functions = {
                        "tavily_search": tavily_search
                        }
                        
                        
                        """
                        # 执行工具函数
                        # iscoroutinefunction 是 Python 标准库 asyncio 中的一个函数，用于判断某个函数是否为协程函数（即 async def 定义的函数）。
                        # 如果是协程函数，需要用 await 调用；否则直接普通调用。
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
            
            # 这里的 first_response 指的是通过流式（stream=True）方式请求大模型后，收到的完整回复对象。
            # 在流式过程中，模型会分多次（chunk）返回内容，最终 first_response 汇总了所有chunk的数据。
            # 判断 first_response.tool_calls 是否有值，就是在判断这些chunk的集合中是否包含了工具调用（tool_calls）。
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