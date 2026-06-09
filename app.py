from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from meeting_agent.config import Settings
from meeting_agent.pipeline import run_meeting_pipeline
from meeting_agent.storage import MeetingStore


st.set_page_config(page_title="Meeting Agent", layout="wide")


def save_upload(uploaded_file, upload_dir: Path) -> Path:
    suffix = Path(uploaded_file.name).suffix or ".audio"
    target = upload_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
    target.write_bytes(uploaded_file.getbuffer())
    return target


settings = Settings.from_env()
settings.ensure_dirs()

st.title("Meeting Agent")

with st.sidebar:
    st.subheader("配置")
    st.write(f"DeepSeek 模型：`{settings.deepseek_model}`")
    st.write(f"Whisper 模型：`{settings.whisper_model_size}`")
    st.caption("API Key 从 DEEPSEEK_API_KEY 环境变量读取，不会写入项目代码。")

    st.subheader("历史会议")
    store = MeetingStore(settings.data_dir / "meetings.sqlite3")
    for item in store.list_recent():
        st.markdown(f"**{item['title']}**")
        st.caption(item["created_at"])

title = st.text_input("会议标题", value=f"会议-{datetime.now().strftime('%Y-%m-%d')}")
uploaded_file = st.file_uploader("上传会议录音", type=["mp3", "wav", "m4a", "mp4", "aac", "flac"])

if uploaded_file and st.button("开始分析", type="primary"):
    if not settings.deepseek_api_key:
        st.error("缺少 DEEPSEEK_API_KEY。请在 .env 或系统环境变量中配置。")
        st.stop()

    audio_path = save_upload(uploaded_file, settings.upload_dir)

    with st.spinner("正在转录和分析会议，这一步可能需要几分钟..."):
        result = run_meeting_pipeline(audio_path, title, settings)

    st.success(f"分析完成，会议记录 ID：{result.meeting_id}")

    tab_summary, tab_tasks, tab_risks, tab_transcript, tab_export = st.tabs(
        ["会议纪要", "任务清单", "风险识别", "原始转录", "导出"]
    )

    with tab_summary:
        st.markdown(result.summary)

    with tab_tasks:
        if result.tasks:
            st.dataframe(result.tasks, use_container_width=True)
        else:
            st.info("未提取到明确任务。")

    with tab_risks:
        if result.risks:
            st.dataframe(result.risks, use_container_width=True)
        else:
            st.info("未识别到明显风险。")

    with tab_transcript:
        st.text_area("转录文本", result.transcript, height=420)

    with tab_export:
        st.download_button(
            "下载 Markdown",
            data=result.markdown,
            file_name=f"{title}.md",
            mime="text/markdown",
        )
        st.markdown(result.markdown)
elif not uploaded_file:
    st.info("上传一段会议录音后即可开始分析。")
