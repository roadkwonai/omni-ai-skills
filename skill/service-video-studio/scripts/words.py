"""음성 → 단어 시각 → words.json + 자막(captions.html): python3 words.py <작업 폴더>

whisper는 단어를 다르게 나누거나 틀리게 적는다. 그래서 글자를 맞추지 않고 '글자 순서'로 붙인다:
받아 적은 단어(숫자는 다시 한글 읽기로: 6.4%→육점사퍼센트)의 시간을 글자마다 고르게 나누고,
읽기(tts)의 i번째 글자를 비율로 대응시킨 뒤 자막(cap) 단어를 쓴다.
출력의 +초는 '장면 시작 기준'이라 compositions/<part>.html의 tl 시각과 SpotTour의 stops에 그대로 쓴다."""
import difflib
import re
import shutil
import subprocess

from lib import HF, load, save, work
from reading import plain, to_reading

CH = re.compile(r"[가-힣A-Za-z0-9]")


def chars(s):
    return CH.findall(s)


def spoken(text):
    try:
        return to_reading(text)
    except ValueError:  # 사전에 없는 영어
        return text


def char_times(words):
    out = []
    for w in words:
        n = len(chars(spoken(w["text"])))
        step = (w["end"] - w["start"]) / n if n else 0
        out += [(w["start"] + k * step, w["start"] + (k + 1) * step) for k in range(n)]
    return out


def align(line, heard, start):
    """한 문장의 자막 단어 시각."""
    tl, tts, cap = char_times(heard), plain(line["tts"]).split(), line["cap"].split()
    assert len(tts) == len(cap), f"{line['id']}: 어절 수가 다름"
    total = sum(len(chars(w)) for w in tts)
    assert tl and total, f"{line['id']}: 받아 적은 말이 없음"
    out, i = [], 0
    for tw, cw in zip(tts, cap):
        n = len(chars(tw)) or 1
        a = tl[min(len(tl) - 1, int(i * len(tl) / total))][0]
        b = tl[max(0, min(len(tl) - 1, int((i + n) * len(tl) / total) - 1))][1]
        out.append({"id": line["id"], "text": cw, "start": round(start + a, 3), "end": round(start + max(b, a + 0.08), 3)})
        i += n
    return out


def transcribe(W, i):
    """assets/tr/<ID>/에 음성을 복사해 받아 적는다. 음성이 바뀌면 다시 한다."""
    d, src = W / "assets" / "tr" / i, W / "assets" / "vo" / f"{i}.mp3"
    mp3, js = d / "a.mp3", d / "transcript.json"
    if not (js.exists() and mp3.exists() and mp3.read_bytes() == src.read_bytes()):
        d.mkdir(parents=True, exist_ok=True)
        js.unlink(missing_ok=True)
        shutil.copy2(src, mp3)
        # 기본 모델(small.en)은 한국어를 영어로 번역해 버리므로 모델·언어를 꼭 준다
        r = subprocess.run(["npx", "--yes", HF, "transcribe", str(mp3), "--model", "small", "--language", "ko", "--json"],
                           cwd=W, capture_output=True, text=True, timeout=600)
        if not js.exists():
            raise SystemExit(f"{i} 받아쓰기 실패: {r.stdout[-400:]} {r.stderr[-400:]}")
    tr = load(js)
    return tr.get("words", tr) if isinstance(tr, dict) else tr


def main():
    W = work()
    d, tl = load(W / "script.json"), load(W / "timeline.json")
    start = {r["id"]: r["start"] for r in tl["lines"]}
    words, prev = [], None
    for ln in d["lines"]:
        heard = transcribe(W, ln["id"])
        ratio = sum(len(chars(spoken(w["text"]))) for w in heard) / max(1, len(chars(plain(ln["tts"]))))
        same = difflib.SequenceMatcher(None, "".join(chars(spoken(" ".join(w["text"] for w in heard)))), "".join(chars(plain(ln["tts"])))).ratio()
        warn = "" if 0.7 <= ratio <= 1.3 and same >= 0.75 else f"  ← 받아 적은 말이 대본과 {same:.0%} 같음: 음성을 들어 보고 다르면 tts.py --only {ln['id']}(시드를 바꿔) 다시"
        ws = align(ln, heard, start[ln["id"]])
        words += ws
        base = tl["parts"][ln["part"]]["scene_start"]
        if ln["part"] != prev:
            print(f"\n[{ln['part']}] 장면 시작 {base}초, 길이 {tl['parts'][ln['part']]['scene_end'] - base:.2f}초")
            prev = ln["part"]
        print(ln["id"], " ".join(f"{w['text']}+{w['start'] - base:.2f}" for w in ws) + warn)
    theme = sorted([tl["parts"][p]["scene_start"] + t, name] for p, t, name in d["theme"])
    save(W / "words.json", {"duration": tl["duration"], "accent": d["accent"], "theme": theme, "words": words})
    import captions
    captions.build(W)


if __name__ == "__main__":
    main()
