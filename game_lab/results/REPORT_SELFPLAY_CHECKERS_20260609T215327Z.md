# Self-Play — checkers — biocapt@worker

**Date:** 2026-06-09
**Method:** 10 self-play games (both sides biocapt@worker), max 200 plies, cross-game memory ON (cap 512 positions)
**Memory bank:** `memory_bank_checkers_biocapt_mocklocal.jsonl`, games 0..9, head `766ae5faa0af53f4…`

## Progress windows

| Through game | Results | Avg plies | Games/s |
|---|---|---|---|
| 10 | {'black_wins': 6, 'red_wins': 4} | 59.2 | 2.79 |

## Memory evidence

- Hash chain verification: PASSED
- Opening diversity: 5 distinct first moves across 10 games (with deterministic evaluation, diversity > 1 is direct evidence that carried memory changes decisions)
- Top first moves: [('d6-c5', 3), ('h6-g5', 3), ('f6-e5', 2), ('d6-e5', 1), ('f6-g5', 1)]

## Claim boundary

Engine: biocapt@worker. Supports determinism, memory-carry, and state-evolution claims only; no mastery or learning claim without a pre-registered improvement protocol.
