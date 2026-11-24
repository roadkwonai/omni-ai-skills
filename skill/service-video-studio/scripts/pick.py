"""레시피·배경음·효과음을 고른다. 자동으로 고른 것은 다시 돌리면 다시 고르고, 사용자가 정한 것은 절대 바꾸지 않는다.

python3 pick.py <작업 폴더>                       자동 선택 → script.json, RECIPES.md
python3 pick.py <작업 폴더> --set S04=CrashZoom P9=Lockup --bgm house-vibez --kit soft --mood bright   사용자 지정(고정)
python3 pick.py <작업 폴더> --auto S04 bgm kit     지정을 풀고 자동으로 되돌림
python3 pick.py <작업 폴더> --list [낱말]          고를 수 있는 것 보기

문장마다 script.json의 kind(말하는 내용의 종류)를 보고 고른다. mood(calm·heavy·bright·fast)는 배경음·효과음과 후보 순서를 정한다."""
import difflib
import shutil
import sys
from pathlib import Path

from lib import SKILL, audio, dur, load, save, work

# 종류 → 후보(앞일수록 우선). hf:는 HyperFrames 장면(assets/examples), record는 실제 녹화, 나머지는 값만 넣는 Remotion 샷
KINDS = {
    "hook": ["hf:title", "TextMask"], "identity": ["TextMask", "hf:title"], "stat": ["hf:count"], "compare": ["hf:table", "BeforeAfter"],
    "before_after": ["BeforeAfter", "hf:count"], "structure": ["hf:flow"], "overview": ["TiltGlide", "SpotTour"], "cells": ["SpotTour", "TiltGlide"],
    "focus": ["CrashZoom", "SpotTour"], "action": ["record"], "switch": ["CardFlip", "record"], "inputs": ["hf:converge"], "steps": ["hf:gates"],
    "conditions": ["hf:switches"], "log": ["hf:cards", "record"], "schedule": ["hf:timeline"], "result": ["hf:count", "CrashZoom"],
    "disclaimer": ["hf:title"], "outro": ["Lockup", "hf:outro"],
}
WHAT = {
    "hf:title": "큰 글자 등장·밑줄", "hf:count": "숫자 굴림·막대", "hf:table": "줄마다 열리는 비교표", "hf:flow": "선이 따라가는 흐름도", "hf:converge": "입력이 모여 결과가 됨",
    "hf:gates": "여러 관문에서 막히는 단면도", "hf:switches": "모두 켜져야 불이 들어오는 스위치", "hf:cards": "기록 카드가 쌓임", "hf:timeline": "하루 시간 막대", "hf:outro": "요소가 빠지고 이름으로 모임",
    "record": "실제 녹화", "SpotTour": "말하는 칸을 차례로 비춤", "TextMask": "큰 글자 구멍으로 화면이 흐르다 뛰어듦", "CrashZoom": "한 칸으로 확 다가가 쾅 멈춤",
    "TiltGlide": "기울어진 화면 위를 미끄러지며 훑음", "BeforeAfter": "손잡이를 끌어 앞뒤 화면 비교", "CardFlip": "화면이 카드처럼 뒤집혀 다음 화면", "Lockup": "화면이 점으로 줄며 로고·이름",
}
MOODS = {"calm": "차분함", "heavy": "묵직함", "bright": "경쾌함", "fast": "빠름"}
FLASHY = {"TextMask", "CrashZoom", "BeforeAfter", "CardFlip", "TiltGlide"}  # 빠른 분위기에서 앞으로, 차분하면 한 편에 하나씩만
CATALOG = {c["name"]: c for c in load(SKILL / "assets" / "shots-catalog.json")}


def check_shot(name):
    if name not in WHAT and name not in CATALOG:
        low = {n.lower(): n for n in [*WHAT, *CATALOG]}
        near = [low[n] for n in difflib.get_close_matches(name.lower(), low, 4, 0.5)] + [n for n in low.values() if name.lower() in n.lower()]
        raise SystemExit(f"모르는 레시피: {name}" + (f" — 비슷한 것: {', '.join(dict.fromkeys(near[:6]))}" if near else " (--list로 확인)"))


def choose(lines, mood):
    """kind → 레시피. 사용자 지정은 그대로 두고, 앞 문장과 같은 레시피와 이미 쓴 강한 샷은 뒤로 미룬다."""
    used, prev = {}, None
    for ln in lines:
        s = ln.get("shot") or {}
        if s.get("by") != "user":
            kind = ln.get("kind")
            if kind not in KINDS:
                raise SystemExit(f"{ln['id']}: kind가 없거나 모름({kind}). 고를 것: {', '.join(KINDS)}")
            cands = KINDS[kind]

            def cost(c):
                flashy = c in FLASHY
                return (cands.index(c) - (0.6 if flashy and mood in ("bright", "fast") else 0)
                        + (1.5 if c == prev and c != "record" else 0) + (1.2 * used.get(c, 0) if flashy and mood in ("calm", "heavy") else 0.4 * used.get(c, 0) if flashy else 0))
            name = min(cands, key=cost)
            why = f"{kind}" + ("" if name == cands[0] else f" · {cands[0]} 대신({'같은 샷 반복을 피함' if cands[0] == prev or used.get(cands[0]) else MOODS[mood] + ' 분위기'})")
            ln["shot"] = {"name": name, "by": "auto", "why": why}
        prev = ln["shot"]["name"]
        used[prev] = used.get(prev, 0) + 1


def pick_sound(d, sound):
    mood = d["mood"]
    if (d.get("bgm") or {}).get("by") != "user":
        name = next(n for n, b in sound["bgm"].items() if b["mood"] == mood)
        d["bgm"] = {"name": name, "by": "auto", "why": f"{MOODS[mood]} — {sound['bgm'][name]['note']}"}
    if (d.get("kit") or {}).get("by") != "user":
        name = next(n for n, k in sound["kit"].items() if mood in k["mood"])
        d["kit"] = {"name": name, "by": "auto", "why": sound["kit"][name]["note"]}


def put_bgm(W, name):
    dst = W / "assets" / "bgm.mp3"
    if name == "none":
        dst.unlink(missing_ok=True)
        return
    ours = name in load(SKILL / "assets" / "sound.json")["bgm"]
    src = audio(f"bgm/{name}") if ours else (Path(name) if Path(name).is_absolute() else W / name)
    if not src.exists():
        raise SystemExit(f"배경음 없음: {name} — 있는 곡 이름, 파일 경로, none 중 하나")
    dur(src)  # 소리 파일인지
    shutil.copy2(src, dst)


def show(word):
    sound = load(SKILL / "assets" / "sound.json")
    print("바로 쓰는 레시피")
    for n, w in WHAT.items():
        print(f"  {n}: {w}")
    print("배경음(이름 · 파일 경로 · none)")
    for n, b in sound["bgm"].items():
        print(f"  {n}: {b['title']} · {b['style']} · {b['note']}")
    print("효과음 세트")
    for n, k in sound["kit"].items():
        print(f"  {n}: {k['note']}")
    hit = [c for c in CATALOG.values() if not word or word.lower() in (c["name"] + c["category"] + c["what"] + c["use"]).lower()]
    print(f"video-shotcraft 샷 {len(hit)}개(add_shot.py로 가져와 쓴다. 설명은 원문 중국어 — 사용자에게는 한국어로 옮겨 보여 준다)")
    for c in hit if word else []:
        print(f"  {c['name']} [{c['category']}] {c['what']} | {c['length'][:24]} | {c['use']}")
    if not word:
        for cat in dict.fromkeys(c["category"] for c in hit):
            print(f"  {cat}: " + ", ".join(c["name"] for c in hit if c["category"] == cat))


def table(d):
    md = [f"# 고른 레시피와 소리 · {d['title']}", "", f"분위기 **{MOODS[d['mood']]}** · 배경음 **{d['bgm']['name']}**({'사용자 지정' if d['bgm']['by'] == 'user' else d['bgm']['why']}) · 효과음 **{d['kit']['name']}**({'사용자 지정' if d['kit']['by'] == 'user' else d['kit']['why']})", "",
          "| 문장 | 대본 | 레시피 | 무엇 | 정한 쪽 | 이유 |", "| --- | --- | --- | --- | --- | --- |"]
    for ln in d["lines"]:
        s = ln["shot"]
        what = WHAT.get(s["name"]) or f"shotcraft {CATALOG[s['name']]['category']} (가져와야 함)"
        md.append(f"| {ln['id']} | {ln['cap']} | {s['name']} | {what} | {'사용자' if s['by'] == 'user' else '자동'} | {s.get('why', '')} |")
    return "\n".join(md) + "\n"


def args(flag):
    """--flag 뒤의 값들(다음 --까지)."""
    if flag not in sys.argv:
        return []
    rest = sys.argv[sys.argv.index(flag) + 1:]
    return rest[:next((i for i, a in enumerate(rest) if a.startswith("--")), len(rest))]


def main():
    W = work()
    if "--list" in sys.argv:
        return show(" ".join(args("--list")))
    d, sound = load(W / "script.json"), load(SKILL / "assets" / "sound.json")
    ids = {ln["id"]: ln for ln in d["lines"]}
    if args("--mood"):
        d["mood"] = args("--mood")[0]
    d.setdefault("mood", "calm")
    if d["mood"] not in MOODS:
        raise SystemExit(f"분위기는 {', '.join(MOODS)} 중 하나")
    for a in args("--auto"):
        if a in ("bgm", "kit"):
            d.pop(a, None)
        elif a in ids:
            ids[a].pop("shot", None)
        else:
            raise SystemExit(f"모르는 대상: {a}")
    for pair in args("--set"):
        target, _, name = pair.partition("=")
        check_shot(name)
        hit = [ids[target]] if target in ids else [ln for ln in d["lines"] if ln["part"] == target]
        if not hit:
            raise SystemExit(f"모르는 문장·파트: {target}")
        for ln in hit:
            ln["shot"] = {"name": name, "by": "user", "why": "사용자 지정"}
    if args("--bgm"):
        d["bgm"] = {"name": args("--bgm")[0], "by": "user"}
    if args("--kit"):
        if args("--kit")[0] not in sound["kit"]:
            raise SystemExit(f"효과음 세트는 {', '.join(sound['kit'])} 중 하나")
        d["kit"] = {"name": args("--kit")[0], "by": "user"}
    choose(d["lines"], d["mood"])
    pick_sound(d, sound)
    put_bgm(W, d["bgm"]["name"])
    save(W / "script.json", d)
    (W / "RECIPES.md").write_text(table(d))
    print(table(d))
    port = sorted({ln["shot"]["name"] for ln in d["lines"]} - set(WHAT))
    if port:
        print("가져와야 하는 샷:", " ".join(port), "→ python3 add_shot.py <작업 폴더>", " ".join(port))


if __name__ == "__main__":
    main()
