"""문장별 음성을 만든다 → assets/vo_raw/<ID>.mp3 (바뀐 문장만).

python3 tts.py <작업 폴더> [--engine drama-3|s2-pro|fish-api] [--env .env 경로] [--only S03 S05]
python3 tts.py <작업 폴더> --audition 4     같은 설계의 목소리 후보(시드만 다름)
python3 tts.py --options                    로컬 모델에서 쓸 수 있는 옵션 전부

엔진: script.json voice_engine. drama-3·s2-pro는 이 컴퓨터에서 만들고(글이 밖으로 나가지 않음) fish-api는 Fish Audio 무료 API다.
--engine을 주면 script.json에 저장한다. 직접 녹음한 소리는 assets/vo_raw/<ID>.mp3에 넣고 이 단계를 건너뛴다."""
import sys

from lib import load, save, work

ENGINES = ("drama-3", "s2-pro", "fish-api")


def arg(flag):
    return sys.argv[sys.argv.index(flag) + 1:] if flag in sys.argv else []


def main():
    import tts_local
    if "--options" in sys.argv:
        return tts_local.show()
    W = work()
    d = load(W / "script.json")
    if arg("--engine"):
        d["voice_engine"] = arg("--engine")[0]
        save(W / "script.json", d)
    engine = d.get("voice_engine", "fish-api")
    if engine not in ENGINES:
        raise SystemExit(f"voice_engine은 {', '.join(ENGINES)} 중 하나")
    if "--audition" in sys.argv:
        return tts_local.audition(W, d, int((arg("--audition") or ["3"])[0]))
    missing = [ln["id"] for ln in d["lines"] if not ln.get("tts")]
    if missing:
        raise SystemExit(f"읽기(tts)가 빈 문장: {', '.join(missing)} — review_script.py를 먼저")
    if engine == "fish-api":
        import tts_fish
        bad = [ln["id"] for ln in d["lines"] if "<" in ln["tts"]]
        if bad:
            raise SystemExit(f"감싸는 지시 < >는 drama-3에서만 씀: {', '.join(bad)}")
        return tts_fish.make(W, d, (arg("--env") or [None])[0])
    only = {a for a in arg("--only") if not a.startswith("--")}
    tts_local.make(W, d, engine, only)


if __name__ == "__main__":
    main()
