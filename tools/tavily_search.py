import logging
from typing import Optional, Literal
from tavily import TavilyClient

logger = logging.getLogger(__name__)

async def tavily_search(
    query: str,
    max_results: int = 3,
    time_range: Optional[Literal["day", "week", "month", "year"]] = None,
    include_answer: Literal["basic", "advanced"] = "advanced",
    include_favicon: bool = False
) -> str:
    """Tavily异步网络搜索"""
    try:
        client = TavilyClient("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")
        
        # 构建参数
        params = {
            "query": query,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_favicon": include_favicon
        }
        if time_range:
            params["time_range"] = time_range
        
        response = client.search(**params)
        
        # 提取结果
        answer = response.get("answer", "")
        results = response.get("results", [])
        
        if not results and not answer:
            return f"未找到'{query}'相关结果"
        
        # 格式化输出
        output = [f"搜索：{query}\n{'='*40}"]
        
        if answer:
            output.append(f"\n【AI答案】\n{answer}\n")
        
        if results:
            output.append(f"【搜索结果】共{len(results)}条")
            for i, result in enumerate(results, 1):
                title = result.get('title', '无标题')
                url = result.get('url', 'N/A')
                content = result.get('content', '')[:500]
                if len(result.get('content', '')) > 500:
                    content += "..."
                output.append(f"\n{i}. {title}\n   {url}\n   {content}")
        
        return '\n'.join(output)
        
    except Exception as e:
        logger.error(f"搜索错误: {e}")
        return f"搜索失败：{str(e)}"