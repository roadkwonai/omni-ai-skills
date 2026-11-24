"""파트 하나를 녹화한다: python3 record.py <작업 폴더> <이름> <URL> [첫 그리기 대기 ms, 기본 3000]

capture/<이름>.scene.js(장면) + capture/mask.config.json(가림) → capture/out/<이름>/ → assets/clips/<이름>.mp4.
클립 안 표시 시각과 SpotTour 좌표를 출력한다. 이미 있는 녹화는 지우고 다시 찍는다."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

from lib import load, work

W = work()
name, url = sys.argv[2], sys.argv[3]
out = W / "capture" / "out" / name
if not shutil.which("ego-browser"):
    raise SystemExit(f"ego-browser가 없어 녹화할 수 없음 — 직접 찍은 1920×1080 30fps 영상을 {W}/assets/clips/{name}.mp4에 넣고 가림을 확인한다")
shutil.rmtree(out, ignore_errors=True)
out.mkdir(parents=True)
cfg = load(W / "capture" / "mask.config.json")
R = {"out": str(out), "url": url, "css": cfg.get("css", 1920), "first": int(sys.argv[4]) if len(sys.argv) > 4 else 3000, "cfg": {"accent": load(W / "script.json")["accent"], **cfg["mask"]},
     "mask": (W / "capture" / "mask.js").read_text(), "img": str(W / "assets" / "img"), "pub": str(W / "remotion" / "public")}
js = (Path(__file__).parent / "record.js").read_text().replace("/*SCENE*/", (W / "capture" / f"{name}.scene.js").read_text())
r = subprocess.run(["ego-browser", "nodejs"], input=f"const R = {json.dumps(R)};\n{js}", text=True, capture_output=True, timeout=300)
print(r.stdout.strip()[-800:])
if not (out / "frames.json").exists():
    raise SystemExit(f"녹화 실패: {r.stderr[-800:]}")
err = load(out / "frames.json")["err"]
if err:
    raise SystemExit(f"장면 오류: {err}")
subprocess.run([sys.executable, str(Path(__file__).parent / "build_recording.py"), str(out), str(W / "assets" / "clips" / f"{name}.mp4")], check=True)
