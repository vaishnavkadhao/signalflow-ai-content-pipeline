import math
from typing import List, Dict
from schemas.pipeline_schemas import TrendInput, ValidatedTopic

class TopicValidatorAgent:
    def __init__(self, creator_pillars: List[str] = None):
        self.creator_pillars = creator_pillars or ["AI Automation", "Marketing Systems", "Build in Public"]

    def calculate_engagement_score(self, trend: TrendInput) -> float:
        """
        Calculates engagement rate score from 0 to 10 based on views to likes/comments ratio.
        """
        if trend.views == 0:
            return 0.0
        
        # Calculate a proxy for engagement
        total_interactions = trend.likes + trend.comments * 2 + trend.shares * 1.5
        ratio = total_interactions / trend.views
        
        # Normalize with logarithmic scale so rare viral posts get higher scores cleanly
        # Expecting around 1% to 10% interactions
        score = (math.log1p(ratio * 100) / math.log1p(10.0)) * 10.0
        return min(max(round(score, 2), 0.0), 10.0)

    def calculate_trend_score(self, trend: TrendInput) -> float:
        """
        Calculates high-performance trend scale score from 0 to 10 based on view volume.
        """
        if trend.views == 0:
            return 0.0
        # Views log scale (10k is low, 1M is high)
        score = (math.log10(trend.views) / 7.0) * 10.0  # Normalized to 10M views as max (log10(10M)=7)
        return min(max(round(score, 2), 0.0), 10.0)

    def calculate_creator_fit(self, trend: TrendInput) -> float:
        """
        Calculates how closely a topic fits content pillars (0 to 10).
        """
        title_lower = trend.trend_title.lower()
        score = 3.0  # Base line fit
        
        # Keyword matching for content pillars
        matches = 0
        if "ai" in title_lower or "llm" in title_lower or "chatbot" in title_lower or "claude" in title_lower:
            matches += 1
            score += 3.0
        if "code" in title_lower or "coding" in title_lower or "build" in title_lower or "pipeline" in title_lower:
            matches += 1
            score += 2.0
        if "marketing" in title_lower or "content" in title_lower or "automation" in title_lower:
            matches += 1
            score += 2.0
            
        return min(score, 10.0)

    def process(self, raw_trends: List[Dict]) -> List[ValidatedTopic]:
        """
        Deduplicates, validates, scores and reports top validated topics.
        """
        validated_topics = []
        seen_titles = set()
        
        for item in raw_trends:
            # Pydantic validation
            trend = TrendInput(**item)
            
            # Simple deduplication
            title_clean = trend.trend_title.strip().lower()
            if title_clean in seen_titles:
                continue
            seen_titles.add(title_clean)
            
            # Calculate metrics
            trend_score = self.calculate_trend_score(trend)
            engagement_score = self.calculate_engagement_score(trend)
            creator_fit = self.calculate_creator_fit(trend)
            
            # Weighted final score compilation
            final_score = round((trend_score * 0.4) + (engagement_score * 0.3) + (creator_fit * 0.3), 2)
            
            # Detailed explanation logic
            explanation = f"Topic prioritized with final score {final_score}/10. "
            explanation += f"View volume indicator of {trend_score}/10 is backed by robust "
            explanation += f"engagement metric ({engagement_score}/10) and matches creator alignment ({creator_fit}/10)."
            
            validated_topic = ValidatedTopic(
                trend_title=trend.trend_title,
                views=trend.views,
                likes=trend.likes,
                comments=trend.comments,
                shares=trend.shares,
                platform=trend.platform,
                url=trend.url or "",
                trend_score=trend_score,
                engagement_score=engagement_score,
                creator_fit_score=creator_fit,
                final_score=final_score,
                explanation=explanation
            )
            validated_topics.append(validated_topic)
            
        # Rank by final score
        validated_topics.sort(key=lambda t: t.final_score, reverse=True)
        return validated_topics
