"""
WebSearchAgent - 网络搜索智能代理主程序
使用dataclass进行配置管理的生产级实现
"""

import asyncio
import os
import sys
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from llm import LLM
from tools import tools, tool_functions

# ============================================
# 配置管理
# ============================================

@dataclass
class AgentConfig:
    """代理配置 - 使用dataclass管理所有配置项
    
    优先级: 命令行参数 > 环境变量 > 配置文件 > 默认值
    """
    # API配置
    api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", "sk-f5889d58c6db4dd38ca78389a6c7a7e8"))
    base_url: str = field(default_factory=lambda: os.getenv("API_BASE_URL", "https://api.deepseek.com/v1"))
    model: str = field(default_factory=lambda: os.getenv("MODEL", "deepseek-chat"))
    
    # 行为配置
    stream: bool = field(default_factory=lambda: os.getenv("STREAM", "false").lower() == "true")
    temperature: float = field(default_factory=lambda: float(os.getenv("TEMPERATURE", "0.7")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("MAX_TOKENS", "4096")))
    max_tool_calls: int = field(default_factory=lambda: int(os.getenv("MAX_TOOL_CALLS", "3")))
    
    # 系统配置
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    log_file: Optional[str] = field(default_factory=lambda: os.getenv("LOG_FILE"))
    config_file: str = field(default="config.json")
    
    @classmethod
    def from_file(cls, path: str = "config.json") -> "AgentConfig":
        """从配置文件加载"""
        config_path = Path(path)
        if config_path.exists():
            with open(config_path, 'r') as f:
                data = json.load(f)
                return cls(**data)
        return cls()
    
    def save(self, path: Optional[str] = None):
        """保存配置到文件"""
        save_path = path or self.config_file
        with open(save_path, 'w') as f:
            # 过滤掉敏感信息
            data = asdict(self)
            data['api_key'] = "***" if self.api_key else ""
            json.dump(data, f, indent=2)
    
    def validate(self) -> bool:
        """验证配置有效性"""
        if not self.api_key or self.api_key == "***":
            raise ValueError("API密钥未设置")
        if not self.base_url:
            raise ValueError("API基础URL未设置")
        return True

# ============================================
# 日志配置
# ============================================

def setup_logging(config: AgentConfig) -> logging.Logger:
    """配置日志系统"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_level = logging.DEBUG if config.debug else logging.INFO
    
    handlers = [logging.StreamHandler()]
    if config.log_file:
        handlers.append(logging.FileHandler(config.log_file))
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )
    
    return logging.getLogger('WebSearchAgent')

# ============================================
# 核心代理类
# ============================================

class WebSearchAgent:
    """网络搜索智能代理
    
    架构特点:
    1. 单一职责 - 专注于搜索和对话功能
    2. 依赖注入 - 通过配置对象注入所有依赖
    3. 异步设计 - 全程使用async/await
    4. 错误恢复 - 完善的异常处理
    """
    
    def __init__(self, config: AgentConfig):
        """初始化代理
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = setup_logging(config)
        
        # 验证配置
        config.validate()
        
        # 初始化LLM
        self.llm = LLM(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            stream=config.stream,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            tool_choice="auto"
        )
        
        # 系统提示词
        self.system_prompt = """你是一个专业的网络搜索助手。

核心能力：
1. 智能判断是否需要搜索：常识问题直接回答，实时信息使用搜索工具
2. 高效使用搜索工具：精准构造搜索关键词，避免重复搜索
3. 综合分析能力：整合多个搜索结果，提供全面准确的答案

请根据用户问题的性质，自主决定最佳的回答策略。"""
        
        self.logger.info(f"WebSearchAgent初始化完成 - 模型: {config.model}")
    
    async def search(self, 
                    query: str, 
                    stream: Optional[bool] = None,
                    max_tool_calls: Optional[int] = None) -> str:
        """执行搜索查询
        
        Args:
            query: 用户查询
            stream: 是否流式输出（覆盖默认配置）
            max_tool_calls: 最大工具调用次数（覆盖默认配置）
            
        Returns:
            搜索结果或回答
        """
        use_stream = stream if stream is not None else self.config.stream
        use_max_calls = max_tool_calls if max_tool_calls is not None else self.config.max_tool_calls
        
        self.logger.debug(f"处理查询: {query[:100]}...")
        
        try:
            # 使用LLM的工具调用功能
            result = await self.llm.chat_with_tools(
                user_input=query,
                tools=tools,
                tool_functions=tool_functions,
                system_prompt=self.system_prompt,
                stream=use_stream,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            self.logger.debug("查询处理完成")
            return result
            
        except Exception as e:
            self.logger.error(f"查询处理失败: {e}")
            raise
    
    def clear_history(self):
        """清空对话历史"""
        self.llm.clear_history()
        self.logger.debug("对话历史已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            "model": self.config.model,
            "history_length": len(self.llm.conversation_history),
            "max_tool_calls": self.config.max_tool_calls
        }

# ============================================
# 交互界面
# ============================================

class InteractiveSession:
    """交互式会话管理器"""
    
    def __init__(self, agent: WebSearchAgent):
        """初始化会话
        
        Args:
            agent: WebSearchAgent实例
        """
        self.agent = agent
        self.commands = {
            'help': self.show_help,
            'clear': self.clear_history,
            'stats': self.show_stats,
            'stream': self.toggle_stream,
            'debug': self.toggle_debug,
            'save': self.save_config,
            'quit': self.quit
        }
        self.running = True
    
    async def run(self):
        """运行交互式会话"""
        self.show_welcome()
        
        while self.running:
            try:
                # 获取用户输入
                user_input = input("\n🔍 > ").strip()
                
                if not user_input:
                    continue
                
                # 检查是否是命令
                if user_input.startswith('/'):
                    await self.handle_command(user_input[1:])
                else:
                    # 处理查询
                    await self.handle_query(user_input)
                    
            except KeyboardInterrupt:
                print("\n\n使用 /quit 退出")
            except Exception as e:
                print(f"\n❌ 错误: {e}")
                self.agent.logger.error(f"会话错误: {e}", exc_info=True)
    
    async def handle_query(self, query: str):
        """处理用户查询"""
        print("\n💭 思考中", end="")
        
        if self.agent.config.stream:
            print("...\n")
            result = await self.agent.search(query, stream=True)
        else:
            print("...")
            result = await self.agent.search(query, stream=False)
            print(f"\n📝 回答：\n{result}")
    
    async def handle_command(self, command: str):
        """处理命令"""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd in self.commands:
            await self.commands[cmd](args)
        else:
            print(f"未知命令: {cmd}。使用 /help 查看帮助")
    
    def show_welcome(self):
        """显示欢迎信息"""
        print("\n" + "="*60)
        print("🤖 WebSearchAgent - 网络搜索智能代理")
        print("="*60)
        print("\n输入问题进行搜索，或使用 /help 查看命令")
    
    async def show_help(self, args: str):
        """显示帮助信息"""
        print("\n📚 可用命令：")
        print("  /help     - 显示帮助")
        print("  /clear    - 清空对话历史")
        print("  /stats    - 显示统计信息")
        print("  /stream   - 切换流式输出")
        print("  /debug    - 切换调试模式")
        print("  /save     - 保存当前配置")
        print("  /quit     - 退出程序")
    
    async def clear_history(self, args: str):
        """清空历史"""
        self.agent.clear_history()
        print("✅ 对话历史已清空")
    
    async def show_stats(self, args: str):
        """显示统计"""
        stats = self.agent.get_stats()
        print("\n📊 统计信息：")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    async def toggle_stream(self, args: str):
        """切换流式输出"""
        self.agent.config.stream = not self.agent.config.stream
        status = "开启" if self.agent.config.stream else "关闭"
        print(f"✅ 流式输出已{status}")
    
    async def toggle_debug(self, args: str):
        """切换调试模式"""
        self.agent.config.debug = not self.agent.config.debug
        # 更新日志级别
        level = logging.DEBUG if self.agent.config.debug else logging.INFO
        self.agent.logger.setLevel(level)
        status = "开启" if self.agent.config.debug else "关闭"
        print(f"✅ 调试模式已{status}")
    
    async def save_config(self, args: str):
        """保存配置"""
        try:
            self.agent.config.save(args if args else None)
            print(f"✅ 配置已保存到 {args or self.agent.config.config_file}")
        except Exception as e:
            print(f"❌ 保存失败: {e}")
    
    async def quit(self, args: str):
        """退出程序"""
        print("\n👋 再见！")
        self.running = False

# ============================================
# 主函数
# ============================================

async def main():
    """主函数 - 程序入口
    
    执行流程：
    1. 加载配置（支持多种来源）
    2. 初始化代理
    3. 处理命令行参数或进入交互模式
    """
    
    # 加载配置
    config = AgentConfig()
    
    # 尝试从文件加载配置（如果存在）
    if Path(config.config_file).exists():
        try:
            config = AgentConfig.from_file(config.config_file)
            print(f"✅ 已加载配置文件: {config.config_file}")
        except Exception as e:
            print(f"⚠️ 配置文件加载失败，使用默认配置: {e}")
    
    # 处理命令行参数（简单方式）
    if len(sys.argv) > 1:
        # 单次查询模式
        query = " ".join(sys.argv[1:])
        
        try:
            agent = WebSearchAgent(config)
            print(f"\n🔍 搜索: {query}")
            result = await agent.search(query)
            if not config.stream:
                print(f"\n📝 结果:\n{result}")
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            sys.exit(1)
    else:
        # 交互模式
        try:
            agent = WebSearchAgent(config)
            session = InteractiveSession(agent)
            await session.run()
        except Exception as e:
            print(f"\n❌ 启动失败: {e}")
            sys.exit(1)

# ============================================
# 快速启动函数
# ============================================

def quick_start(api_key: Optional[str] = None):
    """快速启动函数 - 一行代码启动
    
    Usage:
        from main import quick_start
        quick_start("your-api-key")
    """
    if api_key:
        os.environ["DEEPSEEK_API_KEY"] = api_key
    asyncio.run(main())

# ============================================
# 程序入口
# ============================================

if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())