"""video-shotcraft 원본 샷을 remotion/으로 가져온다: python3 add_shot.py <작업 폴더> <샷 이름> [...]

remotion/src/shots/<이름>/에 코드(+공용 부품·그림), 카드 설명은 CARD.md. 컴포지션 이름과 길이를 출력한다.
가져온 그대로는 원본의 글꼴·색·문구·가짜 화면이 나온다. SPEC에 맞게 고친 뒤 still로 확인하고 렌더한다(references/motion.md).
원본은 ~/.cache/video-showcase/에 확인한 커밋으로 한 번만 받는다. shotcraft 코드는 Apache-2.0(LICENSE-video-shotcraft)."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from lib import SKILL, load, work

PIN = "075b548c2405a07b77129eb448b0b504fc60dea3"
REPO = os.environ.get("SHOTCRAFT", "https://github.com/Vincentwei1021/video-shotcraft.git")
CACHE = Path.home() / ".cache" / "video-showcase" / "video-shotcraft"


def source():
    if not (CACHE / "demos" / "_fixtures").exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        for c in (["init", "--quiet"], ["fetch", "--quiet", "--depth", "1", REPO, PIN], ["checkout", "--quiet", "FETCH_HEAD"]):
            subprocess.run(["git", "-C", str(CACHE), *c], check=True)
    return CACHE


def main():
    W, names = work(), sys.argv[2:]
    cat = {c["name"]: c for c in load(SKILL / "assets" / "shots-catalog.json")}
    bad = [n for n in names if n not in cat or not cat[n]["demos"]]
    if bad or not names:
        raise SystemExit(f"가져올 수 없는 샷: {' '.join(bad) or '(이름 없음)'} — pick.py --list로 확인")
    src, R = source(), W / "remotion"
    shots = R / "src" / "shots"
    shutil.copytree(src / "demos" / "_fixtures", shots / "_fixtures", dirs_exist_ok=True)
    (shots / "_textures").mkdir(exist_ok=True)
    reg = R / "ported.json"
    done = load(reg) if reg.exists() else []
    for n in names:
        dst = shots / cat[n]["category"] / n
        if dst.exists():
            print(f"{n}: 이미 있음(고친 내용을 지키려고 그대로 둠)")
            continue
        shutil.copytree(src / "demos" / cat[n]["category"] / n, dst)
        shutil.copy2(src / "references" / "shots" / cat[n]["category"] / f"{n}.md", dst / "CARD.md")
        # 같은 폴더 밖의 부품(다른 데모·assets)을 부르는 샷은 그 파일도 가져온다
        for f in list(dst.rglob("*.tsx")):
            code = f.read_text()
            for rel in re.findall(r"from '(\.\.?/[^']+)'", code):
                want = (f.parent / rel).resolve()
                if any(want.with_suffix(e).exists() for e in (".tsx", ".ts")) or want.exists():
                    continue
                orig = (src / "demos" / cat[n]["category"] / n / rel).resolve()
                for cand in (orig, orig.with_suffix(".tsx"), orig.with_suffix(".ts")):
                    if cand.is_file():
                        to = want if cand == orig else want.with_suffix(cand.suffix)
                        if R / "src" in to.parents:
                            to.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(cand, to)
                        break
            if "textures/live" in code:  # 카드 번호를 코드로 조합해 부르는 샷이 있어 통째로 가져온다(고칠 때 우리 화면으로 바꾼다)
                shutil.copytree(src / "demos" / "_textures", R / "public" / "textures" / "live", dirs_exist_ok=True)
            for tex in re.findall(r"staticFile\(\s*['\"`]([^'\"`$]+)", code):
                for base in (src / "demos" / "_textures" / Path(tex).name, src / "template" / "public" / tex):
                    if base.is_file():
                        to = R / "public" / tex
                        to.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(base, to)
                        break
            for comp in re.findall(r"export const (\w+): React\.FC\b(?!<)", code):
                key = comp[0].upper() + comp[1:]
                snake = re.sub(r"(?<!^)(?=[A-Z])", "_", comp).upper()
                durs = dict(re.findall(r"export const (\w*DUR\w*)\s*=\s*(\d+)", code))
                frames = int(durs.get(f"{snake}_DURATION") or next(iter(durs.values()), 150))
                done.append({"id": key, "comp": comp, "file": str(f.relative_to(R / "src").with_suffix("")), "frames": frames, "shot": n})
                print(f"{n}: 컴포지션 {key} {frames}프레임 — {f.relative_to(W)}")
    extra = sorted({m for f in shots.rglob("*.tsx") for m in re.findall(r"from '(@remotion/[\w-]+)'", f.read_text())})
    pkg = load(R / "package.json")
    missing = [m for m in extra if m not in pkg["dependencies"]]
    if missing:
        pkg["dependencies"] |= {m: pkg["dependencies"]["remotion"] for m in missing}
        (R / "package.json").write_text(json.dumps(pkg, indent=2) + "\n")
        print("새로 필요한 패키지:", " ".join(missing), "→ npm install")
    reg.write_text(json.dumps(done, ensure_ascii=False, indent=1))
    imp = "".join(f"import {{ {x['comp']} }} from './{x['file']}';\n" for x in done)
    (R / "src" / "ported.tsx").write_text("// add_shot.py가 다시 쓴다\nimport React from 'react';\n" + imp +
        "export const PORTED: [string, React.FC, number][] = [" + ", ".join(f"['{x['id']}', {x['comp']}, {x['frames']}]" for x in done) + "];\n")


if __name__ == "__main__":
    main()
