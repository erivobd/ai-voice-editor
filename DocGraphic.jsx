import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const FONT_STACK = "'Hind Siliguri', 'Noto Sans Bengali', 'Noto Sans', sans-serif";

const PALETTES = {
  cinematic_teal: {
    bg1: "#07101d",
    bg2: "#0e2238",
    accent: "#facc15",
    accent2: "#38bdf8",
    text: "#f8fafc",
    muted: "#cbd5e1",
  },
  warm_history: {
    bg1: "#140d09",
    bg2: "#291a10",
    accent: "#facc15",
    accent2: "#fb923c",
    text: "#fdf6ea",
    muted: "#d6c5ad",
  },
  cool_science: {
    bg1: "#080e20",
    bg2: "#132245",
    accent: "#facc15",
    accent2: "#38bdf8",
    text: "#f1f5f9",
    muted: "#a8bddb",
  },
  neutral_doc: {
    bg1: "#0b1120",
    bg2: "#172033",
    accent: "#facc15",
    accent2: "#38bdf8",
    text: "#f8fafc",
    muted: "#94a3b8",
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
  colorGrade = "cinematic_teal",
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const pal = PALETTES[colorGrade] || PALETTES.cinematic_teal;
  const mainAccent = accent === "red" ? "#ef4444" : pal.accent;
  const secAccent = pal.accent2;

  // Global subtle camera zoom + grid drift
  const camScale = interpolate(frame, [0, durationInFrames], [1.0, 1.045], {
    extrapolateRight: "clamp",
  });
  const gridShift = interpolate(frame, [0, durationInFrames], [0, 64]);

  // Header spring entrances
  const barProgress = spring({ frame, fps, config: { damping: 16, stiffness: 120 } });
  const titleSpring = spring({ frame: frame - 4, fps, config: { damping: 14, stiffness: 110 } });
  const subSpring = spring({ frame: frame - 10, fps, config: { damping: 15, stiffness: 105 } });
  const cardSpring = spring({ frame: frame - 14, fps, config: { damping: 16, stiffness: 95 } });

  const safeItems = Array.isArray(items) ? items.filter(Boolean).slice(0, 4) : [];

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 80% 20%, ${pal.bg2} 0%, ${pal.bg1} 72%)`,
        fontFamily: FONT_STACK,
        overflow: "hidden",
        color: pal.text,
      }}
    >
      {/* Animated Blueprint Grid */}
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(to right, rgba(56,189,248,0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(56,189,248,0.08) 1px, transparent 1px)`,
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
          background: `radial-gradient(circle, ${mainAccent}22 0%, transparent 70%)`,
          filter: "blur(30px)",
        }}
      />

      {/* Outer HUD Frame */}
      <div
        style={{
          position: "absolute",
          inset: 42,
          borderRadius: 24,
          border: "2px solid rgba(56, 189, 248, 0.18)",
          boxShadow: "inset 0 0 60px rgba(0,0,0,0.35)",
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
        {/* Top Tag & Animated Accent Bar */}
        <div style={{ display: "flex", alignItems: "center", gap: 18, marginBottom: 18 }}>
          <div
            style={{
              width: `${Math.round(barProgress * 120)}px`,
              height: 8,
              borderRadius: 4,
              background: mainAccent,
              boxShadow: `0 0 18px ${mainAccent}88`,
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

        {/* Kinetic Main Heading */}
        <div
          style={{
            fontSize: 74,
            fontWeight: 700,
            lineHeight: 1.18,
            color: pal.text,
            maxWidth: 1520,
            opacity: titleSpring,
            transform: `translateY(${interpolate(titleSpring, [0, 1], [34, 0])}px)`,
            textShadow: "0 8px 28px rgba(0,0,0,0.45)",
          }}
        >
          {heading}
        </div>

        {/* Subheading */}
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

        {/* Animated Template Body */}
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
              textColor={pal.text}
            />
          )}

          {kind === "timeline" && (
            <TimelineBody
              items={safeItems.length ? safeItems : ["ধাপ ১", "ধাপ ২", "ধাপ ৩"]}
              frame={frame}
              fps={fps}
              mainAccent={mainAccent}
              textColor={pal.text}
            />
          )}

          {kind === "map_marker" && (
            <MapMarkerBody
              items={safeItems}
              frame={frame}
              fps={fps}
              mainAccent={mainAccent}
              secAccent={secAccent}
              textColor={pal.text}
            />
          )}

          {kind !== "stat_chart" && kind !== "timeline" && kind !== "map_marker" && (
            <TitleCardBody
              items={safeItems}
              frame={frame}
              fps={fps}
              mainAccent={mainAccent}
              textColor={pal.text}
            />
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const glassCardStyle = {
  background: "rgba(15, 23, 42, 0.84)",
  border: "2px solid rgba(255, 255, 255, 0.16)",
  borderRadius: 24,
  boxShadow: "0 24px 60px rgba(0, 0, 0, 0.45)",
  position: "relative",
  overflow: "hidden",
};

const StatChartBody = ({ items, frame, fps, mainAccent, secAccent, textColor }) => {
  const maxVal = Math.max(...items.map((x) => x.val), 1);

  return (
    <div style={{ ...glassCardStyle, width: "100%", padding: "40px 52px 44px 64px" }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 26,
          bottom: 26,
          width: 10,
          borderRadius: 5,
          background: mainAccent,
        }}
      />
      <div style={{ display: "flex", flexDirection: "column", gap: 30 }}>
        {items.map((item, idx) => {
          const delay = 18 + idx * 8;
          const prog = spring({ frame: frame - delay, fps, config: { damping: 16, stiffness: 85 } });
          const pct = Math.max(8, (item.val / maxVal) * 100) * prog;
          const displayVal = Math.round(item.val * prog * 10) / 10;
          const barColor = idx === items.length - 1 ? mainAccent : secAccent;

          return (
            <div key={idx} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <span style={{ fontSize: 32, fontWeight: 600, color: textColor }}>{item.label}</span>
                <span style={{ fontSize: 34, fontWeight: 700, color: barColor }}>
                  {Number.isInteger(item.val) ? Math.round(displayVal) : displayVal}
                </span>
              </div>
              <div
                style={{
                  width: "100%",
                  height: 26,
                  borderRadius: 13,
                  background: "rgba(255,255,255,0.10)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${pct}%`,
                    height: "100%",
                    borderRadius: 13,
                    background: `linear-gradient(90deg, ${barColor}cc, ${barColor})`,
                    boxShadow: `0 0 18px ${barColor}66`,
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

const TimelineBody = ({ items, frame, fps, mainAccent, textColor }) => {
  const lineProg = spring({ frame: frame - 16, fps, config: { damping: 18, stiffness: 70 } });

  return (
    <div style={{ ...glassCardStyle, width: "100%", padding: "70px 64px" }}>
      <div style={{ position: "relative", height: 220, display: "flex", alignItems: "center" }}>
        {/* Animated Track */}
        <div
          style={{
            position: "absolute",
            left: 40,
            right: 40,
            top: 76,
            height: 6,
            background: "rgba(255,255,255,0.12)",
            borderRadius: 3,
          }}
        >
          <div
            style={{
              width: `${lineProg * 100}%`,
              height: "100%",
              background: mainAccent,
              borderRadius: 3,
              boxShadow: `0 0 16px ${mainAccent}88`,
            }}
          />
        </div>

        {/* Nodes */}
        <div
          style={{
            position: "relative",
            zIndex: 2,
            width: "100%",
            display: "flex",
            justifyContent: "space-between",
            padding: "0 20px",
          }}
        >
          {items.map((label, idx) => {
            const nodeSpring = spring({
              frame: frame - (20 + idx * 10),
              fps,
              config: { damping: 12, stiffness: 120 },
            });
            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  width: 320,
                  opacity: nodeSpring,
                  transform: `scale(${interpolate(nodeSpring, [0, 1], [0.6, 1])})`,
                }}
              >
                <div
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: "50%",
                    border: `3px solid ${mainAccent}77`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: "#0b1120",
                  }}
                >
                  <div
                    style={{
                      width: 20,
                      height: 20,
                      borderRadius: "50%",
                      background: mainAccent,
                      boxShadow: `0 0 16px ${mainAccent}`,
                    }}
                  />
                </div>
                <div
                  style={{
                    marginTop: 28,
                    fontSize: 30,
                    fontWeight: 600,
                    textAlign: "center",
                    color: textColor,
                    lineHeight: 1.3,
                  }}
                >
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

const MapMarkerBody = ({ items, frame, fps, mainAccent, secAccent, textColor }) => {
  const sweepDeg = (frame * 3.2) % 360;
  const pulse = (frame % 45) / 45;

  return (
    <div style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 60 }}>
      {/* Left Intelligence Card */}
      <div style={{ ...glassCardStyle, flex: 1, padding: "40px 44px 40px 56px", minHeight: 280 }}>
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 24,
            bottom: 24,
            width: 10,
            borderRadius: 5,
            background: mainAccent,
          }}
        />
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {(items.length ? items : ["ভৌগোলিক অবস্থান বিশ্লেষণ", "গুরুত্বপূর্ণ তথ্য পয়েন্ট"]).map((it, idx) => {
            const p = spring({ frame: frame - (18 + idx * 9), fps, config: { damping: 15, stiffness: 100 } });
            return (
              <div
                key={idx}
                style={{
                  fontSize: 34,
                  fontWeight: 600,
                  color: textColor,
                  display: "flex",
                  alignItems: "center",
                  gap: 18,
                  opacity: p,
                  transform: `translateX(${interpolate(p, [0, 1], [-28, 0])}px)`,
                }}
              >
                <span style={{ color: mainAccent, fontSize: 24 }}>●</span>
                <span>{String(it).slice(0, 42)}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Right Animated Radar Target */}
      <div
        style={{
          width: 440,
          height: 440,
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            position: "absolute",
            width: 420,
            height: 420,
            borderRadius: "50%",
            border: `2px solid ${secAccent}44`,
          }}
        />
        <div
          style={{
            position: "absolute",
            width: 280,
            height: 280,
            borderRadius: "50%",
            border: `2px solid ${mainAccent}66`,
          }}
        />
        {/* Expanding Sonar Ring */}
        <div
          style={{
            position: "absolute",
            width: `${80 + pulse * 320}px`,
            height: `${80 + pulse * 320}px`,
            borderRadius: "50%",
            border: `3px solid ${mainAccent}`,
            opacity: 1 - pulse,
          }}
        />
        {/* Rotating Radar Sweep */}
        <div
          style={{
            position: "absolute",
            width: 420,
            height: 420,
            borderRadius: "50%",
            background: `conic-gradient(from ${sweepDeg}deg, ${secAccent}44 0deg, transparent 70deg)`,
          }}
        />
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: mainAccent,
            boxShadow: `0 0 28px ${mainAccent}`,
            zIndex: 2,
          }}
        />
      </div>
    </div>
  );
};

const TitleCardBody = ({ items, frame, fps, mainAccent, textColor }) => {
  if (!items.length) return null;
  return (
    <div style={{ ...glassCardStyle, width: "86%", padding: "38px 48px 38px 60px" }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 24,
          bottom: 24,
          width: 10,
          borderRadius: 5,
          background: mainAccent,
        }}
      />
      <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
        {items.map((it, idx) => {
          const p = spring({ frame: frame - (18 + idx * 9), fps, config: { damping: 15, stiffness: 105 } });
          return (
            <div
              key={idx}
              style={{
                fontSize: 34,
                fontWeight: 600,
                color: textColor,
                opacity: p,
                transform: `translateY(${interpolate(p, [0, 1], [22, 0])}px)`,
                display: "flex",
                alignItems: "center",
                gap: 18,
              }}
            >
              <span style={{ color: mainAccent, fontWeight: 700 }}>—</span>
              <span>{String(it).slice(0, 56)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
