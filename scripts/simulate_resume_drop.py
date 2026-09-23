"""
Simulate Resume Drop Utility
============================
Simulates dropping a new candidate resume into data/resumes/ to demonstrate
real-time event detection by the MCP watch_directory() capability.
"""

import sys
import time
import asyncio
from pathlib import Path

# Ensure root directory is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mcp_client import MCPClient

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SAMPLE_NEW_RESUME = """Candidate: Jordan Lake
Title: Lead AI Systems Architect
Email: jordan.lake@example.com
Phone: +1 (555) 789-0123
Location: San Francisco, CA

PROFESSIONAL SUMMARY
7+ years designing scalable generative AI systems, Model Context Protocol (MCP) servers,
and LangGraph multi-agent teams. Led migration of legacy toolkits to standardized MCP interfaces.

CORE SKILLS
- AI & Agents: LangGraph, LangChain, MCP (Model Context Protocol), FastMCP, PyTorch, Transformers
- Cloud & Infrastructure: AWS, GCP, Docker, Kubernetes, Vector DBs (Pinecone, Qdrant)
- Systems: Python, TypeScript, JSON-RPC, REST APIs, Microservices

EXPERIENCE
Principal AI Architect | Vertex Intelligence (2022 - Present)
- Built enterprise-grade MCP server infrastructure for autonomous coding agents.
- Reduced agent response latency by 55% using streaming tool execution.

EDUCATION
M.S. in Computer Science | Carnegie Mellon University (2019)
"""


async def main():
    print("=" * 70)
    print(">> MCP REAL-TIME DIRECTORY WATCHING SIMULATION")
    print("=" * 70)
    print("Connecting to Filesystem MCP Server over Stdio...")

    client = MCPClient("filesystem", "filesystem_mcp_server.py")
    await client.connect()

    target_dir = "data/resumes"
    simulated_filename = "resume_jordan_lake_lead_architect.txt"
    simulated_path = Path(target_dir) / simulated_filename

    # Clean up any leftover file
    if simulated_path.exists():
        simulated_path.unlink()

    print(f"\n[Step 1] Initializing watch on '{target_dir}' for 3.5 seconds...")

    import threading
    def drop_file_externally():
        time.sleep(1.0)
        print(f"\n[!] SIMULATING EXTERNAL CANDIDATE DROP: Dropping '{simulated_filename}'...")
        with open(simulated_path, "w", encoding="utf-8") as f:
            f.write(SAMPLE_NEW_RESUME)
        print(f"[!] File successfully written to disk in '{target_dir}'.")

    dropper_thread = threading.Thread(target=drop_file_externally)
    dropper_thread.start()

    watch_result = await client.call_tool(
        "watch_directory",
        {"path": target_dir, "duration_seconds": 3.0, "poll_interval": 0.3}
    )
    dropper_thread.join()

    print("\n[Step 2] Watch Window Concluded. Event Detection Results:")
    print(f"  - Status:              {watch_result.get('status')}")
    print(f"  - Duration Monitored:  {watch_result.get('observation_seconds')}s")
    print(f"  - Initial File Count:  {watch_result.get('initial_file_count')}")
    print(f"  - Final File Count:    {watch_result.get('final_file_count')}")
    print(f"  - Events Detected:     {watch_result.get('events_count')}")

    print("\n  [Detected Event Log]:")
    for event in watch_result.get("events", []):
        print(f"    * Event: [{event.get('event_type').upper()}] -> {event.get('filename')}")

    print(f"\n  [New Resumes Flagged for Agent]: {watch_result.get('new_resumes')}")

    # Prompt or clean up
    print("\n[Step 3] Cleaning up simulated resume...")
    if simulated_path.exists():
        simulated_path.unlink()
        print("  - Removed temporary test file.")

    await client.disconnect()
    print("\n" + "=" * 70)
    print(">> DIRECTORY WATCH SIMULATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
