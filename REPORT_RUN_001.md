# HLE Benchmark Report — Run 001

**Date:** 2026-05-30
**Model:** xiaomi/mimo-v2.5 (core) + tencent/hy3-preview (inspection)
**Architecture:** CAPT v2.1 — 11 test vessels, 455 inspection cohort
**Dataset:** HLE (Humanity's Last Exam) — 50-question stratified sample

## Executive Summary

First clean baseline run. All 11 test vessels fired concurrently via OpenRouter using asyncio.gather + httpx pattern (FORGE vessel swarm). Wall time: 83s for all 11 vessels. CAPT inspection layer active throughout.

**Key finding:** mimo-v2.5 is a reasoning model that produces 30K+ character reasoning chains but does not reliably produce structured JSON output. Answer extraction from natural language reasoning is the primary bottleneck.

## Results

| Metric | Value |
|--------|-------|
| Questions | 50 |
| Vessels Fired | 11/11 (concurrent) |
| Wall Time | 83.1s |
| Answers Parsed | 7/50 (14%) |
| Correct | 1 |
| Accuracy (parsed) | 14% |
| Accuracy (all) | 2% |

## By Category

| Category | Parsed | Correct | Accuracy |
|----------|--------|---------|----------|
| Math | 2 | 1 | 50% |
| Biology/Medicine | 1 | 0 | 0% |
| Computer Science/AI | 1 | 0 | 0% |
| Humanities/Social Science | 1 | 0 | 0% |
| Other | 1 | 0 | 0% |
| Chemistry | 0 | - | - |
| Engineering | 0 | - | - |
| Physics | 0 | - | - |

## CAPT System State

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Modules Active | 48 | 48 | 0 |
| ECHO Traces | 20,173 | 20,243 | +70 |
| ChromaDB | Connected | Connected | - |
| Health | Healthy | Healthy | - |

## Architecture

### Vessel Swarm (test-taking)
- **Pattern:** asyncio.gather + httpx.AsyncClient
- **Concurrency:** 11 vessels simultaneously
- **Endpoint:** OpenRouter API (xiaomi/mimo-v2.5)
- **Max tokens:** 8192 per vessel
- **All 11 fired and completed in 83s**

### Inspection Cohort (monitoring)
- **Pattern:** CAPT MCP tools (capt_status, capt_ingest, capt_module_list, capt_observability)
- **455 vessels:** 2 input + 4 internal + 2 output per module (48 active modules × 8 = 384 required)
- **Pre/post test capture:** status, metrics, capabilities
- **Memory ingestion:** 3 trace entries to ECHO

### Scoring
- Exact match with normalization (lowercase, strip $, \, whitespace)
- Parser extracts answers from JSON or natural language reasoning

## Issues & Fixes Needed

1. **Answer extraction:** mimo-v2.5 produces reasoning chains, not structured JSON. Parser extracts 14% of answers. Need either:
   - Different model with structured output support
   - Better NLP extraction from reasoning text
   - Fewer questions per vessel to reduce reasoning length

2. **Scoring normalization:** Trailing period caused false negative on correct Math answer. Fixed in normalization.

3. **Image questions:** 9 of 50 questions have images. Vessels cannot process images through text-only API.

## Files

```
results/
├── run_20260530_225648/
│   ├── manifest_start.json
│   ├── manifest_complete.json
│   ├── scoring_results.json
│   ├── vessel_01_output.json ... vessel_11_output.json
│   └── vessel_01_batch.json ... vessel_11_batch.json
├── inspection/
│   ├── hle_biocapt_internal_trace.jsonl
│   └── chronicle.md
├── hle_blind_sample.json
├── hle_answer_key.json
├── hle_test.parquet
├── hle_vessel_swarm.py
└── hle_inspection_harness.py
```

## Future Runs

This is the **clean baseline** — first attempt with no prior exposure to HLE questions.
Future runs will have memory of this attempt, making them non-independent.

### Scaling to 2,500 questions
- Increase vessel count: 2,500 questions / ~5 per vessel = ~500 vessels
- All fire concurrently via same asyncio.gather pattern
- Expected wall time: ~83s (bounded by slowest vessel, not sum)
- Cost: ~500 × 8K tokens × $0.25/M = ~$10 per full run

## Methodology

1. Dataset: HLE 50-question stratified sample (proportional across 8 categories)
2. Blind test: Questions presented without answer key
3. Vessel architecture: 11 parallel test vessels via asyncio.gather + httpx
4. Inspection: CAPT MCP tools (status, ingest, module_list, observability)
5. Scoring: Exact match with normalized comparison
6. Model: xiaomi/mimo-v2.5 via OpenRouter
