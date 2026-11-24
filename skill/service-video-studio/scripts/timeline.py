"""시간표: 문장 음성을 speed배속(음높이 유지)으로 바꾸고 쉼을 넣어 이어 놓는다 → assets/vo/<ID>.mp3, timeline.json.

장면을 만들기 전에 이 시간표부터 정한다. 다 만든 영상을 나중에 자르거나 배속하면 전환·효과음이 잘려 나간다.
파트 장면은 앞뒤 파트 쉼의 가운데에서 바뀐다."""
from statistics import median

from lib import dur, load, lufs, run, save, work

VO_LUFS = -15.5  # 기준작 내레이션 크기. 배경음 크기가 여기에 맞춰져 있다


def layout(d, lengths):
    """문장 길이(초) → 시간표. lengths: {id: 초}."""
    t, prev, rows = d["lead"], None, []
    for ln in d["lines"]:
        if prev is not None:
            t += d["part_gap"] if ln["part"] != prev else d["gap"]
        a = lengths[ln["id"]]
        rows.append({"id": ln["id"], "part": ln["part"], "start": round(t, 2), "audio": round(a, 2), "end": round(t + a, 2), "cap": ln["cap"]})
        t += a
        prev = ln["part"]
    parts = {}
    for r in rows:
        parts.setdefault(r["part"], {"start": r["start"]})["end"] = r["end"]
    names, total = list(parts), round(rows[-1]["end"] + d["tail"], 2)
    for i, n in enumerate(names):
        parts[n]["scene_start"] = 0.0 if i == 0 else round((parts[names[i - 1]]["end"] + parts[n]["start"]) / 2, 2)
    for i, n in enumerate(names):
        parts[n]["scene_end"] = parts[names[i + 1]]["scene_start"] if i + 1 < len(names) else total
    return {"speed": d["speed"], "duration": total, "parts": parts, "lines": rows}


def main():
    W = work()
    d = load(W / "script.json")
    raw = [W / "assets" / "vo_raw" / f"{ln['id']}.mp3" for ln in d["lines"]]
    gain = VO_LUFS - median(lufs(p) for p in raw)  # 문장끼리의 세기 차이(속삭임·강조)는 남기고 전체만 올린다
    level = f",volume={gain:.1f}dB,alimiter=limit=0.89:level=disabled" if abs(gain) >= 1 else ""
    lengths = {}
    for ln in d["lines"]:
        src, dst = W / "assets" / "vo_raw" / f"{ln['id']}.mp3", W / "assets" / "vo" / f"{ln['id']}.mp3"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", f"atempo={d['speed']}{level}", "-c:a", "libmp3lame", "-b:a", "192k", dst])
        lengths[ln["id"]] = dur(dst)
    tl = layout(d, lengths)
    save(W / "timeline.json", tl)
    if level:
        print(f"내레이션 크기 {gain:+.1f}dB 맞춤")
    for n, p in tl["parts"].items():
        print(f"{n} {d['parts'][n]}: {p['scene_start']} → {p['scene_end']} ({p['scene_end'] - p['scene_start']:.1f}초)")
    lo, hi = d["target_sec"]
    print(f"합계 {tl['duration']}초 (목표 {lo}~{hi}초{'' if lo <= tl['duration'] <= hi else ' — 벗어남: 대본을 줄이거나 target_sec를 고침'})")


if __name__ == "__main__":
    main()
