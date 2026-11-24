"""로컬 TTS 워커. 표준입력의 JSON 한 줄을 요청 하나로 처리하고 이벤트를 JSON 한 줄씩 돌려준다.

모델은 한 번에 하나만 올려 두고 다음 요청에 재사용한다. 표준입력이 닫히면 끝난다.
"""

import gc
import json
import math
import os
import re
import sys

import numpy as np

events = os.fdopen(os.dup(1), "w", encoding="utf-8")
os.dup2(2, 1)  # 라이브러리의 진행 출력이 이벤트 줄에 섞이지 않게 한다.

MAX_REFERENCE_SECONDS = 60
MAX_SPOKEN_LINES = 200
VOICE_LEVEL = 0.1
SILENCE = 0.003
EDGE_SECONDS = 0.05
PAUSE_FIRST = re.compile(r"^(?:\[[^\]]*\]\s*)*?\[(?:long )?pause\]")
PAUSE_LAST = re.compile(r"\[(?:long )?pause\][\s.!?…]*$")


def emit(**event):
    events.write(json.dumps(event, ensure_ascii=False) + "\n")
    events.flush()


class UserError(Exception):
    pass


# 공식 Drama 3 데모(Apache-2.0)의 목소리 설계 프롬프트. https://huggingface.co/spaces/fishaudio/Drama-3
SCENE_INSTRUCTION = "Voice every line of the script in order, with <|audio_separator|> between consecutive lines."
DESIGN_NAME = "Voice"


def trimmed(audio, text, rate):
    """줄 앞뒤의 무음을 다듬는다. 대사에 적은 쉼이 있는 쪽은 그대로 둔다."""
    loud = np.flatnonzero(np.abs(audio) > SILENCE)
    if not len(loud):
        return audio
    edge = round(rate * EDGE_SECONDS)
    start = 0 if PAUSE_FIRST.search(text) else max(0, loud[0] - edge)
    end = len(audio) if PAUSE_LAST.search(text) else min(len(audio), loud[-1] + 1 + edge)
    return audio[start:end]


class Engine:
    def __init__(self):
        self.path = self.model = self.voice = self.build_frames = None
        self.designed = False
        self.spoken = {}

    def load(self, path):
        import mlx.core as mx
        from mlx_audio.tts.utils import load_model

        if self.path == path:
            return False
        self.path = self.model = self.voice = self.build_frames = None
        self.spoken = {}
        gc.collect()
        mx.clear_cache()
        self.model = load_model(path)
        self.build_frames = getattr(self.model, "build_frames", None)
        self.path = path
        return True

    def reference(self, file):
        from mlx_audio.utils import load_audio

        key = (file, os.path.getmtime(file))
        if self.voice and self.voice[0] == key:
            return self.voice[1]
        audio = load_audio(file, sample_rate=self.model.sample_rate)
        if audio.shape[0] > MAX_REFERENCE_SECONDS * self.model.sample_rate:
            raise UserError(f"참조 음성은 {MAX_REFERENCE_SECONDS}초 이하여야 합니다.")
        self.voice = (key, audio)
        return audio

    def designed_frames(self, design, direction, shape):
        """참조 음성 대신 목소리 설명을 시스템 블록에 적는 build_frames(mlx-audio 0.6.7의 행 구성을 따른다)."""
        import mlx.core as mx

        model = self.model
        scene = [f"Scene: {design['scene']}"] if design.get("scene") else []
        system = "\n".join(scene + ["Characters:", f"- {DESIGN_NAME}: {design['description']}", SCENE_INSTRUCTION])
        start, end, voice = "<|im_start|>user\n", "<|im_end|>\n", "<|im_start|>assistant\n<|voice|>"

        def rows(segment):
            if isinstance(segment, str):
                ids = model.tokenizer.encode(segment).ids
                block = np.zeros((len(ids), 1 + model.num_codebooks), dtype=np.int32)
                block[:, 0] = ids
                return block
            codes = np.array(segment, dtype=np.int32)
            return np.concatenate([codes[:1] + model.semantic_begin, codes]).T

        def build(references, history, target):
            head = [rows(part) for part in ("<|im_start|>system\n", system, end)]
            body = []
            for text, codes in history:
                body += [start, f"{DESIGN_NAME}: {direction}{text}", end, voice, codes, end]
            body += [start, f"{DESIGN_NAME}: {shape(target)}", end, voice]
            blocks = head + [rows(part) for part in body]
            return mx.array(np.concatenate(blocks)), sum(map(len, head))

        return build

    def speak(self, request, voice=None, max_tokens=4096):
        """(음성 조각, 지금 묶음, 전체 묶음 수, 진행 비율, 예상 전체 길이)를 차례로 돌려준다."""
        import mlx.core as mx
        from mlx_audio.tts.models.fish_drama3.chunking import split_text
        from mlx_audio.tts.models.fish_drama3 import drama3

        model, direction = self.model, f"[{request['direction']}] " if request.get("direction") else ""
        extra = {key: request[key] for key in ("temperature", "top_p", "top_k") if request.get(key) is not None}
        if voice:
            extra.update(ref_audio=voice[0], ref_text=voice[1])
        elif request.get("refAudio"):
            extra.update(ref_audio=self.reference(request["refAudio"]), ref_text=request["refText"])
        parts = split_text(request["text"])
        # S2 Pro의 model_type은 설정 파일과 달리 "fish_speech"라서 Drama 3에만 있는 build_frames로 구분한다.
        if self.build_frames is None:
            # S2 Pro는 화자 태그에서만 문장을 나눈다. 나누지 않으면 긴 대사가 1,024프레임에서 잘린다.
            text = "\n".join(f"<|speaker:0|>{direction}{part}" for part in parts)
            parts = model._split_generation_text(text, 300)
        else:
            text = request["text"]
            # 시스템 블록을 미리 계산해 둔 값은 설명이 바뀌면 맞지 않으므로 요청마다 비운다.
            if request.get("design") or self.designed:
                model._voices = drama3._VoiceCache(drama3.VOICE_CACHE_SIZE)
            self.designed = bool(request.get("design"))
            frames = round((request.get("seconds") or 0) * model.sample_rate / model.codec.frame_length)
            length = sum(map(len, parts))

            def shape(part):
                # 목표 길이는 묶음의 글자 수에 비례해 나눈다.
                return direction + part + (f" [audio tokens: {max(1, round(frames * len(part) / length))}]" if frames else "")

            def build(references, history, target):
                # 대사만 고칠 때는 앞 음성을 먼저 한 연기로도 들려줘 연기를 이어 가고, 새 지시가 있으면 목소리만 참조한다.
                before = references[:1] if request.get("retake") and not direction else []
                return self.build_frames(references, before + [(direction + said, codes) for said, codes in history], shape(target))

            model.build_frames = self.designed_frames(request["design"], direction, shape) if request.get("design") else build
        if request.get("seed") is not None:
            mx.random.seed(request["seed"])
        weights = [max(1, len(part)) for part in parts]
        pace, current, made, finished = (request.get("seconds") or 0.15 * sum(weights)) / sum(weights), 0, 0.0, 0.0
        # 괄호·태그로 묶인 긴 대사는 나뉘지 않으므로 기본 1,024프레임(약 47초)에서 잘리지 않게 한다.
        for result in model.generate(text=text, verbose=False, max_tokens=max_tokens, stream=True, streaming_interval=1.0, **extra):
            if result.segment_idx != current:
                pace = made / weights[current] or pace
                current, made, finished = result.segment_idx, 0.0, finished + made
            audio = np.asarray(result.audio, dtype=np.float32)
            made += len(audio) / model.sample_rate
            # 예상보다 느리게 말해도 멈춰 보이지 않도록 묶음 안의 비율은 1에 서서히 다가간다.
            inside = 1 - math.exp(-1.8 * made / (pace * weights[current]))
            fraction = (sum(weights[:current]) + inside * weights[current]) / sum(weights)
            total = finished + max(made * 1.15, pace * weights[current]) + pace * sum(weights[current + 1:])
            yield audio, current + 1, len(parts), fraction, total


    def line(self, key, request, voice=None, max_tokens=4096):
        """한 줄을 조각으로 돌려준다. 같은 줄은 만들어 둔 소리를 다시 쓴다."""
        if key not in self.spoken:
            pieces = []
            for audio, *_, fraction, _ in self.speak(request, voice, max_tokens):
                pieces.append(audio)
                yield None, fraction
            while len(self.spoken) >= MAX_SPOKEN_LINES:
                self.spoken.pop(next(iter(self.spoken)))
            self.spoken[key] = np.concatenate(pieces) if pieces else np.zeros(0, np.float32)
        # 다시 쓴 줄을 뒤로 옮겨 오래 쓰지 않은 줄부터 버린다.
        audio = self.spoken[key] = self.spoken.pop(key)
        yield audio, 1.0

    def dialogue(self, request, marks):
        """줄마다 화자의 목소리를 참조해 만들고 쉬는 시간을 넣어 잇는다.

        한 번에 여러 화자를 합성하면 화자가 바뀌어 들리는 줄이 있어 줄 단위로 만든다.
        """
        import mlx.core as mx

        rate, lines, cast = self.model.sample_rate, request["lines"], request["cast"]
        keys = [json.dumps(member if member.get("design") else [member["refAudio"], os.path.getmtime(member["refAudio"])], ensure_ascii=False, sort_keys=True) for member in cast]
        line_keys = [(keys[line["voice"]], line["text"], line["seed"]) for line in lines]
        # 만들어 둔 소리는 바로 끝나므로 진행률에서 뺀다.
        drawn = [len(member["refText"]) if member.get("design") and key not in self.spoken else 0 for member, key in zip(cast, keys)]
        weights = [0 if key in self.spoken else max(1, len(line["text"])) for key, line in zip(line_keys, lines)]
        whole, done = max(1, sum(weights) + sum(drawn)), 0
        voices = []
        for member, key, weight in zip(cast, keys, drawn):
            if member.get("design"):
                for audio, fraction in self.line(key, {"text": member["refText"], "design": member["design"], "seed": member["seed"]}):
                    yield None, 0, (done + fraction * weight) / whole
            else:
                audio = np.asarray(self.reference(member["refAudio"]), dtype=np.float32)
            done += weight
            # 목소리마다 다른 녹음 크기를 맞추되 속삭임과 외침의 차이는 남긴다.
            level = float(np.sqrt(np.mean(audio[np.abs(audio) > 0.01] ** 2))) if np.any(np.abs(audio) > 0.01) else 0.1
            voices.append(((mx.array(audio), member["refText"]), min(4.0, max(0.25, VOICE_LEVEL / level))))
        position, gap = 0, np.zeros(round(request["gap"] * rate), np.float32)
        for index, (line, key, weight) in enumerate(zip(lines, line_keys, weights)):
            voice, gain = voices[line["voice"]]
            for audio, fraction in self.line(key, {"text": line["text"], "seed": line["seed"]}, voice, 150 + 12 * len(line["text"])):
                yield None, index + 1, (done + fraction * weight) / whole
            if len(audio) < rate * 0.1 or float(np.abs(audio).max()) < 1e-3:
                self.spoken.pop(key, None)
                raise UserError(f"{index + 1}번째 줄의 소리를 만들지 못했습니다. 대사를 바꾸거나 그 줄을 다시 만들어 주세요.")
            audio = trimmed(audio * min(gain, 0.98 / float(np.abs(audio).max())), line["text"], rate)
            marks.append([position / rate, (position + len(audio)) / rate])
            yield audio, index + 1, (done + weight) / whole
            position += len(audio)
            done += weight
            if index < len(lines) - 1:
                yield gap, index + 1, done / whole
                position += len(gap)


def handle(engine, request):
    import soundfile

    if engine.path != request["model"]:
        emit(id=request["id"], event="loading")
        engine.load(request["model"])
    emit(id=request["id"], event="generating")
    audio_parts, rate, marks = [], engine.model.sample_rate, []
    if request.get("lines"):
        for audio, part, fraction in engine.dialogue(request, marks):
            if audio is not None:
                audio_parts.append(audio)
            emit(id=request["id"], event="generating", seconds=sum(map(len, audio_parts)) / rate, part=part, parts=len(request["lines"]), fraction=fraction)
    else:
        for audio, part, parts, fraction, total in engine.speak(request):
            audio_parts.append(audio)
            emit(id=request["id"], event="generating", seconds=sum(map(len, audio_parts)) / rate, total=total, part=part, parts=parts, fraction=fraction)
    audio = np.concatenate(audio_parts) if audio_parts else np.zeros(0, np.float32)
    if len(audio) < rate * 0.2 or float(np.abs(audio).max()) < 1e-3:
        raise UserError("모델이 소리를 만들지 못했습니다. 대사를 바꿔 다시 시도해 주세요.")
    soundfile.write(request["output"], audio, rate, subtype="PCM_16")
    emit(id=request["id"], event="done", seconds=len(audio) / rate, rate=rate, **({"marks": marks} if marks else {}))


def main():
    engine = Engine()
    for line in sys.stdin:
        request = json.loads(line)
        try:
            handle(engine, request)
        except UserError as error:
            emit(id=request["id"], event="error", message=str(error))
        except Exception as error:  # 한 요청의 실패가 올려 둔 모델을 버리게 하지 않는다.
            print(f"local-tts {type(error).__name__}: {error}", file=sys.stderr, flush=True)
            emit(id=request["id"], event="error", message="로컬 모델이 음성을 만들지 못했습니다.")


main()
