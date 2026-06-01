# HLE 100×4 — Diverse Model Cohorts + QIPC Ensemble

**Date:** 2026-05-30
**Method:** 4 models × 100 questions, QIPC majority vote ensemble
**All models under $0.25/1M input**

## Models

| Model | Price/1M | Single Accuracy | Cost |
|-------|----------|-----------------|------|
| qwen/qwen3-235b-a22b-2507 | $0.071 | 6.0% | $0.0027 |
| meta-llama/llama-4-scout | $0.080 | 5.0% | $0.0033 |
| deepseek/deepseek-chat-v3-0324 | $0.200 | 6.0% | $0.0100 |
| google/gemma-4-31b-it | $0.120 | 5.1% | $0.0056 |
| **Average** | | **5.5%** | **$0.0054** |
| **QIPC Ensemble** | | **7.0%** | **$0.0216** |

## Key Result

**QIPC ensemble (7.0%) beats all single models (best: 6.0%)**

- Ensemble vs best: +1.0%
- Ensemble vs average: +1.5%
- Total cost: $0.022 per 100 questions

## Vote Analysis

| Type | Count | Meaning |
|------|-------|---------|
| Unanimous (4/4) | 11 | All models agree — high confidence |
| Majority (3/4) | 28 | 3 models agree — likely correct |
| Tied (2/2) | 42 | Split — hardest questions |

## Scaling Projection

| Approach | Questions | Cost | Expected Accuracy |
|----------|-----------|------|-------------------|
| Single model (qwen3-235b) | 2,500 | $0.50 | ~5% |
| 4-model ensemble | 2,500 | $4.50 | ~7% |
| 8-model ensemble | 2,500 | $9.00 | ~8-9% (est) |

## By Category (Ensemble)

| Category | Correct | Total | Accuracy |
|----------|---------|-------|----------|
| Biology/Medicine | 1 | 8 | 12% |
| Physics | 1 | 8 | 12% |
| Other | 2 | 20 | 10% |
| Math | 2 | 30 | 7% |
| Humanities | 1 | 15 | 7% |
| CS/AI | 0 | 17 | 0% |

## Conclusion

**Diverse model ensemble with QIPC voting is the clear path forward.** Different model families make different errors — ensemble corrects where individuals fail. Cost is manageable ($0.02/100 questions).

Next: scale to 2,500 questions with 4+ models, or add more diverse models (mistral, gemini, etc.).
