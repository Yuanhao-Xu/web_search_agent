"""Web搜索Agent - 基于React框架的智能体实现（修复版）"""

import asyncio
import json
from typing import Optional, Dict, List, Literal, Any, AsyncGenerator, Callable
from llm_0908 import LLM
from tools.tavily_search import tavily_search
from tools.function_schema import tools

class WebSearchAgent:
    """Web搜索智能体 - 支持多轮工具调用和智能决策
    
    核心特性:
    - React框架：Think -> Act -> Observe 循环
    - 内置记忆管理：维护完整对话历史
    - 智能工具调用：自主决定何时使用工具
    - 流式/非流式：支持两种输出模式
    """
    
    def __init__(self,
                 api_key: str,
                 base_url: str = "https://api.deepseek.com/v1",
                 model: str = "deepseek-chat",
                 tool_choice: Literal["auto", "required", "none"] = "auto",
                 max_steps: int = 5,
                 temperature: float = 0.7,
                 max_tokens: int = 4096):
        """初始化智能体
        
        Args:
            max_steps: 最大执行步数（防止无限循环）
        """
        self.llm = LLM(
            api_key=api_key,
            base_url=base_url,
            model=model,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        self.max_steps = max_steps
        self.current_step = 0
        
        # 工具注册表
        self.tool_functions = {
            "tavily_search": tavily_search
        }
        
        # 系统提示词 - 定义智能体的行为模式
        self.system_prompt = """你是一个智能搜索助手，具备以下能力：

## 核心能力
1. **智能判断**：判断问题是否需要搜索互联网信息
2. **多轮搜索**：如果初次搜索不够充分，可以进行多轮搜索
3. **策略优化**：基于前次结果调整搜索策略

## 工作流程
1. **分析问题**：理解用户意图，判断是否需要实时信息
2. **执行搜索**：如需要，使用tavily_search工具获取信息
3. **评估结果**：判断搜索结果是否充分回答问题
4. **迭代优化**：如不充分，调整关键词继续搜索（最多{max_steps}轮）
5. **综合回答**：基于所有信息提供准确、全面的答案

## 决策原则
- 如果你的知识库能充分回答，直接回答无需搜索
- 如果涉及实时信息、最新动态，立即搜索
- 如果搜索结果充分，停止搜索并给出答案
- 如果搜索结果不足，优化搜索词继续搜索

## 重要提示
- 获得搜索结果后，必须基于结果生成完整的回答
- 不要在最终回答中说"让我搜索"或类似的话
- 直接给出答案，不要表达继续搜索的意愿""".format(max_steps=max_steps)
        
        # 初始化系统提示
        self._initialize_system_prompt()
    
    def _initialize_system_prompt(self):
        """初始化系统提示词"""
        self.llm.add_message("system", self.system_prompt)
    
    async def think(self, force_answer: bool = False) -> tuple[bool, Optional[str]]:
        """思考阶段：决定是否需要使用工具
        
        Args:
            force_answer: 是否强制生成答案（不使用工具）
        
        Returns:
            (是否需要工具, 助手回复内容)
        """
        # 构建提示
        next_step_prompt = self._build_next_step_prompt()
        
        # 决定是否提供工具（最后一步或强制回答时不提供）
        should_provide_tools = not force_answer and self.current_step < self.max_steps
        
        # 调用LLM
        response = await self.llm.chat_complete(
            user_input=next_step_prompt if self.current_step > 0 else None,
            tools=tools if should_provide_tools else None,
            tool_functions=self.tool_functions,
            use_history=True,
            verbose=False
        )
        
        # 判断是否有工具调用
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return True, None
        else:
            content = response if isinstance(response, str) else response.content
            return False, content
    
    async def act(self) -> List[Dict]:
        """行动阶段：执行工具调用"""
        results = []
        
        # 获取最新的助手消息
        last_message = self.llm.get_history()[-1]
        
        if not last_message.get("tool_calls"):
            return results
        
        # 执行每个工具调用
        for tool_call in last_message["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            
            print(f"🔧 执行工具: {tool_name}")
            print(f"   参数: {tool_args}")
            
            try:
                if asyncio.iscoroutinefunction(self.tool_functions[tool_name]):
                    result = await self.tool_functions[tool_name](**tool_args)
                else:
                    result = self.tool_functions[tool_name](**tool_args)
                
                # 添加工具结果到历史
                self.llm.add_message("tool", str(result), tool_call_id=tool_call["id"])
                
                results.append({
                    "tool": tool_name,
                    "result": str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                })
                
            except Exception as e:
                error_msg = f"工具执行失败: {str(e)}"
                self.llm.add_message("tool", error_msg, tool_call_id=tool_call["id"])
                results.append({"tool": tool_name, "error": error_msg})
        
        return results
    
    def _build_next_step_prompt(self) -> str:
        """构建引导提示词"""
        if self.current_step == 0:
            return ""
        elif self.current_step < self.max_steps:
            return "基于搜索结果，请直接给出完整的答案。如果信息不足可以继续搜索，但优先考虑直接回答。"
        else:
            return "总结以上所有信息给出最终答案"
    
    def run(self, user_input: str, stream: bool = False):
        """运行智能体"""
        if stream:
            return self._run_stream(user_input)
        else:
            return self._run_complete(user_input)
    
    async def _run_complete(self, user_input: str) -> str:
        """非流式运行"""
        self.current_step = 0
        
        # 添加用户输入
        self.llm.add_message("user", user_input)
        
        print(f"\n🤔 智能体开始处理: {user_input}\n")
        
        while self.current_step < self.max_steps:
            self.current_step += 1
            print(f"\n📍 步骤 {self.current_step}/{self.max_steps}")
            
            # Think: 思考是否需要工具
            needs_tool, content = await self.think()
            
            if needs_tool:
                # Act: 执行工具
                print("💭 决定使用工具...")
                tool_results = await self.act()
                
                if tool_results:
                    for result in tool_results:
                        if "error" in result:
                            print(f"   ❌ {result['tool']}: {result['error']}")
                        else:
                            print(f"   ✅ {result['tool']}: 获取结果成功")
                    
                    # 工具执行后，需要再次调用LLM生成基于结果的回答
                    if self.current_step == self.max_steps:
                        # 如果是最后一步，强制生成答案
                        _, final_answer = await self.think(force_answer=True)
                        if final_answer:
                            print(f"\n✨ 智能体完成思考")
                            return final_answer
                    continue
            
            # 如果有内容返回，说明智能体认为可以回答了
            if content:
                print(f"\n✨ 智能体完成思考")
                return content
        
        # 达到最大步数，强制生成答案
        print(f"\n⚠️ 达到最大步数，生成最终答案...")
        _, final_answer = await self.think(force_answer=True)
        return final_answer or "抱歉，我无法获取足够的信息来回答您的问题。"
    
    async def _run_stream(self, user_input: str) -> AsyncGenerator[Dict[str, Any], None]:
        """流式运行"""
        self.current_step = 0
        
        # 添加用户输入
        self.llm.add_message("user", user_input)
        
        yield {"type": "start", "data": f"开始处理: {user_input}"}
        
        while self.current_step < self.max_steps:
            self.current_step += 1
            yield {"type": "step", "data": f"步骤 {self.current_step}/{self.max_steps}"}
            
            # 流式思考
            has_tool_calls = False
            collected_content = []
            
            # 决定是否提供工具
            should_provide_tools = self.current_step < self.max_steps
            
            # 修复：第一步不需要额外提示
            extra_prompt = self._build_next_step_prompt() if self.current_step > 1 else None
            
            async for chunk in self.llm.chat_stream(
                user_input=extra_prompt,
                tools=tools if should_provide_tools else None,
                tool_functions=self.tool_functions,
                use_history=True
            ):
                if chunk["type"] == "content":
                    collected_content.append(chunk["data"])
                    yield chunk
                elif chunk["type"] == "tool_executing":
                    has_tool_calls = True
                    yield chunk
                elif chunk["type"] == "tool_result":
                    yield chunk
                elif chunk["type"] == "done":
                    # 如果执行了工具，需要继续下一轮
                    if has_tool_calls:
                        # 如果是最后一步，强制生成最终答案
                        if self.current_step == self.max_steps:
                            yield {"type": "generating_answer", "data": "生成最终答案..."}
                            async for chunk in self.llm.chat_stream(
                                user_input="基于所有搜索结果，请给出完整的答案。",
                                tools=None,  # 不提供工具
                                tool_functions=None,
                                use_history=True
                            ):
                                if chunk["type"] == "content":
                                    yield chunk
                                elif chunk["type"] == "done":
                                    yield {"type": "complete", "data": "完成"}
                                    return
                    elif collected_content:
                        # 没有工具调用且有内容，说明完成
                        yield {"type": "complete", "data": "".join(collected_content)}
                        return
        
        yield {"type": "max_steps_reached", "data": "达到最大步数限制"}
    
    def reset(self):
        """重置智能体状态"""
        self.llm.clear_history()
        self.current_step = 0
        self._initialize_system_prompt()
        print("✨ 智能体已重置\n")
    
    def get_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.llm.get_history()
    
    def set_max_steps(self, max_steps: int):
        """设置最大步数"""
        self.max_steps = max_steps
        print(f"📊 最大步数设置为: {max_steps}\n")

# 测试代码
async def test_agent():
    """测试重构后的智能体"""
    
    agent = WebSearchAgent(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",
        max_steps=3
    )
    
    # 测试1：非流式
    print("="*60)
    print("测试1: 非流式模式")
    print("="*60)
    
    result = await agent.run("2024年诺贝尔物理学奖获得者是谁？")
    print(f"\n最终答案:\n{result}")
    
    # 重置
    agent.reset()
    
    # 测试2：流式
    print("\n" + "="*60)
    print("测试2: 流式模式")
    print("="*60)
    
    async for chunk in agent.run("今天北京的天气怎么样？", stream=True):
        if chunk["type"] == "content":
            print(chunk["data"], end="", flush=True)
        elif chunk["type"] == "step":
            print(f"\n[{chunk['data']}]")
        elif chunk["type"] == "tool_executing":
            print(f"\n🔧 {chunk['data']}")
        elif chunk["type"] == "complete":
            print(f"\n✅ 完成")

if __name__ == "__main__":
    asyncio.run(test_agent())