#!/usr/bin/env python3
"""Self-play arena for chess and checkers with persistent cross-game memory.

The same engine (CAPT or bioCAPT via the v1 worker API) plays both sides.
Every game's positions are appended to a hash-chained MemoryBank; the tail
of that bank seeds the `history` of the next game, so the sealed binary's
internal state genuinely carries across games while staying a deterministic,
auditable function of the recorded lineage. The bank is append-only, so
runs are resumable: re-running adds games on top of the existing memory.

Offline plumbing validation (mock engine, no worker, no sealed binaries):

  python3 selfplay_arena.py --game checkers --mock --games 5000
  python3 selfplay_arena.py --game chess    --mock --games 5000

Real runs once the worker is deployed:

  python3 selfplay_arena.py --game chess --games 5000 --product biocapt \
      --worker-url https://capt-biocapt-wasm.<account>.workers.dev

Chess rules need python-chess (pip install chess); checkers rules come from
capt-functional-context-public.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from memory_bank import MemoryBank

HERE = Path(__file__).resolve().parent
DEFAULT_RULES = HERE.parents[1] / "capt-functional-context-public" / "src"


# ---------------------------------------------------------------------------
# Game adapters: rules, encoding, terminal detection
# ---------------------------------------------------------------------------

class CheckersAdapter:
    endpoint = "checkers"

    def __init__(self, rules_path: Path):
        sys.path.insert(0, str(rules_path))
        from capt_context.games import checkers  # noqa: PLC0415
        self.ck = checkers

    def new_game(self):
        return {"board": self.ck.initial_board(), "active": "red", "seen": Counter()}

    def position(self, state):
        return self.ck.board_to_rows(state["board"])

    def terminal(self, state):
        if not self.ck.legal_moves(state["board"], state["active"]):
            return f"{'black' if state['active'] == 'red' else 'red'}_wins"
        key = self.ck.board_key(state["board"]) + state["active"]
        if state["seen"][key] >= 3:
            return "draw_repetition"
        return None

    def candidates(self, state):
        moves = self.ck.legal_moves(state["board"], state["active"])
        return [
            {
                "move": self.ck.move_notation(move),
                "board_after": self.ck.board_to_rows(self.ck.apply_move(state["board"], move)),
                "_move": move,
            }
            for move in moves
        ]

    def payload_fields(self, state):
        return {"board": self.position(state), "active": state["active"]}

    def after_key(self):
        return "board_after"

    def apply(self, state, candidate):
        state["seen"][self.ck.board_key(state["board"]) + state["active"]] += 1
        state["board"] = self.ck.apply_move(state["board"], candidate["_move"])
        state["active"] = "red" if state["active"] == "black" else "black"

    def mover(self, state):
        return state["active"]


class ChessAdapter:
    endpoint = "chess"

    def __init__(self, _rules_path):
        import chess  # noqa: PLC0415
        self.chess = chess

    def new_game(self):
        return {"board": self.chess.Board()}

    def position(self, state):
        return state["board"].fen()

    def terminal(self, state):
        board = state["board"]
        if board.is_checkmate():
            return f"{'black' if board.turn else 'white'}_wins"
        if board.is_game_over(claim_draw=True):
            return "draw"
        return None

    def candidates(self, state):
        board = state["board"]
        out = []
        for move in board.legal_moves:
            board.push(move)
            out.append({"move": move.uci(), "fen_after": board.fen(), "_move": move})
            board.pop()
        return out

    def payload_fields(self, state):
        return {"fen": self.position(state)}

    def after_key(self):
        return "fen_after"

    def apply(self, state, candidate):
        state["board"].push(candidate["_move"])

    def mover(self, state):
        return "white" if state["board"].turn else "black"


ADAPTERS = {"checkers": CheckersAdapter, "chess": ChessAdapter}


# ---------------------------------------------------------------------------
# Engines: real worker client and a deterministic mock with the same contract
# ---------------------------------------------------------------------------

class WorkerClient:
    def __init__(self, url: str, product: str, endpoint: str):
        import urllib.request  # noqa: PLC0415
        self.urllib = urllib.request
        self.name = f"{product}@worker"
        self.url = url.rstrip("/")
        self.product = product
        self.endpoint = endpoint

    def request(self, payload):
        data = json.dumps(payload).encode("utf-8")
        req = self.urllib.Request(
            f"{self.url}/v1/{self.endpoint}/evaluate",
            data=data, headers={"content-type": "application/json"}, method="POST",
        )
        with self.urllib.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))


class MockClient:
    """Deterministic stateful kernel mirroring v1 semantics, for plumbing."""

    def __init__(self, product: str, endpoint: str):
        self.name = f"{product}@mock"
        self.product = product
        self.endpoint = endpoint

    @staticmethod
    def _fingerprint(text):
        # FNV-1a scaled to [0, 32): distinct positions -> distinct features,
        # mirroring the worker's positionFingerprint
        hash_value = 2166136261
        for char in text:
            hash_value = ((hash_value ^ ord(char)) * 16777619) & 0xFFFFFFFF
        return (hash_value % 4096) / 128

    def _features(self, position):
        if self.endpoint == "checkers":
            counts = Counter("".join(position))
            return [
                counts["r"] + 2 * counts["R"] - counts["b"] - 2 * counts["B"],
                counts["R"] - counts["B"],
                (counts["r"] + counts["b"]) / 4,
                self._fingerprint("/".join(position)),
            ]
        board = str(position).split()[0]
        values = {"p": 1, "n": 3, "b": 3, "r": 5, "q": 9, "k": 0}
        material = sum(
            (values[char.lower()] if char.isupper() else -values[char.lower()])
            for char in board if char.isalpha()
        )
        return [material, board.count("/"), len(board) / 16,
                self._fingerprint(" ".join(str(position).split()[:4]))]

    def _material_for_mover(self, payload, position):
        if self.endpoint == "checkers":
            counts = Counter("".join(position))
            delta = counts["r"] + 2 * counts["R"] - counts["b"] - 2 * counts["B"]
            return delta if payload["active"] == "red" else -delta
        mover_is_white = str(payload["fen"]).split()[1] != "b"
        delta = self._features(position)[0]
        return delta if mover_is_white else -delta

    def request(self, payload):
        state = {"calls": 0, "acc": 0.0}

        def kernel(position):
            for feature in self._features(position):
                state["calls"] += 1
                # multiplier depends on the input so the signal is nonlinearly
                # coupled to carried state (a linear fold would shift every
                # candidate equally and hide memory effects from rankings)
                step = round(feature * 1000) + 7
                state["acc"] = (state["acc"] * (31 + abs(step) % 17) + step) % 999983
            return round((state["acc"] % 1000003) / 1000003, 9)

        for position in payload["history"]:
            kernel(position)
        before = {"call_count": state["calls"]}
        saved = dict(state)
        after_key = "board_after" if self.endpoint == "checkers" else "fen_after"
        ranked = []
        for candidate in payload["candidates"]:
            state.update(saved)
            signal = kernel(candidate[after_key])
            material = self._material_for_mover(payload, candidate[after_key])
            ranked.append({
                "move": candidate["move"], "wasm_signal": signal,
                "material_for_mover": material,
                "score": round(0.5 * signal + 1.0 * material, 9),
            })
        ranked.sort(key=lambda entry: (-entry["score"], entry["move"]))
        state.update(saved)
        chosen = next(c for c in payload["candidates"] if c["move"] == ranked[0]["move"])
        kernel(chosen[after_key])
        return {
            "mode": f"{self.product}_{self.endpoint}_eval_v1_mock",
            "selected_move": ranked[0]["move"],
            "ranked_moves": ranked,
            "memory": {
                "history_length": len(payload["history"]),
                "state_before_move": before,
                "state_after_move": {"call_count": state["calls"]},
            },
        }


# ---------------------------------------------------------------------------
# Self-play loop
# ---------------------------------------------------------------------------

def play_one_game(adapter, engine, seed_history, max_plies):
    state = adapter.new_game()
    game_positions = [adapter.position(state)]
    moves = []
    last_memory_state = None
    result = "draw_move_cap"
    for _ in range(max_plies):
        terminal = adapter.terminal(state)
        if terminal:
            result = terminal
            break
        candidates = adapter.candidates(state)
        payload = {
            "product": engine.product,
            **adapter.payload_fields(state),
            "history": seed_history + game_positions[:-1],
            "candidates": [
                {"move": c["move"], adapter.after_key(): c[adapter.after_key()]}
                for c in candidates
            ],
        }
        response = engine.request(payload)
        chosen = next(
            (c for c in candidates if c["move"] == response["selected_move"]), None)
        if chosen is None:
            raise RuntimeError(f"engine returned unknown move {response['selected_move']}")
        top = response["ranked_moves"][0]
        moves.append({
            "mover": adapter.mover(state), "move": chosen["move"],
            "signal": top.get("wasm_signal"), "score": top.get("score"),
        })
        last_memory_state = response.get("memory", {}).get("state_after_move")
        adapter.apply(state, chosen)
        game_positions.append(adapter.position(state))
    else:
        terminal = adapter.terminal(state)
        if terminal:
            result = terminal
    return {
        "result": result, "plies": len(moves), "moves": moves,
        "positions": game_positions, "final_state": last_memory_state,
        "first_move": moves[0]["move"] if moves else None,
    }


def run(args):
    adapter = ADAPTERS[args.game](Path(args.rules_path))
    if args.mock:
        engine = MockClient(args.product, adapter.endpoint)
    else:
        if not args.worker_url:
            raise SystemExit("--worker-url is required unless --mock is set")
        engine = WorkerClient(args.worker_url, args.product, adapter.endpoint)

    out_dir = Path(args.out_dir)
    bank = MemoryBank(out_dir / "memory", args.game, engine.name.replace("@", "_"))
    start_index = bank.games_recorded
    print(f"memory bank: {bank.path} ({start_index} games already recorded)")

    windows = []
    window_stats = Counter()
    window_plies = []
    first_moves = Counter()
    started = time.time()

    for game_number in range(args.games):
        seed = bank.seed_history(args.memory_cap) if args.carry_memory else []
        record = play_one_game(adapter, engine, seed, args.max_plies)
        bank.append_game(
            positions=record["positions"], result=record["result"],
            plies=record["plies"], final_state=record["final_state"],
            extra={"first_move": record["first_move"], "seed_positions": len(seed)},
        )
        window_stats[record["result"]] += 1
        window_plies.append(record["plies"])
        first_moves[record["first_move"]] += 1
        if (game_number + 1) % args.window == 0 or game_number + 1 == args.games:
            elapsed = time.time() - started
            done = game_number + 1
            windows.append({
                "through_game": start_index + done,
                "results": dict(window_stats),
                "avg_plies": round(sum(window_plies) / max(1, len(window_plies)), 1),
                "games_per_sec": round(done / max(elapsed, 1e-9), 2),
            })
            print(f"[{args.game}/{engine.name}] {done}/{args.games} games "
                  f"({windows[-1]['games_per_sec']}/s) window={dict(window_stats)} "
                  f"avg_plies={windows[-1]['avg_plies']}")
            window_stats = Counter()
            window_plies = []

    chain = bank.verify_chain()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = out_dir / f"REPORT_SELFPLAY_{args.game.upper()}_{stamp}.md"
    write_report(report_path, args, engine, bank, windows, first_moves, chain, start_index)
    print(f"chain verification: {chain}")
    print(f"wrote {report_path}")


def write_report(path, args, engine, bank, windows, first_moves, chain, start_index):
    diversity = len(first_moves)
    total = sum(first_moves.values())
    lines = [
        f"# Self-Play — {args.game} — {engine.name}",
        "",
        f"**Date:** {datetime.now(timezone.utc).date().isoformat()}",
        f"**Method:** {total} self-play games (both sides {engine.name}), "
        f"max {args.max_plies} plies, cross-game memory "
        f"{'ON (cap ' + str(args.memory_cap) + ' positions)' if args.carry_memory else 'OFF'}",
        f"**Memory bank:** `{bank.path.name}`, games {start_index}..{bank.games_recorded - 1}, "
        f"head `{bank.head_hash[:16]}…`",
        "",
        "## Progress windows",
        "",
        "| Through game | Results | Avg plies | Games/s |",
        "|---|---|---|---|",
    ]
    for window in windows:
        lines.append(f"| {window['through_game']} | {window['results']} "
                     f"| {window['avg_plies']} | {window['games_per_sec']} |")
    lines += [
        "",
        "## Memory evidence",
        "",
        f"- Hash chain verification: {'PASSED' if chain['ok'] else 'FAILED: ' + str(chain)}",
        f"- Opening diversity: {diversity} distinct first moves across {total} games "
        f"(with deterministic evaluation, diversity > 1 is direct evidence that "
        f"carried memory changes decisions)",
        f"- Top first moves: {first_moves.most_common(5)}",
        "",
        "## Claim boundary",
        "",
        f"Engine: {engine.name}. "
        + ("MOCK RUN: validates self-play plumbing, memory persistence, and "
           "chain integrity only — no claim about CAPT/bioCAPT behavior."
           if "mock" in engine.name else
           "Supports determinism, memory-carry, and state-evolution claims "
           "only; no mastery or learning claim without a pre-registered "
           "improvement protocol."),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", choices=["chess", "checkers"], required=True)
    parser.add_argument("--games", type=int, default=5000)
    parser.add_argument("--product", default="biocapt", choices=["capt", "biocapt"])
    parser.add_argument("--worker-url", default="")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--max-plies", type=int, default=200)
    parser.add_argument("--memory-cap", type=int, default=512,
                        help="max seed positions carried into each new game")
    parser.add_argument("--no-carry-memory", dest="carry_memory", action="store_false")
    parser.add_argument("--window", type=int, default=250)
    parser.add_argument("--rules-path", default=str(DEFAULT_RULES))
    parser.add_argument("--out-dir", default=str(HERE / "results"))
    run(parser.parse_args())


if __name__ == "__main__":
    main()
