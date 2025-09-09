"""Web搜索Agent会话层 - 支持真正的流式传输"""

import asyncio
import json
from typing import Optional, Dict, List, Literal, Any, AsyncGenerator
from llm_0908 import LLM
from tools.tavily_search import tavily_search
from tools.function_schema import tools

class WebSearchAgent:
   """Web搜索Agent会话管理类"""
   
   def __init__(self,
                api_key: str,
                base_url: str = "https://api.deepseek.com/v1",
                model: str = "deepseek-chat",
                tool_choice: Literal["auto", "required", "none"] = "auto",
                max_tool_calls: int = 3,
                temperature: float = 0.7,
                max_tokens: int = 4096,
                stream: bool = True):
       """
       Args:
           api_key: DeepSeek API密钥
           base_url: API基础URL
           model: 模型名称
           tool_choice: 工具选择模式 ("auto", "required", "none")
           max_tool_calls: 单次对话最大工具调用次数
           temperature: 温度参数
           max_tokens: 最大tokens
           stream: 是否流式输出
       """
       # max_tokens参数用于控制大模型每次生成回复时的最大token（标记）数。
       # 它决定了模型输出内容的长度上限，防止生成过长的回复导致消耗过多资源或超出接口限制。
       # 例如，max_tokens=4096表示单次回复最多生成4096个token，超出部分会被截断。
       self.llm = LLM(
           api_key=api_key,
           base_url=base_url,
           model=model,
           tool_choice=tool_choice,
           temperature=temperature,
           max_tokens=max_tokens,
           stream=stream
       )
       
       self.tool_choice = tool_choice
       self.max_tool_calls = max_tool_calls
       self.tool_call_count = 0  # 当前对话工具调用计数
       
       # 工具函数映射
       self.tool_functions = {
           "tavily_search": tavily_search
       }
       
       # session_active参数用于管理当前会话是否处于激活状态（即是否继续与用户交互）。
       # 当session_active为True时，Agent会持续接收和处理用户输入；
       # 如果设置为False，则会话终止，Agent不再响应新的消息（如用户输入/exit命令时）。
       self.session_active = True 
       self.system_prompt = """你是一个智能助手，可以通过搜索工具获取最新的互联网信息。

搜索策略指导：
1. 当用户询问需要实时信息的问题时，使用搜索工具
2. 如果首次搜索结果不够充分或相关，可以进行多轮搜索：
   - 尝试不同的搜索关键词
   - 使用更具体或更宽泛的搜索词
   - 基于前次搜索结果调整搜索策略
3. 最多可以进行3次搜索，请合理利用搜索次数
4. 基于所有搜索结果提供准确、全面、有帮助的回答

搜索质量评估：
- 如果搜索结果与用户问题高度相关且信息充分，可以停止搜索
- 如果搜索结果不够相关或信息不足，继续优化搜索策略"""
       
       # 初始化时注入系统提示（到conversation_history）
       self.llm.add_message("system", self.system_prompt)
   
   def reset_session(self):
       """重置会话状态"""
       self.llm.clear_history()
       self.tool_call_count = 0
       # 重新注入系统提示（到conversation_history）
       self.llm.add_message("system", self.system_prompt)
       print("✨ 会话已重置\n")
   
   def set_tool_choice(self, choice: Literal["auto", "required", "none"]):
       """设置工具选择模式"""
       self.tool_choice = choice
       self.llm.tool_choice = choice
       print(f"🔧 工具选择模式设置为: {choice}\n")
   
   def set_max_tool_calls(self, max_calls: int):
       """设置最大工具调用次数"""
       self.max_tool_calls = max_calls
       print(f"📊 最大工具调用次数设置为: {max_calls}\n")
   
   def set_stream_mode(self, stream: bool):
       """设置流式输出模式"""
       self.llm.stream = stream
       mode_str = "流式" if stream else "非流式"
       print(f"📡 输出模式设置为: {mode_str}\n")
   
   async def process_message_stream(self, user_input: str) -> AsyncGenerator[Dict[str, Any], None]:
       """流式处理单条用户消息（简化版，完全复用LLM类逻辑）"""
       self.tool_call_count = 0
       
       try:
           async for chunk in self.llm.chat_with_tools_stream(
               user_input=user_input,
               tools=None if self.tool_choice == "none" else tools,
               tool_functions=self.tool_functions
           ):
               # 仅处理工具调用次数限制
               if chunk["type"] == "tool_executing":
                   self.tool_call_count += 1
                   if self.tool_call_count > self.max_tool_calls:
                       self.llm.add_message(
                           "tool", 
                           f"[已达到{self.max_tool_calls}次调用上限]",
                           tool_call_id="limit"
                       )
                       yield {"type": "tool_limit", "data": f"达到上限{self.max_tool_calls}次"}
                       break
               
               # 透传所有其他事件
               yield chunk
               
       except Exception as e:
           yield {"type": "error", "data": f"处理消息时出错: {str(e)}"}
   
   
   async def process_message(self, user_input: str) -> str:
       """非流式处理单条用户消息"""
       tools_to_use = None if self.tool_choice == "none" else tools
       
       try:
           return await self.llm.chat_with_tools(
               user_input=user_input,
               tools=tools_to_use,
               tool_functions=self.tool_functions,
               stream=False
           )
       except Exception as e:
           return f"处理消息时出错: {str(e)}"

# ============================================
# 测试入口
# ============================================

async def main():
   """测试入口"""
   agent = WebSearchAgent(
       api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",  
       tool_choice="auto",
       max_tool_calls=3,
       stream=True
   )
   
   # 简单测试
   print("测试WebSearchAgent...")
   result = await agent.process_message("今天北京的天气怎么样？")
   print(f"结果: {result}")

if __name__ == "__main__":
   asyncio.run(main())