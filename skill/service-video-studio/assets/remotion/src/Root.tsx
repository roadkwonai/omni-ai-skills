import React from 'react';
import { Composition } from 'remotion';
import { SpotTour } from './SpotTour';
import { BeforeAfter, CardFlip, CrashZoom, Lockup, TextMask, TiltGlide } from './Shots';
import { PORTED } from './ported';
import tours from '../tours.json';

// tours.json의 이름마다 샷 하나("shot" 생략 = SpotTour), ported.tsx는 add_shot.py가 가져온 원본 샷:
//   npx remotion render src/index.ts <이름> ../assets/clips/<이름>.mp4
const SHOTS: Record<string, React.FC<any>> = { SpotTour, TextMask, CrashZoom, TiltGlide, BeforeAfter, CardFlip, Lockup };
const box = { fps: 30, width: 1920, height: 1080 };
export const Root: React.FC = () => (
  <>
    {Object.entries(tours as Record<string, any>).map(([id, t]) => (
      <Composition key={id} id={id} component={SHOTS[t.shot ?? 'SpotTour']} durationInFrames={t.frames} {...box} defaultProps={t} />
    ))}
    {PORTED.map(([id, C, frames]) => <Composition key={id} id={id} component={C} durationInFrames={frames} {...box} />)}
  </>
);
