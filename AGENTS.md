# AGENTS.md

## Project purpose
This repo is an MVP for an AI content-agent pipeline that turns trend inputs into validated topics, reusable generation prompts, scripts, hooks, and a content calendar.

Core flow:
CSV trend input → Topic Validator → Pattern Analyzer → Prompt Generator → Script Writer → Hook Generator → Calendar Planner → exports.

## Important directories
- `agents/`: individual pipeline agents. Keep each agent small, testable, and deterministic where possible.
- `connectors/`: data ingestion connectors. Start with `manual_csv.py`; add platform APIs later.
- `schemas/`: Pydantic models and data contracts. Prefer adding/strengthening schemas before changing agent logic.
- `workflows/`: orchestration entry points. `workflows/run_pipeline.py` is the main CLI pipeline.
- `prompts/`: prompt templates. Version prompt files when behavior changes.
- `creator_memory/`: tone rules, content pillars, banned phrases, and creator-specific context.
- `data/sample_trends.csv`: safe sample input for local testing.
- `docs/`: architecture, build stages, and error playbooks.
- `tests/`: unit tests.

## How to run locally
Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Run the dry-run pipeline:

```bash
python -m workflows.run_pipeline --input data/sample_trends.csv --dry-run
```

Run tests:

```bash
pytest
```

## Environment and secrets
- Never commit `.env` or real API keys.
- Use `.env.example` for placeholder environment variables only.
- Keep private exports and raw client data out of Git unless explicitly approved.
- Do not log secrets, access tokens, private client data, or PII.

## Engineering rules
- Keep the project working in dry-run mode without any paid API key.
- Prefer deterministic Python logic for scoring, validation, CSV parsing, deduplication, and calendar formatting.
- Use LLM calls only where generation or judgment is genuinely needed.
- Validate all agent outputs with Pydantic schemas before passing them to the next step.
- Avoid platform-policy-risky scraping. Use APIs, approved exports, RSS, Google Trends, or manual CSV input first.
- Add or update tests whenever changing agent behavior.
- Keep prompts in `prompts/`, not hardcoded inside Python files unless there is a strong reason.
- Preserve `Asia/Kolkata` as the default timezone unless the user changes it.

## Review guidelines
When reviewing code changes, prioritize:
- pipeline breakage or invalid data flow between agents;
- missing schema validation;
- unsafe secret handling;
- brittle parsing of AI output;
- untested agent behavior;
- accidental commits of generated exports, cache files, or `__pycache__`;
- platform-policy-risky scraping patterns.

## Done means
A change is complete only when:
- the dry-run pipeline completes successfully;
- relevant tests pass with `pytest`;
- generated outputs are understandable and saved in `data/exports/` when expected;
- README or docs are updated if commands, architecture, or behavior changed.

# Claude Code Instructions

You are working on a private MVP for a multi-agent content pipeline.

Main goal:
Build a reliable local pipeline before adding platform APIs.

Core workflow:
1. Read trend data from CSV.
2. Validate and score topics.
3. Analyze patterns from high-performing content.
4. Generate reusable prompts.
5. Generate script, hooks, caption, hashtags, CTA, and B-roll ideas.
6. Export a content calendar.

Rules:
- Keep prompts inside `/prompts`.
- Keep schemas inside `/schemas`.
- Do not hardcode API keys.
- Do not scrape platforms directly in MVP.
- Prefer official APIs and manual CSV imports.
- Always validate agent outputs with Pydantic schemas.
- Save generated outputs in `/data/exports`.
- Add tests when modifying scoring, schemas, or workflow logic.

Immediate improvement ideas:
- Add Google Sheets export.
- Add Notion/Airtable review board.
- Add analytics feedback input.
- Add dashboard UI.
