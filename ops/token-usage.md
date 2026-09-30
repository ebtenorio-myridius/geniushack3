# Token Usage

The extraction step uses `gpt-4o-mini` and currently bounds document input to 12,000 characters. This is a defensive budget, not a measured token guarantee.

Telemetry now records provider usage metadata, model name, prompt version,
input/output tokens when returned by the provider, latency, and success/error
type. The live evaluator records latency and accuracy per case. A live
extraction may issue up to three requests after transient connection, timeout,
or rate-limit failures; telemetry records the overall operation, not each
attempt, so use provider-side usage records for exact cost accounting.

The remaining optimization experiment is to compare shorter prompt/context
variants against field-level accuracy and measured token cost before reducing
context. Do not claim cost savings without recording provider usage and the
comparison result.
