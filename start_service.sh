#!/bin/bash

echo "========================================"
echo "启动Web搜索智能体服务"
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
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "错误: 依赖包安装失败"
    exit 1
fi

echo
echo "启动服务..."
echo "服务地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo
echo "按 Ctrl+C 停止服务"
echo

python3 web_search_agent_service.py
