# Token Usage

The extraction step uses `gpt-4o-mini` and currently bounds document input to 12,000 characters. This is a defensive budget, not a measured token guarantee.

The next instrumentation increment should record provider usage metadata per case, model name, prompt version, input/output tokens, latency, and estimated cost. Compare chunking and summarization strategies against field-level extraction accuracy before reducing context.
