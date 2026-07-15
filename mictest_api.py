import io
import hashlib
import threading
import time
import wave
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel


router = APIRouter()


class MicTestState(BaseModel):
    seq: int
    received_at: Optional[str]
    duration_sec: Optional[float]
    asr_text: Optional[str]
    asr_ms: Optional[float]
    reply_text: Optional[str]
    tts_ready: bool
    tts_ms: Optional[float]


_lock = threading.Lock()
_latest_wav: Optional[bytes] = None
_reply_mp3: Optional[bytes] = None
_reply_etag: Optional[str] = None
_state = MicTestState(
    seq=0,
    received_at=None,
    duration_sec=None,
    asr_text=None,
    asr_ms=None,
    reply_text=None,
    tts_ready=False,
    tts_ms=None,
)


def reset_mictest_state() -> None:
    global _latest_wav, _reply_mp3, _reply_etag, _state
    with _lock:
        _latest_wav = None
        _reply_mp3 = None
        _reply_etag = None
        _state = MicTestState(
            seq=0,
            received_at=None,
            duration_sec=None,
            asr_text=None,
            asr_ms=None,
            reply_text=None,
            tts_ready=False,
            tts_ms=None,
        )


def _duration_sec(wav_bytes: bytes) -> float:
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
            rate = wav.getframerate()
            if rate <= 0:
                return 0.0
            return round(wav.getnframes() / float(rate), 3)
    except wave.Error:
        raise HTTPException(status_code=400, detail="invalid_wav")


def _transcribe_wav_bytes(wav_bytes: bytes) -> str:
    from local_whisper_asr import transcribe_wav_bytes

    return transcribe_wav_bytes(wav_bytes)


async def _edge_tts_save_to_bytes(text: str) -> bytes:
    import config
    import edge_tts  # type: ignore[import-untyped]
    import tempfile
    import os

    voice = getattr(config, "EDGE_TTS_VOICE", "zh-TW-HsiaoChenNeural")
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _synthesize_reply_mp3(text: str) -> bytes:
    import asyncio

    return asyncio.run(_edge_tts_save_to_bytes(text))


def _build_reply_text(asr_text: str) -> str:
    return f"我聽到了：{asr_text}"


def _run_asr(seq: int, wav_bytes: bytes) -> None:
    started = time.perf_counter()
    try:
        text = _transcribe_wav_bytes(wav_bytes).strip()
        if not text:
            text = "ASR_EMPTY: 模型未載入、未辨識到語音，或轉寫結果為空"
    except Exception as exc:
        text = f"ASR_ERROR: {type(exc).__name__}: {exc}"
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)

    reply_text = _build_reply_text(text)
    tts_started = time.perf_counter()
    reply_mp3: Optional[bytes] = None
    try:
        reply_mp3 = _synthesize_reply_mp3(reply_text)
    except Exception as exc:
        reply_text = f"{reply_text}（TTS_ERROR: {type(exc).__name__}: {exc}）"
    tts_ms = round((time.perf_counter() - tts_started) * 1000.0, 2)

    global _reply_etag, _reply_mp3, _state
    with _lock:
        if _state.seq != seq:
            return
        if reply_mp3:
            _reply_mp3 = reply_mp3
            _reply_etag = f'"{seq}-{hashlib.sha256(reply_mp3).hexdigest()[:16]}"'
        _state = _state.model_copy(
            update={
                "asr_text": text,
                "asr_ms": elapsed_ms,
                "reply_text": reply_text,
                "tts_ready": bool(reply_mp3),
                "tts_ms": tts_ms,
            }
        )


@router.post("/api/mictest", response_model=MicTestState)
async def upload_mictest_wav(request: Request, background_tasks: BackgroundTasks) -> MicTestState:
    content_type = (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    if content_type != "audio/wav":
        raise HTTPException(status_code=415, detail="expected_audio_wav")

    wav_bytes = await request.body()
    if not wav_bytes:
        raise HTTPException(status_code=400, detail="empty_audio")

    duration = _duration_sec(wav_bytes)
    received_at = datetime.fromtimestamp(time.time(), timezone.utc).isoformat()

    global _latest_wav, _reply_etag, _reply_mp3, _state
    with _lock:
        seq = _state.seq + 1
        _latest_wav = wav_bytes
        _reply_mp3 = None
        _reply_etag = None
        _state = MicTestState(
            seq=seq,
            received_at=received_at,
            duration_sec=duration,
            asr_text=None,
            asr_ms=None,
            reply_text=None,
            tts_ready=False,
            tts_ms=None,
        )
        response_state = _state

    background_tasks.add_task(_run_asr, seq, wav_bytes)
    return response_state


@router.get("/api/mictest/latest.wav")
async def latest_mictest_wav() -> Response:
    with _lock:
        wav_bytes = _latest_wav
    if wav_bytes is None:
        raise HTTPException(status_code=404, detail="no_mictest_audio")
    return Response(content=wav_bytes, media_type="audio/wav")


@router.get("/api/mictest/reply.mp3")
async def latest_mictest_reply(request: Request) -> Response:
    with _lock:
        reply_mp3 = _reply_mp3
        reply_etag = _reply_etag
        seq = _state.seq
    if not reply_mp3 or not reply_etag:
        raise HTTPException(status_code=404, detail="no_mictest_reply")

    headers = {
        "ETag": reply_etag,
        "X-Mictest-Seq": str(seq),
        "Cache-Control": "private, max-age=0, must-revalidate",
    }
    if (request.headers.get("if-none-match") or "").strip() == reply_etag:
        return Response(status_code=304, headers=headers)
    return Response(content=reply_mp3, media_type="audio/mpeg", headers=headers)


@router.get("/api/mictest/state", response_model=MicTestState)
async def get_mictest_state() -> MicTestState:
    with _lock:
        return _state.model_copy()
