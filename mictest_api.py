import io
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
    global _latest_wav, _state
    with _lock:
        _latest_wav = None
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


def _run_asr(seq: int, wav_bytes: bytes) -> None:
    started = time.perf_counter()
    try:
        text = _transcribe_wav_bytes(wav_bytes).strip()
        if not text:
            text = "ASR_EMPTY: 模型未載入、未辨識到語音，或轉寫結果為空"
    except Exception as exc:
        text = f"ASR_ERROR: {type(exc).__name__}: {exc}"
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)

    global _state
    with _lock:
        if _state.seq != seq:
            return
        _state = _state.model_copy(
            update={
                "asr_text": text,
                "asr_ms": elapsed_ms,
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

    global _latest_wav, _state
    with _lock:
        seq = _state.seq + 1
        _latest_wav = wav_bytes
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


@router.get("/api/mictest/state", response_model=MicTestState)
async def get_mictest_state() -> MicTestState:
    with _lock:
        return _state.model_copy()
