"""
Tests for Part B: LangGraph Matching Agent & Multi-MCP Integration
==================================================================
Verifies end-to-end execution of the refactored agent communicating
strictly via Model Context Protocol clients.
"""

import json
import pytest
from pathlib import Path
from matching_agent import run_matching_agent


@pytest.mark.asyncio
class TestMatchingAgentWorkflow:
    """Integration tests verifying full agent lifecycle through MCP servers."""

    async def test_full_matching_agent_execution_ai_role(self):
        """Verify complete agent execution for Senior AI Engineer job."""
        final_state = await run_matching_agent("job_senior_ai_engineer.txt")

        # 1. Verify Job Parsing Node
        assert "Senior AI" in final_state["job_title"]
        assert len(final_state["required_skills"]) >= 5
        assert final_state["min_experience_years"] >= 3

        # 2. Verify Candidate Discovery & Ingestion
        assert len(final_state["candidate_files"]) >= 5
        assert len(final_state["parsed_candidates"]) >= 5

        # 3. Verify Multi-MCP Market Intelligence
        benchmark = final_state["market_benchmark"]
        assert benchmark.get("median_salary_usd", 0) > 100000
        assert benchmark.get("market_demand") == "Very High"

        # 4. Verify Rankings & Scoring
        results = final_state["match_results"]
        assert len(results) >= 5

        # Ensure sorted descending
        scores = [c["composite_score"] for c in results]
        assert scores == sorted(scores, reverse=True)

        top_cand = results[0]
        assert top_cand["name"] in ["Alex Rivers", "Priya Sharma"]
        assert top_cand["composite_score"] >= 80.0
        assert top_cand["recommendation"] == "Strongly Recommend"

        # 5. Verify Output Reports saved via MCP
        report_path = Path("data/output/evaluation_report.md")
        json_path = Path("data/output/screening_results.json")
        registry_path = Path("data/output/screening_registry.json")

        assert report_path.exists()
        assert json_path.exists()
        assert registry_path.exists()

        # Check report contents
        report_text = report_path.read_text(encoding="utf-8")
        assert "# Candidate Screening & Matching Evaluation Report" in report_text
        assert "Alex Rivers" in report_text
        assert "Market Benchmark" in report_text

        # Check DB registry contents
        registry_data = json.loads(registry_path.read_text(encoding="utf-8"))
        assert "alex_rivers" in registry_data
        assert registry_data["alex_rivers"]["role"] == "Senior AI / Agent Systems Engineer"

    async def test_matching_agent_fullstack_role(self):
        """Verify agent dynamically adapts rankings for Full Stack role."""
        final_state = await run_matching_agent("job_fullstack_engineer.txt")

        assert "Full Stack" in final_state["job_title"]
        results = final_state["match_results"]

        # For Full Stack role, David Kim (Frontend/React) should rank much higher
        david = next((c for c in results if c["name"] == "David Kim"), None)
        assert david is not None
        # David Kim has react, next.js, typescript, so should have positive skill matches
        assert len(david["matched_skills"]) >= 2
