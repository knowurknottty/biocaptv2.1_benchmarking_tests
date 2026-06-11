# bioCAPT v2.1 → v2.2 Benchmark Comparison

**Date:** 2026-06-11
**Scope:** bounded local benchmark, not full HLE.
**Goal:** compare sealed v2.1 artifacts against the newly built v2.2 pure-CAPTLang sealed artifacts.

## Artifacts compared

| Version | CAPT WASM | bioCAPT WASM |
|---|---:|---:|
| v2.1 | `/Users/knowurknot/2clean4u/CAPTLang_WASM/versions/2.1/wasm/capt_core.sealed.opt.wasm` | `/Users/knowurknot/2clean4u/CAPTLang_WASM/versions/2.1/wasm/biocapt_core.sealed.opt.wasm` |
| v2.2 | `/Users/knowurknot/biocaptv2.2-upgrade-kit/source/biocaptv2.1/build/wasm/capt_core.sealed.wasm` | `/Users/knowurknot/biocaptv2.2-upgrade-kit/source/biocaptv2.1/build/wasm/biocapt_core.sealed.wasm` |

## 1. Deterministic sealed WASM kernel replay

Command:

```bash
node /Users/knowurknot/Biocapt-ecosystem-fullcaptlang/biocaptv2.1_benchmarking_tests/scripts/benchmark_v21_v22_wasm.mjs 500
```

Output JSON:

`/Users/knowurknot/Biocapt-ecosystem-fullcaptlang/biocaptv2.1_benchmarking_tests/results/v21_v22_wasm_direct_benchmark.json`

### CAPT

| Metric | v2.1 | v2.2 | Delta |
|---|---:|---:|---:|
| WASM bytes | 14,688 | 24,531 | +9,843 |
| Steps | 500 | 500 | 0 |
| Final call_count | 500 | 500 | 0 |
| Final active_modules | 46 | 49 | +3 |
| Average active_modules | 46.0 | 49.0 | +3.0 |
| Final metrics | 0.5120184808 | 0.5258014597 | +0.0137829789 |
| Average metrics | 0.6378089508 | 0.5629635641 | -0.0748453867 |

### bioCAPT

| Metric | v2.1 | v2.2 | Delta |
|---|---:|---:|---:|
| WASM bytes | 9,390 | 15,894 | +6,504 |
| Steps | 500 | 500 | 0 |
| Final call_count | 1,000 | 1,000 | 0 |
| Final active_modules | 24 | 27 | +3 |
| Average active_modules | 24.0 | 27.0 | +3.0 |
| Final metrics | 0.6559418381 | 0.5531925647 | -0.1027492734 |
| Average metrics | 0.6909997580 | 0.5756145831 | -0.1153851749 |
| Final bio_load | 0.8770382789 | 0.8792697231 | +0.0022314443 |
| Final recovery_balance | 0.4350713284 | 0.4290934492 | -0.0059778792 |

### Interpretation

- v2.2 is larger because the pure-CAPTLang context/checkpoint/adaptive-effort modules are now inside the sealed binary.
- v2.2 activates +3 modules for both CAPT and bioCAPT, matching the three added v2.2 modules.
- In this deterministic kernel replay, v2.2 does **not** improve the exported scalar `metrics` average. It lowers average metrics in both CAPT and bioCAPT.
- bioCAPT v2.2 final `bio_load` is effectively unchanged from v2.1 in this run.
- This benchmark supports an integration claim, not a quality-improvement claim.

## 2. Checkers probe vs fixed greedy baseline

Setup:

- v2.1 local worker on `http://127.0.0.1:8791`
- v2.2 local worker on `http://127.0.0.1:8792`
- Both loaded the same v1 evaluation code.
- Both used the same primed seed file.
- Checkers: 10 self-play games, max 80 plies, memory cap 512, probe every game, 10 probe games per checkpoint.

v2.1 report:

`/Users/knowurknot/Biocapt-ecosystem-fullcaptlang/biocaptv2.1_benchmarking_tests/game_lab/results/v21_checkers_probe/REPORT_SELFPLAY_CHECKERS_20260611T150646Z.md`

v2.2 report:

`/Users/knowurknot/Biocapt-ecosystem-fullcaptlang/biocaptv2.1_benchmarking_tests/game_lab/results/v22_checkers_probe/REPORT_SELFPLAY_CHECKERS_20260611T150722Z.md`

### Checkers results

| Metric | v2.1 | v2.2 | Delta |
|---|---:|---:|---:|
| Self-play games | 10 | 10 | 0 |
| Avg plies | 80.0 | 80.0 | 0 |
| Result distribution | 10 draw_move_cap | 10 draw_move_cap | 0 |
| Games/s | 2.31 | 2.16 | -0.15 |
| Final probe score vs greedy | 0.25 | 0.25 | 0 |
| Probe score movement | 0.25 → 0.25 | 0.25 → 0.25 | no change |
| Opening diversity | 1 first move | 1 first move | 0 |
| Top first move | b6-a5 | b6-a5 | same |
| Memory hash chain | PASSED | PASSED | — |

### Interpretation

- v2.2 checkers behavior is stable and deterministic.
- In this bounded checkers probe, v2.2 does **not** improve score vs greedy over v2.1.
- v2.2 is slightly slower in this small local run: 2.16 games/s vs 2.31 games/s.
- The checkers probe supports determinism/state-evolution, not a learning or mastery claim.

## Bottom line

The data proves the v2.2 upgrades are integrated and measurable:

- pure-CAPTLang modules are present in the sealed WASM
- active module count increases by exactly +3
- memory/state replay remains deterministic
- checkers hash-chain validation passes

The data does **not** prove a quality improvement yet:

- average exported `metrics` decreased in the deterministic kernel replay
- checkers score vs greedy stayed flat at 0.25
- games/s was slightly lower in the v2.2 checkers run

Next benchmark to prove quality would need a pre-registered protocol: larger game count, multiple seeds, v2.1 vs v2.2 side-by-side probes, and possibly HLE/answer-quality scoring with the same model budget.
