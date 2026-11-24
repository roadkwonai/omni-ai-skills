// 이 파트에서 말하는 순서대로 움직인다(capture/<파트>.scene.js로 복사). 조회만 한다.
// 누르지 않을 것: (저장·전송·결제·주문·스위치·삭제 버튼 이름을 적는다)
// 쓸 수 있는 것: move(x,y,ms) click() press(sel,글자,기다림ms) wait(ms) zoom(x,y,배율) mark(이름) center(sel,글자) scroll(y)
//               spot(이름,sel,글자,여유px) — 칸 좌표를 재서 SpotTour용으로 출력 · still(이름) — 가림된 정지 화면을 assets/img에 저장
mark("overview"); await move(900, 300); await wait(800);
// await press("button", "탭 이름"); mark("tab"); await move(1200, 420); await zoom(1200, 420, 1.6); await wait(1500); await zoom(1200, 420, 1);
// await spot("확인 응답", ".card", "확인 응답"); await still("overview");
await wait(500);
