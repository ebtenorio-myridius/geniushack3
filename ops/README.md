# Ops

Deployment, monitoring, and token-analysis notes — production readiness
(5%) and token efficiency (5%) both draw on this.

Suggested contents:

- `deployment.md` — how/where you deployed (or would deploy) this;
  `Dockerfile` and `docker-compose.yml` in the repo root are the starting
  point
- `monitoring.md` — what you'd watch in production: error rates on the
  extraction call, latency, low-confidence-extraction rate
- `token-usage.md` — where consumption concentrated and what you did about
  it (e.g. the 12k-token input truncation in `llm_service.py`, model choice
  in `ai/agent_config.yaml`)
- `free-first-deployment.md` — zero-licence-cost local deployment, OpenAI cost
  boundary, Ollama target, security baseline, backup, and release gates
