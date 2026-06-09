# 企业客服 RAG Agent Demo

## 简历项目描述

企业客服 RAG Agent Demo 是一个面向企业终端客户服务场景的知识库问答原型。项目支持企业上传产品手册、操作指南等文档，系统将文档解析为知识片段，并在用户提问时进行本地检索，将命中的上下文发送给 DeepSeek API 生成结构化客服答复。该 demo 聚焦客服场景中的“有依据回答、信息不足追问、复杂问题转人工”三类关键能力。

## 可直接放进简历的写法

**企业客服 RAG Agent Demo｜Streamlit / Python / DeepSeek API / RAG**

- 独立实现面向企业客服场景的 RAG 问答 demo，支持上传 PDF、TXT、Markdown、CSV、JSON 等用户手册并自动解析为知识库片段。
- 设计本地检索流程，对用户问题进行关键词与短语召回，命中相关手册片段后拼接上下文调用 DeepSeek Chat Completions API。
- 通过系统 prompt 约束模型仅基于知识库回答，并要求输出固定 JSON 字段，包括标题、回答要点、处理动作和置信度。
- 实现“上传手册”和“客服问答”双页面交互，支持页面切换、示例问题测试、命中依据展示、DeepSeek 调用失败后的本地兜底。
- 针对客服场景设计低置信度处理策略：资料不足时优先追问用户，涉及订单金额、退款到账、发票、投诉升级等问题建议转人工。
- 下载并接入多份长用户手册作为测试集，包括 Canon EOS R5、DJI Mini 4 Pro、Lenovo ThinkPad 用户指南，用于验证长文档解析和检索效果。

## 项目目标

这个项目不是普通聊天机器人，而是一个“企业客服知识库问答原型”：

1. 企业可以上传产品手册或操作说明。
2. 系统把手册解析成可检索知识片段。
3. 终端用户输入问题。
4. 系统先检索相关片段，而不是直接让模型自由发挥。
5. 命中片段后调用 DeepSeek API。
6. 返回结构化客服答复，并展示命中依据。

## 核心功能

### 1. 手册上传与解析

支持上传：

- PDF
- TXT
- Markdown
- CSV
- JSON

PDF 文件通过 `pypdf` 提取文本，文本类文件直接读取 UTF-8 内容。解析后的文本会进入本地切片流程。

### 2. 本地知识库切片

系统会将长文档切成多个片段，每个片段保留：

- 片段编号
- 原始内容
- 检索 terms
- 相关度分数

目前采用轻量级本地检索，适合 demo 展示。后续可以替换为向量数据库，例如 pgvector、Qdrant、Milvus。

### 3. RAG 检索

检索逻辑包括：

- 中文字符与二元词切分
- 英文、数字 token 提取
- 问题与片段 term 匹配打分
- 关键短语 boost，例如“恢复出厂设置”“蓝牙”“退货”“维修”“退款到账”
- Top-k 命中片段返回

### 4. DeepSeek API 调用

系统从环境变量或 `.env` 中读取：

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`

调用流程：

```text
用户问题
  -> 本地 RAG 检索
  -> 拼接系统 prompt + 用户问题 + 命中片段
  -> 调用 DeepSeek Chat Completions API
  -> 解析 JSON
  -> Streamlit 渲染客服答复
```

### 5. 结构化输出

DeepSeek 被要求返回固定 JSON：

```json
{
  "title": "一句话标题",
  "answer": ["面向终端客户的回答要点"],
  "next_action": "给出操作步骤 | 继续追问 | 转人工 | 给出政策说明",
  "confidence": "high | medium | low"
}
```

前端会渲染：

- 标题
- 处理动作
- 置信度
- 回答步骤
- 命中依据
- 生成方式

### 6. 客服策略

项目内置客服场景策略：

- 如果命中依据不足，先追问用户补充型号、故障现象、已尝试步骤等信息。
- 如果连续信息不足，建议转人工。
- 如果涉及订单金额、退款到账、发票抬头修改、投诉升级，直接建议转人工。
- 如果 DeepSeek API 调用失败，使用本地兜底逻辑生成答复。

## 技术栈

- Python
- Streamlit
- DeepSeek Chat Completions API
- pypdf
- 本地关键词检索
- RAG prompt engineering

## 文件结构

```text
.
├── app.py
├── requirements.txt
├── PROJECT_RESUME.md
└── manuals/
    ├── canon_eos_r5_user_guide_en.pdf
    ├── canon_eos_r5_user_guide_en.txt
    ├── dji_mini_4_pro_user_manual_en.pdf
    ├── dji_mini_4_pro_user_manual_en.txt
    ├── lenovo_thinkpad_t14_t15_gen2_user_guide_en.pdf
    └── lenovo_thinkpad_t14_t15_gen2_user_guide_en.txt
```

## 运行方式

安装依赖：

```bash
pip install -r requirements.txt
```

配置环境变量：

```bash
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

启动：

```bash
streamlit run app.py
```

本地访问：

```text
http://127.0.0.1:8501
```

## 测试手册

项目已下载三份长文档用于测试：

- Canon EOS R5 User Guide：919 页
- DJI Mini 4 Pro User Manual：128 页
- Lenovo ThinkPad T14/T15 Gen2 User Guide：80 页

这些文档用于验证：

- 长 PDF 文本提取
- 大规模片段切分
- 多类型设备问题检索
- DeepSeek 结构化问答

## 当前限制

- 检索仍是本地关键词检索，不是真正的 embedding 向量召回。
- 没有数据库，知识库只保存在 Streamlit session 中。
- 没有多租户企业隔离。
- 没有真实人工客服系统接入。
- PDF 表格和图片内容未做 OCR。

## 后续可扩展方向

1. 接入向量数据库，例如 pgvector 或 Qdrant。
2. 引入 embedding 模型和 reranker，提高长文档检索准确率。
3. 增加企业后台，支持多知识库、多版本文档、禁答内容和话术配置。
4. 增加用户会话日志、命中片段审计和回答质量评分。
5. 接入人工客服系统，实现转人工和工单流转。
6. 支持 OCR，解析手册中的图片步骤、截图和表格。
7. 增加多租户隔离，支持不同企业知识库独立管理。

## 面试讲解口径

这个项目的重点不是“调一个大模型接口”，而是把企业客服场景拆成了一个可控链路：文档上传、知识切片、问题检索、上下文注入、模型结构化输出、低置信度追问和转人工兜底。相比直接问大模型，这种设计能减少幻觉，并且能让企业在后台追溯每次回答依据。
