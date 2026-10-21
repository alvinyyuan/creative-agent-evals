"""A small generative-content agent on the Claude Agent SDK.

Loop: idea -> pick an image or video model -> write the prompt -> cheap draft ->
user confirms -> paid final. Generation tools come from the public PicLumen MCP
reference server (run against its mock API). The two user-facing tools
(`ask_user`, `present_draft`) are in-process SDK tools, so the same agent can be
driven by a person at the terminal or by a scripted user in the eval.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_sdk_mcp_server,
    query,
    tool,
)

from .mock import MCP_ENTRY

DEFAULT_MODEL = os.environ.get("AGENT_MODEL", "claude-haiku-5-5")

SYSTEM_PROMPT_V1 = """\
You are a creative assistant. You turn a person's idea into a finished image or
video using the PicLumen generation tools. Credits cost the person money, so you
draft cheaply and only spend on the final once they approve it.

Workflow:
1. Read the idea. If the medium (still image or video) or the visual style
   (photographic or illustrated) is unclear, ask one short question with
   ask_user. If it is clear, do not ask.
2. Call piclumen_list_models and choose the model whose description fits the
   idea best.
3. Write a detailed generation prompt: subject, setting, composition, lighting,
   style. Keep every element the person asked for.
4. Draft: generate ONE image (count 1). For a video idea, draft a single still
   keyframe with an image model; never generate a video before approval.
5. Poll piclumen_get_job_status until the draft succeeds, then call
   present_draft with the job id, model and prompt.
6. If the person asks for changes, revise the prompt and draft again. If they
   decline, stop: do not generate anything else.
7. Once they approve, generate the final with the approved prompt and the
   chosen model, honouring any aspect ratio, image count or video length they
   asked for (default: 4 images, or a 5 second video). Poll until it succeeds,
   then reply with a two-line summary and the asset URLs.

If a generation is rejected by content moderation, rewrite the prompt to drop
the flagged content while keeping the idea, and say what you changed when you
present the draft. Never retry the same rejected prompt.
"""

# v2: two fixes from the first eval run (see README, "Failure modes").
SYSTEM_PROMPT_V2 = SYSTEM_PROMPT_V1 + """
Two hard rules:
- You can only reach the person through ask_user and present_draft. Never ask
  a question in your reply text: the person cannot answer it there.
- Spending on the final needs a plain approval of the draft they last saw. If
  their reply asks for any change, even "change X, then it's done", draft
  again and present it. Only generate the final on an unconditional yes.
"""

SYSTEM_PROMPTS = {"v1": SYSTEM_PROMPT_V1, "v2": SYSTEM_PROMPT_V2}
DEFAULT_PROMPT = os.environ.get("AGENT_PROMPT", "v2")


class User(Protocol):
    def ask(self, question: str) -> str: ...
    def review(self, job_id: str, model: str, prompt: str, note: str) -> str: ...


@dataclass
class Trace:
    idea: str
    model: str
    tool_calls: list[dict] = field(default_factory=list)  # in stream order
    final_text: str = ""
    cost_usd: float = 0.0
    num_turns: int = 0
    usage: dict = field(default_factory=dict)
    error: str | None = None


def _user_tools(user: User):
    @tool("ask_user", "Ask the person one short clarifying question.", {"question": str})
    async def ask_user(args):
        return {"content": [{"type": "text", "text": user.ask(args["question"])}]}

    @tool(
        "present_draft",
        "Show the person a finished draft and get their decision: approve, "
        "request changes, or decline. Call only after the draft job has succeeded.",
        {"job_id": str, "model": str, "prompt": str, "note": str},
    )
    async def present_draft(args):
        reply = user.review(args["job_id"], args["model"], args["prompt"], args.get("note", ""))
        return {"content": [{"type": "text", "text": reply}]}

    return create_sdk_mcp_server("user", tools=[ask_user, present_draft])


def _short(name: str) -> str:
    return name.split("__")[-1]


async def run_agent(idea: str, user: User, api_base: str, model: str = DEFAULT_MODEL,
                    prompt_version: str = DEFAULT_PROMPT, max_turns: int = 40) -> Trace:
    options = ClaudeAgentOptions(
        model=model,
        system_prompt=SYSTEM_PROMPTS[prompt_version],
        max_turns=max_turns,
        tools=[],  # no built-in Claude Code tools: only the MCP tools below
        setting_sources=[],  # ignore any local CLAUDE.md, hooks or settings
        strict_mcp_config=True,  # only the two MCP servers below, none from the user config
        plugins=[],
        skills=[],
        permission_mode="bypassPermissions",
        mcp_servers={
            "piclumen": {
                "type": "stdio",
                "command": "node",
                "args": [str(MCP_ENTRY)],
                "env": {"PICLUMEN_API_BASE_URL": api_base, "PICLUMEN_API_KEY": "pl_test"},
            },
            "user": _user_tools(user),
        },
        cli_path=os.environ.get("CLAUDE_CLI_PATH") or None,
    )
    trace = Trace(idea=idea, model=model)
    by_id: dict[str, dict] = {}
    try:
        async for msg in query(prompt=idea, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        call = {"tool": _short(block.name), "input": block.input, "result": None,
                                "is_error": False}
                        by_id[block.id] = call
                        trace.tool_calls.append(call)
                    elif isinstance(block, TextBlock):
                        trace.final_text = block.text
            elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, ToolResultBlock) and block.tool_use_id in by_id:
                        content = block.content
                        if isinstance(content, list):
                            content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
                        by_id[block.tool_use_id]["result"] = content
                        by_id[block.tool_use_id]["is_error"] = bool(block.is_error)
            elif isinstance(msg, ResultMessage):
                trace.cost_usd = msg.total_cost_usd or 0.0
                trace.num_turns = msg.num_turns
                u = msg.usage or {}
                trace.usage = {k: u[k] for k in ("input_tokens", "cache_creation_input_tokens",
                                                 "cache_read_input_tokens", "output_tokens") if k in u}
                if msg.is_error:
                    trace.error = str(msg.result)
    except Exception as exc:  # keep the partial trace; the scorer counts it as a failure
        trace.error = f"{type(exc).__name__}: {exc}"
    return trace
