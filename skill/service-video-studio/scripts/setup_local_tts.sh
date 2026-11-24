#!/bin/bash
# Apple Silicon용 로컬 TTS 설치. 사용법: setup_local_tts.sh [설치 폴더, 기본 ~/.local/share/local-tts] [이미 받은 s2-pro 폴더]
# 이미 설치한 폴더(.venv와 models가 있는 곳)가 있으면 받지 말고 install.py --local-tts <폴더>로 연결한다.
# s2-pro 폴더를 주면 이미 받은 원본을 쓰고, 없으면 Hugging Face에서 받는다(약 11GB). Drama 3는 약 24GB를 받는다.
set -euo pipefail
home="${1:-$HOME/.local/share/local-tts}"
source_dir="${2:-}"
[ -z "$source_dir" ] || source_dir="$(cd "$source_dir" && pwd)"
[ "$(uname -sm)" = "Darwin arm64" ] || { echo "Apple Silicon Mac에서만 설치할 수 있습니다." >&2; exit 1; }
mkdir -p "$home/models"
cd "$home"
home="$PWD"
[ -x .venv/bin/python ] || uv venv -p 3.12 .venv
uv pip install -p .venv/bin/python "mlx-audio==0.6.7" soundfile huggingface_hub

if [ ! -e models/s2-pro-8bit/.ready ]; then
  # 중간에 멈춰도 다시 실행하면 받은 파일부터 이어간다.
  work="$home/s2-pro-source"
  mkdir -p "$work"
  if [ -n "$source_dir" ]; then
    # APFS 복제라서 원본 용량을 다시 쓰지 않는다.
    cp -cf "$source_dir"/*.{json,jinja,safetensors,pth} "$source_dir"/LICENSE* "$work/"
  else
    .venv/bin/hf download fishaudio/s2-pro --local-dir "$work"
  fi
  uv run --no-project -p 3.12 --with "torch==2.8.0" --with safetensors --with numpy python -I - "$work" <<'PY'
import sys, torch
from safetensors.torch import save_file
root = sys.argv[1]
state = torch.load(f"{root}/codec.pth", map_location="cpu", weights_only=True, mmap=True)
state = state.get("state_dict", state)
save_file({k: v.contiguous().clone() for k, v in state.items() if torch.is_tensor(v)}, f"{root}/pytorch_model.safetensors")
PY
  rm -rf models/s2-pro-8bit
  .venv/bin/python -m mlx_audio.convert --hf-path "$work" --mlx-path models/s2-pro-8bit -q --q-bits 8
  cp "$work"/LICENSE* models/s2-pro-8bit/
  touch models/s2-pro-8bit/.ready
  rm -rf "$work"
fi

if [ ! -e models/drama-3-4bit/.ready ]; then
  .venv/bin/hf download mlx-community/fish-audio-drama-3-4bit --revision 2b0c8028998533972e77359cce56b8bf1c5d6d4a --local-dir models/drama-3-4bit
  touch models/drama-3-4bit/.ready
fi
echo "로컬 TTS를 설치했습니다: $home"
echo "연결: python3 install.py --local-tts $home"
