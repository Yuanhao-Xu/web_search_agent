"""
测试LLM调用Tavily搜索工具的能力
包括非流式和流式两种调用方式
"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm import LLM
from tools.tavily_search import tavily_search
from tools.function_schema import tools

async def test_non_stream():
    """测试非流式调用Tavily搜索"""
    print("="*60)
    print("🔍 测试非流式搜索")
    print("="*60)
    
    # 初始化LLM
    llm = LLM(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",  # DeepSeek API key
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        temperature=0.7
    )
    
    # 设置系统提示
    llm.add_message("system", """
    你是一个智能搜索助手。当用户询问需要实时信息的问题时，使用tavily_search工具进行搜索。
    搜索后，基于搜索结果给出简洁准确的回答。
    """)
    
    # 工具配置
    tools = tools
    tool_functions = {
        "tavily_search": tavily_search
    }
    
    # 测试查询
    query = "2024年诺贝尔物理学奖获得者是谁？他们的主要贡献是什么？"
    print(f"[用户]: {query}\n")
    
    # 非流式调用
    response = await llm.chat_complete(
        user_input=query,
        tools=tools,
        tool_functions=tool_functions,
        verbose=True,  # 打印详细信息
        max_tool_rounds=2  # 最多2轮搜索
    )
    
    print(f"\n[最终回答]: {response}")
    
    # 打印对话历史
    print("\n📝 对话历史：")
    for i, msg in enumerate(llm.get_history(), 1):
        role = msg['role']
        content = msg.get('content', '')
        if content:
            content_preview = content[:100] + "..." if len(content) > 100 else content
            print(f"{i}. [{role}]: {content_preview}")
        if 'tool_calls' in msg:
            print(f"   [工具调用]: {msg['tool_calls'][0]['function']['name']}")

async def test_stream():
    """测试流式调用Tavily搜索"""
    print("\n" + "="*60)
    print("🔄 测试流式搜索")
    print("="*60)
    
    # 初始化新的LLM实例
    llm = LLM(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        temperature=0.7
    )
    
    # 设置系统提示
    llm.add_message("system", """
    你是一个智能搜索助手。使用tavily_search工具获取最新信息。
    基于搜索结果提供准确的答案。
    """)
    
    # 工具配置
    tools = tools
    tool_functions = {
        "tavily_search": tavily_search
    }
    
    # 测试查询
    query = "今天的科技新闻有哪些重要事件？"
    print(f"[用户]: {query}\n")
    
    # 流式调用
    print("[助手]: ", end="", flush=True)
    
    async for chunk in llm.chat_stream(
        user_input=query,
        tools=tools,
        tool_functions=tool_functions,
        max_tool_rounds=2
    ):
        if chunk["type"] == "content":
            # 实时输出文本内容
            print(chunk["data"], end="", flush=True)
        
        elif chunk["type"] == "tool_execution_start":
            print("\n[系统]: 开始执行工具调用...")
        
        elif chunk["type"] == "tool_executing":
            tool_name = chunk["data"]["name"]
            args = chunk["data"].get("arguments", {})
            print(f"[工具]: 调用 {tool_name}")
            if "query" in args:
                print(f"        搜索词: {args['query']}")
        
        elif chunk["type"] == "tool_result":
            result_preview = chunk["data"]["result"][:200] + "..."
            print(f"[结果]: {result_preview}")
            print("[助手]: ", end="", flush=True)
        
        elif chunk["type"] == "continue_generation":
            round_num = chunk["data"]["round"]
            print(f"\n[系统]: 继续生成（第{round_num}轮）...")
            print("[助手]: ", end="", flush=True)
        
        elif chunk["type"] == "system_info":
            print(f"\n[系统]: {chunk['data']}")
            print("[助手]: ", end="", flush=True)
    
    print()  # 换行

async def test_multi_round_search():
    """测试多轮搜索能力"""
    print("\n" + "="*60)
    print("🔄 测试多轮搜索对话")
    print("="*60)
    
    llm = LLM(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        temperature=0.7
    )
    
    llm.add_message("system", "你是一个研究助手，可以进行深入的信息搜索和分析。")
    
    tools = [tavily_search_schema]
    tool_functions = {"tavily_search": tavily_search}
    
    # 第一个问题
    print("[用户]: 什么是量子计算？")
    response1 = await llm.chat_complete(
        user_input="什么是量子计算？",
        tools=tools,
        tool_functions=tool_functions,
        verbose=False
    )
    print(f"[助手]: {response1}\n")
    
    # 后续问题（基于上下文）
    print("[用户]: 它与传统计算有什么区别？")
    response2 = await llm.chat_complete(
        user_input="它与传统计算有什么区别？",
        tools=tools,
        tool_functions=tool_functions,
        verbose=False
    )
    print(f"[助手]: {response2}\n")
    
    # 需要新搜索的问题
    print("[用户]: 目前有哪些公司在研发量子计算机？")
    response3 = await llm.chat_complete(
        user_input="目前有哪些公司在研发量子计算机？",
        tools=tools,
        tool_functions=tool_functions,
        verbose=True,
        max_tool_rounds=2
    )
    print(f"\n[最终回答]: {response3}")

async def main():
    """主测试函数"""
    print("\n🚀 开始测试 LLM + Tavily 搜索工具\n")
    
    # 检查环境变量
    if not os.getenv("TAVILY_API_KEY"):
        print("⚠️ 警告: 未设置 TAVILY_API_KEY 环境变量")
        print("请设置: export TAVILY_API_KEY='your-api-key'")
        print("继续测试（可能会失败）...\n")
    
    try:
        # 测试非流式
        await test_non_stream()
        
        # 测试流式
        await test_stream()
        
        # 测试多轮对话
        await test_multi_round_search()
        
        print("\n✅ 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 设置 Tavily API Key（如果还没设置）
    if not os.getenv("TAVILY_API_KEY"):
        # 这里替换为你的实际 API key
        os.environ["TAVILY_API_KEY"] = "tvly-YOUR_ACTUAL_API_KEY"
    
    asyncio.run(main())