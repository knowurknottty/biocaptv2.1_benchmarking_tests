#!/usr/bin/env python3
"""
HLE bioCAPT inspection harness — follows Jenn-ai golden monitor pattern exactly.
455 vessels: 2 input + 4 internal + 2 output per module, remainder as proctors.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

BIOCAPT_ROOT = Path("/Users/knowurknot/Biocapt-ecosystem-fullcaptlang/primary/biocapt-desktop")
HLE_ROOT = Path("/Users/knowurknot/Biocapt-ecosystem-fullcaptlang/hle-eval")
INSPECTION_DIR = HLE_ROOT / "results" / "inspection"

sys.path.insert(0, str(BIOCAPT_ROOT))

from openclaw_skill.capt_skill import (
    capt_capabilities,
    capt_memory_recent,
    capt_memory_recall,
    capt_memory_store,
    capt_metrics,
    capt_status,
    capt_vector_search,
    capt_vector_store,
)


def now() -> float:
    return time.time()


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def capture_call(trace: Path, name: str, fn: Any, *args: Any, **kwargs: Any) -> Any:
    started = now()
    write_jsonl(trace, {"event": "biocapt_call_start", "name": name, "ts": started})
    try:
        result = fn(*args, **kwargs)
        write_jsonl(
            trace,
            {
                "event": "biocapt_call_end",
                "name": name,
                "ts": now(),
                "elapsed_s": round(now() - started, 6),
                "ok": True,
                "result_digest": digest_text(json.dumps(result, default=str, sort_keys=True)),
                "result_preview": json.dumps(result, default=str, sort_keys=True)[:900],
            },
        )
        return result
    except Exception as exc:
        write_jsonl(
            trace,
            {
                "event": "biocapt_call_end",
                "name": name,
                "ts": now(),
                "elapsed_s": round(now() - started, 6),
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        raise


def vessel_map(status: dict[str, Any], requested_vessels: int) -> dict[str, Any]:
    modules = sorted((status.get("module_status") or {}).keys())
    required = len(modules) * 8
    slack = requested_vessels - required
    allocations = []
    vessel_index = 1
    for module in modules:
        slots = []
        for phase, count in (("input", 2), ("internal", 4), ("output", 2)):
            for local_index in range(1, count + 1):
                slots.append(
                    {
                        "vessel": f"inspection-v{vessel_index:03d}",
                        "phase": phase,
                        "slot": local_index,
                    }
                )
                vessel_index += 1
        allocations.append({"module": module, "slots": slots})
    return {
        "requested_vessels": requested_vessels,
        "modules": len(modules),
        "required_vessels": required,
        "slack_vessels": slack,
        "coverage_rule": "2 input, 4 internal, 2 output vessels per active module",
        "allocations": allocations,
    }


def run_hle_inspection() -> int:
    trace = INSPECTION_DIR / "hle_biocapt_internal_trace.jsonl"
    stage = "hle_benchmark"
    write_jsonl(trace, {"event": "inspection_stage_start", "stage": stage, "ts": now()})

    # --- PRE-TEST CAPTURE ---
    before_status = capture_call(trace, "capt_status.before", capt_status)
    before_metrics = capture_call(trace, "capt_metrics.before", capt_metrics)
    capabilities = capture_call(trace, "capt_capabilities", capt_capabilities)
    allocations = vessel_map(before_status, 455)

    # --- LOAD TEST QUESTIONS ---
    questions_file = HLE_ROOT / "hle_blind_sample.json"
    with open(questions_file) as f:
        questions = json.load(f)

    answer_key_file = HLE_ROOT / "hle_answer_key.json"
    with open(answer_key_file) as f:
        answer_key = json.load(f)

    # Store question set to CAPT memory
    for i, q in enumerate(questions):
        capture_call(
            trace,
            f"capt_memory_store.question_{i}",
            capt_memory_store,
            f"hle_benchmark:question:{q['id']}",
            {
                "question_id": q['id'],
                "question_text": q['question'][:2000],
                "category": q['category'],
                "answer_type": q['answer_type'],
                "raw_subject": q['raw_subject'],
                "stage": stage,
            },
            "hle_benchmark",
        )

    # Store questions to vector store for retrieval
    capture_call(
        trace,
        "capt_vector_store.questions",
        capt_vector_store,
        "hle_benchmark",
        json.dumps([{"id": q["id"], "question": q["question"][:1000], "category": q["category"]} for q in questions]),
        {"source": "hle_blind_sample", "count": len(questions), "stage": stage},
    )

    # --- LOAD VESSEL RESULTS (what the test vessels produced) ---
    results_dir = HLE_ROOT / "results" / "run_20260530_225648"
    all_predictions = {}
    vessel_files = sorted(results_dir.glob("vessel_*_results.json"))
    for vf in vessel_files:
        vessel_data = json.loads(vf.read_text())
        for pred in vessel_data:
            all_predictions[pred["id"]] = pred
            capture_call(
                trace,
                f"capt_memory_store.prediction.{pred['id'][:8]}",
                capt_memory_store,
                f"hle_benchmark:prediction:{pred['id']}",
                {
                    "question_id": pred["id"],
                    "answer": pred.get("answer", ""),
                    "confidence": pred.get("confidence", 0),
                    "reasoning_preview": pred.get("reasoning", "")[:500],
                    "stage": stage,
                },
                "hle_benchmark",
            )

    # Store predictions to vector store
    capture_call(
        trace,
        "capt_vector_store.predictions",
        capt_vector_store,
        "hle_benchmark_predictions",
        json.dumps([{"id": p["id"], "answer": p.get("answer", ""), "confidence": p.get("confidence", 0)} for p in all_predictions.values()]),
        {"source": "vessel_results", "count": len(all_predictions), "stage": stage},
    )

    # --- SCORING ---
    scored = 0
    correct = 0
    score_details = []
    for qid, pred in all_predictions.items():
        expected = answer_key.get(qid, "")
        got = pred.get("answer", "")
        scored += 1

        got_norm = got.strip().lower().replace("$", "").replace("\\", "").replace(" ", "")
        exp_norm = expected.strip().lower().replace("$", "").replace("\\", "").replace(" ", "")
        is_correct = got_norm == exp_norm

        if is_correct:
            correct += 1

        detail = {
            "id": qid,
            "expected": expected,
            "got": got,
            "correct": is_correct,
            "confidence": pred.get("confidence", 0),
        }
        score_details.append(detail)

        capture_call(
            trace,
            f"capt_memory_store.score.{qid[:8]}",
            capt_memory_store,
            f"hle_benchmark:score:{qid}",
            detail,
            "hle_benchmark",
        )

    accuracy = correct / scored if scored > 0 else 0

    # Store aggregate score
    capture_call(
        trace,
        "capt_memory_store.score_aggregate",
        capt_memory_store,
        "hle_benchmark:score:aggregate",
        {
            "total_questions": len(questions),
            "scored": scored,
            "correct": correct,
            "accuracy": accuracy,
            "vessel_count": len(vessel_files),
            "stage": stage,
        },
        "hle_benchmark",
    )

    # --- VECTOR SEARCH PROBE ---
    vector_probe = capture_call(
        trace,
        "capt_vector_search.probe",
        capt_vector_search,
        "hle_benchmark",
        "CAPT cognitive architecture benchmark performance HLE accuracy",
        4,
    )

    # --- RECENT MEMORY PROBE ---
    recent_probe = capture_call(
        trace,
        "capt_memory_recent.inspection",
        capt_memory_recent,
        10,
        "hle_benchmark",
    )

    # --- POST-TEST CAPTURE ---
    after_status = capture_call(trace, "capt_status.after", capt_status)
    after_metrics = capture_call(trace, "capt_metrics.after", capt_metrics)

    # --- RECALL PROBE ---
    recall_probe = capture_call(
        trace,
        "capt_memory_recall.probe",
        capt_memory_recall,
        "HLE benchmark accuracy CAPT vessel performance",
    )

    # --- BUILD REPORT ---
    report = {
        "stage": stage,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "limits": {
            "external_llm_cognition_observed": False,
            "external_llm_observed_surface": ["prompt boundary", "timing", "usage/errors"],
            "biocapt_observed_surface": [
                "module status",
                "metrics",
                "capabilities",
                "memory store/recall/recent calls",
                "vector store/search calls",
                "vessel allocation map",
                "result digests and previews",
            ],
        },
        "test_config": {
            "core_model": "xiaomi/mimo-v2.5",
            "inspection_model": "tencent/hy3-preview",
            "test_vessels": 11,
            "inspection_vessels": 455,
            "questions": len(questions),
            "questions_answered": scored,
        },
        "before_status": before_status,
        "before_metrics": before_metrics,
        "after_status": after_status,
        "after_metrics": after_metrics,
        "capabilities": capabilities,
        "vessel_map": allocations,
        "scoring": {
            "total_questions": len(questions),
            "scored": scored,
            "correct": correct,
            "accuracy": accuracy,
            "details": score_details,
        },
        "vector_search_probe": vector_probe,
        "recent_memory_probe": recent_probe,
        "recall_probe": recall_probe,
        "trace_file": str(trace),
    }

    report_path = INSPECTION_DIR / "hle_biocapt_internal_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    # --- CHRONICLE ---
    chronicle = INSPECTION_DIR / "chronicle.md"
    with chronicle.open("a", encoding="utf-8") as handle:
        handle.write("\n## bioCAPT Internal Inspection: HLE Benchmark\n\n")
        handle.write(f"- Report: `{report_path}`\n")
        handle.write(f"- Trace: `{trace}`\n")
        handle.write(f"- Active modules: {after_status.get('modules_active')}/{after_status.get('total_modules')}\n")
        handle.write(
            f"- Vessel coverage: {allocations['required_vessels']} required, "
            f"{allocations['requested_vessels']} allocated, {allocations['slack_vessels']} slack\n"
        )
        handle.write(f"- Questions: {len(questions)} total, {scored} scored, {correct} correct, {accuracy:.1%} accuracy\n")
        handle.write(
            "- Boundary truth: external model cognition is not visible; bioCAPT-local "
            "module status, memory/vector operations, and wrapper call boundaries were recorded.\n"
        )

    print(json.dumps({
        "report": str(report_path),
        "trace": str(trace),
        "modules_active": after_status.get("modules_active"),
        "accuracy": accuracy,
        "correct": correct,
        "scored": scored,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_hle_inspection())
