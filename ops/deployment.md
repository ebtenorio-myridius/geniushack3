# Deployment

The recommended deployment is the free-first local Docker Compose setup in
[`free-first-deployment.md`](free-first-deployment.md). It uses the existing
FastAPI image, a named SQLite volume, and synthetic data only.

This has no infrastructure or software licence charge when run on a local or
organisation-owned machine. Live OpenAI extraction is still metered API usage;
the fully free Ollama option requires an LLM provider adapter that is not yet
implemented.

Deployment gates:

- compile and unit tests pass;
- synthetic evaluation regression passes;
- `/healthz` returns `{"status":"ok"}`;
- secrets are injected through environment configuration;
- only synthetic data is loaded.

Production additions are PostgreSQL and migrations, object storage for source
documents, real authentication, TLS termination, malware scanning, provider
timeouts/retries, backups, alerting, and a rollback plan. The free-first
deployment document describes the open-source alternatives and their limits.
