# Self-Play — chess — biocapt@mock

**Date:** 2026-06-09
**Method:** 5000 self-play games (both sides biocapt@mock), max 200 plies, cross-game memory ON (cap 512 positions)
**Memory bank:** `memory_bank_chess_biocapt_mock.jsonl`, games 0..4999, head `4c2a17713afeeda5…`

## Progress windows

| Through game | Results | Avg plies | Games/s |
|---|---|---|---|
| 500 | {'draw': 391, 'draw_move_cap': 80, 'black_wins': 17, 'white_wins': 12} | 141.6 | 1.11 |
| 1000 | {'draw_move_cap': 94, 'draw': 373, 'black_wins': 17, 'white_wins': 16} | 143.2 | 1.1 |
| 1500 | {'draw_move_cap': 100, 'draw': 378, 'white_wins': 17, 'black_wins': 5} | 148.2 | 1.09 |
| 2000 | {'draw': 386, 'draw_move_cap': 100, 'black_wins': 7, 'white_wins': 7} | 148.2 | 1.08 |
| 2500 | {'draw_move_cap': 99, 'draw': 381, 'white_wins': 11, 'black_wins': 9} | 147.7 | 1.08 |
| 3000 | {'draw': 364, 'draw_move_cap': 109, 'white_wins': 17, 'black_wins': 10} | 146.4 | 1.08 |
| 3500 | {'draw': 383, 'draw_move_cap': 93, 'black_wins': 11, 'white_wins': 13} | 144.5 | 1.08 |
| 4000 | {'white_wins': 13, 'draw': 386, 'draw_move_cap': 85, 'black_wins': 16} | 143.8 | 1.08 |
| 4500 | {'draw_move_cap': 95, 'draw': 386, 'white_wins': 7, 'black_wins': 12} | 147.9 | 1.08 |
| 5000 | {'draw_move_cap': 89, 'draw': 393, 'black_wins': 5, 'white_wins': 13} | 146.2 | 1.08 |

## Memory evidence

- Hash chain verification: PASSED
- Opening diversity: 20 distinct first moves across 5000 games (with deterministic evaluation, diversity > 1 is direct evidence that carried memory changes decisions)
- Top first moves: [('g2g3', 386), ('b1c3', 379), ('f2f4', 372), ('b1a3', 357), ('a2a4', 351)]

## Claim boundary

Engine: biocapt@mock. MOCK RUN: validates self-play plumbing, memory persistence, and chain integrity only — no claim about CAPT/bioCAPT behavior.
