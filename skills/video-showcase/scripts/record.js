// record.py가 앞에 설정(R)을 붙이고 아래 SCENE 자리에 장면을 넣어 ego-browser nodejs로 실행한다.
const fs = await import("node:fs");
fs.mkdirSync(R.out + "/frames", { recursive: true });
const K = 1920 / R.css; // css 폭을 줄이면(예 1280) 같은 1920×1080 영상에 글자가 1.5배 크게 담긴다
const task = await taskSpace("video record");
const page = await task.newPage();
await page.cdp("Emulation.setDeviceMetricsOverride", { width: R.css, height: Math.round(R.css * 9 / 16), deviceScaleFactor: K, mobile: false });
await page.goto(R.url, { timeout: 60000 });
await page.waitForTimeout(R.first);
const mask = () => page.evaluate(`(${R.mask})(${JSON.stringify(R.cfg)})`);
console.log("가림", await mask());
const marks = {}, mark = (k) => { marks[k] = Date.now(); };
const wait = (ms) => page.waitForTimeout(ms);
let cx = R.css / 2, cy = R.css / 3;
const move = async (x, y, ms = 700) => { await page.evaluate(([x, y, ms]) => window.__cursor(x, y, ms), [x, y, ms]); await page.mouse.move(x, y); cx = x; cy = y; await wait(ms); };
const click = async () => { await page.evaluate(() => window.__ring()); await page.mouse.click(cx, cy); };
const zoom = async (x, y, k = 1, ms = 900) => { await page.evaluate(([x, y, k, ms]) => window.__zoom(x, y, k, ms), [x, y, k, ms]); await wait(ms); };
// 본문 스크롤 영역(가장 넓은 스크롤 요소)을 고른다: 사이드바가 잡히지 않게
const scroll = async (y, ms = 1200) => { await page.evaluate((y) => { const s = [document.scrollingElement, ...document.querySelectorAll("*")].filter((e) => e.scrollHeight > e.clientHeight + 100 && (e === document.scrollingElement || /auto|scroll/.test(getComputedStyle(e).overflowY))).sort((a, b) => b.clientWidth - a.clientWidth)[0]; s && s.scrollTo({ top: y, behavior: "smooth" }); }, y); await wait(ms); };
// 보이는 것 중 첫 줄 글자가 정확히 같은 것(없으면 그 글자로 시작하는 것)
const box = (sel, text) => page.evaluate(([sel, text]) => { const v = [...document.querySelectorAll(sel)].filter((e) => { const b = e.getBoundingClientRect(); return b.width && b.height && getComputedStyle(e).visibility !== "hidden"; });
  const e = text ? v.find((e) => e.innerText.trim() === text) || v.find((e) => e.innerText.trim().split("\n")[0] === text) : v[0];
  if (!e) return null; const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; }, [sel, text]);
const need = async (sel, text) => { const b = await box(sel, text); if (!b) throw new Error(`못 찾음: ${sel} ${text ?? ""}`); return b; };
const center = async (sel, text) => { const [x, y, w, h] = await need(sel, text); return [x + w / 2, y + h / 2]; };
const press = async (sel, text, settle = 1500) => { await move(...await center(sel, text)); mark(`누름:${text}`); await click(); await wait(250); paused = true; await wait(settle); await mask(); paused = false; };
const spots = {}, frames = [];
const spot = async (name, sel, text, pad = 0) => { const [x, y, w, h] = await need(sel, text); spots[name] = { x: Math.round((x - pad) * K), y: Math.round((y - pad) * K), w: Math.round((w + 2 * pad) * K), h: Math.round((h + 2 * pad) * K) }; };
const shot = async (q) => Buffer.from((await page.cdp("Page.captureScreenshot", { format: "jpeg", quality: q })).data, "base64");
const still = async (name) => { paused = true; await wait(120); await mask(); await page.evaluate(() => { document.getElementById("vm-cursor").style.opacity = 0; }); await wait(60);
  const b = await shot(95); fs.writeFileSync(`${R.img}/${name}.jpg`, b); fs.writeFileSync(`${R.pub}/${name}.jpg`, b); await page.evaluate(() => { document.getElementById("vm-cursor").style.opacity = 1; }); paused = false; };
let rec = true, paused = false, err = null;
await page.evaluate(([x, y]) => window.__cursor(x, y, 0), [cx, cy]);
const loop = (async () => { let n = 0; while (rec) { if (paused) { await wait(50); continue; }
  const b = await shot(88), f = `frames/f${String(n++).padStart(5, "0")}.jpg`; fs.writeFileSync(`${R.out}/${f}`, b); frames.push([f, Date.now()]); } })();
try {
/*SCENE*/
} catch (e) { err = String(e); }
rec = false; await loop;
fs.writeFileSync(`${R.out}/frames.json`, JSON.stringify({ frames, marks, spots, err }));
console.log({ frames: frames.length, err });
await task.finish({ keep: [] });
