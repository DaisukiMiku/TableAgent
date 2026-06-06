# xlsx Skill Selection Matrix

> Last run: 2026-05-29 11:42 +0800

## Purpose

Compare TableClaw spreadsheet QA behavior with builtin `xlsx` skill enabled vs disabled.

This evaluation tracks four things:

- Whether the model actually reads `nanobot/nanobot/skills/xlsx/SKILL.md`.
- At which tool step the skill is read.
- Whether the final answer matches the task gold answer.
- Token usage for skill-on and skill-off runs.

## Setup

- Runner: `./eval.sh`
- Dataset: `eval_test/test_dataset/tasks.jsonl`
- Table: `eval_test/test_dataset/tables/市州数据-营业收现率台账.xlsx`
- Skill-on config: `nanobot/configs/tableclaw-bailian-dashscope.json`
- Skill-off config: `nanobot/configs/tableclaw-bailian-dashscope-no-xlsx-skill.json`
- Full raw report: `docs/实验评测/skill-matrix/latest-eval-summary.md`
- Machine-readable result: `eval_test/results/skill_matrix/latest_eval.json`

The current `xlsx` skill is the builtin copy under `nanobot/nanobot/skills/xlsx/SKILL.md`. The old workspace skill override has been removed.

## Aggregate Result

| Mode | Runs | Auto pass | Manual check | Skill reads | Total tokens | Avg tokens | Prompt | Completion | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| skill-on | 10 | 8/10 | 10/10 | 3/10 | 730,590 | 73,059 | 712,692 | 17,898 | 569,856 |
| skill-off | 10 | 7/10 | 10/10 | 0/10 | 712,548 | 71,254 | 693,463 | 19,085 | 446,976 |

Notes:

- `Auto pass` uses the current strict scorer. Several false cases are rounding-only misses because the model answered values like `0.3954` while gold tolerance is `1e-6`.
- `Manual check` reviews answer previews for factual correctness: unit names, counts, rankings, and approximate numeric values.
- Skill-on used about `+18,042` total tokens across 10 tasks (`+2.5%`) compared with skill-off.

## Difficulty Breakdown

| Difficulty | Mode | Runs | Auto pass | Manual check | Skill reads | Total tokens | Avg tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| simple | skill-on | 3 | 3/3 | 3/3 | 1/3 | 230,365 | 76,788 |
| simple | skill-off | 3 | 3/3 | 3/3 | 0/3 | 239,725 | 79,908 |
| medium | skill-on | 4 | 2/4 | 4/4 | 1/4 | 282,509 | 70,627 |
| medium | skill-off | 4 | 2/4 | 4/4 | 0/4 | 249,823 | 62,455 |
| hard | skill-on | 3 | 3/3 | 3/3 | 1/3 | 217,716 | 72,572 |
| hard | skill-off | 3 | 2/3 | 3/3 | 0/3 | 223,000 | 74,333 |

## Task Matrix

| Task | Difficulty | Skill-on result | Skill-on skill | Skill-on tokens | Skill-off result | Skill-off skill | Skill-off tokens | Delta |
| --- | --- | --- | --- | ---: | --- | --- | ---: | ---: |
| tc_simple_001 | simple | pass | step 3 | 83,053 | pass | no | 66,646 | +16,407 |
| tc_simple_002 | simple | pass | no | 75,377 | pass | no | 59,029 | +16,348 |
| tc_simple_003 | simple | pass | no | 71,935 | pass | no | 114,050 | -42,115 |
| tc_medium_001 | medium | pass | no | 79,658 | rounded* | no | 65,935 | +13,723 |
| tc_medium_002 | medium | rounded* | step 3 | 75,445 | pass | no | 43,608 | +31,837 |
| tc_medium_003 | medium | pass | no | 70,945 | pass | no | 69,786 | +1,159 |
| tc_medium_004 | medium | rounded* | no | 56,461 | rounded* | no | 70,494 | -14,033 |
| tc_hard_001 | hard | pass | no | 72,176 | pass | no | 65,555 | +6,621 |
| tc_hard_002 | hard | pass | no | 62,756 | pass | no | 78,556 | -15,800 |
| tc_hard_003 | hard | pass | step 3 | 82,784 | rounded* | no | 78,889 | +3,895 |

`rounded*` means the answer is semantically correct but failed the strict numeric scorer because it reported rounded values rather than full-precision floats.

## Observations

- Enabling a skill does not mean the model will always read it. In this run, skill-on selected the builtin `xlsx` skill in `3/10` tasks.
- When selected, the skill was read at step 3 in all three cases. The model first inspected the table or a tool result, then decided to read the skill.
- Skill-off never read the builtin skill, confirming that `disabledSkills = ["xlsx"]` works for the ablation.
- Both modes solved the current 10-table task set after manual review. The difference is mainly path quality, token shape, and whether the skill document is consulted.
- The current builtin skill is still the large Codex spreadsheet skill, so skill selection can add prompt overhead. It helped some hard/simple runs consume fewer tokens, but medium tasks show overhead.

## Case Study: tc_hard_003

Task:

- Calculate the 202602 average, max, and min of `营业收现率完成` across 21 city/state units.
- Exclude `市州合计`.
- Gold answer:
  - Average: `0.8958562052739871`
  - Max: `达州`, `1.08669577950616`
  - Min: `阿坝`, `0.395424633160755`

| Mode | Skill read | Tool steps | Auto pass | Manual check | Total tokens | Prompt | Completion | Cached | Elapsed ms |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| skill-on | step 3 | 6 | pass | pass | 82,784 | 80,798 | 1,986 | 65,152 | 65,569 |
| skill-off | no | 5 | rounded* | pass | 78,889 | 77,263 | 1,626 | 43,136 | 46,485 |

Path difference:

- `skill-on` first read the table, then a tool-result preview, then read `nanobot/nanobot/skills/xlsx/SKILL.md` at step 3.
- After reading the skill, it inspected rows, extracted the 21 unit values, and ran a final calculation over an explicit `(unit, value)` list.
- `skill-off` also inspected rows and computed with openpyxl, but did not consult the skill document.

Answer difference:

| Metric | Gold | skill-on output | skill-off output |
| --- | ---: | ---: | ---: |
| Average | 0.8958562052739871 | 0.895856 | 0.8959 |
| Max | 1.08669577950616 | 1.086696 达州 | 1.0867 达州 |
| Min | 0.395424633160755 | 0.395425 阿坝 | 0.3954 阿坝 |

Interpretation:

- Both modes are semantically correct.
- `skill-on` is stricter and more explanatory: it reports six decimals, includes a small interpretation, and mentions `市州合计` context.
- `skill-off` is faster and slightly cheaper, but rounds to four decimals, which fails the current `1e-6` numeric scorer.
- This is not yet strong evidence that the current skill improves reasoning quality; it mainly shows that skill availability can change answer precision and reporting style.
- The token overhead is visible: `skill-on` costs `+3,895` tokens (`+4.9%`) on this task because it reads the large generic spreadsheet skill.

## Current Interpretation

This run supports the current architecture decision:

- Keep `xlsx` as a builtin nanobot skill, not a workspace override.
- Keep skill/no-skill ablation in `eval_test` because the framework can clearly show when skill routing changes the model path.
- Next skill work should focus on a lighter TableClaw-specific spreadsheet QA skill, because the current full Codex spreadsheet skill is broader than needed for read-only table analysis.

## Reproduce

```bash
./eval.sh
./eval.sh --list-tasks
./eval.sh --difficulty hard
./eval.sh --modes skill-on skill-off --task-id tc_hard_003
```
