# ReAct 支持的模型配置

## 🤖 LiteLLM 支持的模型

LiteLLM 支持几乎所有主流的 LLM 提供商，您可以根据需要选择不同的模型。

### 🔧 配置方式

在 `.env` 文件中设置 `REACT_MODEL` 和相应的 API 密钥：

```bash
# 选择模型
REACT_MODEL=gemini-2.0-flash

# 配置对应的 API 密钥
GOOGLE_API_KEY=your_api_key_here
```

### 📋 支持的模型列表

#### **Google Gemini** (推荐)
```bash
# 配置
REACT_MODEL=gemini-2.0-flash
GOOGLE_API_KEY=your_google_api_key

# 其他 Gemini 模型
REACT_MODEL=gemini-1.5-pro
REACT_MODEL=gemini-1.5-flash
```

#### **OpenAI**
```bash
# 配置
REACT_MODEL=gpt-4
OPENAI_API_KEY=your_openai_api_key

# 其他 OpenAI 模型
REACT_MODEL=gpt-4-turbo
REACT_MODEL=gpt-3.5-turbo
REACT_MODEL=gpt-4o
```

#### **Anthropic Claude**
```bash
# 配置
REACT_MODEL=claude-3-opus
ANTHROPIC_API_KEY=your_anthropic_api_key

# 其他 Claude 模型
REACT_MODEL=claude-3-sonnet
REACT_MODEL=claude-3-haiku
```

#### **通过 OpenRouter 使用多种模型**
```bash
# 配置
REACT_MODEL=openrouter/google/gemini-2.0-flash
OPENROUTER_API_KEY=your_openrouter_api_key

# 其他 OpenRouter 模型
REACT_MODEL=openrouter/anthropic/claude-3-opus
REACT_MODEL=openrouter/meta-llama/llama-3.1-70b
REACT_MODEL=openrouter/mistralai/mistral-large
```

#### **Azure OpenAI**
```bash
# 配置
REACT_MODEL=azure/gpt-4
AZURE_API_KEY=your_azure_api_key
AZURE_API_BASE=your_azure_endpoint
AZURE_API_VERSION=2023-12-01-preview
```

#### **其他提供商**
```bash
# Cohere
REACT_MODEL=cohere/command-r-plus
COHERE_API_KEY=your_cohere_api_key

# Together AI
REACT_MODEL=together_ai/meta-llama/Llama-3-70b-chat-hf
TOGETHER_API_KEY=your_together_api_key

# Fireworks AI
REACT_MODEL=fireworks_ai/llama-v3p1-70b-instruct
FIREWORKS_API_KEY=your_fireworks_api_key
```

### 💡 模型选择建议

#### **性能优先**
- `gemini-2.0-flash` - 速度快，成本低，推理能力强
- `gpt-4o` - OpenAI 最新模型，平衡性能和速度
- `claude-3-haiku` - Anthropic 快速模型

#### **质量优先**
- `gpt-4` - OpenAI 旗舰模型，推理能力最强
- `claude-3-opus` - Anthropic 最强模型
- `gemini-1.5-pro` - Google 高质量模型

#### **成本优先**
- `gemini-2.0-flash` - Google 免费额度充足
- `gpt-3.5-turbo` - OpenAI 经济型选择
- `claude-3-haiku` - Anthropic 经济型选择

### 🔑 获取 API 密钥

| 提供商 | 获取链接 | 免费额度 |
|--------|----------|----------|
| **Google Gemini** | https://ai.google.dev/ | 每分钟 15 次请求 |
| **OpenAI** | https://platform.openai.com/api-keys | $5 免费额度 |
| **Anthropic** | https://console.anthropic.com/ | $5 免费额度 |
| **OpenRouter** | https://openrouter.ai/ | $1 免费额度 |
| **Azure OpenAI** | https://azure.microsoft.com/en-us/products/ai-services/openai-service | 需要申请 |

### ⚙️ 高级配置

#### **自定义模型参数**
```python
# 在 brain.py 中可以自定义模型参数
model = LiteLLMModel(
    model_id=settings.llm.react_model,
    max_tokens=4096,        # 最大输出长度
    temperature=0.1,        # 创造性 (0-1)
    top_p=0.9,             # 核采样
    frequency_penalty=0.0,  # 频率惩罚
    presence_penalty=0.0    # 存在惩罚
)
```

#### **模型切换策略**
```python
# 可以根据查询复杂度选择不同模型
if complexity > 0.8:
    model = "gpt-4"  # 复杂查询用最强模型
elif complexity > 0.5:
    model = "gemini-2.0-flash"  # 中等查询用平衡模型
else:
    model = "gpt-3.5-turbo"  # 简单查询用快速模型
```

### 🚨 注意事项

1. **API 密钥安全**: 不要将 API 密钥提交到版本控制系统
2. **成本控制**: 监控 API 使用量，避免超出预算
3. **速率限制**: 不同提供商有不同的速率限制
4. **模型能力**: 不是所有模型都支持工具调用功能
5. **网络访问**: 某些提供商可能需要特殊的网络配置

### 🔧 故障排除

#### **常见错误**
```bash
# API 密钥错误
Error: Invalid API key
解决: 检查 .env 文件中的 API 密钥配置

# 模型不存在
Error: Model not found
解决: 检查模型名称是否正确，参考上面的模型列表

# 速率限制
Error: Rate limit exceeded
解决: 降低请求频率或升级 API 计划

# 网络连接错误
Error: Connection timeout
解决: 检查网络连接和防火墙设置
```

#### **调试模式**
```bash
# 启用详细日志
DEBUG=true
LOG_LEVEL=DEBUG

# 查看 LiteLLM 日志
export LITELLM_LOG=DEBUG
```
