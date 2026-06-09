"""Memory bank chain integrity tests: python3 test_memory_bank.py"""
import json
import tempfile
from pathlib import Path

from memory_bank import MemoryBank


def test_chain_roundtrip_and_tamper_detection():
    with tempfile.TemporaryDirectory() as tmp:
        bank = MemoryBank(tmp, "checkers", "test")
        for index in range(5):
            bank.append_game(positions=[f"pos{index}a", f"pos{index}b"],
                             result="draw", plies=2,
                             final_state={"call_count": index})
        assert bank.verify_chain()["ok"]

        reloaded = MemoryBank(tmp, "checkers", "test")
        assert reloaded.games_recorded == 5
        assert reloaded.head_hash == bank.head_hash
        assert reloaded.verify_chain()["ok"]
        assert reloaded.seed_history(3) == ["pos3b", "pos4a", "pos4b"]
        assert reloaded.seed_history(100)[0] == "pos0a"

        # tamper with a mid-chain record: verification must localize it
        path = bank.path
        lines = path.read_text().splitlines()
        record = json.loads(lines[2])
        record["result"] = "red_wins"
        lines[2] = json.dumps(record, sort_keys=True, separators=(",", ":"))
        path.write_text("\n".join(lines) + "\n")
        verdict = MemoryBank(tmp, "checkers", "test").verify_chain()
        assert not verdict["ok"] and verdict["broken_at"] == 2

        # resume on top of a clean bank keeps the chain linked
        bank.append_game(positions=["pos5a"], result="draw", plies=1, final_state=None)
        assert bank.games_recorded == 6


if __name__ == "__main__":
    test_chain_roundtrip_and_tamper_detection()
    print("memory bank chain tests passed")
