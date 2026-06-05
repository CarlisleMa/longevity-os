# AI-READI Progress Update - Speaker Notes

## 1. AI-READI
Start with the high-level picture: this is a layered system for turning synchronized multimodal physiology into a model-backed scientific discovery and N-of-1 trial engine. The raster image is intentionally text-free; use it as emotional context, not evidence.

## 2. One system, four layers
This is the architecture in one slide: Layer 0 data, Layer 1 foundation model perception, Layer 2 agentic science, Layer 3 Longevity OS/N-of-1 translation.

## 3. Dataset: breadth plus synchrony
Keep the dataset slide compact. The point is not just nine modalities; the point is that the 10-day sensor window is anchored to clinical and imaging measurements from the same visit.

## 4. The 10-day window changes the science
Say explicitly: this is not a longitudinal disease-outcome cohort. It is a short, synchronized within-person window that enables causal hypotheses and N-of-1 trial design.

## 5. Foundation model layer
Foundation models provide perception: retinal/cardiac embeddings, future wearable/CGM/environment encoders, and cross-modal reconstruction. Agents reason over these computed representations.

## 6. Agent system layer
The generated image is a visual metaphor. The scientific implementation is concrete: agents are scoped code-generating analysts over scripts, a shared workspace, memory, and critic checks.

## 7. What each agent group makes computable
This replaces the long per-agent text slides. In narration, expand each group: ClinicalAgent handles OMOP and disease gradients; GlucoseAgent handles CGM metrics; Wearable and Environment agents make the 10-day inference layer; Cardiac and Retinal agents provide high-value organ readouts; reasoning agents test and critique.

## 8. Latest results, regenerated from current artifacts
This slide addresses provenance. It uses the latest result files and records exact paths and timestamps in sources.json.

## 9. Aging-clock progress
This is an informative chart from clock_performance.csv. The key message is that the infrastructure now supports many aging dimensions; current performance varies and should be treated as preliminary.

## 10. Cross-system concordance
This replaces a dense heatmap with the top concordance pairs. It shows strong blood/inflammatory coupling and a circadian-autonomic-physical axis, with weaker cross-system coupling elsewhere.

## 11. Diabetes-stage gradient
This chart comes from diabetes_gradient.csv. It makes the current diabetes-stage signals explicit, especially the CGM-metabolic and clinical metabolic dimensions.

## 12. Digital biomarker signal
This chart comes from the latest biomarker_panel.csv. It shows which features drive the strongest current screen. Interpret as a model-development signal, not a clinical biomarker claim.

## 13. 10-day causal signal: environment and HR
This chart uses the latest, enlarged causal_pm25_hr.csv. It summarizes cohort-scale lag-model output and is still nominal until the Critic applies multiple-comparison control, confounder checks, and site sensitivity.

## 14. New problems this architecture can solve
These are the scientific problems that require the whole architecture. A single modality or a generic LLM cannot solve them cleanly.

## 15. N-of-1 and test-time learning
This is the future integration vision. After the system identifies a person-level phenotype, it proposes a low-risk trial, observes the response, and updates both the person-specific latent state and the agent workflow memory.

## 16. Roadmap
Close with the plan by layers: QC and result manifests for Layer 0; encoders and cross-modal JEPA for Layer 1; agent benchmarking, critic gates, and memory for Layer 2; N-of-1 suggestion and Bayesian monitoring for Layer 3.
