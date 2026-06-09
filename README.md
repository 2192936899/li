# Meeting Agent

一个学生项目友好的会议助手 MVP：

- 上传会议录音
- Faster-Whisper 转录
- DeepSeek 生成会议纪要
- DeepSeek 提取任务
- DeepSeek 识别风险
- SQLite 保存会议记录
- ChromaDB 可选保存会议记忆
- 导出 Markdown

## 安装

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 配置

复制环境变量模板：

```bash
copy .env.example .env
```

然后在 `.env` 中设置：

```bash
DEEPSEEK_API_KEY=你的DeepSeekKey
```

如果你已经把 key 发到公开聊天或代码仓库里，建议去 DeepSeek 控制台重新生成一个 key。

## 运行

```bash
streamlit run app.py
```

## 模型说明

DeepSeek API 兼容 OpenAI SDK。本项目默认使用 `deepseek-v4-flash`，你也可以通过环境变量切换：

```bash
DEEPSEEK_MODEL=deepseek-v4-flash
```

官方文档目前列出的 OpenAI 格式 base URL 是 `https://api.deepseek.com`，可用模型包括 `deepseek-v4-flash` 和 `deepseek-v4-pro`。旧模型名 `deepseek-chat` 与 `deepseek-reasoner` 将于 2026-07-24 15:59 UTC 停用。

## 项目结构

```text
app.py
meeting_agent/
  config.py
  llm.py
  pipeline.py
  prompts.py
  storage.py
  transcribe.py
```
