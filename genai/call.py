# ai-generated: 80% - Claude Code wrote the script from HANDOUT.md "Stretch 1"; I ran it with my own Gemini key
"""One instrumented LLM call for Lab 3 Stretch 1 (MONITORING-SPEC.md M-28).

Calls Gemini through its OpenAI-compatible endpoint with the OpenAI client, instrumented by
opentelemetry-instrumentation-genai-openai, and writes the spans as OTLP JSON to genai/spans.json.
Message content is not captured (OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT unset), and the API key is
read from GEMINI_API_KEY and never written anywhere.

    pip install openai==3.19.2 opentelemetry-sdk==1.45.0 opentelemetry-instrumentation-genai-openai==1.2b0 \
        opentelemetry-exporter-otlp-json-file==0.66b0
    GEMINI_API_KEY=... python genai/call.py genai/spans.json
"""

import os
import sys

from openai import OpenAI
from opentelemetry import trace
from opentelemetry.exporter.otlp.json.file import FileSpanExporter
from opentelemetry.instrumentation.genai.openai import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL = os.environ.get("GENAI_MODEL", "gemini-3.5-flash-lite")


def main(out_path: str) -> None:
    provider = TracerProvider(resource=Resource.create({"service.name": "svcdesk-genai-probe"}))
    provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(out_path)))
    trace.set_tracer_provider(provider)
    OpenAIInstrumentor().instrument(tracer_provider=provider)

    client = OpenAI(base_url=BASE_URL, api_key=os.environ["GEMINI_API_KEY"])
    answer = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "In one sentence: what is a known error in ITIL problem management?"}],
        max_tokens=200,
        temperature=0.2,
    )
    print(answer.choices[0].message.content)
    provider.shutdown()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "genai/spans.json")
