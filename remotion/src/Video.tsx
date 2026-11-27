import React from "react";
import { AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import {
  AnimatedMotionGraphic,
  AnimatedPresetCard,
  CinematicIntroCard,
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
    bg2: "#162033",
    accent: "#dc2626",
    accent2: "#ffffff",
    text: "#ffffff",
    muted: "#e4e4e7",
    panel: "rgba(15,20,30,.78)",
    grid: "rgba(255,255,255,.14)",
    overlay: "rgba(5,5,8,.20)",
    isLight: false,
  },
  cinematic_dark: {
    bg: "#08101c",
    bg2: "#0f2035",
    accent: "#facc15",
    accent2: "#d6a84b",
    text: "#f8fafc",
    muted: "#cbd5e1",
    panel: "rgba(15,23,42,.80)",
    grid: "rgba(226,232,240,.16)",
    overlay: "rgba(3,10,20,.20)",
    isLight: false,
  },
  vox_colorful: {
    bg: "#fef08a",
    bg2: "#fde047",
    accent: "#dc2626",
    accent2: "#111827",
    text: "#111827",
    muted: "#374151",
    panel: "rgba(255,255,255,.88)",
    grid: "rgba(17,24,39,.15)",
    overlay: "rgba(17,24,39,.16)",
    isLight: true,
  },
  editorial_paper: {
    bg: "#f6f1e7",
    bg2: "#ebe2d2",
    accent: "#d97706",
    accent2: "#1c1917",
    text: "#1c1917",
    muted: "#57534e",
    panel: "rgba(255,253,249,.90)",
    grid: "rgba(68,55,40,.14)",
    overlay: "rgba(28,25,23,.16)",
    isLight: true,
  },
  vibrant_gradient: {
    bg: "#1e1b4b",
    bg2: "#4c1d95",
    accent: "#22d3ee",
    accent2: "#e879f9",
    text: "#ffffff",
    muted: "#e0e7ff",
    panel: "rgba(30,27,75,.80)",
    grid: "rgba(224,231,255,.17)",
    overlay: "rgba(15,10,45,.20)",
    isLight: false,
  },
  minimal_light: {
    bg: "#f8fafc",
    bg2: "#e2e8f0",
    accent: "#2563eb",
    accent2: "#0f172a",
    text: "#0f172a",
    muted: "#475569",
    panel: "rgba(255,255,255,.92)",
    grid: "rgba(15,23,42,.13)",
    overlay: "rgba(15,23,42,.15)",
    isLight: true,
  },
};

const getTheme = (key?: string): ThemePalette => THEMES[key as ThemeKey] || THEMES.crimson_noir;

const BeatView: React.FC<{ beat: Beat; theme: ThemePalette; fps: number; isIntro: boolean }> = ({
  beat,
  theme,
  fps,
  isIntro,
}) => {
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
  const hasText = isIntro ? Boolean(beat.headline || beat.graphic?.heading) : Boolean(isGraphic || beat.showOverlay);

  return (
    <AbsoluteFill
      style={{
        background: isGraphic
          ? `radial-gradient(ellipse at 65% 28%, ${theme.bg2} 0%, ${theme.bg} 62%, ${theme.bg} 100%)`
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
              opacity: 0.16,
              backgroundImage:
                "linear-gradient(rgba(255,255,255,.10) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.10) 1px,transparent 1px)",
              backgroundSize: "64px 64px",
              transform: `translate(${(p * 24).toFixed(1)}px,${(p * -16).toFixed(1)}px)`,
            }}
          />
          <AnimatedMotionGraphic
            kind={beat.graphic?.kind}
            items={beat.graphic?.items || []}
            theme={theme}
            fps={fps}
            len={len}
            fontFamily={FONT}
          />
        </AbsoluteFill>
      )}

      <VisualEffectOverlay effect={beat.visualEffect} fps={fps} />

      {/* Very soft, light readability scrim ONLY when text floats over video (max 0.22 opacity — no heavy black shadow!) */}
      {!isGraphic && hasText && (
        <AbsoluteFill
          style={{
            background: "linear-gradient(180deg, rgba(0,0,0,0.22) 0%, rgba(0,0,0,0.06) 45%, rgba(0,0,0,0.22) 100%)",
            pointerEvents: "none",
          }}
        />
      )}

      {isIntro && (beat.headline || beat.graphic?.heading) ? (
        <CinematicIntroCard
          tag={beat.tag}
          headline={beat.headline || beat.graphic?.heading}
          items={beat.graphic?.items || []}
          theme={theme}
          fps={fps}
          len={len}
          fontFamily={FONT}
        />
      ) : (isGraphic || beat.showOverlay) ? (
        <AnimatedPresetCard
          preset={beat.textPreset}
          tag={beat.tag}
          headline={beat.headline || beat.graphic?.heading}
          items={beat.graphic?.items || []}
          position={beat.position}
          theme={theme}
          fps={fps}
          len={len}
          overVideo={!isGraphic}
          fontFamily={FONT}
        />
      ) : null}

      {beat.sfx && <Audio src={staticFile(beat.sfx)} volume={0.11} />}
      {flashOpacity > 0 && <AbsoluteFill style={{ background: "#ffffff", opacity: flashOpacity, pointerEvents: "none" }} />}
    </AbsoluteFill>
  );
};

export const Main: React.FC<Scene> = (scene) => {
  const theme = getTheme(scene.videoTheme);
  return (
    <AbsoluteFill style={{ background: theme.bg, fontFamily: FONT }}>
      <style>{`@font-face{font-family:'Hind Siliguri';src:url('${staticFile("fonts/HindSiliguri-Regular.ttf")}')} @font-face{font-family:'Hind Siliguri';font-weight:500;src:url('${staticFile("fonts/HindSiliguri-Medium.ttf")}')} @font-face{font-family:'Hind Siliguri';font-weight:600;src:url('${staticFile("fonts/HindSiliguri-SemiBold.ttf")}')} @font-face{font-family:'Hind Siliguri';font-weight:700;src:url('${staticFile("fonts/HindSiliguri-Bold.ttf")}')} *{box-sizing:border-box}`}</style>

      {scene.beats.map((b, idx) => (
        <Sequence key={b.id} from={b.start} durationInFrames={Math.max(1, b.end - b.start)}>
          <BeatView beat={b} theme={theme} fps={scene.fps || 30} isIntro={idx === 0} />
        </Sequence>
      ))}

      <Audio src={staticFile(scene.voice)} />
      {scene.burnSubtitles && (
        <KaraokeSubtitleBar subtitles={scene.subtitles} fps={scene.fps || 30} theme={theme} fontFamily={FONT} />
      )}
    </AbsoluteFill>
  );
};