"""words.json → compositions/captions.html (노래방식 자막): python3 captions.py <작업 폴더>

아래 가운데 한 줄, Pretendard 800 46px, 최대 6어절. 지금 말하는 단어에 강조색 상자가 미끄러지듯 옮겨 간다(0.1초).
어두운 장면은 theme "dark", 밝은 녹화 화면은 "light"(글자 크기만큼 밝은 판을 깔아 표·차트 위에서도 읽힌다).
"""
import html
import json

from lib import load, work

MAX_WORDS = 6
GROUP_TAIL = 0.35      # 마지막 단어 뒤 잠깐 머무름


def groups(words):
    """한 줄 묶음: 문장 끝은 항상, 쉼표는 3어절 이상일 때, 말 쉼은 0.35초 이상일 때 끊는다. 문장 끝 한 어절은 앞 줄에 붙인다."""
    gs, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        gap = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 9
        end = w["text"].endswith((".", "?", "!"))
        if len(cur) >= MAX_WORDS or end or (w["text"].endswith(",") and len(cur) >= 3) or (gap >= 0.35 and len(cur) >= 2):
            if end and len(cur) == 1 and gs and len(gs[-1]) < MAX_WORDS and not words[gs[-1][-1]]["text"].endswith((".", "?", "!")):
                gs[-1] += cur
            else:
                gs.append(cur)
            cur = []
    if cur:
        gs.append(cur)
    # 6어절 제한에 밀려 한 어절만 남은 줄: 같은 문장의 앞 줄(4어절 이상)에서 마지막 어절을 넘겨받는다
    for k in range(1, len(gs)):
        prev = gs[k - 1]
        if len(gs[k]) == 1 and len(prev) >= 4 and not words[prev[-1]]["text"].endswith((".", "?", "!")):
            gs[k].insert(0, prev.pop())
    return gs


def theme_at(themes, t):
    cur = "light"
    for s, name in themes:
        if t >= s:
            cur = name
    return cur


def build(W):
    spec = load(W / "words.json")
    words, themes, total = spec["words"], spec["theme"], float(spec["duration"])
    gs = groups(words)
    rows, timing = [], []
    for gi, g in enumerate(gs):
        start = max(0.1, words[g[0]]["start"] - 0.1)
        nxt = words[gs[gi + 1][0]]["start"] - 0.1 if gi + 1 < len(gs) else total
        end = min(words[g[-1]]["end"] + GROUP_TAIL, nxt)
        theme = theme_at(themes, start)
        spans = "".join(f'<span class="w" id="w{i}">{html.escape(words[i]["text"])}</span> ' for i in g).strip()
        hi = "".join(f'<span id="h{i}">{html.escape(words[i]["text"])}</span> ' for i in g).strip()
        rows.append(
            f'    <div id="g{gi}" class="grp clip {theme}" data-start="{start:.2f}" data-duration="{end - start:.2f}">\n'
            f'      <div class="line"><span class="base">{spans}</span>'
            f'<span class="hi" id="hi{gi}" aria-hidden="true" data-layout-allow-occlusion data-layout-allow-overlap><span class="bar"></span><span class="txt">{hi}</span></span></div>\n'
            f'    </div>')
        timing.append({"g": gi, "start": round(start, 3), "end": round(end, 3),
                       "words": [{"i": i, "start": words[i]["start"], "end": words[i]["end"]} for i in g]})
    out = TEMPLATE.replace("%ROWS%", "\n".join(rows)).replace("%TIMING%", json.dumps(timing, ensure_ascii=False)).replace("%ACCENT%", spec["accent"])
    (W / "compositions" / "captions.html").write_text(out)
    print(f"\n자막 {len(words)}어절 {len(gs)}줄, 마지막 {words[-1]['end']:.2f}초")


TEMPLATE = """<template>
  <style>
    @font-face { font-family: "Pretendard"; src: url("assets/fonts/PretendardVariable.woff2") format("woff2"); font-weight: 100 900; }
    #root { position: absolute; inset: 0; pointer-events: none; }
    .grp { position: absolute; left: 0; right: 0; bottom: 80px; height: 64px; display: flex; justify-content: center; overflow: visible; }
    .line { position: relative; font-family: "Pretendard", sans-serif; font-size: 46px; font-weight: 800; letter-spacing: -0.02em; line-height: 64px; white-space: nowrap; }
    .base .w { color: var(--todo); }
    .hi { position: absolute; inset: 0; clip-path: inset(0 100% 0 0 round 9px); }
    .hi .bar { position: absolute; left: -10px; right: -10px; top: 3px; bottom: 3px; background: %ACCENT%; }
    .hi .txt { position: relative; color: #ffffff; }
    .light { --done: #111111; --todo: #44413e; }
    /* 밝은 녹화 화면 위: 글자 크기에 맞춘 판(밝은 판)을 깔아 표·차트와 겹쳐도 읽히게 */
    .light .line { background: rgba(247, 247, 244, 0.94); border-radius: 14px; padding: 0 22px; box-shadow: 0 6px 24px rgba(0, 0, 0, 0.18); }
    .light .hi { padding: 0 22px; }
    .dark { --done: #f3f4f5; --todo: #a9acb3; }
    /* 어두운 조명의 화면(SpotTour) 위: 바탕색 판이라 카드 장면에서는 보이지 않고 화면 글자와 겹칠 때만 자막을 지킨다 */
    .dark .line { background: rgba(19, 18, 9, 0.78); border-radius: 14px; padding: 0 22px; }
    .dark .hi { padding: 0 22px; }
  </style>
  <div id="root" data-composition-id="captions" data-width="1920" data-height="1080">
%ROWS%
  </div>
  <script>
    window.__timelines = window.__timelines || {};
    const T = %TIMING%;
    const tl = gsap.timeline({ paused: true });
    const PAD = 10; // 상자 좌우 여백(px)
    // 단어 상자 위치는 글꼴이 그려진 뒤(첫 seek)에 잰다: 함수 값은 트윈이 처음 그려질 때 계산된다
    const clipFor = (i) => () => {
      const w = document.getElementById("w" + i), line = w.parentElement.parentElement;
      const L = w.offsetLeft - PAD, R = line.offsetWidth - (w.offsetLeft + w.offsetWidth) - PAD;
      return `inset(0 ${R}px 0 ${L}px round 9px)`;
    };
    T.forEach((g) => {
      const grp = "#g" + g.g, hi = "#hi" + g.g;
      tl.fromTo(grp, { opacity: 0 }, { opacity: 1, duration: 0.15, ease: "power2.out" }, g.start);
      g.words.forEach((w, k) => {
        const slide = k === 0 ? 0.01 : Math.min(0.1, w.start - g.words[k - 1].start);
        tl.to(hi, { clipPath: clipFor(w.i), duration: slide, ease: "power2.out" }, w.start);
        tl.set("#w" + w.i, { color: "var(--done)" }, w.start);
      });
      tl.to(grp, { opacity: 0, duration: 0.12, ease: "power2.in" }, g.end - 0.12);
    });
    window.__timelines["captions"] = tl;
  </script>
</template>
"""

if __name__ == "__main__":
    build(work())
