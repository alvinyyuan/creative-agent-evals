"""LLM-as-judge: does the final generation prompt faithfully carry what the person asked for?

The judge is a different model from the agent, sees only the request history and
the final prompt (not the agent's reasoning), reasons before it scores, and
returns JSON. Its verdicts are cached so re-scoring costs nothing. We check it
against a cheap deterministic keyword check and list every disagreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import anyio
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

RUBRIC_VERSION = "v2"  # v1 lacked the content-policy sentence and marked down a correct rewrite
RUBRIC = """\
You are grading one output of an image and video generation assistant.

The person's request history:
{history}

The assistant chose model "{model}" and sent this final generation prompt:
<prompt>
{prompt}
</prompt>

Grade only prompt fidelity: does the prompt contain every element the person
asked for (including every requested change), contradict nothing they said, and
add nothing that changes their intent? Style detail the assistant added is fine
if it fits the request. The platform's content policy blocks graphic gore and
sexual content, so toning those down to pass moderation is correct and must
not lower the score.

Score 1 to 5:
5 every element present, nothing contradicted
4 a minor detail softened or missing, intent intact
3 a requested element or change missing
2 several elements missing or one contradicted
1 a different image or video from the one requested

First think in two or three sentences, then output only this JSON on the last line:
{{"score": <1-5>, "missing": [<strings>], "reason": "<one sentence>"}}
"""


def history(rec: dict) -> str:
    lines = [f"- Idea: {rec['task']['idea']}"]
    for e in rec["user_log"]:
        if e["event"] == "ask":
            lines.append(f"- Asked \"{e['question']}\", the person answered: {e['reply']}")
        elif e["event"] == "review" and not e["approve"]:
            lines.append(f"- On a draft, the person said: {e['reply']}")
    return "\n".join(lines)


async def _judge_one(rec: dict, row: dict, model: str) -> dict:
    prompt = RUBRIC.format(history=history(rec), model=row["final_model"], prompt=row["final_prompt"])
    text = ""
    opts = ClaudeAgentOptions(model=model, max_turns=1, tools=[], setting_sources=[],
                              strict_mcp_config=True, plugins=[], skills=[])
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, ResultMessage):
            text = msg.result or ""
    last = next((ln for ln in reversed(text.strip().splitlines()) if ln.strip().startswith("{")), "{}")
    try:
        v = json.loads(last)
    except json.JSONDecodeError:
        v = {"score": 0, "missing": [], "reason": "judge output did not parse"}
    v["pass"] = int(v.get("score", 0)) >= 4
    return v


def judge_all(recs: list[dict], rows: list[dict], model: str, cache_path: Path) -> dict:
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    todo = [(rec, row) for rec, row in zip(recs, rows)
            if row["final_prompt"] and (cache.get(row["id"], {}).get("prompt"), cache.get(row["id"], {}).get("rubric"))
            != (row["final_prompt"], RUBRIC_VERSION)]

    async def go():
        lim = anyio.CapacityLimiter(4)

        async def one(rec, row):
            async with lim:
                v = await _judge_one(rec, row, model)
                cache[row["id"]] = {**v, "prompt": row["final_prompt"], "judge_model": model, "rubric": RUBRIC_VERSION}

        async with anyio.create_task_group() as tg:
            for rec, row in todo:
                tg.start_soon(one, rec, row)

    if todo:
        anyio.run(go)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2))
    ids = {r["id"] for r in rows if r["final_prompt"]}
    return {k: v for k, v in cache.items() if k in ids}
