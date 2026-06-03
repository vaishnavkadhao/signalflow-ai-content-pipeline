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
from schemas.pipeline_schemas import PipelineRunResult

def run(input_csv: str, dry_run: bool = True, use_llm: bool = False, max_trends: int = 0):
    print("=" * 60)
    print("STARTING AI CONTENT PIPELINE MULTI-AGENT EXECUTION")
    print("=" * 60)
    print(f"Input file: {input_csv}")
    print(f"Dry-run: {dry_run} | Use LLM: {use_llm} | Max trends: {max_trends if max_trends > 0 else 'all'}")
    
    # 1. Ingest Data via Trend Collector Connector
    print("\n[Step 1/7] Collecting trend inputs...")
    try:
        raw_trends = read_trends_from_csv(input_csv)
        print(f"Collected {len(raw_trends)} raw trend ideas.")
    except Exception as e:
        print(f"ERROR reading trend input: {e}")
        sys.exit(1)
        
    # 2. Score and Validate Topics
    print("\n[Step 2/7] Validating and scoring topics...")
    validator = TopicValidatorAgent()
    validated_topics = validator.process(raw_trends)

    # Apply max_trends cap AFTER scoring so we always use the highest-ranked topics
    if max_trends and max_trends > 0:
        validated_topics = validated_topics[:max_trends]
        print(f"Capped to top {max_trends} topics by score.")

    print(f"Successfully validated {len(validated_topics)} topics (ranked by score).")
    for t in validated_topics[:3]:
        print(f"  - Topic: '{t.trend_title}' (Score: {t.final_score}/10)")

    # 3. Analyze High-Performing Patterns
    print("\n[Step 3/7] Analyzing content structure patterns...")
    analyzer = PatternAnalyzerAgent()
    patterns = analyzer.process(validated_topics)
    print(f"Extracted {len(patterns)} style patterns.")
    
    # 4. Generate Reusable Creative Prompts
    print("\n[Step 4/7] Generating prompt configurations...")
    prompt_gen = PromptGeneratorAgent()
    prompts = prompt_gen.process(patterns)
    print(f"Generated {len(prompts)} reusable AI prompts.")
    
    # 5. Script Writing with Guardrails
    print("\n[Step 5/7] Drafting scripts...")
    script_writer = ScriptWriterAgent()
    scripts = script_writer.process(prompts)
    print(f"Drafted {len(scripts)} scripts with compliance guardrails.")
    
    # 6. Hook Selection Variations
    print("\n[Step 6/7] Creating hook options...")
    hook_gen = HookGeneratorAgent()
    hooks = hook_gen.process(scripts)
    print(f"Generated hook options (5 styles per script).")
    
    # 7. Calendar Compilation and Output Exports
    print("\n[Step 7/7] Compiling content calendar...")
    planner = CalendarPlannerAgent()
    calendar_items = planner.plan_calendar(scripts, hooks)
    export_paths = planner.export(calendar_items)
    
    # Construct structured run result via contract schema
    run_result = PipelineRunResult(
        run_timestamp=datetime.now(timezone.utc).isoformat(),
        trends_processed=len(raw_trends),
        topics_validated=len(validated_topics),
        prompts_generated=len(prompts),
        scripts_written=len(scripts),
        calendar_items_count=len(calendar_items),
        exported_calendar_path=export_paths["csv"],
        exported_json_path=export_paths["json"]
    )
    
    print("\n" + "=" * 60)
    print("PIPELINE PIPELINE RUN TERMINATED SUCCESSFULLY")
    print("=" * 60)
    print(f"Exported Calendar CSV: {run_result.exported_calendar_path}")
    print(f"Exported Calendar JSON: {run_result.exported_json_path}")
    print(f"Run Report MD:         data/exports/run_report.md")
    print(f"Totals Scheduled:       {run_result.calendar_items_count} posts")
    print("=" * 60)
    
    return run_result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SignalFlow AI — Multi-agent Content Generation Pipeline")
    parser.add_argument("--input", default="data/sample_trends.csv", help="Path to raw trends CSV")
    parser.add_argument("--dry-run", action="store_true", help="Run without paid provider APIs")
    parser.add_argument("--use-llm", action="store_true", help="Enable LLM generation context")
    parser.add_argument(
        "--max-trends",
        type=int,
        default=0,
        help="Cap the number of validated topics to process (0 = no cap, use all)",
    )

    args = parser.parse_args()
    run(
        input_csv=args.input,
        dry_run=args.dry_run,
        use_llm=args.use_llm,
        max_trends=args.max_trends,
    )
