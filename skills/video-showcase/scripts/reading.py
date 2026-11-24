"""자막 문장(cap) → TTS 읽기 문장. 영어와 숫자를 모두 한글로 바꾼다.

숫자: 한자어 읽기(3000년→삼천년, 1.5→일점오). 1은 자리 앞에서 생략(10→십, 100→백).
      NATIVE 단위가 바로 뒤에 오면 고유어(15개→열다섯개, 3명→세명, 2배→두배), 1~99. 개월은 한자어(3개월→삼개월).
      '번·대·장'처럼 뜻에 따라 갈리는 단위는 한자어로 두니, 고유어로 읽어야 하면 script.json의 tts를 직접 고친다.
기호: % → 퍼센트, %p → 퍼센트포인트.
영어: WORDS + script.json의 reading 사전(대소문자 구분 없음). 사전에 없는 영어가 남으면 오류로 멈춘다.
어절 수를 바꾸지 않는다(음성 단어 시간을 자막 단어에 순서대로 붙이기 위해).
"""
import re
import sys

WORDS = {"ai": "에이아이", "api": "에이피아이", "pdf": "피디에프", "github": "깃허브", "claude": "클로드", "code": "코드"}
NATIVE = ("개", "명", "시간", "시", "가지", "곳", "마리", "살", "배", "편", "권", "잔")
DIGIT = "영일이삼사오육칠팔구"
NATIVE_ONES = ["", "하나", "둘", "셋", "넷", "다섯", "여섯", "일곱", "여덟", "아홉"]
NATIVE_ONES_ADN = ["", "한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉"]  # 수 관형사(개 앞)
NATIVE_TENS = ["", "열", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔"]


def sino_under_10000(n: int) -> str:
    out = ""
    for unit, name in ((1000, "천"), (100, "백"), (10, "십"), (1, "")):
        d = n // unit % 10
        if d:
            out += ("" if (d == 1 and name) else DIGIT[d]) + name
    return out


def sino(n: int) -> str:
    if n == 0:
        return "영"
    parts, units = [], ["", "만", "억", "조"]
    i = 0
    while n:
        chunk = n % 10000
        if chunk:
            word = sino_under_10000(chunk)
            if units[i] == "만" and chunk == 1:
                word = ""  # 10000 → 만
            parts.append(word + units[i])
        n //= 10000
        i += 1
    return "".join(reversed(parts))


def number(text: str) -> str:
    if "." in text:
        a, b = text.split(".", 1)
        return sino(int(a)) + "점" + "".join(DIGIT[int(c)] for c in b)
    return sino(int(text))


def native_counter(n: int) -> str:
    if n == 20:
        return "스무"
    return NATIVE_TENS[n // 10] + NATIVE_ONES_ADN[n % 10]


def plain(text: str) -> str:
    """읽기에서 연기 지시([pause]·<emphasis>)를 뺀, 실제로 소리 내는 말."""
    s = re.sub(r"\[[^\[\]\n]*\]", " ", re.sub(r"</?[a-z][a-z-]*>", "", text, flags=re.I))
    return re.sub(r" ([.,!?…])", r"\1", re.sub(r"[ \t]+", " ", s)).strip()


def to_reading(cap: str, extra: dict | None = None) -> str:
    words = WORDS | {k.lower(): v for k, v in (extra or {}).items()}
    s = cap.replace("%p", "퍼센트포인트").replace("%", "퍼센트")

    def num(m):
        raw, after = m.group(1), m.group(2) or ""
        if after.startswith(NATIVE) and not after.startswith("개월") and "." not in raw and 0 < int(raw.replace(",", "")) < 100:
            return native_counter(int(raw)) + after
        return number(raw.replace(",", "")) + after

    s = re.sub(r"((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)([가-힣]*)", num, s)  # 쉼표는 천 단위(1,000)일 때만 숫자

    def eng(m):
        w = m.group(0)
        if w.lower() not in words:
            raise ValueError(f"사전에 없는 영어: {w} (script.json reading에 추가)")
        return words[w.lower()]

    s = re.sub(r"[A-Za-z]+", eng, s)
    if len(s.split()) != len(cap.split()):
        raise ValueError(f"어절 수가 바뀜: {cap} → {s}")
    return s


def _selftest():
    cases = {
        "3000년": "삼천년", "30": "삼십", "1.5배": "일점오배", "2026년": "이천이십육년", "10": "십", "0": "영",
        "101": "백일", "1305": "천삼백오", "12345": "만이천삼백사십오", "46%가": "사십육퍼센트가", "6.5%p": "육점오퍼센트포인트",
        "15개가": "열다섯개가", "20개": "스무개", "3개월": "삼개월", "3명이": "세명이", "24시간": "스물네시간", "2배로": "두배로",
        "2만 원": "이만 원", "1분마다": "일분마다", "나스닥100": "나스닥백", "20, 30, 40% 하락": "이십, 삼십, 사십퍼센트 하락",
        "1,000원": "천원", "Omni AI는": "옴니 에이아이는",
    }
    for cap, want in cases.items():
        got = to_reading(cap, {"Omni": "옴니"})
        assert got == want, (cap, got, want)
    print(f"selftest ok ({len(cases)} cases)")


if __name__ == "__main__":
    _selftest()
    for line in sys.argv[1:]:
        print(to_reading(line))
