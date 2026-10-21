# creative-agent-evals

A small generative-content agent built on the Claude Agent SDK, and the eval set I use to measure it.

The agent takes an idea, picks an image or video model, writes the generation prompt, makes a cheap draft, waits for the person to confirm, and only then spends credits on the final. Its tools come from my public [PicLumen MCP reference server](https://github.com/alvinyyuan/piclumen-mcp-server-reference), which runs against that repo's mock API.

> **A personal side build.** This is not a PicLumen product and is not connected to any PicLumen service. The mock returns placeholder media, credit prices are the mock's own, and no PicLumen data or figures appear here.

## Results

40 tasks, one run per agent version, agent on `claude-haiku-5-5`, judge on `claude-sonnet-5-5`.

| Metric | v1 prompt | v2 prompt |
|---|---|---|
| Task completion | 38/40 (95%) | 40/40 (100%) |
| Model-routing accuracy (tasks that reached a final) | 35/35 | 37/37 |
| Spend on a final before the person approved it | 1 task | 0 tasks |
| Agent LLM cost per accepted output | $0.0025 | $0.0024 |
| Generation credits per accepted output | 31.7 | 31.6 |
| LLM-as-judge prompt fidelity pass (4 or 5 out of 5) | 35/35 | 36/37 |
| Judge agrees with the keyword check | 35/35 | 36/37 |

Full tables, per category and per task: [`results/claude-haiku-5-5-v1.md`](results/claude-haiku-5-5-v1.md) and [`results/claude-haiku-5-5-v2.md`](results/claude-haiku-5-5-v2.md). Raw traces are in `results/runs/`.

The headline numbers are high because most tasks are easy on purpose. The useful output is the failure modes below, and the v2 fixes came from them. v2 was tuned on the same 40 tasks it is scored on, so its 100% is a regression check against known failures and says little about unseen ideas.

## Failure modes found

**1. Asking in chat instead of through the tool (V01, v1).** For "waves rolling onto a beach at sunset" the agent wanted to know the style and wrote the question in its reply text. Nobody can answer there, so the run ended after one turn with nothing made. Fix in v2: a hard rule that the person can only be reached through `ask_user` and `present_draft`.

**2. Treating a conditional reply as approval and spending on it (R04, v1).** After two rounds of changes the scripted person said "Closer, but the plate should be white. Then it's done." The agent read that as a yes and generated the paid final with a plate the person had not seen. It is an understandable reading of a vague reply, which is the point: when money is spent, a vague reply should get another draft. Fix in v2: the final needs an unconditional yes to the draft the person last saw. In v2, R04 went through a third draft and then the final.

**3. Over-asking on video ideas (8 to 9 tasks, both versions, still open).** The agent asks "photographic or illustrated?" on most video ideas and almost never on image ideas. The image tasks name a style ("realistic photo", "anime"), and the video tasks mostly don't, so the question is defensible and my task labels may be what's wrong. One extra question costs the person a turn. It doesn't cost credits. The fix belongs in the product: either default video to photographic and say so in the draft note, or ask about style and medium in one question. I have left it flagged rather than tune it away.

**4. The judge marked down a correct moderation rewrite (M02, rubric v1).** "An anime battle scene with gore everywhere" has to lose "gore" to pass moderation. The first judge rubric didn't know the content policy, so it scored the rewrite 3/5 for "softening the gore". Rubric v2 says toning down blocked content is correct. A judge only scores well against the rules it has been told.

**5. The keyword check missed what the judge caught (V08, v2).** "A skateboarder doing a kickflip, slow motion": the v2 prompt described a "cinematic still" with a "high-frame-rate camera" and never asked for slow motion. The keywords (`skateboard`, `kickflip`) passed. The judge scored it 3/5 and named the missing element. That's what the judge adds over string matching. In the other direction, the keyword check failed I05 because the prompt said "bicycles" and the keyword was "bike". The judge passed it, correctly. Keywords now accept alternatives (`bike|bicycle`).

**6. A harness bug that made each task cost 200 times more (setup).** The first smoke run cost $0.63 for one task, against about $0.002 now. The SDK's child process had inherited my local Claude Code setup, every MCP server and plugin, so each turn carried roughly 70k tokens of unrelated tool definitions. `strict_mcp_config=True` with empty `plugins`, `skills` and `setting_sources` fixed it. An eval that silently inherits its host's config measures the wrong thing, and pays for it.

## What drafting first costs, and when it pays

With the mock's prices (4 credits an image, 10 a video second), a draft adds 4 credits to every accepted image and saves the 16-credit final whenever the person declines. On paper, drafting first is cheaper per accepted image once more than 25% of ideas are declined after the first look. For video, where the draft is a 4-credit still and the final is 50, the break-even is a decline rate of 8%. This is arithmetic on mock prices, untested against real user behaviour. It's the trade-off I'd test first in a real product.

## How the eval works

The method is adapted from [τ-bench](https://github.com/sierra-research/tau-bench): a simulated user, and a check on the end state the agent leaves behind. I wrote a small harness instead of adopting promptfoo or deepeval so every scoring rule is readable in one file ([`evals/score.py`](evals/score.py)).

- **Tasks** ([`evals/make_tasks.py`](evals/make_tasks.py)): 40 ideas in 8 groups: photographic (8), illustrated (8), video (8), ambiguous ideas that need a question (4), revisions (4), declines (3), moderation (3), and requested settings such as 9:16 or 2 images (2). Each task states the expected model, the expected end state, the scripted replies and the elements the final prompt must keep.
- **Simulated user** ([`evals/run.py`](evals/run.py)): scripted replies, so runs are reproducible and cheap. τ-bench uses an LLM as the user. That's more realistic, and it adds noise.
- **Task completion:** a draft was presented, the final came only after an approval, it was the right medium, it honoured any requested settings, and the agent polled it to success. For decline tasks: nothing was generated after the person said no.
- **Model-routing accuracy:** the final's model matches the expected model.
- **Cost per accepted output:** total agent LLM cost across all 40 tasks, and total generation credits, divided by the number of accepted finals. LLM cost is the SDK's API-price figure.
- **LLM-as-judge** ([`evals/judge.py`](evals/judge.py)): a different model from the agent grades prompt fidelity from 1 to 5 against the request history. It reasons before scoring, and its verdicts are cached. It is checked against a deterministic keyword check, and every disagreement is listed in the results.

## Run it

Needs Node 18+, Python 3.12, [uv](https://github.com/astral-sh/uv), and a Claude login (`claude /login`) or `ANTHROPIC_API_KEY`.

```bash
git clone --recurse-submodules https://github.com/alvinyyuan/creative-agent-evals
cd creative-agent-evals
make setup
.venv/bin/python -m creative_agent "a red lighthouse on a rocky coast at dawn"   # talk to the agent
make eval                                                                       # all 40 tasks, then score with the judge
```

`make eval` costs about $0.10 of agent calls on Haiku, plus the judge calls.

## Limits

- One run per version. Agent behaviour varies between runs, and pass^k over several runs would show how much.
- 40 hand-written tasks, mostly easy. No adversarial prompts or prompt injection through tool outputs.
- The mock never fails a job, so error recovery past moderation is untested.
- The judge hasn't been calibrated against human labels. Agreement with the keyword check is only a sanity check.

## Layout

| Path | What it is |
|---|---|
| `creative_agent/agent.py` | The agent: system prompts v1 and v2, SDK options, trace capture |
| `creative_agent/__main__.py` | Interactive use at the terminal |
| `creative_agent/mock.py` | Starts the mock API on a free port |
| `evals/` | Task set, runner, scorer, judge |
| `results/` | Scored tables, raw traces, cached judge verdicts |
| `mcp/` | Git submodule: the public MCP reference server and mock API |

Built with Claude Code. MIT licence.
