from typing import List, Dict, Optional
from schemas.pipeline_schemas import GeneratedPrompt, ScriptOutput, HookOption
from agents.gemini_client import GeminiClient


# ---------------------------------------------------------------------------
# Structured output schema
# Passed to GeminiClient.generate_json() as response_json_schema so Gemini is
# forced to emit valid JSON rather than markdown-fenced text that must be parsed.
# ---------------------------------------------------------------------------

_ASSIST_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "script_text": {
            "type": "string",
            "description": (
                "Full spoken script with clearly labelled [Hook], [Body], and [CTA] "
                "sections. Should take 45-60 seconds when read aloud."
            ),
        },
        "cta": {
            "type": "string",
            "description": "One clear, specific call to action.",
        },
        "visual_notes": {
            "type": "string",
            "description": "B-roll and visual direction notes for the video editor.",
        },
        "hooks": {
            "type": "array",
            "description": "Exactly 5 hook variations for A/B testing.",
            "minItems": 5,
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": (
                            "Hook category: Curiosity, Pain Point, Bold Claim, "
                            "Tutorial, or Mistake/Myth"
                        ),
                    },
                    "text": {
                        "type": "string",
                        "description": "The hook line itself.",
                    },
                },
                "required": ["category", "text"],
            },
        },
    },
    "required": ["script_text", "cta", "visual_notes", "hooks"],
}


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _assist_prompt(prompt: GeneratedPrompt) -> str:
    return f"""You are a professional content creator and copywriter.

Topic: {prompt.topic_cluster}
Platform: {prompt.intended_platform}
Context: {prompt.prompt_text}

Write a short-form content package for the topic above.

Rules:
- No hype phrases: game-changing, revolutionary, mind-blowing, unlock your potential
- No fake statistics or invented numbers
- Practical, specific, natural spoken language
- Platform-appropriate tone for {prompt.intended_platform}
- Script sections must be labelled: [Hook], [Body], [CTA]
- Script should take 45-60 seconds when spoken aloud
- Provide exactly 5 hook variations with these categories: Curiosity, Pain Point, Bold Claim, Tutorial, Mistake/Myth"""


def _pro_critique_prompt(script_text: str, platform: str) -> str:
    return f"""You are a senior content strategist. Improve the {platform} script below.

Make the hook land in the first 2 seconds. Add one concrete example or data point to the body. Strengthen the CTA to drive a specific action.

Keep the same [Hook] / [Body] / [CTA] structure and the same spoken length (45-60 seconds).
Return ONLY the improved script text - no JSON, no explanation, no labels outside the script itself.

Script to improve:
{script_text}"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ScriptWriterAgent:
    """
    Generates platform-specific short-form video scripts.

    generation_mode:
      "free"   - deterministic template output, no API calls
      "assist" - one combined Gemini call per trend (script + hooks + CTA + visual notes)
                 Uses native structured output (response_json_schema) for reliability,
                 with automatic fallback to plain-text parsing.
      "pro"    - same as assist, plus a second Gemini critique/rewrite pass per script

    ai_hooks: populated during process() for assist/pro modes so that
    HookGeneratorAgent can reuse the hooks from the same Gemini call instead of
    making extra calls.

    ai_generated_count / template_fallback_count: populated during process() so
    the pipeline can include generation metadata in the run report.
    """

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

    def __init__(self, generation_mode: str = "free") -> None:
        self.generation_mode = generation_mode
        self.client = GeminiClient()
        # Keyed by topic cluster; populated during AI generation runs.
        self.ai_hooks: Dict[str, List[HookOption]] = {}
        # Per-run counters for the report.
        self.ai_generated_count: int = 0
        self.template_fallback_count: int = 0
        # Unique safe error categories seen during this run (insertion-ordered).
        self.gemini_error_categories: List[str] = []

    # ------------------------------------------------------------------
    # Sanitization
    # ------------------------------------------------------------------

    def _sanitize(self, text: str) -> str:
        result = text
        for phrase in self.BANNED_PHRASES:
            result = result.replace(phrase, "").replace(phrase.capitalize(), "")
        while "  " in result:
            result = result.replace("  ", " ")
        return result.strip()

    # ------------------------------------------------------------------
    # Template (Free Mode)
    # ------------------------------------------------------------------

    def _template_script(self, prompt: GeneratedPrompt) -> ScriptOutput:
        topic = prompt.topic_cluster
        platform = prompt.intended_platform.lower()

        if "youtube" in platform:
            script_text = (
                f"[Hook] Here is what most people get wrong about {topic}.\n"
                f"[Context] I spent the last two weeks testing different approaches, "
                f"and the results were not what I expected.\n"
                f"[Body] The most common mistake: jumping to tools before defining the workflow. "
                f"Start with the smallest working version. Document what breaks. Iterate from there.\n"
                f"[CTA] Subscribe for the next part - I'll show the actual numbers."
            )
            cta = "Subscribe for part 2 - with real results."
            visual_notes = (
                "Screen-record the workflow. Use text overlays at each step transition. "
                "Keep cuts under 3 seconds. End with a still frame showing the output."
            )
            duration = 90

        elif "linkedin" in platform:
            script_text = (
                f"[Hook] {topic} - here is what I noticed after three months of testing.\n"
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
            script_text = (
                f"[Hook] {topic} - this is the part nobody shows you.\n"
                f"[Body] I built this from scratch in two days. No paid tools, no shortcuts. "
                f"Here is the exact process I used, step by step.\n"
                f"[Payoff] The output looked exactly like what our team used to spend a week producing.\n"
                f"[CTA] Save this - you will want to come back when you need it."
            )
            cta = "Save this post and follow for the full breakdown."
            visual_notes = (
                "Fast cuts. Show the screen or the physical output. "
                "Add subtitles - 85% of short-form is watched on mute. "
                "Keep the hook under 2 seconds of visuals."
            )
            duration = 50

        return ScriptOutput(
            topic=topic,
            script_text=self._sanitize(script_text),
            cta=cta,
            estimated_duration_sec=duration,
            visual_notes=visual_notes,
        )

    # ------------------------------------------------------------------
    # AI generation (Assist + Pro)
    # ------------------------------------------------------------------

    def _ai_draft(self, prompt: GeneratedPrompt) -> Optional[ScriptOutput]:
        """
        One Gemini call per trend using native structured output.
        Returns script + CTA + visual notes, and caches the 5 hooks in
        self.ai_hooks[topic] for HookGeneratorAgent.
        Returns None on any failure.
        """
        data = self.client.generate_json(
            _assist_prompt(prompt),
            json_schema=_ASSIST_JSON_SCHEMA,
        )
        if data is None:
            return None

        try:
            script_text = self._sanitize(str(data.get("script_text", "")))
            cta = str(data.get("cta", ""))
            visual_notes = str(data.get("visual_notes", ""))

            if not script_text:
                return None

            # Parse and cache hooks so HookGeneratorAgent can reuse them
            raw_hooks = data.get("hooks", [])
            parsed_hooks: List[HookOption] = []
            for h in raw_hooks:
                if isinstance(h, dict) and "category" in h and "text" in h:
                    parsed_hooks.append(
                        HookOption(
                            category=str(h["category"]),
                            text=self._sanitize(str(h["text"])),
                        )
                    )
            if parsed_hooks:
                self.ai_hooks[prompt.topic_cluster] = parsed_hooks

            # Estimate duration: ~130 words per minute for spoken content
            word_count = len(script_text.split())
            duration = max(30, min(120, round((word_count / 130) * 60)))

            return ScriptOutput(
                topic=prompt.topic_cluster,
                script_text=script_text,
                cta=cta,
                estimated_duration_sec=duration,
                visual_notes=visual_notes,
            )
        except Exception:
            print(
                f"[Gemini] Failed to parse response for '{prompt.topic_cluster}' "
                "- using template"
            )
            return None

    def _ai_pro_refine(self, script: ScriptOutput, platform: str) -> ScriptOutput:
        """
        Second Gemini call (Pro mode only): critique + rewrite the draft script.
        Returns the original script unchanged if the call fails.
        """
        improved = self.client.generate(
            _pro_critique_prompt(script.script_text, platform),
            max_output_tokens=1024,
        )
        if not improved or not improved.strip():
            print(f"[Gemini] Pro refinement failed for '{script.topic}' - keeping draft")
            return script

        return ScriptOutput(
            topic=script.topic,
            script_text=self._sanitize(improved.strip()),
            cta=script.cta,
            estimated_duration_sec=script.estimated_duration_sec,
            visual_notes=script.visual_notes,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def write_script(self, prompt: GeneratedPrompt) -> ScriptOutput:
        if self.generation_mode != "free" and self.client.is_available():
            draft = self._ai_draft(prompt)
            if draft is None:
                print(
                    f"[Gemini] Assist generation failed for '{prompt.topic_cluster}' "
                    "- using template fallback"
                )
                self.template_fallback_count += 1
                # Collect the safe error category for the run report.
                cat = self.client.last_error_category
                if cat and cat not in self.gemini_error_categories:
                    self.gemini_error_categories.append(cat)
            else:
                self.ai_generated_count += 1
                if self.generation_mode == "pro":
                    return self._ai_pro_refine(draft, prompt.intended_platform)
                return draft

        return self._template_script(prompt)

    def process(self, prompts: List[GeneratedPrompt]) -> List[ScriptOutput]:
        return [self.write_script(p) for p in prompts]
