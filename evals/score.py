"""Score saved traces and write results/<label>.md.

    python -m evals.score --label claude-haiku-5-5            # deterministic metrics
    python -m evals.score --label claude-haiku-5-5 --judge    # plus the LLM-as-judge check
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN_TOOLS = {"piclumen_generate_image": "image", "piclumen_generate_video": "video"}
JOB_RE = re.compile(r"job_[0-9a-f-]{36}")


def credits(kind: str, inp: dict) -> int:
    """Same pricing rule as the mock API: 4 per image, 10 per video second."""
    return 10 * int(inp.get("duration_seconds", 5)) if kind == "video" else 4 * int(inp.get("count", 1))


def analyse(rec: dict) -> dict:
    task, trace, log = rec["task"], rec["trace"], rec["user_log"]
    calls = trace["tool_calls"]
    reviews = [e for e in log if e["event"] == "review"]

    gens, review_at, approved_at = [], [], None
    for i, c in enumerate(calls):
        if c["tool"] in GEN_TOOLS:
            res = c["result"] or ""
            m = JOB_RE.search(res)
            rejected = c["is_error"] or "moderation" in res.lower() or not m
            gens.append({"i": i, "kind": GEN_TOOLS[c["tool"]], "input": c["input"],
                         "job_id": m.group(0) if m else None, "rejected": rejected})
        elif c["tool"] == "present_draft":
            k = len(review_at)
            review_at.append(i)
            if approved_at is None and k < len(reviews) and reviews[k]["approve"]:
                approved_at = i

    ok_gens = [g for g in gens if not g["rejected"]]
    before = [g for g in ok_gens if approved_at is None or g["i"] < approved_at]
    finals = [g for g in ok_gens if approved_at is not None and g["i"] > approved_at]
    premature = [g for g in before if g["kind"] == "video" or int(g["input"].get("count", 1)) > 1]
    asked = any(c["tool"] == "ask_user" for c in calls)

    rejected_prompts = [g["input"].get("prompt", "") for g in gens if g["rejected"]]
    retried_same = len(rejected_prompts) != len(set(rejected_prompts))

    a = {"id": task["id"], "category": task["category"], "expected_outcome": task["expected_outcome"],
         "error": trace["error"], "cost_usd": trace["cost_usd"], "turns": trace["num_turns"],
         "credits": sum(credits(g["kind"], g["input"]) for g in ok_gens),
         "drafts": len(review_at), "asked": asked, "premature_spend": bool(premature),
         "retried_rejected_prompt": retried_same, "final_model": None, "final_prompt": None,
         "routing_ok": None, "constraints_ok": None, "polled_final": None, "failure_modes": []}
    fm = a["failure_modes"]

    if task["expected_outcome"] == "final":
        final = next((g for g in reversed(finals) if g["kind"] == task["expected_kind"]), None)
        if final:
            inp = final["input"]
            a["final_model"] = inp.get("model") or ("piclumen-video-v1" if final["kind"] == "video" else "piclumen-v1")
            a["final_prompt"] = inp.get("prompt", "")
            a["routing_ok"] = a["final_model"] == task["expected_model"]
            a["constraints_ok"] = all(str(inp.get(k, "")) == str(v) for k, v in task["constraints"].items())
            a["polled_final"] = any(
                c["tool"] == "piclumen_get_job_status" and c["input"].get("job_id") == final["job_id"]
                and "succeeded" in (c["result"] or "") for c in calls)
        a["completed"] = bool(final and approved_at is not None and a["constraints_ok"]
                              and a["polled_final"] and not premature)
        if not calls:
            pass  # reported below as "asked in plain text and stopped"
        elif approved_at is None:
            fm.append("never reached an approved draft")
        elif not final:
            wrong_kind = [g for g in finals if g["kind"] != task["expected_kind"]]
            fm.append("final was the wrong medium" if wrong_kind else "no final after approval")
        if final and not a["routing_ok"]:
            fm.append(f"routed to {a['final_model']}")
        if final and not a["constraints_ok"]:
            fm.append("ignored a requested setting")
        if final and not a["polled_final"]:
            fm.append("did not confirm the final finished")
    else:
        last_review = review_at[-1] if review_at else None
        after = [g for g in ok_gens if last_review is not None and g["i"] > last_review]
        a["completed"] = bool(review_at) and not after and not premature
        if after:
            fm.append("generated after the person declined")
        if not review_at:
            fm.append("never presented a draft")

    if premature:
        fm.append("spent on a final-tier job before approval")
    if retried_same:
        fm.append("retried a prompt moderation had rejected")
    if task["category"] == "ambiguous" and not asked:
        fm.append("guessed instead of asking")
    if task["category"] not in ("ambiguous",) and asked:
        fm.append("asked an unnecessary question")
    if task["category"] == "video" and before and before[0]["kind"] == "video":
        fm.append("drafted a video instead of a still")
    if task["category"] == "revision" and a["final_prompt"] is not None:
        if len(review_at) < len(task["reviews"]):
            fm.append("finalised before every requested change was drafted")
    if not calls and "?" in trace["final_text"]:
        fm.append("asked in plain text and stopped")
    if a["error"]:
        fm.append("run error: " + a["error"][:60])

    p = (a["final_prompt"] or "").lower()
    a["keyword_ok"] = (None if a["final_prompt"] is None else
                       all(any(alt in p for alt in k.split("|")) for k in task["must_include"]) and not any(k in p for k in task["must_not_include"]))
    return a


def pct(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "n/a"


def render(label: str, rows: list[dict], judged: dict | None) -> str:
    n = len(rows)
    done = [r for r in rows if r["completed"]]
    accepted = [r for r in done if r["expected_outcome"] == "final"]
    routed = [r for r in rows if r["routing_ok"] is not None]
    total_usd = sum(r["cost_usd"] for r in rows)
    total_cr = sum(r["credits"] for r in rows)
    L = [f"# Results: {label}", "",
         "| Metric | Value |", "|---|---|",
         f"| Task completion | {pct(len(done), n)} |",
         f"| Model-routing accuracy (tasks that reached a final) | {pct(sum(r['routing_ok'] for r in routed), len(routed))} |",
         f"| Accepted outputs | {len(accepted)} of {sum(r['expected_outcome'] == 'final' for r in rows)} expected |",
         f"| Agent LLM cost per accepted output | ${total_usd / max(len(accepted), 1):.4f} |",
         f"| Generation credits per accepted output | {total_cr / max(len(accepted), 1):.1f} |",
         f"| Total agent LLM cost, all {n} tasks | ${total_usd:.3f} |",
         f"| Median turns per task | {statistics.median(r['turns'] for r in rows)} |",
         f"| Premature spend (final-tier job before approval) | {sum(r['premature_spend'] for r in rows)} |"]
    if judged:
        js = [judged[r["id"]] for r in rows if r["id"] in judged]
        both = [(judged[r["id"]]["pass"], r["keyword_ok"]) for r in rows if r["id"] in judged]
        agree = sum(a == b for a, b in both)
        L += [f"| LLM-as-judge prompt fidelity pass (score 4 or 5) | {pct(sum(j['pass'] for j in js), len(js))} |",
              f"| Judge agrees with the keyword check | {pct(agree, len(both))} |"]
    L += ["", "## By category", "", "| Category | Tasks | Completed | Routing | Credits per task |", "|---|---|---|---|---|"]
    by = defaultdict(list)
    for r in rows:
        by[r["category"]].append(r)
    for cat, rs in by.items():
        rr = [r for r in rs if r["routing_ok"] is not None]
        L.append(f"| {cat} | {len(rs)} | {pct(sum(r['completed'] for r in rs), len(rs))} | "
                 f"{pct(sum(r['routing_ok'] for r in rr), len(rr))} | {sum(r['credits'] for r in rs) / len(rs):.0f} |")
    L += ["", "## Failure modes", "", "| Failure mode | Tasks |", "|---|---|"]
    c = Counter(m.split(":")[0] if m.startswith("run error") else re.sub(r"routed to .*", "routed to the wrong model", m)
                for r in rows for m in r["failure_modes"])
    for mode, k in c.most_common():
        ids = ", ".join(r["id"] for r in rows if any(
            (m.startswith("run error") and mode == "run error") or m == mode
            or (mode == "routed to the wrong model" and m.startswith("routed to")) for m in r["failure_modes"]))
        L.append(f"| {mode} | {k} ({ids}) |")
    if judged:
        L += ["", "## Judge and keyword check disagreements", ""]
        for r in rows:
            j = judged.get(r["id"])
            if j and j["pass"] != r["keyword_ok"]:
                L.append(f"- **{r['id']}** judge {j['score']}/5, keywords {'pass' if r['keyword_ok'] else 'fail'}: {j['reason']}")
    L += ["", "## Per task", "", "| Task | Done | Model | Drafts | Credits | LLM $ | Notes |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        js = f" judge {judged[r['id']]['score']}/5;" if judged and r["id"] in judged else ""
        L.append(f"| {r['id']} | {'yes' if r['completed'] else 'no'} | {r['final_model'] or '-'} | {r['drafts']} | "
                 f"{r['credits']} | {r['cost_usd']:.4f} |{js} {'; '.join(r['failure_modes'])} |")
    return "\n".join(L) + "\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--label", required=True)
    p.add_argument("--judge", action="store_true")
    p.add_argument("--judge-model", default="claude-sonnet-5-5")
    a = p.parse_args()
    run_dir = ROOT / "results" / "runs" / a.label
    recs = [json.loads(f.read_text()) for f in sorted(run_dir.glob("*.json"))]
    rows = [analyse(r) for r in recs]
    judged = None
    if a.judge:
        from evals.judge import judge_all
        judged = judge_all(recs, rows, a.judge_model, run_dir.parent.parent / "judge" / f"{a.label}.json")
    (ROOT / "results" / f"{a.label}.json").write_text(json.dumps(rows, indent=2))
    md = render(a.label, rows, judged)
    (ROOT / "results" / f"{a.label}.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
