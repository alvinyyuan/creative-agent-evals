"""Run the agent interactively: python -m creative_agent "a lighthouse at dawn"."""

import argparse
import json

import anyio

from .agent import DEFAULT_MODEL, DEFAULT_PROMPT, SYSTEM_PROMPTS, run_agent
from .mock import mock_api


class TerminalUser:
    def ask(self, question: str) -> str:
        return input(f"\nAgent asks: {question}\n> ")

    def review(self, job_id: str, model: str, prompt: str, note: str) -> str:
        print(f"\nDraft ready ({model}, {job_id})\nPrompt: {prompt}")
        if note:
            print(f"Note: {note}")
        return input("Approve, ask for changes, or decline:\n> ")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("idea")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--prompt", default=DEFAULT_PROMPT, choices=sorted(SYSTEM_PROMPTS))
    p.add_argument("--trace", action="store_true", help="print the tool-call trace as JSON")
    a = p.parse_args()

    async def go():
        with mock_api() as base:
            t = await run_agent(a.idea, TerminalUser(), base, model=a.model, prompt_version=a.prompt)
        print("\n" + t.final_text)
        print(f"\n[{len(t.tool_calls)} tool calls, {t.num_turns} turns, ${t.cost_usd:.4f}]")
        if t.error:
            print(f"[error] {t.error}")
        if a.trace:
            print(json.dumps(t.tool_calls, indent=2))

    anyio.run(go)


if __name__ == "__main__":
    main()
