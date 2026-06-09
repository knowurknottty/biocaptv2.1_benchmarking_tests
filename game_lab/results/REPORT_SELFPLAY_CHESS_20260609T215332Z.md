# Self-Play — chess — biocapt@worker

**Date:** 2026-06-09
**Method:** 10 self-play games (both sides biocapt@worker), max 200 plies, cross-game memory ON (cap 512 positions)
**Memory bank:** `memory_bank_chess_biocapt_mocklocal.jsonl`, games 0..9, head `a446e91df9781bd2…`

## Progress windows

| Through game | Results | Avg plies | Games/s |
|---|---|---|---|
| 10 | {'draw': 8, 'white_wins': 1, 'black_wins': 1} | 116.8 | 1.22 |

## Memory evidence

- Hash chain verification: PASSED
- Opening diversity: 7 distinct first moves across 10 games (with deterministic evaluation, diversity > 1 is direct evidence that carried memory changes decisions)
- Top first moves: [('c2c4', 2), ('d2d4', 2), ('b1a3', 2), ('g1h3', 1), ('e2e4', 1)]

## Claim boundary

Engine: biocapt@worker. Supports determinism, memory-carry, and state-evolution claims only; no mastery or learning claim without a pre-registered improvement protocol.
