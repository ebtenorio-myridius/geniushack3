# Token Usage

The extraction step uses `gpt-4o-mini` and currently bounds document input to 12,000 characters. This is a defensive budget, not a measured token guarantee.

Telemetry now records provider usage metadata, model name, prompt version,
input/output tokens when returned by the provider, latency, and success/error
type. The live evaluator records latency and accuracy per case.

The remaining optimization experiment is to compare shorter prompt/context
variants against field-level accuracy and measured token cost before reducing
context. Do not claim cost savings without recording provider usage and the
comparison result.
