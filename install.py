"""스킬을 연결하고 준비 상태를 알려 준다.

python3 install.py             Claude Code(~/.claude/skills)에 연결
python3 install.py --codex     Codex(~/.codex/skills)에 연결
python3 install.py --local-tts <폴더>   이미 설치한 로컬 음성 모델(.venv와 models가 있는 폴더)을 쓰게 저장
python3 install.py --voice <파일> "<그 소리가 읽은 말>" ["<이름·출처>"]   새 영상의 기본 목소리로 저장(60초 이하, 쓸 권리가 있는 것만)
python3 install.py --check     연결하지 않고 준비 상태만
이미 다른 것이 있으면 건드리지 않고 멈춘다. 지울 때는 연결(심볼릭 링크)만 지우면 된다."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

NAME = "service-video-studio"
SRC = Path(__file__).resolve().parent / "skill" / NAME


def link(home: Path):
    dst = home / "skills" / NAME
    if dst.is_symlink() and dst.resolve() == SRC:
        return print(f"이미 연결됨: {dst}")
    if dst.exists() or dst.is_symlink():
        raise SystemExit(f"이미 다른 것이 있음: {dst}\n옮기거나 이름을 바꾼 뒤 다시 실행하세요.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.symlink_to(SRC)
    print(f"연결함: {dst} → {SRC}")


def check():
    ok = lambda good, name, how: print(f"  {'✓' if good else '✗'} {name}" + ("" if good else f" — {how}"))
    print("준비 상태")
    ok(sys.version_info >= (3, 12), f"Python {sys.version.split()[0]}", "3.12 이상 필요")
    ok(shutil.which("node"), "Node.js", "https://nodejs.org")
    ok(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg", "brew install ffmpeg")
    ok(shutil.which("ego-browser"), "ego-browser(화면 녹화)", "없으면 녹화를 직접 찍어 assets/clips에 넣는다")
    sys.path.insert(0, str(SRC / "scripts"))
    sys.dont_write_bytecode = True
    import tts_local
    r = tts_local.ready(tts_local.home())
    ok(r["drama-3"], f"로컬 음성 Drama 3 ({tts_local.home()})", "install.py --local-tts <폴더> 또는 scripts/setup_local_tts.sh")
    ok(r["s2-pro"], "로컬 음성 S2 Pro(비상업)", "같은 방법")
    ok(os.environ.get("FISH_AUDIO_API_KEY"), "FISH_AUDIO_API_KEY 환경변수(Fish API를 쓸 때만)", "tts.py --env <.env 경로>로 주어도 된다")
    env = os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}
    r = subprocess.run([sys.executable, str(SRC / "scripts" / "selftest.py")], capture_output=True, text=True, env=env)
    ok(r.returncode == 0, "도구 자체 점검", r.stderr.strip()[-200:])


def local_tts(folder: Path):
    sys.path.insert(0, str(SRC / "scripts"))
    sys.dont_write_bytecode = True
    import tts_local
    if not any(tts_local.ready(folder).values()):
        raise SystemExit(f"로컬 음성 모델이 없는 폴더: {folder} (.venv/bin/python과 models/<모델>/.ready가 있어야 함)")
    tts_local.CONFIG.parent.mkdir(parents=True, exist_ok=True)
    c = json.loads(tts_local.CONFIG.read_text()) if tts_local.CONFIG.exists() else {}
    tts_local.CONFIG.write_text(json.dumps(c | {"local_tts_home": str(folder)}, ensure_ascii=False, indent=1))
    print(f"저장: {tts_local.CONFIG}")


def default_voice(src: Path, text: str, note: str):
    sys.path.insert(0, str(SRC / "scripts"))
    sys.dont_write_bytecode = True
    import tts_local
    from lib import dur
    if not src.exists() or not text.strip() or dur(src) > 60:
        raise SystemExit("60초 이하의 소리 파일과 그 소리가 실제로 읽은 말이 필요합니다.")
    dst = tts_local.CONFIG.parent / "voice" / f"default{src.suffix}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    c = tts_local.config() | {"voice": {"audio": str(dst), "text": text.strip(), "note": note}}
    tts_local.CONFIG.write_text(json.dumps(c, ensure_ascii=False, indent=1))
    print(f"기본 목소리 저장: {dst}")


if __name__ == "__main__":
    if "--voice" in sys.argv:
        a = sys.argv[sys.argv.index("--voice") + 1:]
        default_voice(Path(a[0]).expanduser().resolve(), a[1], a[2] if len(a) > 2 else "")
        raise SystemExit
    if "--local-tts" in sys.argv:
        local_tts(Path(sys.argv[sys.argv.index("--local-tts") + 1]).expanduser().resolve())
        check()
        raise SystemExit
    if "--check" not in sys.argv:
        link(Path.home() / (".codex" if "--codex" in sys.argv else ".claude"))
    check()
