# 🔧 环境变量配置

## OpenAI API Key 配置

NovelGen 需要 OpenAI API Key 来调用 LLM。你可以通过以下任一方式配置：

### 方式1: 环境变量（推荐用于开发）

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

将上述命令添加到你的 shell 配置文件中（如 `~/.zshrc` 或 `~/.bashrc`）以永久保存。

### 方式2: .env 文件（推荐用于项目）

在项目根目录创建 `.env` 文件：

```bash
# 创建 .env 文件
cat > .env << 'EOF'
OPENAI_API_KEY=sk-your-api-key-here
EOF
```

`.env` 文件内容示例：

```env
# OpenAI API 配置
OPENAI_API_KEY=sk-your-api-key-here

# 可选：指定 API Base URL（如果使用代理或其他服务）
# OPENAI_API_BASE=https://api.openai.com/v1

# 可选：默认模型
# DEFAULT_MODEL=gpt-4

# 可选：默认温度参数
# DEFAULT_TEMPERATURE=0.7
```

**注意**: `.env` 文件已被添加到 `.gitignore`，不会被提交到 Git。

### 方式3: 代码中直接配置

```python
from novelgen.config import LLMConfig

config = LLMConfig(
    api_key="sk-your-api-key-here",
    model_name="gpt-4",
    temperature=0.7
)
```

**注意**: 不推荐在代码中硬编码 API Key，特别是如果要分享代码。

## 获取 API Key

1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 注册/登录账户
3. 进入 API Keys 页面
4. 创建新的 API Key
5. 复制并妥善保存（只会显示一次）

## 验证配置

运行以下命令验证 API Key 是否配置正确：

```python
from novelgen.llm import get_llm

llm = get_llm()
result = llm.invoke("测试")
print(result)
```

如果成功输出响应，说明配置正确。

## 使用其他 LLM 提供商

如果要使用其他兼容 OpenAI API 的服务（如 Azure OpenAI, 本地部署的模型等）：

```python
from novelgen.config import LLMConfig
from langchain_openai import ChatOpenAI

config = LLMConfig(
    model_name="your-model-name",
    api_key="your-api-key",
    # 可以添加其他参数
)

# 或者直接创建自定义 LLM
custom_llm = ChatOpenAI(
    model="your-model",
    api_key="your-key",
    base_url="https://your-api-endpoint.com/v1"
)
```

然后在使用时传入自定义配置。

## 成本控制

使用 OpenAI API 会产生费用。建议：

1. **设置使用限额**：在 OpenAI 平台设置每月使用限额
2. **选择合适的模型**：
   - GPT-4: 高质量，较贵
   - GPT-3.5-turbo: 性价比高
3. **控制生成长度**：通过 `max_tokens` 参数控制
4. **监控使用量**：定期检查 OpenAI 平台的使用统计

## 故障排查

### 错误: "No module named 'openai'"

```bash
pip install openai langchain-openai
```

### 错误: "Incorrect API key provided"

- 检查 API Key 是否正确
- 确认环境变量已正确设置
- 重启终端/IDE 使环境变量生效

### 错误: "Rate limit exceeded"

- 你的 API 请求速率超过限制
- 等待一段时间后重试
- 考虑升级 OpenAI 账户等级

### 错误: "Insufficient quota"

- API 配额不足
- 检查账户余额
- 前往 OpenAI 平台充值

---

作者：Jamesenh  
最后更新：2025-11-14

