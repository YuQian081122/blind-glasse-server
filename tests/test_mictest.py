import io
import unittest
import wave
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import mictest_api
from mictest_api import reset_mictest_state, router


def _make_wav(duration_sec: float = 0.05, sample_rate: int = 16000) -> bytes:
    frames = int(duration_sec * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frames)
    return buf.getvalue()


class MicTestApiTest(unittest.TestCase):
    def setUp(self):
        reset_mictest_state()
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_mictest_accepts_wav_and_exposes_latest_state(self):
        wav_data = _make_wav()

        upload = self.client.post(
            "/api/mictest",
            content=wav_data,
            headers={"Content-Type": "audio/wav", "X-Device-Token": "test-token"},
        )
        self.assertEqual(upload.status_code, 200)
        self.assertEqual(upload.json()["seq"], 1)

        state = self.client.get("/api/mictest/state")
        self.assertEqual(state.status_code, 200)
        self.assertEqual(state.json()["seq"], 1)
        self.assertGreater(state.json()["duration_sec"], 0)

        latest = self.client.get("/api/mictest/latest.wav")
        self.assertEqual(latest.status_code, 200)
        self.assertTrue(latest.headers["content-type"].startswith("audio/wav"))
        self.assertEqual(latest.content, wav_data)

    def test_mictest_updates_state_with_asr_text(self):
        wav_data = _make_wav()

        with mock.patch.object(mictest_api, "_transcribe_wav_bytes", return_value="測試中文"):
            upload = self.client.post(
                "/api/mictest",
                content=wav_data,
                headers={"Content-Type": "audio/wav", "X-Device-Token": "test-token"},
            )

        self.assertEqual(upload.status_code, 200)
        state = self.client.get("/api/mictest/state").json()
        self.assertEqual(state["seq"], 1)
        self.assertEqual(state["asr_text"], "測試中文")
        self.assertIsInstance(state["asr_ms"], float)

    def test_mictest_reports_explicit_asr_empty_result(self):
        wav_data = _make_wav()

        with mock.patch.object(mictest_api, "_transcribe_wav_bytes", return_value=""):
            upload = self.client.post(
                "/api/mictest",
                content=wav_data,
                headers={"Content-Type": "audio/wav", "X-Device-Token": "test-token"},
            )

        self.assertEqual(upload.status_code, 200)
        state = self.client.get("/api/mictest/state").json()
        self.assertIn("ASR_EMPTY", state["asr_text"])
        self.assertIsInstance(state["asr_ms"], float)

    def test_mictest_returns_404_before_first_upload(self):
        latest = self.client.get("/api/mictest/latest.wav")

        self.assertEqual(latest.status_code, 404)


if __name__ == "__main__":
    unittest.main()
