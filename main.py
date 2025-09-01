from openai import OpenAI
from tavily import AsyncTavilyClient
import requests
import asyncio
import logging
from llm import LLM
import json

# 全局配置日志级别
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# Tavily搜索工具
# ============================================

async def tavily_search(query: str, max_results: int = 3) -> str:
    """Tavily异步网络搜索工具"""
    try:
        tavily_client = AsyncTavilyClient("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")
        
        response = await tavily_client.search(
            query=query,
            include_answer="advanced",
            max_results=max_results
        )
        logger.debug("搜索响应: %s", response)
        
        results = response.get("results", [])
        if not results:
            return f"未找到与'{query}'相关的结果"
        
        output = f"搜索：{query}\n找到{len(results)}个结果：\n\n"
        
        for i, result in enumerate(results, 1):
            output += f"【{i}】{result.get('title', '无标题')}\n"
            output += f"链接：{result.get('url', '')}\n"
            content = result.get('content', '')
            if len(content) > 200:
                content = content[:200] + "..."
            output += f"摘要：{content}\n\n"
        
        return output
        
    except Exception as e:
        return f"搜索出错：{str(e)}"

# 工具的function schema
tools = [{
    "type": "function",
    "function": {
        "name": "tavily_search",
        "description": "搜索互联网上的最新信息。仅在需要获取实时信息、最新数据或你不确定的内容时使用",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或问题"
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 3
                }
            },
            "required": ["query"]
        }
    }
}]

# ============================================
# 优化后的多轮对话函数
# ============================================

async def optimized_multi_round_chat(
    llm_instance, 
    user_input, 
    tools, 
    tool_functions, 
    system_prompt=None, 
    max_tool_calls=5
):
    """
    优化后的多轮对话和工具调用函数
    
    主要改进：
    1. 每次工具调用后让模型判断是否需要继续搜索
    2. 在系统提示中明确指导何时使用/不使用工具
    3. 确保最终一定会生成总结性回答
    """
    
    # 清空历史记录
    llm_instance.clear_history()
    
    # 优化的系统提示词 - 明确指导工具使用策略
    optimized_system_prompt = """你是一个智能助手。请遵循以下原则：

1. 首先判断问题类型：
   - 如果是常识性问题或你已知的信息，直接回答，无需搜索
   - 如果涉及最新信息、实时数据或你不确定的内容，使用搜索工具

2. 使用搜索工具时：
   - 每次搜索后评估：信息是否足够回答用户问题？
   - 如果信息充足，立即停止搜索并给出完整答案
   - 如果信息不足，继续搜索补充信息，但不要超过必要的次数

3. 回答要求：
   - 基于所有收集的信息，提供准确、全面、有条理的答案
   - 如果搜索结果不足，诚实告知用户并提供已知信息"""
    
    # 使用优化的系统提示或用户提供的
    if system_prompt:
        llm_instance.add_message("system", system_prompt)
    else:
        llm_instance.add_message("system", optimized_system_prompt)
    
    # 添加用户消息
    llm_instance.add_message("user", user_input)
    
    tool_call_count = 0
    final_answer_generated = False
    
    print(f"\n用户问题: {user_input}")
    print("="*60)
    
    while tool_call_count < max_tool_calls and not final_answer_generated:
        print(f"\n[第 {tool_call_count + 1} 轮对话]")
        
        # 调用LLM
        response = await llm_instance.chat(
            tools=tools,
            stream=False,
            use_history=True,
            tool_choice="auto"  # 让模型自主决定
        )
        
        # 检查是否有工具调用
        if response.tool_calls:
            tool_call_count += 1
            print(f"[执行第 {tool_call_count} 次工具调用]")
            
            # 执行工具调用
            for tool_call in response.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                
                print(f"  工具: {func_name}")
                print(f"  参数: {func_args}")
                
                if func_name in tool_functions:
                    result = await tool_functions[func_name](**func_args)
                    
                    # 添加工具结果
                    llm_instance.conversation_history.append({
                        "role": "tool",
                        "content": str(result),
                        "tool_call_id": tool_call.id
                    })
                    
                    print(f"  结果预览: {result[:200]}...")
            
            # 关键改进：每次工具调用后，让模型评估是否需要继续
            if tool_call_count < max_tool_calls:
                # 添加引导消息，让模型判断
                evaluation_prompt = """基于已获得的搜索结果，请评估：
1. 信息是否足够回答用户的问题？
2. 如果足够，请直接给出完整答案
3. 如果不足，请继续搜索补充信息"""
                
                llm_instance.add_message("system", evaluation_prompt)
                
                # 继续下一轮（模型会决定是否继续搜索）
                continue
                
        else:
            # 没有工具调用，说明模型认为可以直接回答或已有足够信息
            if response.content:
                print(f"\n[模型回答]:")
                print(response.content)
                final_answer_generated = True
                return response.content
    
    # 确保生成最终答案
    if not final_answer_generated:
        print(f"\n[达到搜索上限 {max_tool_calls} 次，基于已有信息生成答案]")
        
        # 添加总结指令
        llm_instance.add_message(
            "system", 
            "你已经完成了所有必要的搜索。现在请基于所有收集到的信息，为用户提供一个完整、准确的答案。"
        )
        
        # 生成最终回答（流式）
        print("\n[最终回答]:")
        final_response = await llm_instance.chat(
            tools=None,  # 不再提供工具，强制生成答案
            stream=True,
            use_history=True
        )
        
        return final_response.content

# ============================================
# 对比测试函数
# ============================================

async def comparison_test():
    """对比测试：展示优化前后的差异"""
    
    llm_instance = LLM(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        stream=False,
        temperature=0.7,
        max_tokens=4096
    )
    
    tool_functions = {
        "tavily_search": tavily_search
    }
    
    # 测试用例
    test_cases = [
        {
            "question": "Python是什么编程语言？",  # 不需要搜索的问题
            "expected": "应该直接回答，不调用搜索"
        },
        {
            "question": "2025年英雄联盟LPL春季赛冠军是谁？",  # 需要搜索的问题
            "expected": "应该搜索并给出答案"
        },
        {
            "question": "今天上海的天气如何？",  # 需要实时信息
            "expected": "应该搜索最新天气信息"
        }
    ]
    
    print("="*60)
    print("优化效果对比测试")
    print("="*60)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test['question']}")
        print(f"期望行为: {test['expected']}")
        print("-"*40)
        
        result = await optimized_multi_round_chat(
            llm_instance=llm_instance,
            user_input=test['question'],
            tools=tools,
            tool_functions=tool_functions,
            max_tool_calls=3
        )
        
        print("\n" + "="*60)

# ============================================
# 主函数
# ============================================

async def main():
    """主函数：使用优化后的多轮对话"""
    
    llm_instance = LLM(
        api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        stream=True,
        temperature=0.7,
        max_tokens=4096
    )
    
    tool_functions = {
        "tavily_search": tavily_search
    }
    
    # 用户问题
    # user_input = "2025年英雄联盟LPL赛区第一赛段优胜者（冠军）是哪一只队伍"
    user_input = "今天广州佛山的天气怎么样 "
    print("="*60)
    print("优化后的多轮对话示例")
    print("="*60)
    
    try:
        result = await optimized_multi_round_chat(
            llm_instance=llm_instance,
            user_input=user_input,
            tools=tools,
            tool_functions=tool_functions,
            max_tool_calls=5
        )
        
        print("\n" + "="*60)
        print("对话完成")
        print("="*60)
        
    except Exception as e:
        print(f"错误: {str(e)}")
        logger.error(f"执行过程中出现错误: {str(e)}")

if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
    
    # 或运行对比测试
    # asyncio.run(comparison_test())