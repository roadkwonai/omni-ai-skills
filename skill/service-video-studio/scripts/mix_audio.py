"""렌더 결과(내레이션만 든 영상)에 배경음·효과음을 섞는다.

python3 mix_audio.py <작업 폴더> <렌더.mp4> <최종.mp4>
python3 mix_audio.py <작업 폴더> --preview [초, 기본 20]   내레이션 앞부분에 배경음 후보를 하나씩 깐 mp3 → previews/

배경음: assets/bgm.mp3(pick.py가 고른 곡). 곡마다 녹음 크기가 10dB까지 달라 재서 같은 크기로 맞추고, 내레이션이 나오면 자동으로 더 낮춘다. 파일이 없으면 뺀다.
효과음: script.json의 kit(clean 합성 · soft · cinematic). 파트 전환 whoosh는 자동, 나머지는 sfx [["P3", 장면 안 초, "pop"], ...] (whoosh·tick·thud·pop). 장면마다 1~2종류만.
음량: −14 LUFS, 최고 −1 dBTP."""
import array
import math
import subprocess
import sys

from lib import SKILL, audio, dur, load, lufs, run, work

MAKE = {
    "whoosh": "anoisesrc=d=0.5:c=pink:a=0.6,highpass=f=600,lowpass=f=5000,afade=t=in:d=0.22,afade=t=out:st=0.25:d=0.25",
    "tick": "sine=f=1700:d=0.05,afade=t=out:st=0.01:d=0.04,volume=0.5",
    "thud": "sine=f=85:d=0.22,afade=t=out:st=0.02:d=0.2,volume=1.6",
    "pop": "sine=f=1100:d=0.07,afade=t=out:st=0.02:d=0.05,volume=0.35",
}
PEAK = {"whoosh": -12.0, "tick": -14.0, "thud": -6.0, "pop": -16.0}  # 파일 효과음을 맞출 최고값(dBFS, 섞기 전)
BGM_LUFS = -22.7  # 기준작의 배경음 크기(낮추기 전)
LEAD = {"whoosh": 0.23, "tick": 0.0, "thud": 0.0, "pop": 0.0}  # events의 시각에서 소리 정점까지(합성음 기준)


def events(d, tl):
    ev = [("whoosh", max(0, p["scene_start"] - 0.2)) for p in list(tl["parts"].values())[1:]]
    for part, t, kind in d.get("sfx", []):
        p = tl["parts"][part]
        assert kind in MAKE, f"모르는 효과음 {kind}"
        assert 0 <= t <= p["scene_end"] - p["scene_start"], f"{part} {t}초는 장면 밖"
        ev.append((kind, round(p["scene_start"] + t, 3)))
    return sorted(ev, key=lambda e: e[1])


def peak(path):
    """소리 파일의 (정점 시각 초, 최고 dBFS)."""
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", "8000", "-"], capture_output=True, check=True).stdout
    a = array.array("h", raw)
    i = max(range(len(a)), key=lambda k: abs(a[k]))
    return i / 8000, 20 * math.log10(max(1, abs(a[i])) / 32768)


def mix(W, src, dst, ev, bgm, total, kit, video=True):
    (W / "assets" / "sfx").mkdir(exist_ok=True)
    inputs, f, parts = ["-i", src], [], ["[vo]"]
    f.append("[0:a]aresample=48000,aformat=channel_layouts=stereo" + (",asplit=2[vo][key]" if bgm else "[vo]"))
    n = 1
    if bgm:
        inputs += ["-stream_loop", "-1", "-i", bgm]
        f.append(f"[1:a]atrim=0:{total},asetpts=N/SR/TB,volume={BGM_LUFS - lufs(bgm):.2f}dB,afade=t=in:d=1.5,afade=t=out:st={max(0, total - 3.5)}:d=3.5,aresample=48000,aformat=channel_layouts=stereo[bgm]")
        f.append("[bgm][key]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400:makeup=1[duck]")
        parts.append("[duck]")
        n = 2
    files = load(SKILL / "assets" / "sound.json")["kit"][kit]["files"]
    labels = []
    for kind in MAKE:
        ts = [t for k, t in ev if k == kind and t < total]
        if not ts:
            continue
        shift, fx = 0.0, ""
        if kind in files:  # 파일 효과음은 정점이 화면 움직임과 같은 순간에 오게 당기고, 크기를 맞추고, 긴 꼬리는 자른다
            wav = audio(f"sfx/{files[kind]}")
            at, db = peak(wav)
            shift, fx = at - LEAD[kind], f"atrim=0:{at + 1.2:.2f},afade=t=out:st={at + 0.6:.2f}:d=0.6,volume={PEAK[kind] - db:.1f}dB,"
        else:
            wav = W / "assets" / "sfx" / f"{kind}.wav"
            run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", MAKE[kind] + ",aresample=48000", "-ac", "1", wav])
        inputs += ["-i", wav]
        f.append(f"[{n}:a]{fx}aresample=48000,aformat=channel_layouts=stereo,asplit={len(ts)}" + "".join(f"[{kind}{i}]" for i in range(len(ts))))
        for i, t in enumerate(ts):
            f.append(f"[{kind}{i}]adelay={max(0, int((t - shift) * 1000))}:all=1,apad=whole_dur={total}[e{len(labels)}]")
            labels.append(f"[e{len(labels)}]")
        n += 1
    if labels:
        f.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,volume=0.55[sfx]")
        parts.append("[sfx]")
    f.append("".join(parts) + f"amix=inputs={len(parts)}:normalize=0:duration=first,loudnorm=I=-14:TP=-1:LRA=11[a]")
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(f), *(["-map", "0:v", "-c:v", "copy"] if video else []), "-map", "[a]",
         *(["-c:a", "aac", "-movflags", "+faststart"] if video else ["-c:a", "libmp3lame"]), "-b:a", "192k", "-ar", "48000", dst])


def main():
    W = work()
    d, tl = load(W / "script.json"), load(W / "timeline.json")
    ev, kit, bgm = events(d, tl), (d.get("kit") or {}).get("name", "clean"), W / "assets" / "bgm.mp3"
    if "--preview" in sys.argv:
        sec = float(sys.argv[sys.argv.index("--preview") + 1]) if len(sys.argv) > sys.argv.index("--preview") + 1 else 20.0
        sec = min(sec, tl["duration"])
        out = W / "previews"
        out.mkdir(exist_ok=True)
        rows = [r for r in tl["lines"] if r["start"] < sec]
        ins = [x for r in rows for x in ("-i", W / "assets" / "vo" / f"{r['id']}.mp3")]
        g = ";".join(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(r['start'] * 1000)}:all=1,apad=whole_dur={sec}[v{i}]" for i, r in enumerate(rows))
        g += ";" + "".join(f"[v{i}]" for i in range(len(rows))) + f"amix=inputs={len(rows)}:normalize=0,atrim=0:{sec}[a]"
        run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", g, "-map", "[a]", out / "vo.wav"])
        names = list(load(SKILL / "assets" / "sound.json")["bgm"])
        cur = (d.get("bgm") or {}).get("name")
        tracks = {n: audio(f"bgm/{n}") for n in names} | ({"지금-고른-곡": bgm} if bgm.exists() and cur not in names else {})
        for n, p in tracks.items():
            mix(W, out / "vo.wav", out / f"{n}.mp3", ev, p, sec, kit, video=False)
            print(f"previews/{n}.mp3" + ("  ← 지금 고른 곡" if n == cur else ""))
        return
    src, dst = sys.argv[2], sys.argv[3]
    total = dur(src)
    mix(W, src, dst, ev, bgm if bgm.exists() else None, total, kit)
    print(f"배경음 {(d.get('bgm') or {}).get('name', 'assets/bgm.mp3') if bgm.exists() else '없음'} · 효과음 {kit} {len(ev)}개 · {total:.2f}초 → {dst}")


if __name__ == "__main__":
    main()
