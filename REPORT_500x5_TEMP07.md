# HLE 500×5 — temp=0.7 + QIPC Ensemble

**Date:** 2026-05-30
**Model:** qwen/qwen3-235b-a22b-2507 (JSON mode, temp=0.7)
**Method:** 5 loops × 100 vessels, QIPC majority vote ensemble

## Results

| Loop | Correct | Scored | Accuracy |
|------|---------|--------|----------|
| 1 | 25 | 499 | 5.0% |
| 2 | 24 | 498 | 4.8% |
| 3 | 27 | 498 | 5.4% |
| 4 | 24 | 493 | 4.9% |
| 5 | 23 | 497 | 4.6% |
| **Avg** | **24.6** | **497** | **4.9%** |
| **QIPC** | **25** | **499** | **5.0%** |

## Ensemble Impact

| Metric | Value |
|--------|-------|
| Single-loop avg | 4.9% |
| Best single loop | 5.4% |
| QIPC ensemble | 5.0% |
| Delta vs avg | +0.1% |
| Delta vs best | -0.4% |

## Analysis

Ensemble helps marginally (+0.1% over average). Best single loop (5.4%) still beats ensemble (5.0%).

The model is **stable across stochastic runs** — most answers are the same regardless of temperature. This suggests:
1. The model has high confidence in its answers (even wrong ones)
2. Stochastic sampling doesn't explore enough diversity to help
3. Ensemble voting corrects some errors but introduces others

## What Would Help More

1. **Diverse models** — ensemble across different models (qwen + deepseek + gemini)
2. **Chain-of-thought** — reasoning traces before final answer
3. **CAPT augmentation** — route through knowledge engine for fact-checking
4. **Temperature scheduling** — start high, anneal down

## Files

- Results: `results/500x5_temp07/`
- Master: `master_results.json`
- Scoring: `scoring_results.json`
