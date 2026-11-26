import React from "react";
import { Composition } from "remotion";
import { DocGraphic } from "./DocGraphic";

export const RemotionRoot = () => {
  return (
    <Composition
      id="DocGraphic"
      component={DocGraphic}
      width={1920}
      height={1080}
      fps={30}
      durationInFrames={150}
      defaultProps={{
        kind: "stat_chart",
        heading: "ডকুমেন্টারি তথ্য",
        subheading: "স্বয়ংক্রিয় মোশন গ্রাফিক্স",
        items: ["ধাপ ১: 35", "ধাপ ২: 68", "ধাপ ৩: 100"],
        accent: "gold",
        colorGrade: "cinematic_teal",
        duration: 5.0,
      }}
      calculateMetadata={({ props }) => {
        const dur = Math.max(1.5, Number(props.duration || 5.0));
        return {
          durationInFrames: Math.max(45, Math.round(dur * 30)),
          fps: 30,
          width: 1920,
          height: 1080,
        };
      }}
    />
  );
};
