@echo off
title Web搜索智能体服务 - 快速启动
color 0A

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    Web搜索智能体服务                        ║
echo ║                    快速启动脚本                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo 🔍 检查环境...
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或不在PATH中
    echo    请安装Python 3.8+并确保在PATH中
    pause
    exit /b 1
)
echo ✅ Python环境检查通过

REM 检查依赖
echo.
echo 📦 安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 依赖包安装失败
    pause
    exit /b 1
)
echo ✅ 依赖包安装完成

echo.
echo 🚀 启动服务...
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                        服务信息                              ║
echo ╠══════════════════════════════════════════════════════════════╣
echo ║ 服务地址: http://localhost:8000                             ║
echo ║ API文档:  http://localhost:8000/docs                        ║
echo ║ 交互文档: http://localhost:8000/redoc                       ║
echo ║                                                              ║
echo ║ 测试密钥: sk-test-key-1                                     ║
echo ║ 停止服务: 按 Ctrl+C                                         ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo 正在启动服务...
python web_search_agent_service.py

echo.
echo 服务已停止
pause
