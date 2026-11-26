import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const FONT_STACK = "'Hind Siliguri', 'Noto Sans Bengali', 'Noto Sans', sans-serif";

const THEMES = {
  cinematic_dark: {
    bg: "radial-gradient(circle at 80% 20%, #0e2238 0%, #07101d 72%)",
    gridColor: "rgba(56,189,248,0.08)",
    hudBorder: "rgba(56, 189, 248, 0.18)",
    cardBg: "rgba(15, 23, 42, 0.84)",
    cardBorder: "rgba(255, 255, 255, 0.16)",
    trackBg: "rgba(255, 255, 255, 0.12)",
    nodeInnerBg: "#0b1120",
    accent: "#facc15",
    accent2: "#38bdf8",
    text: "#f8fafc",
    isLight: false,
  },
  vox_colorful: {
    bg: "linear-gradient(135deg, #fef08a 0%, #fde047 55%, #facc15 100%)",
    gridColor: "rgba(17,24,39,0.07)",
    hudBorder: "rgba(17, 24, 39, 0.20)",
    cardBg: "rgba(255, 255, 255, 0.94)",
    cardBorder: "rgba(17, 24, 39, 0.16)",
    trackBg: "rgba(17, 24, 39, 0.12)",
    nodeInnerBg: "#ffffff",
    accent: "#dc2626",
    accent2: "#111827",
    text: "#111827",
    isLight: true,
  },
  editorial_paper: {
    bg: "radial-gradient(circle at 20% 20%, #fffdf7 0%, #efe6d5 100%)",
    gridColor: "rgba(120, 113, 108, 0.10)",
    hudBorder: "rgba(120, 113, 108, 0.25)",
    cardBg: "rgba(255, 253, 249, 0.92)",
    cardBorder: "rgba(120, 113, 108, 0.22)",
    trackBg: "rgba(28, 25, 23, 0.12)",
    nodeInnerBg: "#fffdf9",
    accent: "#d97706",
    accent2: "#0f766e",
    text: "#1c1917",
    isLight: true,
  },
  vibrant_gradient: {
    bg: "linear-gradient(135deg, #1e1b4b 0%, #4c1d95 50%, #0f172a 100%)",
    gridColor: "rgba(34, 211, 238, 0.10)",
    hudBorder: "rgba(244, 114, 182, 0.28)",
    cardBg: "rgba(30, 27, 75, 0.78)",
    cardBorder: "rgba(255, 255, 255, 0.22)",
    trackBg: "rgba(255, 255, 255, 0.16)",
    nodeInnerBg: "#1e1b4b",
    accent: "#22d3ee",
    accent2: "#f472b6",
    text: "#ffffff",
    isLight: false,
  },
  minimal_light: {
    bg: "linear-gradient(180deg, #ffffff 0%, #e2e8f0 100%)",
    gridColor: "rgba(15, 23, 42, 0.06)",
    hudBorder: "rgba(37, 99, 235, 0.20)",
    cardBg: "rgba(255, 255, 255, 0.95)",
    cardBorder: "rgba(15, 23, 42, 0.10)",
    trackBg: "rgba(15, 23, 42, 0.10)",
    nodeInnerBg: "#ffffff",
    accent: "#2563eb",
    accent2: "#10b981",
    text: "#0f172a",
    isLight: true,
  },
};

const parseStatItems = (items) => {
  const list = Array.isArray(items) ? items.slice(0, 4) : [];
  const parsed = list.map((raw, idx) => {
    const str = String(raw || "");
    const m = str.match(/([0-9]+(?:\.[0-9]+)?)/);
    const val = m ? parseFloat(m[1]) : (idx + 1) * 25;
    const label = str.replace(/[:\-]?\s*[0-9]+(?:\.[0-9]+)?%?/, "").trim() || str || `ধাপ ${idx + 1}`;
    return { label: label.slice(0, 32), val };
  });
  if (parsed.length === 0) {
    return [
      { label: "প্রাথমিক ধাপ", val: 38 },
      { label: "মধ্যম পর্যায়", val: 72 },
      { label: "সর্বোচ্চ মাত্রা", val: 100 },
    ];
  }
  return parsed;
};

export const DocGraphic = ({
  kind = "title_card",
  heading = "ডকুমেন্টারি তথ্য",
  subheading = "",
  items = [],
  accent = "gold",
  videoTheme = "cinematic_dark",
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const theme = THEMES[videoTheme] || THEMES.cinematic_dark;
  const mainAccent = accent === "red" && !theme.isLight ? "#ef4444" : theme.accent;
  const secAccent = theme.accent2;

  const camScale = interpolate(frame, [0, durationInFrames], [1.0, 1.045], {
    extrapolateRight: "clamp",
  });
  const gridShift = interpolate(frame, [0, durationInFrames], [0, 64]);

  const barProgress = spring({ frame, fps, config: { damping: 16, stiffness: 120 } });
  const titleSpring = spring({ frame: frame - 4, fps, config: { damping: 14, stiffness: 110 } });
  const subSpring = spring({ frame: frame - 10, fps, config: { damping: 15, stiffness: 105 } });
  const cardSpring = spring({ frame: frame - 14, fps, config: { damping: 16, stiffness: 95 } });

  const safeItems = Array.isArray(items) ? items.filter(Boolean).slice(0, 4) : [];

  const cardStyle = {
    background: theme.cardBg,
    border: `2px solid ${theme.cardBorder}`,
    borderRadius: 24,
    boxShadow: theme.isLight
      ? "0 20px 50px rgba(15, 23, 42, 0.12)"
      : "0 24px 60px rgba(0, 0, 0, 0.45)",
    position: "relative",
    overflow: "hidden",
  };

  return (
    <AbsoluteFill
      style={{
        background: theme.bg,
        fontFamily: FONT_STACK,
        overflow: "hidden",
        color: theme.text,
      }}
    >
      {/* Animated Grid */}
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(to right, ${theme.gridColor} 1px, transparent 1px), linear-gradient(to bottom, ${theme.gridColor} 1px, transparent 1px)`,
          backgroundSize: "64px 64px",
          backgroundPosition: `${gridShift}px ${gridShift * 0.5}px`,
          transform: `scale(${camScale})`,
        }}
      />

      {/* Ambient Glow Orb */}
      <div
        style={{
          position: "absolute",
          right: -140,
          top: -120,
          width: 680,
          height: 680,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${mainAccent}26 0%, transparent 70%)`,
          filter: "blur(30px)",
        }}
      />

      {/* Outer HUD Frame */}
      <div
        style={{
          position: "absolute",
          inset: 42,
          borderRadius: 24,
          border: `2px solid ${theme.hudBorder}`,
          pointerEvents: "none",
        }}
      />

      {/* Content Container */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          padding: "110px 140px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "flex-start",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18, marginBottom: 18 }}>
          <div
            style={{
              width: `${Math.round(barProgress * 120)}px`,
              height: 8,
              borderRadius: 4,
              background: mainAccent,
            }}
          />
          <span
            style={{
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: 4,
              color: secAccent,
              opacity: barProgress,
              textTransform: "uppercase",
            }}
          >
            DOCUMENTARY ANALYSIS
          </span>
        </div>

        <div
          style={{
            fontSize: 74,
            fontWeight: 700,
            lineHeight: 1.18,
            color: theme.text,
            maxWidth: 1520,
            opacity: titleSpring,
            transform: `translateY(${interpolate(titleSpring, [0, 1], [34, 0])}px)`,
          }}
        >
          {heading}
        </div>

        {subheading ? (
          <div
            style={{
              marginTop: 14,
              fontSize: 36,
              fontWeight: 600,
              color: mainAccent,
              maxWidth: 1450,
              opacity: subSpring,
              transform: `translateY(${interpolate(subSpring, [0, 1], [24, 0])}px)`,
            }}
          >
            {subheading}
          </div>
        ) : null}

        <div
          style={{
            marginTop: 52,
            flex: 1,
            display: "flex",
            alignItems: "center",
            opacity: cardSpring,
            transform: `translateY(${interpolate(cardSpring, [0, 1], [36, 0])}px)`,
          }}
        >
          {kind === "stat_chart" && (
            <StatChartBody
              items={parseStatItems(safeItems)}
              frame={frame}
              fps={fps}
              mainAccent={mainAccent}
              secAccent={secAccent}
              theme={theme}
              cardStyle={cardStyle}
            />
          )}

          {kind === "timeline" && (
            <TimelineBody
              items={safeItems.length ? safeItems : ["ধাপ ১", "ধাপ ২", "ধাপ ৩"]}
              frame={frame}
              fps={fps}
              mainAccent={mainAccent}
              theme={theme}
              cardStyle={cardStyle}
            />
          )}

          {kind === "map_marker" && (
            <MapMarkerBody
              items={safeItems}
              frame={frame}
              fps={fps}
              mainAccent={mainAccent}
              secAccent={secAccent}
              theme={theme}
              cardStyle={cardStyle}
            />
          )}

          {kind !== "stat_chart" && kind !== "timeline" && kind !== "map_marker" && (
            <TitleCardBody
              items={safeItems}
              frame={frame}
              fps={fps}
              mainAccent={mainAccent}
              theme={theme}
              cardStyle={cardStyle}
            />
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const StatChartBody = ({ items, frame, fps, mainAccent, secAccent, theme, cardStyle }) => {
  const maxVal = Math.max(...items.map((x) => x.val), 1);

  return (
    <div style={{ ...cardStyle, width: "100%", padding: "40px 52px 44px 64px" }}>
      <div style={{ position: "absolute", left: 0, top: 26, bottom: 26, width: 10, borderRadius: 5, background: mainAccent }} />
      <div style={{ display: "flex", flexDirection: "column", gap: 30 }}>
        {items.map((item, idx) => {
          const prog = spring({ frame: frame - (18 + idx * 8), fps, config: { damping: 16, stiffness: 85 } });
          const pct = Math.max(8, (item.val / maxVal) * 100) * prog;
          const displayVal = Math.round(item.val * prog * 10) / 10;
          const barColor = idx === items.length - 1 ? mainAccent : secAccent;

          return (
            <div key={idx} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <span style={{ fontSize: 32, fontWeight: 600, color: theme.text }}>{item.label}</span>
                <span style={{ fontSize: 34, fontWeight: 700, color: barColor }}>
                  {Number.isInteger(item.val) ? Math.round(displayVal) : displayVal}
                </span>
              </div>
              <div style={{ width: "100%", height: 26, borderRadius: 13, background: theme.trackBg, overflow: "hidden" }}>
                <div style={{ width: `${pct}%`, height: "100%", borderRadius: 13, background: barColor }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const TimelineBody = ({ items, frame, fps, mainAccent, theme, cardStyle }) => {
  const lineProg = spring({ frame: frame - 16, fps, config: { damping: 18, stiffness: 70 } });

  return (
    <div style={{ ...cardStyle, width: "100%", padding: "70px 64px" }}>
      <div style={{ position: "relative", height: 220, display: "flex", alignItems: "center" }}>
        <div style={{ position: "absolute", left: 40, right: 40, top: 76, height: 6, background: theme.trackBg, borderRadius: 3 }}>
          <div style={{ width: `${lineProg * 100}%`, height: "100%", background: mainAccent, borderRadius: 3 }} />
        </div>
        <div style={{ position: "relative", zIndex: 2, width: "100%", display: "flex", justifyContent: "space-between", padding: "0 20px" }}>
          {items.map((label, idx) => {
            const nodeSpring = spring({ frame: frame - (20 + idx * 10), fps, config: { damping: 12, stiffness: 120 } });
            return (
              <div
                key={idx}
                style={{
                  display: "flex", flexDirection: "column", alignItems: "center", width: 320,
                  opacity: nodeSpring, transform: `scale(${interpolate(nodeSpring, [0, 1], [0.6, 1])})`,
                }}
              >
                <div style={{ width: 44, height: 44, borderRadius: "50%", border: `3px solid ${mainAccent}`, display: "flex", alignItems: "center", justifyContent: "center", background: theme.nodeInnerBg }}>
                  <div style={{ width: 20, height: 20, borderRadius: "50%", background: mainAccent }} />
                </div>
                <div style={{ marginTop: 28, fontSize: 30, fontWeight: 600, textAlign: "center", color: theme.text, lineHeight: 1.3 }}>
                  {String(label).slice(0, 30)}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

const MapMarkerBody = ({ items, frame, fps, mainAccent, secAccent, theme, cardStyle }) => {
  const sweepDeg = (frame * 3.2) % 360;
  const pulse = (frame % 45) / 45;

  return (
    <div style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 60 }}>
      <div style={{ ...cardStyle, flex: 1, padding: "40px 44px 40px 56px", minHeight: 280 }}>
        <div style={{ position: "absolute", left: 0, top: 24, bottom: 24, width: 10, borderRadius: 5, background: mainAccent }} />
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {(items.length ? items : ["ভৌগোলিক অবস্থান বিশ্লেষণ", "গুরুত্বপূর্ণ তথ্য পয়েন্ট"]).map((it, idx) => {
            const p = spring({ frame: frame - (18 + idx * 9), fps, config: { damping: 15, stiffness: 100 } });
            return (
              <div key={idx} style={{ fontSize: 34, fontWeight: 600, color: theme.text, display: "flex", alignItems: "center", gap: 18, opacity: p, transform: `translateX(${interpolate(p, [0, 1], [-28, 0])}px)` }}>
                <span style={{ color: mainAccent, fontSize: 24 }}>●</span>
                <span>{String(it).slice(0, 42)}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ width: 440, height: 440, position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "absolute", width: 420, height: 420, borderRadius: "50%", border: `2px solid ${secAccent}55` }} />
        <div style={{ position: "absolute", width: 280, height: 280, borderRadius: "50%", border: `2px solid ${mainAccent}77` }} />
        <div style={{ position: "absolute", width: `${80 + pulse * 320}px`, height: `${80 + pulse * 320}px`, borderRadius: "50%", border: `3px solid ${mainAccent}`, opacity: 1 - pulse }} />
        <div style={{ position: "absolute", width: 420, height: 420, borderRadius: "50%", background: `conic-gradient(from ${sweepDeg}deg, ${secAccent}44 0deg, transparent 70deg)` }} />
        <div style={{ width: 28, height: 28, borderRadius: "50%", background: mainAccent, zIndex: 2 }} />
      </div>
    </div>
  );
};

const TitleCardBody = ({ items, frame, fps, mainAccent, theme, cardStyle }) => {
  if (!items.length) return null;
  return (
    <div style={{ ...cardStyle, width: "86%", padding: "38px 48px 38px 60px" }}>
      <div style={{ position: "absolute", left: 0, top: 24, bottom: 24, width: 10, borderRadius: 5, background: mainAccent }} />
      <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
        {items.map((it, idx) => {
          const p = spring({ frame: frame - (18 + idx * 9), fps, config: { damping: 15, stiffness: 105 } });
          return (
            <div key={idx} style={{ fontSize: 34, fontWeight: 600, color: theme.text, opacity: p, transform: `translateY(${interpolate(p, [0, 1], [22, 0])}px)`, display: "flex", alignItems: "center", gap: 18 }}>
              <span style={{ color: mainAccent, fontWeight: 700 }}>—</span>
              <span>{String(it).slice(0, 56)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
