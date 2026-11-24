"""로컬 Fish Audio 모델(Drama 3 4bit · S2 Pro 8bit, Apple Silicon MLX)로 문장별 음성을 만든다. tts.py가 부른다.

script.json의 voice_engine("drama-3"|"s2-pro")과 voice_opts를 쓰고, 문장의 opts가 그 위에 덮인다.
목소리는 셋 중 하나다(모두 assets/voice/ref.wav 한 소리를 모든 문장의 참조로 써서 문장마다 목소리가 달라지지 않게 한다).
  design  성별·나이·음높이·음색·분위기·설명·장면으로 새로 만든다(Drama 3가 한 번 읽고, S2 Pro도 그 소리를 참조한다)
  ref     {"audio": 파일, "text": 그 소리가 실제로 읽은 말} — 60초 이하, 쓸 권리가 있는 목소리만
  없음    기본 설계(차분한 중년 남성)
대사 안 지시: 문장의 tts에 [pause]·[sighs]나 <emphasis>말</emphasis>처럼 적는다(자막에는 나오지 않는다)."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from lib import dur, load, run, save
from reading import plain

FOLDERS = {"s2-pro": "s2-pro-8bit", "drama-3": "drama-3-4bit"}
CONFIG = Path.home() / ".config" / "video-showcase" / "config.json"
LICENSE = {"drama-3": "Drama 3: 최근 12개월 매출 50만 달러 미만이면 상업 이용 가능(Fish Audio Community License). 실존 인물을 동의 없이 흉내 내지 않는다.",
           "s2-pro": "S2 Pro: 연구·비상업 용도만(Fish Audio Research License). 수익이 목적인 영상에는 쓰지 않는다."}
GENDERS = {"female": "여성", "male": "남성"}
AGES = {"child": "어린이", "teen": "청소년", "young": "청년", "middle": "중년", "old": "노년"}
AGE_NOUNS = {
    "child": {"female": "little girl, about seven years old", "male": "little boy, about seven years old", "any": "child, about seven years old"},
    "teen": {"female": "teenage girl, about sixteen", "male": "teenage boy, about sixteen", "any": "teenager, about sixteen"},
    "young": {"female": "young woman in her twenties", "male": "young man in his twenties", "any": "young adult in their twenties"},
    "middle": {"female": "middle-aged woman in her late forties", "male": "middle-aged man in his late forties", "any": "middle-aged person in their late forties"},
    "old": {"female": "elderly woman, about seventy-five, slightly shaky", "male": "elderly man, about seventy-five, gravelly and slightly shaky", "any": "elderly person, about seventy-five"},
}
PITCHES = {"low": ("낮게", "deep, low-pitched voice"), "high": ("높게", "high-pitched voice")}
TONES = {"soft": ("부드러운", "soft and gentle"), "clear": ("맑은", "clear and bright"), "warm": ("따뜻한", "warm"), "husky": ("허스키한", "husky, breathy"),
         "deep": ("묵직한", "rich and resonant"), "gravelly": ("거친", "gravelly and rough"), "thin": ("가녀린", "thin and delicate"), "cold": ("차가운", "cold and flat")}
ENERGIES = {"calm": ("차분하게", "calm, slow and gentle"), "lively": ("활기차게", "energetic, fast-talking and lively"), "confident": ("당당하게", "confident and assertive"),
            "shy": ("수줍게", "shy and hesitant"), "tired": ("지친 듯", "tired and low-energy")}
STYLES = {"happy": ("기쁨", "with bright eager excitement"), "sad": ("슬픔", "heavy, deflated sadness"), "angry": ("분노", "furious, shouting"), "restrained": ("참는 분노", "furious, barely holding it together"),
          "scared": ("두려움", "breathless and terrified"), "tender": ("다정함", "warm, gentle bedtime voice"), "icy": ("냉정함", "icy calm"), "sarcastic": ("비꼼", "sarcastic and deadpan"),
          "whisper": ("속삭임", "whispering softly"), "shout": ("외침", "shouting"), "excited": ("들뜸", "more excited"), "loud": ("크게", "louder"), "fast": ("빠르게", "faster"),
          "slow": ("천천히", "slower, with more pauses"), "high": ("높은 음", "higher pitch"), "low": ("낮은 음", "lower pitch"),
          "narration": ("내레이션", "calm documentary narration"), "broadcast": ("방송", "professional broadcast tone")}
POINTS = {"drama-3": "pause, long pause, hesitates, laughs, giggles, chuckles, scoffs, sighs, gasps, inhales, exhales, panting, sobs, cries, sniffles, coughs, clears throat, yawns, groans, hums".split(", "),
          "s2-pro": ("laughing, chuckling, sigh, coughing, clearing throat, moaning, pause, short pause, emphasis, inhale, exhale, panting, chuckle, tsk, singing, laughing tone, excited, excited tone, delight, "
                     "sad, angry, surprised, shocked, whisper, shouting, screaming, loud, volume up, low volume, volume down, low voice, with strong accent, interrupting, echo, audience laughter").split(", ")}
SPANS = {"drama-3": "whisper, slow, fast, emphasis, loud, shout, high-pitched, sad, angry, scared, crying, laughing, singing".split(", "), "s2-pro": []}
RANGES = {"speed": (0.7, 1.5), "semitones": (-4, 4), "temperature": (0.3, 1.3), "top_p": (0.5, 1.0), "top_k": (1, 100), "seed": (0, 2**31 - 1)}
INT = {"semitones", "top_k", "seed"}
# 2026-11-24 설계 12가지를 같은 문장으로 재서 가장 또렷하게 빠른 것(초당 4.9음절). 무료 API 목소리는 6.1음절이라 DEFAULT_OPTS의 speed로 맞춘다
DEFAULT_DESIGN = {"gender": "male", "age": "middle", "pitch": "low", "tones": ["warm", "deep"], "note": "clear, composed documentary narrator at a natural conversational pace"}
DEFAULT_OPTS = {"style": "narration", "speed": 1.15}
REF_TEXT = "안녕하세요. 지금부터 이 서비스가 어떤 문제를 풀고, 화면에서 무엇이 움직이는지 차근차근 소개해 드리겠습니다."


def config() -> dict:
    return load(CONFIG) if CONFIG.exists() else {}


def default_opts(W) -> dict:
    """새 프로젝트의 voice_opts. 저장한 기본 목소리(install.py --voice)가 있으면 프로젝트 안에 복사해 참조한다."""
    v = config().get("voice")
    if not v:
        return dict(DEFAULT_OPTS)
    src = Path(v["audio"])
    if not src.exists():
        print(f"기본 목소리 파일이 없어 기본 설계를 씀: {src}")
        return dict(DEFAULT_OPTS)
    dst = W / "assets" / "voice" / f"default{src.suffix}"
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return {"ref": {"audio": str(dst.relative_to(W)), "text": v["text"]}, "style": "narration"}


def home() -> Path:
    """.venv와 models가 있는 폴더: 환경변수 LOCAL_TTS_HOME → install.py --local-tts로 저장한 값 → 기본 위치."""
    p = os.environ.get("LOCAL_TTS_HOME") or config().get("local_tts_home") or Path.home() / ".local/share/local-tts"
    return Path(p).expanduser()


def ready(h: Path) -> dict:
    py = (h / ".venv/bin/python").exists()
    return {m: py and (h / "models" / d / ".ready").exists() for m, d in FOLDERS.items()}


def describe(d: dict) -> str:
    age, g = d.get("age"), d.get("gender")
    person = AGE_NOUNS[age][g or "any"] if age else {"female": "adult woman", "male": "adult man"}.get(g, "")
    parts = [person, PITCHES[d["pitch"]][1] if d.get("pitch") else "", *(TONES[t][1] for t in d.get("tones", [])), ENERGIES[d["energy"]][1] if d.get("energy") else "", d.get("note", "")]
    return ", ".join(p for p in parts if p) or "natural speaking voice"


def text_ok(v, limit):
    return isinstance(v, str) and 0 < len(v.strip()) <= limit and not re.search(r"[\x00-\x1f\x7f\[\]]|<\|", v)


def check_design(d):
    bad = set(d) - {"gender", "age", "pitch", "tones", "energy", "note", "scene", "seed"}
    if bad:
        raise SystemExit(f"design에 모르는 항목: {', '.join(bad)}")
    for k, t in (("gender", GENDERS), ("age", AGES), ("pitch", PITCHES), ("energy", ENERGIES)):
        if k in d and d[k] not in t:
            raise SystemExit(f"design.{k}은 {', '.join(t)} 중 하나")
    if len(d.get("tones", [])) > 3 or any(t not in TONES for t in d.get("tones", [])):
        raise SystemExit(f"design.tones는 최대 3개: {', '.join(TONES)}")
    for k in ("note", "scene"):
        if k in d and not text_ok(d[k], 200):
            raise SystemExit(f"design.{k}은 200자 이하의 한 줄([ ] 없이)")


def options(engine, voice_opts, line_opts, text, where=""):
    """voice_opts 위에 문장 opts를 덮고 범위를 확인한다."""
    o = {k: v for k, v in {**voice_opts, **line_opts}.items() if k not in ("design", "ref")}
    bad = set(o) - {*RANGES, "style", "style_note", "seconds", "normalize"}
    if bad:
        raise SystemExit(f"{where} 모르는 음성 옵션: {', '.join(sorted(bad))}")
    for k, (lo, hi) in RANGES.items():
        if k in o and (isinstance(o[k], bool) or not isinstance(o[k], int if k in INT else (int, float)) or not lo <= o[k] <= hi):
            raise SystemExit(f"{where} {k}는 {lo}~{hi}{' 정수' if k in INT else ''}")
    if o.get("style") and o["style"] not in STYLES:
        raise SystemExit(f"{where} style은 {', '.join(STYLES)} 중 하나")
    if o.get("style_note") and (o.get("style") or not text_ok(o["style_note"], 120)):
        raise SystemExit(f"{where} style_note는 120자 이하 한 줄이고 style과 함께 쓰지 않는다")
    if "seconds" in o:
        n = len(plain(text))
        lo, hi = -(-n * 4 // 10) / 2, max(3, -(-n * 8 // 10) / 2)
        if engine != "drama-3":
            raise SystemExit(f"{where} seconds(목표 길이)는 drama-3만")
        if not lo <= o["seconds"] <= hi:
            raise SystemExit(f"{where} seconds는 이 문장에서 {lo}~{hi}초(더 짧으면 뒷말이 빠진다)")
    for close, tag in re.findall(r"<(/?)([a-z][a-z-]*)>", text):
        if tag not in SPANS[engine]:
            raise SystemExit(f"{where} <{close}{tag}>는 {engine}에서 쓸 수 없음. 감싸는 지시: {', '.join(SPANS[engine]) or '없음'}")
    for tag in re.findall(r"\[([^\[\]]+)\]", text):
        if tag not in POINTS[engine]:
            print(f"  {where} [{tag}]는 확인된 지시가 아님 — 소리 내어 읽을 수 있으니 들어 본다")
    return o


def edges(text):
    """앞뒤 무음을 0.06초만 남긴다(문장 사이 쉼은 timeline.py가 정한다). 대본에 적은 쉼이 있는 쪽은 그대로 둔다."""
    cut = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06"
    head = [] if re.match(r"\s*(\[[^\]]*\]\s*)*?\[(long )?pause\]", text) else [cut]
    tail = [] if re.search(r"\[(long |short )?pause\][\s.!?…]*$", text) else ["areverse", cut, "areverse"]
    return head + tail


def filters(o, rate):
    ratio = 2 ** (o.get("semitones", 0) / 12)
    tempo = round(o.get("speed", 1) / ratio, 4)
    f = ([f"asetrate={round(rate * ratio)}", f"aresample={rate}"] if o.get("semitones") else []) + ([f"atempo={tempo}"] if tempo != 1 else [])
    return f + (["loudnorm=I=-16:TP=-1.5:LRA=11", f"aresample={rate}"] if o.get("normalize") else [])


class Worker:
    """모델 하나를 올려 둔 채 문장을 차례로 만든다(표준입출력 JSON 줄, 네트워크 포트 없음)."""

    def __init__(self, h):
        self.h, self.p = h, subprocess.Popen([str(h / ".venv/bin/python"), "-I", str(Path(__file__).parent / "local_tts_worker.py")], cwd=h, text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                             stderr=subprocess.DEVNULL, env={k: os.environ[k] for k in ("PATH", "HOME", "TMPDIR") if k in os.environ} | {"HF_HUB_OFFLINE": "1"})

    def say(self, engine, text, out, o, ref=None, design=None):
        rid = str(uuid.uuid4())
        direction = o.get("style_note") or (STYLES[o["style"]][1] if o.get("style") else "")
        req = {"id": rid, "model": str(self.h / "models" / FOLDERS[engine]), "text": text, "output": str(out)}
        req |= {"refAudio": str(ref[0]), "refText": ref[1]} if ref else {}
        req |= {"design": {"description": describe(design)} | ({"scene": design["scene"]} if design.get("scene") else {})} if design else {}
        req |= {"direction": direction} if direction else {}
        req |= {k: o[k] for k in ("temperature", "top_p", "top_k", "seed", "seconds") if o.get(k) is not None}
        self.p.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
        self.p.stdin.flush()
        for line in self.p.stdout:
            e = json.loads(line)
            if e.get("id") != rid:
                continue
            if e["event"] == "error":
                raise SystemExit(f"로컬 음성 실패: {e.get('message')} — {text[:40]}")
            if e["event"] == "done":
                return e["seconds"], e["rate"]
        raise SystemExit("로컬 음성 모델이 멈췄습니다(메모리가 부족하거나 다른 프로그램이 GPU를 쓰는지 확인).")

    def close(self):
        self.p.stdin.close()
        try:
            self.p.wait(20)
        except subprocess.TimeoutExpired:
            self.p.kill()


def digest(*x):
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def open_worker(need):
    h = home()
    r = ready(h)
    miss = [m for m in need if not r[m]]
    if miss:
        raise SystemExit(f"로컬 모델이 없음: {', '.join(miss)} ({h})\n  이미 설치했으면 python3 install.py --local-tts <폴더>, 아니면 scripts/setup_local_tts.sh")
    return Worker(h)


def voice(W, d, w):
    """모든 문장이 참조할 목소리 (파일, 읽은 말, 지문)."""
    v = d.get("voice_opts", {})
    V = W / "assets" / "voice"
    if v.get("ref"):
        src = Path(v["ref"]["audio"]).expanduser()
        src = src if src.is_absolute() else W / src
        if not src.exists() or not v["ref"].get("text", "").strip():
            raise SystemExit("voice_opts.ref에는 audio(파일)와 text(그 소리가 실제로 읽은 말)가 모두 필요")
        if dur(src) > 60:
            raise SystemExit("참조 음성은 60초 이하")
        return src, v["ref"]["text"], digest(src.read_bytes().hex(), v["ref"]["text"])
    design = v.get("design") or DEFAULT_DESIGN
    check_design(design)
    key = digest(design, REF_TEXT)
    wav, stamp = V / "ref.wav", V / "ref.json"
    if not (wav.exists() and stamp.exists() and load(stamp)["key"] == key):
        V.mkdir(parents=True, exist_ok=True)
        t = time.time()
        sec, _ = w.say("drama-3", REF_TEXT, wav, {"seed": design.get("seed", 7)}, design=design)
        save(stamp, {"key": key, "design": design, "text": REF_TEXT})
        print(f"목소리 만듦: {describe(design)} ({sec:.1f}초, {time.time() - t:.0f}초 걸림) → assets/voice/ref.wav", flush=True)
    return wav, REF_TEXT, key


def make(W, d, engine, only=None):
    v = d.get("voice_opts", {})
    opts = {ln["id"]: options(engine, v, ln.get("opts", {}), ln["tts"], ln["id"]) for ln in d["lines"]}  # 모두 확인한 뒤 시작
    out = W / "assets" / "vo_raw"
    out.mkdir(parents=True, exist_ok=True)
    print(LICENSE[engine])
    w = open_worker({engine} | (set() if v.get("ref") else {"drama-3"}))
    made = spent = 0.0
    try:
        ref = voice(W, d, w)
        for ln in d["lines"]:
            if only and ln["id"] not in only:
                continue
            p, stamp, o = out / f"{ln['id']}.mp3", out / f"{ln['id']}.txt", opts[ln["id"]]
            want = f"{engine}\n{ref[2]}\n{json.dumps(o, sort_keys=True, ensure_ascii=False)}\n{ln['tts']}"
            if p.exists() and stamp.exists() and stamp.read_text() == want and not only:
                print(f"{ln['id']} 그대로")
                continue
            wav, t = out / f"{ln['id']}.wav", time.time()
            sec, rate = w.say(engine, ln["tts"], wav, {"seed": 1, **o}, ref=ref[:2])
            f = edges(ln["tts"]) + filters(o, rate)
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", ",".join(f) or "anull", "-c:a", "libmp3lame", "-b:a", "192k", p])
            wav.unlink()
            stamp.write_text(want)
            took, n = time.time() - t, len(re.findall(r"[가-힣]", plain(ln["tts"])))
            made, spent = made + sec, spent + took
            rate_syl = n / sec
            print(f"{ln['id']} {dur(p):5.2f}초 ({took:.0f}초 걸림)" + ("" if 3.5 <= rate_syl <= 9 else f"  ← 초당 {rate_syl:.1f}음절: 말이 빠지거나 늘어졌는지 들어 보기"), flush=True)
    finally:
        w.close()
    if made:
        print(f"새로 만든 음성 {made:.1f}초, 걸린 시간 {spent:.0f}초(1초당 {spent / made:.2f}초)")


def audition(W, d, n):
    """같은 설계로 시드만 바꾼 목소리 n개 → previews/voice-<시드>.wav. 고른 시드를 voice_opts.design.seed에 적는다."""
    design = d.get("voice_opts", {}).get("design") or DEFAULT_DESIGN
    check_design(design)
    out = W / "previews"
    out.mkdir(exist_ok=True)
    w = open_worker({"drama-3"})
    try:
        for s in range(1, n + 1):
            sec, _ = w.say("drama-3", REF_TEXT, out / f"voice-{s}.wav", {"seed": s}, design=design)
            print(f"previews/voice-{s}.wav {sec:.1f}초", flush=True)
    finally:
        w.close()


def show():
    h = home()
    print(f"설치 폴더 {h}: " + ", ".join(f"{m} {'됨' if ok else '없음'}" for m, ok in ready(h).items()))
    tab = lambda t: ", ".join(f"{k}({v[0] if isinstance(v, tuple) else v})" for k, v in t.items())
    print("design(새 목소리) gender:", tab(GENDERS), "\n  age:", tab(AGES), "\n  pitch:", tab(PITCHES), "\n  tones(최대 3):", tab(TONES), "\n  energy:", tab(ENERGIES), "\n  note·scene: 200자 이하 설명, seed: 목소리 고르기")
    print("style(말투):", tab(STYLES), "또는 style_note(직접 쓴 120자)")
    print("seconds(목표 길이, drama-3만) ·", " · ".join(f"{k} {a}~{b}" for k, (a, b) in RANGES.items()), "· normalize true")
    for m in FOLDERS:
        print(f"{m} 대사 안 지시 [ ]: {', '.join(POINTS[m])}\n  감싸는 지시 < >: {', '.join(SPANS[m]) or '없음'}")
        print("  " + LICENSE[m])
