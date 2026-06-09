#!/usr/bin/env python3
"""Checkers arena: CAPT/bioCAPT worker vs baseline bots, with evidence.

Plays N games between the Cloudflare worker engine (POST
/v1/checkers/evaluate) and local baselines (random, greedy-material),
alternating colors, and writes:

  - games JSONL (every move, every worker response incl. memory state)
  - a REPORT-style markdown summary (win/draw/loss, Elo diff estimate,
    memory-state trajectory, replay-determinism check)

Rules come from capt-functional-context-public's verified checkers module
(forced captures, multi-jumps, promotion). Point --rules-path at that
repo's src directory.

Offline plumbing test (no worker, no sealed binaries):

  python3 checkers_worker_arena.py --mock --games 4

Real run:

  python3 checkers_worker_arena.py \
      --worker-url https://capt-biocapt-wasm.<account>.workers.dev \
      --product biocapt --games 20
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_RULES = Path(__file__).resolve().parents[2] / "capt-functional-context-public" / "src"


def load_rules(rules_path: Path):
    sys.path.insert(0, str(rules_path))
    from capt_context.games import checkers  # noqa: PLC0415

    return checkers


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------

class RandomBot:
    name = "random"

    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def choose(self, ck, board, player, history):
        moves = ck.legal_moves(board, player)
        return self.rng.choice(moves), None


class GreedyBot:
    """Max captures, then max material after the move, deterministic ties."""

    name = "greedy"

    def choose(self, ck, board, player, history):
        moves = ck.legal_moves(board, player)
        values = {"r": 1, "R": 2, "b": 1, "B": 2}

        def material(after):
            total = 0
            for row in after:
                for piece in row:
                    if piece == ".":
                        continue
                    sign = 1 if (piece.lower() == "r") == (player == "red") else -1
                    total += sign * values[piece]
            return total

        scored = [
            (len(move.captures), material(ck.apply_move(board, move)), ck.move_notation(move), move)
            for move in moves
        ]
        scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
        return scored[0][3], None


class WorkerEngine:
    """Drives /v1/checkers/evaluate; history of board rows is the memory."""

    def __init__(self, url: str, product: str):
        self.name = f"{product}@worker"
        self.url = url.rstrip("/")
        self.product = product

    def request(self, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}/v1/checkers/evaluate",
            data=data,
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def choose(self, ck, board, player, history):
        moves = ck.legal_moves(board, player)
        by_notation = {ck.move_notation(move): move for move in moves}
        payload = {
            "product": self.product,
            "active": player,
            "board": ck.board_to_rows(board),
            # copy: the live history list keeps growing after this request,
            # and the recorded request must stay byte-replayable
            "history": list(history),
            "candidates": [
                {"move": notation, "board_after": ck.board_to_rows(ck.apply_move(board, move))}
                for notation, move in sorted(by_notation.items())
            ],
        }
        response = self.request(payload)
        chosen = by_notation.get(response.get("selected_move"))
        if chosen is None:
            raise RuntimeError(f"worker returned unknown move: {response.get('selected_move')}")
        return chosen, {"request": payload, "response": response}


class MockWorkerEngine(WorkerEngine):
    """In-process stand-in mirroring worker semantics, for plumbing tests."""

    def __init__(self, product: str = "biocapt"):
        self.name = f"{product}@mock"
        self.product = product

    def request(self, payload):
        state = {"call_count": 0, "acc": 0.0}

        def kernel(rows, active_red):
            counts = Counter("".join(rows))
            features = [
                counts["r"] + 2 * counts["R"] - counts["b"] - 2 * counts["B"],
                counts["R"] - counts["B"],
                1 if active_red else 0,
            ]
            for feature in features:
                state["call_count"] += 1
                state["acc"] = (state["acc"] * 31 + feature * 1000 + 7) % 999983
            return round((state["acc"] % 1000003) / 1000003, 9)

        active_red = payload["active"] == "red"
        for rows in payload["history"]:
            kernel(rows, active_red)
        before = dict(call_count=state["call_count"])
        saved = dict(state)
        ranked = []
        values = {"r": 1, "R": 2, "b": 1, "B": 2, ".": 0}
        for candidate in payload["candidates"]:
            state.update(saved)
            signal = kernel(candidate["board_after"], active_red)
            material = sum(
                (1 if (piece.lower() == "r") == active_red else -1) * values[piece]
                for row in candidate["board_after"] for piece in row if piece != "."
            )
            ranked.append({
                "move": candidate["move"],
                "wasm_signal": signal,
                "material_for_mover": material,
                "score": round(0.5 * signal + 1.0 * material, 9),
            })
        ranked.sort(key=lambda entry: (-entry["score"], entry["move"]))
        state.update(saved)
        chosen_after = next(
            c["board_after"] for c in payload["candidates"] if c["move"] == ranked[0]["move"]
        )
        kernel(chosen_after, active_red)
        return {
            "mode": f"{self.product}_checkers_eval_v1_mock",
            "selected_move": ranked[0]["move"],
            "ranked_moves": ranked,
            "memory": {
                "history_length": len(payload["history"]),
                "state_before_move": before,
                "state_after_move": {"call_count": state["call_count"]},
            },
        }


# ---------------------------------------------------------------------------
# Arena
# ---------------------------------------------------------------------------

def play_game(ck, red_player, black_player, max_plies: int):
    board = ck.initial_board()
    history: list[list[str]] = []
    seen: Counter = Counter()
    moves_log = []
    players = {"red": red_player, "black": black_player}
    active = "red"
    result = "draw_move_cap"
    for ply in range(max_plies):
        legal = ck.legal_moves(board, active)
        if not legal:
            result = f"{('black' if active == 'red' else 'red')}_wins"
            break
        key = ck.board_key(board) + active
        seen[key] += 1
        if seen[key] >= 3:
            result = "draw_repetition"
            break
        move, evidence = players[active].choose(ck, board, active, history)
        history.append(ck.board_to_rows(board))
        entry = {"ply": ply, "player": active, "engine": players[active].name,
                 "move": ck.move_notation(move)}
        if evidence:
            memory = evidence["response"].get("memory", {})
            entry["memory_state"] = memory.get("state_after_move")
            entry["worker_evidence"] = evidence
        moves_log.append(entry)
        board = ck.apply_move(board, move)
        active = "red" if active == "black" else "black"
    return {"result": result, "plies": len(moves_log), "moves": moves_log}


def elo_diff(score_fraction: float) -> float | None:
    if score_fraction <= 0 or score_fraction >= 1:
        return None
    return round(-400 * math.log10(1 / score_fraction - 1), 1)


def run_arena(args):
    ck = load_rules(Path(args.rules_path))
    if args.mock:
        engine = MockWorkerEngine(args.product)
    else:
        if not args.worker_url:
            raise SystemExit("--worker-url is required unless --mock is set")
        engine = WorkerEngine(args.worker_url, args.product)
    baselines = [RandomBot(seed=args.seed), GreedyBot()]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    games_path = out_dir / f"checkers_arena_games_{stamp}.jsonl"
    report_path = out_dir / f"REPORT_CHECKERS_ARENA_{stamp}.md"

    summary = []
    replay_check = None
    with games_path.open("w", encoding="utf-8") as games_file:
        for baseline in baselines:
            tally = Counter()
            call_counts = []
            for game_index in range(args.games):
                engine_is_red = game_index % 2 == 0
                red, black = (engine, baseline) if engine_is_red else (baseline, engine)
                record = play_game(ck, red, black, args.max_plies)
                engine_color = "red" if engine_is_red else "black"
                if record["result"] == f"{engine_color}_wins":
                    tally["win"] += 1
                elif record["result"].endswith("_wins"):
                    tally["loss"] += 1
                else:
                    tally["draw"] += 1
                for move in record["moves"]:
                    state = move.get("memory_state") or {}
                    if "call_count" in state:
                        call_counts.append(state["call_count"])
                games_file.write(json.dumps({
                    "pairing": f"{engine.name} vs {baseline.name}",
                    "engine_color": engine_color,
                    **record,
                }) + "\n")
                # Replay-determinism spot check on the very first worker move.
                if replay_check is None:
                    first = next((m for m in record["moves"] if "worker_evidence" in m), None)
                    if first:
                        again = engine.request(first["worker_evidence"]["request"])
                        replay_check = again == first["worker_evidence"]["response"]
            score = (tally["win"] + 0.5 * tally["draw"]) / max(1, args.games)
            summary.append({
                "baseline": baseline.name,
                "games": args.games,
                "wins": tally["win"], "draws": tally["draw"], "losses": tally["loss"],
                "score": round(score, 3),
                "elo_diff_estimate": elo_diff(score),
                "max_call_count_seen": max(call_counts) if call_counts else None,
            })

    write_report(report_path, engine, args, summary, replay_check, games_path)
    print(f"wrote {games_path}")
    print(f"wrote {report_path}")
    for row in summary:
        print(row)
    return summary


def write_report(path, engine, args, summary, replay_check, games_path):
    lines = [
        f"# Checkers Arena — {engine.name} vs baselines",
        "",
        f"**Date:** {datetime.now(timezone.utc).date().isoformat()}",
        f"**Method:** {args.games} games per pairing, colors alternated, "
        f"max {args.max_plies} plies, threefold repetition = draw",
        f"**Engine:** {engine.name} (history-replay memory, v1 API)",
        "",
        "## Results",
        "",
        "| Baseline | W | D | L | Score | Elo diff est. |",
        "|----------|---|---|---|-------|---------------|",
    ]
    for row in summary:
        elo = row["elo_diff_estimate"]
        lines.append(
            f"| {row['baseline']} | {row['wins']} | {row['draws']} | {row['losses']} "
            f"| {row['score']} | {elo if elo is not None else 'n/a (shutout)'} |"
        )
    lines += [
        "",
        "## Memory evidence",
        "",
        f"- Replay determinism spot check: "
        f"{'PASSED (byte-identical response)' if replay_check else 'NOT VERIFIED' if replay_check is None else 'FAILED'}",
        f"- Max sealed-binary call_count observed in-game: "
        f"{max((row['max_call_count_seen'] or 0) for row in summary)}",
        f"- Full per-move worker requests/responses: `{games_path.name}`",
        "",
        "## Claim boundary",
        "",
        "Win/loss numbers measure this evaluation policy (wasm signal + "
        "material blend) against weak baselines only. No checkers-mastery, "
        "model-quality, or learning claim is supported by this report.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker-url", default="")
    parser.add_argument("--product", default="biocapt", choices=["capt", "biocapt"])
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--max-plies", type=int, default=160)
    parser.add_argument("--seed", type=int, default=20260609)
    parser.add_argument("--rules-path", default=str(DEFAULT_RULES))
    parser.add_argument("--out-dir", default=str(Path(__file__).resolve().parent / "results"))
    parser.add_argument("--mock", action="store_true",
                        help="use an in-process mock engine (plumbing test, no worker)")
    run_arena(parser.parse_args())


if __name__ == "__main__":
    main()
