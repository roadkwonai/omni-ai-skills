"""도구 자체 점검(네트워크·영상 없이): python3 selftest.py"""
import reading
from captions import groups
from lib import SKILL, load
from mix_audio import events
from pick import KINDS, WHAT, choose, pick_sound
from review_script import review
from timeline import layout
from words import align

reading._selftest()
D = {"speed": 1.1, "gap": 1.0, "part_gap": 1.5, "lead": 0.6, "tail": 2.5, "pace": 6.0, "target_sec": [5, 60], "parts": {"P0": "훅", "P1": "본"},
     "banned": ["무조건"], "sfx": [["P1", 0.5, "pop"]],
     "lines": [{"id": "S01", "part": "P0", "cap": "AI가 1분마다 봅니다.", "fact": "-"}, {"id": "S02", "part": "P0", "cap": "둘째 문장입니다.", "fact": "-"},
               {"id": "S03", "part": "P1", "cap": "무조건 됩니다.", "fact": ""}]}
_, issues, _ = review(D)
assert D["lines"][0]["tts"] == "에이아이가 일분마다 봅니다."
assert [i for i, _ in issues] == ["S03"] and len(issues[0][1]) == 2, issues
tl = layout(D, {"S01": 2.0, "S02": 1.0, "S03": 1.0})
assert [r["start"] for r in tl["lines"]] == [0.6, 3.6, 6.1] and tl["duration"] == 9.6
assert tl["parts"]["P0"]["scene_end"] == tl["parts"]["P1"]["scene_start"] == 5.35
assert events(D, tl) == [("whoosh", 5.1499999999999995), ("pop", 5.85)]
ws = align({"id": "S01", "cap": "AI가 1분마다", "tts": "에이아이가 일분마다"}, [{"text": "AI가", "start": 0, "end": 0.6}, {"text": "1분마다", "start": 0.7, "end": 1.4}], 10)
assert [w["text"] for w in ws] == ["AI가", "1분마다"] and ws[0]["start"] == 10 and 11.3 < ws[1]["end"] <= 11.4, ws
ws = align({"id": "S", "cap": "노쇼율이 6.4%로 줄었습니다.", "tts": "노쇼율이 육점사퍼센트로 줄었습니다."},
           [{"text": "노쇼율이", "start": 0, "end": 0.6}, {"text": "6.4%로", "start": 0.6, "end": 1.8}, {"text": "줄었습니다.", "start": 1.8, "end": 2.4}], 0)
assert [w["start"] for w in ws] == [0, 0.6, 1.8], ws  # 숫자 뒤 단어가 밀리지 않는다
w = [{"text": t, "start": i * 0.3, "end": i * 0.3 + 0.25} for i, t in enumerate("하나 둘 셋 넷 다섯 여섯 일곱.".split())]
assert [len(g) for g in groups(w)] == [5, 2], groups(w)  # 한 어절만 남는 줄을 만들지 않는다

# 자동 선택: 같은 샷을 이어 쓰지 않고, 사용자 지정은 지킨다
assert {c for v in KINDS.values() for c in v} <= set(WHAT)
L = [{"id": f"S{i}", "part": "P", "kind": k} for i, k in enumerate(["hook", "cells", "cells", "focus", "outro"])]
choose(L, "calm")
assert [x["shot"]["name"] for x in L] == ["hf:title", "SpotTour", "TiltGlide", "CrashZoom", "Lockup"], L
L[3]["shot"] = {"name": "BeforeAfter", "by": "user"}
choose(L, "fast")
assert L[3]["shot"]["name"] == "BeforeAfter" and L[0]["shot"]["by"] == "auto"
snd, d = load(SKILL / "assets" / "sound.json"), {"mood": "bright", "bgm": {"name": "cat-walk", "by": "user"}}
pick_sound(d, snd)
assert d["bgm"]["name"] == "cat-walk" and d["kit"]["name"] == "soft"
assert {f"bgm/{n}" for n in snd["bgm"]} | {f"sfx/{f}" for k in snd["kit"].values() for f in k["files"].values()} <= set(snd["files"])
import tts_local as T
from reading import plain

assert plain("[sighs] 그래. <whisper>아무에게도</whisper> 말하지 마. [pause]") == "그래. 아무에게도 말하지 마."
assert T.describe({"gender": "female", "age": "young", "tones": ["husky"]}) == "young woman in her twenties, husky, breathy"
assert T.options("drama-3", {"style": "narration", "speed": 1.1}, {"speed": 1.2}, "한 문장")["speed"] == 1.2
for engine, o, text in (("drama-3", {"speed": 2}, "말"), ("s2-pro", {"seconds": 5}, "말"), ("s2-pro", {}, "<slow>말</slow>"), ("drama-3", {"top_k": 1.5}, "말"), ("drama-3", {"x": 1}, "말")):
    try:
        T.options(engine, {}, o, text)
        raise AssertionError((engine, o))
    except SystemExit:
        pass
assert T.filters({"speed": 1.25}, 44100) == ["atempo=1.25"] and T.filters({"semitones": 12}, 44100) == ["asetrate=88200", "aresample=44100", "atempo=0.5"]
assert len(T.edges("말")) == 4 and len(T.edges("말 [pause]")) == 1
print("selftest ok")
