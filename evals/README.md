# Deadlock RAG Evals

This directory contains the offline evaluation set for Deadlock RAG.

## Files

- `golden_set.jsonl` - draft control questions and expected answers.

## Case Format

Each line is one JSON object:

```json
{"id":"strategy_abrams_001","type":"strategy","question":"Which items help Abrams survive longer in close fights?","reference_answer":"The answer should mention defensive or sustain items and explain why Abrams benefits from durability in melee-range engagements.","tags":["items","strategy","retrieval_required"],"needs_review":true}
```

Required fields:

- `id`: stable unique identifier.
- `type`: one of `lore`, `mechanics`, `strategy`, `numeric`.
- `question`: user-facing question.
- `reference_answer`: expected answer or grading note.
- `tags`: list of labels such as `tool_required`, `retrieval_required`, `hero_stats`.
- `needs_review`: `true` when the reference answer is a draft and needs manual review.

Numeric cases must also provide `expected_value` with `tolerance`, or `expected_label`.

## Offline Commands

These commands do not call the live RAG pipeline:

```bash
python scripts/run_eval.py --validate
python scripts/run_eval.py --stats
python scripts/run_eval.py --list
```

Live RAG execution and RAGAS scoring will be added after the offline schema is stable.
