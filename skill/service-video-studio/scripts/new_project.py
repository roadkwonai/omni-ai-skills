"""새 영상 작업 폴더를 만든다: python3 new_project.py <작업 폴더> "<제목>" [목표 초, 예 25-40]
있는 파일은 덮어쓰지 않는다."""
import shutil
import sys

import tts_local
from lib import SKILL, audio, save, work

W = work()
title = sys.argv[2] if len(sys.argv) > 2 else W.name
lo, hi = (sys.argv[3] if len(sys.argv) > 3 else "60-120").split("-")
A = SKILL / "assets"
for d in ("assets/fonts", "assets/clips", "assets/img", "assets/vo", "assets/vo_raw", "compositions", "capture", "boards", "renders"):
    (W / d).mkdir(parents=True, exist_ok=True)


def put(src, dst):
    if not dst.exists():
        shutil.copy2(src, dst)


put(A / "fonts" / "PretendardVariable.woff2", W / "assets" / "fonts" / "PretendardVariable.woff2")
put(audio("bgm/tonight-hiphop"), W / "assets" / "bgm.mp3")
put(A / "package.json", W / "package.json")
put(A / "hyperframes.json", W / "hyperframes.json")
put(A / "SPEC.md", W / "SPEC.md")
for f in (A / "capture").iterdir():
    put(f, W / "capture" / f.name)
if not (W / "remotion").exists():
    shutil.copytree(A / "remotion", W / "remotion")
    (W / "remotion" / "public").mkdir()
    put(A / "fonts" / "PretendardVariable.woff2", W / "remotion" / "public" / "PretendardVariable.woff2")
if not (W / "meta.json").exists():
    save(W / "meta.json", {"id": W.name, "name": title})
if not (W / "script.json").exists():
    local = tts_local.ready(tts_local.home())["drama-3"]
    save(W / "script.json", {
        "title": title, "mood": "calm", "target_sec": [int(lo), int(hi)], "accent": "#ff6600",
        "voice_engine": "drama-3" if local else "fish-api", "voice_opts": tts_local.default_opts(W) if local else {},
        "voice": "ca3becd0e8014733b0405c3ad9ffe50e", "pace": 5.6 if local else 6.0,
        "speed": 1.1, "gap": 1.0, "part_gap": 1.5, "lead": 0.6, "tail": 2.5,
        "reading": {}, "banned": ["보장", "무조건", "확실한 수익"],
        "parts": {"P0": "훅"}, "theme": [["P0", 0, "dark"]], "sfx": [],
        "lines": [{"id": "S01", "part": "P0", "cap": "첫 문장을 여기에 씁니다.", "kind": "hook", "screen": "무엇이 보이는지", "fact": "사실 근거(문서·화면). 주장이 아니면 '-'"}],
    })
print(f"작업 폴더 준비: {W}")
