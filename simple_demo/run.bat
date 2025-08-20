@echo off
echo 设置环境变量...

REM 请将以下值替换为您的实际API密钥
set DEEPSEEK_API_KEY=your_deepseek_api_key_here
set TAVILY_API_KEY=your_tavily_api_key_here

echo 环境变量设置完成！
echo DEEPSEEK_API_KEY: %DEEPSEEK_API_KEY%
echo TAVILY_API_KEY: %TAVILY_API_KEY%

echo.
echo 开始运行项目...
python main_v1.py

pause
