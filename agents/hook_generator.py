from typing import List
from schemas.pipeline_schemas import ScriptOutput, HookOutput, HookOption

class HookGeneratorAgent:
    def generate_hooks(self, script: ScriptOutput) -> HookOutput:
        """
        Creates 5 hooks for the video, categorized properly for A/B testing.
        """
        topic = script.topic
        
        hooks = [
            HookOption(
                category="Curiosity",
                text=f"The hidden algorithm behind {topic} was finally exposed."
            ),
            HookOption(
                category="Pain Point",
                text=f"Tired of manual workflows? Here is how {topic} saves 10 hours a week."
            ),
            HookOption(
                category="Bold Claim",
                text=f"Traditional pipelines are dead. Welcome to the era of {topic}."
            ),
            HookOption(
                category="Tutorial",
                text=f"How to build your first {topic} system in under 5 minutes."
            ),
            HookOption(
                category="Mistake/Myth",
                text=f"The biggest lie you believe about {topic} limits your growth."
            )
        ]
        
        return HookOutput(
            topic=topic,
            hooks=hooks
        )

    def process(self, scripts: List[ScriptOutput]) -> List[HookOutput]:
        return [self.generate_hooks(s) for s in scripts]
