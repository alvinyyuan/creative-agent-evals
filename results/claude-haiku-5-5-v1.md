# Results: claude-haiku-5-5-v1

| Metric | Value |
|---|---|
| Task completion | 38/40 (95%) |
| Model-routing accuracy (tasks that reached a final) | 35/35 (100%) |
| Accepted outputs | 35 of 37 expected |
| Agent LLM cost per accepted output | $0.0025 |
| Generation credits per accepted output | 31.7 |
| Total agent LLM cost, all 40 tasks | $0.086 |
| Median turns per task | 7.0 |
| Premature spend (final-tier job before approval) | 1 |
| LLM-as-judge prompt fidelity pass (score 4 or 5) | 35/35 (100%) |
| Judge agrees with the keyword check | 35/35 (100%) |

## By category

| Category | Tasks | Completed | Routing | Credits per task |
|---|---|---|---|---|
| ambiguous | 4 | 4/4 (100%) | 4/4 (100%) | 28 |
| constraints | 2 | 2/2 (100%) | 2/2 (100%) | 48 |
| decline | 3 | 3/3 (100%) | n/a | 4 |
| illustration | 8 | 8/8 (100%) | 8/8 (100%) | 20 |
| moderation | 3 | 3/3 (100%) | 3/3 (100%) | 20 |
| photo | 8 | 8/8 (100%) | 8/8 (100%) | 20 |
| revision | 4 | 3/4 (75%) | 3/3 (100%) | 32 |
| video | 8 | 7/8 (88%) | 7/7 (100%) | 47 |

## Failure modes

| Failure mode | Tasks |
|---|---|
| asked an unnecessary question | 9 (C02, D03, R03, V02, V03, V05, V06, V07, V08) |
| never reached an approved draft | 1 (R04) |
| spent on a final-tier job before approval | 1 (R04) |
| asked in plain text and stopped | 1 (V01) |

## Judge and keyword check disagreements


## Per task

| Task | Done | Model | Drafts | Credits | LLM $ | Notes |
|---|---|---|---|---|---|---|
| A01 | yes | piclumen-anime-v1 | 1 | 20 | 0.0021 | judge 4/5;  |
| A02 | yes | piclumen-v1 | 1 | 20 | 0.0020 | judge 5/5;  |
| A03 | yes | piclumen-video-v1 | 1 | 54 | 0.0027 | judge 5/5;  |
| A04 | yes | piclumen-v1 | 1 | 20 | 0.0020 | judge 5/5;  |
| C01 | yes | piclumen-v1 | 1 | 12 | 0.0019 | judge 5/5;  |
| C02 | yes | piclumen-video-v1 | 1 | 84 | 0.0024 | judge 5/5; asked an unnecessary question |
| D01 | yes | - | 1 | 4 | 0.0014 |  |
| D02 | yes | - | 1 | 4 | 0.0013 |  |
| D03 | yes | - | 1 | 4 | 0.0015 | asked an unnecessary question |
| I01 | yes | piclumen-anime-v1 | 1 | 20 | 0.0020 | judge 5/5;  |
| I02 | yes | piclumen-anime-v1 | 1 | 20 | 0.0020 | judge 5/5;  |
| I03 | yes | piclumen-anime-v1 | 1 | 20 | 0.0021 | judge 5/5;  |
| I04 | yes | piclumen-anime-v1 | 1 | 20 | 0.0020 | judge 5/5;  |
| I05 | yes | piclumen-anime-v1 | 1 | 20 | 0.0022 | judge 5/5;  |
| I06 | yes | piclumen-anime-v1 | 1 | 20 | 0.0019 | judge 5/5;  |
| I07 | yes | piclumen-anime-v1 | 1 | 20 | 0.0019 | judge 5/5;  |
| I08 | yes | piclumen-anime-v1 | 1 | 20 | 0.0020 | judge 5/5;  |
| M01 | yes | piclumen-v1 | 1 | 20 | 0.0029 | judge 5/5;  |
| M02 | yes | piclumen-anime-v1 | 1 | 20 | 0.0026 | judge 5/5;  |
| M03 | yes | piclumen-v1 | 1 | 20 | 0.0021 | judge 5/5;  |
| P01 | yes | piclumen-v1 | 1 | 20 | 0.0018 | judge 5/5;  |
| P02 | yes | piclumen-v1 | 1 | 20 | 0.0019 | judge 5/5;  |
| P03 | yes | piclumen-v1 | 1 | 20 | 0.0020 | judge 5/5;  |
| P04 | yes | piclumen-v1 | 1 | 20 | 0.0018 | judge 5/5;  |
| P05 | yes | piclumen-v1 | 1 | 20 | 0.0020 | judge 5/5;  |
| P06 | yes | piclumen-v1 | 1 | 20 | 0.0019 | judge 5/5;  |
| P07 | yes | piclumen-v1 | 1 | 20 | 0.0022 | judge 5/5;  |
| P08 | yes | piclumen-v1 | 1 | 20 | 0.0020 | judge 5/5;  |
| R01 | yes | piclumen-v1 | 2 | 24 | 0.0032 | judge 5/5;  |
| R02 | yes | piclumen-anime-v1 | 2 | 24 | 0.0032 | judge 5/5;  |
| R03 | yes | piclumen-video-v1 | 2 | 58 | 0.0034 | judge 5/5; asked an unnecessary question |
| R04 | no | - | 2 | 24 | 0.0029 | never reached an approved draft; spent on a final-tier job before approval |
| V01 | no | - | 0 | 0 | 0.0001 | asked in plain text and stopped |
| V02 | yes | piclumen-video-v1 | 1 | 54 | 0.0021 | judge 5/5; asked an unnecessary question |
| V03 | yes | piclumen-video-v1 | 1 | 54 | 0.0023 | judge 4/5; asked an unnecessary question |
| V04 | yes | piclumen-video-v1 | 1 | 54 | 0.0024 | judge 4/5;  |
| V05 | yes | piclumen-video-v1 | 1 | 54 | 0.0024 | judge 5/5; asked an unnecessary question |
| V06 | yes | piclumen-video-v1 | 1 | 54 | 0.0022 | judge 5/5; asked an unnecessary question |
| V07 | yes | piclumen-video-v1 | 1 | 54 | 0.0025 | judge 4/5; asked an unnecessary question |
| V08 | yes | piclumen-video-v1 | 1 | 54 | 0.0024 | judge 5/5; asked an unnecessary question |
