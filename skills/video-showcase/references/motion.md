# 장면 설계 · SpotTour · HyperFrames

## 장면 처방

| 말하는 내용 | 화면 |
| --- | --- |
| 문제를 던지는 첫 문장 | 큰 글자 두 줄, 핵심 낱말 하나만 강조색, 밑줄이 그어짐. 또는 큰 글자 모양 구멍 안으로 실제 화면이 흐름 |
| 통계·수치 | 숫자 굴림(`count`) 뒤 멈춤, 막대는 실제 비율. 출처·연도를 28px로. '1% 미만'처럼 센 값은 `slam` + 화면 흔들림 |
| 사람은/우리는 비교 | 표가 줄마다 잘려 열림, 마지막 줄만 강조색 |
| 구조·흐름 | 선이 따라 그려지고(`draw`) 빛 점이 돈다. 막히는 예 하나를 빨강으로 튕겨 낸다 |
| 조건이 모두 맞아야 함 | 스위치가 단어마다 켜지고 램프가 켜짐 → 하나 끄면 꺼짐까지 보여 준다 |
| 안전장치·단계 | 단면도의 문을 주문이 지나며 문마다 막히는 예시 |
| 한 화면의 여러 칸 | SpotTour |
| 눌러서 열림·훑어봄 | 실제 녹화 → 같은 화면 정지본으로 이어 확대·도장 |
| 기록·근거 | 카드가 쌓이며 넘어감(실제 기록 문구) |
| 하루 일정·자동화 | 시간 막대를 따라가며 작업이 켜짐. 대화 예시는 '예시'라고 적는다 |
| 마무리 | 요소가 빠지고 로고·이름·주소로 모임, 면책 |

장면 움직임은 모두 `words.py`의 +초에 맞춘다. 말과 관계없이 일정 간격으로 나오게 하지 않는다. 다 나온 뒤에는 읽을 시간 동안 멈춘다. 다만 3초 넘게 완전히 정지하면 아주 느린 카메라(`cam`, ease "none")를 준다. 훅의 첫 줄은 0.2초 안에 보이기 시작한다(첫 프레임이 비었다는 `first_frame_empty` 경고는 등장 동작 때문이면 둔다). 파트 장면은 첫 단어보다 0.7초쯤 먼저 시작하므로 **0.3초 안에 무엇이든 보이게** 하고(아니면 빈 화면이 된다), 파트 끝에서도 마지막 요소를 다음 파트까지 남긴다. 자막 자리(y 900 아래)와 파트 이름표(왼쪽 위)를 비운다. **파트 이름표가 제품 화면의 로고·메뉴를 가리면** 3초 뒤 사라지게 하거나 빈 모서리로 옮긴다.

## SpotTour

`remotion/tours.json`:

```json
{ "P3Cards": { "src": "overview.jpg", "frames": 213, "accent": "#ff6600", "stops": [
  { "x": 372, "y": 472, "w": 355, "h": 98, "t": 0.84, "label": "체결과 손익", "lift": true, "zoom": 1.75 } ] } }
```

- `src`: `remotion/public/`의 1920×1080 가림본. 좌표는 `record.py`가 출력한 칸 좌표를 그대로 쓴다. `lift`하는 칸에는 여유 없이, 구역을 감쌀 때는 `spot(..., 여유px)`.
- `t`: 샷 시작 기준 초 = 단어의 +초 − 샷이 장면에서 시작하는 초. 0.17초 먼저 켜지는 것은 샷이 알아서 한다.
- `label`: 화면에 실제로 있는 글자. `lift`: 카드가 떠오름(큰 구역·표에는 끈다). `zoom`: 작은 글자 2.0~2.4, 카드 1.45~1.75, 전체 1.1~1.2.
- 첫 칸의 `t`는 0.45초 이상이어야 0.17초 먼저 켜진다(조명이 켜지는 8프레임). 장면 첫 단어를 짚으려면 샷을 그만큼 일찍 시작한다. 첫 칸이 켜지기 전이 1초를 넘으면 어두운 화면만 보이니 샷을 늦게 시작하거나 넓은 칸을 먼저 켠다. 가려진 칸은 비추지 않는다.
- 마지막 stop은 넓은 칸으로 끝내 다음 장면으로 넘어가기 쉽게 한다. `frames` = 길이 × 30.
- 렌더: `cd $W/remotion && npm install && npx remotion still src/index.ts P3Cards out.png --frame=60`(위치 확인) → `npx remotion render src/index.ts P3Cards ../assets/clips/P3Cards.mp4`
- 샷이 가린 나머지 화면도 흐릿하게 보인다. 바탕 이미지 전체가 가림본이어야 한다.

## kind (pick.py가 읽는 말의 종류)

| kind | 뜻 | 후보(앞이 우선) |
| --- | --- | --- |
| hook · identity | 문제 제기 · 이름과 정체 | 큰 글자 / TextMask |
| stat · result | 통계 · 결과 숫자 | 숫자 굴림 / CrashZoom(result) |
| compare · before_after | 말로 비교 · 앞뒤 화면 비교 | 비교표 / BeforeAfter / 숫자 굴림 |
| overview · cells · focus | 화면 전체 · 여러 칸 · 한 칸 | TiltGlide · SpotTour · CrashZoom |
| action · switch | 눌러서 열림 · 화면에서 화면으로 | 녹화 · CardFlip |
| structure · inputs · steps · conditions | 구조 · 입력 모음 · 관문 · 모두 켜져야 함 | 흐름도 · 모음 · 단면도 · 스위치 |
| log · schedule | 기록 · 일정 | 카드 쌓기 · 시간 막대 |
| disclaimer · outro | 면책 · 마무리 | 큰 글자 · Lockup |

`hf:`로 시작하는 것은 HyperFrames 장면이다(`assets/examples/`: title·count·table은 p1, flow는 p2, converge·cards는 p4, gates·switches는 p5, timeline은 p8, outro는 p9).

## 값만 넣는 샷

`tours.json`에 `"shot"`을 적는다(생략하면 SpotTour). 시각은 모두 샷 시작 기준 초, 이미지는 `remotion/public/`의 1920×1080 가림본.

```json
{ "P0Mask":  { "shot": "TextMask", "src": "a.jpg", "frames": 150, "accent": "#ff6600", "word": "이름(2~6자)", "sub": "한 줄 설명", "rush": 3.2 },
  "P2Crash": { "shot": "CrashZoom", "src": "a.jpg", "frames": 90, "accent": "#ff6600", "target": {"x":798,"y":161,"w":306,"h":263}, "label": "확인 응답", "hit": 1.2 },
  "P2Glide": { "shot": "TiltGlide", "src": "a.jpg", "frames": 150, "accent": "#ff6600", "stops": [ {"x":462,"y":161,"w":980,"h":263,"t":0.9,"label":"오늘 예약"} ] },
  "P3BA":    { "shot": "BeforeAfter", "before": "old.jpg", "after": "new.jpg", "frames": 120, "accent": "#ff6600", "beforeLabel": "전", "afterLabel": "후", "t": 0.5 },
  "P3Flip":  { "shot": "CardFlip", "from": "a.jpg", "to": "b.jpg", "frames": 90, "accent": "#ff6600", "t": 1.0, "fromLabel": "목록", "toLabel": "상세" },
  "P9End":   { "shot": "Lockup", "src": "a.jpg", "frames": 120, "accent": "#ff6600", "title": "이름", "at": 1.2, "sub": "설명", "url": "주소", "note": "면책", "logo": "logo.png" } }
```

- `hit`·`t`·`rush`는 그 단어의 +초 − 샷 시작. CrashZoom은 그 순간 쾅 멈추므로 `sfx`에 같은 시각의 `thud`, CardFlip·BeforeAfter는 `whoosh`를 넣는다.
- Lockup의 `at`은 이름이 나오는 초(말하는 단어에 맞춘다). 마무리에 CardFlip을 쓰면 `to` 대신 `toTitle`·`toSub`·`toUrl`을 주어 뒷면을 이름 카드로 만든다.
- **레시피를 바꾸면 세 곳이 함께 바뀌어야 한다**: `pick.py`(선택) → `tours.json`(값) → `compositions/`의 `<video src>`(연결). `qa.py`가 선택과 실제 장면이 다르면 알린다. 한 문장이 녹화로 시작해 샷으로 넘어가면 `kind`는 마지막 강조에 맞춘다.
- BeforeAfter는 **정말 앞뒤인 두 화면**에만 쓴다. TextMask의 글자 안이 어두우면 밝은 화면을 고른다.
- 렌더는 **한 번에 하나씩** 한다(처음에 브라우저를 받는 동안 여러 개를 돌리면 모두 실패한다).

## 원본 shotcraft 샷 가져오기

`add_shot.py $W <이름>`이 video-shotcraft(https://github.com/Vincentwei1021/video-shotcraft, Apache-2.0, 확인한 커밋 `075b548`)에서 코드·부품·그림을 `remotion/src/shots/`로 가져오고 컴포지션 이름과 길이를 알려 준다. 그다음:

1. `npm install`(새 패키지가 있으면) → `CARD.md`에서 시간표와 함정을 읽는다.
2. 원본은 가짜 화면·중국어나 영어 문구·자기 색이다. 화면은 가림본 이미지로, 문구·글꼴(Pretendard)·색은 SPEC으로 바꾼다. 길이는 문장 시간에 맞춘다(배속은 클립의 `data-playback-rate` 0.9~1.15까지).
3. `npx remotion still src/index.ts <이름> out.png --frame=N`으로 세 시점을 본다. **원본의 문구·상표·가짜 화면이 한 곳이라도 남으면 쓰지 않는다.**
4. 렌더해서 `assets/clips/`에 넣고 컴포지션에서 쓴다. 기본 모양이 남으면 템플릿처럼 보인다.

그 밖에: lemo-opuscar `swiss-motion`은 문법(격자·신호색 하나·잘려 올라오는 등장)만 참고했고 그 결과가 틀의 `rev()`다. 검토했지만 쓰지 않은 것: OpenMontage(AGPL·생성형 중심), community `duo`(사진 권리 불분명).

## HyperFrames 함정 (0.9.72)

- **timed `<video>`는 컴포지션 루트의 바로 아래**에 둔다. 다른 div 안에 두면 렌더되지 않거나 시간이 어긋난다. 겹칠 때는 `z-index`, 사라질 때는 opacity 트윈.
- `left`/`top` 트윈은 lint 오류다. `x`/`y`/`scale`로 움직인다. 크기를 바꾸는 막대는 `scaleX` + `transformOrigin`(글자가 든 요소에는 쓰지 않는다 — 찌그러진다).
- 스타일 선택자는 장면 id로 시작한다(`#p3 .card`). 장면끼리 같은 id·클래스가 부딪힌다.
- 한 파일에 timeline 하나, `window.__timelines["p3"]`에 등록, `paused: true`. `Math.random`·`Date`·네트워크를 쓰지 않는다.
- 숨겨 두었다가 나올 요소는 CSS에 `opacity: 0`을 두고 `tl.fromTo`·`tl.to`로 켠다. `tl.set(sel, {opacity:0}, 0)`은 0프레임에 먹지 않을 수 있어 check가 경고한다(`examples/`의 옛 장면에는 남아 있다).
- 파트 장면 안 시각은 0부터다. `index.html`의 절대 시각과 섞지 않는다(`nested_media_start_basis_ambiguous` 경고는 장면 안 시각이면 그대로 둔다).
- 루트에 `index*.html`을 여러 개 두면 check가 실패한다. 비교판은 다른 폴더에 둔다.
- 일부러 겹치거나 넘치는 요소에는 `data-layout-allow-overlap` / `-overflow` / `-occlusion`.
- 장면 길이가 바뀌면(대본을 고치면) `make_index.py`가 `index.html`은 새로 쓰지만 기존 `compositions/`의 clip 길이는 그대로다. `words.py` 출력을 보고 장면 시각을 다시 맞춘다.
- 컴포지션은 `check` 통과만 보지 말고 움직임이 있는 순간을 `snapshot --at`으로 본다. 화면 글자 잘림·겹침은 check가 다 잡지 못한다.
- 이 ffmpeg에 drawtext·libwebp가 없을 수 있다. 글자는 HTML로, webp는 `cwebp`로.
- 배포판 다른 판으로 올리려면 check → snapshot을 다시 보고 올린다.

## 비교해서 고르기

사용자가 두 방식 사이에서 고민하면 그 파트만 두 판 렌더(`--start/--end`)해 나란히(`hstack`) 보여 준다. 말로 설명하는 것보다 빠르다.
