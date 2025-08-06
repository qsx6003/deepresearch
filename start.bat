@echo off
REM DeepSearch 快速启动脚本 (Windows)
REM 检查并启动 DeepSearch 服务

echo 🚀 DeepSearch 启动脚本
echo =====================

REM 检查 Python 版本
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python 未安装或不在 PATH 中
    pause
    exit /b 1
)
echo ✅ Python 已安装

REM 检查 .env 文件
if not exist ".env" (
    echo ❌ .env 文件不存在
    echo 请复制 .env.example 为 .env 并配置相关 API 密钥
    echo   copy .env.example .env
    pause
    exit /b 1
)
echo ✅ 配置文件: .env

REM 检查依赖
echo 🔍 检查依赖...
pip check >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  依赖包存在问题，尝试重新安装...
    pip install -r requirements.txt
)

REM 创建必要目录
if not exist "data\chroma" mkdir "data\chroma"
if not exist "logs" mkdir "logs"
echo ✅ 目录结构检查完成

REM 启动服务
echo.
echo 🚀 启动 DeepSearch 服务...
echo 访问地址: http://localhost:8000
echo API 文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo.

python -m app.main

pause
