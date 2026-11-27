import React from "react";
import { Composition } from "remotion";
import { Main } from "./Video";
import scene from "./scene.json";
export const RemotionRoot: React.FC = () => <Composition id="Main" component={Main} defaultProps={scene as any} durationInFrames={(scene as any).duration} fps={(scene as any).fps} width={(scene as any).width} height={(scene as any).height} />;
