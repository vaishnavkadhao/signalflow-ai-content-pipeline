from typing import List
from schemas.pipeline_schemas import ValidatedTopic, PatternAnalysis

class PatternAnalyzerAgent:
    def analyze(self, topic: ValidatedTopic) -> PatternAnalysis:
        """
        Studies structural elements of high-performing subjects.
        Returns deterministic structured pattern analysis for the pipeline.
        """
        title_lower = topic.trend_title.lower()
        
        # Determine Hook Style
        if "vibe" in title_lower or "coding" in title_lower:
            hook_style = "Contrarian hook: 'We entered the vibe coding era, and normal SWE is dead.'"
            content_angle = "Case study: Analyzing the shift from syntax typing to visual design logic."
            audience_trigger = "FOMO and career adaptation in AI times."
            key_takeaway = "SaaS developers need product management skills more than raw syntax mastery."
        elif "hackathon" in title_lower or "agent" in title_lower:
            hook_style = "Action/Curiosity hook: 'I spent 48 hours at an AI Hackathon and saw the future.'"
            content_angle = "Event showcase & project breakdowns."
            audience_trigger = "Excitement about builder capabilities."
            key_takeaway = "Multi-agent frameworks can construct full SaaS MVPs over a single weekend."
        elif "building" in title_lower or "cursor" in title_lower:
            hook_style = "Tools tutorial hook: 'Stop using traditional IDEs. Here is how Cursor builds in public.'"
            content_angle = "Step-by-step visual demonstration."
            audience_trigger = "Productivity hacking desires."
            key_takeaway = "Live building in public creates high digital trust and organic users."
        else:
            hook_style = "Insight hook: 'The hidden algorithm behind this content trend was leaked.'"
            content_angle = "Strategy walk-through."
            audience_trigger = "Desire for high competitive advantage."
            key_takeaway = "Deterministic pipelines backed structured validation win content loops."

        return PatternAnalysis(
            topic=topic.trend_title,
            hook_style=hook_style,
            content_angle=content_angle,
            key_takeaway=key_takeaway,
            audience_trigger=audience_trigger
        )

    def process(self, validated_topics: List[ValidatedTopic]) -> List[PatternAnalysis]:
        return [self.analyze(topic) for topic in validated_topics]
