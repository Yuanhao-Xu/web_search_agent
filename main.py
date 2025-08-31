# from openai import OpenAI
# from tavily import AsyncTavilyClient
# import requests
# import asyncio
# import logging
# from llm import LLM
# import json

# # 全局配置日志级别，异步代码也能使用
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # 封装搜索工具Tavily

# async def tavily_search(query: str, max_results: int = 3) -> str:
#     """
#     Tavily异步网络搜索工具
    
#     Args:
#         query: 搜索查询内容
#         max_results: 返回结果数量，默认3
        
#     Returns:
#         格式化的搜索结果字符串
#     """
#     try:
#         # 使用官方异步客户端
#         tavily_client = AsyncTavilyClient("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")
        
#         # 异步搜索
#         response = await tavily_client.search(
#             query=query,
#             include_answer="advanced",
#             max_results=max_results
#         )
#         logger.debug("原始 response: %s", response)
#         logger.info("原始 response: %s", response)
#         # 格式化结果
#         results = response.get("results", [])
#         if not results:
#             return f"未找到与'{query}'相关的结果"
        
#         output = f"搜索：{query}\n找到{len(results)}个结果：\n\n"
        
#         for i, result in enumerate(results, 1):
#             output += f"【{i}】{result.get('title', '无标题')}\n"
#             output += f"链接：{result.get('url', '')}\n"
#             content = result.get('content', '')
#             if len(content) > 200:
#                 content = content[:200] + "..."
#             output += f"摘要：{content}\n\n"
        
#         return output
        
#     except Exception as e:
#         return f"搜索出错：{str(e)}"

# """
# 相应示例
# {
#   "query": "哈尔滨天气怎么样",
#   "follow_up_questions": null,
#   "answer": null,
#   "images": [],
#   "results": [
#     {
#       "url": "https://www.accuweather.com/zh/cn/harbin/102669/daily-weather-forecast/102669",
#       "title": "哈爾濱, 黑龍江省, 中國每日天氣 - AccuWeather",
#       "content": "最大紫外線指數2.0 (良好) 風南 7英里/小时 最大紫外線指數6.0 (不健康－敏感人士) ...更多内容",
#       "score": 0.73778254,
#       "raw_content": null
#     }
#   ],
#   "response_time": 0.7,
#   "request_id": "2fd6ec31-5efa-40c7-b9d2-b0e4fa9d3c86"
# }

# """


# # 工具的 function schema
# tools = [{
#     "type": "function",
#     "function": {
#         "name": "tavily_search",
#         "description": "搜索互联网上的最新信息",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "query": {
#                     "type": "string",
#                     "description": "搜索关键词或问题"
#                 },
#                 "max_results": {
#                     "type": "integer",
#                     "description": "返回结果数量",
#                     "default": 3
#                 }
#             },
#             "required": ["query"]
#         }
#     }
# }]



# # Tavily 工具封装调试
# async def simple_example():
#     """最简单的使用示例"""
    
#     print("="*50)
#     print("示例1：单个搜索")
#     print("="*50)
    
#     # 单个搜索
#     result = await tavily_search("2024年NBA总冠军")
#     print("="*10,result)



# # 封装大模型
# # 先建立一个基类，再建立一个deepseek模型类


# # =====================================================
# # ... existing code ...

# # 封装大模型
# # 先建立一个基类，再建立一个deepseek模型类

# async def main():
#     """主函数：实例化流式LLM对象并支持多轮对话和多次工具调用"""
    
#     # 实例化流式LLM对象
#     llm_instance = LLM(
#         api_key="sk-f5889d58c6db4dd38ca78389a6c7a7e8",
#         base_url="https://api.deepseek.com/v1",
#         model="deepseek-chat",
#         stream=True,  # 启用流式输出
#         temperature=0.7,
#         max_tokens=4096
#     )
    
#     # 定义工具函数映射
#     tool_functions = {
#         "tavily_search": tavily_search
#     }
    
#     # 系统提示词
#     system_prompt = """你是一个专业的新闻分析师，能够通过搜索互联网获取最新信息并进行分析总结。
# 请根据搜索结果，为用户提供准确、全面、有条理的信息总结。
# 你可以进行多次搜索来获取更全面的信息，但请确保每次搜索都有明确的目的。
# 当你有足够的信息来回答用户问题时，请停止搜索并给出完整的答案。"""
    
#     # 用户提示词
#     user_input = "2025年英雄联盟LPL赛区第一赛段优胜者（冠军）是哪一只队伍"
    
#     print("="*60)
#     print("多轮对话 + 多次工具调用示例")
#     print("="*60)
#     print(f"用户问题: {user_input}")
#     print("="*60)
    
#     try:
#         # 多轮对话和工具调用
#         result = await multi_round_chat_with_tools(
#             llm_instance=llm_instance,
#             user_input=user_input,
#             tools=tools,
#             tool_functions=tool_functions,
#             system_prompt=system_prompt,
#             max_tool_calls=5  # 设置工具调用次数上限
#         )
        
#         print("\n" + "="*60)
#         print("多轮对话完成")
#         print("="*60)
        
#     except Exception as e:
#         print(f"错误: {str(e)}")
#         logger.error(f"执行过程中出现错误: {str(e)}")

# async def multi_round_chat_with_tools(llm_instance, user_input, tools, tool_functions, 
#                                     system_prompt=None, max_tool_calls=2):
#     """
#     多轮对话和工具调用函数
    
#     Args:
#         llm_instance: LLM实例
#         user_input: 用户输入
#         tools: 工具schema列表
#         tool_functions: 工具函数映射
#         system_prompt: 系统提示词
#         max_tool_calls: 最大工具调用次数，默认5次
        
#     Returns:
#         str: 最终回复
#     """
#     # 清空历史记录
#     llm_instance.clear_history()
    
#     # 添加系统提示词
#     if system_prompt:
#         llm_instance.add_message("system", system_prompt)
    
#     # 添加用户消息
#     llm_instance.add_message("user", user_input)
    
#     tool_call_count = 0  # 工具调用计数器
    
#     while tool_call_count < max_tool_calls:
#         print(f"\n[第 {tool_call_count + 1} 轮对话]")
#         print("-" * 40)
        
#         # 调用LLM
#         response = await llm_instance.chat(
#             tools=tools,
#             stream=False,  # 非流式调用以便处理工具调用
#             use_history=True
#         )
        
#         # 检查是否有工具调用
#         if response.tool_calls:
#             tool_call_count += 1
#             print(f"[执行第 {tool_call_count} 次工具调用]:")
            
#             # 执行所有工具调用
#             for tool_call in response.tool_calls:
#                 func_name = tool_call.function.name
#                 func_args = json.loads(tool_call.function.arguments)
                
#                 print(f"  - 工具: {func_name}")
#                 print(f"    参数: {func_args}")
                
#                 if func_name in tool_functions:
#                     # 执行工具函数
#                     if asyncio.iscoroutinefunction(tool_functions[func_name]):
#                         result = await tool_functions[func_name](**func_args)
#                     else:
#                         result = tool_functions[func_name](**func_args)
                    
#                     # 添加工具结果到历史
#                     llm_instance.conversation_history.append({
#                         "role": "tool",
#                         "content": str(result),
#                         "tool_call_id": tool_call.id
#                     })
                    
#                     print(f"    结果: {result[:200]}..." if len(str(result)) > 200 else f"    结果: {result}")
#                 else:
#                     print(f"    错误: 未找到工具 {func_name}")
            
#             # 检查是否达到最大工具调用次数
#             if tool_call_count >= max_tool_calls:
#                 print(f"\n[达到最大工具调用次数 {max_tool_calls}，生成最终回复]")
#                 break
                
#         else:
#             # 没有工具调用，生成最终回复
#             print(f"\n[第 {tool_call_count + 1} 轮对话完成，无需工具调用]")
#             break
    
#     # 生成最终回复（流式）
#     print("\n[生成最终回复]:")
#     final_response = await llm_instance.chat(
#         tools=tools,
#         stream=True,  # 最终回复使用流式输出
#         use_history=True
#     )
    
#     return final_response.content

# if __name__ == "__main__":
#     # 注释掉原来的测试代码
#     # asyncio.run(simple_example())
    
#     # 运行新的主函数
#     asyncio.run(main())






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