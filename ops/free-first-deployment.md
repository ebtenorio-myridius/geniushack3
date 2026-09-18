# Free-First Deployment Plan

## Recommendation

Use Docker Compose on a developer workstation or an organisation-owned Linux host. This has no software licence cost and uses the repository's existing FastAPI, SQLite, and synthetic-data design.

The current application has two cost modes:

| Mode | Infrastructure cost | Model cost | Current status |
|---|---:|---:|---|
| Local Compose + OpenAI | Free locally | API usage is charged | Works now |
| Local Compose + Ollama | Free locally | No per-call API charge | Requires an LLM provider adapter |

The OpenAI key must never be committed, placed in an image, or printed in logs.

## Current deployment: Docker Compose

### Prerequisites

- Docker Desktop or Docker Engine with Compose
- 4 GB RAM minimum; 8 GB recommended
- synthetic PDF inputs only
- an OpenAI API key if live extraction is enabled

### Setup

From the repository root:

```powershell
Copy-Item .env.example .env
# Edit .env and add the key only when using OpenAI

docker compose build
docker compose up
```

Open `http://localhost:8000` and upload `evals/data/sample_change_request.pdf`.

Verify health:

```powershell
Invoke-WebRequest http://localhost:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

The SQLite database is stored in the named Docker volume `risk_workbench_data` at `/code/data/risk_workbench.db`. The volume survives container recreation.

### Stop and remove

```powershell
docker compose down
```

Keep the volume when stopping. To delete synthetic demo state deliberately:

```powershell
docker compose down -v
```

## Zero-API-cost target: Ollama

Ollama is free local software, but the current `AsyncOpenAI` client is OpenAI-specific. Do not claim Ollama support until an adapter is implemented and tested.

Required changes:

1. Add an `LLMProvider` interface with an extraction method.
2. Keep the current OpenAI provider behind that interface.
3. Add an Ollama provider using the local model endpoint and a schema-validation step.
4. Add `LLM_PROVIDER=openai|ollama` configuration.
5. Add provider-specific evaluation results; local models may have different accuracy.
6. Keep the deterministic scoring and workflow provider-independent.

A future local setup would be:

```text
FastAPI container -> Ollama on the host -> local model
                 -> SQLite named volume
```

On Windows, the application container must be configured to reach the host service through `host.docker.internal`. Model downloads consume disk and RAM, and CPU inference may be slow without a supported GPU.

## Free production-like services

For a larger local environment, use open-source containers:

- PostgreSQL instead of SQLite
- MinIO instead of cloud object storage
- Redis plus a worker for asynchronous extraction
- Keycloak instead of a managed identity provider
- Prometheus and Grafana for metrics
- OpenTelemetry for traces

These have no software licence charge but still require machine resources, maintenance, backups, patching, and network security.

## Security baseline

- bind the demo to localhost unless remote access is intentional;
- use a firewall and TLS reverse proxy on a shared host;
- keep `.env` outside version control;
- use synthetic data only;
- do not expose SQLite or uploaded files directly;
- rotate any accidentally exposed API key immediately;
- limit PDF size, page count, and content type;
- restrict demo role headers to local testing only;
- replace demo headers with real identity before production.

## Backup and recovery

For the current demo, stop the application before copying the SQLite volume or use SQLite's backup API. At minimum, verify that a copied database can be opened and that case/audit records are present.

For production, use PostgreSQL backups, object-storage versioning, restore tests, and a documented retention policy.

## Deployment gates

Before each demo or release:

```powershell
python -m pytest -q
python -m compileall -q src tests evals
python evals/run_extraction_eval.py
```

The live evaluation calls the configured model provider and may incur OpenAI charges. Run it only when a current model-quality measurement is needed.

## Known limitations

The free-first Compose deployment is appropriate for a synthetic demo or internal prototype. It is not a public production service until PostgreSQL, real authentication, TLS, backups, upload malware scanning, provider timeouts/retries, and operational alerting are added.
