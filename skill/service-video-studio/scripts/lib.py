"""모든 단계가 함께 쓰는 것: 작업 폴더의 script.json·timeline.json 읽기, 길이 재기."""
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

HF = "hyperframes@0.9.72"  # 이 판으로 확인한 흐름. 올리면 check·snapshot부터 다시 본다
SKILL = Path(__file__).resolve().parents[1]


def work() -> Path:
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        raise SystemExit(f"사용: python3 {Path(sys.argv[0]).name} <작업 폴더>")
    return Path(sys.argv[1]).resolve()


def load(p: Path):
    return json.loads(p.read_text())


def save(p: Path, d, indent=1):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=indent))


def dur(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def lufs(path) -> float:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])


def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def audio(name: str) -> Path:
    """bgm/<곡> · sfx/<소리>. 음원은 재배포할 수 없어 저장소에 없다: 처음 쓸 때 원 출처에서 받아 해시를 확인한다."""
    dst = SKILL / "assets" / f"{name}.mp3"
    if not dst.exists():
        f = load(SKILL / "assets" / "sound.json")["files"][name]
        try:
            data = urllib.request.urlopen(urllib.request.Request(f["url"], headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
        except OSError as e:
            raise SystemExit(f"음원을 받지 못함({name}): {e} — 인터넷 연결을 확인하거나 {f['url']}을 {dst}로 저장")
        if hashlib.sha256(data).hexdigest() != f["sha256"]:
            raise SystemExit(f"음원이 확인한 것과 다름({name}): {f['url']} — 내용이 바뀌었으니 들어 보고 sound.json을 고친다")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
    return dst
