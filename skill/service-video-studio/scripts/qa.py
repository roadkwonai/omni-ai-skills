"""최종 검수: python3 qa.py <작업 폴더> <영상.mp4>  → qa/ 폴더(시트·원본 프레임), 기계 검사 결과. 실패가 있으면 종료 코드 1.

기계가 보는 것: 크기·fps·길이(시간표와 0.3초 안)·음량(−14±1 LUFS)·최고(0 dBTP 미만)·검은 화면·3초 넘는 정지 화면·문장 사이 쉼.
사람·에이전트가 볼 것: qa/frames의 원본 크기 프레임(가림 누락은 축소 시트에서 안 보인다), qa/sync의 자막 강조 단어, 처음부터 끝까지 한 번 재생."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from lib import dur, load, run, work


def ff(args):
    return subprocess.run(["ffmpeg", "-hide_banner", *args], capture_output=True, text=True).stderr


def main():
    W = work()
    v, tl, words = sys.argv[2], load(W / "timeline.json"), load(W / "words.json")["words"]
    d = load(W / "script.json")
    Q = W / "qa"
    shutil.rmtree(Q, ignore_errors=True)
    for s in ("frames", "sync"):
        (Q / s).mkdir(parents=True)
    bad, note = [], []
    st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", v], capture_output=True, text=True, check=True).stdout)["streams"]
    vs = next(s for s in st if s["codec_type"] == "video")
    if (vs["width"], vs["height"], vs["r_frame_rate"]) != (1920, 1080, "30/1"):
        bad.append(f"영상 형식 {vs['width']}x{vs['height']} {vs['r_frame_rate']}")
    if not any(s["codec_type"] == "audio" for s in st):
        bad.append("소리 없음")
    if abs(dur(v) - tl["duration"]) > 0.3:
        bad.append(f"길이 {dur(v):.2f}초 ≠ 시간표 {tl['duration']}초")
    lo, hi = d["target_sec"]
    if not lo <= dur(v) <= hi:
        bad.append(f"길이 {dur(v):.1f}초가 목표 {lo}~{hi}초 밖")
    loud = ff(["-i", v, "-af", "ebur128=peak=true", "-f", "null", "-"]).rsplit("Summary:", 1)[-1]
    I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", loud).group(1))
    peak = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", loud).group(1))
    if abs(I + 14) > 1:
        bad.append(f"음량 {I} LUFS")
    if peak >= 0:
        bad.append(f"최고 {peak} dBFS")
    for s, e in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", ff(["-i", v, "-vf", "crop=iw:ih*0.86:0:0,blackdetect=d=0.5:pix_th=0.10:pic_th=0.995", "-an", "-f", "null", "-"])):
        note.append(f"빈 화면 {float(s):.1f}~{float(e):.1f}초")
    fz = ff(["-i", v, "-vf", "crop=iw:ih*0.86:0:0,freezedetect=n=0.0008:d=3", "-an", "-f", "null", "-"])  # 자막 줄은 빼고 본다
    for s, e in zip(re.findall(r"freeze_start: ([\d.]+)", fz), re.findall(r"freeze_duration: ([\d.]+)", fz) + ["끝까지"]):
        note.append(f"정지 화면 {float(s):.1f}초부터 {e if e == "끝까지" else e + "초 동안"}")
    for a, b in zip(tl["lines"], tl["lines"][1:]):
        want = d["part_gap"] if a["part"] != b["part"] else d["gap"]
        if abs(b["start"] - a["end"] - want) > 0.05:
            note.append(f"{a['id']}→{b['id']} 쉼 {b['start'] - a['end']:.2f}초(설정 {want}) — script.json을 고친 뒤 timeline.py를 다시 안 돌린 듯")
    # 파트마다 무엇으로 만들었는지: 실제 녹화 0초인 화면 파트, 한 번도 안 쓴 Remotion 샷을 여기서 드러낸다
    ported = W / "remotion" / "ported.json"
    tours = (set(load(W / "remotion" / "tours.json")) - {"Example"}) | ({x["id"] for x in load(ported)} if ported.exists() else set())
    used = False
    for part in tl["parts"]:
        f = W / "compositions" / f"{part.lower()}.html"
        src = re.sub(r"<!--.*?-->", "", f.read_text(), flags=re.S) if f.exists() else ""
        clips = [Path(c).stem for c in re.findall(r'<video[^>]*src="([^"]+)"', src)]
        spot = [c for c in clips if c in tours]
        used |= bool(spot)
        print(f"  {part} {d['parts'][part]}: 녹화 {len(clips) - len(spot)} · Remotion 샷 {len(spot)} · 숫자 {len(re.findall(r'count[(]', src))} · 선 {src.count('draw(')}")
    # 고른 레시피(script.json shot)와 실제 장면이 같은지: Remotion 샷은 그 파트가 그 종류의 클립을 써야 한다
    T = load(W / "remotion" / "tours.json")
    kinds = {k: v.get("shot", "SpotTour") for k, v in T.items()} | ({x["id"]: x["shot"] for x in load(ported)} if ported.exists() else {})
    for ln in d["lines"]:
        want = (ln.get("shot") or {}).get("name")
        f = W / "compositions" / f"{ln['part'].lower()}.html"
        if not want or want.startswith("hf:") or not f.exists():
            continue
        src = re.sub(r"<!--.*?-->", "", f.read_text(), flags=re.S)
        have = {kinds.get(Path(c).stem, "record") for c in re.findall(r'<video[^>]*src="([^"]+)"', src)}
        if want not in have:
            note.append(f"{ln['id']} 레시피 {want}를 {ln['part']} 장면이 쓰지 않음(있는 것: {', '.join(sorted(have)) or '없음'}) — RECIPES.md와 영상이 다름")
    if not used:
        note.append("Remotion 샷을 쓴 파트가 없음 — RECIPES.md의 선택이 반영됐는지 본다")
    # 문장마다 세 장(시작·가운데·끝) + 파트가 바뀐 직후. 가림과 글자 겹침은 이 원본 크기 프레임을 확대해 본다
    at = sorted({round(t, 2) for r in tl["lines"] for t in (r["start"] + 0.3, (r["start"] + r["end"]) / 2, r["end"] - 0.1)}
                | {round(p["scene_start"] + 0.4, 2) for p in tl["parts"].values()})
    for i, t in enumerate(at):
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", t, "-i", v, "-frames:v", "1", "-q:v", "2", Q / "frames" / f"{i:03d}_{t:07.2f}s.jpg"])
    run(["ffmpeg", "-y", "-loglevel", "error", "-pattern_type", "glob", "-i", str(Q / "frames" / "*.jpg"),
         "-vf", "scale=640:-1,tile=3x4:padding=6:color=white", Q / "sheet-%02d.jpg"])
    step = max(1, len(words) // 6)
    sync = []
    for w in words[step // 2::step]:
        t = round((w["start"] + w["end"]) / 2 + 0.05, 2)
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", t, "-i", v, "-frames:v", "1", "-vf", "crop=iw:200:0:ih-240", Q / "sync" / f"{t:07.2f}s.jpg"])
        sync.append(f"{t}초 → 강조 단어가 '{w['text']}'이어야 함")
    print(f"{v}: {dur(v):.2f}초, {I} LUFS, 최고 {peak} dBFS, 프레임 {len(at)}장 → {Q}/sheet-*.jpg")
    for s in sync:
        print("  자막 확인", s)
    for n in note:
        print("확인:", n)
    for b in bad:
        print("실패:", b)
    print("기계 검사 통과 — 이제 qa/frames를 원본 크기로 보고 영상을 끝까지 재생하세요" if not bad else f"기계 검사 실패 {len(bad)}건")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
