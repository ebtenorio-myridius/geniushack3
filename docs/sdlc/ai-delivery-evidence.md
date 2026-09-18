# AI Delivery Evidence

This file maps the six delivery stages to the artifact, human gate, and measurable output in this repository. The reusable instructions are in `ai/prompts/sdlc_delivery.md`.

| Stage | AI contribution | Human gate | Repository evidence |
|---|---|---|---|
| 01 Requirements | Expands the intentionally incomplete brief into personas, states, acceptance criteria, assumptions, and open questions. | FCRM owner approves scope and decisions. | `docs/requirements/spec.md`, `docs/requirements/open-questions.md` |
| 02 Design | Compares architectures, data models, workflow boundaries, and failure modes. | Engineering/risk owners approve the decision log. | `docs/architecture/overview.md`, `data-model.md`, `decisions.md` |
| 03 Development | Generates and critiques implementation slices; runtime LLM extracts structure while deterministic code scores and governs transitions. | Code review and automated tests. | `src/`, `ai/prompts/extract_change_request.md`, `tests/` |
| 04 Testing | Generates synthetic cases and proposes expected labels; evaluation runner measures field accuracy and risk agreement. | Analyst approves labels and reviews failures. | `evals/data/`, `evals/run_extraction_eval.py`, `evals/results/` |
| 05 Deployment | Reviews Docker configuration, secrets, persistence, health, and free-first/production migration paths. | Release gate checks tests, compilation, health, and data restrictions. | `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `ops/` |
| 06 Operations | Defines telemetry, token/cost tracking, error handling, and continuous-improvement triggers. | Operations owner reviews thresholds and remediation. | `src/app/services/llm_service.py`, `ops/monitoring.md`, `ops/token-usage.md` |

## Failure-to-improvement loop

1. The live evaluator identified missing products, weak risk-factor preservation, and transient provider failures.
2. The extraction prompt gained explicit product, risk-factor, contradiction, and pending-vendor rules.
3. The evaluator gained normalization, retry handling, latency, and risk-agreement metrics.
4. The deterministic scorer gained narrow high-impact signals and regression tests.
5. The next evaluation run is compared with the recorded baseline rather than judged by visual inspection.

## Evidence discipline

The team must preserve prompt versions, evaluation outputs, human corrections, and rejected alternatives. A claim in the presentation is only made when it links to a repository artifact or a reproducible command.
