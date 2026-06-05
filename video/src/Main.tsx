import React from "react";
import { AbsoluteFill, Series, Audio, staticFile } from "remotion";
import { fontCssVars } from "./fonts";
import { colors, sec } from "./theme";
import { SCENES } from "./script";
import { DURATIONS } from "./durations";
import { AUDIO_IDS, HAS_MUSIC } from "./audioManifest";
import { Scene } from "./components/Scene";

import { Title } from "./scenes/Title";
import { Problem } from "./scenes/Problem";
import { Dataset } from "./scenes/Dataset";
import { JEPA } from "./scenes/JEPA";
import { Agentic } from "./scenes/Agentic";
import { HowItWorks } from "./scenes/HowItWorks";
import { Dashboard } from "./scenes/Dashboard";
import { Evidence } from "./scenes/Evidence";
import { Interventions } from "./scenes/Interventions";
import { Evaluation } from "./scenes/Evaluation";
import { Disclosure } from "./scenes/Disclosure";
import { Close } from "./scenes/Close";

const COMPONENTS: Record<string, React.FC> = {
  title: Title,
  problem: Problem,
  dataset: Dataset,
  jepa: JEPA,
  agentic: Agentic,
  howitworks: HowItWorks,
  dashboard: Dashboard,
  evidence: Evidence,
  interventions: Interventions,
  evaluation: Evaluation,
  disclosure: Disclosure,
  close: Close,
};

// Per-scene chrome (brand mark + rubric chip) and theme.
const CONFIG: Record<string, { chrome?: boolean; ink?: boolean }> = {
  title: { chrome: false },
  close: { chrome: false, ink: true },
};

// Resolve a scene's frame count: measured audio duration wins, else script fallback.
export const sceneFrames = (id: string, fallbackS: number) =>
  sec(DURATIONS[id] ?? fallbackS);

export const TOTAL_FRAMES = SCENES.reduce(
  (acc, s) => acc + sceneFrames(s.id, s.durationS),
  0
);

export const Main: React.FC = () => {
  return (
    <AbsoluteFill style={{ ...fontCssVars, background: colors.bg }}>
      {HAS_MUSIC && (
        <Audio src={staticFile("audio/music.mp3")} volume={0.12} loop />
      )}
      <Series>
        {SCENES.map((s) => {
          const Cmp = COMPONENTS[s.id];
          const cfg = CONFIG[s.id] ?? {};
          const frames = sceneFrames(s.id, s.durationS);
          return (
            <Series.Sequence key={s.id} durationInFrames={frames}>
              {AUDIO_IDS.includes(s.id) && (
                <Audio src={staticFile(`audio/${s.id}.mp3`)} />
              )}
              <Scene
                rubric={s.rubric}
                caption={s.caption}
                chrome={cfg.chrome}
                ink={cfg.ink}
                durationInFrames={frames}
              >
                <Cmp />
              </Scene>
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
