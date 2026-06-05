import React from "react";
import { Composition } from "remotion";
import { FPS } from "./theme";
import { Main, TOTAL_FRAMES } from "./Main";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="LongevityOS"
      component={Main}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={1920}
      height={1080}
    />
  );
};
