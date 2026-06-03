from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class TrendInput(BaseModel):
    trend_title: str = Field(..., description="The name of the trending topic")
    views: int = Field(default=0, description="Number of views on the source trend")
    likes: int = Field(default=0, description="Number of likes on the source trend")
    comments: int = Field(default=0, description="Number of comments on the source trend")
    shares: int = Field(default=0, description="Number of shares on the source trend")
    platform: str = Field(default="Unknown", description="Platform where the trend was spotted")
    url: Optional[str] = Field(default="", description="URL to the original post")

class ValidatedTopic(BaseModel):
    trend_title: str
    views: int
    likes: int
    comments: int
    shares: int
    platform: str
    url: str
    trend_score: float = Field(..., ge=0, le=10, description="Value/popularity score")
    engagement_score: float = Field(..., ge=0, le=10, description="Engagement rate score")
    creator_fit_score: float = Field(..., ge=0, le=10, description="How well this fits the creator memory")
    final_score: float = Field(..., ge=0, le=10, description="Combined prioritized score")
    explanation: str = Field(..., description="Details on why this topic was selected and prioritized")

class PatternAnalysis(BaseModel):
    topic: str
    hook_style: str = Field(..., description="e.g. curiosity listicle, direct callout")
    content_angle: str = Field(..., description="Angle/narrative perspective")
    key_takeaway: str = Field(..., description="Core lesson or value")
    audience_trigger: str = Field(..., description="Why the target audience will watch")

class GeneratedPrompt(BaseModel):
    prompt_id: str
    prompt_version: str = Field(default="1.0.0")
    topic_cluster: str
    intended_platform: str
    content_format: str
    prompt_text: str = Field(..., description="The generated generative prompt for an LLM scriptwriter")

class HookOption(BaseModel):
    category: str = Field(..., description="e.g., curiosity, pain point, tutorial")
    text: str = Field(..., description="The actual hook hook text")

class ScriptOutput(BaseModel):
    topic: str
    script_text: str = Field(..., description="Full spoken script")
    cta: str = Field(..., description="Call to action")
    estimated_duration_sec: int = Field(..., description="Duration in seconds")
    visual_notes: str = Field(..., description="B-roll and visual annotations")

class HookOutput(BaseModel):
    topic: str
    hooks: List[HookOption]

class CalendarItem(BaseModel):
    date: str
    local_time: str
    timezone: str = "Asia/Kolkata"
    platform: str
    content_pillar: str
    topic: str
    format: str
    hook: str
    script_status: str
    caption_status: str
    cta: str
    priority: str
    repurpose_plan: str
    human_review_status: str = "Pending"

class PipelineRunResult(BaseModel):
    run_timestamp: str
    trends_processed: int
    topics_validated: int
    prompts_generated: int
    scripts_written: int
    calendar_items_count: int
    exported_calendar_path: str
    exported_json_path: str
