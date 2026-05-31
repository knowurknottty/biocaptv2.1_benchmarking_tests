# HLE Full Run 001 — 2,500 Questions

**Date:** 2026-05-30
**Model:** qwen/qwen3-235b-a22b-2507 (JSON mode, reasoning off)
**Architecture:** CAPT v2.1 — 432 vessels concurrent, 455 inspection cohort
**Dataset:** HLE (Humanity's Last Exam) — full 2,500 questions

## Results

| Metric | Value |
|--------|-------|
| Total Questions | 2,500 |
| Text Questions | 2,158 |
| Image Questions | 342 (skipped) |
| Vessels Fired | 432/432 (100%) |
| Wall Time | 99.5s |
| Predictions Parsed | 2,158 (86.1%) |
| Correct | 98 |
| Incorrect | 2,055 |
| Accuracy (on scored) | 4.6% |
| Accuracy (on total) | 3.9% |

## By Category

| Category | Correct | Total | Accuracy | Unparsed |
|----------|---------|-------|----------|----------|
| Math | 46 | 1,021 | 5% | 48 |
| Biology/Medicine | 17 | 280 | 8% | 59 |
| Humanities/Social Science | 9 | 219 | 5% | 26 |
| Computer Science/AI | 6 | 241 | 3% | 17 |
| Other | 6 | 233 | 3% | 58 |
| Physics | 5 | 230 | 2% | 28 |
| Chemistry | 5 | 165 | 5% | 64 |
| Engineering | 4 | 111 | 6% | 47 |

## Comparison with Leaderboard

| Model | Accuracy |
|-------|----------|
| OpenAI o3 | 15.2% |
| Claude 3.5 Sonnet | 9.3% |
| GPT-4o | 8.3% |
| **bioCAPT (qwen3-235b)** | **4.6%** |
| Gemini 1.5 Pro | 7.2% |

## Key Findings

1. **Vessel swarm pattern validated:** 432 vessels fired concurrently in 99.5s via asyncio.gather + httpx
2. **JSON mode works:** qwen3-235b produces structured output with reasoning off
3. **Parse rate 86.1%:** 342 image questions skipped, 15 unparsed text responses
4. **Math strongest by count:** 46/1021 correct (5%)
5. **Biology strongest by rate:** 17/280 correct (8%)
6. **Physics weakest:** 5/230 correct (2%)

## Next Steps

- [ ] Add image processing (vision model for 342 image questions)
- [ ] Try ensemble voting (multiple models per question)
- [ ] Increase parse rate (better JSON extraction)
- [ ] CAPT module-augmented answers (route through knowledge engine)

## Files

- Results: `results/full_run_001/`
- Swarm: `hle_full_swarm.py`
- Score: `results/full_run_001/scoring_results.json`
