# Paper-Style Agentic Results Figures

These figures replace the earlier bar-heavy visuals with aging-clock paper conventions:
predicted-vs-age calibration, age-gap profiles, concordance matrices, disease-gradient
trajectories, association maps, and control curves.

## Figure Set

| Figure | File stem | Best slide use | Main message |
| --- | --- | --- | --- |
| A | `figA_clock_calibration_scatter` | Single-modality clock results | Retinal and multimodal clocks estimate chronological age well; cardiac and narrow clinical clocks carry weaker but distinct signal. |
| B | `figB_clock_benchmark_landscape` | Clock benchmark overview | Multimodal static and retinal clocks separate from weaker single-system baselines in the MAE/R2 plane. |
| C | `figC_agegap_profiles_and_concordance` | Biological heterogeneity | Participants form age-gap profiles across systems; clocks are partially concordant rather than redundant. |
| D1 | `figD_diabetes_agegap_trajectory` | Why residual age gap matters | Residual age gaps recover glycemic-severity gradients even though clocks were trained against chronological age. |
| D2 | `figD_coupling_association_and_prediction_map` | Agentic dynamic physiology result | Glucose-HR and glucose-activity coupling features are severity-associated and predictive. |
| E | `figE_foundation_model_controls` | Handoff to foundation model | Agent-designed controls separate static shortcuts from temporal alignment in JEPA experiments. |

## Visual Inspirations

- Organ-aging clock papers commonly use predicted age versus chronological age scatter panels with MAE and correlation annotations.
- Organ/system aging papers use age-gap heatmaps and correlation matrices to argue that biological aging is heterogeneous across systems.
- Disease and mortality analyses usually move from age-gap residuals to forest plots, effect-size maps, or risk trajectories rather than simple performance bars.
- Foundation-model controls are clearer as dot/error plots and temporal line plots because the central question is robustness and alignment, not category ranking.

## Slide Sequence Suggestion

1. Show `figA` as the baseline clock validation.
2. Use `figB` as the compact benchmark summary.
3. Use `figC` to motivate why a single aging score is insufficient.
4. Use `figD_diabetes_agegap_trajectory` to show disease-relevant residual structure.
5. Use `figD_coupling_association_and_prediction_map` as the agentic discovery result.
6. Use `figE` to transition from agentic workflow to representation/foundation-model results.
