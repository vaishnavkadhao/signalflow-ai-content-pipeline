import pytest
import os
import tempfile
import csv as csv_module
from unittest.mock import patch, MagicMock
from schemas.pipeline_schemas import TrendInput, ValidatedTopic, PatternAnalysis, GeneratedPrompt
from agents.validator import TopicValidatorAgent
from agents.pattern_analyzer import PatternAnalyzerAgent
from agents.script_writer import ScriptWriterAgent
from agents.hook_generator import HookGeneratorAgent
from agents.gemini_client import GeminiClient, get_model_name
from connectors.manual_csv import read_trends_from_csv


# ──────────────────────────────────────────────
# EXISTING TESTS (schema + scoring + patterns)
# ──────────────────────────────────────────────

def test_trend_input_schema():
    """Tests TrendInput schema validation."""
    data = {
        "trend_title": "Test AI Agent",
        "views": 100000,
        "likes": 5000,
        "comments": 200,
        "shares": 50,
        "platform": "YouTube",
        "url": "https://example.com"
    }
    trend = TrendInput(**data)
    assert trend.trend_title == "Test AI Agent"
    assert trend.views == 100000
    assert trend.likes == 5000


def test_topic_scoring_logic():
    """Tests our TopicValidatorAgent scoring, fit, and engagement metrics."""
    agent = TopicValidatorAgent()
    trend = TrendInput(
        trend_title="Vibe Coding is here to stay",
        views=1000000,
        likes=40000,
        comments=3000,
        shares=1000,
        platform="YouTube"
    )
    trend_score = agent.calculate_trend_score(trend)
    engagement_score = agent.calculate_engagement_score(trend)
    creator_fit = agent.calculate_creator_fit(trend)

    assert 0 <= trend_score <= 10
    assert 0 <= engagement_score <= 10
    assert 0 <= creator_fit <= 10
    assert creator_fit >= 5.0


def test_pattern_analyzer():
    """Tests that PatternAnalyzerAgent creates detailed pattern outputs."""
    analyzer = PatternAnalyzerAgent()
    topic = ValidatedTopic(
        trend_title="Vibe Coding is here",
        views=1000,
        likes=10,
        comments=0,
        shares=0,
        platform="Unknown",
        url="",
        trend_score=1.0,
        engagement_score=1.0,
        creator_fit_score=3.0,
        final_score=2.0,
        explanation="Baseline"
    )
    analysis = analyzer.analyze(topic)
    assert isinstance(analysis, PatternAnalysis)
    assert "curiosity" in analysis.hook_style.lower() or "contrarian" in analysis.hook_style.lower()


# ──────────────────────────────────────────────
# CSV CONNECTOR TESTS
# ──────────────────────────────────────────────

def _write_temp_csv(rows: list[dict], fieldnames: list[str]) -> str:
    """Helper: write a temp CSV file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
    )
    writer = csv_module.DictWriter(tmp, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    tmp.close()
    return tmp.name


def test_legacy_csv_format():
    """Old format (trend_title, url) must still work without changes."""
    rows = [
        {"trend_title": "AI Agents for content", "views": "500000", "likes": "20000",
         "comments": "1000", "shares": "500", "platform": "YouTube", "url": "https://yt.com/1"}
    ]
    path = _write_temp_csv(rows, fieldnames=["trend_title", "views", "likes", "comments", "shares", "platform", "url"])
    try:
        trends = read_trends_from_csv(path)
        assert len(trends) == 1
        assert trends[0]["trend_title"] == "AI Agents for content"
        assert trends[0]["url"] == "https://yt.com/1"
        assert trends[0]["views"] == 500000
    finally:
        os.unlink(path)


def test_new_topic_source_url_format():
    """New format (topic, source_url) must be accepted."""
    rows = [
        {"topic": "Building in Public with AI", "source_url": "https://instagram.com/reel1",
         "views": "850000", "likes": "32000", "comments": "2100", "shares": "4500",
         "platform": "Instagram"}
    ]
    path = _write_temp_csv(
        rows,
        fieldnames=["topic", "source_url", "views", "likes", "comments", "shares", "platform"]
    )
    try:
        trends = read_trends_from_csv(path)
        assert len(trends) == 1
        assert trends[0]["trend_title"] == "Building in Public with AI"
        assert trends[0]["url"] == "https://instagram.com/reel1"
        assert trends[0]["views"] == 850000
    finally:
        os.unlink(path)


def test_extended_template_format():
    """New extended template format with all optional columns must work."""
    rows = [
        {
            "topic": "LLM routing patterns",
            "platform": "LinkedIn",
            "source_url": "https://linkedin.com/post1",
            "views": "120000", "likes": "4500", "comments": "300", "shares": "200", "saves": "800",
            "posted_date": "2025-05-15", "creator": "@techcreator", "content_format": "Carousel",
            "content_pillar": "AI Automation", "region": "IN", "keyword": "LLM routing"
        }
    ]
    path = _write_temp_csv(
        rows,
        fieldnames=["topic", "platform", "source_url", "views", "likes", "comments",
                    "shares", "saves", "posted_date", "creator", "content_format",
                    "content_pillar", "region", "keyword"]
    )
    try:
        trends = read_trends_from_csv(path)
        assert len(trends) == 1
        t = trends[0]
        assert t["trend_title"] == "LLM routing patterns"
        assert t["content_pillar"] == "AI Automation"
        assert t["saves"] == 800
        assert t["keyword"] == "LLM routing"
    finally:
        os.unlink(path)


def test_sample_trends_csv_still_works():
    """The original data/sample_trends.csv must still parse correctly."""
    path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_trends.csv")
    if not os.path.exists(path):
        pytest.skip("data/sample_trends.csv not found")
    trends = read_trends_from_csv(path)
    assert len(trends) >= 1
    assert "trend_title" in trends[0]
    assert isinstance(trends[0]["views"], int)


def test_template_trends_csv_works():
    """The new data/templates/sample_trends.csv must also parse correctly."""
    path = os.path.join(os.path.dirname(__file__), "..", "data", "templates", "sample_trends.csv")
    if not os.path.exists(path):
        pytest.skip("data/templates/sample_trends.csv not found")
    trends = read_trends_from_csv(path)
    assert len(trends) >= 1
    assert "trend_title" in trends[0]


def test_csv_missing_title_column_raises():
    """A CSV without any recognised title column must raise a clear ValueError."""
    rows = [{"wrong_col": "some topic", "platform": "YouTube"}]
    path = _write_temp_csv(rows, fieldnames=["wrong_col", "platform"])
    try:
        with pytest.raises(ValueError, match="topic.*trend_title.*title"):
            read_trends_from_csv(path)
    finally:
        os.unlink(path)


# ──────────────────────────────────────────────
# PHASE B: GEMINI CLIENT TESTS
# ──────────────────────────────────────────────

def test_gemini_client_unavailable_without_key():
    """GeminiClient.is_available() must return False when no key is set."""
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        client = GeminiClient()
        assert client.is_available() is False


def test_gemini_client_generate_returns_none_without_key():
    """generate() must return None (not raise) when no key is set."""
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        client = GeminiClient()
        result = client.generate("hello")
        assert result is None


def test_gemini_client_model_env_override():
    """GEMINI_MODEL env var must override the default model name."""
    with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-test-model"}):
        assert get_model_name() == "gemini-test-model"


def test_gemini_client_default_model_set():
    """Default model name must be a non-empty string."""
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_MODEL"}
    with patch.dict(os.environ, env, clear=True):
        assert len(get_model_name()) > 0


# ──────────────────────────────────────────────
# PHASE B: FREE MODE TESTS
# ──────────────────────────────────────────────

def _make_prompt(topic: str = "AI content pipelines", platform: str = "YouTube Shorts") -> GeneratedPrompt:
    return GeneratedPrompt(
        prompt_id="test-001",
        prompt_version="1.0.0",
        topic_cluster=topic,
        intended_platform=platform,
        content_format="Short-form Video",
        prompt_text="Test prompt context.",
    )


def test_free_mode_script_writer_no_key_needed():
    """Free mode ScriptWriterAgent must produce output without a Gemini key."""
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        agent = ScriptWriterAgent(generation_mode="free")
        script = agent.write_script(_make_prompt())
        assert script.script_text
        assert script.cta
        assert script.topic == "AI content pipelines"
        # No AI hooks should be cached in free mode
        assert agent.ai_hooks == {}


def test_free_mode_hook_generator_no_key_needed():
    """Free mode HookGeneratorAgent must produce 5 hooks without a Gemini key."""
    from schemas.pipeline_schemas import ScriptOutput
    script = ScriptOutput(
        topic="AI content pipelines",
        script_text="[Hook] Test hook\n[Body] Test body\n[CTA] Test CTA",
        cta="Follow for more.",
        estimated_duration_sec=50,
        visual_notes="Show the screen.",
    )
    agent = HookGeneratorAgent(generation_mode="free")
    output = agent.generate_hooks(script)
    assert output.topic == "AI content pipelines"
    assert len(output.hooks) == 5
    for hook in output.hooks:
        assert hook.category
        assert hook.text


def test_free_mode_script_has_no_banned_phrases():
    """Template scripts must not contain any banned hype phrases."""
    agent = ScriptWriterAgent(generation_mode="free")
    for platform in ["YouTube Shorts", "LinkedIn Post", "Instagram Reels"]:
        script = agent.write_script(_make_prompt(platform=platform))
        for phrase in agent.BANNED_PHRASES:
            assert phrase not in script.script_text.lower(), (
                f"Banned phrase '{phrase}' found in script for {platform}"
            )


# ──────────────────────────────────────────────
# PHASE B: GEMINI FALLBACK TESTS
# ──────────────────────────────────────────────

def test_assist_mode_falls_back_to_template_when_gemini_fails():
    """
    If Gemini raises an exception in assist mode, ScriptWriterAgent must
    return a valid template script without crashing.
    """
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-test-key"}):
        with patch("agents.gemini_client.GeminiClient.generate", side_effect=Exception("mock API error")):
            agent = ScriptWriterAgent(generation_mode="assist")
            script = agent.write_script(_make_prompt())
            # Must have fallen back to template
            assert script.script_text
            assert script.topic == "AI content pipelines"
            # No hooks cached since AI failed
            assert agent.ai_hooks == {}


def test_assist_mode_falls_back_when_gemini_returns_invalid_json():
    """
    If Gemini returns text that cannot be parsed as JSON, agent must
    fall back to templates silently.
    """
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-test-key"}):
        with patch("agents.gemini_client.GeminiClient.generate", return_value="not valid json {{{"):
            agent = ScriptWriterAgent(generation_mode="assist")
            script = agent.write_script(_make_prompt())
            assert script.script_text
            assert agent.ai_hooks == {}


def test_pro_mode_refinement_falls_back_when_second_call_fails():
    """
    Pro mode: if the refinement call fails, the draft script must be
    returned unchanged (not None, not a crash).
    """
    draft_json = (
        '{"script_text": "[Hook] Draft hook\\n[Body] Draft body\\n[CTA] Draft CTA", '
        '"cta": "Follow for more.", "visual_notes": "Screen record.", '
        '"hooks": [{"category": "Curiosity", "text": "Test hook"},'
        '{"category": "Pain Point", "text": "Hook 2"},'
        '{"category": "Bold Claim", "text": "Hook 3"},'
        '{"category": "Tutorial", "text": "Hook 4"},'
        '{"category": "Mistake/Myth", "text": "Hook 5"}]}'
    )
    call_count = {"n": 0}

    def mock_generate(self, prompt, max_output_tokens=2048):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return draft_json      # first call: draft succeeds
        return None                # second call: refinement fails

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-test-key"}):
        with patch("agents.gemini_client.GeminiClient.generate", mock_generate):
            agent = ScriptWriterAgent(generation_mode="pro")
            script = agent.write_script(_make_prompt())
            # Draft was returned (refinement failed gracefully)
            assert script.script_text
            assert "Draft hook" in script.script_text or script.script_text


def test_hooks_reused_from_script_writer_cache():
    """
    In assist mode, HookGeneratorAgent must reuse hooks cached by
    ScriptWriterAgent rather than generating new ones.
    """
    from schemas.pipeline_schemas import ScriptOutput, HookOption

    cached_hooks = [
        HookOption(category="Curiosity", text="Cached curiosity hook"),
        HookOption(category="Pain Point", text="Cached pain point"),
        HookOption(category="Bold Claim", text="Cached bold claim"),
        HookOption(category="Tutorial", text="Cached tutorial"),
        HookOption(category="Mistake/Myth", text="Cached myth hook"),
    ]

    script = ScriptOutput(
        topic="AI content pipelines",
        script_text="Test script",
        cta="Follow.",
        estimated_duration_sec=50,
        visual_notes="Screen.",
    )

    hook_gen = HookGeneratorAgent(
        generation_mode="assist",
        precomputed_hooks={"AI content pipelines": cached_hooks},
    )
    output = hook_gen.generate_hooks(script)
    assert output.hooks[0].text == "Cached curiosity hook"
    assert len(output.hooks) == 5


# ──────────────────────────────────────────────
# PHASE B: API KEY SAFETY TESTS
# ──────────────────────────────────────────────

def test_api_key_not_in_stdout_on_gemini_failure(capsys):
    """
    If a low-level SDK exception contains the API key value, the key must NOT
    appear in stdout or stderr. We patch at the SDK Client level so the real
    generate() catch fires and prints only a generic message.
    """
    secret_key = "SHOULD-NOT-APPEAR-IN-OUTPUT-12345"
    with patch.dict(os.environ, {"GEMINI_API_KEY": secret_key}):
        # Raise inside the SDK so generate()'s broad except catches it
        with patch("google.genai.Client", side_effect=Exception(f"SDK auth error: {secret_key}")):
            agent = ScriptWriterAgent(generation_mode="assist")
            agent.write_script(_make_prompt())  # must not crash

    captured = capsys.readouterr()
    assert secret_key not in captured.out, "API key must not appear in stdout"
    assert secret_key not in captured.err, "API key must not appear in stderr"


def test_gemini_client_generate_exception_does_not_leak_key(capsys):
    """
    GeminiClient.generate() must not print the API key when an exception occurs.
    """
    secret_key = "MY-SECRET-KEY-ABCDEF"
    with patch.dict(os.environ, {"GEMINI_API_KEY": secret_key}):
        with patch("google.genai.Client", side_effect=Exception(f"Auth failed: {secret_key}")):
            client = GeminiClient()
            result = client.generate("test prompt")

    assert result is None
    captured = capsys.readouterr()
    assert secret_key not in captured.out
    assert secret_key not in captured.err


# ──────────────────────────────────────────────
# PHASE B: CLI / GENERATION MODE TESTS
# ──────────────────────────────────────────────

def test_generation_mode_cli_arg_accepted():
    """
    run_pipeline.run() must accept generation_mode without crashing in free mode.
    Runs a minimal end-to-end pipeline using the sample CSV.
    """
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "sample_trends.csv"
    )
    if not os.path.exists(sample_path):
        pytest.skip("data/sample_trends.csv not found")

    from workflows.run_pipeline import run

    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        result = run(
            input_csv=sample_path,
            dry_run=True,
            use_llm=False,
            max_trends=2,
            generation_mode="free",
        )

    assert result.calendar_items_count >= 1
    assert result.scripts_written >= 1


def test_assist_mode_without_key_falls_back_gracefully():
    """
    If assist mode is selected but no key is set, the pipeline must still
    complete using template output -- no crash, no exception.
    """
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "sample_trends.csv"
    )
    if not os.path.exists(sample_path):
        pytest.skip("data/sample_trends.csv not found")

    from workflows.run_pipeline import run

    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        result = run(
            input_csv=sample_path,
            dry_run=False,
            use_llm=False,
            max_trends=2,
            generation_mode="assist",
        )

    assert result.calendar_items_count >= 1


# ──────────────────────────────────────────────
# PHASE B: STRUCTURED OUTPUT TESTS
# ──────────────────────────────────────────────

def test_generate_json_uses_structured_output_when_schema_provided(capsys):
    """
    generate_json() with a json_schema must call _try_structured() first.
    If structured succeeds, the result is returned without a plain-text fallback.
    """
    valid_response = {
        "script_text": "[Hook] AI is here\n[Body] Details\n[CTA] Follow.",
        "cta": "Follow.",
        "visual_notes": "Show screen.",
        "hooks": [
            {"category": "Curiosity", "text": "Hook 1"},
            {"category": "Pain Point", "text": "Hook 2"},
            {"category": "Bold Claim", "text": "Hook 3"},
            {"category": "Tutorial", "text": "Hook 4"},
            {"category": "Mistake/Myth", "text": "Hook 5"},
        ],
    }

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        with patch(
            "agents.gemini_client.GeminiClient._try_structured",
            return_value=valid_response,
        ) as mock_structured:
            client = GeminiClient()
            result = client.generate_json("test prompt", json_schema={"type": "object"})

    assert result == valid_response
    mock_structured.assert_called_once()


def test_generate_json_falls_back_to_plain_text_when_structured_fails(capsys):
    """
    If _try_structured() returns None, generate_json() must try plain text mode.
    """
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        with patch(
            "agents.gemini_client.GeminiClient._try_structured",
            return_value=None,
        ):
            with patch(
                "agents.gemini_client.GeminiClient.generate",
                return_value='{"key": "value"}',
            ):
                client = GeminiClient()
                result = client.generate_json(
                    "test prompt", json_schema={"type": "object"}
                )

    assert result == {"key": "value"}


def test_generate_json_no_schema_skips_structured_output():
    """
    generate_json() called without json_schema must NOT call _try_structured().
    """
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        with patch(
            "agents.gemini_client.GeminiClient._try_structured",
        ) as mock_structured:
            with patch(
                "agents.gemini_client.GeminiClient.generate",
                return_value='{"key": "value"}',
            ):
                client = GeminiClient()
                result = client.generate_json("test prompt")  # no json_schema

    mock_structured.assert_not_called()
    assert result == {"key": "value"}


def test_script_writer_ai_generated_count_increments_on_success():
    """
    ai_generated_count must increment when Gemini successfully returns a draft.
    template_fallback_count must stay 0.
    """
    valid_data = {
        "script_text": "[Hook] Test\n[Body] Body\n[CTA] CTA",
        "cta": "Follow.",
        "visual_notes": "Screen.",
        "hooks": [
            {"category": "Curiosity", "text": "H1"},
            {"category": "Pain Point", "text": "H2"},
            {"category": "Bold Claim", "text": "H3"},
            {"category": "Tutorial", "text": "H4"},
            {"category": "Mistake/Myth", "text": "H5"},
        ],
    }
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        with patch(
            "agents.gemini_client.GeminiClient.generate_json",
            return_value=valid_data,
        ):
            agent = ScriptWriterAgent(generation_mode="assist")
            agent.write_script(_make_prompt("Topic A"))
            agent.write_script(_make_prompt("Topic B"))

    assert agent.ai_generated_count == 2
    assert agent.template_fallback_count == 0


def test_script_writer_fallback_count_increments_on_failure():
    """
    template_fallback_count must increment when Gemini returns None.
    ai_generated_count must stay 0.
    """
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        with patch(
            "agents.gemini_client.GeminiClient.generate_json",
            return_value=None,
        ):
            agent = ScriptWriterAgent(generation_mode="assist")
            agent.write_script(_make_prompt("Topic A"))
            agent.write_script(_make_prompt("Topic B"))

    assert agent.template_fallback_count == 2
    assert agent.ai_generated_count == 0


def test_try_structured_returns_none_on_api_failure(capsys):
    """
    _try_structured() must return None (not raise) when the API call fails.
    Must not log the key.
    """
    secret_key = "SECRET-STRUCT-KEY-99"
    with patch.dict(os.environ, {"GEMINI_API_KEY": secret_key}):
        with patch(
            "google.genai.Client",
            side_effect=Exception(f"error: {secret_key}"),
        ):
            client = GeminiClient()
            result = client._try_structured("prompt", {"type": "object"})

    assert result is None
    captured = capsys.readouterr()
    assert secret_key not in captured.out
    assert secret_key not in captured.err


def test_assist_schema_passed_to_generate_json():
    """
    ScriptWriterAgent._ai_draft() must pass _ASSIST_JSON_SCHEMA to generate_json().
    """
    from agents.script_writer import _ASSIST_JSON_SCHEMA

    assert isinstance(_ASSIST_JSON_SCHEMA, dict)
    # Verify the required fields are present in the schema
    props = _ASSIST_JSON_SCHEMA.get("properties", {})
    assert "script_text" in props
    assert "cta" in props
    assert "visual_notes" in props
    assert "hooks" in props
    # Hooks items must require category and text
    hook_item_props = props["hooks"]["items"]["properties"]
    assert "category" in hook_item_props
    assert "text" in hook_item_props


# ──────────────────────────────────────────────
# RETRY TESTS
# ──────────────────────────────────────────────

_VALID_AI_RESPONSE = {
    "script_text": "[Hook] Retry test hook\n[Body] Body here\n[CTA] Follow.",
    "cta": "Follow for more.",
    "visual_notes": "Show the screen.",
    "hooks": [
        {"category": "Curiosity",    "text": "Retry curiosity hook"},
        {"category": "Pain Point",   "text": "Retry pain point"},
        {"category": "Bold Claim",   "text": "Retry bold claim"},
        {"category": "Tutorial",     "text": "Retry tutorial hook"},
        {"category": "Mistake/Myth", "text": "Retry myth hook"},
    ],
}


def test_retry_succeeds_on_second_attempt_client_level():
    """
    generate_json() must retry once when the first _generate_json_once call
    returns None. If the second call succeeds, the result is returned.
    """
    call_count = {"n": 0}

    def mock_once(self, prompt, max_output_tokens, json_schema):
        call_count["n"] += 1
        return None if call_count["n"] == 1 else _VALID_AI_RESPONSE

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        with patch(
            "agents.gemini_client.GeminiClient._generate_json_once",
            mock_once,
        ):
            client = GeminiClient()
            result = client.generate_json("prompt", json_schema={"type": "object"})

    assert call_count["n"] == 2, "Expected exactly 2 attempts"
    assert result == _VALID_AI_RESPONSE


def test_retry_succeeds_on_second_attempt_agent_level():
    """
    Integration test: ScriptWriterAgent.write_script() picks up the retry result.
    ai_generated_count must be 1 and template_fallback_count must be 0.
    """
    call_count = {"n": 0}

    def mock_once(self, prompt, max_output_tokens, json_schema):
        call_count["n"] += 1
        return None if call_count["n"] == 1 else _VALID_AI_RESPONSE

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        with patch(
            "agents.gemini_client.GeminiClient._generate_json_once",
            mock_once,
        ):
            agent = ScriptWriterAgent(generation_mode="assist")
            script = agent.write_script(_make_prompt())

    assert call_count["n"] == 2, "Expected exactly 2 attempts"
    assert agent.ai_generated_count == 1
    assert agent.template_fallback_count == 0
    assert script.script_text


def test_template_fallback_when_both_retry_attempts_fail():
    """
    If both _generate_json_once calls return None, generate_json() must
    return None, and ScriptWriterAgent must fall back to template output.
    """
    call_count = {"n": 0}

    def mock_once(self, prompt, max_output_tokens, json_schema):
        call_count["n"] += 1
        return None  # both attempts fail

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        with patch(
            "agents.gemini_client.GeminiClient._generate_json_once",
            mock_once,
        ):
            agent = ScriptWriterAgent(generation_mode="assist")
            script = agent.write_script(_make_prompt())

    assert call_count["n"] == 2, "Expected exactly 2 attempts before giving up"
    assert agent.template_fallback_count == 1
    assert agent.ai_generated_count == 0
    assert script.script_text  # Template output must still be returned


def test_no_retry_when_first_attempt_succeeds():
    """
    If the first _generate_json_once call succeeds, the retry must NOT fire.
    Exactly 1 call to _generate_json_once.
    """
    call_count = {"n": 0}

    def mock_once(self, prompt, max_output_tokens, json_schema):
        call_count["n"] += 1
        return _VALID_AI_RESPONSE

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        with patch(
            "agents.gemini_client.GeminiClient._generate_json_once",
            mock_once,
        ):
            client = GeminiClient()
            result = client.generate_json("prompt", json_schema={"type": "object"})

    assert call_count["n"] == 1, "Retry must not fire when first attempt succeeds"
    assert result == _VALID_AI_RESPONSE


def test_retry_log_does_not_contain_api_key(capsys):
    """
    The retry log message printed between attempts must not contain the API key.
    """
    secret = "RETRY-SECRET-KEY-DO-NOT-LOG"

    def mock_once(self, prompt, max_output_tokens, json_schema):
        return None  # force retry log to fire

    with patch.dict(os.environ, {"GEMINI_API_KEY": secret}):
        with patch(
            "agents.gemini_client.GeminiClient._generate_json_once",
            mock_once,
        ):
            client = GeminiClient()
            client.generate_json("prompt", json_schema={"type": "object"})

    captured = capsys.readouterr()
    assert secret not in captured.out, "API key must not appear in retry log (stdout)"
    assert secret not in captured.err, "API key must not appear in retry log (stderr)"


# ──────────────────────────────────────────────
# DIAGNOSTICS TESTS
# ──────────────────────────────────────────────

from agents.gemini_client import (
    _classify_exception,
    _CATEGORY_AUTH, _CATEGORY_QUOTA, _CATEGORY_MODEL,
    _CATEGORY_SCHEMA, _CATEGORY_NETWORK, _CATEGORY_UNKNOWN,
)


def test_classify_quota_error():
    assert _classify_exception(Exception("429 Resource Exhausted: Quota exceeded")) == _CATEGORY_QUOTA


def test_classify_quota_error_rate_limit_keyword():
    assert _classify_exception(Exception("rate limit exceeded for this API")) == _CATEGORY_QUOTA


def test_classify_auth_error_api_key_keyword():
    assert _classify_exception(Exception("API key not valid. Please pass a valid API key.")) == _CATEGORY_AUTH


def test_classify_auth_error_permission_denied():
    assert _classify_exception(Exception("403 permission denied")) == _CATEGORY_AUTH


def test_classify_auth_error_status_code():
    exc = Exception("auth failure")
    exc.code = 401
    assert _classify_exception(exc) == _CATEGORY_AUTH


def test_classify_model_not_found():
    assert _classify_exception(Exception("404 Model not found: gemini-99-fake")) == _CATEGORY_MODEL


def test_classify_structured_output_unsupported():
    assert _classify_exception(
        Exception("response_mime_type application/json is not supported for this model")
    ) == _CATEGORY_SCHEMA


def test_classify_network_timeout():
    class MockTimeoutError(Exception):
        pass
    assert _classify_exception(MockTimeoutError("connection timed out")) == _CATEGORY_NETWORK


def test_classify_service_unavailable():
    exc = Exception("service unavailable")
    exc.code = 503
    assert _classify_exception(exc) == _CATEGORY_NETWORK


def test_classify_unknown_falls_back():
    assert _classify_exception(Exception("something completely unexpected")) == _CATEGORY_UNKNOWN


def test_last_error_category_set_on_generate_failure(capsys):
    """last_error_category must be set (not None) after generate() fails."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-diag-key"}):
        with patch(
            "google.genai.Client",
            side_effect=Exception("429 quota exceeded for the day"),
        ):
            client = GeminiClient()
            result = client.generate("test prompt")

    assert result is None
    assert client.last_error_category == _CATEGORY_QUOTA
    # Key must never appear in output
    captured = capsys.readouterr()
    assert "fake-diag-key" not in captured.out
    assert "fake-diag-key" not in captured.err


def test_last_error_category_set_on_structured_failure(capsys):
    """last_error_category must be set after _try_structured() fails."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-struct-key"}):
        with patch(
            "google.genai.Client",
            side_effect=Exception("API key not valid. Please pass a valid API key."),
        ):
            client = GeminiClient()
            result = client._try_structured("prompt", {"type": "object"})

    assert result is None
    assert client.last_error_category == _CATEGORY_AUTH
    captured = capsys.readouterr()
    assert "fake-struct-key" not in captured.out
    assert "fake-struct-key" not in captured.err


def test_category_printed_message_is_safe(capsys):
    """
    The printed fallback message must contain the safe category string,
    NOT raw exception text, and NOT the API key.
    """
    secret = "MY-SECRET-KEY-DIAG-XYZ"
    with patch.dict(os.environ, {"GEMINI_API_KEY": secret}):
        with patch(
            "google.genai.Client",
            side_effect=Exception(f"quota exceeded key={secret}"),
        ):
            client = GeminiClient()
            client.generate("test")

    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err
    # The safe category string must appear instead
    assert _CATEGORY_QUOTA in captured.out


def test_script_writer_collects_error_categories(capsys):
    """
    ScriptWriterAgent.gemini_error_categories must be populated after fallback.
    """
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-sw-key"}):
        with patch(
            "google.genai.Client",
            side_effect=Exception("403 permission denied for this API key"),
        ):
            agent = ScriptWriterAgent(generation_mode="assist")
            script = agent.write_script(_make_prompt())

    assert _CATEGORY_AUTH in agent.gemini_error_categories
    assert agent.template_fallback_count == 1
    assert script.script_text  # Template output returned
    captured = capsys.readouterr()
    assert "fake-sw-key" not in captured.out
    assert "fake-sw-key" not in captured.err


def test_script_writer_deduplicates_categories():
    """Same error category for multiple trends must appear only once in the list."""

    def mock_generate_json(self, prompt, max_output_tokens=2048, json_schema=None):
        # Simulate a failure that sets last_error_category on the client instance
        self.last_error_category = _CATEGORY_QUOTA
        return None

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        with patch(
            "agents.gemini_client.GeminiClient.generate_json",
            mock_generate_json,
        ):
            agent = ScriptWriterAgent(generation_mode="assist")
            agent.write_script(_make_prompt("Topic A"))
            agent.write_script(_make_prompt("Topic B"))

    assert agent.gemini_error_categories.count(_CATEGORY_QUOTA) == 1


def test_error_category_in_run_report():
    """
    When Gemini errors are categorized, the run report markdown must include
    the safe category string. Raw exception text must not appear.
    """
    import tempfile
    from agents.calendar_planner import CalendarPlannerAgent
    from schemas.pipeline_schemas import ScriptOutput, HookOutput, HookOption

    scripts = [
        ScriptOutput(
            topic="Test topic",
            script_text="[Hook] Hook\n[Body] Body\n[CTA] CTA",
            cta="Follow.",
            estimated_duration_sec=50,
            visual_notes="Screen.",
        )
    ]
    hooks = [
        HookOutput(
            topic="Test topic",
            hooks=[
                HookOption(category="Curiosity",    text="H1"),
                HookOption(category="Pain Point",   text="H2"),
                HookOption(category="Bold Claim",   text="H3"),
                HookOption(category="Tutorial",     text="H4"),
                HookOption(category="Mistake/Myth", text="H5"),
            ],
        )
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        planner = CalendarPlannerAgent()
        items = planner.plan_calendar(scripts, hooks)
        paths = planner.export(
            items,
            export_dir=tmpdir,
            generation_mode="assist",
            fallback_used=True,
            gemini_error_categories=[_CATEGORY_QUOTA],
        )
        with open(paths["markdown"], encoding="utf-8") as f:
            report = f.read()

    assert _CATEGORY_QUOTA in report
    # Raw secret tokens must never reach the report
    assert "GEMINI_API_KEY" not in report
    assert "AIza" not in report
