#!/bin/bash

echo "========================================"
echo "运行Web搜索智能体服务测试"
echo "========================================"
echo

echo "检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3环境，请先安装Python 3.8+"
    exit 1
fi

python3 --version

echo
echo "检查依赖包..."
pip3 install aiohttp
if [ $? -ne 0 ]; then
    echo "错误: 测试依赖包安装失败"
    exit 1
fi

echo
echo "运行测试..."
echo "请确保服务已启动: python3 web_search_agent_service.py"
echo

python3 test_service.py
