"""
Web搜索智能体服务测试代码
测试所有API端点和功能
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

# 测试配置
TEST_CONFIG = {
    "base_url": "http://localhost:8000",
    "api_key": "sk-test-key-1",  # 使用测试密钥
    "timeout": 30
}

class ServiceTester:
    """服务测试器"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.session = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=TEST_CONFIG["timeout"])
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def test_health_check(self) -> Dict[str, Any]:
        """测试健康检查端点"""
        print("🔍 测试健康检查端点...")
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                result = await response.json()
                print(f"✅ 健康检查成功: {result['status']}")
                return result
        except Exception as e:
            print(f"❌ 健康检查失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_root_endpoint(self) -> Dict[str, Any]:
        """测试根端点"""
        print("🔍 测试根端点...")
        
        try:
            async with self.session.get(f"{self.base_url}/") as response:
                result = await response.json()
                print(f"✅ 根端点测试成功: {result['message']}")
                return result
        except Exception as e:
            print(f"❌ 根端点测试失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_tools_endpoint(self) -> Dict[str, Any]:
        """测试工具端点"""
        print("🔍 测试工具端点...")
        
        try:
            async with self.session.get(f"{self.base_url}/tools") as response:
                result = await response.json()
                print(f"✅ 工具端点测试成功，可用工具: {len(result['tools'])}")
                return result
        except Exception as e:
            print(f"❌ 工具端点测试失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_direct_search(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """测试直接搜索端点"""
        print(f"🔍 测试直接搜索: {query}")
        
        try:
            payload = {
                "query": query,
                "max_results": max_results
            }
            
            async with self.session.post(
                f"{self.base_url}/search",
                headers=self.headers,
                json=payload
            ) as response:
                result = await response.json()
                if result.get("success"):
                    print(f"✅ 搜索成功，结果数: {result['total_results']}")
                else:
                    print(f"❌ 搜索失败: {result.get('error', '未知错误')}")
                return result
        except Exception as e:
            print(f"❌ 搜索测试失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_chat_endpoint(self, message: str, stream: bool = False, 
                                max_tool_calls: int = 3, system_prompt: str = None) -> Dict[str, Any]:
        """测试聊天端点"""
        print(f"🔍 测试聊天端点: {message[:50]}...")
        
        try:
            payload = {
                "message": message,
                "stream": stream,
                "max_tool_calls": max_tool_calls
            }
            
            if system_prompt:
                payload["system_prompt"] = system_prompt
            
            endpoint = "/chat/stream" if stream else "/chat"
            
            async with self.session.post(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                json=payload
            ) as response:
                if stream:
                    # 处理流式响应
                    content = ""
                    async for line in response.content:
                        if line:
                            try:
                                chunk_data = json.loads(line.decode().strip())
                                if chunk_data.get("success"):
                                    content += chunk_data.get("chunk", "")
                                    if chunk_data.get("is_final"):
                                        break
                            except json.JSONDecodeError:
                                continue
                    
                    result = {
                        "success": True,
                        "content": content,
                        "stream": True
                    }
                else:
                    result = await response.json()
                
                if result.get("success"):
                    print(f"✅ 聊天成功，工具调用次数: {result.get('tool_calls_count', 0)}")
                    print(f"   响应时间: {result.get('response_time', 0):.2f}秒")
                else:
                    print(f"❌ 聊天失败: {result.get('error', '未知错误')}")
                
                return result
        except Exception as e:
            print(f"❌ 聊天测试失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_authentication(self) -> Dict[str, Any]:
        """测试认证功能"""
        print("🔍 测试认证功能...")
        
        # 测试无效密钥
        try:
            invalid_headers = {
                "Authorization": "Bearer invalid-key",
                "Content-Type": "application/json"
            }
            
            payload = {"message": "测试消息"}
            
            async with self.session.post(
                f"{self.base_url}/chat",
                headers=invalid_headers,
                json=payload
            ) as response:
                if response.status == 401:
                    print("✅ 无效密钥认证测试通过")
                else:
                    print(f"❌ 无效密钥认证测试失败，状态码: {response.status}")
                    return {"success": False, "error": "认证测试失败"}
                
        except Exception as e:
            print(f"❌ 认证测试失败: {str(e)}")
            return {"success": False, "error": str(e)}
        
        # 测试有效密钥
        try:
            payload = {"message": "测试认证"}
            
            async with self.session.post(
                f"{self.base_url}/chat",
                headers=self.headers,
                json=payload
            ) as response:
                if response.status == 200:
                    print("✅ 有效密钥认证测试通过")
                    return {"success": True}
                else:
                    print(f"❌ 有效密钥认证测试失败，状态码: {response.status}")
                    return {"success": False, "error": "有效密钥认证失败"}
                
        except Exception as e:
            print(f"❌ 有效密钥认证测试失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行综合测试"""
        print("🚀 开始运行综合测试...")
        print("=" * 60)
        
        test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "details": []
        }
        
        # 测试用例
        test_cases = [
            {
                "name": "健康检查",
                "func": self.test_health_check,
                "args": {}
            },
            {
                "name": "根端点",
                "func": self.test_root_endpoint,
                "args": {}
            },
            {
                "name": "工具端点",
                "func": self.test_tools_endpoint,
                "args": {}
            },
            {
                "name": "认证测试",
                "func": self.test_authentication,
                "args": {}
            },
            {
                "name": "直接搜索测试",
                "func": self.test_direct_search,
                "args": {"query": "Python编程语言", "max_results": 2}
            },
            {
                "name": "聊天测试-常识问题",
                "func": self.test_chat_endpoint,
                "args": {
                    "message": "什么是Python编程语言？",
                    "stream": False,
                    "max_tool_calls": 2
                }
            },
            {
                "name": "聊天测试-需要搜索的问题",
                "func": self.test_chat_endpoint,
                "args": {
                    "message": "今天北京的天气怎么样？",
                    "stream": False,
                    "max_tool_calls": 3
                }
            },
            {
                "name": "流式聊天测试",
                "func": self.test_chat_endpoint,
                "args": {
                    "message": "介绍一下人工智能的发展历史",
                    "stream": True,
                    "max_tool_calls": 2
                }
            },
            {
                "name": "自定义系统提示测试",
                "func": self.test_chat_endpoint,
                "args": {
                    "message": "计算一下25乘以4等于多少？",
                    "stream": False,
                    "max_tool_calls": 1,
                    "system_prompt": "你是一个数学专家，请用中文回答"
                }
            }
        ]
        
        for test_case in test_cases:
            test_results["total_tests"] += 1
            print(f"\n📋 测试 {test_results['total_tests']}: {test_case['name']}")
            print("-" * 40)
            
            try:
                start_time = time.time()
                result = await test_case["func"](**test_case["args"])
                end_time = time.time()
                
                if result.get("success"):
                    test_results["passed_tests"] += 1
                    test_case["result"] = "PASS"
                    test_case["duration"] = end_time - start_time
                    print(f"✅ {test_case['name']} 测试通过 (耗时: {test_case['duration']:.2f}秒)")
                else:
                    test_results["failed_tests"] += 1
                    test_case["result"] = "FAIL"
                    test_case["error"] = result.get("error", "未知错误")
                    print(f"❌ {test_case['name']} 测试失败: {test_case['error']}")
                
                test_case["result_data"] = result
                test_results["details"].append(test_case)
                
            except Exception as e:
                test_results["failed_tests"] += 1
                test_case["result"] = "ERROR"
                test_case["error"] = str(e)
                test_case["result_data"] = {"success": False, "error": str(e)}
                test_results["details"].append(test_case)
                print(f"❌ {test_case['name']} 测试出错: {str(e)}")
            
            # 添加延迟避免API限制
            await asyncio.sleep(1)
        
        # 输出测试总结
        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)
        print(f"总测试数: {test_results['total_tests']}")
        print(f"通过: {test_results['passed_tests']} ✅")
        print(f"失败: {test_results['failed_tests']} ❌")
        print(f"成功率: {(test_results['passed_tests'] / test_results['total_tests'] * 100):.1f}%")
        
        if test_results["failed_tests"] > 0:
            print("\n❌ 失败的测试:")
            for test in test_results["details"]:
                if test["result"] in ["FAIL", "ERROR"]:
                    print(f"  - {test['name']}: {test.get('error', '未知错误')}")
        
        return test_results

async def main():
    """主测试函数"""
    print("🧪 Web搜索智能体服务测试程序")
    print("=" * 60)
    print(f"测试目标: {TEST_CONFIG['base_url']}")
    print(f"API密钥: {TEST_CONFIG['api_key']}")
    print(f"超时设置: {TEST_CONFIG['timeout']}秒")
    print("=" * 60)
    
    # 检查服务是否运行
    print("🔍 检查服务状态...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{TEST_CONFIG['base_url']}/health") as response:
                if response.status == 200:
                    print("✅ 服务正在运行")
                else:
                    print(f"❌ 服务响应异常，状态码: {response.status}")
                    return
    except Exception as e:
        print(f"❌ 无法连接到服务: {str(e)}")
        print("请确保服务已启动: python web_search_agent_service.py")
        return
    
    # 运行测试
    async with ServiceTester(TEST_CONFIG["base_url"], TEST_CONFIG["api_key"]) as tester:
        results = await tester.run_comprehensive_test()
        
        # 保存测试结果
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 测试结果已保存到: {filename}")
        
        # 返回测试结果
        if results["failed_tests"] == 0:
            print("\n🎉 所有测试通过！服务运行正常。")
            return 0
        else:
            print(f"\n⚠️  有 {results['failed_tests']} 个测试失败，请检查服务配置。")
            return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n❌ 测试程序异常: {str(e)}")
        exit(1)
