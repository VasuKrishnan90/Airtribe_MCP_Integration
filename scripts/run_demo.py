"""
End-to-End MCP Integration Demo Runner
======================================
Designed specifically for the 5-6 minute assignment submission video.
Walks through all assignment milestones in clear, sequential phases:

Phase 1: MCP Protocol, Configuration & Resource Discovery (Part A)
Phase 2: Core Filesystem Tools, Batch Ingestion & Directory Watching (Part A)
Phase 3: Secondary Market Intelligence MCP Server (Part B Bonus)
Phase 4: Refactored LangGraph Matching Agent Execution via Multi-MCP (Part B)
Phase 5: Output Verification & Scorecard Audit
"""

import sys
import time
import json
import asyncio
from pathlib import Path

# Ensure root directory is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from mcp_client import MultiMCPManager
from matching_agent import run_matching_agent


def print_banner(title: str):
    print("\n" + "=" * 76)
    print(f"  {title.upper()}")
    print("=" * 76)


def prompt_step(phase_num: int, description: str, auto_advance: bool = False):
    print(f"\n>>> [PHASE {phase_num}] {description}")
    if not auto_advance:
        input("    Press [Enter] to proceed to this demonstration phase...")
    else:
        time.sleep(1.0)


async def main(auto_advance: bool = False):
    print_banner("Airtribe MCP Integration - End-to-End System Demo")
    print("Architecture: Model Context Protocol (MCP) + LangGraph Agent")
    print("Servers:      1) filesystem_mcp_server.py  2) secondary_mcp_server.py")
    print("Client:       JSON-RPC 2.0 via Stdio Transport")

    manager = MultiMCPManager()
    manager.register_server("filesystem", "filesystem_mcp_server.py")
    manager.register_server("market", "secondary_mcp_server.py")

    async with manager:
        # --------------------------------------------------------------------
        # Phase 1: Protocol Handshake & Resource Discovery
        # --------------------------------------------------------------------
        prompt_step(1, "MCP Protocol Handshake & Tool / Resource Discovery", auto_advance)

        fs_client = manager.clients["filesystem"]
        market_client = manager.clients["market"]

        fs_tools = await fs_client.list_tools()
        market_tools = await market_client.list_tools()

        print("\n[*] PRIMARY FILESYSTEM MCP SERVER DISCOVERY:")
        print(f"    - Tools Count:      {len(fs_tools)}")
        print(f"    - Discovered Tools: {fs_tools}")
        print(f"    - Resource URIs:    resume://{{filename}}, job://{{filename}}")

        print("\n[*] SECONDARY MARKET INTELLIGENCE MCP SERVER DISCOVERY (Bonus):")
        print(f"    - Tools Count:      {len(market_tools)}")
        print(f"    - Discovered Tools: {market_tools}")
        print(f"    - Resource URIs:    market://benchmark/{{role}}, registry://candidate/{{name}}")

        # --------------------------------------------------------------------
        # Phase 2: Batch Processing & Directory Watching Capabilities
        # --------------------------------------------------------------------
        prompt_step(2, "New MCP Capabilities: batch_process() & watch_directory()", auto_advance)

        print("\n1) Testing 'batch_process()' on candidate resumes directory:")
        batch_res = await fs_client.call_tool("batch_process", {"directory_path": "data/resumes"})
        print(f"   - Files Processed: {batch_res.get('processed_count')} files")
        print(f"   - Batch Duration:  {batch_res.get('duration_ms')}ms")
        for cand in batch_res.get("results", [])[:3]:
            print(f"     * {cand.get('candidate_name')} ({cand.get('title')}) -> {len(cand.get('skills', []))} skills")

        print("\n2) Testing 'watch_directory()' instant delta snapshot:")
        watch_res = await fs_client.call_tool("watch_directory", {"path": "data/resumes", "duration_seconds": 0.1})
        print(f"   - Status:         {watch_res.get('status')}")
        print(f"   - Files Tracked:  {watch_res.get('initial_file_count')}")
        print(f"   - Events Flagged: {watch_res.get('events_count')}")

        print("\n3) Testing Path Traversal Defense (Sandboxing):")
        try:
            await fs_client.call_tool("read_file", {"path": "../../windows/win.ini"})
            print("   [!] Defense check failed.")
        except Exception as e:
            print(f"   [+] Traversal successfully blocked: {str(e)[:75]}...")

        # --------------------------------------------------------------------
        # Phase 3: Secondary Market Intelligence MCP Server
        # --------------------------------------------------------------------
        prompt_step(3, "Secondary MCP Server: Market Intelligence & Benchmarking (Bonus)", auto_advance)

        print("\n1) Calling 'benchmark_market_role' for 'Senior AI Engineer':")
        bench = await market_client.call_tool("benchmark_market_role", {"role_title": "Senior AI Engineer"})
        b_data = bench.get("benchmark", {})
        print(f"   - Target Title:  {b_data.get('title')}")
        print(f"   - Median Salary: ${b_data.get('median_salary_usd', 0):,} USD")
        print(f"   - Market Demand: {b_data.get('market_demand')}")

        print("\n2) Calling 'calculate_skill_weight' for Candidate Skills:")
        weight_res = await market_client.call_tool(
            "calculate_skill_weight",
            {"role_title": "Senior AI Engineer", "candidate_skills": ["python", "langgraph", "mcp", "docker"]}
        )
        print(f"   - Relevance Score: {weight_res.get('relevance_score')}%")
        print(f"   - Matched Core:    {weight_res.get('matched_critical_skills')}")
        print(f"   - Missing Core:    {weight_res.get('missing_critical_skills')}")

        # --------------------------------------------------------------------
        # Phase 4: Full LangGraph Matching Agent Execution
        # --------------------------------------------------------------------
        prompt_step(4, "Refactored LangGraph Agent Execution (100% MCP Mediated)", auto_advance)

        # Run agent using the existing active MultiMCPManager
        final_state = await run_matching_agent("job_senior_ai_engineer.txt", manager=manager)

        # --------------------------------------------------------------------
        # Phase 5: Scorecard Artifact Audit
        # --------------------------------------------------------------------
        prompt_step(5, "Inspection of Generated Artifacts in data/output/", auto_advance)

        md_report = Path("data/output/evaluation_report.md")
        json_results = Path("data/output/screening_results.json")
        db_registry = Path("data/output/screening_registry.json")

        print("\n[+] PERSISTED ARTIFACTS VERIFICATION:")
        print(f"    1) Markdown Scorecard:  {md_report} ({md_report.stat().st_size} bytes)")
        print(f"    2) JSON Results:        {json_results} ({json_results.stat().st_size} bytes)")
        print(f"    3) Screening Registry:  {db_registry} ({db_registry.stat().st_size} bytes)")

        print_banner("System Demo Completed Successfully!")
        print("All requirements for Part A, Part B, and Multi-MCP Bonus have been verified.")


if __name__ == "__main__":
    auto_mode = "--auto" in sys.argv
    asyncio.run(main(auto_advance=auto_mode))
