# 0907


"""Web搜索Agent会话层"""

import asyncio
import json
from typing import Optional, Dict, List, Literal, Any
from enum import Enum
from llm import LLM
from tools.tavily_search import tavily_search
from tools.function_schema import tools

class ToolMode(Enum):
    """工具调用模式"""
    NEVER = "never"          # 从不调用
    AUTO = "auto"            # 自动决定
    ALWAYS = "always"        # 始终调用

# 该枚举类ToolMode用于定义Web搜索Agent的工具调用模式：
# NEVER  表示从不调用工具，始终只用大模型对话；
# AUTO   表示由大模型自动决定是否需要调用工具（如遇到需要实时信息时）；
# ALWAYS 表示每次对话都强制调用工具（如搜索）并基于工具结果作答。
# 这样可以灵活控制Agent是否以及何时调用外部工具（如搜索API），以适应不同的业务场景和需求。

class WebSearchAgent:
    """Web搜索Agent会话管理类"""
    
    def __init__(self,
                 api_key: str,
                 base_url: str = "https://api.deepseek.com/v1",
                 model: str = "deepseek-chat",
                 tool_mode: ToolMode = ToolMode.AUTO,
                 max_tool_calls: int = 3,
                 temperature: float = 0.7,
                 max_tokens: int = 4096,
                 stream: bool = True):
        """
        Args:
            api_key: DeepSeek API密钥
            base_url: API基础URL
            model: 模型名称
            tool_mode: 工具调用模式
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
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
        
        self.tool_mode = tool_mode
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
当用户询问需要实时信息的问题时，你会使用搜索工具。
请基于搜索结果提供准确、有帮助的回答。"""
        
        # 初始化时注入系统提示
        if not self.llm.conversation_history:
            self.llm.add_message("system", self.system_prompt)
    
    def reset_session(self):
        """重置会话状态"""
        self.llm.clear_history()
        self.tool_call_count = 0
        # 重新注入系统提示
        self.llm.add_message("system", self.system_prompt)
        print("✨ 会话已重置\n")
    
    def set_tool_mode(self, mode: ToolMode):
        """设置工具调用模式"""
        self.tool_mode = mode
        print(f"🔧 工具模式设置为: {mode.value}\n")
    # 在process_message方法中，会根据self.tool_mode的值决定是否调用工具（如tavily_search）。
    # 通过set_tool_mode方法可以动态修改self.tool_mode，从而真正改变了工具调用模式。
    # 例如，设置为ToolMode.NEVER时，模型不会调用工具；设置为ToolMode.ALWAYS时，每次都强制调用工具；AUTO则让模型自行决定。
    
    def set_max_tool_calls(self, max_calls: int):
        """设置最大工具调用次数"""
        self.max_tool_calls = max_calls
        print(f"📊 最大工具调用次数设置为: {max_calls}\n")
    
    def set_stream_mode(self, stream: bool):
        """设置流式输出模式"""
        self.llm.stream = stream
        mode_str = "流式" if stream else "非流式"
        print(f"📡 输出模式设置为: {mode_str}\n")
    
    def _add_tool_message(self, content: str, tool_call_id: str):
        """安全地添加工具消息到历史"""
        self.llm.conversation_history.append({
            "role": "tool",
            "content": content,
            "tool_call_id": tool_call_id
        })
    
    async def process_message(self, user_input: str) -> str:
        """处理单条用户消息
        
        Args:
            user_input: 用户输入
            
        Returns:
            str: Agent响应
        """
        # 重置单次对话的工具调用计数
        self.tool_call_count = 0
        
        # 添加用户消息
        self.llm.add_message("user", user_input)
        
        # 根据工具模式决定是否使用工具
        if self.tool_mode == ToolMode.NEVER:
            # 不使用工具，直接对话
            response = await self._chat_without_tools()
        elif self.tool_mode == ToolMode.ALWAYS:
            # 始终使用工具
            response = await self._chat_with_tools(force_tool=True)
        else:  # AUTO模式
            # 让模型决定是否使用工具
            response = await self._chat_with_tools(force_tool=False)
        
        return response
    
    async def _chat_without_tools(self) -> str:
        """不使用工具的对话"""
        response = await self.llm.chat(stream=self.llm.stream)
        
        if self.llm.stream:
            # 流式已在chat方法中打印
            return response.content or ""
        else:
            content = response.content or ""
            print(f"[助手]: {content}")
            return content
    
    async def _chat_with_tools(self, force_tool: bool = False) -> str:
        """使用工具的对话"""
        final_response = ""
        
        # 特殊情况处理
        if self.max_tool_calls == 0:
            # 当工具调用次数为0时，直接生成回答，不使用任何工具
            print("🔧 工具调用次数为0，直接生成回答...")
            response = await self.llm.chat(
                tools=None,
                stream=self.llm.stream
            )
            final_response = response.content or ""
            if not self.llm.stream:
                print(f"[助手]: {final_response}")
            else:
                print()
            return final_response
        while self.tool_call_count < self.max_tool_calls:
            # 设置工具选择模式
            if force_tool:
                tool_choice = "required"  # ALWAYS 模式下始终强制使用工具
            else:
                tool_choice = "auto"      # AUTO 模式下让模型决定
            
            # 调用模型
            if self.llm.stream:
                print("[助手]: ", end="")
            
            response = await self.llm.chat(
                tools=tools,
                tool_choice=tool_choice,
                stream=self.llm.stream
            )
            
            # 如果没有工具调用，返回响应
            if not response.tool_calls:
                final_response = response.content or ""
                if not self.llm.stream:
                    print(f"[助手]: {final_response}")
                else:
                    print()  # 流式输出后换行
                break
            
            # 执行工具调用
            if self.llm.stream:
                print("\n")
            
            print(f"[执行搜索] (第{self.tool_call_count + 1}次)")
            
            for tool_call in response.tool_calls:
                func_name = tool_call.function.name
                
                # 安全解析JSON参数
                try:
                    func_args = json.loads(tool_call.function.arguments or "{}")
                except Exception as e:
                    error_msg = f"工具参数解析失败: {e}"
                    print(f"  ❌ {error_msg}")
                    self._add_tool_message(error_msg, tool_call.id)
                    continue
                
                if func_name in self.tool_functions:
                    # 执行工具
                    try:
                        if asyncio.iscoroutinefunction(self.tool_functions[func_name]):
                            result = await self.tool_functions[func_name](**func_args)
                        else:
                            result = self.tool_functions[func_name](**func_args)
                        
                        # 使用封装方法添加工具结果
                        self._add_tool_message(str(result), tool_call.id)
                        
                        # 简短显示搜索参数
                        print(f"  搜索: {func_args.get('query', 'N/A')}")
                        self.tool_call_count += 1
                    except Exception as e:
                        error_msg = f"工具执行失败: {e}"
                        print(f"  ❌ {error_msg}")
                        self._add_tool_message(error_msg, tool_call.id)
                else:
                    error_msg = f"未知工具: {func_name}"
                    print(f"  ❌ {error_msg}")
                    self._add_tool_message(error_msg, tool_call.id)
            
            # 如果达到最大调用次数，强制生成最终回答
            if self.tool_call_count >= self.max_tool_calls:
                print(f"\n⚠️ 已达到最大工具调用次数({self.max_tool_calls}次)，生成最终回答...\n")
                
                # 添加上限提示到历史
                self._add_tool_message(
                    f"[系统提示] 已达到工具调用上限({self.max_tool_calls}次)，请基于现有信息生成回答。",
                    "system_limit"
                )
                
                if self.llm.stream:
                    print("[最终回答]: ", end="")
                
                # 不再提供工具，强制生成答案
                final_resp = await self.llm.chat(
                    tools=None,  # 不提供工具
                    stream=self.llm.stream
                )
                final_response = final_resp.content or ""
                
                if not self.llm.stream:
                    print(f"[最终回答]: {final_response}")
                else:
                    print()
                break
        
        return final_response
    
    async def run_interactive(self):
        """运行交互式会话"""
        print("="*60)
        print("🤖 Web搜索Agent - 交互式会话")
        print("="*60)
        print("命令说明:")
        print("  /reset    - 清空对话历史")
        print("  /mode     - 切换工具调用模式")
        print("  /stream   - 切换流式/非流式输出")
        print("  /max N    - 设置最大工具调用次数(N为数字)")
        print("  /history  - 查看对话历史")
        print("  /exit     - 退出会话")
        print(f"\n当前设置: 工具模式={self.tool_mode.value}, 流式={self.llm.stream}, 最大调用={self.max_tool_calls}次")
        print("="*60 + "\n")
        
        # 添加系统提示（如果历史为空）
        if not self.llm.conversation_history:
            self.llm.add_message("system", self.system_prompt)
        
        while self.session_active:
            try:
                # 获取用户输入
                user_input = input("\n[用户]: ").strip()
                
                if not user_input:
                    continue
                
                # 处理命令
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue
                
                # 处理普通消息
                print()
                await self.process_message(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 会话已中断")
                break
            except Exception as e:
                print(f"\n❌ 发生错误: {str(e)}")
                continue
    
    async def _handle_command(self, command: str):
        """处理命令"""
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()
        
        if cmd == "/exit":
            print("👋 再见！")
            self.session_active = False
            
        elif cmd == "/reset":
            self.reset_session()
            
        elif cmd == "/mode":
            print("\n选择工具调用模式:")
            print("1. never  - 从不调用工具")
            print("2. auto   - 自动决定(默认)")
            print("3. always - 始终调用工具")
            
            choice = input("请选择(1/2/3): ").strip()
            mode_map = {"1": ToolMode.NEVER, "2": ToolMode.AUTO, "3": ToolMode.ALWAYS}
            
            if choice in mode_map:
                self.set_tool_mode(mode_map[choice])
            else:
                print("⚠️ 无效选择")
                
        elif cmd == "/stream":
            current = self.llm.stream
            self.set_stream_mode(not current)
            
        elif cmd == "/max":
            if len(cmd_parts) > 1 and cmd_parts[1].isdigit():
                self.set_max_tool_calls(int(cmd_parts[1]))
            else:
                print("⚠️ 请提供有效数字，如: /max 5")
                
        elif cmd == "/history":
            print("\n📜 对话历史:")
            for i, msg in enumerate(self.llm.get_history(), 1):
                role = msg["role"]
                content = msg.get("content", "")
                
                if role == "tool":
                    # 工具结果简化显示
                    print(f"{i}. [{role}]: <搜索结果...>")
                elif content:
                    # 普通消息截断显示
                    display = content[:100] + "..." if len(content) > 100 else content
                    print(f"{i}. [{role}]: {display}")
                elif msg.get("tool_calls"):
                    print(f"{i}. [{role}]: <调用工具>")
        else:
            print(f"⚠️ 未知命令: {cmd}")

# ============================================
# FastAPI适配接口
# ============================================

class SessionManager:
    """会话管理器 - 用于FastAPI集成"""
    
    def __init__(self):
        self.sessions: Dict[str, WebSearchAgent] = {}
    
    def create_session(self, 
                       session_id: str,
                       api_key: str,
                       **kwargs) -> WebSearchAgent:
        """创建新会话"""
        # 转换工具模式字符串为枚举
        if 'tool_mode' in kwargs and isinstance(kwargs['tool_mode'], str):
            kwargs['tool_mode'] = ToolMode(kwargs['tool_mode'])
            
        session = WebSearchAgent(api_key=api_key, **kwargs)
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[WebSearchAgent]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    async def process_request(self,
                             session_id: str,
                             message: str,
                             create_if_not_exists: bool = True,
                             api_key: Optional[str] = None,
                             **session_kwargs) -> Dict[str, Any]:
        """处理请求 - FastAPI友好接口
        
        Returns:
            Dict包含: success, response, session_id, error
        """
        try:
            # 获取或创建会话
            session = self.get_session(session_id)
            if not session and create_if_not_exists:
                if not api_key:
                    return {
                        "success": False,
                        "error": "需要提供api_key创建新会话"
                    }
                session = self.create_session(session_id, api_key, **session_kwargs)
            elif not session:
                return {
                    "success": False,
                    "error": "会话不存在"
                }
            
            # 处理消息
            response = await session.process_message(message)
            
            return {
                "success": True,
                "response": response,
                "session_id": session_id,
                "tool_calls": session.tool_call_count
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

# ============================================
# 测试入口
# ============================================

async def main():
    """测试入口"""
    agent = WebSearchAgent(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",  
        tool_mode=ToolMode.AUTO,
        max_tool_calls=3,
        stream=True
    )
    
    await agent.run_interactive()

if __name__ == "__main__":
    asyncio.run(main())