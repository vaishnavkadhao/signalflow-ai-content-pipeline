import uuid
from typing import List
from schemas.pipeline_schemas import PatternAnalysis, GeneratedPrompt

class PromptGeneratorAgent:
    def generate(self, analysis: PatternAnalysis, platform: str = "YouTube Shorts") -> GeneratedPrompt:
        """
        Creates a reusable prompt that can guide writing the video scripts.
        """
        prompt_id = f"prompt-{str(uuid.uuid4())[:8]}"
        
        # Create robust reusable prompt content
        prompt_text = f"""
        Role: Senior Creator Coach and Copywriter
        Platform Target: {platform}
        Topic Context: {analysis.topic}
        Hook Style Guidance: {analysis.hook_style}
        Content Angle Logic: {analysis.content_angle}
        Core Takeaway: {analysis.key_takeaway}
        Audience Trigger Hook: {analysis.audience_trigger}
        
        Task: Write an engaging 45-60s script. 
        Formatting guidelines:
        - Hook (0-5s): High retention trigger. No generic introductions.
        - Body (5-45s): Staccato bullet points, low filler words.
        - CTA (45-50s): Clear visual callout to leave comments.
        - Visuals: Provide side annotations with visual transition cues.
        """
        
        return GeneratedPrompt(
            prompt_id=prompt_id,
            prompt_version="1.0.0",
            topic_cluster=analysis.topic,
            intended_platform=platform,
            content_format="Short-form Video",
            prompt_text=prompt_text.strip()
        )

    def process(self, analyses: List[PatternAnalysis]) -> List[GeneratedPrompt]:
        return [self.generate(a) for a in analyses]
