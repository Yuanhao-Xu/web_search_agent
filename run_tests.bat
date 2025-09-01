@echo off
echo ========================================
echo 运行Web搜索智能体服务测试
echo ========================================
echo.

echo 检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到Python环境，请先安装Python 3.8+
    pause
    exit /b 1
)

echo.
echo 检查依赖包...
pip install aiohttp
if errorlevel 1 (
    echo 错误: 测试依赖包安装失败
    pause
    exit /b 1
)

echo.
echo 运行测试...
echo 请确保服务已启动: python web_search_agent_service.py
echo.

python test_service.py

pause
