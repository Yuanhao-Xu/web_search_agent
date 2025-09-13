"""
WebSearchAgent - 简化的网络搜索智能体
核心设计：
1. 单一类实现，无复杂继承
2. 充分利用LLM类的记忆管理
3. 支持流式和非流式
4. 保证最终答案输出
"""

import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from llm import LLM
from tools.tavily_search import tavily_search
from tools.function_schema import tools

class WebSearchAgent:
    """简化的网络搜索智能体"""
    
    def __init__(self, 
                 api_key: str,
                 base_url: str,
                 model: str = "deepseek-chat",
                 max_search_rounds: int = 5,
                 temperature: float = 0.7):
        """
        初始化WebSearchAgent
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            max_search_rounds: 最大搜索轮数
            temperature: 生成温度
        """
        # 初始化LLM
        self.llm = LLM(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature
        )
        
        self.max_search_rounds = max_search_rounds
        
        # 准备工具
        self._prepare_tools()
        
    def _prepare_tools(self):
        """准备工具集"""
        # 直接使用导入的tools
        self.tools = tools
        
        # 工具函数映射
        self.tool_functions = {
            "tavily_search": tavily_search,
            "terminate": self._terminate
        }
    
    async def _terminate(self):
        """终止工具"""
        return "搜索完成，准备生成最终答案"
    
    def _create_system_prompt(self):
        """创建搜索专用系统提示"""
        return """你是一个智能搜索助手。你可以使用以下工具：
1. tavily_search: 搜索互联网获取最新信息
2. terminate: 当收集到足够信息后结束搜索

搜索策略：
- 首先分析用户问题，确定需要搜索的关键信息
- 使用不同的搜索词进行多角度搜索
- 当收集到足够信息能够全面回答用户问题时，调用terminate结束搜索
- 如果搜索3-4轮仍未找到满意答案，也应该terminate并基于已有信息回答

重要：每次搜索后都要评估是否已有足够信息，避免不必要的重复搜索。"""
    
    def _called_terminate(self, response):
        """检查是否调用了terminate工具"""
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function.name == "terminate":
                    return True
        return False
    
    def _should_continue(self, response, current_round):
        """判断是否继续搜索"""
        # 检查是否调用了terminate
        if self._called_terminate(response):
            return False
        
        # 检查是否达到最大轮数
        if current_round >= self.max_search_rounds - 1:
            return False
        
        # 检查是否有工具调用
        if not hasattr(response, 'tool_calls') or not response.tool_calls:
            return False
        
        return True
    
    async def search(self, query: str, stream: bool = False, clear_history: bool = True):
        """
        执行搜索
        
        Args:
            query: 用户查询
            stream: 是否流式输出
            clear_history: 是否清空历史
            
        Returns:
            非流式: 返回最终答案字符串
            流式: 返回异步生成器
        """
        if clear_history:
            self.clear_history()
        
        if stream:
            return self._search_stream(query)
        else:
            return await self._search_complete(query)
    
    async def _search_complete(self, query: str) -> str:
        """非流式搜索"""
        # 设置系统提示
        system_prompt = self._create_system_prompt()
        
        # 初始用户输入
        print(f"[用户]: {query}")
        print("[搜索助手]: 正在分析问题并搜索相关信息...\n")
        
        # 搜索循环
        rounds = 0
        terminated = False
        
        while rounds < self.max_search_rounds:
            # 调用LLM
            response = await self.llm.chat_complete(
                user_input=query if rounds == 0 else None,
                system_prompt=system_prompt if rounds == 0 else None,
                tools=self.tools,
                tool_functions=self.tool_functions,
                use_history=True,
                verbose=True
            )
            
            # 检查是否继续
            if self._called_terminate(response):
                terminated = True
                break
            
            # 检查是否有工具调用
            if not hasattr(response, 'tool_calls') or not response.tool_calls:
                break
                
            rounds += 1
        
        # 生成最终答案
        if not terminated and rounds >= self.max_search_rounds:
            print("\n[达到最大搜索轮数，生成最终答案...]")
        
        # 强制生成最终答案（无工具）
        final_prompt = """基于以上所有搜索结果，请给出全面准确的最终答案。
不要说"需要更多搜索"或"信息不足"。
请直接回答用户的问题。"""
        
        final_response = await self.llm.chat_complete(
            user_input=final_prompt,
            tools=self.tools,
            tool_choice="none",  # 禁用工具
            use_history=True,
            verbose=False
        )
        
        # 获取最终文本
        if hasattr(final_response, 'content'):
            result = final_response.content
        else:
            result = str(final_response)
        
        print(f"\n[最终答案]: {result}")
        return result
    
    async def _search_stream(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """流式搜索"""
        # 设置系统提示
        system_prompt = self._create_system_prompt()
        
        # 初始化
        rounds = 0
        terminated = False
        first_round = True
        
        # 发送开始事件
        yield {"type": "search_start", "data": {"query": query}}
        
        while rounds < self.max_search_rounds:
            # 收集本轮的工具调用
            tool_calls_in_round = []
            content_in_round = []
            
            # 调用LLM流式接口
            async for event in self.llm.chat_stream(
                user_input=query if first_round else None,
                system_prompt=system_prompt if first_round else None,
                tools=self.tools,
                tool_functions=self.tool_functions,
                use_history=True
            ):
                # 透传事件
                if event["type"] == "content":
                    content_in_round.append(event["data"])
                    yield event
                elif event["type"] == "tool_executing":
                    # 检查是否是terminate
                    if event["data"]["name"] == "terminate":
                        terminated = True
                    yield event
                elif event["type"] == "tool_result":
                    yield event
                elif event["type"] == "tool_call_complete":
                    tool_calls_in_round.append(event["data"])
                elif event["type"] == "done":
                    # 本轮结束
                    if terminated:
                        break
                    if not event["data"].get("tool_calls"):
                        break
            
            first_round = False
            
            if terminated:
                break
                
            # 检查是否有工具调用
            if not tool_calls_in_round:
                break
                
            rounds += 1
        
        # 生成最终答案
        if not terminated and rounds >= self.max_search_rounds:
            yield {"type": "max_rounds_reached", "data": {"rounds": rounds}}
        
        # 发送最终答案开始信号
        yield {"type": "final_answer_start", "data": {}}
        
        # 强制生成最终答案
        final_prompt = """基于所有搜索结果，给出全面准确的最终答案。
直接回答用户的问题。"""
        
        async for event in self.llm.chat_stream(
            user_input=final_prompt,
            tools=self.tools,
            tool_choice="none",  # 禁用工具
            use_history=True
        ):
            if event["type"] == "content":
                yield {"type": "final_answer", "data": event["data"]}
            elif event["type"] == "done":
                yield {"type": "search_complete", "data": {}}
    
    def clear_history(self):
        """清空对话历史"""
        self.llm.clear_history()
    
    def get_history(self):
        """获取对话历史"""
        return self.llm.get_history()


# ============================================
# 使用示例
# ============================================

async def test_non_stream():
    """测试非流式搜索"""
    agent = WebSearchAgent(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",
        base_url="https://api.deepseek.com/v1",
        max_search_rounds=3
    )
    
    result = await agent.search(
        "2024年诺贝尔物理学奖获得者是谁？他们的主要贡献是什么？",
        stream=False
    )
    print(f"\n最终结果: {result}")

async def test_stream():
    """测试流式搜索"""
    agent = WebSearchAgent(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8", 
        base_url="https://api.deepseek.com/v1",
        max_search_rounds=3
    )
    
    print("[开始流式搜索测试]")
    print("查询: 今天北京的天气如何？有什么适合的户外活动？\n")
    
    async for event in agent.search(
        "今天北京的天气如何？有什么适合的户外活动？",
        stream=True
    ):
        if event["type"] == "search_start":
            print(f"[开始搜索]: {event['data']['query']}")
        elif event["type"] == "content":
            print(event["data"], end="", flush=True)
        elif event["type"] == "tool_executing":
            print(f"\n[执行工具]: {event['data']['name']}")
            if event['data']['name'] == 'tavily_search':
                print(f"  搜索内容: {event['data']['arguments'].get('query', '')}")
        elif event["type"] == "tool_result":
            print(f"[工具结果]: 获取到搜索结果")
        elif event["type"] == "max_rounds_reached":
            print(f"\n[达到最大搜索轮数: {event['data']['rounds']}轮]")
        elif event["type"] == "final_answer_start":
            print("\n[生成最终答案]:")
        elif event["type"] == "final_answer":
            print(event["data"], end="", flush=True)
        elif event["type"] == "search_complete":
            print("\n\n[搜索完成]")

if __name__ == "__main__":
    # 运行测试
    print("="*60)
    print("WebSearchAgent 测试")
    print("="*60)
    
    # 测试非流式
    asyncio.run(test_non_stream())
    
    print("\n" + "="*60 + "\n")
    
    # 测试流式
    asyncio.run(test_stream())