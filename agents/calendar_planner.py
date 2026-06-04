import json
import csv
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from schemas.pipeline_schemas import ScriptOutput, HookOutput, CalendarItem


class CalendarPlannerAgent:
    def __init__(self, start_date: str = None):
        self.start_date_str = start_date or "2026-06-02"
        self.pillars = [
            "AI Automation",
            "Marketing Systems",
            "Build in Public",
            "Case Studies",
            "Tool Tutorials",
        ]
        self.platforms = [
            "YouTube Shorts",
            "Instagram Reels",
            "LinkedIn Post",
            "X Thread",
        ]

    def plan_calendar(
        self, scripts: List[ScriptOutput], hooks: List[HookOutput]
    ) -> List[CalendarItem]:
        calendar_items = []
        base_date = datetime.strptime(self.start_date_str, "%Y-%m-%d")
        hooks_map = {h.topic: h.hooks for h in hooks}

        for i, script in enumerate(scripts):
            current_date_obj = base_date + timedelta(days=i)
            date_str = current_date_obj.strftime("%Y-%m-%d")

            platform = self.platforms[i % len(self.platforms)]
            pillar = self.pillars[i % len(self.pillars)]

            topic_hooks = hooks_map.get(script.topic, [])
            primary_hook = topic_hooks[0].text if topic_hooks else "Unlock the system."

            item = CalendarItem(
                date=date_str,
                local_time="10:00 AM",
                timezone="Asia/Kolkata",
                platform=platform,
                content_pillar=pillar,
                topic=script.topic,
                format=(
                    "Short-form Video"
                    if "Shorts" in platform or "Reels" in platform
                    else "Text/Image Post"
                ),
                hook=primary_hook,
                script_status="Draft",
                caption_status="Pending",
                cta=script.cta,
                priority="High" if i % 2 == 0 else "Medium",
                repurpose_plan=(
                    f"Repurpose {platform} to other networks within 48 hours."
                ),
                human_review_status="Needs Review",
            )
            calendar_items.append(item)

        return calendar_items

    def export(
        self,
        items: List[CalendarItem],
        export_dir: str = "data/exports",
        generation_mode: str = "free",
        fallback_used: bool = False,
        gemini_warnings: List[str] = None,
        ai_generated: int = 0,
        template_fallback: int = 0,
        gemini_error_categories: List[str] = None,
    ) -> Dict[str, str]:
        os.makedirs(export_dir, exist_ok=True)

        csv_path = os.path.join(export_dir, "content_calendar.csv")
        json_path = os.path.join(export_dir, "content_calendar.json")
        md_path = os.path.join(export_dir, "run_report.md")

        # Use model_dump() (Pydantic v2); dict() is deprecated in v2
        dict_items = [item.model_dump() for item in items]

        # 1. JSON export
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dict_items, f, indent=2)

        # 2. CSV export
        if items:
            headers = list(dict_items[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(dict_items)

        # 3. Markdown report
        warnings = gemini_warnings or []
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Content Pipeline Run Report\n\n")
            f.write(
                f"Generated on: "
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
            )
            f.write("## Run Metadata\n\n")
            f.write(f"| Field | Value |\n|---|---|\n")
            f.write(f"| Generation Mode | {generation_mode.upper()} |\n")
            f.write(f"| Total Posts Scheduled | {len(items)} |\n")
            if generation_mode != "free":
                f.write(f"| AI Generated Scripts | {ai_generated} |\n")
                f.write(f"| Template Fallback Scripts | {template_fallback} |\n")
            f.write(
                f"| Gemini Fallback Used | {'Yes' if fallback_used else 'No'} |\n"
            )
            if generation_mode != "free" and gemini_error_categories:
                cats = ", ".join(gemini_error_categories)
                f.write(f"| Gemini Error Category | {cats} |\n")
            if warnings:
                f.write("\n## Warnings\n\n")
                for w in warnings:
                    f.write(f"- {w}\n")

            f.write("\n## Content Calendar Overview\n\n")
            f.write("| Date | Platform | Pillar | Topic | Status |\n")
            f.write("|---|---|---|---|---|\n")
            for item in items:
                f.write(
                    f"| {item.date} | {item.platform} | "
                    f"{item.content_pillar} | {item.topic} | "
                    f"{item.human_review_status} |\n"
                )

        return {"csv": csv_path, "json": json_path, "markdown": md_path}
