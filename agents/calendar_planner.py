import json
import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict
from schemas.pipeline_schemas import ScriptOutput, HookOutput, CalendarItem

class CalendarPlannerAgent:
    def __init__(self, start_date: str = None):
        self.start_date_str = start_date or "2026-06-02"
        self.pillars = ["AI Automation", "Marketing Systems", "Build in Public", "Case Studies", "Tool Tutorials"]
        self.platforms = ["YouTube Shorts", "Instagram Reels", "LinkedIn Post", "X Thread"]

    def plan_calendar(self, scripts: List[ScriptOutput], hooks: List[HookOutput]) -> List[CalendarItem]:
        """
        Plans a sequential, timezone-aware content schedule.
        """
        calendar_items = []
        base_date = datetime.strptime(self.start_date_str, "%Y-%m-%d")
        
        hooks_map = {h.topic: h.hooks for h in hooks}
        
        for i, script in enumerate(scripts):
            current_date_obj = base_date + timedelta(days=i)
            date_str = current_date_obj.strftime("%Y-%m-%d")
            
            # Select platform, pillar and hooks sequentially
            platform = self.platforms[i % len(self.platforms)]
            pillar = self.pillars[i % len(self.pillars)]
            
            # Retrieve primary curiosity hook
            topic_hooks = hooks_map.get(script.topic, [])
            primary_hook = topic_hooks[0].text if topic_hooks else "Unlock the system."
            
            item = CalendarItem(
                date=date_str,
                local_time="10:00 AM",
                timezone="Asia/Kolkata",
                platform=platform,
                content_pillar=pillar,
                topic=script.topic,
                format="Short-form Video" if "Shorts" in platform or "Reels" in platform else "Text/Image Post",
                hook=primary_hook,
                script_status="Draft",
                caption_status="Pending",
                cta=script.cta,
                priority="High" if i % 2 == 0 else "Medium",
                repurpose_plan=f"Repurpose {platform} to other networks within 48 hours.",
                human_review_status="Needs Review"
            )
            calendar_items.append(item)
            
        return calendar_items

    def export(self, items: List[CalendarItem], export_dir: str = "data/exports") -> Dict[str, str]:
        """
        Exports content calendar items into CSV, JSON, and Markdown files.
        """
        os.makedirs(export_dir, exist_ok=True)
        
        csv_path = os.path.join(export_dir, "content_calendar.csv")
        json_path = os.path.join(export_dir, "content_calendar.json")
        md_path = os.path.join(export_dir, "run_report.md")
        
        # 1. Export JSON
        dict_items = [item.dict() for item in items]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dict_items, f, indent=2)
            
        # 2. Export CSV
        if items:
            headers = list(dict_items[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(dict_items)
                
        # 3. Export Markdown Report
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Content Pipeline Run Report\n\n")
            f.write(f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")
            f.write("## Content Calendar Overview\n\n")
            f.write("| Date | Platform | Pillar | Topic | Status |\n")
            f.write("|---|---|---|---|---|\n")
            for item in items:
                f.write(f"| {item.date} | {item.platform} | {item.content_pillar} | {item.topic} | {item.human_review_status} |\n")
                
        return {
            "csv": csv_path,
            "json": json_path,
            "markdown": md_path
        }
