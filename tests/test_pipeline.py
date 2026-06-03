import pytest
import os
import tempfile
import csv as csv_module
from schemas.pipeline_schemas import TrendInput, ValidatedTopic, PatternAnalysis
from agents.validator import TopicValidatorAgent
from agents.pattern_analyzer import PatternAnalyzerAgent
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

    # Assert score bounds [0, 10]
    assert 0 <= trend_score <= 10
    assert 0 <= engagement_score <= 10
    assert 0 <= creator_fit <= 10

    # Assert Vibe Coding matches our creator alignment rules
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
