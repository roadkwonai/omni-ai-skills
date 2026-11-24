이 폴더의 다음 파일은 프로젝트의 MIT 라이선스가 아니라 각자의 라이선스를 따른다.

- `remotion/src/PageCam2D.tsx`, `Polish.tsx`, `SpotTour.tsx`(고쳐 씀), `Shots.tsx`(방식을 따라 새로 씀): video-shotcraft 075b548, Apache-2.0 (`remotion/LICENSE-video-shotcraft`)
- `fonts/PretendardVariable.woff2`: Pretendard 1.309, SIL OFL 1.1 (`fonts/OFL.txt`)
- 배경음·효과음은 저장소에 없다. `lib.audio()`가 처음 쓸 때 Mixkit에서 받아 해시를 확인한다(`sound.json` files). 조건은 2026-11-24에 원문으로 확인했다.
  - Mixkit Stock Music Free License(https://mixkit.co/license/#musicFree): 웹·소셜·팟캐스트·온라인 광고 영상에 상업적으로 쓸 수 있다. TV·라디오 방송, 게임, CD·DVD에는 못 쓴다. 음악만 다시 만들거나 자기 것으로 등록할 수 없다. Tonight(Michael Ramir C.), G Eazy NBA type·Cat Walk(Arulo), House Vibez(Lily J)
  - Mixkit Sound Effects Free License(https://mixkit.co/license/#sfxFree): 영상·방송·게임에 쓸 수 있다. 소리 파일만 따로, 또는 도구·템플릿·소스와 함께 재배포할 수 없다.
- 로컬 음성: `scripts/local_tts_worker.py`와 `setup_local_tts.sh`는 Omni AI Canvas의 로컬 TTS 구현에서 가져왔다(목소리 설계 프롬프트는 공식 Drama 3 데모, Apache-2.0). 모델 가중치는 저장소에 없다. Built with Fish Audio. Drama 3 = Fish Audio Community License(매출 50만 달러 미만 상업 가능, 음성 생성 서비스 제공 불가), S2 Pro = Fish Audio Research License(연구·비상업만)
- Remotion(https://www.remotion.dev/docs/license): 개인과 3명 이하 회사는 무료, 그 밖에는 회사 라이선스가 필요하다.
