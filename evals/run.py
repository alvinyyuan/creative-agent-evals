"""Run the agent on every task with a scripted user and save one trace per task.

    python -m evals.run                      # all 40 tasks
    python -m evals.run --only P01,R04 -j 2  # a subset
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

import anyio

from creative_agent.agent import DEFAULT_MODEL, DEFAULT_PROMPT, SYSTEM_PROMPTS, run_agent
from creative_agent.mock import mock_api

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "evals" / "tasks.jsonl"


class ScriptedUser:
    """Deterministic stand-in for the person (the tau-bench idea, without an LLM user)."""

    def __init__(self, task: dict):
        self.task = task
        self.reviews = list(task["reviews"])
        self.log: list[dict] = []

    def ask(self, question: str) -> str:
        reply = self.task["clarify_reply"] or "No preference, you decide."
        self.log.append({"event": "ask", "question": question, "reply": reply})
        return reply

    def review(self, job_id: str, model: str, prompt: str, note: str) -> str:
        r = self.reviews.pop(0) if self.reviews else {"reply": "No more feedback.", "approve": False}
        self.log.append({"event": "review", "job_id": job_id, "model": model, "prompt": prompt,
                         "note": note, "reply": r["reply"], "approve": r["approve"]})
        return r["reply"]


def load_tasks(only: str | None = None) -> list[dict]:
    tasks = [json.loads(line) for line in TASKS.read_text().splitlines() if line.strip()]
    if only:
        keep = set(only.split(","))
        tasks = [t for t in tasks if t["id"] in keep]
    return tasks


async def main_async(args) -> None:
    tasks = load_tasks(args.only)
    out = ROOT / "results" / "runs" / args.label
    out.mkdir(parents=True, exist_ok=True)
    limiter = anyio.CapacityLimiter(args.jobs)

    with mock_api() as base:
        async def one(task):
            async with limiter:
                user = ScriptedUser(task)
                t0 = time.time()
                trace = await run_agent(task["idea"], user, base, model=args.model, prompt_version=args.prompt)
                record = {"task": task, "trace": asdict(trace), "user_log": user.log,
                          "seconds": round(time.time() - t0, 1)}
                (out / f"{task['id']}.json").write_text(json.dumps(record, indent=2))
                flag = "ERR" if trace.error else "ok"
                print(f"{task['id']:4} {flag:3} {len(trace.tool_calls):2} calls  ${trace.cost_usd:.4f}",
                      flush=True)

        async with anyio.create_task_group() as tg:
            for task in tasks:
                tg.start_soon(one, task)
    print(f"traces in {out}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--prompt", default=DEFAULT_PROMPT, choices=sorted(SYSTEM_PROMPTS))
    p.add_argument("--label", default=None, help="results/runs/<label> (default: <model>-<prompt>)")
    p.add_argument("--only", default=None)
    p.add_argument("-j", "--jobs", type=int, default=4)
    a = p.parse_args()
    a.label = a.label or f"{a.model}-{a.prompt}"
    anyio.run(main_async, a)


if __name__ == "__main__":
    main()
