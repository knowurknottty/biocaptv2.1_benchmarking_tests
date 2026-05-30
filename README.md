# bioCAPT v2.1 Benchmarking Tests

Public record of all cognitive architecture evaluations.

## Benchmarks

### HLE (Humanity's Last Exam)
- 2,500 expert-level questions across dozens of subjects
- Published on Nature (Jan 2026)
- Dataset: `cais/hle` on HuggingFace

## Runs

| Run | Date | Model | Questions | Vessels | Accuracy | Report |
|-----|------|-------|-----------|---------|----------|--------|
| 001 | 2026-05-30 | mimo-v2.5 | 50 | 11 | 14% (parsed) | [REPORT](REPORT_RUN_001.md) |

## Architecture

- **Vessel Swarm:** asyncio.gather + httpx concurrent OpenRouter calls
- **Inspection:** CAPT MCP tools (status, ingest, module_list, observability)
- **Scoring:** Exact match with normalization

## Notes

- Run 001 is the clean baseline — no prior exposure to HLE questions
- mimo-v2.5 is a reasoning model; answer extraction from reasoning chains is the bottleneck
- Future runs will have memory of this attempt
