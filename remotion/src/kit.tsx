import React, { createContext, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { AbsoluteFill, cancelRender, continueRender, delayRender, Easing, Img, interpolate, random, spring, staticFile, useCurrentFrame } from "remotion";

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

export const EASE: Record<string, (t: number) => number> = {
  linear: Easing.linear,
  in: Easing.in(Easing.quad),
  out: Easing.out(Easing.quad),
  inout: Easing.inOut(Easing.quad),
  outcubic: Easing.out(Easing.cubic),
  sin: Easing.inOut(Easing.sin),
};

export const progress = (frame: number, from: number, to: number, ease = Easing.inOut(Easing.cubic)) =>
  interpolate(frame, [from, to], [0, 1], { ...clamp, easing: ease });

export const useStepped = (every = 2) => {
  const f = useCurrentFrame();
  return Math.floor(f / every) * every;
};

export const boil = (key: string, step: number, amp = 1.5) => ({
  x: (random(`${key}x${step}`) - 0.5) * 2 * amp,
  y: (random(`${key}y${step}`) - 0.5) * 2 * amp,
  r: (random(`${key}r${step}`) - 0.5) * amp * 0.3,
});

export const Tex: React.FC<{ src: string; style?: React.CSSProperties }> = ({ src, style }) => (
  <Img src={staticFile(src)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", ...style }} />
);

// Preserves Bengali word integrity & prevents glyph clipping/overflow:
// Never splits Bengali words into individual characters/vowel signs/conjuncts; wraps cleanly by word.
const hasBengali = (s: string) => /[\u0980-\u09FF]/.test(s);

export const BENGALI_DIGITS = ["০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯"];

export const toBengaliDigits = (value: string | number): string =>
  String(value).replace(/\d/g, (d) => BENGALI_DIGITS[Number(d)] ?? d);

export const fromBengaliDigits = (value: string): string =>
  value.replace(/[০-৯]/g, (d) => String(BENGALI_DIGITS.indexOf(d)));

export type ThemePalette = {
  bg: string;
  bg2: string;
  accent: string;
  accent2: string;
  text: string;
  muted: string;
  panel: string;
  grid: string;
  overlay: string;
  isLight: boolean;
};

export type SubtitleWord = { start: number; end: number; word: string };
export type SubtitleCue = {
  start: number;
  end: number;
  text: string;
  words?: SubtitleWord[];
  keywords?: string[];
};

export const getMediaEffectFilter = (effect: string | undefined, grade: string | undefined, frame: number): string => {
  const fx = (effect || "none").toLowerCase();
  if (fx === "old_footage") {
    const flicker = 0.86 + Math.sin(frame * 1.9) * 0.03 + Math.cos(frame * 0.7) * 0.02;
    return `sepia(.48) contrast(1.18) brightness(${flicker.toFixed(3)}) saturate(.72)`;
  }
  if (fx === "archival_photo") {
    return "sepia(.32) contrast(1.10) brightness(.88) saturate(.80)";
  }
  if (fx === "vhs_retro") {
    return "contrast(1.14) saturate(1.18) brightness(.88) hue-rotate(-6deg)";
  }
  if (fx === "noir_bw") {
    return "grayscale(1) contrast(1.30) brightness(.86)";
  }
  if (fx === "cctv_cam") {
    return "grayscale(.65) sepia(.25) hue-rotate(78deg) contrast(1.22) brightness(.84)";
  }
  if (fx === "dream_glow") {
    return "brightness(.96) saturate(1.12) contrast(.95)";
  }
  if (fx === "glitch_pulse") {
    const burst = frame < 8 ? 1.25 : 1.04;
    return `brightness(.86) contrast(${burst}) saturate(1.12)`;
  }
  if (grade === "warm_history") return "brightness(.84) sepia(.10) saturate(1.08) contrast(1.06)";
  if (grade === "cool_science") return "brightness(.84) saturate(.92) hue-rotate(5deg) contrast(1.08)";
  if (grade === "cinematic_teal") return "brightness(.84) saturate(1.04) contrast(1.08)";
  return "brightness(.84) saturate(.98) contrast(1.04)";
};

export const VisualEffectOverlay: React.FC<{ effect?: string; fps: number }> = ({ effect, fps }) => {
  const frame = useCurrentFrame();
  const fx = (effect || "none").toLowerCase();
  if (fx === "none") return null;

  if (fx === "old_footage") {
    const step = Math.floor(frame / 2);
    const scratchX1 = 12 + Math.floor(random(`s1-${step}`) * 76);
    const scratchX2 = 18 + Math.floor(random(`s2-${step}`) * 68);
    const showScratch2 = random(`s2v-${step}`) > 0.45;
    const dustX = 10 + Math.floor(random(`dx-${step}`) * 80);
    const dustY = 10 + Math.floor(random(`dy-${step}`) * 80);
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        {/* Aged warm film tint + heavy vintage vignette */}
        <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(255,220,160,0.06) 35%, rgba(12,8,4,0.62) 100%)" }} />
        {/* Deterministic vertical film scratches */}
        <div style={{ position: "absolute", left: `${scratchX1}%`, top: 0, bottom: 0, width: 1.5, background: "rgba(255,244,214,0.28)" }} />
        {showScratch2 && (
          <div style={{ position: "absolute", left: `${scratchX2}%`, top: "8%", bottom: "12%", width: 1, background: "rgba(20,14,8,0.38)" }} />
        )}
        {/* Vintage dust speck */}
        <div style={{ position: "absolute", left: `${dustX}%`, top: `${dustY}%`, width: 4, height: 4, borderRadius: "50%", background: "rgba(255,240,210,0.35)" }} />
        {/* Vintage grain */}
        <AbsoluteFill style={{ opacity: 0.09, backgroundImage: "repeating-radial-gradient(circle at 20% 30%, rgba(255,235,200,0.8) 0, rgba(0,0,0,0.8) 1px, transparent 2px)", backgroundSize: "5px 5px" }} />
      </AbsoluteFill>
    );
  }

  if (fx === "archival_photo") {
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <AbsoluteFill style={{ border: "26px solid rgba(240,230,210,0.14)", boxShadow: "inset 0 0 90px rgba(15,10,5,0.68)" }} />
        <AbsoluteFill style={{ opacity: 0.06, backgroundImage: "repeating-radial-gradient(circle at 30% 40%, rgba(255,245,220,0.7) 0, rgba(0,0,0,0.7) 1px, transparent 2px)", backgroundSize: "6px 6px" }} />
      </AbsoluteFill>
    );
  }

  if (fx === "vhs_retro") {
    const scanY = (frame * 9) % 1080;
    const sec = Math.floor(frame / Math.max(1, fps));
    const tc = `00:${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        {/* CRT scanlines */}
        <AbsoluteFill style={{ opacity: 0.18, backgroundImage: "repeating-linear-gradient(0deg, rgba(0,0,0,0.55) 0px, rgba(0,0,0,0.55) 1px, transparent 1px, transparent 4px)" }} />
        {/* Rolling VHS tracking bar */}
        <div style={{ position: "absolute", left: 0, right: 0, top: scanY, height: 18, background: "linear-gradient(180deg, transparent, rgba(255,255,255,0.14), transparent)" }} />
        {/* Safe-zone retro REC indicator */}
        <div style={{ position: "absolute", left: 96, bottom: 58, fontFamily: "monospace", fontSize: 20, fontWeight: 700, color: "rgba(255,255,255,0.78)", textShadow: "2px 0 rgba(255,0,80,0.55), -2px 0 rgba(0,220,255,0.55)" }}>
          ● PLAY {tc}
        </div>
      </AbsoluteFill>
    );
  }

  if (fx === "noir_bw") {
    return (
      <AbsoluteFill style={{ pointerEvents: "none", background: "radial-gradient(ellipse at center, transparent 42%, rgba(0,0,0,0.72) 100%)" }} />
    );
  }

  if (fx === "cctv_cam") {
    const blink = Math.floor(frame / Math.max(1, Math.round(fps / 2))) % 2 === 0;
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <AbsoluteFill style={{ opacity: 0.16, backgroundImage: "repeating-linear-gradient(0deg, rgba(0,25,10,0.6) 0px, rgba(0,25,10,0.6) 1px, transparent 1px, transparent 3px)" }} />
        {/* Corner surveillance brackets inside 5% safe zone */}
        <div style={{ position: "absolute", left: 96, top: 54, width: 34, height: 34, borderLeft: "3px solid rgba(167,243,208,0.7)", borderTop: "3px solid rgba(167,243,208,0.7)" }} />
        <div style={{ position: "absolute", right: 96, top: 54, width: 34, height: 34, borderRight: "3px solid rgba(167,243,208,0.7)", borderTop: "3px solid rgba(167,243,208,0.7)" }} />
        <div style={{ position: "absolute", left: 96, bottom: 54, width: 34, height: 34, borderLeft: "3px solid rgba(167,243,208,0.7)", borderBottom: "3px solid rgba(167,243,208,0.7)" }} />
        <div style={{ position: "absolute", right: 96, bottom: 54, width: 34, height: 34, borderRight: "3px solid rgba(167,243,208,0.7)", borderBottom: "3px solid rgba(167,243,208,0.7)" }} />
        <div style={{ position: "absolute", left: 112, top: 64, fontFamily: "monospace", fontSize: 18, fontWeight: 700, color: "rgba(167,243,208,0.85)" }}>
          {blink ? "● REC" : "  REC"} · CAM-01
        </div>
      </AbsoluteFill>
    );
  }

  if (fx === "dream_glow") {
    const shift = Math.sin(frame / Math.max(1, fps)) * 8;
    return (
      <AbsoluteFill
        style={{
          pointerEvents: "none",
          background: `radial-gradient(circle at ${22 + shift}% 24%, rgba(255,210,140,0.22), transparent 52%), radial-gradient(circle at ${78 - shift}% 74%, rgba(160,210,255,0.16), transparent 55%)`,
          mixBlendMode: "screen",
        }}
      />
    );
  }

  if (fx === "glitch_pulse") {
    if (frame > 10) return null;
    const bandTop = 180 + (frame * 77) % 620;
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: bandTop, height: 22, background: "rgba(34,211,238,0.28)", transform: `translateX(${frame % 2 === 0 ? 12 : -12}px)` }} />
        <div style={{ position: "absolute", left: 0, right: 0, top: bandTop + 18, height: 12, background: "rgba(244,63,94,0.28)", transform: `translateX(${frame % 2 === 0 ? -10 : 10}px)` }} />
      </AbsoluteFill>
    );
  }

  return null;
};

export const computeCameraTransform = (
  preset: string | undefined,
  frame: number,
  len: number,
  fps: number,
  fallbackZoom = 0.045
): string => {
  const safeLen = Math.max(1, len);
  const p = interpolate(frame, [0, safeLen], [0, 1], { ...clamp, easing: Easing.inOut(Easing.quad) });
  const key = (preset || "CAM-PUSH").toUpperCase();

  switch (key) {
    case "CAM-PULL": {
      const s = interpolate(p, [0, 1], [1.08, 1.0]);
      return `scale(${s.toFixed(4)})`;
    }
    case "CAM-PAN-L": {
      const tx = interpolate(p, [0, 1], [28, -28]);
      return `scale(1.06) translate3d(${tx.toFixed(2)}px, 0px, 0)`;
    }
    case "CAM-PAN-R": {
      const tx = interpolate(p, [0, 1], [-28, 28]);
      return `scale(1.06) translate3d(${tx.toFixed(2)}px, 0px, 0)`;
    }
    case "CAM-DRIFT": {
      const s = 1.03 + Math.sin(p * Math.PI * 2) * 0.012;
      const tx = Math.sin(p * Math.PI * 2) * 10;
      const ty = Math.cos(p * Math.PI * 2) * 7;
      return `scale(${s.toFixed(4)}) translate3d(${tx.toFixed(2)}px, ${ty.toFixed(2)}px, 0)`;
    }
    case "CAM-PUNCH": {
      const upEnd = Math.max(2, Math.round(fps * 0.1));
      const downEnd = Math.max(upEnd + 3, Math.round(fps * 0.35));
      const punch =
        frame <= upEnd
          ? interpolate(frame, [0, upEnd], [1.0, 1.055], { ...clamp, easing: Easing.out(Easing.cubic) })
          : interpolate(frame, [upEnd, downEnd], [1.055, 1.015], { ...clamp, easing: Easing.out(Easing.quad) });
      const slow = interpolate(p, [0, 1], [0, 0.03]);
      return `scale(${(punch + slow).toFixed(4)})`;
    }
    case "CAM-SHAKE": {
      const shakeFrames = Math.max(6, Math.round(fps * 0.4));
      const decay = interpolate(frame, [0, shakeFrames], [1, 0], clamp);
      const sx = Math.sin(frame * 2.7) * 9 * decay;
      const sy = Math.cos(frame * 3.3) * 6 * decay;
      const s = 1.04 + p * 0.03;
      return `scale(${s.toFixed(4)}) translate3d(${sx.toFixed(2)}px, ${sy.toFixed(2)}px, 0)`;
    }
    case "CAM-PUSH":
    default: {
      const s = 1.0 + Math.max(0.04, fallbackZoom * 1.4) * p;
      return `scale(${s.toFixed(4)})`;
    }
  }
};

export const computeTransitionStyle = (
  transition: string | undefined,
  frame: number,
  len: number,
  fps: number,
  durationSec = 0.35
): { style: React.CSSProperties; flashOpacity: number } => {
  const tr = (transition || "TR-CUT").toUpperCase();
  const trFrames = Math.max(4, Math.min(Math.floor(len / 3), Math.round(durationSec * fps)));

  if (tr === "TR-DISSOLVE") {
    const op = interpolate(frame, [0, trFrames], [0.0, 1.0], clamp);
    return { style: { opacity: op }, flashOpacity: 0 };
  }
  if (tr === "TR-FADEBLACK") {
    const inOp = interpolate(frame, [0, trFrames], [0.0, 1.0], clamp);
    const outOp = interpolate(frame, [Math.max(trFrames, len - trFrames), len], [1.0, 0.0], clamp);
    return { style: { opacity: Math.min(inOp, outOp) }, flashOpacity: 0 };
  }
  if (tr === "TR-WHIP") {
    const whipFrames = Math.max(4, Math.round(fps * 0.25));
    const tx = interpolate(frame, [0, whipFrames], [140, 0], { ...clamp, easing: Easing.out(Easing.cubic) });
    const op = interpolate(frame, [0, Math.max(2, Math.floor(whipFrames / 2))], [0.35, 1.0], clamp);
    return { style: { opacity: op, transform: `translate3d(${tx.toFixed(1)}px, 0, 0)` }, flashOpacity: 0 };
  }
  if (tr === "TR-WIPE") {
    const pct = interpolate(frame, [0, trFrames], [100, 0], { ...clamp, easing: Easing.out(Easing.quad) });
    return { style: { clipPath: `inset(0 ${pct.toFixed(1)}% 0 0)` }, flashOpacity: 0 };
  }
  if (tr === "TR-ZOOMTHRU") {
    const s = interpolate(frame, [0, trFrames], [1.14, 1.0], { ...clamp, easing: Easing.out(Easing.cubic) });
    const op = interpolate(frame, [0, trFrames], [0.15, 1.0], clamp);
    return { style: { opacity: op, transform: `scale(${s.toFixed(4)})` }, flashOpacity: 0 };
  }
  if (tr === "TR-FLASH") {
    const flashOpacity = frame < 2 ? 0.85 : interpolate(frame, [2, 6], [0.4, 0], clamp);
    return { style: {}, flashOpacity };
  }
  return { style: {}, flashOpacity: 0 };
};

export const AnimatedPresetCard: React.FC<{
  preset?: string;
  tag?: string;
  headline?: string;
  items?: string[];
  position?: string;
  theme: ThemePalette;
  fps: number;
  fontFamily: string;
}> = ({ preset, tag, headline, items = [], position = "left", theme, fps, fontFamily }) => {
  const frame = useCurrentFrame();
  const key = (preset || "HDR-DROP").toUpperCase();
  const alignRight = position === "right";
  const baseStyle: React.CSSProperties = {
    position: "absolute",
    left: alignRight ? "auto" : 96,
    right: alignRight ? 96 : "auto",
    top: 86,
    maxWidth: 1120,
    textAlign: alignRight ? "right" : "left",
    fontFamily,
  };

  if (key === "TAG-WIPE") {
    const wipe = interpolate(frame, [0, Math.round(fps * 0.35)], [100, 0], { ...clamp, easing: Easing.out(Easing.cubic) });
    const barScale = interpolate(frame, [0, Math.round(fps * 0.2)], [0, 1], clamp);
    return (
      <div style={baseStyle}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 14, flexDirection: alignRight ? "row-reverse" : "row" }}>
          <div style={{ width: 6, height: 68, background: theme.accent, transform: `scaleY(${barScale})`, transformOrigin: "top" }} />
          <div style={{ clipPath: `inset(0 ${wipe.toFixed(1)}% 0 0)` }}>
            {tag && <div style={{ fontSize: 22, fontWeight: 700, color: theme.accent, marginBottom: 4 }}>{tag}</div>}
            {headline && <div style={{ fontSize: 50, fontWeight: 700, lineHeight: 1.32, color: theme.text, textShadow: "0 4px 20px rgba(0,0,0,.65)" }}>{headline}</div>}
          </div>
        </div>
        {items.length > 0 && (
          <div style={{ marginTop: 22, display: "flex", gap: 14, flexWrap: "wrap", justifyContent: alignRight ? "flex-end" : "flex-start", opacity: interpolate(frame, [8, 18], [0, 1], clamp) }}>
            {items.slice(0, 3).map((x, i) => (
              <div key={i} style={{ fontSize: 24, lineHeight: 1.35, color: theme.text, padding: "10px 20px", background: theme.panel, borderLeft: `4px solid ${theme.accent}`, borderRadius: 6 }}>{x}</div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (key === "NUM-ROLL") {
    const rawNumMatch = fromBengaliDigits(`${headline || ""} ${items.join(" ")}`).match(/\d[\d,.]*/);
    const targetNum = rawNumMatch ? parseFloat(rawNumMatch[0].replace(/,/g, "")) : 100;
    const rollP = interpolate(frame, [0, Math.round(fps * 0.9)], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
    const currentVal = Math.round(targetNum * rollP);
    const popScale = frame > Math.round(fps * 0.9)
      ? 1 + Math.sin(Math.min(1, (frame - fps * 0.9) / 8) * Math.PI) * 0.08
      : 1;
    return (
      <div style={baseStyle}>
        {tag && <div style={{ display: "inline-block", background: theme.accent, color: "#fff", padding: "7px 18px", borderRadius: 4, fontSize: 22, fontWeight: 700, marginBottom: 14 }}>{tag}</div>}
        <div style={{ fontSize: 82, fontWeight: 700, lineHeight: 1.2, color: theme.accent, transform: `scale(${popScale.toFixed(3)})`, transformOrigin: alignRight ? "right center" : "left center", textShadow: `0 6px 28px rgba(0,0,0,.65)` }}>
          {toBengaliDigits(currentVal)}
        </div>
        {headline && <div style={{ fontSize: 44, fontWeight: 700, lineHeight: 1.35, color: theme.text, marginTop: 8, textShadow: "0 4px 18px rgba(0,0,0,.65)" }}>{headline}</div>}
        {items.length > 0 && (
          <div style={{ marginTop: 22, display: "flex", gap: 14, flexWrap: "wrap", justifyContent: alignRight ? "flex-end" : "flex-start" }}>
            {items.slice(0, 3).map((x, i) => (
              <div key={i} style={{ fontSize: 24, lineHeight: 1.35, color: theme.text, padding: "10px 20px", background: theme.panel, borderLeft: `4px solid ${theme.accent}`, borderRadius: 6 }}>{x}</div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (key === "BIG-STAMP") {
    const stampScale = interpolate(frame, [0, Math.round(fps * 0.25)], [1.55, 1.0], { ...clamp, easing: Easing.out(Easing.cubic) });
    const stampOp = interpolate(frame, [0, Math.round(fps * 0.2)], [0, 1], clamp);
    const glow = 14 + Math.sin((frame / fps) * Math.PI * 2) * 8;
    return (
      <div style={{ ...baseStyle, opacity: stampOp, transform: `scale(${stampScale.toFixed(3)})`, transformOrigin: alignRight ? "right top" : "left top" }}>
        {tag && <div style={{ display: "inline-block", background: theme.accent, color: "#fff", padding: "8px 20px", borderRadius: 4, fontSize: 23, fontWeight: 700, marginBottom: 16 }}>{tag}</div>}
        {headline && (
          <div style={{ fontSize: 64, fontWeight: 700, lineHeight: 1.32, color: theme.text, textShadow: `0 0 ${glow.toFixed(1)}px ${theme.accent}, 0 6px 24px rgba(0,0,0,.75)` }}>
            {headline}
          </div>
        )}
      </div>
    );
  }

  if (key === "QUOTE-STAGGER") {
    const words = (headline || "").normalize("NFC").split(/\s+/).filter(Boolean);
    return (
      <div style={{ ...baseStyle, background: theme.panel, padding: "28px 34px", borderRadius: 12, borderLeft: `6px solid ${theme.accent}` }}>
        {tag && <div style={{ fontSize: 22, fontWeight: 700, color: theme.accent, marginBottom: 12 }}>{tag}</div>}
        <div style={{ fontSize: 44, fontWeight: 600, lineHeight: 1.42, color: theme.text, letterSpacing: 0 }}>
          {words.map((w, i) => {
            const startF = i * Math.max(2, Math.round(fps * 0.08));
            const op = interpolate(frame, [startF, startF + 6], [0, 1], clamp);
            const ty = interpolate(frame, [startF, startF + 6], [16, 0], { ...clamp, easing: Easing.out(Easing.quad) });
            return (
              <span key={i} style={{ display: "inline-block", marginRight: 12, opacity: op, transform: `translateY(${ty.toFixed(1)}px)` }}>
                {w}
              </span>
            );
          })}
        </div>
      </div>
    );
  }

  if (key === "CTA-STAGGER") {
    const pulse = 1 + Math.sin((frame / fps) * Math.PI * 1.6) * 0.035;
    return (
      <div style={{ ...baseStyle, left: 96, right: 96, textAlign: "center", top: 220, maxWidth: "none" }}>
        {headline && (
          <div style={{ fontSize: 56, fontWeight: 700, lineHeight: 1.35, color: theme.text, opacity: interpolate(frame, [0, 10], [0, 1], clamp), transform: `translateY(${interpolate(frame, [0, 10], [26, 0], clamp)}px)`, textShadow: "0 4px 20px rgba(0,0,0,.65)" }}>
            {headline}
          </div>
        )}
        <div style={{ marginTop: 28, display: "inline-flex", gap: 16, flexWrap: "wrap", justifyContent: "center" }}>
          {(items.length ? items : ["সাবস্ক্রাইব করুন", "লাইক ও শেয়ার করুন"]).slice(0, 3).map((x, i) => {
            const st = 8 + i * 5;
            const op = interpolate(frame, [st, st + 8], [0, 1], clamp);
            return (
              <div key={i} style={{ opacity: op, transform: i === 0 ? `scale(${pulse.toFixed(3)})` : undefined, background: i === 0 ? theme.accent : theme.panel, color: i === 0 ? "#fff" : theme.text, padding: "14px 28px", borderRadius: 999, fontSize: 26, fontWeight: 700, boxShadow: i === 0 ? `0 0 24px ${theme.accent}` : "none" }}>
                {x}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  const sp = spring({ frame, fps, config: { damping: 14, stiffness: 150, mass: 0.8 } });
  const dropY = interpolate(sp, [0, 1], [-36, 0]);
  const dropScale = interpolate(sp, [0, 1], [0.92, 1.0]);
  const shinePos = interpolate(frame, [6, Math.round(fps * 0.75)], [-40, 140], clamp);
  return (
    <div style={{ ...baseStyle, opacity: interpolate(frame, [0, 10], [0, 1], clamp), transform: `translateY(${dropY.toFixed(1)}px) scale(${dropScale.toFixed(3)})`, transformOrigin: alignRight ? "right top" : "left top" }}>
      {tag && (
        <div style={{ position: "relative", overflow: "hidden", display: "inline-block", background: theme.accent, padding: "9px 22px", fontSize: 24, fontWeight: 700, color: "#fff", borderRadius: 6, marginBottom: 18 }}>
          <span>{tag}</span>
          <div style={{ position: "absolute", inset: 0, background: `linear-gradient(110deg, transparent ${shinePos - 18}%, rgba(255,255,255,0.45) ${shinePos}%, transparent ${shinePos + 18}%)`, pointerEvents: "none" }} />
        </div>
      )}
      {headline && (
        <div style={{ fontSize: 56, lineHeight: 1.35, fontWeight: 700, color: theme.text, textShadow: "0 4px 22px rgba(0,0,0,.65)", maxWidth: 1120, letterSpacing: 0 }}>
          {headline}
        </div>
      )}
      {items.length > 0 && (
        <div style={{ marginTop: 26, display: "flex", gap: 16, flexWrap: "wrap", justifyContent: alignRight ? "flex-end" : "flex-start" }}>
          {items.slice(0, 3).map((x, i) => {
            const itemOp = interpolate(frame, [6 + i * 4, 14 + i * 4], [0, 1], clamp);
            return (
              <div key={i} style={{ opacity: itemOp, fontSize: 25, lineHeight: 1.35, color: theme.text, padding: "11px 22px", background: theme.panel, borderLeft: `4px solid ${theme.accent}`, borderRadius: 6, backdropFilter: "blur(8px)" }}>
                {x}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export const KaraokeSubtitleBar: React.FC<{
  subtitles: SubtitleCue[];
  fps: number;
  theme: ThemePalette;
  fontFamily: string;
}> = ({ subtitles, fps, theme, fontFamily }) => {
  const frame = useCurrentFrame();
  const nowSec = frame / fps;
  const active = subtitles.find((s) => nowSec >= s.start && nowSec < s.end);
  if (!active) return null;

  const cueStartF = Math.floor(active.start * fps);
  const cueEndF = Math.ceil(active.end * fps);
  const boxIn = interpolate(frame, [cueStartF, cueStartF + 6], [0.92, 1.0], clamp);
  const boxOp = Math.min(
    interpolate(frame, [cueStartF, cueStartF + 5], [0, 1], clamp),
    interpolate(frame, [Math.max(cueStartF + 5, cueEndF - 5), cueEndF], [1, 0], clamp)
  );

  const words: SubtitleWord[] =
    active.words && active.words.length > 0
      ? active.words
      : active.text
          .normalize("NFC")
          .split(/\s+/)
          .filter(Boolean)
          .map((w, i, arr) => {
            const span = Math.max(0.1, active.end - active.start);
            const step = span / arr.length;
            return { start: active.start + i * step, end: active.start + (i + 1) * step, word: w };
          });

  const PAGE_SIZE = 10;
  let activeIdx = words.findIndex((w) => nowSec >= w.start && nowSec <= w.end);
  if (activeIdx === -1) {
    activeIdx = words.reduce((acc, w, i) => (nowSec >= w.start ? i : acc), 0);
  }
  const pageStart = Math.floor(activeIdx / PAGE_SIZE) * PAGE_SIZE;
  const visibleWords = words.slice(pageStart, pageStart + PAGE_SIZE);
  const keywordSet = new Set((active.keywords || []).map((k) => k.normalize("NFC").trim()));

  return (
    <div
      style={{
        position: "absolute",
        left: 160,
        right: 160,
        bottom: 58,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          opacity: boxOp,
          transform: `scale(${boxIn.toFixed(3)})`,
          background: theme.panel,
          border: `1px solid ${theme.grid}`,
          borderRadius: 16,
          padding: "14px 28px",
          maxWidth: 1480,
          textAlign: "center",
          fontFamily,
          fontSize: 33,
          fontWeight: 600,
          lineHeight: 1.38,
          letterSpacing: 0,
          wordBreak: "keep-all",
          overflowWrap: "break-word",
          fontFeatureSettings: '"kern" 1, "liga" 1, "calt" 1',
          boxShadow: "0 10px 30px rgba(0,0,0,0.45)",
        }}
      >
        {visibleWords.map((w, i) => {
          const cleanWord = w.word.normalize("NFC");
          const wStartF = Math.floor(w.start * fps);
          const p = interpolate(frame, [wStartF, wStartF + 6], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
          const isCurrent = nowSec >= w.start && nowSec <= w.end + 0.08;
          const stripped = cleanWord.replace(/[।.,!?;:'"()[\]{}]/g, "");
          const isKeyword = keywordSet.has(cleanWord) || keywordSet.has(stripped);
          const opacity = frame < wStartF ? 0.32 : interpolate(p, [0, 1], [0.35, 1.0]);
          const ty = frame < wStartF ? 8 : interpolate(p, [0, 1], [8, 0]);
          const kwScale = isKeyword && isCurrent ? 1.12 : isCurrent ? 1.04 : 1.0;

          return (
            <span
              key={`${pageStart + i}-${cleanWord}`}
              style={{
                display: "inline-block",
                marginRight: 10,
                opacity,
                color: isKeyword ? theme.accent : isCurrent ? theme.text : theme.muted,
                transform: `translateY(${ty.toFixed(1)}px) scale(${kwScale.toFixed(3)})`,
                textShadow: isKeyword
                  ? `0 0 14px ${theme.accent}, 0 2px 6px rgba(0,0,0,0.85)`
                  : "0 2px 8px rgba(0,0,0,0.85)",
              }}
            >
              {cleanWord}
            </span>
          );
        })}
      </div>
    </div>
  );
};

export const Typed: React.FC<{ text: string; from: number; cps?: number; style?: React.CSSProperties }> = ({
  text,
  from,
  cps = 2,
  style,
}) => {
  const frame = useCurrentFrame();
  const normalized = useMemo(() => text.normalize("NFC"), [text]);

  if (hasBengali(normalized)) {
    const tokens = normalized.split(/(\s+)/);
    const wordsPerSec = Math.max(2.5, cps * 1.4);
    const totalWords = tokens.filter((t) => t.trim().length > 0).length;
    const revealedWords = Math.max(0, Math.min(totalWords, Math.floor(((frame - from) / 30) * wordsPerSec) + 1));
    let seen = 0;
    return (
      <div
        style={{
          whiteSpace: "pre-wrap",
          wordBreak: "keep-all",
          overflowWrap: "break-word",
          fontFeatureSettings: '"kern" 1, "liga" 1, "calt" 1',
          ...style,
          letterSpacing: 0,
        }}
      >
        {tokens.map((tok, i) => {
          if (!tok.trim()) return <span key={i}>{tok}</span>;
          seen += 1;
          const visible = frame >= from && seen <= revealedWords;
          return (
            <span key={i} style={{ opacity: visible ? 1 : 0, display: "inline" }}>
              {tok}
            </span>
          );
        })}
      </div>
    );
  }

  const units = Array.from(normalized);
  const n = Math.max(0, Math.min(units.length, Math.floor((frame - from) * cps)));
  return (
    <div style={{ whiteSpace: "pre-wrap", ...style }}>
      {units.slice(0, n).join("")}
      <span style={{ opacity: 0 }}>{units.slice(n).join("")}</span>
    </div>
  );
};

type Pt = number[];
export type Layer = { id: string; x: number; y: number; w: number; h: number; kind: string; strokes: Pt[][]; reveal?: number };
const Layers = createContext<Record<string, Layer>>({});
export const LayersProvider: React.FC<{ layers: Layer[]; children: React.ReactNode }> = ({ layers, children }) => (
  <Layers.Provider value={Object.fromEntries(layers.map((l) => [l.id, l]))}>{children}</Layers.Provider>
);

const pathLen = (pts: Pt[]) => pts.slice(1).reduce((s, p, i) => s + Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]), 0);

const images = new Map<string, Promise<HTMLImageElement>>();
const loaded = new Map<string, HTMLImageElement>();
const load = (src: string) => {
  if (!images.has(src)) {
    images.set(
      src,
      new Promise((res, rej) => {
        const im = new Image();
        im.onload = () => {
          loaded.set(src, im);
          res(im);
        };
        im.onerror = () => rej(new Error(`could not load ${src}`));
        im.src = src;
      })
    );
  }
  return images.get(src)!;
};

export const BrushLayer: React.FC<{
  id: string;
  from: number;
  to: number;
  until?: number;
  ease?: string;
  boilEvery?: number;
}> = ({ id, from, to, until = Infinity, ease = "inout", boilEvery = 8 }) => {
  const frame = useCurrentFrame();
  const l = useContext(Layers)[id];
  const srcs = useMemo(() => [1, 2, 3].map((s) => staticFile(`brush/a_${id}_${s}.png`)), [id]);
  const [handle] = useState(() => delayRender(`brush ${id}`));
  const [ready, setReady] = useState(false);
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    Promise.all(srcs.map(load)).then(
      () => {
        setReady(true);
        continueRender(handle);
      },
      (e) => cancelRender(e)
    );
  }, [srcs, handle]);

  const p = !l ? 0 : to <= from ? (frame >= from ? 1 : 0) : progress(frame, from, to, EASE[ease] ?? EASE.inout);
  const visible = ready && p > 0 && frame < until;
  const seed = Math.floor(frame / boilEvery) % 3;

  useLayoutEffect(() => {
    const c = ref.current;
    if (!c || !l) return;
    const ctx = c.getContext("2d")!;
    ctx.clearRect(0, 0, l.w, l.h);
    const im = loaded.get(srcs[seed]);
    if (!visible || !im) return;
    ctx.globalCompositeOperation = "source-over";
    ctx.drawImage(im, 0, 0, l.w, l.h);
    if (p >= 1) return;
    ctx.globalCompositeOperation = "destination-in";
    ctx.lineWidth = l.reveal ?? 60;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "#000";
    const lens = l.strokes.map(pathLen);
    let budget = p * lens.reduce((a, b) => a + b, 0);
    ctx.beginPath();
    l.strokes.forEach((pts, i) => {
      const show = Math.max(0, Math.min(lens[i], budget));
      budget -= lens[i];
      if (show <= 0) return;
      let left = show;
      ctx.moveTo(pts[0][0], pts[0][1]);
      for (let k = 1; k < pts.length && left > 0; k++) {
        const [x0, y0] = pts[k - 1],
          [x1, y1] = pts[k];
        const seg = Math.hypot(x1 - x0, y1 - y0) || 1e-6;
        const f = Math.min(1, left / seg);
        ctx.lineTo(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f);
        left -= seg;
      }
      if (show < 1) ctx.lineTo(pts[0][0] + 0.1, pts[0][1]);
    });
    ctx.stroke();
    ctx.globalCompositeOperation = "source-over";
  });

  if (!l) return null;
  return <canvas ref={ref} width={l.w} height={l.h} style={{ position: "absolute", left: l.x, top: l.y }} />;
};
