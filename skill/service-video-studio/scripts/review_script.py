"""대본 검수: python3 review_script.py <작업 폴더>  → SCRIPT.md, script.json의 빈 tts 채움. 문제가 있으면 종료 코드 1.

① 자막(cap)과 읽기(tts)의 어절 수가 같은가(음성 단어 시간을 자막 단어에 순서로 붙이기 위해)
② 읽기에 숫자·영문·기호가 남지 않았는가  ③ 금지 표현  ④ 문장마다 근거(fact)가 있는가
⑤ 한 문장이 14초를 넘지 않는가  ⑥ 전체 예상 길이가 목표(target_sec) 안인가  ⑦ id 중복·파트 이름 누락"""
import re
import sys

from lib import load, save, work
from reading import plain, to_reading


def syl(text: str) -> int:
    return len(re.findall(r"[가-힣]", text)) + (len(re.findall(r"[A-Za-z0-9]", text)) + 1) // 2


def review(d):
    """(줄, 문제 목록, 예상 길이). d의 빈 tts를 채운다."""
    issues, rows, total, prev, seen = [], [], d["lead"] + d["tail"], None, set()
    for ln in d["lines"]:
        flags = []
        if not ln.get("tts"):
            try:
                ln["tts"] = to_reading(ln["cap"], d.get("reading", {}))
            except ValueError as e:
                flags.append(str(e))
        tts = plain(ln.get("tts", ""))  # 연기 지시는 세지 않는다
        est = (syl(tts) / d["pace"] + 0.25 * tts.count(",") + 0.35 * max(0, tts.count(".") - 1)) / d["speed"]
        if prev is not None:
            total += d["part_gap"] if ln["part"] != prev else d["gap"]
        total += est
        prev = ln["part"]
        if tts and len(ln["cap"].split()) != len(tts.split()):
            flags.append(f"어절 수 다름: 자막 {len(ln['cap'].split())} / 읽기 {len(tts.split())}")
        left = re.findall(r"[A-Za-z0-9%$₩℃]+", tts)
        if left:
            flags.append("읽기에 숫자·영문 남음: " + ", ".join(left))
        bad = [b for b in d.get("banned", []) if b in ln["cap"]]
        if bad:
            flags.append("금지 표현: " + ", ".join(bad))
        if not ln.get("fact", "").strip():
            flags.append("근거(fact) 없음")
        if est > 14:
            flags.append(f"너무 긴 문장 {est:.1f}초 → 나누기")
        if ln["id"] in seen:
            flags.append("id 중복")
        seen.add(ln["id"])
        if ln["part"] not in d["parts"]:
            flags.append(f"파트 이름 없음: {ln['part']}")
        if flags:
            issues.append((ln["id"], flags))
        rows.append(f"| {ln['id']} | {ln['part']} | {ln.get('screen', '')} | {ln['cap']} | 약 {est:.1f}초 | {ln.get('fact', '')} |")
    lo, hi = d["target_sec"]
    if not lo <= total <= hi:
        issues.append(("전체", [f"예상 길이 {total:.0f}초가 목표 {lo}~{hi}초 밖"]))
    return rows, issues, total


def main():
    W = work()
    d = load(W / "script.json")
    rows, issues, total = review(d)
    save(W / "script.json", d)
    md = [f"# 대본 · {d['title']}", "", f"예상 길이 약 {total:.0f}초 (말 속도 {d['pace']}음절/초 × {d['speed']}배속, 쉼 {d['gap']}초 / 파트 사이 {d['part_gap']}초)", "",
          "| # | 파트 | 화면 | 대본(자막) | 길이 | 근거 |", "| --- | --- | --- | --- | --- | --- |", *rows, "", "## 읽기가 다른 문장", ""]
    md += [f"- {ln['id']}: {ln['tts']}" for ln in d["lines"] if ln.get("tts") and ln["tts"] != ln["cap"]]
    (W / "SCRIPT.md").write_text("\n".join(md) + "\n")
    print(f"문장 {len(d['lines'])}개, 예상 {total:.0f}초 → SCRIPT.md")
    for i, f in issues:
        print(f"- {i}: " + "; ".join(f))
    print("문제 없음" if not issues else f"문제 {len(issues)}건")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
