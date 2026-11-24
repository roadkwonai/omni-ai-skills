// 녹화하는 브라우저에만 넣는 준비: 값 가림 · canvas 표 가림 · 가짜 커서 · 확대. 앱·서버·설정은 건드리지 않는다.
// page.evaluate(`(${MASK})(${JSON.stringify(CFG)})`) 로 넣고, 화면이 다시 그려진 뒤(탭 전환·팝업)마다 다시 부른다.
// CFG(모두 정규식 글자열/선택자, 생략 가능):
//   value   가릴 수 있는 값            기본: 숫자가 든 글자
//   secret  이 글자가 든 카드·행은 값을 모두 가림(금액뿐 아니라 %·건수·시각도)
//   open    이 글자가 든 카드·행은 보여 줌(secret이 함께 있으면 가림)
//   rest    둘 다 아닌 곳: "hide"(기본) | "show"
//   blurSel 늘 흐릴 선택자(이름·이메일처럼 숫자가 없는 값, 예: "td:nth-child(2)")
//   card    카드로 볼 선택자            blockSel 문단으로 볼 선택자(카드 · 행 · 문단 중 하나라도 secret이면 가림)
//   hideSel 아예 숨길 요소(도구 막대 등)   table  canvas 표 선택자(행은 role="row"), rowH 행 높이, keepPx 왼쪽에 남길 폭
(cfg) => {
  if (window.__mask) return window.__mask();
  const C = Object.assign({ value: "[0-9]", secret: "(?!)", open: "(?!)", rest: "hide", blurSel: "", card: ".card,[data-card]",
    blockSel: "tr,[role=row],p,li,h1,h2,h3,h4,label,div", hideSel: '[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"]',
    table: '[data-testid="stDataFrame"]', rowH: 32, keepPx: 265, accent: "#ff6600" }, cfg || {});
  const V = new RegExp(C.value), S = new RegExp(C.secret), O = new RegExp(C.open);
  const st = document.createElement("style");
  st.textContent = `${C.hideSel}{visibility:hidden!important}
    .vm-blur{filter:blur(max(9px,.55em))!important} /* 42px 숫자는 8px 흐림으로 읽힌다: 글자 크기에 비례 */
    .vm-veil{position:absolute;right:0;backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);background:rgba(255,255,255,.35);z-index:5;pointer-events:none}
    #vm-cursor{position:fixed;left:0;top:0;width:26px;height:26px;z-index:2147483647;pointer-events:none;transition:transform .6s cubic-bezier(.2,.7,.2,1);filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))}
    #vm-cursor.click::after{content:"";position:absolute;left:-14px;top:-14px;width:28px;height:28px;border-radius:50%;border:3px solid ${C.accent};animation:vmRing .5s ease-out forwards}
    @keyframes vmRing{from{transform:scale(.3);opacity:1}to{transform:scale(1.6);opacity:0}}`;
  document.head.appendChild(st);
  const hide = (el) => {
    const boxes = [el.closest(C.card), el.closest("tr,[role=row],li"), el.closest(C.blockSel) || el].filter(Boolean);
    const ts = boxes.map((b) => (b.innerText || b.textContent || "").slice(0, 400));
    if (ts.some((t) => S.test(t))) return true;
    return ts.some((t) => O.test(t)) ? false : C.rest === "hide";
  };
  const scan = () => {
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) {
      const p = w.currentNode.parentElement;
      if (!p || /^(SCRIPT|STYLE)$/.test(p.tagName) || !V.test(w.currentNode.textContent)) continue;
      p.classList.toggle("vm-blur", hide(p)); // 다시 그려 값이 바뀐 요소도 매번 다시 판정한다
    }
    if (C.blurSel) document.querySelectorAll(C.blurSel).forEach((e) => e.classList.add("vm-blur"));
    document.querySelectorAll("input,textarea,select").forEach((i) => i.classList.toggle("vm-blur", V.test(i.value || "") && hide(i)));
    // canvas로 그린 표는 글자 노드가 없다: 숨은 접근성 행에서 내용을 읽어 행을 덮는다. 행 높이는 화면마다 재서 rowH로 준다
    document.querySelectorAll(C.table).forEach((d) => {
      const rows = [...d.querySelectorAll('[role="row"]')], key = rows.map((r) => r.innerText).join("|");
      if (d.dataset.vmKey === key) return;
      d.dataset.vmKey = key; d.querySelectorAll(".vm-veil").forEach((v) => v.remove());
      if (getComputedStyle(d).position === "static") d.style.position = "relative";
      rows.slice(1).forEach((r, i) => {
        if (!S.test(r.innerText) && (O.test(r.innerText) || C.rest === "show")) return;
        const v = document.createElement("div"); v.className = "vm-veil";
        Object.assign(v.style, { left: C.keepPx + "px", top: C.rowH * (i + 1) - 2 + "px", height: C.rowH + 5 + "px" }); d.appendChild(v);
      });
    });
  };
  scan();
  new MutationObserver(scan).observe(document.body, { childList: true, subtree: true, characterData: true });
  const c = document.createElement("div"); c.id = "vm-cursor";
  c.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26"><path d="M3 2l7 19 2.6-7.4L20 11z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  document.body.appendChild(c);
  window.__cursor = (x, y, ms = 600) => { c.style.transitionDuration = ms + "ms"; c.style.transform = `translate(${x}px,${y}px)`; };
  window.__ring = () => { c.classList.remove("click"); void c.offsetWidth; c.classList.add("click"); };
  // 화면 한 점을 중심으로 확대했다가(k) 되돌린다(1): 작은 라벨을 촬영에서 바로 읽히게
  window.__zoom = (x, y, k = 1, ms = 900, sel = "main,body") => { const m = document.querySelector(sel), b = m.getBoundingClientRect(); document.documentElement.style.overflowX = "hidden"; // 확대 때 가로 스크롤 막대가 생기지 않게
    m.style.transition = `transform ${ms}ms cubic-bezier(.2,.7,.2,1)`; m.style.transformOrigin = `${x - b.left}px ${y - b.top}px`; m.style.transform = k === 1 ? "" : `scale(${k})`; };
  window.__mask = () => { scan(); return { blurred: document.querySelectorAll(".vm-blur").length, veils: document.querySelectorAll(".vm-veil").length }; };
  return window.__mask();
}
