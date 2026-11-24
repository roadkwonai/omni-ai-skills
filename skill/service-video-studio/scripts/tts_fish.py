"""Fish Audio API로 문장별 음성을 만든다(tts.py가 부른다).

키는 환경변수 FISH_AUDIO_API_KEY 또는 .env에서 읽고 출력하지 않는다. 무료 모델 s2.1-pro-free.
같은 문장·목소리면 건너뛰고(옆의 .txt로 비교), 문장이 바뀐 것만 다시 만든다. 글은 외부 서비스로 나간다."""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from lib import dur

MODEL = "s2.1-pro-free"


def key(env) -> str:
    if os.environ.get("FISH_AUDIO_API_KEY"):
        return os.environ["FISH_AUDIO_API_KEY"]
    for line in (Path(env).read_text().splitlines() if env else []):
        if line.startswith("FISH_AUDIO_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("FISH_AUDIO_API_KEY 없음: 환경변수나 --env <.env 경로>를 주세요")


def tts(text: str, voice: str, k: str) -> bytes:
    body = json.dumps({"text": text, "reference_id": voice, "format": "mp3", "mp3_bitrate": 128, "sample_rate": 44100,
                       "latency": "normal", "normalize": False, "language": "ko"}).encode()
    req = urllib.request.Request("https://api.fish.audio/v1/tts", data=body, method="POST", headers={
        "Authorization": f"Bearer {k}", "Content-Type": "application/json", "model": MODEL})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 3:
                time.sleep(2 ** attempt * 3)
                continue
            raise SystemExit(f"HTTP {e.code}: {e.read()[:200]!r}")
    raise SystemExit("재시도 초과")


def make(W, d, env=None):
    k = key(env)
    out = W / "assets" / "vo_raw"
    out.mkdir(parents=True, exist_ok=True)
    total = 0.0
    for ln in d["lines"]:
        p, stamp = out / f"{ln['id']}.mp3", out / f"{ln['id']}.txt"
        want = f"{d['voice']}\n{ln['tts']}"
        if not p.exists() or not stamp.exists() or stamp.read_text() != want:
            p.write_bytes(tts(ln["tts"], d["voice"], k))
            stamp.write_text(want)
        total += dur(p)
        print(f"{ln['id']} {dur(p):5.2f}초", flush=True)
    print(f"합계 {total:.1f}초(배속·쉼 전 — 영상 길이는 timeline.py에서)")

