# HLE 500×5 — Iteration Analysis

**Date:** 2026-05-30
**Model:** qwen/qwen3-235b-a22b-2507 (JSON mode, reasoning off, temp=0.0)
**Dataset:** First 500 text questions from HLE
**Loops:** 5 (each question answered 5 times independently)

## Results

| Loop | Correct | Scored | Accuracy | Time |
|------|---------|--------|----------|------|
| 1 | 27 | 498 | 5.4% | 25.9s |
| 2 | 25 | 500 | 5.0% | 24.0s |
| 3 | 21 | 492 | 4.3% | 120.0s |
| 4 | 25 | 500 | 5.0% | 25.3s |
| 5 | 24 | 499 | 4.8% | 29.6s |
| **Total** | **122** | **2,489** | **4.9%** | |

## Iteration Trend

```
Loop 1:  5.4%  ████████████
Loop 2:  5.0%  ██████████
Loop 3:  4.3%  ████████
Loop 4:  5.0%  ██████████
Loop 5:  4.8%  █████████
```

**Trend: 5.4% → 4.8% (Δ -0.6%) — DEGRADING**

## Why No Improvement?

1. **Temperature = 0.0** — deterministic output, same input = same answer
2. **No memory** — each loop is independent, no feedback from previous attempts
3. **No ensemble** — single model, no voting across loops

## What Would Improve Scores?

1. **Temperature > 0** — stochastic sampling, different answers each loop
2. **Ensemble voting** — majority vote across 5 loops per question
3. **Feedback loop** — feed wrong answers back with corrections
4. **CAPT augmentation** — route through knowledge engine for fact-checking

## Ensemble Voting Test

If we take majority vote across 5 loops:

| Questions | All 5 correct | 4/5 correct | 3/5 correct | 2/5 correct | 1/5 correct | 0/5 correct |
|-----------|---------------|-------------|-------------|-------------|-------------|-------------|
| (to compute) | | | | | | |

## Files

- Results: `results/500x5/`
- Per-loop: `loop_1_results.json` ... `loop_5_results.json`
- Master: `master_results.json`
