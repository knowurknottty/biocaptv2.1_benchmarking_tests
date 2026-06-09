# Game Lab

Benchmarks that use chess/checkers as a behavioral testbed for the sealed
CAPT/bioCAPT v2.1 WASM binaries served by the `capt-biocapt-wasm`
Cloudflare Worker (v1 API — see
`capt-functional-context-public/docs/WORKER_API.md`).

What games give us that static benchmarks don't:

1. **Memory under task pressure** — per-game state is reconstructed by
   deterministic history replay, so every decision is auditable and the
   state trajectory (call_count, bio_load, recovery_balance) is recorded
   move by move.
2. **A measurable opponent ladder** — score vs fixed baselines converts
   to an Elo-difference estimate, giving a scalar that can be tracked
   across binary versions and evaluation policies.
3. **Replay determinism as a standing proof** — every run re-sends a
   recorded request and demands a byte-identical response.

## Scripts

### checkers_worker_arena.py

```bash
# offline plumbing test (mock engine, no worker, no binaries)
python3 checkers_worker_arena.py --mock --games 4

# real run against the deployed worker
python3 checkers_worker_arena.py \
    --worker-url https://capt-biocapt-wasm.<account>.workers.dev \
    --product biocapt --games 20
```

Outputs `results/checkers_arena_games_*.jsonl` (full evidence) and
`results/REPORT_CHECKERS_ARENA_*.md` (summary in house report style).
Rules (forced captures, multi-jump, promotion) are imported from
`capt-functional-context-public/src/capt_context/games/checkers.py`;
override the location with `--rules-path`.

## Claim boundary

These reports support claims about determinism, state evolution, and
relative score vs the listed baselines under the documented policy.
They do not support chess/checkers mastery, learning, or model-quality
claims. A learning claim would additionally require a pre-registered
cross-game protocol with improvement trends.
