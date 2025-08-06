#!/bin/bash

# DeepSearch 快速启动脚本
# 检查并启动 DeepSearch 服务

echo "🚀 DeepSearch 启动脚本"
echo "====================="

# 检查 Python 版本
python_version=$(python --version 2>&1)
if [[ $? -ne 0 ]]; then
    echo "❌ Python 未安装或不在 PATH 中"
    exit 1
fi
echo "✅ Python 版本: $python_version"

# 检查虚拟环境
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  警告: 未在虚拟环境中运行"
    read -p "是否继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "请先激活虚拟环境:"
        echo "  python -m venv venv"
        echo "  source venv/bin/activate  # Linux/Mac"
        echo "  venv\\Scripts\\activate     # Windows"
        exit 1
    fi
else
    echo "✅ 虚拟环境: $VIRTUAL_ENV"
fi

# 检查 .env 文件
if [[ ! -f ".env" ]]; then
    echo "❌ .env 文件不存在"
    echo "请复制 .env.example 为 .env 并配置相关 API 密钥"
    echo "  cp .env.example .env"
    exit 1
fi
echo "✅ 配置文件: .env"

# 检查依赖
echo "🔍 检查依赖..."
pip check > /dev/null 2>&1
if [[ $? -ne 0 ]]; then
    echo "⚠️  依赖包存在问题，尝试重新安装..."
    pip install -r requirements.txt
fi

# 创建必要目录
mkdir -p data/chroma
mkdir -p logs
echo "✅ 目录结构检查完成"

# 启动服务
echo ""
echo "🚀 启动 DeepSearch 服务..."
echo "访问地址: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

python -m app.main
