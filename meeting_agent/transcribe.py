from __future__ import annotations

from pathlib import Path

from faster_whisper import WhisperModel
import streamlit as st


@st.cache_resource(show_spinner=False)
def load_whisper_model(model_size: str) -> WhisperModel:
    return WhisperModel(model_size, device="cpu", compute_type="int8")


def transcribe_audio(audio_path: Path, model_size: str = "base") -> str:
    model = load_whisper_model(model_size)
    segments, _ = model.transcribe(str(audio_path), vad_filter=True)
    lines = [segment.text.strip() for segment in segments if segment.text.strip()]
    return "\n".join(lines)
