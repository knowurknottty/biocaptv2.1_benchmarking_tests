# Self-Play — checkers — biocapt@worker

**Date:** 2026-06-11
**Method:** 10 self-play games (both sides biocapt@worker), max 80 plies, cross-game memory ON (cap 512 positions)
**Memory bank:** `memory_bank_checkers_v22_checkers_probe.jsonl`, games 0..9, head `5d67efea26800092…`

## Progress windows

| Through game | Results | Avg plies | Games/s |
|---|---|---|---|
| 10 | {'draw_move_cap': 10} | 80.0 | 2.16 |

## Learning curve (probe matches vs fixed greedy baseline)

| After games | Score vs greedy | Probe games | Memory positions |
|---|---|---|---|
| 0 | 0.25 | 10 | 0 |
| 1 | 0.25 | 10 | 81 |
| 2 | 0.25 | 10 | 162 |
| 3 | 0.25 | 10 | 243 |
| 4 | 0.25 | 10 | 324 |
| 5 | 0.25 | 10 | 405 |
| 6 | 0.25 | 10 | 486 |
| 7 | 0.25 | 10 | 512 |
| 8 | 0.25 | 10 | 512 |
| 9 | 0.25 | 10 | 512 |
| 10 | 0.25 | 10 | 512 |

Probe matches use the current memory bank but are NOT recorded into it. Score moved 0.25 -> 0.25 over the run. A flat curve means accumulated memory does not improve play against this baseline; only a sustained rise supports a learning claim.

## Memory evidence

- Hash chain verification: PASSED
- Opening diversity: 1 distinct first moves across 10 games (with deterministic evaluation, diversity > 1 is direct evidence that carried memory changes decisions)
- Top first moves: [('b6-a5', 10)]

## Claim boundary

Engine: biocapt@worker. Supports determinism, memory-carry, and state-evolution claims only; no mastery or learning claim without a pre-registered improvement protocol.
