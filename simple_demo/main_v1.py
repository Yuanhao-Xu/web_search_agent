import os
import asyncio
import aiohttp
from typing import Optional


# 导入配置
try:
    from config import DEEPSEEK_API_KEY, TAVILY_API_KEY
except ImportError:
    print("错误：找不到 config.py 文件")
    print("请创建 config.py 并添加 API 密钥")
    exit(1)

# 验证配置
assert DEEPSEEK_API_KEY and not DEEPSEEK_API_KEY.startswith("your_"), \
    "请在 config.py 中配置 DEEPSEEK_API_KEY"
assert TAVILY_API_KEY and not TAVILY_API_KEY.startswith("your_"), \
    "请在 config.py 中配置 TAVILY_API_KEY"

print("配置加载成功")


class SimpleAgent:
    """最简单的Agent实现"""
    
    def __init__(self):
        # 优先使用配置文件中的密钥，如果没有则使用环境变量
        self.deepseek_key = DEEPSEEK_API_KEY or os.getenv("DEEPSEEK_API_KEY")
        self.tavily_key = TAVILY_API_KEY or os.getenv("TAVILY_API_KEY")
        
        if not self.deepseek_key or not self.tavily_key:
            raise ValueError("请设置 DEEPSEEK_API_KEY 和 TAVILY_API_KEY 环境变量，或在 config.py 文件中配置，或创建.env文件")
    
    async def answer(self, question: str) -> str:
        """回答问题的主入口"""
        # Step 1: 搜索
        search_results = await self.search(question)
        
        # Step 2: 生成回答
        answer = await self.generate_answer(question, search_results)
        
        return answer
    
    async def search(self, query: str) -> str:
        """调用Tavily搜索"""
        async with aiohttp.ClientSession() as session:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.tavily_key,
                "query": query,
                "max_results": 3
            }
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    # 简单拼接搜索结果
                    results = data.get("results", [])
                    context = "\n".join([
                        f"- {r.get('title', '')}: {r.get('content', '')[:200]}"
                        for r in results
                    ])
                    return context
                return ""
    
    async def generate_answer(self, question: str, context: str) -> str:
        """调用DeepSeek生成回答"""
        async with aiohttp.ClientSession() as session:
            url = "https://api.deepseek.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.deepseek_key}"}
            
            prompt = f"基于以下搜索结果回答用户问题。\n\n搜索结果:\n{context}\n\n用户问题: {question}"
            
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}]
            }
            
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                return "抱歉，生成回答时出错了"

# 测试代码
async def test_v1():
    agent = SimpleAgent()
    answer = await agent.answer("今天的天气怎么样？")
    print(answer)

if __name__ == "__main__":
    asyncio.run(test_v1())