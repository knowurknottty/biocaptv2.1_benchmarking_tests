"""Persistent, hash-chained memory bank for CAPT/bioCAPT game self-play.

The v1 worker API reconstructs sealed-binary state by replaying a position
history. Cross-game memory therefore lives client-side: this bank persists
every game's positions in an append-only JSONL ledger, and the tail of the
cumulative position stream seeds the `history` of the next game's requests.
Each record carries a SHA-256 chain hash so the whole memory lineage is
tamper-evident and independently replayable.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


def _canonical(record: dict) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MemoryBank:
    def __init__(self, directory: str | Path, game: str, product: str):
        self.game = game
        self.product = product
        self.path = Path(directory) / f"memory_bank_{game}_{product}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: list[dict] = []
        if self.path.exists():
            with self.path.open(encoding="utf-8") as handle:
                self._records = [json.loads(line) for line in handle if line.strip()]

    @property
    def games_recorded(self) -> int:
        return len(self._records)

    @property
    def head_hash(self) -> str:
        return self._records[-1]["chain_hash"] if self._records else GENESIS

    def append_game(self, *, positions: list, result: str, plies: int,
                    final_state: dict | None, extra: dict | None = None) -> dict:
        body = {
            "schema": "capt_game_memory_v1",
            "game": self.game,
            "product": self.product,
            "game_index": self.games_recorded,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "prev_chain_hash": self.head_hash,
            "result": result,
            "plies": plies,
            "final_state": final_state,
            "positions": positions,
        }
        if extra:
            body["extra"] = extra
        body["chain_hash"] = _sha256(body["prev_chain_hash"] + _canonical(
            {key: value for key, value in body.items() if key != "prev_chain_hash"}
        ))
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(_canonical(body) + "\n")
        self._records.append(body)
        return body

    def seed_history(self, max_positions: int) -> list:
        """Tail of the cumulative position stream, oldest first."""
        if max_positions <= 0:
            return []
        positions: list = []
        for record in reversed(self._records):
            for position in reversed(record["positions"]):
                positions.append(position)
                if len(positions) >= max_positions:
                    return list(reversed(positions))
        return list(reversed(positions))

    def verify_chain(self) -> dict:
        prev = GENESIS
        for index, record in enumerate(self._records):
            if record["prev_chain_hash"] != prev:
                return {"ok": False, "broken_at": index, "reason": "prev_chain_hash mismatch"}
            expected = _sha256(prev + _canonical(
                {key: value for key, value in record.items()
                 if key not in ("prev_chain_hash", "chain_hash")}
            ))
            if record["chain_hash"] != expected:
                return {"ok": False, "broken_at": index, "reason": "chain_hash mismatch"}
            prev = record["chain_hash"]
        return {"ok": True, "games": len(self._records), "head_hash": prev}
