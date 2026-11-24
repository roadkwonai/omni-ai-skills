// SpotTour — video-shotcraft spotlight-hero-card(Apache-2.0)를 바탕으로 만든 '말하는 칸을 비추는' 공용 샷.
// props: 화면 이미지, 길이, 칸 목록(페이지 좌표, 시작 초, 이름표, 떠오름, 확대 배율).
// 문법: 꺼진 극장 조명 → 말하는 단어보다 0.17초 먼저 그 칸 모양으로 빛 → 칸이 살짝 떠오름(그림자) + 주황 테두리 + 이름표,
//       카메라는 약한 3D 기울기로 지금 칸을 따라감.
import React from 'react';
import { AbsoluteFill, interpolate, staticFile, useCurrentFrame, Easing, continueRender, delayRender } from 'remotion';
import { PageCam2D, CamKey2D } from './PageCam2D';
import { EASE, Grain } from './Polish';

export type TourStop = { x: number; y: number; w: number; h: number; t: number; label: string; lift?: boolean; zoom?: number };
export type SpotTourProps = { src: string; frames: number; stops: TourStop[]; startZoom?: number; accent?: string };

/* 강조색은 tours.json의 accent */
const FONT = '"Pretendard Variable", Pretendard, sans-serif';
const clampOpt = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
const LEAD = 5;

export const SpotTour: React.FC<SpotTourProps> = ({ src, frames, stops, startZoom = 0.96, accent = '#ff6600' }) => {
  const frame = useCurrentFrame();
  const [handle] = React.useState(() => delayRender('font'));
  React.useEffect(() => {
    const f = new FontFace('Pretendard Variable', `url(${staticFile('PretendardVariable.woff2')})`);
    f.load().then((ff) => { document.fonts.add(ff); continueRender(handle); }).catch(() => continueRender(handle));
  }, [handle]);

  const S = (sec: number) => Math.round(sec * 30);
  const fIn = (i: number) => Math.max(8, S(stops[i].t) - LEAD);
  const fOut = (i: number) => (i + 1 < stops.length ? fIn(i + 1) : frames);
  const onAmt = (i: number) =>
    interpolate(frame, [fIn(i), fIn(i) + 6, fOut(i), fOut(i) + 6], [0, 1, 1, 0], { ...clampOpt, easing: EASE.smooth });
  const camFor = (s: TourStop, f: number): CamKey2D => {
    const zoom = s.zoom ?? (s.w > 1000 ? 1.12 : s.w > 400 ? 1.45 : 1.75);
    return { frame: f, cx: s.x + s.w / 2, cy: s.y + s.h / 2 - 10, zoom, rotX: 9, rotY: 7, rotZ: 0.5, persp: 1400 };
  };
  const keys: CamKey2D[] = [
    { frame: 0, cx: 960, cy: 560, zoom: startZoom, rotX: 0, rotY: 0, rotZ: 0, persp: 1400 },
    { frame: Math.max(1, fIn(0) - 4), cx: 960, cy: 580, zoom: startZoom + 0.04, rotX: 5, rotY: 4, rotZ: 0, persp: 1400 },
  ];
  stops.forEach((s, i) => {
    const a = fIn(i) + 12; const b = Math.max(a + 1, fOut(i) - 2);
    keys.push(camFor(s, a)); keys.push(camFor(s, b));
  });
  if (keys[keys.length - 1].frame < frames) keys.push(camFor(stops[stops.length - 1], frames));

  const lamp = interpolate(frame, [1, 3, 4, 6], [0, 1, 0.62, 1], clampOpt);
  const anyOn = Math.max(...stops.map((_, i) => onAmt(i)));
  const preDark = interpolate(frame, [6, fIn(0)], [0.5, 0.86], clampOpt);

  return (
    <AbsoluteFill style={{ backgroundColor: '#0c0b07' }}>
      <PageCam2D src={src} pageH={1080} keys={keys} ease={Easing.bezier(0.33, 0, 0.2, 1)} bg="#0c0b07">
        <svg width={1920} height={1080} style={{ position: 'absolute', left: 0, top: 0, transform: 'translateZ(1px)' }}>
          <defs>
            <filter id="t" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="12" /></filter>
            <filter id="w" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="36" /></filter>
            {stops.map((s, i) => (
              <mask key={i} id={`m${i}`} maskUnits="userSpaceOnUse" x={0} y={0} width={1920} height={1080}>
                <rect x={0} y={0} width={1920} height={1080} fill="white" />
                <rect x={s.x - 32} y={s.y - 26} width={s.w + 64} height={s.h + 52} rx={36} fill="#2a2a2a" filter="url(#w)" />
                <rect x={s.x - 8} y={s.y - 8} width={s.w + 16} height={s.h + 16} rx={14} fill="black" filter="url(#t)" />
              </mask>
            ))}
          </defs>
          <rect x={0} y={0} width={1920} height={1080} fill="rgb(14,12,10)" fillOpacity={preDark * (1 - anyOn) * lamp} />
          {stops.map((_, i) => {
            const a = onAmt(i);
            return a > 0.001 ? <rect key={i} x={0} y={0} width={1920} height={1080} fill="rgb(14,12,10)" fillOpacity={0.86 * a} mask={`url(#m${i})`} /> : null;
          })}
        </svg>
        <div style={{ transformStyle: 'preserve-3d' }}>
          {stops.map((s, i) => {
            const a = onAmt(i);
            if (a < 0.001) return null;
            const rise = interpolate(frame, [fIn(i), fIn(i) + 9], [0, 1], { ...clampOpt, easing: Easing.bezier(0.2, 1.25, 0.3, 1) });
            const lift = (s.lift ? 30 : 0) * rise * a;
            const tag = interpolate(frame, [fIn(i) + 3, fIn(i) + 9], [0, 1], clampOpt) * a;
            const tagSize = Math.round(42 / (s.zoom ?? (s.w > 1000 ? 1.12 : s.w > 400 ? 1.45 : 1.75)));
            return (
              <div key={i} style={{ position: 'absolute', left: s.x, top: s.y, width: s.w, height: s.h, transform: `translateZ(${(2 + lift).toFixed(2)}px)`, transformStyle: 'preserve-3d' }}>
                {s.lift ? (
                  <div style={{ position: 'absolute', inset: 0, borderRadius: 8, overflow: 'hidden', opacity: a,
                    boxShadow: `${-6 * rise}px ${10 * rise}px ${22 * rise}px rgba(0,0,0,${0.45 * a})`,
                    backgroundImage: `url(${staticFile(src)})`, backgroundSize: '1920px 1080px', backgroundPosition: `-${s.x}px -${s.y}px` }} />
                ) : null}
                <div style={{ position: 'absolute', inset: -4, borderRadius: 12, border: `${Math.max(2, Math.round(tagSize / 7))}px solid ${accent}`, opacity: a, boxShadow: `0 0 24px ${accent}73` }} />
                <div style={{ position: 'absolute', left: -4, bottom: '100%', marginBottom: 8, transform: `translateY(${((1 - tag) * 8).toFixed(1)}px)`, opacity: tag,
                  background: accent, color: '#131209', fontFamily: FONT, fontWeight: 800, fontSize: tagSize, letterSpacing: '-0.02em', padding: `${Math.round(tagSize / 5)}px ${Math.round(tagSize / 1.8)}px`, borderRadius: 6, whiteSpace: 'nowrap' }}>{s.label}</div>
              </div>
            );
          })}
        </div>
      </PageCam2D>
      <AbsoluteFill style={{ background: 'rgb(14,12,10)', opacity: 0.85 * (1 - lamp) }} />
      <Grain opacity={0.06} blend="soft-light" />
    </AbsoluteFill>
  );
};
