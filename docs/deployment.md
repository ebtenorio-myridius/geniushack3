# Deployment

This guide covers local operation and free or free-to-start hosting for the current FastAPI application. The application uses SQLite, stores case data locally, calls OpenAI for extraction, and uses demo role headers rather than production authentication. It is suitable for a synthetic-data demo, not for public production use.

## Choose a target

| Target | Current code changes | Data durability | Best use |
| --- | --- | --- | --- |
| Local Python or Docker Compose | None | Persistent on the local machine | Development and judging |
| Render Free Web Service | None for a disposable demo | None; local files are ephemeral | Fast public preview |
| Google Cloud Run | None for a disposable demo; database change for persistence | None for local SQLite | Serverless public preview |
| Oracle Cloud Always Free VM | None | Persistent VM disk | Free persistent demo |
| Cloud Run + Supabase PostgreSQL | Replace SQLite storage layer and add migrations | PostgreSQL | More durable hosted prototype |

The default recommendation is **Render for a short-lived public demo** and **Oracle Cloud Always Free for a persistent deployment without changing the current SQLite implementation**. For either option, use synthetic PDFs only.

OpenAI model calls are not free. Hosting may be free while extraction still incurs OpenAI API usage charges. A fully local Ollama provider requires an LLM provider adapter that this repository does not currently implement. See [the free-first deployment notes](../ops/free-first-deployment.md).

## Required security steps

1. Revoke and rotate any OpenAI key exposed in chat, logs, screenshots, or a shared working directory.
2. Keep `.env` local. It is ignored by Git, but never commit it or copy it into a Docker image.
3. Configure `OPENAI_API_KEY` through the hosting provider's secret manager.
4. Use synthetic data only. Do not upload customer, employee, regulated, or confidential documents.
5. Do not treat `X-Demo-User` and `X-Demo-Role` as authentication. They are demo controls.
6. Set spending limits and usage alerts for the OpenAI account.

Required environment variables:

```text
OPENAI_API_KEY=<secret>
OPENAI_MODEL=gpt-4o-mini
DATABASE_PATH=risk_workbench.db
PROMPT_VERSION=extract_change_request_v1
```

## Local deployment

### Python virtual environment

On Windows, PowerShell may block the activation script. Activation is optional; calling the virtual-environment interpreter directly avoids the execution-policy problem.

```powershell
Set-Location "C:\GENIUS HACK\GeniusHack3"
Copy-Item .env.example .env
# Edit .env and add a valid key only when using live extraction.

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn src.app.main:app --reload --port 8000
```

Alternatively, allow activation for the current PowerShell process only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
uvicorn src.app.main:app --reload --port 8000
```

Open `http://localhost:8000`. Check health from another terminal:

```powershell
Invoke-WebRequest http://localhost:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

### Docker Compose

Install Docker Desktop, then run from the repository root:

```powershell
Copy-Item .env.example .env
# Edit .env and add a valid key only when using live extraction.

docker compose build
docker compose up
```

The Compose file stores SQLite in the named `risk_workbench_data` volume. Stop the service without deleting data:

```powershell
docker compose down
```

Delete the demo database deliberately with:

```powershell
docker compose down -v
```

## Render Free Web Service

Render is the quickest public preview because it can build the repository's Dockerfile and provides HTTPS. Its free web service sleeps after inactivity and has an ephemeral filesystem. Any local SQLite database and uploaded files are lost after restart, redeploy, or sleep.

### Dashboard setup

1. Push the repository to a private GitHub repository without `.env`.
2. Create a new **Web Service** in the [Render dashboard](https://dashboard.render.com/).
3. Select the repository and choose **Docker** as the runtime.
4. Use the repository root as the Docker build context.
5. Set the service plan to **Free**.
6. Add these environment variables in Render:
   - `OPENAI_API_KEY` as a secret
   - `OPENAI_MODEL` set to `gpt-4o-mini`
   - `DATABASE_PATH` set to `risk_workbench.db`
   - `PROMPT_VERSION` set to `extract_change_request_v1`
7. Deploy and wait for the build to finish.
8. Open the generated HTTPS URL and verify `/healthz`.
9. Upload only `evals/data/sample_change_request.pdf` or another synthetic PDF.

Do not use Render's free PostgreSQL for durable records: the current Render free database expires after 30 days. Use Supabase PostgreSQL or another durable database after adapting the storage service.

Reference: [Render free services](https://render.com/docs/free).

## Google Cloud Run

Cloud Run is appropriate when a Docker image, scale-to-zero behavior, and a managed HTTPS endpoint are preferred. Its free tier is usage-based and requires a Google Cloud billing account. Configure a budget alert before deploying.

### Deployment outline

1. Create a Google Cloud project and enable billing.
2. Enable Cloud Run, Cloud Build, and Artifact Registry.
3. Create an Artifact Registry Docker repository.
4. Build and deploy the existing Dockerfile, or deploy from source using the Google Cloud CLI.
5. Set the service to allow unauthenticated access only for a synthetic demo.
6. Add `OPENAI_API_KEY` as a Secret Manager secret and expose it to the service.
7. Add the remaining settings as non-secret environment variables.
8. Set minimum instances to zero and configure a low maximum instance count.
9. Verify `/healthz` and test one synthetic PDF upload.

The container's local filesystem is not durable across instance replacement. Cloud Run therefore requires a database migration before it is used for cases that must survive restarts. Do not rely on `risk_workbench.db` in Cloud Run.

Reference: [Cloud Run pricing and free tier](https://cloud.google.com/run/pricing).

## Oracle Cloud Always Free VM

An Oracle Always Free VM is the closest hosted equivalent to the current local Compose deployment. It can run Docker Compose with a persistent VM disk and does not require a database migration. Availability of free VM capacity is not guaranteed, and account creation commonly requires phone verification and a credit card.

### VM setup outline

1. Create an [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/) account and select the home region carefully.
2. Provision an Always Free Ampere or eligible VM running Ubuntu.
3. Allow inbound TCP `80` and `443` in the cloud security list and the VM firewall. Do not expose SQLite or port `8000` publicly.
4. Install Docker Engine and Docker Compose on the VM.
5. Clone the repository onto the VM.
6. Create `.env` on the VM and add the OpenAI key as a secret.
7. Run `docker compose up -d`.
8. Put Nginx or Caddy in front of the app for TLS and route HTTPS traffic to the web container.
9. Verify `/healthz`, then test with synthetic data.
10. Back up `risk_workbench.db` and test restoring a backup before relying on the deployment.

This option still needs real authentication, upload scanning, monitoring, backups, and patching before it can be considered production-ready.

Reference: [Oracle Cloud Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm).

## Supabase PostgreSQL migration

[Supabase Free](https://supabase.com/docs/guides/platform/billing-on-supabase) is useful as a small hosted PostgreSQL database. It provides two free projects and a 500 MB database quota per project, but inactive projects may pause. The current `CaseStore` uses SQLite-specific connection and schema code, so Supabase cannot be added by changing only `DATABASE_PATH`.

Required application work:

1. Add a PostgreSQL driver and connection configuration.
2. Replace SQLite connection code in `src/app/services/case_store.py` with a PostgreSQL implementation or repository interface.
3. Add migrations for `cases`, `extraction_versions`, `workflow_events`, and `telemetry`.
4. Move uploaded source documents to object storage instead of local disk.
5. Add connection pooling and startup failure handling.
6. Test concurrent requests and migration rollback.
7. Set the database URL through the hosting provider's secret settings.

Until this work is complete, use an Oracle VM for durable SQLite or accept that a Render/Cloud Run deployment is disposable.

## Deployment validation

Run these checks from the repository root before each deployment:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests tools evals
.\.venv\Scripts\python.exe -m pytest -q
```

For a live OpenAI extraction regression, run the evaluation separately because it can incur API charges:

```powershell
.\.venv\Scripts\python.exe evals/run_extraction_eval.py
```

After deployment:

- `/healthz` returns `{"status":"ok"}`;
- the intake page loads over HTTPS;
- a synthetic PDF is accepted and extracted;
- the analyst review workflow records a case and rationale;
- logs do not contain API keys or uploaded document contents;
- the configured database survives the type of restart used by the host.

## Not recommended as the primary target

- **Railway:** its current free plan is limited usage credit rather than a dependable free always-on service; volumes and additional usage can become billable.
- **Hugging Face Docker Spaces:** normal Docker Spaces require a paid plan; free static Spaces cannot run this backend.
- **Cloudflare Workers:** the free platform is attractive, but this Python, Jinja2, SQLite, and file-upload application would require a substantial rewrite.

## Production gap

Before public production, add PostgreSQL and migrations, object storage, malware scanning, real authentication and authorization, TLS termination, provider timeouts and retries, rate limits, backups, audit retention, monitoring, alerting, and a rollback plan. The current demo role headers and local SQLite design are not production controls.
