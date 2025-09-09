"""
通用LLM类 - 支持DeepSeek等OpenAI兼容API
支持多轮对话、Function Calling、流式/非流式输出
完整支持SSE流式传输
"""

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage
from typing import List, Dict, Optional, Literal, Callable, AsyncGenerator, Any
import asyncio
import json

class LLM:
   """通用大模型类，支持OpenAI兼容的API（包括DeepSeek）
   
   Args:
       api_key (str): API密钥
       base_url (str): API基础URL
       model (str, optional): 模型名称，默认"deepseek-chat"
       tool_choice (str, optional): 工具选择模式，包括"auto", "required", "none"，默认"auto"
       temperature (float, optional): 温度，控制生成结果的随机性，默认1
       max_tokens (int, optional): 最大tokens，默认4096
       stream (bool, optional): 是否流式输出，默认False
   """

   def __init__(self,
                api_key: str,
                base_url: str,
                model: str = "deepseek-chat",
                tool_choice: Literal["auto", "required", "none"] = "auto",
                temperature: float = 1,
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
       """与模型进行交互对话（非流式，保持向后兼容）

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
           # 简化逻辑：优先使用传入的消息，否则使用历史记录
           if messages is not None:
               messages_to_use = messages
               # 如果使用历史记录，将传入的消息添加到历史中
               if use_history:
                   for msg in messages:
                       self.conversation_history.append(msg)
           elif use_history:
               messages_to_use = self.conversation_history
           else:
               raise ValueError("没有提供消息且未启用历史记录")
           
           # 构建请求参数
           request_params = {
               "model": self.model,
               "messages": messages_to_use,
               "temperature": self.temperature if temperature is None else temperature,
               "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
               "stream": False,  # 非流式方法强制为False
           }
           
           # 处理工具调用
           # 当 tools 为 None、空列表 []、空字符串 ""、0、False 等"假值"时，if tools 判断为 False，不会进入分支。
           # 当 tools 为非空列表（如有 function schema 的工具），if tools 判断为 True，会进入分支。
           if tools:
               request_params["tools"] = tools
               request_params["tool_choice"] = self.tool_choice if tool_choice is None else tool_choice
               
           # 调用API
           # **request_params 是 Python 的"字典解包"语法，可以把一个字典的每个键值对都当作独立的参数传递给函数。
           response = await self.client.chat.completions.create(**request_params)
           
           # 如果使用历史记录，将回复添加到对话历史
           if use_history:
               message = response.choices[0].message
               
               # 添加文本内容（如果有）
               if message.content:
                   self.conversation_history.append({
                       "role": "assistant",
                       "content": message.content
                   })
               
               # 添加工具调用（如果有）
               if message.tool_calls:
                   self.conversation_history.append({
                       "role": "assistant",
                       "content": None,  # 工具调用时content为None，避免重复 # 降噪，更稳的因果链：把"意图"与"最终答复"严格拆分
                       "tool_calls": [tc.model_dump() for tc in message.tool_calls]
                   })
           
           # choices 是一个列表，通常情况下只包含一个对象（即 choices[0]），因为默认情况下模型只生成一个回复（n=1）。
           return response.choices[0].message
           
       except Exception as e:
           raise Exception(f"调用API失败: {str(e)}")

   async def chat_stream(self,
                        messages: Optional[List[Dict]] = None,
                        tools: Optional[List[Dict]] = None,
                        temperature: Optional[float] = None,
                        max_tokens: Optional[int] = None,
                        tool_choice: Optional[Literal["auto", "required", "none"]] = None,
                        use_history: bool = True) -> AsyncGenerator[Dict[str, Any], None]:
       """流式对话 - 返回异步生成器供SSE使用
       
       Returns:
           AsyncGenerator: 生成包含以下类型的字典：
               - {"type": "content", "data": str} - 文本内容块
               - {"type": "tool_call_delta", "data": dict} - 工具调用增量
               - {"type": "tool_call_complete", "data": dict} - 完整的工具调用
               - {"type": "done", "data": dict} - 流式结束，包含完整内容
       """
       
       if messages is not None:
           messages_to_use = messages
           if use_history:
               for msg in messages:
                   self.conversation_history.append(msg)
       elif use_history:
           messages_to_use = self.conversation_history
       else:
           raise ValueError("没有提供消息且未启用历史记录")
       
       # 构建请求参数
       request_params = {
           "model": self.model,
           "messages": messages_to_use,
           "temperature": self.temperature if temperature is None else temperature,
           "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
           "stream": True,  # 强制流式
       }
       
       if tools:
           request_params["tools"] = tools
           request_params["tool_choice"] = self.tool_choice if tool_choice is None else tool_choice
       
       # 流式请求
       # await 用于异步编程，表示在此处"等待"一个异步操作完成（如网络请求、IO等），但不会阻塞整个线程。
       response = await self.client.chat.completions.create(**request_params)
       
       # 收集完整内容用于历史记录
       collected_content = []
       collected_tool_calls = []
       current_tool_call = None
       
       # response 是一个异步生成器（async generator），其每次迭代会返回一个 chunk
       # 在流式调用时，模型会边生成边返回内容，每次循环会处理当前已生成的部分
       async for chunk in response:
           delta = chunk.choices[0].delta
           
           # 处理文本内容
           if delta.content:
               """
               触发条件：模型正在生成普通文本回复
               处理逻辑：
               1. 提取文本片段
               2. 添加到收集器（用于最终拼接）
               3. 立即yield给调用方（实现实时效果）
               """
               collected_content.append(delta.content)
               yield {
                   "type": "content",
                   "data": delta.content
               }
           
           # 处理工具调用
           if delta.tool_calls:
               """
               触发条件：模型需要调用工具（Function Calling）
               处理逻辑：需要处理多层嵌套的复杂情况
               """
               for tool_call in delta.tool_calls:
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
                               yield {
                                   "type": "tool_call_complete",
                                   "data": current_tool_call
                               }
                           
                           current_tool_call = {
                               # "or" 在这里的作用是：如果 tool_call.id 为 None 或空值，则使用空字符串 "" 作为默认值
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
                       yield {
                           "type": "tool_call_delta",
                           "data": {
                               "index": current_tool_call["index"],
                               "arguments_delta": tool_call.function.arguments
                           }
                       }
       
       # 添加最后一个工具调用
       if current_tool_call:
           collected_tool_calls.append(current_tool_call)
           yield {
               "type": "tool_call_complete",
               "data": current_tool_call
           }
       
       # 构建最终内容
       final_content = "".join(collected_content).strip() if collected_content else None
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
       
       # 发送完成信号
       yield {
           "type": "done",
           "data": {
               "content": final_content,
               "tool_calls": collected_tool_calls if collected_tool_calls else None
           }
       }

   async def chat_with_tools_stream(self,
                                   user_input: str,
                                   tools: List[Dict],
                                   tool_functions: Dict[str, Callable],
                                   system_prompt: Optional[str] = None,
                                   temperature: Optional[float] = None,
                                   max_tokens: Optional[int] = None) -> AsyncGenerator[Dict[str, Any], None]:
       """带工具调用的流式对话 - 返回异步生成器
       
       Args:
           user_input: 用户输入
           tools: 工具schema列表
           tool_functions: 工具名称到函数的映射字典
           system_prompt: 系统提示词
           temperature: 温度参数
           max_tokens: 最大tokens
           
       Yields:
           Dict: 包含type和data的事件字典
       """
       
       # 添加系统提示（如果提供且历史为空）
       if system_prompt and not self.conversation_history:
           self.add_message("system", system_prompt)
       
       # 添加用户消息
       self.add_message("user", user_input)
       
       # 第一次调用：判断是否需要工具
       tool_calls_to_execute = []
       
       async for chunk in self.chat_stream(tools=tools, temperature=temperature, max_tokens=max_tokens):
           if chunk["type"] == "content":
               # 透传文本内容
               yield chunk
           elif chunk["type"] == "tool_call_complete":
               # 收集完整的工具调用
               tool_calls_to_execute.append(chunk["data"])
           elif chunk["type"] == "done":
               # 第一轮完成
               if tool_calls_to_execute:
                   # 执行工具调用
                   yield {"type": "tool_execution_start", "data": {}}
                   
                   for tool_call in tool_calls_to_execute:
                       func_name = tool_call["function"]["name"]
                       func_args = json.loads(tool_call["function"]["arguments"])
                       
                       yield {
                           "type": "tool_executing",
                           "data": {
                               "name": func_name,
                               "arguments": func_args
                           }
                       }
                       
                       if func_name in tool_functions:
                           # 执行工具函数
                           # iscoroutinefunction 是 Python 标准库 asyncio 中的一个函数，用于判断某个函数是否为协程函数（即 async def 定义的函数）。
                           # 如果是协程函数，需要用 await 调用；否则直接普通调用。
                           if asyncio.iscoroutinefunction(tool_functions[func_name]):
                               result = await tool_functions[func_name](**func_args)
                           else:
                               result = tool_functions[func_name](**func_args)
                           
                           # 添加工具结果到历史
                           self.add_message("tool", str(result), tool_call_id=tool_call["id"])
                           
                           yield {
                               "type": "tool_result",
                               "data": {
                                   "name": func_name,
                                   "result": str(result)[:500]  # 限制长度
                               }
                           }
                       else:
                           error_msg = f"未找到工具: {func_name}"
                           self.add_message("tool", error_msg, tool_call_id=tool_call["id"])
                           yield {
                               "type": "tool_error",
                               "data": {"name": func_name, "error": error_msg}
                           }
                   
                   # 基于工具结果生成最终回答
                   yield {"type": "final_answer_start", "data": {}}
                   
                   async for final_chunk in self.chat_stream(tools=tools, temperature=temperature, max_tokens=max_tokens):
                       if final_chunk["type"] == "content":
                           yield final_chunk
                       elif final_chunk["type"] == "done":
                           yield final_chunk
                           break
               else:
                   # 不需要工具，直接结束
                   yield chunk

   async def chat_with_tools(self,
                            user_input: str,
                            tools: List[Dict],
                            tool_functions: Dict[str, Callable],
                            system_prompt: Optional[str] = None,
                            stream: Optional[bool] = None,
                            temperature: Optional[float] = None,
                            max_tokens: Optional[int] = None) -> str:
       """带工具调用的完整对话流程（保持向后兼容）
       
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
       
       # 添加系统提示（如果提供且历史为空）
       if system_prompt and not self.conversation_history:
           self.add_message("system", system_prompt)
       
       # 添加用户消息
       self.add_message("user", user_input)
       
       print(f"[用户]: {user_input}\n")
       print("[助手]: ", end="")
       
       response = await self.chat(
           tools=tools,
           stream=False,
           temperature=temperature,
           max_tokens=max_tokens
       )
       
       # 如果有工具调用
       if response.tool_calls:
           print("\n[执行工具调用]:")
           
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
                   self.add_message("tool", str(result), tool_call_id=tool_call.id)
                   print(f"    结果: {result[:100]}..." if len(str(result)) > 100 else f"    结果: {result}")
               else:
                   print(f"    错误: 未找到工具 {func_name}")
           
           # 基于工具结果生成最终回复
           print("\n[最终回答]: ", end="")
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
           print(response.content)
           return response.content


# ============================================
# 使用示例和测试
# ============================================

async def test_llm():
   """测试LLM类的各种功能"""
   
   # 初始化 - 支持DeepSeek
   llm = LLM(
       api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",
       base_url="https://api.deepseek.com/v1",  # DeepSeek
       model="deepseek-chat",
       stream=False,  # 默认非流式
       temperature=0.7
   )
   
   print("="*60)
   print("测试1: 纯文本流式")
   print("="*60)
   
   llm.clear_history()
   llm.add_message("user", "介绍一下Python语言")
   
   async for chunk in llm.chat_stream():
       if chunk["type"] == "content":
           print(chunk["data"], end="", flush=True)
       elif chunk["type"] == "done":
           print("\n\n流式完成")
           print(f"完整内容长度: {len(chunk['data']['content'])} 字符")
           break
   
   print("\n" + "="*60)
   print("测试2: 带工具的流式对话")
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
   
   async for chunk in llm.chat_with_tools_stream(
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
           print("\n流式完成")
           break

if __name__ == "__main__":
   asyncio.run(test_llm())