"""
Web搜索智能体服务客户端示例
演示如何使用Python客户端调用服务
"""

import requests
import json
import time
from typing import Dict, Any

class SearchAgentClient:
    """搜索智能体客户端"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def chat(self, message: str, stream: bool = False, 
             max_tool_calls: int = 3, system_prompt: str = None) -> Dict[str, Any]:
        """聊天接口"""
        try:
            payload = {
                "message": message,
                "stream": stream,
                "max_tool_calls": max_tool_calls
            }
            
            if system_prompt:
                payload["system_prompt"] = system_prompt
            
            endpoint = "/chat/stream" if stream else "/chat"
            
            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            if stream:
                # 处理流式响应
                content = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk_data = json.loads(line.decode())
                            if chunk_data.get("success"):
                                content += chunk_data.get("chunk", "")
                                if chunk_data.get("is_final"):
                                    break
                        except json.JSONDecodeError:
                            continue
                
                return {
                    "success": True,
                    "content": content,
                    "stream": True
                }
            else:
                return response.json()
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """直接搜索"""
        try:
            payload = {
                "query": query,
                "max_results": max_results
            }
            
            response = requests.post(
                f"{self.base_url}/search",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_tools(self) -> Dict[str, Any]:
        """获取可用工具"""
        try:
            response = requests.get(f"{self.base_url}/tools", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

def demo_usage():
    """演示使用方法"""
    print("🚀 Web搜索智能体服务客户端演示")
    print("=" * 60)
    
    # 创建客户端
    client = SearchAgentClient(
        base_url="http://localhost:8000",
        api_key="sk-test-key-1"
    )
    
    # 1. 健康检查
    print("\n1️⃣ 健康检查")
    print("-" * 30)
    health = client.health_check()
    if health.get("success"):
        print(f"✅ 服务状态: {health['status']}")
        print(f"   版本: {health['version']}")
        print(f"   模型: {health['model_info']['model']}")
    else:
        print(f"❌ 健康检查失败: {health.get('error')}")
        print("请确保服务已启动")
        return
    
    # 2. 获取可用工具
    print("\n2️⃣ 获取可用工具")
    print("-" * 30)
    tools = client.get_tools()
    if tools.get("success"):
        print(f"✅ 可用工具数量: {len(tools['tools'])}")
        for tool in tools['tools']:
            print(f"   - {tool['function']['name']}: {tool['function']['description']}")
    else:
        print(f"❌ 获取工具失败: {tools.get('error')}")
    
    # 3. 直接搜索测试
    print("\n3️⃣ 直接搜索测试")
    print("-" * 30)
    search_result = client.search("Python编程语言", max_results=2)
    if search_result.get("success"):
        print(f"✅ 搜索成功，结果数: {search_result['total_results']}")
        for i, result in enumerate(search_result['results'], 1):
            content = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
            print(f"   结果{i}: {content}")
    else:
        print(f"❌ 搜索失败: {search_result.get('error')}")
    
    # 4. 聊天测试 - 常识问题
    print("\n4️⃣ 聊天测试 - 常识问题")
    print("-" * 30)
    chat_result = client.chat(
        message="什么是Python编程语言？",
        stream=False,
        max_tool_calls=2
    )
    if chat_result.get("success"):
        print(f"✅ 聊天成功，工具调用次数: {chat_result.get('tool_calls_count', 0)}")
        print(f"   响应时间: {chat_result.get('response_time', 0):.2f}秒")
        print(f"   回答: {chat_result['message'][:200]}...")
    else:
        print(f"❌ 聊天失败: {chat_result.get('error')}")
    
    # 5. 聊天测试 - 需要搜索的问题
    print("\n5️⃣ 聊天测试 - 需要搜索的问题")
    print("-" * 30)
    chat_result2 = client.chat(
        message="今天北京的天气怎么样？",
        stream=False,
        max_tool_calls=3
    )
    if chat_result2.get("success"):
        print(f"✅ 聊天成功，工具调用次数: {chat_result2.get('tool_calls_count', 0)}")
        print(f"   响应时间: {chat_result2.get('response_time', 0):.2f}秒")
        print(f"   回答: {chat_result2['message'][:200]}...")
    else:
        print(f"❌ 聊天失败: {chat_result2.get('error')}")
    
    # 6. 流式聊天测试
    print("\n6️⃣ 流式聊天测试")
    print("-" * 30)
    print("正在获取流式回答...")
    stream_result = client.chat(
        message="介绍一下人工智能的发展历史",
        stream=True,
        max_tool_calls=2
    )
    if stream_result.get("success"):
        print(f"✅ 流式聊天成功，工具调用次数: {stream_result.get('tool_calls_count', 0)}")
        print(f"   回答: {stream_result['content'][:200]}...")
    else:
        print(f"❌ 流式聊天失败: {stream_result.get('error')}")
    
    # 7. 自定义系统提示测试
    print("\n7️⃣ 自定义系统提示测试")
    print("-" * 30)
    custom_result = client.chat(
        message="计算一下25乘以4等于多少？",
        stream=False,
        max_tool_calls=1,
        system_prompt="你是一个数学专家，请用中文回答，只给出计算结果"
    )
    if custom_result.get("success"):
        print(f"✅ 自定义提示测试成功，工具调用次数: {custom_result.get('tool_calls_count', 0)}")
        print(f"   回答: {custom_result['message']}")
    else:
        print(f"❌ 自定义提示测试失败: {custom_result.get('error')}")
    
    print("\n" + "=" * 60)
    print("🎉 演示完成！")
    print("=" * 60)

def interactive_mode():
    """交互模式"""
    print("💬 交互模式 - 输入 'quit' 退出")
    print("=" * 60)
    
    client = SearchAgentClient(
        base_url="http://localhost:8000",
        api_key="sk-test-key-1"
    )
    
    while True:
        try:
            user_input = input("\n🤖 请输入您的问题: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                print("👋 再见！")
                break
            
            if not user_input:
                continue
            
            print("⏳ 正在处理...")
            start_time = time.time()
            
            # 根据问题类型选择处理方式
            if user_input.startswith("搜索:"):
                query = user_input[3:].strip()
                result = client.search(query)
                if result.get("success"):
                    print(f"🔍 搜索结果 ({result['total_results']}个):")
                    for i, res in enumerate(result['results'], 1):
                        print(f"  {i}. {res['content'][:150]}...")
                else:
                    print(f"❌ 搜索失败: {result.get('error')}")
            else:
                # 普通聊天
                result = client.chat(user_input, stream=False, max_tool_calls=3)
                if result.get("success"):
                    print(f"🤖 回答 (工具调用: {result.get('tool_calls_count', 0)}次):")
                    print(f"    {result['message']}")
                else:
                    print(f"❌ 聊天失败: {result.get('error')}")
            
            response_time = time.time() - start_time
            print(f"⏱️  响应时间: {response_time:.2f}秒")
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 发生错误: {str(e)}")

if __name__ == "__main__":
    print("选择运行模式:")
    print("1. 演示模式 (运行预设测试)")
    print("2. 交互模式 (手动输入问题)")
    
    try:
        choice = input("请输入选择 (1/2): ").strip()
        
        if choice == "1":
            demo_usage()
        elif choice == "2":
            interactive_mode()
        else:
            print("无效选择，运行演示模式")
            demo_usage()
            
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
    except Exception as e:
        print(f"❌ 程序异常: {str(e)}")
