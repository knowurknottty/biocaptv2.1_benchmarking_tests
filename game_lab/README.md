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

### selfplay_arena.py + memory_bank.py

Self-play (same engine both sides) for chess and checkers with
**persistent cross-game memory**: every game's positions are appended to
a hash-chained JSONL memory bank (`results/memory/`), and the tail of
that bank (capped by `--memory-cap`, default 512 positions) seeds the
`history` of the next game's requests. The worker replays that history,
so the sealed binary's internal state genuinely carries across games
while remaining a deterministic, tamper-evident function of the recorded
lineage. Banks are append-only, so runs resume by re-running the command.

```bash
# plumbing validation at scale (mock engine, no worker required)
python3 selfplay_arena.py --game checkers --mock --games 5000
python3 selfplay_arena.py --game chess    --mock --games 5000   # needs python-chess

# real 5k runs once the worker is deployed
python3 selfplay_arena.py --game checkers --games 5000 --product biocapt \
    --worker-url https://capt-biocapt-wasm.<account>.workers.dev
python3 selfplay_arena.py --game chess --games 5000 --product biocapt \
    --worker-url https://capt-biocapt-wasm.<account>.workers.dev
```

Each run writes `REPORT_SELFPLAY_<GAME>_*.md` with progress windows,
hash-chain verification, and opening diversity (with a deterministic
engine, diversity above 1 is direct evidence that carried memory changes
decisions). Chess rules need python-chess (`pip install chess`; if the
wheel build fails, extract the sdist's `chess/` package onto the path).

### run_priming_pipeline.sh (the local 50k → primed worker path)

One command on a machine with the local WASM bundle:

```bash
./run_priming_pipeline.sh                  # 25000 games per game type vs REAL binaries
GAMES=500 ./run_priming_pipeline.sh        # smaller run
MOCK=1 GAMES=10 ./run_priming_pipeline.sh  # pipeline validation, no binaries
```

It starts `scripts/local-server.mjs` (the worker's exact evaluation code
over the local sealed binaries, bound to 127.0.0.1), runs chess and
checkers self-play in parallel, verifies both memory-bank chains, and
exports primed seeds (`export_primed_seed.py`) into the worker package's
`primed/primed-seeds.json`. Then `cd <worker> && npm test && npm run
deploy` ships a worker whose binaries start every game pre-warmed by the
recorded lineage. Banks are append-only — rerunning resumes on top of
existing memory. Mock and real lineages use separate bank labels and the
exporter refuses broken chains and flags mock-sourced seeds.

## Claim boundary

These reports support claims about determinism, state evolution, and
relative score vs the listed baselines under the documented policy.
They do not support chess/checkers mastery, learning, or model-quality
claims. A learning claim would additionally require a pre-registered
cross-game protocol with improvement trends.
