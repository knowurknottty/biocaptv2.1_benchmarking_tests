#!/usr/bin/env python3
"""
HLE Vessel Swarm — fires 11 test vessels concurrently through OpenRouter.
Follows FORGE pattern: asyncio.gather + httpx.AsyncClient + semaphore.
"""

import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import httpx

HLE_ROOT = Path("/Users/knowurknot/Biocapt-ecosystem-fullcaptlang/hle-eval")
RESULTS_DIR = HLE_ROOT / "results" / "run_20260530_225648"
INSPECTION_DIR = HLE_ROOT / "results" / "inspection"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "xiaomi/mimo-v2.5"

SYSTEM_PROMPT = """You are answering questions from Humanity's Last Exam (HLE) — the hardest academic benchmark.

CRITICAL: You MUST respond with valid JSON only. No text before or after the JSON.
Your entire response must be a JSON object in a code block.

For each question, provide:
1. Step-by-step reasoning
2. Exact final answer (single letter for multipleChoice, exact string/number/formula for exactMatch)
3. Confidence score 0-100

RESPONSE FORMAT (your ENTIRE response must be exactly this structure):
```json
{"answers": [{"id": "question_id", "reasoning": "your reasoning", "answer": "your answer", "confidence": 85}]}
```

Be precise. Scoring is exact-match. Format answers to match expected format exactly.
Do NOT include any text outside the JSON code block."""


def load_env():
    """Load OpenRouter API key from environment."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        # Try reading from hermes config
        config_path = Path.home() / ".hermes" / "config.yaml"
        if config_path.exists():
            import re
            text = config_path.read_text()
            # Look for openrouter key in providers section
            match = re.search(r'OPENROUTER_API_KEY[_2]?=(["\']?)(sk-or-[^"\']+)\1', text)
            if match:
                key = match.group(2)
    return key


def load_questions():
    """Load blind questions."""
    with open(HLE_ROOT / "hle_blind_sample.json") as f:
        return json.load(f)


def load_answer_key():
    """Load answer key."""
    with open(HLE_ROOT / "hle_answer_key.json") as f:
        return json.load(f)


def split_into_vessels(questions, num_vessels=11):
    """Split questions into vessel batches, stratified by category."""
    by_cat = {}
    for q in questions:
        cat = q["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(q)

    vessels = [[] for _ in range(num_vessels)]
    idx = 0
    for cat, qs in sorted(by_cat.items()):
        for q in qs:
            vessels[idx % num_vessels].append(q)
            idx += 1
    return vessels


def vessel_prompt(vessel_id, vessel_questions):
    """Build prompt for a vessel."""
    q_text = json.dumps([
        {"id": q["id"], "question": q["question"], "answer_type": q["answer_type"], "category": q["category"]}
        for q in vessel_questions
    ], indent=2)
    return f"""You are Test Vessel {vessel_id} in the CAPT HLE evaluation cohort.
Answer {len(vessel_questions)} questions from Humanity's Last Exam.

{SYSTEM_PROMPT}

QUESTIONS:
{q_text}"""


def write_jsonl(path, event):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True, default=str) + "\n")


async def call_openrouter(client, endpoint, api_key, vessel_id, prompt, trace, max_tokens=8192):
    """Fire a single vessel through OpenRouter."""
    started = time.time()
    write_jsonl(trace, {"event": "vessel_fire", "vessel": vessel_id, "ts": started})

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }

    try:
        resp = await client.post(endpoint, json=payload, headers=headers)
        elapsed = time.time() - started

        if resp.status_code != 200:
            error = resp.text[:500]
            write_jsonl(trace, {"event": "vessel_error", "vessel": vessel_id, "status": resp.status_code, "error": error, "elapsed_s": elapsed})
            return {"vessel_id": vessel_id, "ok": False, "error": error, "elapsed_s": elapsed}

        data = resp.json()
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content", "")
        # mimo-v2.5 returns content=null, reasoning in reasoning_details
        if not content:
            reasoning_details = msg.get("reasoning_details", [])
            if reasoning_details:
                # Concatenate reasoning text as the content
                content = "\n".join(rd.get("text", "") for rd in reasoning_details if rd.get("text"))
            # Also check 'reasoning' field
            if not content and msg.get("reasoning"):
                content = msg["reasoning"]
        usage = data.get("usage", {})

        write_jsonl(trace, {
            "event": "vessel_complete",
            "vessel": vessel_id,
            "ts": time.time(),
            "elapsed_s": elapsed,
            "tokens_in": usage.get("prompt_tokens", 0),
            "tokens_out": usage.get("completion_tokens", 0),
            "content_length": len(content),
        })

        return {
            "vessel_id": vessel_id,
            "ok": True,
            "content": content,
            "usage": usage,
            "elapsed_s": elapsed,
        }
    except Exception as e:
        elapsed = time.time() - started
        write_jsonl(trace, {"event": "vessel_exception", "vessel": vessel_id, "error": str(e), "elapsed_s": elapsed})
        return {"vessel_id": vessel_id, "ok": False, "error": str(e), "elapsed_s": elapsed}


def parse_answers(content):
    """Parse vessel response to extract answers from JSON or natural language."""
    if not content:
        return []

    # Try JSON parse (direct or in code block)
    for text in [content, content]:
        import re
        match = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict) and "answers" in data:
                    return data["answers"]
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "answers" in data:
                return data["answers"]
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # Fallback: extract answers from natural language using regex patterns
    answers = []
    import re

    # Find question IDs mentioned in the content
    qid_pattern = re.compile(r'["\']?(?:id|ID)["\']?\s*[:=]\s*["\']?([a-f0-9]{24})["\']?')
    found_ids = qid_pattern.findall(content)

    # For each found ID, try to find the associated answer
    for qid in found_ids:
        # Look for answer pattern near the ID
        idx = content.find(qid)
        if idx == -1:
            continue
        nearby = content[idx:idx+2000]

        # Try to extract answer from nearby text
        answer_match = re.search(r'(?:answer|Answer|ANSWER)\s*[:=]\s*["\']?([A-Z]|[^"\'\n]{1,100})["\']?', nearby)
        confidence_match = re.search(r'(?:confidence|Confidence|CONFIDENCE)\s*[:=]\s*(\d+)', nearby)
        reasoning_match = re.search(r'(?:reasoning|Reasoning)\s*[:=]\s*["\']?(.{50,500})["\']?', nearby)

        answer = answer_match.group(1).strip().rstrip(',.') if answer_match else ""
        confidence = int(confidence_match.group(1)) if confidence_match else 50
        reasoning = reasoning_match.group(1).strip() if reasoning_match else nearby[:200]

        if answer:
            answers.append({
                "id": qid,
                "answer": answer,
                "confidence": confidence,
                "reasoning": reasoning,
            })

    # If no IDs found, try to extract sequential answers
    if not answers:
        # Look for "Answer: X" patterns
        answer_patterns = re.findall(r'(?:Answer|answer|ANSWER)\s*[:=]\s*["\']?([A-Z](?:\s*,\s*[A-Z])*|[^"\'\n]{1,50})["\']?', content)
        for i, ans in enumerate(answer_patterns):
            answers.append({
                "id": f"unknown_{i}",
                "answer": ans.strip().rstrip(',.'),
                "confidence": 50,
                "reasoning": "",
            })

    return answers


def score_answers(predictions, answer_key, questions):
    """Score predictions against answer key."""
    q_map = {q["id"]: q for q in questions}
    correct = 0
    incorrect = 0
    by_cat = {}
    details = []

    for qid, pred in predictions.items():
        expected = answer_key.get(qid, "")
        got = pred.get("answer", "")
        q = q_map.get(qid, {})
        cat = q.get("category", "unknown")

        if cat not in by_cat:
            by_cat[cat] = {"correct": 0, "total": 0}
        by_cat[cat]["total"] += 1

        got_norm = got.strip().lower().replace("$", "").replace("\\", "").replace(" ", "")
        exp_norm = expected.strip().lower().replace("$", "").replace("\\", "").replace(" ", "")
        is_correct = got_norm == exp_norm

        if is_correct:
            correct += 1
            by_cat[cat]["correct"] += 1
        else:
            incorrect += 1

        details.append({
            "id": qid, "category": cat, "expected": expected,
            "got": got, "correct": is_correct,
            "confidence": pred.get("confidence", 0),
        })

    scored = correct + incorrect
    return {
        "scored": scored, "correct": correct, "incorrect": incorrect,
        "accuracy": correct / scored if scored > 0 else 0,
        "by_category": by_cat, "details": details,
    }


async def main():
    api_key = load_env()
    if not api_key:
        print("ERROR: No OpenRouter API key found")
        sys.exit(1)

    print(f"API key: {api_key[:10]}...{api_key[-4:]}")
    print(f"Model: {MODEL}")

    questions = load_questions()
    answer_key = load_answer_key()
    vessels = split_into_vessels(questions, num_vessels=11)

    print(f"\nQuestions: {len(questions)}")
    print(f"Vessels: {len(vessels)}")
    for i, v in enumerate(vessels):
        print(f"  Vessel {i+1:2d}: {len(v)} questions")

    trace = INSPECTION_DIR / "hle_vessel_trace.jsonl"
    INSPECTION_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {
        "stage": "hle_benchmark",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_vessels": len(vessels),
        "model": MODEL,
        "questions": len(questions),
    }
    (RESULTS_DIR / "manifest_start.json").write_text(json.dumps(manifest, indent=2))
    write_jsonl(trace, {"event": "swarm_start", "ts": time.time(), "manifest": manifest})

    # FIRE ALL VESSELS CONCURRENTLY
    print(f"\nFiring {len(vessels)} vessels concurrently...")
    start_time = time.time()

    limits = httpx.Limits(max_connections=32, max_keepalive_connections=16)
    timeout = httpx.Timeout(connect=20.0, read=300.0, write=60.0, pool=30.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        tasks = []
        for i, v in enumerate(vessels):
            vessel_id = f"vessel_{i+1:02d}"
            prompt = vessel_prompt(i+1, v)
            tasks.append(call_openrouter(client, ENDPOINT, api_key, vessel_id, prompt, trace))

        results = await asyncio.gather(*tasks)

    elapsed = time.time() - start_time
    print(f"All vessels completed in {elapsed:.1f}s")

    # COLLECT RESULTS
    all_predictions = {}
    vessels_ok = 0
    for result in results:
        if not result.get("ok"):
            print(f"  {result['vessel_id']}: FAILED — {result.get('error', 'unknown')[:100]}")
            continue

        vessels_ok += 1
        vessel_id = result["vessel_id"]
        content = result["content"]
        vessel_idx = int(vessel_id.split("_")[1]) - 1

        # Save raw output
        output_file = RESULTS_DIR / f"{vessel_id}_output.json"
        output_file.write_text(json.dumps({
            "vessel_id": vessel_id,
            "content": content,
            "usage": result.get("usage", {}),
            "elapsed_s": result.get("elapsed_s", 0),
        }, indent=2))

        # Parse answers
        answers = parse_answers(content)
        for ans in answers:
            qid = ans.get("id", "")
            if qid:
                all_predictions[qid] = {
                    "answer": ans.get("answer", ""),
                    "confidence": ans.get("confidence", 0),
                    "reasoning": ans.get("reasoning", ""),
                    "vessel": vessel_id,
                }

        print(f"  {vessel_id}: {len(answers)} answers parsed ({result.get('elapsed_s', 0):.1f}s)")

    print(f"\nVessels OK: {vessels_ok}/{len(vessels)}")
    print(f"Total predictions: {len(all_predictions)}")

    # SCORE
    scores = score_answers(all_predictions, answer_key, questions)
    print(f"\n=== SCORES ===")
    print(f"Scored: {scores['scored']}/50")
    print(f"Correct: {scores['correct']}")
    print(f"Incorrect: {scores['incorrect']}")
    print(f"Accuracy: {scores['accuracy']:.1%}")
    print(f"\nBy category:")
    for cat, data in sorted(scores["by_category"].items()):
        acc = data["correct"] / data["total"] if data["total"] > 0 else 0
        print(f"  {cat}: {data['correct']}/{data['total']} ({acc:.0%})")

    # SAVE RESULTS
    complete = {
        **manifest,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_s": elapsed,
        "vessels_ok": vessels_ok,
        "predictions": len(all_predictions),
        "scoring": {
            "scored": scores["scored"],
            "correct": scores["correct"],
            "accuracy": scores["accuracy"],
            "by_category": scores["by_category"],
        },
        "trace_file": str(trace),
    }
    (RESULTS_DIR / "manifest_complete.json").write_text(json.dumps(complete, indent=2, ensure_ascii=False, default=str))
    (RESULTS_DIR / "scoring_results.json").write_text(json.dumps(scores, indent=2, ensure_ascii=False, default=str))

    write_jsonl(trace, {"event": "swarm_complete", "ts": time.time(), "elapsed_s": elapsed, "accuracy": scores["accuracy"]})

    print(f"\nResults saved to {RESULTS_DIR}")
    print(json.dumps({"vessels_ok": vessels_ok, "accuracy": scores["accuracy"], "correct": scores["correct"]}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
