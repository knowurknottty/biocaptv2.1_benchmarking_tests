# Self-Play — checkers — biocapt@mock

**Date:** 2026-06-09
**Method:** 5000 self-play games (both sides biocapt@mock), max 200 plies, cross-game memory ON (cap 512 positions)
**Memory bank:** `memory_bank_checkers_biocapt_mock.jsonl`, games 0..4999, head `08f4312d5dc12f95…`

## Progress windows

| Through game | Results | Avg plies | Games/s |
|---|---|---|---|
| 500 | {'black_wins': 247, 'red_wins': 242, 'draw_move_cap': 4, 'draw_repetition': 7} | 65.8 | 2.23 |
| 1000 | {'red_wins': 241, 'black_wins': 253, 'draw_move_cap': 3, 'draw_repetition': 3} | 65.8 | 2.22 |
| 1500 | {'red_wins': 239, 'black_wins': 258, 'draw_repetition': 3} | 63.2 | 2.24 |
| 2000 | {'red_wins': 237, 'black_wins': 259, 'draw_repetition': 4} | 64.8 | 2.24 |
| 2500 | {'red_wins': 246, 'black_wins': 250, 'draw_repetition': 4} | 65.3 | 2.24 |
| 3000 | {'black_wins': 244, 'red_wins': 252, 'draw_repetition': 1, 'draw_move_cap': 3} | 66.0 | 2.23 |
| 3500 | {'black_wins': 243, 'red_wins': 253, 'draw_repetition': 4} | 62.9 | 2.25 |
| 4000 | {'black_wins': 245, 'red_wins': 246, 'draw_repetition': 7, 'draw_move_cap': 2} | 62.6 | 2.26 |
| 4500 | {'red_wins': 232, 'black_wins': 260, 'draw_repetition': 7, 'draw_move_cap': 1} | 64.1 | 2.26 |
| 5000 | {'red_wins': 247, 'black_wins': 246, 'draw_repetition': 7} | 66.4 | 2.25 |

## Memory evidence

- Hash chain verification: PASSED
- Opening diversity: 7 distinct first moves across 5000 games (with deterministic evaluation, diversity > 1 is direct evidence that carried memory changes decisions)
- Top first moves: [('b6-a5', 870), ('d6-c5', 830), ('d6-e5', 815), ('f6-e5', 796), ('b6-c5', 780)]

## Claim boundary

Engine: biocapt@mock. MOCK RUN: validates self-play plumbing, memory persistence, and chain integrity only — no claim about CAPT/bioCAPT behavior.
