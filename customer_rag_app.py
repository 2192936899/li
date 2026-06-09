import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import streamlit as st
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent

SAMPLE_MANUAL = """星云耳机 X1 用户操作手册

一、蓝牙连接
首次使用时，请长按电源键 3 秒开机。指示灯蓝白交替闪烁表示进入配对模式。
在手机蓝牙列表中选择“Nebula X1”即可连接。
如果手机搜索不到设备，请先关闭耳机，再长按电源键 6 秒，直到听到“pairing”提示音。

二、恢复出厂设置
耳机开机状态下，同时长按音量加键和音量减键 8 秒。
听到两声提示音后，指示灯快速闪烁，表示已恢复出厂设置。
恢复出厂设置会清除历史配对记录，需要重新连接手机。

三、充电说明
请使用 5V/1A 或 5V/2A 充电器。充电时红灯常亮，充满后白灯常亮。
完整充电约需 90 分钟。请勿使用明显损坏的充电线。

四、常见故障排查
如果设备连不上蓝牙，请依次尝试：确认耳机电量充足；删除手机中的旧配对记录；重启手机蓝牙；将耳机恢复出厂设置后重新配对。
如果只有一边有声音，请将两只耳机放回充电盒 10 秒后取出，等待左右耳自动同步。

五、售后与退换货
自签收日起 7 天内，非人为损坏且包装配件完整，可申请无理由退货。
自签收日起 15 天内，产品出现性能故障，可申请换货。
超过 15 天但仍在一年质保期内，产品性能故障可申请维修。
进水、摔裂、私自拆修等人为损坏不属于免费质保范围。

六、人工客服
涉及订单金额、退款到账、发票抬头修改、投诉升级的问题，请转人工客服处理。
"""


@dataclass
class Chunk:
    id: int
    content: str
    terms: list[str]
    score: float = 0.0


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_env() -> None:
    load_env_file(ROOT / ".env")


def init_state() -> None:
    defaults = {
        "manual_text": SAMPLE_MANUAL,
        "chunks": [],
        "messages": [],
        "low_confidence_turns": 0,
        "last_error": "",
        "page": "上传手册",
        "api_key_input": "",
        "api_base_url_input": "",
        "api_model_input": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[，。！？、；：“”\"'（）()\[\]{}【】]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> list[str]:
    normalized = normalize(text)
    latin_terms = re.findall(r"[a-z0-9]+", normalized)
    zh_chars = [char for char in re.sub(r"[a-z0-9\s]", "", normalized) if char]

    terms = []
    for index, char in enumerate(zh_chars):
        terms.append(char)
        if index < len(zh_chars) - 1:
            terms.append(char + zh_chars[index + 1])
    return [*latin_terms, *terms]


def split_manual(text: str) -> list[Chunk]:
    blocks = [
        block.strip()
        for block in re.split(r"\n\s*\n|(?=^[一二三四五六七八九十]+、)", text, flags=re.M)
        if block.strip()
    ]

    raw_chunks = []
    for block in blocks:
        if len(block) <= 450:
            raw_chunks.append(block)
            continue
        for start in range(0, len(block), 340):
            raw_chunks.append(block[start : start + 450])

    return [
        Chunk(id=index + 1, content=content, terms=tokenize(content))
        for index, content in enumerate(raw_chunks)
    ]


def rebuild_knowledge_base() -> None:
    text = st.session_state.manual_text.strip()
    st.session_state.chunks = split_manual(text) if text else []
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "知识库已生成。你可以切到“客服问答”页面，用终端客户的口吻提问。",
        }
    ]
    st.session_state.low_confidence_turns = 0
    st.session_state.last_error = ""


def read_uploaded_manual(uploaded_file: Any) -> str:
    file_name = uploaded_file.name.lower()
    if file_name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"\n\n--- Page {page_number} ---\n{text}")
        return "\n".join(pages).strip()

    return uploaded_file.read().decode("utf-8", errors="ignore")


def bundled_manuals() -> dict[str, Path]:
    manuals_dir = ROOT / "manuals"
    if not manuals_dir.exists():
        return {}
    return {
        path.stem.replace("_", " "): path
        for path in sorted(manuals_dir.glob("*.txt"))
    }


def retrieve(question: str, chunks: list[Chunk]) -> list[Chunk]:
    question_terms = set(tokenize(question))
    question_text = normalize(question)
    key_phrases = [
        "恢复出厂设置",
        "出厂设置",
        "蓝牙",
        "连接",
        "退货",
        "换货",
        "质保",
        "维修",
        "充电",
        "发票",
        "投诉",
        "退款到账",
    ]
    scored = []

    for chunk in chunks:
        score = 0.0
        chunk_text = normalize(chunk.content)
        for term in chunk.terms:
            if term in question_terms:
                score += 2.0 if len(term) > 1 else 0.45

        for phrase in key_phrases:
            if phrase in question and phrase in chunk.content:
                score += 12.0 if len(phrase) >= 4 else 5.0

        if question_text and question_text in chunk_text:
            score += 8.0

        if score > 1.8:
            scored.append(Chunk(chunk.id, chunk.content, chunk.terms, score))

    return sorted(scored, key=lambda item: item.score, reverse=True)[:4]


def needs_clarification(question: str, hits: list[Chunk]) -> bool:
    if not hits:
        return True
    if re.search(r"退款到账|订单|发票|投诉|金额", question):
        return False
    if re.search(r"耳机|设备|产品", question) and not re.search(
        r"型号|x1|nebula|星云", question, flags=re.I
    ):
        return hits[0].score < 8
    return hits[0].score < 3.2


def deepseek_config() -> dict[str, str]:
    def read_secret(key: str, default: str) -> str:
        try:
            return st.secrets.get(key, default)
        except Exception:
            return default

    api_key = read_secret("DEEPSEEK_API_KEY", os.environ.get("DEEPSEEK_API_KEY", ""))
    base_url = read_secret(
        "DEEPSEEK_BASE_URL",
        os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    model = read_secret(
        "DEEPSEEK_MODEL",
        os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
    )

    if st.session_state.get("api_key_input"):
        api_key = st.session_state.api_key_input.strip()
    if st.session_state.get("api_base_url_input"):
        base_url = st.session_state.api_base_url_input.strip()
    if st.session_state.get("api_model_input"):
        model = st.session_state.api_model_input.strip()

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    }


def chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def build_prompt(question: str, hits: list[Chunk]) -> list[dict[str, str]]:
    context = "\n\n".join(
        f"[片段 {hit.id} | 相关度 {hit.score:.1f}]\n{hit.content}" for hit in hits
    )
    if not context:
        context = "未检索到可靠知识片段。"

    system = """你是企业客服 RAG Agent。你必须只基于“知识库片段”回答，不允许编造企业政策。
如果用户信息不足，先追问，不要急着拒答。
如果问题涉及订单金额、退款到账、发票抬头修改、投诉升级，建议转人工。
输出必须是 JSON，不要输出 Markdown，不要包裹代码块。
JSON 字段：
{
  "title": "一句话标题",
  "answer": ["面向终端客户的回答要点"],
  "next_action": "给出操作步骤 | 继续追问 | 转人工 | 给出政策说明",
  "confidence": "high | medium | low"
}"""
    user = f"""用户问题：
{question}

知识库片段：
{context}"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def call_deepseek(question: str, hits: list[Chunk]) -> dict[str, Any]:
    config = deepseek_config()
    if not config["api_key"]:
        raise RuntimeError("没有找到 DEEPSEEK_API_KEY，请在平台 Secrets 或本地 .env 中配置。")

    payload = {
        "model": config["model"],
        "messages": build_prompt(question, hits),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        chat_completions_url(config["base_url"]),
        data=body,
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"DeepSeek HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"DeepSeek 请求失败：{error.reason}") from error

    content = data["choices"][0]["message"]["content"]
    parsed = extract_json(content)
    return {
        "title": str(parsed.get("title", "客服答复")),
        "answer": parsed.get("answer", []),
        "next_action": str(parsed.get("next_action", "给出答复")),
        "confidence": str(parsed.get("confidence", "medium")),
        "raw": content,
    }


def fallback_answer(question: str, hits: list[Chunk]) -> dict[str, Any]:
    if re.search(r"订单|退款到账|发票|投诉|金额", question):
        return {
            "title": "需要人工客服处理",
            "answer": [
                "这个问题涉及订单、金额或投诉升级，建议转人工客服确认。",
                "请提供订单号或下单手机号，人工客服会根据系统记录继续处理。",
            ],
            "next_action": "转人工",
            "confidence": "medium",
        }

    if needs_clarification(question, hits):
        st.session_state.low_confidence_turns += 1
        if st.session_state.low_confidence_turns >= 2:
            body = [
                "我还没有找到足够可靠的手册依据。",
                "请补充产品型号、故障现象或购买时间；如果问题紧急，建议直接转人工客服。",
            ]
        else:
            body = ["为了更准确处理，请补充产品型号、当前状态，以及你已经尝试过的步骤。"]
        return {
            "title": "需要补充信息",
            "answer": body,
            "next_action": "继续追问",
            "confidence": "low",
        }

    st.session_state.low_confidence_turns = 0
    sentences = [
        sentence.strip()
        for sentence in re.split(r"[。！？\n]", "\n".join(hit.content for hit in hits))
        if len(sentence.strip()) > 5
    ][:5]
    return {
        "title": "基于手册的客服答复",
        "answer": sentences,
        "next_action": "给出操作步骤",
        "confidence": "medium",
    }


def render_answer(answer: dict[str, Any], hits: list[Chunk], used_deepseek: bool) -> str:
    items = answer.get("answer", [])
    if isinstance(items, str):
        items = [items]

    lines = [
        f"**{answer.get('title', '客服答复')}**",
        "",
        f"处理动作：`{answer.get('next_action', '给出答复')}`",
        f"置信度：`{answer.get('confidence', 'medium')}`",
        f"生成方式：`{'DeepSeek API' if used_deepseek else '本地兜底'}`",
        "",
    ]
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {item}")

    lines.extend(["", "**命中依据**"])
    if hits:
        for hit in hits:
            preview = hit.content[:160] + ("..." if len(hit.content) > 160 else "")
            lines.append(f"- 片段 {hit.id}，相关度 {hit.score:.1f}：{preview}")
    else:
        lines.append("- 未找到足够可靠的知识片段。")

    return "\n".join(lines)


def handle_question(question: str) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    hits = retrieve(question, st.session_state.chunks)

    used_deepseek = False
    try:
        answer = call_deepseek(question, hits)
        used_deepseek = True
        st.session_state.last_error = ""
    except Exception as error:
        answer = fallback_answer(question, hits)
        st.session_state.last_error = str(error)

    st.session_state.messages.append(
        {"role": "assistant", "content": render_answer(answer, hits, used_deepseek)}
    )


def render_upload_page() -> None:
    title_col, nav_col = st.columns([0.72, 0.28])
    with title_col:
        st.header("上传手册")
        st.caption("先把企业操作手册上传或粘贴进来，再生成本地知识库。")
    with nav_col:
        st.write("")
        if st.button("去客服问答", type="primary", use_container_width=True):
            st.session_state.page = "客服问答"
            st.rerun()

    uploaded = st.file_uploader("上传手册", type=["pdf", "txt", "md", "csv", "json"])
    if uploaded:
        with st.spinner("正在解析上传的手册..."):
            st.session_state.manual_text = read_uploaded_manual(uploaded)

    manuals = bundled_manuals()
    if manuals:
        manual_name = st.selectbox("或载入内置测试手册", ["不载入"] + list(manuals.keys()))
        if manual_name != "不载入" and st.button("载入选中的测试手册", use_container_width=True):
            st.session_state.manual_text = manuals[manual_name].read_text(
                encoding="utf-8",
                errors="ignore",
            )
            rebuild_knowledge_base()
            st.rerun()

    col_left, col_right = st.columns([0.7, 0.3], gap="large")
    with col_left:
        st.session_state.manual_text = st.text_area(
            "手册内容",
            value=st.session_state.manual_text,
            height=430,
        )
        action_col, sample_col = st.columns(2)
        if action_col.button("生成知识库", type="primary", use_container_width=True):
            rebuild_knowledge_base()
            st.success("知识库已生成，可以切到“客服问答”。")
        if sample_col.button("载入示例手册", use_container_width=True):
            st.session_state.manual_text = SAMPLE_MANUAL
            rebuild_knowledge_base()
            st.rerun()
        if st.session_state.chunks and st.button("立即开始客服问答", use_container_width=True):
            st.session_state.page = "客服问答"
            st.rerun()

    with col_right:
        st.metric("知识片段", len(st.session_state.chunks))
        st.metric("约略字数", len(st.session_state.manual_text))
        if st.session_state.chunks:
            st.success("知识库已就绪")
            with st.expander("查看前 3 个片段"):
                for chunk in st.session_state.chunks[:3]:
                    st.markdown(f"**片段 {chunk.id}**")
                    st.write(chunk.content)
        else:
            st.warning("还没有生成知识库")


def render_chat_page() -> None:
    title_col, nav_col = st.columns([0.72, 0.28])
    with title_col:
        st.header("客服问答")
        st.caption("命中知识片段后，会把用户问题和片段发给 DeepSeek API 生成结构化答复。")
    with nav_col:
        st.write("")
        if st.button("返回上传手册", use_container_width=True):
            st.session_state.page = "上传手册"
            st.rerun()

    if not st.session_state.chunks and st.session_state.manual_text.strip():
        rebuild_knowledge_base()

    config = deepseek_config()
    status_col, model_col, chunk_col = st.columns(3)
    status_col.metric("DeepSeek", "已配置" if bool(config["api_key"]) else "未配置")
    model_col.metric("模型", config["model"])
    chunk_col.metric("知识片段", len(st.session_state.chunks))

    if st.session_state.last_error:
        st.warning(f"DeepSeek 调用失败，已使用本地兜底：{st.session_state.last_error}")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    examples = st.columns(4)
    sample_questions = [
        "星云 X1 耳机怎么恢复出厂设置？",
        "设备连不上蓝牙怎么办？",
        "可以退货吗？",
        "退款什么时候到账？",
    ]
    for col, question in zip(examples, sample_questions):
        if col.button(question, use_container_width=True):
            handle_question(question)
            st.rerun()

    question = st.chat_input("输入终端客户的问题")
    if question:
        handle_question(question)
        st.rerun()


def render_api_settings() -> None:
    config = deepseek_config()
    st.subheader("DeepSeek API Settings")
    st.text_input(
        "API Key",
        key="api_key_input",
        type="password",
        placeholder="sk-...",
        help="Session only. It is not written to the repo or saved on disk.",
    )
    st.text_input(
        "Base URL",
        key="api_base_url_input",
        placeholder=config["base_url"],
        help="Default: https://api.deepseek.com",
    )
    st.text_input(
        "Model",
        key="api_model_input",
        placeholder=config["model"],
        help="Example: deepseek-v4-flash",
    )

    active_config = deepseek_config()
    if active_config["api_key"]:
        st.success("DeepSeek API configured")
    else:
        st.warning("DeepSeek API key missing")
    st.caption(f"Active model: {active_config['model']}")
    st.caption(f"Active base URL: {active_config['base_url']}")
    st.divider()


def main() -> None:
    load_env()
    st.set_page_config(page_title="企业客服 RAG Agent Demo", page_icon="AI", layout="wide")
    init_state()

    st.title("企业客服 RAG Agent Demo")

    with st.sidebar:
        render_api_settings()
        st.subheader("导航")
        st.session_state.page = st.radio(
            "选择页面",
            ["上传手册", "客服问答"],
            index=0 if st.session_state.page == "上传手册" else 1,
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("RAG 检索 + DeepSeek API + 格式化客服输出")

    if st.session_state.page == "上传手册":
        render_upload_page()
    else:
        render_chat_page()


if __name__ == "__main__":
    main()
