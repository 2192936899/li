from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Settings
from .llm import DeepSeekClient, parse_json_array
from .prompts import RISK_PROMPT, SUMMARY_PROMPT, TASK_PROMPT
from .storage import MeetingMemory, MeetingStore
from .transcribe import transcribe_audio


@dataclass
class MeetingResult:
    meeting_id: int
    title: str
    transcript: str
    summary: str
    tasks: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    markdown: str


def run_meeting_pipeline(audio_path: Path, title: str, settings: Settings) -> MeetingResult:
    transcript = transcribe_audio(audio_path, settings.whisper_model_size)
    llm = DeepSeekClient(settings)

    summary = llm.complete(SUMMARY_PROMPT, f"会议标题：{title}\n\n会议转录：\n{transcript}")
    tasks_raw = llm.complete(TASK_PROMPT, transcript)
    risks_raw = llm.complete(RISK_PROMPT, transcript)

    tasks = parse_json_array(tasks_raw)
    risks = parse_json_array(risks_raw)

    store = MeetingStore(settings.data_dir / "meetings.sqlite3")
    meeting_id = store.save(title, transcript, summary, tasks, risks)

    memory = MeetingMemory(settings.data_dir / "chroma")
    memory.add(meeting_id, title, transcript, summary)

    markdown = build_markdown(title, transcript, summary, tasks, risks)
    return MeetingResult(meeting_id, title, transcript, summary, tasks, risks, markdown)


def build_markdown(
    title: str,
    transcript: str,
    summary: str,
    tasks: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> str:
    tasks_md = "\n".join(
        f"- 负责人：{item.get('owner', '未明确')}；任务：{item.get('task', '')}；截止时间：{item.get('deadline', '未明确')}"
        for item in tasks
    ) or "- 未提取到明确任务"

    risks_md = "\n".join(
        f"- [{item.get('severity', '未明确')}] {item.get('risk', '')}；依据：{item.get('evidence', '未明确')}；建议：{item.get('mitigation', '未明确')}"
        for item in risks
    ) or "- 未识别到明显风险"

    return f"""# {title}

## 会议纪要

{summary}

## 任务清单

{tasks_md}

## 风险识别

{risks_md}

## 原始转录

{transcript}
"""
