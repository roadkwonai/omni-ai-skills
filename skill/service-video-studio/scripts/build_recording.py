"""녹화 프레임 → 30fps mp4: python3 build_recording.py <녹화 폴더(frames.json)> <결과.mp4>  (record.py가 부른다)

프레임 시각대로 놓아 실제 속도를 지키고, 0.3초 넘는 간격(화면을 다시 그리는 동안 녹화를 멈춘 곳)은 0.1초로 잘라 점프 컷으로 만든다."""
import json
import sys

from lib import dur, load, run, work

W = work()
d = load(W / "frames.json")
fr, dst = d["frames"], sys.argv[2]
# 절대 경로로 적는다: 상대 경로 녹화 폴더에서도 ffconcat이 프레임을 찾는다
lines, at, clock = ["ffconcat version 1.0"], [], 0.0
for (p, t), (_, t2) in zip(fr, fr[1:] + [[None, fr[-1][1] + 70]]):
    gap = (t2 - t) / 1000
    gap = gap if gap <= 0.3 else 0.1
    at.append((t, clock))
    clock += gap
    lines += [f"file '{W / p}'", f"duration {gap:.3f}"]
lines.append(f"file '{W / fr[-1][0]}'")
(W / "list.ffconcat").write_text("\n".join(lines) + "\n")
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", W / "list.ffconcat",
     "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "18", "-movflags", "+faststart", dst])
print(f"프레임 {len(fr)}장 → {dst} ({dur(dst):.1f}초)")
for name, ms in d.get("marks", {}).items():  # 멈춘 구간을 뺀 클립 안 시각 = data-media-start에 쓸 값
    print(f"  {name}: {max([c for t, c in at if t <= ms] or [0]):.2f}초")
for name, r in d.get("spots", {}).items():  # SpotTour stops에 그대로 쓰는 좌표(1920×1080 기준)
    print(f"  칸 {name}: " + json.dumps(r, ensure_ascii=False))
