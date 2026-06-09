# 企业客服 RAG Agent Demo

一个基于 Streamlit 的企业客服知识库问答 demo。企业上传用户手册后，系统会进行本地 RAG 检索，并把命中的知识片段发送给 DeepSeek API，生成结构化客服答复。

## 功能

- 上传 PDF、TXT、Markdown、CSV、JSON 用户手册
- 将长文档解析并切成知识片段
- 根据用户问题检索相关片段
- 调用 DeepSeek API 生成结构化客服回答
- 展示命中依据、处理动作、置信度
- 信息不足时追问，复杂问题建议转人工
- DeepSeek 调用失败时本地兜底

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

打开：

```text
http://127.0.0.1:8501
```

## 环境变量

本地可以创建 `.env`：

```bash
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

云端部署时不要提交 `.env`，请在平台 Secrets 中配置同名字段。

## 免费部署到 Streamlit Community Cloud

1. 把项目推送到 GitHub。
2. 打开 Streamlit Community Cloud。
3. 选择仓库、分支和入口文件 `app.py`。
4. 在 App secrets 中填写：

```toml
DEEPSEEK_API_KEY = "your_deepseek_api_key"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
```

5. 点击 Deploy。

## 项目简历

完整项目介绍、简历写法和面试讲解口径见：

[PROJECT_RESUME.md](PROJECT_RESUME.md)
