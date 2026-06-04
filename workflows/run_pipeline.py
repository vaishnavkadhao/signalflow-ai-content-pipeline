import argparse
import os
import sys
import json
from datetime import datetime, timezone
from connectors.manual_csv import read_trends_from_csv
from agents.validator import TopicValidatorAgent
from agents.pattern_analyzer import PatternAnalyzerAgent
from agents.prompt_generator import PromptGeneratorAgent
from agents.script_writer import ScriptWriterAgent
from agents.hook_generator import HookGeneratorAgent
from agents.calendar_planner import CalendarPlannerAgent
from agents.gemini_client import GeminiClient, get_model_name
from schemas.pipeline_schemas import PipelineRunResult

_VALID_MODES = ("free", "assist", "pro")


def _resolve_generation_mode(generation_mode: str, use_llm: bool) -> str:
    """
    Normalise the generation mode.
    --use-llm without --generation-mode defaults to 'assist' for backward compat.
    """
    mode = generation_mode.lower().strip()
    if mode not in _VALID_MODES:
        print(f"[Pipeline] Unknown generation mode '{mode}' - defaulting to 'free'")
        mode = "free"
    # Legacy flag: --use-llm alone implies assist
    if mode == "free" and use_llm:
        mode = "assist"
    return mode


def _estimate_ai_calls(mode: str, trend_count: int) -> int:
    if mode == "assist":
        return trend_count          # 1 combined call per trend
    if mode == "pro":
        return trend_count * 2      # 1 draft + 1 refinement per trend
    return 0


def run(
    input_csv: str,
    dry_run: bool = True,
    use_llm: bool = False,
    max_trends: int = 0,
    generation_mode: str = "free",
):
    generation_mode = _resolve_generation_mode(generation_mode, use_llm)

    print("=" * 60)
    print("STARTING AI CONTENT PIPELINE MULTI-AGENT EXECUTION")
    print("=" * 60)
    print(f"Input file:       {input_csv}")
    print(f"Dry-run:          {dry_run}")
    print(f"Generation mode:  {generation_mode.upper()}")
    print(f"Max trends:       {max_trends if max_trends > 0 else 'all'}")

    # ── Gemini key check ──────────────────────────────────────────────────────
    fallback_used = False
    gemini_warnings: list[str] = []

    client = GeminiClient()
    if generation_mode != "free":
        if not client.is_available():
            warning = (
                f"Generation mode is '{generation_mode}' but GEMINI_API_KEY is "
                "not set. Template fallback used for all trends."
            )
            print(f"[Pipeline] WARNING: {warning}")
            fallback_used = True
            gemini_warnings.append(warning)
        else:
            estimated = _estimate_ai_calls(generation_mode, max_trends or 999)
            print(f"[Pipeline] Gemini enabled - model: {get_model_name()}")
            print(
                f"[Pipeline] Estimated Gemini calls: "
                f"~{_estimate_ai_calls(generation_mode, max_trends or 0) or 'N x'} "
                f"(1 per trend{'+ 1 refinement' if generation_mode == 'pro' else ''})"
            )

    # 1. Ingest
    print("\n[Step 1/7] Collecting trend inputs...")
    try:
        raw_trends = read_trends_from_csv(input_csv)
        print(f"Collected {len(raw_trends)} raw trend ideas.")
    except Exception as e:
        print(f"ERROR reading trend input: {e}")
        sys.exit(1)

    # 2. Validate & score
    print("\n[Step 2/7] Validating and scoring topics...")
    validator = TopicValidatorAgent()
    validated_topics = validator.process(raw_trends)

    if max_trends and max_trends > 0:
        validated_topics = validated_topics[:max_trends]
        print(f"Capped to top {max_trends} topics by score.")

    print(f"Successfully validated {len(validated_topics)} topics (ranked by score).")
    for t in validated_topics[:3]:
        print(f"  - Topic: '{t.trend_title}' (Score: {t.final_score}/10)")

    # 3. Analyze patterns
    print("\n[Step 3/7] Analyzing content structure patterns...")
    analyzer = PatternAnalyzerAgent()
    patterns = analyzer.process(validated_topics)
    print(f"Extracted {len(patterns)} style patterns.")

    # 4. Generate prompts
    print("\n[Step 4/7] Generating prompt configurations...")
    prompt_gen = PromptGeneratorAgent()
    prompts = prompt_gen.process(patterns)
    print(f"Generated {len(prompts)} reusable AI prompts.")

    # 5. Script writing
    print(f"\n[Step 5/7] Drafting scripts ({generation_mode} mode)...")
    script_writer = ScriptWriterAgent(generation_mode=generation_mode)
    scripts = script_writer.process(prompts)

    # Use per-run counters from ScriptWriterAgent (more precise than hook-cache check)
    ai_generated = script_writer.ai_generated_count
    template_fallback = script_writer.template_fallback_count

    if generation_mode != "free" and not client.is_available():
        template_fallback = len(scripts)

    if generation_mode != "free" and client.is_available() and template_fallback > 0:
        fallback_used = True
        if ai_generated == 0:
            gemini_warnings.append(
                "Gemini unavailable - using template fallback for all scripts and hooks"
            )
        else:
            gemini_warnings.append(
                f"Gemini template fallback used for "
                f"{template_fallback}/{len(scripts)} scripts"
            )

    # Collect safe error categories (never contains raw exception text or key).
    gemini_error_categories = script_writer.gemini_error_categories

    if generation_mode != "free" and client.is_available():
        print(
            f"  AI generated: {ai_generated}  |  "
            f"Template fallback: {template_fallback}"
        )
        if gemini_error_categories:
            print(
                f"  Gemini error categories: "
                f"{', '.join(gemini_error_categories)}"
            )

    print(f"Drafted {len(scripts)} scripts with compliance guardrails.")

    # 6. Hook generation (reuses cached AI hooks from ScriptWriter)
    print("\n[Step 6/7] Creating hook options...")
    hook_gen = HookGeneratorAgent(
        generation_mode=generation_mode,
        precomputed_hooks=script_writer.ai_hooks,
    )
    hooks = hook_gen.process(scripts)
    print(f"Generated hook options (5 styles per script).")

    # 7. Calendar compilation
    print("\n[Step 7/7] Compiling content calendar...")
    planner = CalendarPlannerAgent()
    calendar_items = planner.plan_calendar(scripts, hooks)
    export_paths = planner.export(
        calendar_items,
        generation_mode=generation_mode,
        fallback_used=fallback_used,
        gemini_warnings=gemini_warnings,
        ai_generated=ai_generated,
        template_fallback=template_fallback,
        gemini_error_categories=gemini_error_categories,
    )

    run_result = PipelineRunResult(
        run_timestamp=datetime.now(timezone.utc).isoformat(),
        trends_processed=len(raw_trends),
        topics_validated=len(validated_topics),
        prompts_generated=len(prompts),
        scripts_written=len(scripts),
        calendar_items_count=len(calendar_items),
        exported_calendar_path=export_paths["csv"],
        exported_json_path=export_paths["json"],
    )

    print("\n" + "=" * 60)
    print("PIPELINE RUN COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"Generation mode:        {generation_mode.upper()}")
    if gemini_warnings:
        for w in gemini_warnings:
            print(f"WARNING: {w}")
    if gemini_error_categories:
        print(
            f"Gemini error categories: "
            f"{', '.join(gemini_error_categories)}"
        )
    print(f"Exported Calendar CSV:  {run_result.exported_calendar_path}")
    print(f"Exported Calendar JSON: {run_result.exported_json_path}")
    print(f"Run Report MD:          data/exports/run_report.md")
    print(f"Total posts scheduled:  {run_result.calendar_items_count}")
    print("=" * 60)

    return run_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SignalFlow AI - Multi-agent Content Generation Pipeline"
    )
    parser.add_argument(
        "--input", default="data/sample_trends.csv", help="Path to raw trends CSV"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Run without paid provider APIs"
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Enable LLM generation (legacy flag, equivalent to --generation-mode assist)",
    )
    parser.add_argument(
        "--generation-mode",
        default="free",
        choices=list(_VALID_MODES),
        help="Generation mode: free | assist | pro (default: free)",
    )
    parser.add_argument(
        "--max-trends",
        type=int,
        default=0,
        help="Cap the number of validated topics (0 = no cap)",
    )

    args = parser.parse_args()
    run(
        input_csv=args.input,
        dry_run=args.dry_run,
        use_llm=args.use_llm,
        max_trends=args.max_trends,
        generation_mode=args.generation_mode,
    )
