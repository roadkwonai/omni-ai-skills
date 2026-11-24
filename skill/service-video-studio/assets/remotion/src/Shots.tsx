// 값만 넣으면 되는 샷 6개. 방식은 video-shotcraft 샷 카드(text-as-mask · crash-zoom-punch · steep-tilt-glide ·
// before-after-slider-scrub · card-flip-reveal · logo-shrink-wordmark-lockup)를 따르고 모양은 SPEC(바탕·강조색 하나·Pretendard)으로 새로 썼다.
// 시각 t는 모두 샷 시작 기준 초. 이미지는 remotion/public의 1920×1080 가림본.
import React from 'react';
import { AbsoluteFill, Easing, Img, continueRender, delayRender, interpolate, staticFile, useCurrentFrame } from 'remotion';
import { CamKey2D, PageCam2D } from './PageCam2D';
import { EASE, Grain, SpeedBlur, mix, ramp } from './Polish';

const BG = '#131209', INK = '#f3f4f5', MUTE = '#b0b3ba';
const FONT = '"Pretendard Variable", Pretendard, sans-serif';
const S = (sec: number) => Math.round(sec * 30);
const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
type Rect = { x: number; y: number; w: number; h: number };

// 글꼴을 다 불러온 뒤에 그린다(없으면 글자 크기·구멍 위치가 달라진다)
const useFont = () => {
  const [ready, set] = React.useState(false);
  const [handle] = React.useState(() => delayRender('font'));
  React.useEffect(() => {
    new FontFace('Pretendard Variable', `url(${staticFile('PretendardVariable.woff2')})`, { weight: '100 900' })
      .load().then((f) => { document.fonts.add(f); set(true); continueRender(handle); });
  }, [handle]);
  return ready;
};
const Full: React.FC<{ src: string; style?: React.CSSProperties }> = ({ src, style }) => (
  <Img src={staticFile(src)} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', ...style }} />
);
const Tag: React.FC<{ text: string; accent: string; style?: React.CSSProperties }> = ({ text, accent, style }) => (
  <div style={{ position: 'absolute', background: accent, color: BG, fontFamily: FONT, fontWeight: 800, letterSpacing: '-0.02em', fontSize: 38, padding: '8px 22px', borderRadius: 10, whiteSpace: 'nowrap', ...style }}>{text}</div>
);

// 1. TextMask — 큰 글자 모양 구멍으로 실제 화면이 흐르다가 글자 속으로 뛰어들어 전체 화면이 된다(오프닝·정체)
export type TextMaskProps = { src: string; frames: number; accent: string; word: string; sub?: string; rush?: number };
// 글자 획 안에서 가장 두꺼운 곳(뛰어들 자리)을 잰다: 안쪽으로 한 겹씩 깎아 마지막까지 남는 점
const thickest = (word: string, size: number) => {
  const k = 6, W = 320, H = 180, c = document.createElement('canvas');
  c.width = W; c.height = H;
  const g = c.getContext('2d')!;
  g.font = `900 ${size / k}px "Pretendard Variable"`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(word, W / 2, H / 2);
  const d = g.getImageData(0, 0, W, H).data;
  let on = new Uint8Array(W * H), last = [W / 2, H / 2];
  for (let i = 0; i < on.length; i++) on[i] = d[i * 4 + 3] > 128 ? 1 : 0;
  for (let r = 0; r < 60; r++) {
    const nx = new Uint8Array(W * H);
    let best = 1e9, found = false;
    for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
      const i = y * W + x;
      if (on[i] && on[i - 1] && on[i + 1] && on[i - W] && on[i + W]) {
        nx[i] = 1; found = true;
        const dist = Math.abs(x - W / 2) + Math.abs(y - H / 2);
        if (dist < best) { best = dist; last = [x, y]; }
      }
    }
    if (!found) break;
    on = nx;
  }
  return { x: last[0] * k, y: last[1] * k };
};
export const TextMask: React.FC<TextMaskProps> = ({ src, frames, accent, word, sub, rush }) => {
  const f = useCurrentFrame(), ready = useFont();
  const size = Math.min(470, 1640 / Math.max(1, [...word].reduce((a, c) => a + (/[가-힣]/.test(c) ? 0.9 : 0.7), 0)));
  const o = React.useMemo(() => (ready ? thickest(word, size) : { x: 960, y: 540 }), [ready, word, size]);
  const r0 = rush === undefined ? frames - 60 : S(rush), r1 = r0 + 24;
  const go = Math.pow(ramp(f, r0, r1 - r0, EASE.linear), 1.8);
  const s = (1.04 - 0.04 * ramp(f, 0, 18)) * (1 - 0.035 * ramp(f, r0 - 8, 8, EASE.swift));
  const scale = s * Math.pow(46 / s, go);
  const wipe = ramp(f, 0, 16, EASE.out), drift = ramp(f, 0, r0, EASE.linear);
  const hole = interpolate(go, [0.86, 0.95], [1, 0], clamp);
  if (!ready) return <AbsoluteFill style={{ background: BG }} />;
  return (
    <AbsoluteFill style={{ background: BG }}>
      <Full src={src} style={{ transform: `translate(${(60 - 120 * drift) * (1 - go)}px,0) scale(${mix(1.25, 1, ramp(f, r0, 28))})` }} />
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0, opacity: hole }}>
        <defs>
          <mask id="tm" maskUnits="userSpaceOnUse" x={0} y={0} width={1920} height={1080}>
            <rect width={1920} height={1080} fill="white" />
            <g transform={`translate(${mix(o.x, 960, go)} ${mix(o.y, 540, go)}) scale(${scale}) translate(${-o.x} ${-o.y})`}>
              <text x={960} y={540} textAnchor="middle" dominantBaseline="central" fontFamily={FONT} fontWeight={900} fontSize={size} fill="black"
                style={{ clipPath: `inset(${(1 - wipe) * 100}% 0 0 0)` }}>{word}</text>
            </g>
          </mask>
        </defs>
        <rect width={1920} height={1080} fill={BG} mask="url(#tm)" />
        {/* 화면의 어두운 곳에서도 글자가 읽히게 얇은 윤곽 */}
        <text x={960} y={540} textAnchor="middle" dominantBaseline="central" fontFamily={FONT} fontWeight={900} fontSize={size} fill="none" stroke={INK} strokeOpacity={0.45 * (1 - ramp(f, r0, 8)) * wipe} strokeWidth={3}
          transform={`translate(${o.x} ${o.y}) scale(${s}) translate(${-o.x} ${-o.y})`}>{word}</text>
      </svg>
      {sub ? <div style={{ position: 'absolute', left: 0, right: 0, top: 540 + size * 0.62, textAlign: 'center', fontFamily: FONT, fontWeight: 700, fontSize: 46, color: INK, opacity: ramp(f, 14, 14) * (1 - ramp(f, r0 - 8, 8)) }}>{sub}</div> : null}
      <div style={{ position: 'absolute', left: 860, top: 540 - size * 0.62 - 14, width: 200 * ramp(f, 8, 16), height: 8, background: accent, opacity: 1 - ramp(f, r0 - 8, 8) }} />
    </AbsoluteFill>
  );
};

// 2. CrashZoom — 화면 전체에서 한 칸으로 확 다가가 쾅 멈춘다(핵심 한 칸)
export type CrashZoomProps = { src: string; frames: number; accent: string; target: Rect; label: string; hit: number };
export const CrashZoom: React.FC<CrashZoomProps> = ({ src, frames, accent, target: r, label, hit }) => {
  const f = useCurrentFrame(); useFont();
  const h = Math.max(14, S(hit)), cx = r.x + r.w / 2, cy = r.y + r.h / 2, z = Math.min(3.2, 1150 / r.w, 620 / r.h);
  const keys: CamKey2D[] = [
    { frame: 0, cx: 960, cy: 540, zoom: 1 }, { frame: h - 10, cx: 960, cy: 540, zoom: 1.03 }, { frame: h - 6, cx: 960, cy: 540, zoom: 1 },
    { frame: h, cx, cy, zoom: z }, { frame: frames, cx, cy, zoom: z * 1.02 },
  ];
  const env = f >= h ? 14 * Math.exp(-(f - h) / 1.8) : 0; // 부딪힌 뒤 6프레임만 떨린다
  const on = ramp(f, h, 4), rip = ramp(f, h, 14, EASE.out);
  return (
    <AbsoluteFill style={{ background: BG, transform: `translate(${(env * 0.55 * Math.sin((f - h) * 2.4 + 0.6)).toFixed(2)}px, ${(env * Math.cos((f - h) * 2.9)).toFixed(2)}px)` }}>
      <PageCam2D src={src} pageH={1080} keys={keys} ease={Easing.bezier(0.6, 0, 0.9, 0.6)} bg={BG}>
        <div style={{ position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, borderRadius: 10, boxShadow: `0 0 0 3000px rgba(14,12,10,${0.62 * on})`, outline: `${Math.max(2, 7 / z)}px solid ${accent}`, outlineOffset: 3, opacity: on }} />
        <div style={{ position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, borderRadius: 10 + 20 * rip, border: `${3 / z}px solid ${accent}`, transform: `scale(${1 + 0.25 * rip})`, opacity: f < h ? 0 : 1 - rip }} />
      </PageCam2D>
      <Tag text={label} accent={accent} style={{ left: 960 - (r.w * z) / 2, top: 540 - (r.h * z) / 2 - 84, opacity: ramp(f, h + 3, 6), fontSize: 46 }} />
    </AbsoluteFill>
  );
};

// 3. TiltGlide — 기울어진 화면 위를 미끄러지며 훑는다(전체를 소개할 때). stops를 차례로 지나간다
export type TiltGlideProps = { src: string; frames: number; accent: string; stops: (Rect & { t: number; label?: string; zoom?: number })[] };
export const TiltGlide: React.FC<TiltGlideProps> = ({ src, frames, accent, stops }) => {
  const f = useCurrentFrame(); useFont();
  const at = (s: TiltGlideProps['stops'][0], frame: number, rotX: number): CamKey2D => ({ frame, cx: s.x + s.w / 2, cy: s.y + s.h / 2, zoom: s.zoom ?? 1.35, rotX, rotY: -6, rotZ: 1, persp: 1500 });
  const keys: CamKey2D[] = [{ frame: 0, cx: 960, cy: 560, zoom: 0.86, rotX: 34, rotY: 0, rotZ: -4, persp: 1500 }];
  stops.forEach((s, i) => { const a = Math.max(i ? keys[keys.length - 1].frame + 8 : 18, S(s.t) + 4); keys.push(at(s, a, 16)); const end = i + 1 < stops.length ? S(stops[i + 1].t) - 14 : frames; if (end > a + 1) keys.push(at(s, end, 14)); });
  return (
    <AbsoluteFill style={{ background: '#0c0b07' }}>
      <PageCam2D src={src} pageH={1080} keys={keys} ease={Easing.bezier(0.45, 0, 0.15, 1)} bg="#0c0b07">
        {stops.map((s, i) => {
          const on = ramp(f, Math.max(0, S(s.t) - 5), 7) * (i + 1 < stops.length ? 1 - ramp(f, S(stops[i + 1].t) - 8, 6) : 1);
          return s.label ? (
            <div key={i} style={{ position: 'absolute', left: s.x, top: s.y, width: s.w, height: s.h, opacity: on }}>
              <div style={{ position: 'absolute', inset: -5, borderRadius: 12, border: `4px solid ${accent}`, boxShadow: `0 0 24px ${accent}66` }} />
              <Tag text={s.label} accent={accent} style={{ left: -5, bottom: '100%', marginBottom: 12, fontSize: 30 }} />
            </div>) : null;
        })}
      </PageCam2D>
      <Grain opacity={0.06} blend="soft-light" />
    </AbsoluteFill>
  );
};

// 4. BeforeAfter — 손잡이를 확 끌었다가 천천히 되돌려 앞뒤 화면을 견준다
export type BeforeAfterProps = { before: string; after: string; frames: number; accent: string; beforeLabel: string; afterLabel: string; t?: number };
export const BeforeAfter: React.FC<BeforeAfterProps> = ({ before, after, accent, beforeLabel, afterLabel, t = 0.5 }) => {
  const f = useCurrentFrame(), a = S(t); useFont();
  const pos = (x: number) => x < a ? mix(8, 6.5, ramp(x, a - 4, 4, EASE.smooth)) : x < a + 12 ? mix(6.5, 78, ramp(x, a, 12, EASE.out)) : x < a + 24 ? mix(78, 72, ramp(x, a + 12, 12, EASE.smooth)) : mix(72, 50, ramp(x, a + 42, 48, EASE.smooth));
  const x = (pos(f) / 100) * 1920, vx = ((pos(f + 0.5) - pos(f - 0.5)) / 100) * 1920;
  return (
    <AbsoluteFill style={{ background: BG, overflow: 'hidden' }}>
      <Full src={before} style={{ filter: 'saturate(.55) brightness(.92)' }} />
      <Tag text={beforeLabel} accent="#d9dbe0" style={{ right: 70, bottom: 190, fontSize: 44 }} />
      <div style={{ position: 'absolute', inset: 0, clipPath: `inset(0 ${1920 - x}px 0 0)` }}>
        <Full src={after} />
        <Tag text={afterLabel} accent={accent} style={{ left: 70, bottom: 190, fontSize: 44 }} />
      </div>
      <SpeedBlur vx={vx} amount={0.12} max={14}>
        <div style={{ position: 'absolute', left: x - 3, top: 0, width: 6, height: 1080, background: '#fff', boxShadow: '0 0 30px rgba(0,0,0,.4)' }} />
        <div style={{ position: 'absolute', left: x - 42, top: 498, width: 84, height: 84, borderRadius: 42, background: '#fff', boxShadow: '0 10px 40px rgba(0,0,0,.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scaleX(${1 + Math.min(Math.abs(vx) / 110, 1) * 0.18})` }}>
          <svg width={44} height={28} viewBox="0 0 44 28"><path d="M16 4 5 14l11 10M28 4l11 10-11 10" fill="none" stroke={BG} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" /></svg>
        </div>
      </SpeedBlur>
    </AbsoluteFill>
  );
};

// 5. CardFlip — 화면이 카드처럼 뒤집혀 다음 화면이 된다(화면에서 화면으로)
// to 대신 toTitle(+toSub·toUrl)을 주면 뒷면이 이름 카드가 된다(마무리)
export type CardFlipProps = { from: string; to?: string; toTitle?: string; toSub?: string; toUrl?: string; frames: number; accent: string; t: number; fromLabel?: string; toLabel?: string };
export const CardFlip: React.FC<CardFlipProps> = ({ from, to, toTitle, toSub, toUrl, frames, accent, t, fromLabel, toLabel }) => {
  const f = useCurrentFrame(), a = S(t) - 8; useFont();
  const p = ramp(f, a, 22, EASE.smooth), sc = 0.78 - 0.05 * Math.sin(Math.PI * p) + 0.05 * (f / frames);
  const face = (src: string | undefined, back: boolean, label?: string) => (
    <div style={{ position: 'absolute', inset: 0, backfaceVisibility: 'hidden', transform: back ? 'rotateY(180deg)' : undefined, borderRadius: 26, overflow: 'hidden', boxShadow: '0 50px 140px rgba(0,0,0,.65), 0 0 0 3px rgba(255,255,255,.14)', background: '#1f1e17', fontFamily: FONT, color: INK, textAlign: 'center' }}>
      {src ? <Full src={src} /> : (
        <>
          <div style={{ position: 'absolute', left: 0, right: 0, top: 350, fontSize: 150, fontWeight: 900, letterSpacing: '-0.04em' }}>{toTitle}</div>
          <div style={{ position: 'absolute', left: 0, right: 0, top: 570, fontSize: 56, fontWeight: 700, color: MUTE }}>{toSub}</div>
          <div style={{ position: 'absolute', left: 0, right: 0, top: 690, fontSize: 46, fontWeight: 800, color: accent }}>{toUrl}</div>
        </>)}{label ? <Tag text={label} accent={accent} style={{ left: 60, bottom: 60, fontSize: 48 }} /> : null}
    </div>);
  return (
    <AbsoluteFill style={{ background: `radial-gradient(1400px 900px at 50% 45%, #2a281f 0%, ${BG} 75%)`, perspective: 2400 }}>
      <div style={{ position: 'absolute', inset: 0, top: -30, transformStyle: 'preserve-3d', transform: `scale(${sc}) rotateX(${4 * (1 - p)}deg) rotateY(${(180 * p).toFixed(2)}deg)` }}>
        {face(from, false, fromLabel)}{face(to, true, toLabel)}
      </div>
      <Grain opacity={0.05} blend="soft-light" />
    </AbsoluteFill>
  );
};

// 6. Lockup — 마지막 화면이 점으로 줄어들고 그 자리에 로고·이름·주소가 자리 잡는다(마무리)
export type LockupProps = { src: string; frames: number; accent: string; title: string; sub?: string; url?: string; note?: string; logo?: string; at?: number };
export const Lockup: React.FC<LockupProps> = ({ src, frames, accent, title, sub, url, note, logo, at = 1 }) => {
  const f = useCurrentFrame(); useFont();
  const a = Math.max(26, S(at)), z = a - 26; // at = 이름이 나오는 초(그 앞 0.87초 동안 화면이 줄어든다)
  const p = ramp(f, z + 4, 22, EASE.exit), q = ramp(f, a - 2, 16, EASE.overshoot);
  const line = (d: number): React.CSSProperties => ({ opacity: ramp(f, a + d, 10), transform: `translateY(${(1 - ramp(f, a + d, 14)) * 30}px) scale(${1 + 0.035 * Math.max(0, f - a) / frames})` }); // 끝까지 아주 느리게 다가와 멈춘 화면이 되지 않는다
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT, color: INK, textAlign: 'center' }}>
      <div style={{ position: 'absolute', inset: 0, transform: `translateY(${-200 * p}px) scale(${mix(1, 0.02, p)})`, borderRadius: 600 * p, overflow: 'hidden', opacity: f < z + 27 ? 1 : 0 }}><Full src={src} /></div>
      <div style={{ position: 'absolute', left: 960 - 80, top: 260, width: 160, height: 160, transform: `scale(${q})` }}>
        {logo ? <Img src={staticFile(logo)} style={{ width: '100%', height: '100%', objectFit: 'contain' }} /> : <div style={{ width: 64, height: 64, margin: '48px auto', borderRadius: 32, background: accent }} />}
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 450, fontSize: 128, fontWeight: 900, letterSpacing: '-0.04em', ...line(0) }}>{title}</div>
      {sub ? <div style={{ position: 'absolute', left: 0, right: 0, top: 620, fontSize: 48, fontWeight: 700, color: MUTE, ...line(8) }}>{sub}</div> : null}
      {url ? <div style={{ position: 'absolute', left: 0, right: 0, top: 720, fontSize: 40, fontWeight: 800, color: accent, ...line(16) }}>{url}</div> : null}
      {note ? <div style={{ position: 'absolute', left: 0, right: 0, top: 830, fontSize: 28, fontWeight: 500, color: MUTE, ...line(24) }}>{note}</div> : null}
      <Grain opacity={0.05} blend="soft-light" />
    </AbsoluteFill>
  );
};
