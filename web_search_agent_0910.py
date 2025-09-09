"""Web搜索Agent会话层 - 适配LLM类的优化版"""

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
        """初始化WebSearchAgent"""
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.tool_choice = tool_choice
        self.max_tool_calls = max_tool_calls
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream = stream
        
        # 初始化LLM实例
        self._init_llm()
        
        # 工具函数映射
        self.tool_functions = {
            "tavily_search": tavily_search
        }
        
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
    
    def _init_llm(self):
        """初始化或重新初始化LLM实例"""
        self.llm = LLM(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            tool_choice=self.tool_choice,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=self.stream
        )
        # 注入系统提示
        self.llm.add_message("system", self.system_prompt)
        self.tool_call_count = 0
    
    def reset_session(self):
        """重置会话状态"""
        self._init_llm()
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
        self.stream = stream
        self.llm.stream = stream
        mode_str = "流式" if stream else "非流式"
        print(f"📡 输出模式设置为: {mode_str}\n")
    
    async def process_message_stream(self, user_input: str) -> AsyncGenerator[Dict[str, Any], None]:
        """流式处理单条用户消息（适配LLM类）"""
        self.tool_call_count = 0
        
        # 创建受限的工具函数映射
        limited_tool_functions = {}
        tool_limit_reached = False
        
        for name, func in self.tool_functions.items():
            async def limited_wrapper(*args, _original_func=func, _name=name, **kwargs):
                nonlocal tool_limit_reached
                
                # 增加计数
                self.tool_call_count += 1
                
                # 执行原函数
                if asyncio.iscoroutinefunction(_original_func):
                    result = await _original_func(*args, **kwargs)
                else:
                    result = _original_func(*args, **kwargs)
                
                # 检查是否达到限制
                if self.tool_call_count >= self.max_tool_calls:
                    tool_limit_reached = True
                    result += f"\n\n[系统提示：已达到最大搜索次数{self.max_tool_calls}次，请基于现有信息给出综合回答]"
                
                return result
            
            limited_tool_functions[name] = limited_wrapper
        
        try:
            # 第一阶段：带工具的流式处理
            tools_to_use = None if self.tool_choice == "none" else tools
            
            async for chunk in self.llm.chat_with_tools_stream(
                user_input=user_input,
                tools=tools_to_use,
                tool_functions=limited_tool_functions
            ):
                yield chunk
                
                # 检查是否已达到工具调用限制
                if chunk["type"] == "tool_result" and tool_limit_reached:
                    # 通知前端达到限制
                    yield {
                        "type": "tool_limit",
                        "data": f"已达到最大调用次数({self.max_tool_calls}次)"
                    }
                
                # 如果流结束且达到限制，需要生成最终总结
                if chunk["type"] == "done" and tool_limit_reached:
                    # 第二阶段：生成最终总结（无工具）
                    yield {"type": "final_summary_start", "data": "正在生成最终答案..."}
                    
                    # 临时禁用工具
                    original_tool_choice = self.llm.tool_choice
                    self.llm.tool_choice = "none"
                    
                    try:
                        # 添加总结提示
                        self.llm.add_message(
                            "system", 
                            "请基于以上所有搜索结果，给出全面、准确的最终回答。"
                        )
                        
                        # 生成最终总结
                        async for summary_chunk in self.llm.chat_stream():
                            if summary_chunk["type"] == "content":
                                yield {
                                    "type": "final_summary",
                                    "data": summary_chunk["data"]
                                }
                            elif summary_chunk["type"] == "done":
                                yield summary_chunk
                                break
                    finally:
                        # 恢复原始设置
                        self.llm.tool_choice = original_tool_choice
                        # 移除临时的系统消息
                        if self.llm.conversation_history[-2]["role"] == "system":
                            self.llm.conversation_history.pop(-2)
                        
        except Exception as e:
            yield {"type": "error", "data": f"处理消息时出错: {str(e)}"}
    
    async def process_message(self, user_input: str) -> str:
        """非流式处理单条用户消息（适配LLM类）"""
        self.tool_call_count = 0
        tools_to_use = None if self.tool_choice == "none" else tools
        
        try:
            # 创建受限的工具函数映射
            limited_tool_functions = {}
            tool_limit_reached = False
            
            for name, func in self.tool_functions.items():
                async def limited_wrapper(*args, _original_func=func, _name=name, **kwargs):
                    nonlocal tool_limit_reached
                    
                    self.tool_call_count += 1
                    
                    if asyncio.iscoroutinefunction(_original_func):
                        result = await _original_func(*args, **kwargs)
                    else:
                        result = _original_func(*args, **kwargs)
                    
                    if self.tool_call_count >= self.max_tool_calls:
                        tool_limit_reached = True
                        result += f"\n\n[系统提示：已达到最大搜索次数{self.max_tool_calls}次]"
                    
                    return result
                
                limited_tool_functions[name] = limited_wrapper
            
            # 第一阶段：执行带工具的对话
            result = await self.llm.chat_with_tools(
                user_input=user_input,
                tools=tools_to_use,
                tool_functions=limited_tool_functions,
                stream=False
            )
            
            # 第二阶段：如果达到限制，生成最终总结
            if tool_limit_reached:
                print("\n[生成最终总结]:")
                
                # 临时禁用工具
                original_tool_choice = self.llm.tool_choice
                self.llm.tool_choice = "none"
                
                try:
                    # 添加总结提示并生成最终回答
                    self.llm.add_message(
                        "user",
                        "请基于以上所有搜索结果，给出全面、准确的最终回答。"
                    )
                    
                    final_response = await self.llm.chat(
                        tools=None,
                        stream=False
                    )
                    
                    final_result = final_response.content
                    print(final_result)
                    
                    # 清理临时添加的消息
                    self.llm.conversation_history.pop()  # 移除临时user消息
                    self.llm.conversation_history.pop()  # 移除生成的assistant消息
                    
                    # 将最终结果作为原始请求的回复添加到历史
                    self.llm.conversation_history[-1] = {
                        "role": "assistant",
                        "content": final_result
                    }
                    
                    return final_result
                    
                finally:
                    self.llm.tool_choice = original_tool_choice
            
            return result
            
        except Exception as e:
            return f"处理消息时出错: {str(e)}"

# ============================================
# 测试入口
# ============================================

async def test_stream():
    """测试流式输出"""
    agent = WebSearchAgent(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",
        tool_choice="auto",
        max_tool_calls=2,  # 设置较小的值便于测试
        stream=True
    )
    
    print("=== 流式测试 ===\n")
    test_queries = [
        "今天北京的天气怎么样？",
        "最新的AI发展趋势是什么？给我详细分析一下各个方面。"  # 这个会触发多次搜索
    ]
    
    for query in test_queries:
        print(f"\n用户: {query}\n")
        print("助手: ", end="")
        
        async for chunk in agent.process_message_stream(query):
            if chunk["type"] == "content":
                print(chunk["data"], end="", flush=True)
            elif chunk["type"] == "tool_executing":
                print(f"\n🔧 执行工具: {chunk['data']['name']}")
                print(f"   参数: {chunk['data']['arguments']}")
            elif chunk["type"] == "tool_result":
                print(f"   结果预览: {chunk['data']['result'][:100]}...")
                print("\n继续生成: ", end="")
            elif chunk["type"] == "tool_limit":
                print(f"\n⚠️ {chunk['data']}")
            elif chunk["type"] == "final_summary_start":
                print(f"\n📝 {chunk['data']}\n最终答案: ", end="")
            elif chunk["type"] == "final_summary":
                print(chunk["data"], end="", flush=True)
        
        print("\n" + "="*60)
        
        # 重置会话以测试下一个查询
        agent.reset_session()

async def test_non_stream():
    """测试非流式输出"""
    agent = WebSearchAgent(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",
        tool_choice="auto",
        max_tool_calls=2,
        stream=False
    )
    
    print("\n=== 非流式测试 ===\n")
    result = await agent.process_message("分析一下2024年的全球经济形势")
    print(f"\n最终结果长度: {len(result)} 字符")

async def main():
    """主测试函数"""
    await test_stream()
    await test_non_stream()

if __name__ == "__main__":
    asyncio.run(main())