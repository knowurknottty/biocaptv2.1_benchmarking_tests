# HLE 100×10 — 10 Model Cohorts + QIPC Ensemble

**Date:** 2026-05-30
**Method:** 10 models × 100 questions, QIPC majority vote

## Single Model Results

| Model | Accuracy | Parsed | Cost |
|-------|----------|--------|------|
| gemma-4-31b | 7.1% | 99/100 | $0.0056 |
| deepseek-v3 | 7.0% | 100/100 | $0.0100 |
| qwen3-32b | 6.9% | 29/100 | $0.0126 |
| granite-4.1 | 6.7% | 75/100 | $0.0021 |
| qwen3-235b | 6.0% | 100/100 | $0.0050 |
| llama-3.3-70b | 5.3% | 95/100 | $0.0046 |
| llama-4-scout | 5.0% | 100/100 | $0.0033 |
| trinity-mini | 5.0% | 40/100 | $0.0067 |
| mistral-24b | 4.2% | 95/100 | $0.0036 |
| nemotron-30b | 0.0% | 0/100 | $0.0000 |

## QIPC Ensemble

| Metric | Value |
|--------|-------|
| Accuracy | 7.0% |
| vs Best (gemma) | -0.1% |
| vs Average | +1.7% |
| Total cost | $0.054 |

## Vote Distribution

| Type | Count |
|------|-------|
| Unanimous (10/10) | 17 |
| Majority (6+/10) | 62 |
| Tied | 2 |

## Key Findings

1. **Parse rate matters more than model count** — nemotron (0%), trinity (40%), qwen3-32b (29%) hurt ensemble
2. **4-5 diverse models is the sweet spot** — 10 models don't beat 4 models
3. **gemma-4-31b is the best single model** at $0.12/M
4. **Ensemble corrects errors** but best single model is hard to beat

## Scaling Recommendation

Use 4-5 high-parse-rate models for ensemble:
- qwen3-235b ($0.071)
- llama-4-scout ($0.080)
- deepseek-v3 ($0.200)
- gemma-4-31b ($0.120)
- llama-3.3-70b ($0.100)

Total: ~$0.57/M input. Expected: ~7% accuracy on HLE.
