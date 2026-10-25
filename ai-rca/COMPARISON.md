<!-- ai-generated: 60% - Claude Code drafted the comparison from both ledgers; I checked every claim against the queries in ai-rca-eval.json and ai-rca-eval-2.json -->
# Two investigators of lab4-rec-3, compared

Both investigated the same recording through the same read-only MCP server (`prom_mcp.py`, mcp 2.2.0), served on
http://localhost:19090:

- **Investigator 1** (`ai-rca-eval.json`, `ai-rca/transcript.md`): the course agent loop with `gemini-3.5-flash-lite`,
  run by me on 2026-10-25, twice (the first run stated two hypotheses, the handout's "sharper question" rerun added a
  request to look at errors, latency and resources). `gemini-3.8-flash` hung on its first call and left no answer.
- **Investigator 2** (`ai-rca-eval-2.json`, `ai-rca/second/transcript.md`): the same loop with `qwen3:4b-instruct`, the
  lecturer's recorded run of the same incident.

The seeded fault, as my own investigation reads it, had three parts: product-catalog failing GetProduct
(`productCatalogFailure`), ad stalling in forced garbage collections (`adManualGc`) and recommendation switching to a
leaking cache (`recommendationCacheFailure`).

## Where they agreed

Both found the error path, and both found it the same way: by listing `STATUS_CODE_ERROR` series. Gemini's H1 and
H2 and qwen's H2 say the same thing - checkout's failed orders come from failed `ProductCatalogService/GetProduct`
calls, and product-catalog is where those errors originate. All three are `correct`: product-catalog answered 0.149
failed GetProduct/s at 07:11 against nothing at the baseline, and checkout's only failing client call is that one
(0.0082/s). On this part neither agent needed more than the alerts already pointed at, but both went one hop further
than the paging alert, which named only checkout.

## Where they parted

- **Timing.** qwen's H1 put the PlaceOrder errors at "a consistent count of 2 erroneous calls from 07:00Z to 07:20Z":
  it read the raw counter's value, not its rate, and the counter appears only at 07:08, after the 07:05:45 onset. The
  query `A unless on() B` (errors now, unless they were already there ten minutes earlier) is true, so the verdict is
  `partially_correct`: the right component at the wrong time. Gemini got the start right ("starting around 07:05Z /
  07:09Z", H3, `correct`) but then claimed that before 07:05Z "the error rate across all services was essentially zero"
  (H4, `hallucinated`): the healthy shop fails 0.158 calls/s, all of them the load generator's own client calls. It
  believed a query with a 1-minute window that returns nothing on metrics pushed once a minute.
- **Guessing.** qwen guessed twice from general knowledge rather than data: payment ("payment failures commonly cause
  user checkout errors", H3) and "high load or a resource bottleneck" (H4). Both are `hallucinated`: payment served
  0.125 Charge/s with no failures, shop traffic was flat (15.8 against 16.1 calls/s ten minutes earlier) and no shop
  container used more than 0.13 of a CPU. Gemini made no such guess; every claim it made named a series it had queried.
- **Breadth.** Gemini looked at latency once (a p95 range query with a 1-minute window, which came back empty) and at
  CPU metric names, then stopped. qwen never looked beyond errors.

## Which one the data proved right

On what they said, Gemini: three `correct` and one `hallucinated`, against qwen's one `correct`, one
`partially_correct` and two `hallucinated`. But both missed two of the three faults. Neither noticed that ad's median
GetAds went from 4 ms to about 600 ms while ad's JVM spent 0.116 s of every second in garbage collection, which is
why the storefront's p99 went from 47 ms to about 900 ms; and neither noticed that recommendation stopped calling
ListProducts on every request (the ratio fell from 1.0 to 0.49), the signature of the cache flag. Both are latency and
behaviour symptoms without a single error, and both agents searched only where the errors were. The alerts they could
read (`alerts_at`) pointed only at errors too, so neither went beyond what the alerts already told it on those two
faults. A third investigation should be asked about latency per service with 5-minute windows, explicitly.
