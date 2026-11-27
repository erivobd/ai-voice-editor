import React from "react";
import { AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import {
  AnimatedPresetCard,
  KaraokeSubtitleBar,
  SubtitleCue,
  ThemePalette,
  VisualEffectOverlay,
  computeCameraTransform,
  computeTransitionStyle,
  getMediaEffectFilter,
} from "./kit";

type Beat = {
  id: number;
  start: number;
  end: number;
  text: string;
  headline?: string;
  tag?: string;
  storyBeat?: string;
  visualType: string;
  mediaPreference?: string;
  visualEffect?: string;
  video?: string | null;
  zoom?: number;
  cameraPreset?: string;
  textPreset?: string;
  transition?: string;
  transitionDuration?: number;
  musicMode?: string;
  keywords?: string[];
  grade?: string;
  graphic?: { heading?: string; items?: string[]; kind?: string };
  position?: string;
  showOverlay?: boolean;
  sfx?: string | null;
};

type Scene = {
  videoTheme?: string;
  fps: number;
  width: number;
  height: number;
  duration: number;
  title: string;
  voice: string;
  beats: Beat[];
  subtitles: SubtitleCue[];
  burnSubtitles: boolean;
};

const FONT = `"Hind Siliguri", "Noto Sans Bengali", sans-serif`;

type ThemeKey =
  | "crimson_noir"
  | "cinematic_dark"
  | "vox_colorful"
  | "editorial_paper"
  | "vibrant_gradient"
  | "minimal_light";

const THEMES: Record<ThemeKey, ThemePalette> = {
  crimson_noir: {
    bg: "#09090b",
    bg2: "#20060c",
    accent: "#dc2626",
    accent2: "#ffffff",
    text: "#ffffff",
    muted: "#e4e4e7",
    panel: "rgba(18,18,22,.88)",
    grid: "rgba(255,255,255,.12)",
    overlay: "rgba(5,5,8,.72)",
    isLight: false,
  },
  cinematic_dark: {
    bg: "#08101c",
    bg2: "#0f2035",
    accent: "#facc15",
    accent2: "#d6a84b",
    text: "#f8fafc",
    muted: "#cbd5e1",
    panel: "rgba(15,23,42,.90)",
    grid: "rgba(226,232,240,.16)",
    overlay: "rgba(3,10,20,.76)",
    isLight: false,
  },
  vox_colorful: {
    bg: "#fef08a",
    bg2: "#fde047",
    accent: "#dc2626",
    accent2: "#111827",
    text: "#111827",
    muted: "#374151",
    panel: "rgba(255,255,255,.91)",
    grid: "rgba(17,24,39,.15)",
    overlay: "rgba(17,24,39,.25)",
    isLight: true,
  },
  editorial_paper: {
    bg: "#f6f1e7",
    bg2: "#ebe2d2",
    accent: "#d97706",
    accent2: "#1c1917",
    text: "#1c1917",
    muted: "#57534e",
    panel: "rgba(255,253,249,.93)",
    grid: "rgba(68,55,40,.14)",
    overlay: "rgba(28,25,23,.30)",
    isLight: true,
  },
  vibrant_gradient: {
    bg: "#1e1b4b",
    bg2: "#4c1d95",
    accent: "#22d3ee",
    accent2: "#e879f9",
    text: "#ffffff",
    muted: "#e0e7ff",
    panel: "rgba(30,27,75,.90)",
    grid: "rgba(224,231,255,.17)",
    overlay: "rgba(15,10,45,.72)",
    isLight: false,
  },
  minimal_light: {
    bg: "#f8fafc",
    bg2: "#e2e8f0",
    accent: "#2563eb",
    accent2: "#0f172a",
    text: "#0f172a",
    muted: "#475569",
    panel: "rgba(255,255,255,.94)",
    grid: "rgba(15,23,42,.13)",
    overlay: "rgba(15,23,42,.25)",
    isLight: true,
  },
};

const getTheme = (key?: string): ThemePalette => THEMES[key as ThemeKey] || THEMES.crimson_noir;

const BeatView: React.FC<{ beat: Beat; theme: ThemePalette; fps: number }> = ({ beat, theme, fps }) => {
  const frame = useCurrentFrame();
  const len = Math.max(1, beat.end - beat.start);
  const p = interpolate(frame, [0, len], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const cameraTransform = computeCameraTransform(beat.cameraPreset, frame, len, fps, beat.zoom ?? 0.045);
  const { style: transitionStyle, flashOpacity } = computeTransitionStyle(
    beat.transition,
    frame,
    len,
    fps,
    beat.transitionDuration ?? 0.35
  );
  const isGraphic = beat.visualType !== "stock_footage" || !beat.video;
  const mediaFilter = getMediaEffectFilter(beat.visualEffect, beat.grade, frame);

  return (
    <AbsoluteFill
      style={{
        background: isGraphic
          ? `radial-gradient(ellipse at 72% 24%, ${theme.bg2} 0%, ${theme.bg} 58%, ${theme.bg} 100%)`
          : theme.bg,
        overflow: "hidden",
        ...transitionStyle,
      }}
    >
      {beat.video && (
        <OffthreadVideo
          src={staticFile(beat.video)}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: cameraTransform,
            filter: mediaFilter,
          }}
        />
      )}

      {isGraphic && (
        <AbsoluteFill style={{ transform: cameraTransform }}>
          <AbsoluteFill
            style={{
              opacity: 0.22,
              backgroundImage:
                "linear-gradient(rgba(255,255,255,.10) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.10) 1px,transparent 1px)",
              backgroundSize: "64px 64px",
              transform: `translate(${(p * 18).toFixed(1)}px,${(p * -12).toFixed(1)}px)`,
            }}
          />
          {beat.graphic?.kind === "stat_chart" ? (
            <svg viewBox="0 0 700 460" style={{ position: "absolute", right: 110, top: 250, width: 700, height: 460 }}>
              {[0, 1, 2, 3].map((i) => (
                <line key={i} x1="35" y1={80 + i * 85} x2="665" y2={80 + i * 85} stroke={theme.grid} strokeDasharray="6 10" />
              ))}
              {(beat.graphic?.items || ["তথ্য", "বিশ্লেষণ", "প্রভাব"]).slice(0, 4).map((x, i) => {
                const h = (110 + i * 34) * (0.25 + p * 0.75);
                return (
                  <g key={i}>
                    <rect x={70 + i * 150} y={420 - h} width="82" height={h} rx="8" fill={i === 1 ? theme.accent2 : theme.accent} opacity=".88" />
                    <text x={111 + i * 150} y="448" fill={theme.text} fontSize="18" textAnchor="middle" fontFamily={FONT}>
                      {x.slice(0, 9)}
                    </text>
                  </g>
                );
              })}
            </svg>
          ) : beat.graphic?.kind === "timeline" ? (
            <svg viewBox="0 0 760 300" style={{ position: "absolute", right: 96, top: 350, width: 760, height: 300 }}>
              <line x1="55" y1="145" x2="705" y2="145" stroke={theme.text} strokeWidth="5" />
              {(beat.graphic?.items || ["শুরু", "পরিবর্তন", "বর্তমান"]).slice(0, 4).map((x, i) => (
                <g key={i}>
                  <circle cx={85 + i * 195} cy="145" r="15" fill={theme.accent} />
                  <text x={85 + i * 195} y={i % 2 ? 205 : 90} fill={theme.text} fontSize="22" textAnchor="middle" fontFamily={FONT}>
                    {x.slice(0, 14)}
                  </text>
                </g>
              ))}
            </svg>
          ) : beat.graphic?.kind === "map_marker" ? (
            <svg viewBox="0 0 700 560" style={{ position: "absolute", right: 120, top: 210, width: 700, height: 560 }}>
              <path d="M80 100 L220 60 L330 130 L450 75 L620 140 L590 300 L650 420 L470 480 L330 410 L180 480 L90 330 Z" fill={theme.panel} stroke={theme.muted} strokeWidth="4" />
              <path d="M120 260 Q280 160 430 300 T600 270" fill="none" stroke={theme.accent2} strokeWidth="5" strokeDasharray="12 10" />
              <g transform={`translate(${(350 + Math.sin(p * 6) * 8).toFixed(1)},${(260 + Math.cos(p * 6) * 8).toFixed(1)})`}>
                <path d="M0 55 C-80 -25 -55 -105 0 -105 C55 -105 80 -25 0 55Z" fill={theme.accent} />
                <circle cy="-55" r="18" fill="white" />
              </g>
            </svg>
          ) : (
            <>
              <div style={{ position: "absolute", width: 520, height: 520, border: "1px solid rgba(255,255,255,.15)", borderRadius: "50%", right: 100, top: 180, transform: `scale(${(0.88 + p * 0.16).toFixed(3)})` }} />
              <div style={{ position: "absolute", width: 360, height: 360, border: "1px solid rgba(248,54,55,.35)", borderRadius: "50%", right: 180, top: 260, transform: `rotate(${(p * 40).toFixed(1)}deg)` }} />
            </>
          )}
        </AbsoluteFill>
      )}

      {/* Scene-specific documentary visual effect overlay (old_footage, vhs_retro, cctv_cam, etc.) */}
      <VisualEffectOverlay effect={beat.visualEffect} fps={fps} />

      <AbsoluteFill
        style={{
          background: `linear-gradient(90deg,${theme.overlay} 0%,${theme.overlay} 50%,transparent 100%),linear-gradient(0deg,${theme.overlay},transparent 38%)`,
        }}
      />

      {(isGraphic || beat.showOverlay) && (
        <AnimatedPresetCard
          preset={beat.textPreset}
          tag={beat.tag}
          headline={beat.headline || beat.graphic?.heading}
          items={beat.graphic?.items || []}
          position={beat.position}
          theme={theme}
          fps={fps}
          fontFamily={FONT}
        />
      )}

      {beat.sfx && <Audio src={staticFile(beat.sfx)} volume={0.11} />}
      {flashOpacity > 0 && <AbsoluteFill style={{ background: "#ffffff", opacity: flashOpacity, pointerEvents: "none" }} />}

      <div
        style={{
          position: "absolute",
          right: 96,
          top: 54,
          width: 16,
          height: 16,
          background: theme.accent,
          borderRadius: "50%",
          boxShadow: `0 0 22px ${theme.accent}`,
        }}
      />
    </AbsoluteFill>
  );
};

export const Main: React.FC<Scene> = (scene) => {
  const theme = getTheme(scene.videoTheme);
  return (
    <AbsoluteFill style={{ background: theme.bg, fontFamily: FONT }}>
      <style>{`@font-face{font-family:'Hind Siliguri';src:url('${staticFile("fonts/HindSiliguri-Regular.ttf")}')} @font-face{font-family:'Hind Siliguri';font-weight:500;src:url('${staticFile("fonts/HindSiliguri-Medium.ttf")}')} @font-face{font-family:'Hind Siliguri';font-weight:600;src:url('${staticFile("fonts/HindSiliguri-SemiBold.ttf")}')} @font-face{font-family:'Hind Siliguri';font-weight:700;src:url('${staticFile("fonts/HindSiliguri-Bold.ttf")}')} *{box-sizing:border-box}`}</style>

      {scene.beats.map((b) => (
        <Sequence key={b.id} from={b.start} durationInFrames={Math.max(1, b.end - b.start)}>
          <BeatView beat={b} theme={theme} fps={scene.fps || 30} />
        </Sequence>
      ))}

      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse at center, transparent 62%, rgba(0,0,0,0.34) 100%)",
          pointerEvents: "none",
        }}
      />
      <AbsoluteFill
        style={{
          opacity: 0.03,
          backgroundImage:
            "repeating-radial-gradient(circle at 17% 32%, rgba(255,255,255,0.6) 0, rgba(0,0,0,0.6) 1px, transparent 2px)",
          backgroundSize: "6px 6px",
          pointerEvents: "none",
        }}
      />

      <Audio src={staticFile(scene.voice)} />
      {scene.burnSubtitles && (
        <KaraokeSubtitleBar subtitles={scene.subtitles} fps={scene.fps || 30} theme={theme} fontFamily={FONT} />
      )}
    </AbsoluteFill>
  );
};