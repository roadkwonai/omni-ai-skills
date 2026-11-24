"""timeline.json → index.html. 장면 파일이 없는 파트는 틀(compositions/<part>.html)을 만들어 준다(있는 장면은 건드리지 않음).

python3 make_index.py <작업 폴더>. index.html은 매번 새로 쓰므로 손으로 고치지 않는다.
장면 위에 겹칠 것(파트를 걸치는 클립)은 overlay.html에 쓰면 자막 아래에 그대로 들어간다."""
import html
from pathlib import Path

from lib import load, work

A = Path(__file__).resolve().parents[1] / "assets"


def main():
    W = work()
    d, tl = load(W / "script.json"), load(W / "timeline.json")
    total, body = tl["duration"], []
    for part, p in tl["parts"].items():
        cid, length = part.lower(), round(p["scene_end"] - p["scene_start"], 2)
        f = W / "compositions" / f"{cid}.html"
        if not f.exists():
            t = (A / "scene.html").read_text()
            for k, v in {"%ID%": cid, "%PART%": part, "%NAME%": html.escape(d["parts"][part]), "%DUR%": str(length), "%ACCENT%": d["accent"]}.items():
                t = t.replace(k, v)
            f.write_text(t)
            print(f"틀 만듦: compositions/{cid}.html ({length}초)")
        body.append(f'      <div id="{cid}" data-composition-id="{cid}" data-composition-src="compositions/{cid}.html" data-start="{p["scene_start"]}" '
                    f'data-duration="{length}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080"></div>')
    if (W / "overlay.html").exists():
        body.append((W / "overlay.html").read_text())
    if (W / "compositions" / "captions.html").exists():
        body.append(f'      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{total}" '
                    'data-track-index="3" data-track-kind="captions" data-width="1920" data-height="1080" style="z-index: 10"></div>')
    for r in tl["lines"]:
        body.append(f'      <audio id="vo-{r["id"]}" src="assets/vo/{r["id"]}.mp3" data-start="{r["start"]}" data-duration="{r["audio"]}" data-track-index="5" data-track-kind="audio"></audio>')
    (W / "index.html").write_text(f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>{html.escape(d["title"])}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: #131209; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="1920" data-height="1080">
{chr(10).join(body)}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
""")
    print(f"index.html: 장면 {len(tl['parts'])}개, 음성 {len(tl['lines'])}개, {total}초")


if __name__ == "__main__":
    main()
