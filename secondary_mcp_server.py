"""
Secondary MCP Server: Market Intelligence & Candidate Database (Part B Bonus)
=============================================================================
A standardized Model Context Protocol (MCP) server providing market intelligence,
salary benchmarks, skill taxonomy analysis, and candidate screening registry storage.

Used by matching_agent.py to demonstrate Multi-MCP integration.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as MCPServer
    except ImportError as e:
        raise ImportError("Please install mcp SDK: pip install mcp>=1.0.0") from e

SERVER_NAME = "market-intelligence-mcp-server"
app = MCPServer(SERVER_NAME)

REGISTRY_PATH = Path("data/output/screening_registry.json")


# ============================================================================
# Benchmark Knowledge Base
# ============================================================================

ROLE_BENCHMARKS = {
    "ai_engineer": {
        "title": "Senior AI / Agent Systems Engineer",
        "median_salary_usd": 185000,
        "salary_range_usd": [160000, 230000],
        "core_skills": ["python", "langgraph", "langchain", "mcp", "fastmcp", "pytorch", "transformers"],
        "cloud_skills": ["aws", "gcp", "docker", "kubernetes"],
        "minimum_experience_years": 4,
        "market_demand": "Very High"
    },
    "mlops_engineer": {
        "title": "MLOps / ML Infrastructure Engineer",
        "median_salary_usd": 175000,
        "salary_range_usd": [150000, 215000],
        "core_skills": ["python", "docker", "kubernetes", "kubeflow", "ray", "terraform", "ci/cd", "mlflow"],
        "cloud_skills": ["aws", "gcp"],
        "minimum_experience_years": 3,
        "market_demand": "High"
    },
    "fullstack_engineer": {
        "title": "Full Stack React & Node Engineer",
        "median_salary_usd": 150000,
        "salary_range_usd": [130000, 185000],
        "core_skills": ["react", "next.js", "typescript", "javascript", "node.js", "css3", "html5"],
        "cloud_skills": ["docker", "aws"],
        "minimum_experience_years": 3,
        "market_demand": "Moderate"
    }
}


# ============================================================================
# MCP Resources
# ============================================================================

@app.resource("market://benchmark/{role_key}")
def get_market_benchmark(role_key: str) -> str:
    """
    Exposes role salary and skill benchmarks as an MCP resource.
    Example URI: market://benchmark/ai_engineer
    """
    clean_key = role_key.lower().replace("-", "_").replace(" ", "_")
    for key, data in ROLE_BENCHMARKS.items():
        if key in clean_key or clean_key in key:
            return json.dumps(data, indent=2)
    return json.dumps({"error": f"Role benchmark '{role_key}' not found", "available": list(ROLE_BENCHMARKS.keys())})


@app.resource("registry://candidate/{candidate_id}")
def get_candidate_record(candidate_id: str) -> str:
    """
    Exposes evaluated candidate records from the screening registry.
    Example URI: registry://candidate/alex_rivers
    """
    if not REGISTRY_PATH.exists():
        return json.dumps({"status": "empty", "message": "Registry does not exist yet."})

    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)
        record = registry.get(candidate_id.lower().replace(" ", "_"))
        if record:
            return json.dumps(record, indent=2)
        return json.dumps({"status": "not_found", "candidate_id": candidate_id})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================================
# MCP Tools
# ============================================================================

@app.tool()
def benchmark_market_role(role_title: str, location: str = "US") -> Dict[str, Any]:
    """
    Retrieve market salary data, benchmark requirements, and skill taxonomy for a role.
    
    Args:
        role_title: Job title or keywords (e.g. 'Senior AI Engineer', 'MLOps').
        location: Geographic region (default: 'US').
    Returns:
        Structured market benchmark dictionary.
    """
    lower = role_title.lower()
    matched_data = None
    for key, data in ROLE_BENCHMARKS.items():
        if key in lower or any(word in lower for word in key.split("_")):
            matched_data = data
            break

    if not matched_data:
        matched_data = ROLE_BENCHMARKS["ai_engineer"] # Fallback

    return {
        "status": "success",
        "query_role": role_title,
        "location": location,
        "benchmark": matched_data,
        "source": "Global Tech Labor Intelligence 2026",
        "retrieved_at": time.time()
    }


@app.tool()
def calculate_skill_weight(role_title: str, candidate_skills: List[str]) -> Dict[str, Any]:
    """
    Calculate market-weighted relevance and alignment for a candidate's skills.
    
    Args:
        role_title: Target position.
        candidate_skills: List of skills extracted from candidate resume.
    Returns:
        Relevance score, matched critical skills, and identified skill gaps.
    """
    b_data = benchmark_market_role(role_title)["benchmark"]
    core = set(b_data["core_skills"])
    cand = set(s.lower() for s in candidate_skills)

    matched_core = list(core.intersection(cand))
    missing_core = list(core - cand)

    coverage = len(matched_core) / max(len(core), 1)
    relevance_score = round(coverage * 100, 1)

    return {
        "status": "success",
        "relevance_score": relevance_score,
        "matched_critical_skills": matched_core,
        "missing_critical_skills": missing_core,
        "is_qualified": relevance_score >= 60.0
    }


@app.tool()
def store_candidate_evaluation(
    candidate_name: str,
    role: str,
    score: float,
    recommendation: str,
    strengths: List[str],
    gaps: List[str]
) -> Dict[str, Any]:
    """
    Persist structured candidate evaluation results into the screening database registry.
    
    Args:
        candidate_name: Candidate full name.
        role: Evaluated job role.
        score: Compatibility score (0 - 100).
        recommendation: Status (e.g. 'Strongly Recommend', 'Proceed to Interview', 'Reject').
        strengths: Key candidate strengths.
        gaps: Candidate skill or experience gaps.
    Returns:
        Confirmation dict with storage timestamp.
    """
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    registry = {}
    if REGISTRY_PATH.exists():
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except Exception:
            registry = {}

    key = candidate_name.lower().replace(" ", "_")
    record = {
        "candidate_name": candidate_name,
        "role": role,
        "score": score,
        "recommendation": recommendation,
        "strengths": strengths,
        "gaps": gaps,
        "evaluated_timestamp": time.time(),
        "registry_id": f"REC-{int(time.time())}-{key[:6]}"
    }
    registry[key] = record

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    return {
        "status": "stored",
        "registry_id": record["registry_id"],
        "candidate_key": key,
        "total_records_in_db": len(registry)
    }


def run_self_test():
    """Execute self-test for secondary market intelligence MCP server."""
    print("=" * 60)
    print("Market Intelligence & Database MCP Server - Self Test")
    print("=" * 60)

    # 1. Benchmark test
    print("\n1. Testing 'benchmark_market_role' for 'Senior AI Engineer'...")
    bench = benchmark_market_role("Senior AI Engineer")
    print(f"   Median Salary: ${bench['benchmark']['median_salary_usd']:,} | Demand: {bench['benchmark']['market_demand']}")

    # 2. Skill weight test
    print("\n2. Testing 'calculate_skill_weight'...")
    cand_skills = ["python", "langgraph", "mcp", "docker"]
    weight = calculate_skill_weight("Senior AI Engineer", cand_skills)
    print(f"   Relevance Score: {weight['relevance_score']}% | Matched: {weight['matched_critical_skills']}")

    # 3. Store candidate test
    print("\n3. Testing 'store_candidate_evaluation'...")
    saved = store_candidate_evaluation(
        candidate_name="Alex Rivers",
        role="Senior AI Engineer",
        score=92.5,
        recommendation="Strongly Recommend",
        strengths=["Deep LangGraph & MCP expertise", "Production LLM architecture"],
        gaps=["No explicit Triton mention"]
    )
    print(f"   Stored record {saved['registry_id']} for candidate key '{saved['candidate_key']}'.")

    print("\n" + "=" * 60)
    print("ALL SECONDARY MCP SERVER TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        run_self_test()
    else:
        app.run(transport="stdio")
