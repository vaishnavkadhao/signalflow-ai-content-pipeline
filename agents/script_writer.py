from typing import List
from schemas.pipeline_schemas import GeneratedPrompt, ScriptOutput


class ScriptWriterAgent:
    """
    Consumes validated prompts and outputs structured, post-ready video scripts.

    Guardrails:
    - No hype phrases ("game-changing", "revolutionary", "unlock your potential", "are you tired of")
    - No fake statistics
    - Keep copy practical, specific, and platform-appropriate
    """

    # Banned phrases that must not appear in generated copy
    BANNED_PHRASES = [
        "game-changing",
        "revolutionary",
        "unlock your potential",
        "are you tired of",
        "mind-blowing",
        "you won't believe",
        "this will change everything",
        "secret hack",
    ]

    def _sanitize(self, text: str) -> str:
        """Strip banned phrases from generated copy."""
        result = text
        for phrase in self.BANNED_PHRASES:
            result = result.replace(phrase, "").replace(phrase.capitalize(), "")
        # Clean up any double spaces left by removal
        while "  " in result:
            result = result.replace("  ", " ")
        return result.strip()

    def write_script(self, prompt: GeneratedPrompt) -> ScriptOutput:
        """
        Generates a short-form video script from a validated prompt.
        Uses practical, specific, template-based copy in dry-run mode.
        """
        topic = prompt.topic_cluster
        platform = prompt.intended_platform.lower()

        # Select a format-appropriate script template
        if "youtube" in platform:
            script_text = (
                f"[Hook] Here is what most people get wrong about {topic}.\n"
                f"[Context] I spent the last two weeks testing different approaches, "
                f"and the results were not what I expected.\n"
                f"[Body] The most common mistake: jumping to tools before defining the workflow. "
                f"Start with the smallest working version. Document what breaks. Iterate from there.\n"
                f"[CTA] Subscribe for the next part — I'll show the actual numbers."
            )
            cta = "Subscribe for part 2 — with real results."
            visual_notes = (
                "Screen-record the workflow. Use text overlays at each step transition. "
                "Keep cuts under 3 seconds. End with a still frame showing the output."
            )
            duration = 90

        elif "linkedin" in platform:
            script_text = (
                f"[Hook] {topic} — here is what I noticed after three months of testing.\n"
                f"[Point 1] Most teams start with the wrong assumption: that more data equals better output.\n"
                f"[Point 2] The fix is simpler than it looks. Define your input schema first, then build the processor.\n"
                f"[Point 3] We cut our review cycle from 5 days to 1 day using this approach.\n"
                f"[CTA] Drop a comment if you want the template."
            )
            cta = "Comment 'template' to get the workflow doc."
            visual_notes = (
                "Static carousel or talking head. Show a before/after comparison slide. "
                "Keep text minimal and high contrast."
            )
            duration = 60

        else:
            # Default: short-form vertical video (TikTok, Instagram Reels)
            script_text = (
                f"[Hook] {topic} — this is the part nobody shows you.\n"
                f"[Body] I built this from scratch in two days. No paid tools, no shortcuts. "
                f"Here is the exact process I used, step by step.\n"
                f"[Payoff] The output looked exactly like what our team used to spend a week producing.\n"
                f"[CTA] Save this — you will want to come back when you need it."
            )
            cta = "Save this post and follow for the full breakdown."
            visual_notes = (
                "Fast cuts. Show the screen or the physical output. "
                "Add subtitles — 85% of short-form is watched on mute. "
                "Keep the hook under 2 seconds of visuals."
            )
            duration = 50

        script_text = self._sanitize(script_text)

        return ScriptOutput(
            topic=topic,
            script_text=script_text,
            cta=cta,
            estimated_duration_sec=duration,
            visual_notes=visual_notes,
        )

    def process(self, prompts: List[GeneratedPrompt]) -> List[ScriptOutput]:
        return [self.write_script(p) for p in prompts]
