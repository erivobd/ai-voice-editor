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

const TEXT_SHADOW_CRISP = "0 3px 16px rgba(0,0,0,0.88), 0 1px 4px rgba(0,0,0,0.95)";

export const getMediaEffectFilter = (effect: string | undefined, grade: string | undefined, frame: number): string => {
  const fx = (effect || "none").toLowerCase();
  if (fx === "old_footage") {
    const flicker = 0.94 + Math.sin(frame * 1.9) * 0.03 + Math.cos(frame * 0.7) * 0.02;
    return `sepia(.45) contrast(1.14) brightness(${flicker.toFixed(3)}) saturate(.75)`;
  }
  if (fx === "archival_photo") {
    return "sepia(.28) contrast(1.08) brightness(.96) saturate(.84)";
  }
  if (fx === "vhs_retro") {
    return "contrast(1.12) saturate(1.15) brightness(.96) hue-rotate(-5deg)";
  }
  if (fx === "noir_bw") {
    return "grayscale(1) contrast(1.24) brightness(.95)";
  }
  if (fx === "cctv_cam") {
    return "grayscale(.60) sepia(.22) hue-rotate(78deg) contrast(1.18) brightness(.92)";
  }
  if (fx === "dream_glow") {
    return "brightness(1.04) saturate(1.12) contrast(.97)";
  }
  if (fx === "glitch_pulse") {
    const burst = frame < 8 ? 1.22 : 1.03;
    return `brightness(1.0) contrast(${burst}) saturate(1.10)`;
  }
  if (grade === "warm_history") return "brightness(1.0) sepia(.06) saturate(1.06) contrast(1.04)";
  if (grade === "cool_science") return "brightness(1.0) saturate(.98) hue-rotate(4deg) contrast(1.05)";
  if (grade === "cinematic_teal") return "brightness(1.0) saturate(1.04) contrast(1.05)";
  return "brightness(1.0) saturate(1.02) contrast(1.03)";
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
        <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(255,220,160,0.05) 45%, rgba(18,12,6,0.36) 100%)" }} />
        <div style={{ position: "absolute", left: `${scratchX1}%`, top: 0, bottom: 0, width: 1.5, background: "rgba(255,244,214,0.32)" }} />
        {showScratch2 && (
          <div style={{ position: "absolute", left: `${scratchX2}%`, top: "8%", bottom: "12%", width: 1, background: "rgba(20,14,8,0.32)" }} />
        )}
        <div style={{ position: "absolute", left: `${dustX}%`, top: `${dustY}%`, width: 4, height: 4, borderRadius: "50%", background: "rgba(255,240,210,0.38)" }} />
        <AbsoluteFill style={{ opacity: 0.08, backgroundImage: "repeating-radial-gradient(circle at 20% 30%, rgba(255,235,200,0.8) 0, rgba(0,0,0,0.8) 1px, transparent 2px)", backgroundSize: "5px 5px" }} />
      </AbsoluteFill>
    );
  }

  if (fx === "archival_photo") {
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <AbsoluteFill style={{ border: "22px solid rgba(240,230,210,0.16)", boxShadow: "inset 0 0 60px rgba(15,10,5,0.40)" }} />
        <AbsoluteFill style={{ opacity: 0.05, backgroundImage: "repeating-radial-gradient(circle at 30% 40%, rgba(255,245,220,0.7) 0, rgba(0,0,0,0.7) 1px, transparent 2px)", backgroundSize: "6px 6px" }} />
      </AbsoluteFill>
    );
  }

  if (fx === "vhs_retro") {
    const scanY = (frame * 9) % 1080;
    const sec = Math.floor(frame / Math.max(1, fps));
    const tc = `00:${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <AbsoluteFill style={{ opacity: 0.16, backgroundImage: "repeating-linear-gradient(0deg, rgba(0,0,0,0.5) 0px, rgba(0,0,0,0.5) 1px, transparent 1px, transparent 4px)" }} />
        <div style={{ position: "absolute", left: 0, right: 0, top: scanY, height: 18, background: "linear-gradient(180deg, transparent, rgba(255,255,255,0.15), transparent)" }} />
        <div style={{ position: "absolute", left: 96, bottom: 58, fontFamily: "monospace", fontSize: 20, fontWeight: 700, color: "rgba(255,255,255,0.82)", textShadow: "2px 0 rgba(255,0,80,0.55), -2px 0 rgba(0,220,255,0.55)" }}>
          ● PLAY {tc}
        </div>
      </AbsoluteFill>
    );
  }

  if (fx === "noir_bw") {
    return (
      <AbsoluteFill style={{ pointerEvents: "none", background: "radial-gradient(ellipse at center, transparent 52%, rgba(0,0,0,0.42) 100%)" }} />
    );
  }

  if (fx === "cctv_cam") {
    const blink = Math.floor(frame / Math.max(1, Math.round(fps / 2))) % 2 === 0;
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <AbsoluteFill style={{ opacity: 0.15, backgroundImage: "repeating-linear-gradient(0deg, rgba(0,25,10,0.55) 0px, rgba(0,25,10,0.55) 1px, transparent 1px, transparent 3px)" }} />
        <div style={{ position: "absolute", left: 96, top: 54, width: 34, height: 34, borderLeft: "3px solid rgba(167,243,208,0.75)", borderTop: "3px solid rgba(167,243,208,0.75)" }} />
        <div style={{ position: "absolute", right: 96, top: 54, width: 34, height: 34, borderRight: "3px solid rgba(167,243,208,0.75)", borderTop: "3px solid rgba(167,243,208,0.75)" }} />
        <div style={{ position: "absolute", left: 96, bottom: 54, width: 34, height: 34, borderLeft: "3px solid rgba(167,243,208,0.75)", borderBottom: "3px solid rgba(167,243,208,0.75)" }} />
        <div style={{ position: "absolute", right: 96, bottom: 54, width: 34, height: 34, borderRight: "3px solid rgba(167,243,208,0.75)", borderBottom: "3px solid rgba(167,243,208,0.75)" }} />
        <div style={{ position: "absolute", left: 112, top: 64, fontFamily: "monospace", fontSize: 18, fontWeight: 700, color: "rgba(167,243,208,0.88)" }}>
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

/** Clean Vox/Documentary-style sharp accent tag bar (wipes in from left, NO pink box!) */
const EditorialTagBar: React.FC<{ text: string; theme: ThemePalette; fps: number }> = ({ text, theme, fps }) => {
  const frame = useCurrentFrame();
  const wipe = interpolate(frame, [0, Math.round(fps * 0.28)], [100, 0], { ...clamp, easing: Easing.out(Easing.cubic) });
  const barBg = theme.accent === "#dc2626" ? "#facc15" : theme.accent;
  const barText = barBg === "#facc15" || theme.isLight ? "#111827" : "#ffffff";
  return (
    <div style={{ display: "inline-block", clipPath: `inset(0 ${wipe.toFixed(1)}% 0 0)`, marginBottom: 18 }}>
      <div
        style={{
          background: barBg,
          color: barText,
          padding: "6px 16px",
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: 0,
          borderRadius: 2,
          boxShadow: "0 4px 14px rgba(0,0,0,0.35)",
        }}
      >
        {text}
      </div>
    </div>
  );
};

/** Compact floating callout pill with glowing indicator dot (matches reference video) */
const CalloutPill: React.FC<{ title: string; subtitle?: string; theme: ThemePalette; fps: number; delay?: number }> = ({
  title,
  subtitle,
  theme,
  fps,
  delay = 10,
}) => {
  const frame = useCurrentFrame();
  const sp = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 14, stiffness: 160 } });
  const op = interpolate(frame, [delay, delay + 7], [0, 1], clamp);
  const tx = interpolate(sp, [0, 1], [-22, 0]);
  const dotColor = theme.accent === "#dc2626" ? "#facc15" : theme.accent;
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 12,
        opacity: op,
        transform: `translateX(${tx.toFixed(1)}px)`,
        background: "rgba(12, 18, 28, 0.78)",
        border: `1.5px solid ${dotColor}`,
        borderRadius: 10,
        padding: "10px 20px",
        boxShadow: "0 8px 24px rgba(0,0,0,0.45)",
      }}
    >
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: dotColor, boxShadow: `0 0 12px ${dotColor}`, flexShrink: 0 }} />
      <div>
        <div style={{ fontSize: 24, fontWeight: 700, color: "#ffffff", lineHeight: 1.25 }}>{title}</div>
        {subtitle && <div style={{ fontSize: 17, color: "#cbd5e1", lineHeight: 1.25, marginTop: 2 }}>{subtitle}</div>}
      </div>
    </div>
  );
};

/** Word-by-word kinetic Bengali headline floating cleanly over footage (NO background box!) */
const KineticHeadline: React.FC<{
  text: string;
  fps: number;
  color: string;
  fontSize?: number;
  align?: "left" | "center" | "right";
}> = ({ text, fps, color, fontSize = 58, align = "left" }) => {
  const frame = useCurrentFrame();
  const words = text.normalize("NFC").split(/\s+/).filter(Boolean);
  return (
    <div
      style={{
        fontSize,
        fontWeight: 700,
        lineHeight: 1.32,
        color,
        textAlign: align,
        textShadow: TEXT_SHADOW_CRISP,
        letterSpacing: 0,
        maxWidth: 1120,
      }}
    >
      {words.map((w, i) => {
        const st = 3 + i * Math.max(2, Math.round(fps * 0.08));
        const op = interpolate(frame, [st, st + 6], [0, 1], clamp);
        const ty = interpolate(frame, [st, st + 6], [18, 0], { ...clamp, easing: Easing.out(Easing.cubic) });
        return (
          <span key={i} style={{ display: "inline-block", marginRight: 14, opacity: op, transform: `translateY(${ty.toFixed(1)}px)` }}>
            {w}
          </span>
        );
      })}
    </div>
  );
};

export const CinematicIntroCard: React.FC<{
  tag?: string;
  headline?: string;
  items?: string[];
  theme: ThemePalette;
  fps: number;
  len: number;
  fontFamily: string;
}> = ({ tag, headline, items = [], theme, fps, len, fontFamily }) => {
  const frame = useCurrentFrame();
  const exitOp = interpolate(frame, [Math.max(15, len - 12), len], [1, 0], clamp);
  const lineW = interpolate(frame, [4, Math.round(fps * 0.65)], [0, 440], { ...clamp, easing: Easing.out(Easing.cubic) });
  const barColor = theme.accent === "#dc2626" ? "#facc15" : theme.accent;

  return (
    <div
      style={{
        position: "absolute",
        left: 96,
        right: 96,
        top: 120,
        opacity: exitOp,
        fontFamily,
        pointerEvents: "none",
      }}
    >
      {tag && <EditorialTagBar text={tag} theme={theme} fps={fps} />}
      {headline && <KineticHeadline text={headline} fps={fps} color="#ffffff" fontSize={64} align="left" />}
      <div style={{ width: lineW, height: 5, borderRadius: 3, background: barColor, marginTop: 18, boxShadow: `0 0 18px ${barColor}` }} />
      {items.length > 0 && (
        <div style={{ marginTop: 26, display: "flex", gap: 16, flexWrap: "wrap" }}>
          <CalloutPill title={items[0]} subtitle={items[1]} theme={theme} fps={fps} delay={12} />
        </div>
      )}
    </div>
  );
};

/** Reference-style rich animated documentary infographics */
export const AnimatedMotionGraphic: React.FC<{
  kind?: string;
  items?: string[];
  theme: ThemePalette;
  fps: number;
  len: number;
  fontFamily: string;
}> = ({ kind, items = [], theme, fps, len, fontFamily }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, Math.max(1, len)], [0, 1], clamp);
  const primary = theme.accent === "#dc2626" ? "#facc15" : theme.accent;
  const secondary = "#22d3ee";

  // 1. Dual Animated Donut / Ring Percentage Charts (matches 04:15 in reference video!)
  if (kind === "stat_chart") {
    const labels = (items.length >= 2 ? items : ["৯০% বিশেষ বৈশিষ্ট্য", "৯৫% অনন্য তথ্য"]).slice(0, 2);
    const extractPct = (s: string, fallback: number) => {
      const m = fromBengaliDigits(s).match(/\d+/);
      return m ? Math.min(100, Math.max(10, parseInt(m[0], 10))) : fallback;
    };
    const pct1 = extractPct(labels[0], 90);
    const pct2 = extractPct(labels[1] || "", 95);
    const r = 128;
    const circ = 2 * Math.PI * r;
    const prog1 = interpolate(frame, [4, Math.round(fps * 1.1)], [0, pct1 / 100], { ...clamp, easing: Easing.out(Easing.cubic) });
    const prog2 = interpolate(frame, [10, Math.round(fps * 1.3)], [0, pct2 / 100], { ...clamp, easing: Easing.out(Easing.cubic) });

    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <svg viewBox="0 0 1280 540" style={{ position: "absolute", left: 320, top: 310, width: 1280, height: 540 }}>
          {/* Left Ring */}
          <g transform="translate(300, 220)">
            <circle r={r} fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="22" />
            <circle r={r} fill="none" stroke={primary} strokeWidth="22" strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={circ * (1 - prog1)} transform="rotate(-90)" />
            <text y="6" fill={primary} fontSize="64" fontWeight="700" textAnchor="middle" fontFamily={fontFamily}>
              {toBengaliDigits(Math.round(prog1 * 100))}%
            </text>
            <text y="52" fill={theme.text} fontSize="22" textAnchor="middle" fontFamily={fontFamily}>
              {labels[0].slice(0, 22)}
            </text>
          </g>

          {/* Center Connector Badge */}
          <line x1="455" y1="220" x2="825" y2="220" stroke={theme.grid} strokeWidth="2" strokeDasharray="6 8" />
          <rect x="570" y="190" width="140" height="60" rx="8" fill={theme.panel} stroke={theme.grid} strokeWidth="1.5" />
          <text x="640" y="227" fill={theme.text} fontSize="20" fontWeight="700" textAnchor="middle" fontFamily={fontFamily}>তথ্য বিশ্লেষণ</text>

          {/* Right Ring */}
          <g transform="translate(980, 220)">
            <circle r={r} fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="22" />
            <circle r={r} fill="none" stroke={secondary} strokeWidth="22" strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={circ * (1 - prog2)} transform="rotate(-90)" />
            <text y="6" fill={secondary} fontSize="64" fontWeight="700" textAnchor="middle" fontFamily={fontFamily}>
              {toBengaliDigits(Math.round(prog2 * 100))}%
            </text>
            <text y="52" fill={theme.text} fontSize="22" textAnchor="middle" fontFamily={fontFamily}>
              {(labels[1] || "বিশ্লেষণ").slice(0, 22)}
            </text>
          </g>
        </svg>
      </AbsoluteFill>
    );
  }

  // 2. Hub-and-Spoke Curved Network Map (matches 05:15 in reference video!)
  if (kind === "map_marker") {
    const nodes = (items.length ? items : ["কেন্দ্রীয় অবস্থান", "উত্তর সংযোগ", "দক্ষিণ পথ"]).slice(0, 3);
    const draw1 = interpolate(frame, [4, Math.round(fps * 1.1)], [520, 0], clamp);
    const draw2 = interpolate(frame, [10, Math.round(fps * 1.3)], [520, 0], clamp);
    const draw3 = interpolate(frame, [16, Math.round(fps * 1.5)], [520, 0], clamp);
    const pulse = 22 + (frame % 42) * 2.1;
    const pulseOp = interpolate(frame % 42, [0, 41], [0.65, 0], clamp);

    return (
      <svg viewBox="0 0 1100 620" style={{ position: "absolute", right: 96, top: 240, width: 1100, height: 620 }}>
        {/* Radar circles */}
        {[120, 220, 320].map((rad, i) => (
          <circle key={i} cx="540" cy="340" r={rad} fill="none" stroke="rgba(255,255,255,0.08)" strokeDasharray="6 8" />
        ))}
        {/* Curved routes */}
        <path d="M 540 340 Q 410 180 220 140" fill="none" stroke={primary} strokeWidth="4" strokeDasharray="10 8" strokeDashoffset={draw1} />
        <path d="M 540 340 Q 670 150 860 120" fill="none" stroke="#f59e0b" strokeWidth="4" strokeDasharray="10 8" strokeDashoffset={draw2} />
        <path d="M 540 340 Q 760 280 960 260" fill="none" stroke={secondary} strokeWidth="4" strokeDasharray="10 8" strokeDashoffset={draw3} />
        <path d="M 540 340 Q 380 430 220 490" fill="none" stroke="#4ade80" strokeWidth="4" strokeDasharray="10 8" strokeDashoffset={draw3} />

        {/* Destination Nodes */}
        <circle cx="220" cy="140" r="10" fill={primary} />
        <text x="220" y="114" fill={theme.text} fontSize="22" fontWeight="600" textAnchor="middle" fontFamily={fontFamily}>{nodes[0]}</text>

        <circle cx="860" cy="120" r="10" fill="#f59e0b" />
        <text x="860" y="94" fill={theme.text} fontSize="22" fontWeight="600" textAnchor="middle" fontFamily={fontFamily}>{nodes[1] || "সংযোগ ২"}</text>

        <circle cx="960" cy="260" r="10" fill={secondary} />
        <text x="960" y="234" fill={theme.text} fontSize="22" fontWeight="600" textAnchor="middle" fontFamily={fontFamily}>{nodes[2] || "সংযোগ ৩"}</text>

        {/* Central Pulsing Hub */}
        <circle cx="540" cy="340" r={pulse} fill="none" stroke={theme.accent} strokeWidth="3" opacity={pulseOp} />
        <circle cx="540" cy="340" r="18" fill={theme.accent} stroke={primary} strokeWidth="5" />
      </svg>
    );
  }

  // 3. Animated Numbered Step Cards + Rotating Emblem (matches 06:04 & 06:28 in reference video!)
  if (kind === "timeline") {
    const steps = (items.length ? items : ["প্রথম ধাপ", "দ্বিতীয় ধাপ", "তৃতীয় ধাপ"]).slice(0, 3);
    const rot = frame * 0.8;
    const emblemSp = spring({ frame, fps, config: { damping: 14, stiffness: 120 } });
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        {/* Left numbered animated cards */}
        <div style={{ position: "absolute", left: 96, top: 310, width: 780, display: "flex", flexDirection: "column", gap: 22, fontFamily }}>
          {steps.map((stepTxt, i) => {
            const st = 6 + i * 10;
            const sp = spring({ frame: Math.max(0, frame - st), fps, config: { damping: 14, stiffness: 150 } });
            const tx = interpolate(sp, [0, 1], [-48, 0]);
            const op = interpolate(frame, [st, st + 8], [0, 1], clamp);
            return (
              <div
                key={i}
                style={{
                  opacity: op,
                  transform: `translateX(${tx.toFixed(1)}px)`,
                  background: "rgba(15, 23, 42, 0.85)",
                  border: `1.5px solid ${i === 0 ? primary : theme.grid}`,
                  borderLeft: `6px solid ${i === 0 ? primary : secondary}`,
                  borderRadius: 12,
                  padding: "18px 26px",
                  display: "flex",
                  alignItems: "center",
                  gap: 18,
                  boxShadow: "0 10px 28px rgba(0,0,0,0.4)",
                }}
              >
                <span style={{ fontSize: 32, fontWeight: 700, color: i === 0 ? primary : secondary }}>
                  ০{toBengaliDigits(i + 1)}
                </span>
                <span style={{ fontSize: 28, fontWeight: 600, color: "#ffffff", lineHeight: 1.35 }}>{stepTxt}</span>
              </div>
            );
          })}
        </div>

        {/* Right pulsing rotating shield/ring emblem */}
        <svg viewBox="0 0 460 460" style={{ position: "absolute", right: 120, top: 270, width: 460, height: 460 }}>
          <g transform={`translate(230,230) scale(${emblemSp.toFixed(3)})`}>
            <circle r="195" fill="none" stroke={theme.grid} strokeWidth="2" strokeDasharray="8 10" transform={`rotate(${rot.toFixed(1)})`} />
            <circle r="150" fill="none" stroke={primary} strokeWidth="3" strokeDasharray="110 35" opacity="0.75" transform={`rotate(${(-rot * 1.2).toFixed(1)})`} />
            <path d="M 0 -95 L 82 -58 L 82 18 C 82 72 44 108 0 124 C -44 108 -82 72 -82 18 L -82 -58 Z" fill="rgba(16, 185, 129, 0.2)" stroke={primary} strokeWidth="5" />
            <circle r="24" fill={primary} opacity="0.9" />
          </g>
        </svg>
      </AbsoluteFill>
    );
  }

  // 4. Default Full-Screen Kinetic Graphic (rotating orbital system + pulsing nodes)
  const rot1 = frame * 0.7;
  const rot2 = -frame * 1.1;
  const breathe = 0.94 + Math.sin(frame / 18) * 0.06;
  return (
    <svg viewBox="0 0 640 640" style={{ position: "absolute", right: 96, top: 200, width: 600, height: 600 }}>
      <g transform={`translate(320,320) scale(${breathe.toFixed(3)})`}>
        <circle r="245" fill="none" stroke={theme.grid} strokeWidth="2" strokeDasharray="12 10" transform={`rotate(${rot1.toFixed(1)})`} />
        <circle r="185" fill="none" stroke={primary} strokeWidth="2.5" strokeDasharray="90 28" opacity="0.75" transform={`rotate(${rot2.toFixed(1)})`} />
        <circle r="120" fill="none" stroke={secondary} strokeWidth="1.5" opacity="0.55" transform={`rotate(${(rot1 * 1.4).toFixed(1)})`} />
        <circle cx={Math.cos(p * Math.PI * 2) * 185} cy={Math.sin(p * Math.PI * 2) * 185} r="8" fill={primary} />
        <circle cx={Math.cos(-p * Math.PI * 2 + 1.5) * 245} cy={Math.sin(-p * Math.PI * 2 + 1.5) * 245} r="6" fill={secondary} />
      </g>
    </svg>
  );
};

export const AnimatedPresetCard: React.FC<{
  preset?: string;
  tag?: string;
  headline?: string;
  items?: string[];
  position?: string;
  theme: ThemePalette;
  fps: number;
  len: number;
  overVideo?: boolean;
  fontFamily: string;
}> = ({ preset, tag, headline, items = [], position = "left", theme, fps, len, overVideo = false, fontFamily }) => {
  const frame = useCurrentFrame();
  const key = (preset || "HDR-DROP").toUpperCase();
  const alignRight = position === "right";
  const exitOp = interpolate(frame, [Math.max(12, len - 10), len], [1, 0], clamp);
  const textColor = overVideo ? "#ffffff" : theme.text;
  const barColor = theme.accent === "#dc2626" ? "#facc15" : theme.accent;

  // Clean open typography — NO pink box or bulky background card!
  const baseStyle: React.CSSProperties = {
    position: "absolute",
    left: alignRight ? "auto" : 96,
    right: alignRight ? 96 : "auto",
    top: 84,
    maxWidth: 1120,
    textAlign: alignRight ? "right" : "left",
    fontFamily,
    opacity: exitOp,
  };

  if (key === "CTA-STAGGER") {
    const lineW = interpolate(frame, [4, Math.round(fps * 0.6)], [0, 560], { ...clamp, easing: Easing.out(Easing.cubic) });
    const ctaPills = [
      { label: "কমেন্ট করুন", sub: "আপনার মতামত জানান", bg: "#0ea5e9" },
      { label: "লাইক দিন", sub: "ভিডিওটি ভালো লাগলে", bg: "#22c55e" },
      { label: "সাবস্ক্রাইব", sub: "নতুন ভিডিওর জন্য", bg: "#ef4444" },
    ];
    return (
      <div style={{ position: "absolute", left: 96, right: 96, top: 240, textAlign: "center", fontFamily, opacity: exitOp }}>
        {tag && <EditorialTagBar text={tag} theme={theme} fps={fps} />}
        {headline && <KineticHeadline text={headline} fps={fps} color="#ffffff" fontSize={58} align="center" />}
        <div style={{ width: lineW, height: 5, borderRadius: 3, background: barColor, margin: "20px auto 34px", boxShadow: `0 0 18px ${barColor}` }} />
        <div style={{ display: "inline-flex", gap: 22, flexWrap: "wrap", justifyContent: "center" }}>
          {ctaPills.map((pill, i) => {
            const st = 10 + i * 8;
            const sp = spring({ frame: Math.max(0, frame - st), fps, config: { damping: 13, stiffness: 160 } });
            const op = interpolate(frame, [st, st + 7], [0, 1], clamp);
            return (
              <div
                key={i}
                style={{
                  opacity: op,
                  transform: `scale(${interpolate(sp, [0, 1], [0.78, 1]).toFixed(3)})`,
                  background: pill.bg,
                  color: "#ffffff",
                  padding: "16px 34px",
                  borderRadius: 999,
                  boxShadow: "0 10px 28px rgba(0,0,0,0.42)",
                  textAlign: "left",
                }}
              >
                <div style={{ fontSize: 27, fontWeight: 700, lineHeight: 1.2 }}>{pill.label}</div>
                <div style={{ fontSize: 16, opacity: 0.92, marginTop: 2 }}>{pill.sub}</div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (key === "NUM-ROLL") {
    const rawNumMatch = fromBengaliDigits(`${headline || ""} ${items.join(" ")}`).match(/\d[\d,.]*/);
    const targetNum = rawNumMatch ? parseFloat(rawNumMatch[0].replace(/,/g, "")) : 100;
    const rollP = interpolate(frame, [0, Math.round(fps * 0.9)], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
    const currentVal = Math.round(targetNum * rollP);
    return (
      <div style={baseStyle}>
        {tag && <EditorialTagBar text={tag} theme={theme} fps={fps} />}
        <div style={{ fontSize: 82, fontWeight: 700, lineHeight: 1.15, color: barColor, textShadow: TEXT_SHADOW_CRISP }}>
          {toBengaliDigits(currentVal)}
        </div>
        {headline && <KineticHeadline text={headline} fps={fps} color={textColor} fontSize={48} align={alignRight ? "right" : "left"} />}
        {items.length > 0 && (
          <div style={{ marginTop: 22 }}>
            <CalloutPill title={items[0]} subtitle={items[1]} theme={theme} fps={fps} delay={12} />
          </div>
        )}
      </div>
    );
  }

  if (key === "BIG-STAMP") {
    const stampScale = interpolate(frame, [0, Math.round(fps * 0.25)], [1.35, 1.0], { ...clamp, easing: Easing.out(Easing.cubic) });
    const stampOp = interpolate(frame, [0, Math.round(fps * 0.18)], [0, 1], clamp) * exitOp;
    const lineW = interpolate(frame, [6, Math.round(fps * 0.6)], [0, 360], { ...clamp, easing: Easing.out(Easing.cubic) });
    return (
      <div style={{ ...baseStyle, opacity: stampOp, transform: `scale(${stampScale.toFixed(3)})`, transformOrigin: alignRight ? "right top" : "left top" }}>
        {tag && <EditorialTagBar text={tag} theme={theme} fps={fps} />}
        {headline && (
          <div style={{ fontSize: 62, fontWeight: 700, lineHeight: 1.32, color: textColor, textShadow: TEXT_SHADOW_CRISP }}>
            {headline}
          </div>
        )}
        <div style={{ width: lineW, height: 5, borderRadius: 3, background: barColor, marginTop: 14, marginLeft: alignRight ? "auto" : 0 }} />
      </div>
    );
  }

  // Clean word-by-word documentary typography (HDR-DROP, TAG-WIPE, QUOTE-STAGGER)
  return (
    <div style={baseStyle}>
      {tag && <EditorialTagBar text={tag} theme={theme} fps={fps} />}
      {headline && <KineticHeadline text={headline} fps={fps} color={textColor} fontSize={54} align={alignRight ? "right" : "left"} />}
      {items.length > 0 && (
        <div style={{ marginTop: 24, display: "flex", justifyContent: alignRight ? "flex-end" : "flex-start" }}>
          <CalloutPill title={items[0]} subtitle={items[1]} theme={theme} fps={fps} delay={12} />
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
  const boxIn = interpolate(frame, [cueStartF, cueStartF + 6], [0.95, 1.0], clamp);
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
  const kwColor = theme.accent === "#dc2626" ? "#facc15" : theme.accent;

  return (
    <div
      style={{
        position: "absolute",
        left: 160,
        right: 160,
        bottom: 54,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          opacity: boxOp,
          transform: `scale(${boxIn.toFixed(3)})`,
          background: "rgba(10, 14, 22, 0.78)",
          borderRadius: 10,
          padding: "12px 26px",
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
          boxShadow: "0 8px 24px rgba(0,0,0,0.45)",
        }}
      >
        {visibleWords.map((w, i) => {
          const cleanWord = w.word.normalize("NFC");
          const wStartF = Math.floor(w.start * fps);
          const p = interpolate(frame, [wStartF, wStartF + 6], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
          const isCurrent = nowSec >= w.start && nowSec <= w.end + 0.08;
          const stripped = cleanWord.replace(/[।.,!?;:'"()[\]{}]/g, "");
          const isKeyword = keywordSet.has(cleanWord) || keywordSet.has(stripped);
          const opacity = frame < wStartF ? 0.52 : interpolate(p, [0, 1], [0.55, 1.0]);
          const ty = frame < wStartF ? 4 : interpolate(p, [0, 1], [4, 0]);
          const kwScale = isKeyword && isCurrent ? 1.08 : 1.0;

          return (
            <span
              key={`${pageStart + i}-${cleanWord}`}
              style={{
                display: "inline-block",
                marginRight: 10,
                opacity,
                color: isKeyword ? kwColor : "#ffffff",
                transform: `translateY(${ty.toFixed(1)}px) scale(${kwScale.toFixed(3)})`,
                textShadow: isKeyword
                  ? `0 0 12px ${kwColor}, 0 2px 6px rgba(0,0,0,0.9)`
                  : "0 2px 6px rgba(0,0,0,0.9)",
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
