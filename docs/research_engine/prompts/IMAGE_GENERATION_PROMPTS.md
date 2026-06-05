# Image Generation Prompts for Hypothesis Discovery System

## Global Style Specification (apply to ALL images)

```
STYLE: Clean, minimal scientific infographic in the style of Nature Methods / Nature Machine Intelligence system diagrams. White background. Flat vector design with no gradients, no 3D, no drop shadows, no skeuomorphism. Thin lines (1-1.5pt). Rounded rectangle components (8px radius). Sans-serif typography (Inter, Helvetica, or SF Pro). Limited color palette: primary blue (#0072B2), amber (#E69F00), teal (#009E73), vermillion (#D55E00), pink (#CC79A7), dark gray (#333333), light gray (#F5F5F5). High information density with generous whitespace between components. All text must be crisp and readable at 50% zoom. 16:9 aspect ratio (1920×1080px). No decorative elements — every visual element encodes information.
```

---

## FIGURE 1: Full Pipeline Workflow

```
Create a scientific system architecture diagram showing an autonomous hypothesis-driven discovery pipeline. White background, 16:9 ratio.

TOP ROW (Hypothesis Generation):
Two input sources side by side on the left:
- A blue (#0072B2) rounded rectangle labeled "Theory-Driven" containing three bullet items in small text: "Literature & physiology", "Mechanistic predictions", "Known timescales". A small open-book icon in the top-left corner.
- An amber (#E69F00) rounded rectangle labeled "Data-Driven" containing: "Null result patterns", "Surprising findings", "Anomaly detection". A small lightning-bolt icon in the top-left corner.

Both sources have thin arrows pointing into a larger blue component labeled "PROPOSER AGENT" with a small badge reading "LLM" in the corner. Inside the proposer box, show a small JSON-like structured card: "{ statement, mechanism, direction, timescale, controls }".

A thick gray arrow flows right from the Proposer into an amber component labeled "CRITIC AGENT" with an "LLM" badge. Inside, show a compact checklist icon with "10 constraints" and score bars for "rigor | plausibility | novelty". From the Critic, two paths emerge: a green arrow going down labeled "validated" and a red arrow going to a faded "REJECTED" label with an X.

MIDDLE ROW (Workspace):
A wide, light gray (#F5F5F5) rounded rectangle spanning the center, labeled "HYPOTHESIS WORKSPACE" in bold. Inside, show a horizontal chain of 6 small colored pill badges connected by tiny arrows: "proposed" (light blue) → "critiqued" (amber) → "validated" (green) → "executing" (teal) → "completed" (blue) → "verified" (dark). Below the pills, show a tiny miniature table grid suggesting the hypothesis inventory (3-4 rows, faintly visible). A small JSON file icon on the right edge indicates persistence.

BOTTOM ROW (Execution & Verification):
On the left, a teal (#009E73) component labeled "EXECUTOR AGENT" with badges "LLM" and "Code". Inside, show 4 small sequential icons: a code bracket, a server/cluster icon, a clock/spinner, and a download icon, representing "Generate → Submit → Monitor → Collect". Below the executor, show a small cluster illustration with "32 parallel shards" label.

A gray arrow flows right into a pink (#CC79A7) component labeled "VERIFIER AGENT" with a badge "Rules + LLM". Inside, show a 3×3 grid of small green checkmark circles representing 9 checks. Below, show three output paths: green arrow to "supported", red arrow to "refuted", gray arrow to "inconclusive".

FEEDBACK LOOPS (connecting bottom back to top):
Three distinct dashed curved arrows flowing from the bottom-right back up to the top-left inputs:
1. A vermillion dashed arrow from "refuted" back to "Data-Driven", labeled "Null result learning"
2. An amber dashed arrow from somewhere near "completed" (with a star icon) back to "Data-Driven", labeled "Surprise escalation"
3. A green dashed arrow from "supported" back to "Theory-Driven", labeled "Hypothesis deepening"

BOTTOM BAR:
A thin horizontal strip at the very bottom showing 7 small icons with labels: "Direction | Timescale | Refutation | Neg. Control | Confounders | Unique Enabler | Effect Size" with the caption "Every hypothesis must specify all 7 before entering execution queue".

The overall composition should read as a clear top-to-bottom flow (generation → workspace → execution → verification) with feedback loops creating a visible cycle. Use color consistently: blue = generation, amber = critique, teal = execution, pink = verification, gray = storage.
```

---

## FIGURE 2: Dual-Mode Hypothesis Generation

```
Create a side-by-side comparison diagram showing two parallel pathways that converge into a single pipeline. White background, 16:9.

LEFT COLUMN — "Theory-Driven" (all borders in blue #0072B2):
A vertical sequence of 5 rounded rectangles connected by downward arrows:
1. "Literature + Known Physiology" — with a small book icon
2. "Mechanistic Prediction" — with a brain/gear icon (e.g., "Vagal denervation → HR buffering impaired")
3. "Specific Falsifiable Claim" — with a target icon (e.g., "HR peak blunted by d > 0.4, strongest 15-90min post-excursion")
4. "Designed Test with Controls" — with a flask/experiment icon
5. "Structured Result + Verdict" — with a checkmark icon, green border

The column title "Theory-Driven" is in blue, bold, at the top. A small annotation reads "Mechanism BEFORE measurement".

RIGHT COLUMN — "Data-Driven" (all borders in amber #E69F00):
Same vertical sequence of 5 boxes:
1. "Unexpected Result or Anomaly" — with a lightning icon (e.g., "Broadband coupling increases — opposite to prediction")
2. "Formalize into Mechanism" — with a brain icon (e.g., "Fast vs slow coupling may be distinct processes")
3. "Add Direction, Timescale, Controls" — same structure as left column box 3
4. "Same Execution Pipeline" — border changes to blue, indicating convergence
5. "Same Verification" — green border, matching left column

The column title "Data-Driven" is in amber. A small annotation reads "Observation THEN mechanism".

CONVERGENCE ZONE:
At boxes 4 and 5, draw a light gray shaded region spanning both columns, with a label: "Identical quality gate — Critic cannot distinguish source". The last two boxes in each column should be connected by a horizontal double-headed arrow or a shared background, emphasizing convergence.

BOTTOM CAPTION:
"Both modes produce identical structured JSON output → same 10-constraint quality gate → same 9-check verification"

Show a concrete example flow on each side in very small italic text:
- Left: "Autonomic neuropathy literature → post-excursion HR blunting → d = −0.80 SUPPORTED"
- Right: "H-MIG01 surprise (coupling increases) → frequency decomposition → fast↓ slow↑ PARTIAL"
```

---

## FIGURE 3: Hypothesis Deepening Tree

```
Create a tree/genealogy diagram showing how hypotheses deepen from broad to specific findings. White background, 16:9.

ROOT NODE (top center):
A large green-bordered (#009E73) rounded rectangle:
"H-MIG01: Broadband glucose-HR coupling increases with diabetes severity"
Below: "d = 0.59 | FDR < 10⁻¹⁹ | SUPPORTED"
Color: green fill tint, indicating supported status.

LEVEL 1 (two children, left and right):

Left child — blue-bordered (#0072B2):
"H-NEW01: Frequency decomposition"
Below: "Fast ↓ (d = −0.22) | Slow ↑ (d = +0.38) | PARTIAL"
Connected to root by a solid blue arrow.
A small vermillion (#D55E00) starburst/callout near this node: "SURPRISE: direction flips at 2h boundary" — this indicates a data-driven observation.

Right child — blue-bordered:
"H-NEW17: Diurnal profile"
Below: "Day ↑ (d = 0.47) | Night = (d = −0.05) | PARTIAL"
Connected to root by a solid blue arrow.

LEVEL 2 (two grandchildren):

Left grandchild — green-bordered (under H-NEW01):
"H-NEW03: Post-excursion HR blunting"
Below: "d = −0.80 | 9/9 robustness | SUPPORTED ★"
The star indicates flagship finding. This box is slightly larger or has a subtle glow/emphasis.
Connected to H-NEW01 by a solid green arrow.
A small annotation: "Theory-driven: autonomic neuropathy mechanism"

Right grandchild — gray-bordered (under H-NEW17):
"H-NEW06: Nocturnal coupling → next-day glucose"
Below: "ρ = −0.004 | p = 0.67 | NULL ✗"
Gray/faded appearance indicating null result.
Connected to H-NEW17 by a gray arrow.
A small annotation: "Pruned: nocturnal coupling is preserved, not predictive"

SIDE ANNOTATIONS (right margin):
Three labeled arrows or icons:
1. Green downward arrow: "Deepening — supported findings spawn more specific tests"
2. Vermillion star: "Surprise — unexpected results seed data-driven hypotheses"
3. Gray scissors/prune icon: "Pruning — null results close off fruitless directions"

EFFECT SIZE PROGRESSION (bottom):
A small horizontal bar at the bottom showing effect sizes growing through the tree:
"d = 0.59 → d = 0.38 / −0.22 → d = −0.80"
With annotation: "More specific hypotheses yield stronger, more interpretable effects"
```

---

## FIGURE 4: 7 Quality Requirements

```
Create an infographic showing 7 mandatory requirements for hypothesis quality. White background, 16:9.

Layout: 7 cards arranged in a 4+3 grid (4 on top row, 3 on bottom row, centered).

Each card is a rounded rectangle with:
- A numbered circle badge (1-7) in the top-left corner, filled with the card's accent color
- A bold title
- A 2-line description in smaller text
- A small concrete example in italic at the bottom

Card 1 (blue #0072B2): "Direction"
Description: "Expected direction of effect, not just 'differs'"
Example: "HR peak is blunted (lower) in insulin-dependent"

Card 2 (sky blue #56B4E9): "Timescale"
Description: "Specific lag or period range"
Example: "Strongest 15-90 min after glucose excursions"

Card 3 (vermillion #D55E00): "Refutation Criterion"
Description: "What specific result would kill this hypothesis?"
Example: "No group difference after adjusting for excursion magnitude"

Card 4 (amber #E69F00): "Negative Control"
Description: "What comparison should show NO effect?"
Example: "Random non-excursion windows show no group difference"

Card 5 (teal #009E73): "Confounders"
Description: "Minimum: age, site, HbA1c, BMI"
Example: "Survives full adjustment including glucose mean, HR mean"

Card 6 (pink #CC79A7): "Unique Enabler"
Description: "Why can only AI-READI test this?"
Example: "Only dataset with synchronized CGM + wearable HR at N > 2000"

Card 7 (dark #333333): "Expected Effect Size"
Description: "Quantitative prediction, not just significance"
Example: "Cohen's d ~ 0.3-0.5 for insulin vs healthy"

HEADER: "7 Quality Gates — Every Hypothesis Must Pass Before Execution"
FOOTER: A thin bar reading "Prevents: vague claims, fishing expeditions, untestable hypotheses, post-hoc rationalization"
```

---

## FIGURE 5: Hypothesis Overview Table

```
Create a visual hypothesis dashboard/table showing the status of all tested hypotheses. White background, 16:9.

Layout: A clean data table with visual encodings, not just text. Each row represents one hypothesis.

COLUMNS:
1. ID (text, bold, monospace)
2. Status (colored pill badge: green for supported, blue for completed, amber for critiqued, red for refuted, gray for null/inconclusive)
3. Category (text, light gray)
4. Finding (1-line summary)
5. Effect Size (horizontal bar chart, proportional to |d|, green if FDR < 0.05, gray if not)
6. Robustness (small dot grid showing X/9 checks passed, like a miniature progress indicator)

ROWS (top to bottom, ordered by effect size):
H-NEW03 | supported ● | event_dynamics | Post-excursion HR blunting | ████████████ d=0.80 | ●●●●●●●●● 9/9
H-MIG01 | supported ● | temporal_coupling | Broadband coupling increase | ████████░░ d=0.59 | —
H-NEW17 | completed ● | circadian | Diurnal coupling elevation (day only) | ██████░░░░ d=0.47 | —
H-NEW01 | completed ● | frequency | Fast↓ slow↑ timescale flip | █████░░░░░ d=0.38 | ●●●●●○○○○ 5/9
H-NEW05 | completed ● | complexity | Glucose entropy (weak beyond HbA1c) | ██░░░░░░░░ d=0.18 | —
H-NEW13 | null ○ | resilience | Sleep-wake transition (too noisy) | ░░░░░░░░░░ d=0.06 | —
H-NEW06 | null ○ | temporal | Nocturnal prediction (clean null) | ░░░░░░░░░░ d=0.02 | —

VISUAL EMPHASIS:
- H-NEW03 row should be subtly highlighted (light green background tint) as the flagship finding
- Null results should be slightly faded
- The effect size bars use a blue→green gradient for significant results and gray for non-significant

ANNOTATION:
A small callout pointing to the contrast between H-NEW03 (d=0.80) and H-MIG01 (d=0.59): "Event-triggered analysis yields 36% stronger effect than broadband summary"
```

---

## FIGURE 6: 9 Robustness Checks (Verifier)

```
Create an infographic showing the 9 mechanical robustness checks used by the Verifier Agent. White background, 16:9.

Layout: A 3×3 grid of circular check nodes, each with a number, title, and criterion.

Each node consists of:
- A teal (#009E73) filled circle with a white number (1-9)
- Below the circle: bold title text
- Below the title: criterion in smaller gray text

Grid layout:
Row 1: [1. Covariate Adjustment: "age + HbA1c + BMI + site"] [2. Negative Control: "Random windows = no effect"] [3. Dose-Response: "Monotonic H→PD→OM→ID"]
Row 2: [4. Bootstrap CI: "95% CI excludes zero"] [5. Sample Size: "N ≥ 100 per group"] [6. Effect Size: "|d| ≥ 0.2"]
Row 3: [7. FDR Significance: "p < 0.05 after correction"] [8. Site Bias: "Site in covariates"] [9. Sensitivity Survival: "≥ 67% checks pass"]

DECISION RULE BAR (below the grid):
A horizontal bar divided into 3 sections:
- Green section: "≥ 7/9 pass + LLM PASS → SUPPORTED"
- Red section: "≤ 3/9 pass or LLM FAIL → REFUTED"
- Gray section: "Otherwise → INCONCLUSIVE"

KEY PRINCIPLE (bottom annotation):
"Rule-based checks take precedence over LLM judgment. If 8/9 pass but LLM says refuted, rules win."
With a small shield icon and text: "Mechanical evidence > LLM hallucination"

EXAMPLE (right side or bottom):
Show H-NEW03's actual check results as a compact row: ✓✓✓✓✓✓✓✓✓ = 9/9 → SUPPORTED
And H-NEW01: ✓✗✓✗✓✓✓✓✗ = 5/9 → INCONCLUSIVE
```

---

## FIGURE 7: SOTA Comparison Matrix

```
Create a comparison matrix showing how this system compares to state-of-the-art AI scientific discovery systems. White background, 16:9.

Layout: A matrix/heatmap table with systems as rows and capabilities as columns.

COLUMNS (capabilities):
1. "Domain Grounding" — Is the system grounded in specific domain knowledge?
2. "Hypothesis Lifecycle" — Does it track hypotheses through a structured lifecycle?
3. "Automated Execution" — Can it run experiments autonomously?
4. "Mechanical Verification" — Does it verify results with rule-based checks (not just LLM)?
5. "Feedback Loops" — Do results inform the next cycle of hypothesis generation?

ROWS (systems):
1. "AI Scientist (2024)"
2. "Virtual Lab (2024)"
3. "SciAgents (2025)"
4. "Agent Laboratory (2025)"
5. "This System" — emphasized with bold text and a colored left border

CELL ENCODING:
Use four levels with distinct visual treatment:
- Empty/None: light gray cell, dash symbol "—"
- Partial: light yellow cell, "○" hollow circle
- Good: light blue cell, "◐" half circle
- Full: light green cell, "●" filled circle

CELL VALUES:
                  Domain  Lifecycle  Execution  Verification  Feedback
AI Scientist:       —        —          ●           —            ○
Virtual Lab:        ◐        ○          ○           —            ○
SciAgents:          ◐        —          —           —            —
Agent Lab:          ○        ○          ◐           —            ○
This System:        ●        ●          ●           ●            ●

The "This System" row should be visually distinct — slightly taller, green-tinted background, bold text. The "Mechanical Verification" column should be highlighted since it's our unique contribution (no other system has it).

ANNOTATION:
Arrow pointing to the Mechanical Verification column: "Unique to this system: 9 rule-based checks that override LLM judgment"
```

---

## FIGURE 8: Results Summary — The Three-Layer Finding

```
Create a scientific summary figure showing the key finding: diabetes has two distinct coupling disease processes that are invisible to broadband analysis. White background, 16:9.

Layout: Three horizontal panels arranged top to bottom, connected by vertical arrows.

PANEL 1 (top) — "What broadband analysis shows":
A simple bar chart or effect icon showing: "Broadband glucose-HR coupling: d = +0.06, n.s."
The bar is gray and small. Label: "Non-significant. Looks like nothing."
Background tint: light gray (representing hidden information).

PANEL 2 (middle) — "What frequency-resolved analysis reveals":
Split into two side-by-side sub-panels:

Left sub-panel (blue tint): "Fast coupling (<2h)"
A downward arrow icon, "d = −0.22 ***"
Label: "DECREASES with severity"
Mechanism tag: "Autonomic buffering fails"

Right sub-panel (vermillion tint): "Slow coupling (>2h)"
An upward arrow icon, "d = +0.38 ***"
Label: "INCREASES with severity"
Mechanism tag: "Metabolic rigidity"

Between the two: a "≠" symbol or a "↔ opposite directions" annotation.

Arrow from Panel 1 to Panel 2 labeled: "Frequency decomposition separates two opposing signals"

PANEL 3 (bottom) — "What event-triggered analysis reveals":
A prominent green-tinted panel showing:
"Post-excursion HR blunting: d = −0.80 *** [CI: −0.95, −0.68]"
A schematic of the event-triggered response: healthy HR curve (tall peak) vs diabetes HR curve (flat/blunted), drawn as simple overlapping shapes.
Label: "Strongest single effect. 9/9 robustness checks. Detectable in pre-diabetes."
Mechanism tag: "Direct autonomic neuropathy marker"

Arrow from Panel 2 to Panel 3 labeled: "Event-triggered analysis isolates the fast coupling loss"

RIGHT SIDE ANNOTATION:
A vertical arrow spanning all 3 panels: "More specific analysis → stronger, more interpretable effects"
With effect sizes labeled: "d = 0.06 → d = 0.38 → d = 0.80"

BOTTOM:
"Conclusion: Diabetes selectively destroys fast autonomic coupling while strengthening slow metabolic locking. Both invisible to broadband summary statistics."
```

---

## Usage Notes

- These prompts are designed for image generation tools (Midjourney, DALL-E, Ideogram, or similar)
- For best results, generate at 2x resolution (3840×2160) and downscale
- If the model struggles with text rendering, generate the layout/shapes first, then add text in Figma/Canva/PowerPoint
- The SVG/PDF vector figures from `results/figures/deck/` and `results/figures/system_deck/` can serve as layout references
- Color hex codes are Okabe-Ito colorblind-safe palette throughout
