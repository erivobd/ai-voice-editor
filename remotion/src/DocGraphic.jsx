import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const THEMES = {
  cinematic_dark: {
    bg: "radial-gradient(circle at 20% 20%, #102038 0%, #060b14 75%)",
    cardBg: "rgba(15, 23, 42, 0.85)",
    cardBorder: "rgba(250, 204, 21, 0.35)",
    text: "#f8fafc",
    muted: "#94a3b8",
    accent: "#facc15",
    accentText: "#090d16",
    secondary: "#38bdf8",
    grid: "rgba(255,255,255,0.06)",
    pillBg: "rgba(15, 23, 42, 0.9)",
  },
  crimson_noir: {
    bg: "radial-gradient(circle at 18% 22%, #1a0609 0%, #09090b 72%)",
    cardBg: "rgba(18, 18, 22, 0.92)",
    cardBorder: "rgba(220, 38, 38, 0.55)",
    text: "#ffffff",
    muted: "#d4d4d8",
    accent: "#dc2626",
    accentText: "#ffffff",
    secondary: "#ffffff",
    grid: "rgba(255,255,255,0.06)",
    pillBg: "rgba(10, 10, 12, 0.92)",
  },
  vox_colorful: {
    bg: "linear-gradient(135deg, #fef08a 0%, #fde047 55%, #facc15 100%)",
    cardBg: "rgba(255, 255, 255, 0.94)",
    cardBorder: "rgba(220, 38, 38, 0.45)",
    text: "#111827",
    muted: "#374151",
    accent: "#dc2626",
    accentText: "#ffffff",
    secondary: "#111827",
    grid: "rgba(17,24,39,0.07)",
    pillBg: "rgba(17, 24, 39, 0.92)",
  },
  editorial_paper: {
    bg: "radial-gradient(circle at 50% 30%, #faf6ee 0%, #efe7d6 100%)",
    cardBg: "rgba(255, 252, 245, 0.95)",
    cardBorder: "rgba(180, 83, 9, 0.35)",
    text: "#1c1917",
    muted: "#57534e",
    accent: "#d97706",
    accentText: "#ffffff",
    secondary: "#0f766e",
    grid: "rgba(28,25,23,0.07)",
    pillBg: "rgba(28, 25, 23, 0.9)",
  },
  vibrant_gradient: {
    bg: "linear-gradient(135deg, #1e1b4b 0%, #4c1d95 55%, #0f172a 100%)",
    cardBg: "rgba(30, 27, 75, 0.85)",
    cardBorder: "rgba(34, 211, 238, 0.45)",
    text: "#f8fafc",
    muted: "#cbd5e1",
    accent: "#22d3ee",
    accentText: "#0f172a",
    secondary: "#f472b6",
    grid: "rgba(255,255,255,0.07)",
    pillBg: "rgba(15, 23, 42, 0.88)",
  },
  minimal_light: {
    bg: "linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%)",
    cardBg: "#ffffff",
    cardBorder: "rgba(37, 99, 235, 0.25)",
    text: "#0f172a",
    muted: "#475569",
    accent: "#2563eb",
    accentText: "#ffffff",
    secondary: "#0ea5e9",
    grid: "rgba(15,23,42,0.06)",
    pillBg: "rgba(15, 23, 42, 0.9)",
  },
};

const FONT = "'Hind Siliguri', 'Noto Sans Bengali', system-ui, sans-serif";

const GridBackdrop = ({ color }) => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      backgroundImage: `linear-gradient(${color} 1px, transparent 1px), linear-gradient(90deg, ${color} 1px, transparent 1px)`,
      backgroundSize: "72px 72px",
      pointerEvents: "none",
    }}
  />
);

const Badge = ({ text, theme, progress }) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 10,
      background: theme.accent,
      color: theme.accentText,
      padding: "10px 24px",
      borderRadius: 8,
      fontWeight: 700,
      fontSize: 26,
      letterSpacing: "0.02em",
      transform: `translateY(${(1 - progress) * 24}px)`,
      opacity: progress,
      boxShadow: "0 10px 28px rgba(0,0,0,0.22)",
    }}
  >
    <span style={{ width: 10, height: 10, borderRadius: "50%", background: theme.accentText, opacity: 0.85 }} />
    {text}
  </div>
);

const FlowchartView = ({ heading, subheading, items, theme, frame, fps }) => {
  const headIn = spring({ frame, fps, config: { damping: 14 } });
  const steps = items.length ? items.slice(0, 4) : ["ধাপ ১: তথ্য বিশ্লেষণ", "ধাপ ২: মূল কারণ", "ধাপ ৩: ফলাফল"];

  return (
    <div style={{ display: "flex", width: "100%", height: "100%", padding: "90px 100px", gap: 70, alignItems: "center" }}>
      <div style={{ flex: "0 0 42%", display: "flex", flexDirection: "column", gap: 24 }}>
        <Badge text={subheading || "বিশ্লেষণ // ফ্লোচার্ট"} theme={theme} progress={headIn} />
        <div
          style={{
            fontSize: 68,
            fontWeight: 800,
            lineHeight: 1.15,
            color: theme.text,
            transform: `translateY(${(1 - headIn) * 30}px)`,
            opacity: headIn,
          }}
        >
          {heading}
        </div>
        <div style={{ width: 110, height: 7, background: theme.accent, borderRadius: 4, transform: `scaleX(${headIn})`, transformOrigin: "left" }} />
      </div>

      <div
        style={{
          flex: 1,
          background: theme.cardBg,
          border: `2px solid ${theme.cardBorder}`,
          borderRadius: 24,
          padding: "46px 50px",
          display: "flex",
          flexDirection: "column",
          gap: 22,
          boxShadow: "0 24px 60px rgba(0,0,0,0.25)",
        }}
      >
        {steps.map((step, i) => {
          const p = spring({ frame: frame - 10 - i * 10, fps, config: { damping: 14 } });
          return (
            <React.Fragment key={i}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 22,
                  padding: "22px 26px",
                  borderRadius: 16,
                  border: `2px solid ${i === steps.length - 1 ? theme.accent : theme.cardBorder}`,
                  background: i === steps.length - 1 ? `${theme.accent}18` : "transparent",
                  transform: `translateX(${(1 - p) * 45}px)`,
                  opacity: p,
                }}
              >
                <div
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: 12,
                    background: theme.accent,
                    color: theme.accentText,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 26,
                    fontWeight: 800,
                    flexShrink: 0,
                  }}
                >
                  0{i + 1}
                </div>
                <div style={{ fontSize: 32, fontWeight: 700, color: theme.text, lineHeight: 1.25 }}>{step}</div>
              </div>
              {i < steps.length - 1 && (
                <div style={{ display: "flex", justifyContent: "center", opacity: p }}>
                  <div style={{ width: 3, height: 22, background: theme.accent, borderRadius: 2 }} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

const RouteMapView = ({ heading, subheading, items, theme, frame, fps }) => {
  const headIn = spring({ frame, fps, config: { damping: 14 } });
  const nodes = items.length ? items.slice(0, 4) : ["পয়েন্ট ১", "পয়েন্ট ২", "পয়েন্ট ৩", "পয়েন্ট ৪"];
  const coords = [
    { x: 340, y: 310 },
    { x: 1580, y: 310 },
    { x: 340, y: 800 },
    { x: 1580, y: 800 },
  ];
  const cx = 960;
  const cy = 560;

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div style={{ position: "absolute", top: 64, left: 90, zIndex: 5 }}>
        <Badge text={subheading || "সংযোগ // ম্যাপ"} theme={theme} progress={headIn} />
      </div>

      <svg width="1920" height="1080" style={{ position: "absolute", inset: 0 }}>
        {nodes.map((_, i) => {
          const pos = coords[i % coords.length];
          const lineP = interpolate(frame, [10 + i * 8, 32 + i * 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const dashOffset = (1 - lineP) * 700;
          return (
            <path
              key={i}
              d={`M ${cx} ${cy} Q ${(cx + pos.x) / 2} ${cy - 80} ${pos.x} ${pos.y}`}
              fill="none"
              stroke={theme.accent}
              strokeWidth="5"
              strokeDasharray="16 12"
              strokeDashoffset={dashOffset}
              opacity={0.85}
            />
          );
        })}
      </svg>

      {/* Center Hub */}
      <div
        style={{
          position: "absolute",
          left: cx - 210,
          top: cy - 95,
          width: 420,
          minHeight: 190,
          borderRadius: 24,
          background: theme.cardBg,
          border: `3px solid ${theme.accent}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: "24px 30px",
          fontSize: 44,
          fontWeight: 800,
          color: theme.text,
          transform: `scale(${0.85 + headIn * 0.15})`,
          opacity: headIn,
          boxShadow: `0 0 50px ${theme.accent}44`,
        }}
      >
        {heading}
      </div>

      {/* Outer Nodes */}
      {nodes.map((label, i) => {
        const pos = coords[i % coords.length];
        const p = spring({ frame: frame - 16 - i * 8, fps, config: { damping: 14 } });
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: pos.x - 190,
              top: pos.y - 54,
              width: 380,
              padding: "20px 26px",
              borderRadius: 16,
              background: theme.cardBg,
              border: `2px solid ${theme.cardBorder}`,
              color: theme.text,
              fontSize: 30,
              fontWeight: 700,
              textAlign: "center",
              transform: `scale(${0.8 + p * 0.2})`,
              opacity: p,
              boxShadow: "0 16px 36px rgba(0,0,0,0.3)",
            }}
          >
            {label}
          </div>
        );
      })}
    </div>
  );
};

const VisualCalloutView = ({ heading, subheading, items, theme, frame, fps }) => {
  const headIn = spring({ frame, fps, config: { damping: 14 } });
  const points = items.length ? items.slice(0, 4) : ["মূল বৈশিষ্ট্য ১", "মূল বৈশিষ্ট্য ২", "মূল বৈশিষ্ট্য ৩"];

  return (
    <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", width: "100%", height: "100%", padding: "90px 120px", gap: 36 }}>
      <Badge text={subheading || "মূল তথ্য"} theme={theme} progress={headIn} />
      <div
        style={{
          fontSize: 78,
          fontWeight: 800,
          lineHeight: 1.15,
          color: theme.text,
          maxWidth: 1450,
          transform: `translateY(${(1 - headIn) * 30}px)`,
          opacity: headIn,
        }}
      >
        {heading}
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 22, marginTop: 12 }}>
        {points.map((pt, i) => {
          const p = spring({ frame: frame - 12 - i * 8, fps, config: { damping: 14 } });
          return (
            <div
              key={i}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 14,
                padding: "18px 30px",
                borderRadius: 999,
                background: theme.cardBg,
                border: `2px solid ${theme.accent}`,
                color: theme.text,
                fontSize: 32,
                fontWeight: 700,
                transform: `translateY(${(1 - p) * 28}px)`,
                opacity: p,
                boxShadow: "0 12px 30px rgba(0,0,0,0.22)",
              }}
            >
              <span style={{ width: 14, height: 14, borderRadius: "50%", background: theme.accent }} />
              {pt}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const StatChartView = ({ heading, subheading, items, theme, frame, fps }) => {
  const headIn = spring({ frame, fps, config: { damping: 14 } });
  const parsed = (items.length ? items : ["ধাপ ১: 40", "ধাপ ২: 72", "ধাপ ৩: 96"]).slice(0, 5).map((raw, idx) => {
    const parts = String(raw).split(/[:\-—]/);
    const label = (parts[0] || `তথ্য ${idx + 1}`).trim();
    const numMatch = String(raw).match(/(\d+(?:\.\d+)?)/);
    const val = numMatch ? Math.min(100, Math.max(12, Number(numMatch[1]))) : 45 + idx * 15;
    return { label, val, display: parts[1] ? parts[1].trim() : `${val}%` };
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", width: "100%", height: "100%", padding: "85px 120px", gap: 34 }}>
      <Badge text={subheading || "ডেটা বিশ্লেষণ"} theme={theme} progress={headIn} />
      <div style={{ fontSize: 66, fontWeight: 800, color: theme.text, opacity: headIn, transform: `translateY(${(1 - headIn) * 24}px)` }}>
        {heading}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 26, marginTop: 10 }}>
        {parsed.map((row, i) => {
          const barP = spring({ frame: frame - 12 - i * 8, fps, config: { damping: 15 } });
          return (
            <div key={i} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 32, fontWeight: 700, color: theme.text }}>
                <span>{row.label}</span>
                <span style={{ color: theme.accent }}>{row.display}</span>
              </div>
              <div style={{ width: "100%", height: 28, borderRadius: 14, background: theme.cardBorder, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${row.val * barP}%`,
                    height: "100%",
                    borderRadius: 14,
                    background: `linear-gradient(90deg, ${theme.accent}, ${theme.secondary})`,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const DocGraphic = ({
  kind = "visual_callout",
  heading = "ডকুমেন্টারি তথ্য",
  subheading = "",
  items = [],
  videoTheme = "cinematic_dark",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = THEMES[videoTheme] || THEMES.cinematic_dark;

  return (
    <AbsoluteFill style={{ background: theme.bg, fontFamily: FONT, overflow: "hidden" }}>
      <GridBackdrop color={theme.grid} />
      {kind === "flowchart" ? (
        <FlowchartView heading={heading} subheading={subheading} items={items} theme={theme} frame={frame} fps={fps} />
      ) : kind === "route_map" ? (
        <RouteMapView heading={heading} subheading={subheading} items={items} theme={theme} frame={frame} fps={fps} />
      ) : kind === "stat_chart" ? (
        <StatChartView heading={heading} subheading={subheading} items={items} theme={theme} frame={frame} fps={fps} />
      ) : (
        <VisualCalloutView heading={heading} subheading={subheading} items={items} theme={theme} frame={frame} fps={fps} />
      )}
    </AbsoluteFill>
  );
};
