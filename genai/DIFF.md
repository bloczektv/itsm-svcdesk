---
lab3_genai_diff:
  instrumentation: "opentelemetry-instrumentation-genai-openai 1.2b0 (opentelemetry-sdk 1.45.0, openai 3.19.2, exporter opentelemetry-exporter-otlp-json-file 0.66b0)"
  spec_ref: "semantic-conventions@v1.41.1"
  attributes:
    - {name: gen_ai.operation.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.provider.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.temperature, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.max_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.id, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.finish_reasons, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.input_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.output_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.output.type, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.request.choice.count, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.system, emitted: false, in_spec: true, stability: deprecated}
    - {name: gen_ai.usage.prompt_tokens, emitted: false, in_spec: true, stability: deprecated}
---
<!-- ai-generated: 70% - Claude Code ran the instrumented call and compared the spans with the v1.41.1 registry files; I reviewed the claims and the conclusion -->

# What the library emits, against the spec

**The call.** `genai/call.py` makes one chat completion with the `openai` client against Google Gemini's
OpenAI-compatible endpoint (`gemini-3.5-flash-lite`), instrumented by `OpenAIInstrumentor` from
`opentelemetry-instrumentation-genai-openai` 1.2b0, and writes the span as OTLP JSON to `genai/spans.json`.
Message content capture was left off, so no prompt or answer is in the spans, and the API key came from an
environment variable and is in no file. I compared the span's attributes with the GenAI attribute registry of
`open-telemetry/semantic-conventions` at v1.41.1 (`model/gen-ai/registry.yaml` and
`model/gen-ai/deprecated/registry-deprecated.yaml`).

**What agrees.** The span is named `chat gemini-3.5-flash-lite` (operation, then model) and has kind CLIENT, as
the spec's inference span asks. All ten `gen_ai.*` keys the library emitted are defined in v1.41.1, all at
`development` stability: the operation, the provider, the request parameters I set (model, temperature,
max_tokens), the response's model, id and finish reasons, and the input and output token counts. It uses the
current names, not the deprecated ones: `gen_ai.provider.name` instead of `gen_ai.system`, and
`gen_ai.usage.input_tokens` / `output_tokens` instead of `prompt_tokens` / `completion_tokens`. It also sets the
general `server.address`, which the spec recommends on the same span.

**What does not quite agree.** `gen_ai.provider.name` is `"openai"`, but the model behind the endpoint is Google's:
v1.41.1 has a member for exactly this case, `gcp.gemini`, whose note reads "Used when accessing the
'generativelanguage.googleapis.com' endpoint", the very endpoint in this span's `server.address`. The library infers the provider from the client class it patched, not from
`server.address` (`generativelanguage.googleapis.com`), so every OpenAI-compatible backend (Gemini, Ollama, vLLM)
is reported as OpenAI. Two attributes the spec defines are absent: `gen_ai.output.type` (I did not ask for a
structured output, so it is reasonable that it is missing) and `gen_ai.request.choice.count` (I did not set `n`).
The instrumentation is a beta (1.2b0) and every attribute it emits is still `development` in the spec, so names and
meanings can change under it.

**What it means for a dashboard.** Panels that group cost or token usage by `gen_ai.provider.name` would put Gemini
traffic under "openai" and could not be split by vendor; grouping by `gen_ai.request.model` or `server.address`
does the job. Token counts are trustworthy: input and output tokens match what the API reported (16 and 45).
A dashboard built on `development` attributes should pin the instrumentation version, because the next
convention release may rename them, as already happened to `gen_ai.system` and `prompt_tokens`.
