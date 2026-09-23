"""
Refactored LangGraph Matching Agent (Part B)
============================================
An autonomous agent orchestrating candidate resume screening and job matching.
All ad-hoc local file operations are completely replaced with standardized
Model Context Protocol (MCP) clients connecting to multiple MCP servers:

1. Primary Filesystem MCP Server (Part A):
   - Resources: job://{file}, resume://{file}
   - Tools: read_file, list_directory, batch_process, write_file

2. Secondary Market Intelligence MCP Server (Part B Bonus):
   - Tools: benchmark_market_role, calculate_skill_weight, store_candidate_evaluation
"""

import sys
import json
import asyncio
from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime

# Ensure UTF-8 stdout encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from langgraph.graph import StateGraph, START, END
from mcp_client import MultiMCPManager


# ============================================================================
# Agent State Schema
# ============================================================================

class MatchingState(TypedDict):
    job_file: str
    job_title: str
    job_content: str
    required_skills: List[str]
    min_experience_years: int
    candidate_files: List[str]
    parsed_candidates: List[Dict[str, Any]]
    market_benchmark: Dict[str, Any]
    match_results: List[Dict[str, Any]]
    report_markdown: str
    saved_report_path: str
    status: str
    logs: List[str]


# Global MCP Manager reference for LangGraph nodes during invocation
_CURRENT_MCP_MANAGER: Optional[MultiMCPManager] = None


# ============================================================================
# LangGraph Nodes (100% MCP Mediated - ZERO direct file system access)
# ============================================================================

async def fetch_job_description(state: MatchingState) -> Dict[str, Any]:
    """Node 1: Read and parse Job Description using MCP Resource or read_file tool."""
    mcp = _CURRENT_MCP_MANAGER
    job_file = state.get("job_file", "job_senior_ai_engineer.txt")
    logs = list(state.get("logs", []))

    logs.append(f"[MCP Filesystem] Fetching job spec for: '{job_file}' via MCP...")

    # Fetch job description content via MCP tool or resource
    try:
        content = await mcp.read_resource(f"job://{job_file}")
    except Exception:
        # Fallback to read_file tool
        content = await mcp.call_tool("filesystem", "read_file", {"path": f"data/jobs/{job_file}"})

    # Parse title, required skills, and experience
    title = "Senior AI Engineer"
    min_exp = 4
    for line in content.splitlines():
        lower = line.lower()
        if "job title:" in lower:
            title = line.split(":", 1)[1].strip()
        if "4+" in lower or "4 years" in lower:
            min_exp = 4
        elif "3+" in lower or "3 years" in lower:
            min_exp = 3

    common_skills = [
        "python", "langgraph", "langchain", "mcp", "fastmcp", "pytorch",
        "transformers", "docker", "kubernetes", "aws", "gcp", "vector databases",
        "json-rpc", "mlops", "react", "typescript"
    ]
    required_skills = [s for s in common_skills if s in content.lower()]

    logs.append(f"[Agent] Target Role: '{title}' (Min Experience: {min_exp} yrs, Skills Required: {len(required_skills)})")

    return {
        "job_title": title,
        "job_content": content,
        "required_skills": required_skills,
        "min_experience_years": min_exp,
        "logs": logs
    }


async def discover_candidates(state: MatchingState) -> Dict[str, Any]:
    """Node 2: Discover candidate resume files using MCP list_directory tool."""
    mcp = _CURRENT_MCP_MANAGER
    logs = list(state.get("logs", []))

    logs.append("[MCP Filesystem] Invoking 'list_directory' on 'data/resumes'...")
    entries = await mcp.call_tool("filesystem", "list_directory", {"path": "data/resumes"})

    candidate_files = []
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and entry.get("type") == "file":
                candidate_files.append(entry.get("path"))

    logs.append(f"[Agent] Discovered {len(candidate_files)} candidate resume files via MCP.")

    return {
        "candidate_files": candidate_files,
        "logs": logs
    }


async def batch_ingest_candidates(state: MatchingState) -> Dict[str, Any]:
    """Node 3: Concurrently parse candidates using the MCP batch_process capability."""
    mcp = _CURRENT_MCP_MANAGER
    logs = list(state.get("logs", []))

    logs.append("[MCP Filesystem] Executing 'batch_process' across all candidate resumes...")
    batch_result = await mcp.call_tool(
        "filesystem",
        "batch_process",
        {"directory_path": "data/resumes", "action": "parse_resume"}
    )

    parsed = batch_result.get("results", []) if isinstance(batch_result, dict) else []
    duration = batch_result.get("duration_ms", 0) if isinstance(batch_result, dict) else 0

    logs.append(f"[Agent] Batch processed {len(parsed)} resumes in {duration}ms via MCP.")

    return {
        "parsed_candidates": parsed,
        "logs": logs
    }


async def fetch_market_intelligence(state: MatchingState) -> Dict[str, Any]:
    """Node 4 (Multi-MCP Bonus): Retrieve salary and market benchmarks from secondary MCP server."""
    mcp = _CURRENT_MCP_MANAGER
    logs = list(state.get("logs", []))
    title = state.get("job_title", "Senior AI Engineer")

    logs.append(f"[MCP Market] Calling 'benchmark_market_role' for role: '{title}'...")
    benchmark_res = await mcp.call_tool(
        "market",
        "benchmark_market_role",
        {"role_title": title, "location": "US"}
    )

    benchmark = benchmark_res.get("benchmark", {}) if isinstance(benchmark_res, dict) else {}
    salary = benchmark.get("median_salary_usd", 0)
    demand = benchmark.get("market_demand", "Normal")

    logs.append(f"[Agent] Market Intelligence: Median Salary=${salary:,}, Demand='{demand}'.")

    return {
        "market_benchmark": benchmark,
        "logs": logs
    }


async def evaluate_and_rank(state: MatchingState) -> Dict[str, Any]:
    """Node 5: Score candidates, query skill weighting on secondary MCP, and store records in DB registry."""
    mcp = _CURRENT_MCP_MANAGER
    logs = list(state.get("logs", []))
    candidates = state.get("parsed_candidates", [])
    job_skills = set(state.get("required_skills", []))
    min_exp = state.get("min_experience_years", 4)
    job_title = state.get("job_title", "Senior AI Engineer")

    logs.append(f"[Agent] Scoring {len(candidates)} candidates against role requirements...")
    match_results = []

    for cand in candidates:
        name = cand.get("candidate_name", "Unknown")
        cand_skills = cand.get("skills", [])
        cand_exp = cand.get("experience_years", 0)

        # 1. Query market skill weight tool from secondary MCP server
        weight_res = await mcp.call_tool(
            "market",
            "calculate_skill_weight",
            {"role_title": job_title, "candidate_skills": cand_skills}
        )
        market_relevance = weight_res.get("relevance_score", 0.0) if isinstance(weight_res, dict) else 50.0
        matched_critical = weight_res.get("matched_critical_skills", []) if isinstance(weight_res, dict) else []
        missing_critical = weight_res.get("missing_critical_skills", []) if isinstance(weight_res, dict) else []

        # 2. Compute Direct Skill Alignment
        cand_set = set(s.lower() for s in cand_skills)
        matched_job_skills = list(job_skills.intersection(cand_set))
        direct_skill_pct = (len(matched_job_skills) / max(len(job_skills), 1)) * 100

        # 3. Experience Score (Max 100%)
        exp_score = min(100.0, (cand_exp / max(min_exp, 1)) * 100) if cand_exp > 0 else 40.0

        # 4. Composite Match Score
        composite_score = round(
            (0.50 * direct_skill_pct) + (0.30 * exp_score) + (0.20 * market_relevance),
            1
        )

        # 5. Recommendation tier
        if composite_score >= 80.0:
            recommendation = "Strongly Recommend"
        elif composite_score >= 65.0:
            recommendation = "Proceed to Interview"
        elif composite_score >= 45.0:
            recommendation = "Consider for Alternative Role"
        else:
            recommendation = "Reject"

        strengths = [f"Direct skills match: {', '.join(matched_job_skills[:3])}"] if matched_job_skills else ["General engineering background"]
        if cand_exp >= min_exp:
            strengths.append(f"Strong experience: {cand_exp} years (required: {min_exp})")

        gaps = [f"Missing critical skills: {', '.join(missing_critical[:3])}"] if missing_critical else []
        if cand_exp < min_exp and cand_exp > 0:
            gaps.append(f"Experience ({cand_exp} yrs) below threshold ({min_exp} yrs)")

        # 6. Store evaluation into candidate screening database via Secondary MCP Server tool
        store_res = await mcp.call_tool(
            "market",
            "store_candidate_evaluation",
            {
                "candidate_name": name,
                "role": job_title,
                "score": composite_score,
                "recommendation": recommendation,
                "strengths": strengths,
                "gaps": gaps
            }
        )
        registry_id = store_res.get("registry_id", "N/A") if isinstance(store_res, dict) else "N/A"

        match_results.append({
            "name": name,
            "filename": cand.get("filename"),
            "current_title": cand.get("title"),
            "email": cand.get("email"),
            "experience_years": cand_exp,
            "matched_skills": matched_job_skills,
            "missing_skills": list(job_skills - cand_set),
            "market_relevance_score": market_relevance,
            "composite_score": composite_score,
            "recommendation": recommendation,
            "registry_id": registry_id,
            "strengths": strengths,
            "gaps": gaps
        })

    # Sort descending by composite score
    match_results.sort(key=lambda x: x["composite_score"], reverse=True)
    logs.append(f"[Agent] Top candidate: {match_results[0]['name']} (Score: {match_results[0]['composite_score']}%)")

    return {
        "match_results": match_results,
        "logs": logs
    }


async def generate_and_save_report(state: MatchingState) -> Dict[str, Any]:
    """Node 6: Generate structured markdown scorecard and write to disk via MCP write_file tool."""
    mcp = _CURRENT_MCP_MANAGER
    logs = list(state.get("logs", []))
    job_title = state.get("job_title", "Senior AI Engineer")
    results = state.get("match_results", [])
    benchmark = state.get("market_benchmark", {})

    logs.append("[MCP Filesystem] Generating evaluation scorecard and writing reports via MCP...")

    # Build Markdown Report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = [
        f"# Candidate Screening & Matching Evaluation Report",
        f"**Target Role:** {job_title}  ",
        f"**Date Generated:** {timestamp}  ",
        f"**Architecture:** LangGraph Multi-MCP Agent (Filesystem MCP + Market Intelligence MCP)  ",
        f"**Market Benchmark:** Median Salary: ${benchmark.get('median_salary_usd', 0):,} | Demand: {benchmark.get('market_demand', 'N/A')}  ",
        "",
        "## Executive Summary Scorecard",
        "",
        "| Rank | Candidate | Match Score | Recommendation | Experience | Registry ID |",
        "| :--- | :--- | :---: | :--- | :---: | :--- |"
    ]

    for rank, cand in enumerate(results, 1):
        md.append(
            f"| {rank} | **{cand['name']}** | `{cand['composite_score']}%` | {cand['recommendation']} | {cand['experience_years']} yrs | `{cand['registry_id']}` |"
        )

    md.extend([
        "",
        "---",
        "",
        "## Detailed Candidate Breakdown",
        ""
    ])

    for cand in results:
        md.extend([
            f"### {cand['name']} — `{cand['composite_score']}%` ({cand['recommendation']})",
            f"- **Current Title:** {cand['current_title']}",
            f"- **Email / Contact:** {cand['email'] or 'Not provided'}",
            f"- **Source Resume File:** `{cand['filename']}`",
            f"- **Direct Skills Matched:** {', '.join(cand['matched_skills']) if cand['matched_skills'] else 'None'}",
            f"- **Identified Gaps:** {', '.join(cand['gaps']) if cand['gaps'] else 'No major gaps'}",
            f"- **Key Strengths:** {', '.join(cand['strengths'])}",
            ""
        ])

    markdown_report = "\n".join(md)

    # Write Markdown Report via MCP write_file tool
    output_md_path = "data/output/evaluation_report.md"
    await mcp.call_tool(
        "filesystem",
        "write_file",
        {
            "path": output_md_path,
            "content": markdown_report,
            "overwrite": True
        }
    )

    # Write JSON results via MCP write_file tool
    output_json_path = "data/output/screening_results.json"
    await mcp.call_tool(
        "filesystem",
        "write_file",
        {
            "path": output_json_path,
            "content": json.dumps(results, indent=2),
            "overwrite": True
        }
    )

    logs.append(f"[MCP Filesystem] Successfully saved reports to '{output_md_path}' and '{output_json_path}'.")

    return {
        "report_markdown": markdown_report,
        "saved_report_path": output_md_path,
        "status": "completed",
        "logs": logs
    }


# ============================================================================
# LangGraph Workflow Construction
# ============================================================================

def build_matching_graph():
    """Build and compile the LangGraph StateGraph workflow."""
    workflow = StateGraph(MatchingState)

    workflow.add_node("fetch_job_description", fetch_job_description)
    workflow.add_node("discover_candidates", discover_candidates)
    workflow.add_node("batch_ingest_candidates", batch_ingest_candidates)
    workflow.add_node("fetch_market_intelligence", fetch_market_intelligence)
    workflow.add_node("evaluate_and_rank", evaluate_and_rank)
    workflow.add_node("generate_and_save_report", generate_and_save_report)

    # Define State Machine Edges
    workflow.add_edge(START, "fetch_job_description")
    workflow.add_edge("fetch_job_description", "discover_candidates")
    workflow.add_edge("discover_candidates", "batch_ingest_candidates")
    workflow.add_edge("batch_ingest_candidates", "fetch_market_intelligence")
    workflow.add_edge("fetch_market_intelligence", "evaluate_and_rank")
    workflow.add_edge("evaluate_and_rank", "generate_and_save_report")
    workflow.add_edge("generate_and_save_report", END)

    return workflow.compile()


# ============================================================================
# Main Agent Runner
# ============================================================================

async def run_matching_agent(
    job_file: str = "job_senior_ai_engineer.txt",
    manager: Optional[MultiMCPManager] = None
) -> Dict[str, Any]:
    """Execute the complete LangGraph agent workflow connected to MCP servers."""
    global _CURRENT_MCP_MANAGER

    print("\n" + "=" * 70)
    print(">> STARTING LANGGRAPH MATCHING AGENT WITH MULTI-MCP INTEGRATION")
    print("=" * 70)

    async def _execute_with_manager(mcp_mgr: MultiMCPManager) -> Dict[str, Any]:
        global _CURRENT_MCP_MANAGER
        _CURRENT_MCP_MANAGER = mcp_mgr
        app_graph = build_matching_graph()

        initial_state: MatchingState = {
            "job_file": job_file,
            "job_title": "",
            "job_content": "",
            "required_skills": [],
            "min_experience_years": 0,
            "candidate_files": [],
            "parsed_candidates": [],
            "market_benchmark": {},
            "match_results": [],
            "report_markdown": "",
            "saved_report_path": "",
            "status": "started",
            "logs": []
        }

        # Execute LangGraph workflow
        final_state = await app_graph.ainvoke(initial_state)

        # Print Execution Transcript
        print("\n[*] AGENT EXECUTION LOGS:")
        for log in final_state.get("logs", []):
            print(f"  {log}")

        print("\n[+] FINAL CANDIDATE RANKINGS:")
        print(f"  {'Rank':<5} {'Candidate':<22} {'Score':<10} {'Recommendation':<26} {'Registry ID'}")
        print("  " + "-" * 75)
        for i, cand in enumerate(final_state.get("match_results", []), 1):
            print(
                f"  {i:<5} {cand['name']:<22} {cand['composite_score']:<10} {cand['recommendation']:<26} {cand['registry_id']}"
            )

        print("\n" + "=" * 70)
        print(f"[SUCCESS] Screening report successfully generated and saved via MCP:")
        print(f"   - Markdown: {final_state.get('saved_report_path')}")
        print(f"   - JSON:     data/output/screening_results.json")
        print("=" * 70 + "\n")

        return final_state

    if manager is not None:
        return await _execute_with_manager(manager)
    else:
        new_manager = MultiMCPManager()
        new_manager.register_server("filesystem", "filesystem_mcp_server.py")
        new_manager.register_server("market", "secondary_mcp_server.py")
        async with new_manager:
            return await _execute_with_manager(new_manager)


if __name__ == "__main__":
    job_param = "job_senior_ai_engineer.txt"
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        job_param = sys.argv[1]

    asyncio.run(run_matching_agent(job_param))
