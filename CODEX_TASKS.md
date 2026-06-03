# Codex Task List

Use these tasks one at a time in Codex. Do not ask Codex to do all of them in one run.

## Task 1: Clean the repo for a first GitHub commit
Goal: Prepare this Python MVP for a clean private GitHub repository.
Context: This repo currently contains sample code for a content-agent pipeline.
Constraints:
- Do not remove sample input data.
- Do not commit secrets.
- Keep dry-run mode working.
Done when:
- `__pycache__` folders are removed.
- generated exports are either ignored or moved to safe sample outputs if needed.
- `.gitignore` covers `.env`, virtualenvs, caches, logs, and private data.
- `pytest` passes.

## Task 2: Strengthen schemas and output validation
Goal: Ensure every agent output has a Pydantic schema and validation step.
Context: Agent output should not be passed raw to the next stage.
Constraints:
- Keep dry-run mode working.
- Preserve existing CLI arguments.
Done when:
- validator, pattern analyzer, prompt generator, script writer, hook generator, and calendar planner outputs are schema-validated.
- invalid records are logged and skipped safely.
- tests cover at least one valid and one invalid input case.

## Task 3: Add structured LLM adapter
Goal: Improve the optional LLM path so Gemini output is parsed safely.
Context: The system should remain provider-flexible later.
Constraints:
- Do not hardcode API keys.
- Keep a no-key dry-run path.
- Return structured objects, not raw text, where possible.
Done when:
- `llm/` exposes a clean provider interface.
- Gemini calls are isolated behind that interface.
- failures fall back gracefully or produce clear errors.

## Task 4: Add content calendar controls
Goal: Make calendar generation more useful for real posting.
Context: The calendar should respect content pillars, platform, status, local timezone, and repurposing plan.
Constraints:
- Default timezone is Asia/Kolkata.
- Avoid auto-posting.
Done when:
- calendar CSV includes date, local_time, timezone, platform, pillar, topic, hook, status, CTA, and repurpose fields.
- statuses include Draft, Needs Review, Approved, Scheduled, Posted, Rejected.
- docs explain how to use the calendar manually.

## Task 5: Add analytics feedback loop MVP
Goal: Let users import post performance data and learn which prompts/hooks worked.
Context: We want the system to generate better prompts from high-performing content.
Constraints:
- Start with manual CSV import only.
- Do not connect social APIs yet.
Done when:
- a sample analytics CSV exists.
- analytics import maps post performance to prompt_id, hook_pattern, topic_cluster, and content_pillar.
- a report identifies top hooks, topics, and prompt patterns.
