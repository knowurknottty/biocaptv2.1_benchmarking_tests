#!/usr/bin/env python3
"""Export a primed memory seed from a self-play memory bank.

Verifies the bank's hash chain, takes the tail of the cumulative position
stream, and merges it into the worker's primed/primed-seeds.json so the next
`npm run deploy` ships a worker whose sealed binaries start every game
pre-warmed by the recorded self-play lineage.

  python3 export_primed_seed.py --game checkers --product biocapt
  python3 export_primed_seed.py --game chess --product biocapt \
      --positions 512 --seeds-file ../../capt-functional-context-public/cloudflare/capt-wasm-worker/primed/primed-seeds.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from memory_bank import MemoryBank

HERE = Path(__file__).resolve().parent
DEFAULT_SEEDS = (HERE.parents[1] / "capt-functional-context-public" / "cloudflare"
                 / "capt-wasm-worker" / "primed" / "primed-seeds.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", choices=["chess", "checkers"], required=True)
    parser.add_argument("--product", default="biocapt", choices=["capt", "biocapt"])
    parser.add_argument("--bank-label", default="",
                        help="bank product label; defaults to <product>_worker, "
                             "falling back to <product>_mock")
    parser.add_argument("--bank-dir", default=str(HERE / "results" / "memory"))
    parser.add_argument("--positions", type=int, default=512)
    parser.add_argument("--seeds-file", default=str(DEFAULT_SEEDS))
    args = parser.parse_args()

    labels = [args.bank_label] if args.bank_label else [
        f"{args.product}_worker", f"{args.product}_mock"]
    bank = None
    for label in labels:
        candidate = MemoryBank(args.bank_dir, args.game, label)
        if candidate.games_recorded:
            bank = candidate
            break
    if bank is None:
        raise SystemExit(f"no non-empty bank found for labels {labels} in {args.bank_dir}")

    chain = bank.verify_chain()
    if not chain["ok"]:
        raise SystemExit(f"REFUSING to export from a broken chain: {chain}")

    mock_bank = "mock" in bank.path.stem
    seed = {
        "positions": bank.seed_history(args.positions),
        "games": bank.games_recorded,
        "head_hash": bank.head_hash,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bank_file": bank.path.name,
        "mock_source": mock_bank,
    }

    seeds_path = Path(args.seeds_file)
    seeds = json.loads(seeds_path.read_text()) if seeds_path.exists() else {}
    seeds.setdefault(args.game, {})[args.product] = seed
    seeds_path.parent.mkdir(parents=True, exist_ok=True)
    seeds_path.write_text(json.dumps(seeds, indent=2) + "\n")

    print(f"exported {len(seed['positions'])} positions from {bank.games_recorded} games "
          f"({bank.path.name}, chain VERIFIED, head {bank.head_hash[:16]}…)")
    print(f"-> {seeds_path}")
    if mock_bank:
        print("WARNING: source bank is from a MOCK run — fine for pipeline tests, "
              "do not deploy as a real priming claim.")


if __name__ == "__main__":
    main()
