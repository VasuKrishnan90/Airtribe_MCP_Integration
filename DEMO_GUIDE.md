# 5–6 Minute Demo Video Recording Guide

This guide provides a turnkey, timed walkthrough script for recording the assignment submission video demonstrating the **Model Context Protocol (MCP) Filesystem Server**, the **Refactored LangGraph Matching Agent**, and the **Multi-MCP Bonus Integration**.

---

## 🕒 Timing & Agenda Breakdown (Target: 5:00 – 6:00 Minutes)

| Time | Phase | Focus Area | Command / Screen |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:45** | **1. Introduction** | Problem Statement, MCP Motivation & Architecture Overview | Show `ARCHITECTURE.md` diagram |
| **0:45 - 2:00** | **2. Part A: Filesystem MCP Server** | Tools, Resources, `watch_directory()`, `batch_process()`, Sandbox | `python filesystem_mcp_server.py --self-test` & `python scripts/simulate_resume_drop.py` |
| **2:00 - 3:00** | **3. Part B Bonus: Secondary MCP Server** | Market Intelligence, Salary Benchmarks, DB Registry | `python secondary_mcp_server.py --self-test` |
| **3:00 - 4:45** | **4. Part B: LangGraph Agent Execution** | End-to-end execution of `matching_agent.py` through Multi-MCP | `python matching_agent.py` |
| **4:45 - 5:30** | **5. Output Artifact Verification** | Markdown Scorecard, JSON results, Registry DB | Inspect `data/output/evaluation_report.md` |
| **5:30 - 6:00** | **6. Test Suite & Conclusion** | Automated pytest suite (15/15 passing) & Closing | `pytest tests/ -v` |

---

## 🎬 Step-by-Step Recording Script & Talking Points

### Phase 1: Introduction & Architecture (0:00 – 0:45)
**Screen Setup**: Show VS Code with `ARCHITECTURE.md` open.
**Talking Points**:
> *"Hello! Today I will demonstrate our implementation of Anthropic's Model Context Protocol (MCP). In Milestone 1, our resume matching agent interacted directly with the local file system using ad-hoc file functions. In this project, we have completely decoupled the agent from the file system by building a standardized, JSON-RPC 2.0 compliant MCP Server layer.*
>
> *Our architecture consists of:
> 1. A primary **Filesystem MCP Server** exposing tools, resources, and advanced capabilities like batch processing and directory watching.
> 2. A bonus **Market Intelligence MCP Server** providing salary benchmarks and candidate registry storage.
> 3. A refactored **LangGraph Matching Agent** that interacts strictly through our MCP client without any direct file I/O."*

---

### Phase 2: Part A — Filesystem MCP Server & New Capabilities (0:45 – 2:00)
**Terminal Command 1**:
```powershell
.\.venv\Scripts\python filesystem_mcp_server.py --self-test
```
**Talking Points**:
> *"Here we run the self-test for `filesystem_mcp_server.py`. Notice:
> - All Milestone 1 tools are converted to standardized MCP tools: `read_file`, `write_file`, `list_directory`, `search_files`, and `get_file_info`.
> - Resumes and Job Descriptions are exposed as discoverable MCP resources via `resume://` and `job://` URI schemes.
> - High-throughput `batch_process()` parsed all 5 resumes concurrently in less than 2 milliseconds!
> - Strict Sandboxing: When an attempt is made to escape the project folder via path traversal (`../../secret.txt`), access is denied."*

**Terminal Command 2**:
```powershell
.\.venv\Scripts\python scripts/simulate_resume_drop.py
```
**Talking Points**:
> *"Now let's demonstrate the new `watch_directory()` capability. When an applicant drops a new resume into `data/resumes`, our MCP server observes the directory in real time, flags the `[CREATED]` event, and returns the newly discovered resume file ready for agent processing."*

---

### Phase 3: Part B Bonus — Multi-MCP Secondary Server (2:00 – 3:00)
**Terminal Command**:
```powershell
.\.venv\Scripts\python secondary_mcp_server.py --self-test
```
**Talking Points**:
> *"To fulfill the Multi-MCP Bonus, we built a secondary MCP Server: `secondary_mcp_server.py`. This server specializes in Market Intelligence and Candidate Registry persistence:
> - `benchmark_market_role`: Fetches market salary expectations ($185,000 for Senior AI Engineer) and skill taxonomies.
> - `calculate_skill_weight`: Computes market relevance scores.
> - `store_candidate_evaluation`: Stores structured candidate evaluation records into a persistent registry database."*

---

### Phase 4: Part B — Refactored LangGraph Matching Agent (3:00 – 4:45)
**Terminal Command**:
```powershell
.\.venv\Scripts\python matching_agent.py
```
**Talking Points**:
> *"Now let's run our refactored LangGraph Matching Agent (`matching_agent.py`). Notice the terminal execution transcript:
> 1. **Zero direct file I/O**: The agent never calls Python `open()` or `os.listdir()`.
> 2. Node 1 reads the job specification via MCP resource `job://job_senior_ai_engineer.txt`.
> 3. Node 2 discovers candidate resumes using MCP `list_directory`.
> 4. Node 3 executes `batch_process` to ingest all resumes in a single MCP call.
> 5. Node 4 queries our secondary MCP server for live salary benchmarks and market demand.
> 6. Node 5 calculates composite match scores, weights skills against market data, and registers candidates in the database.
> 7. Node 6 saves the evaluation scorecard and JSON results using the MCP `write_file` tool."*

Point out the ranking:
> *"Alex Rivers ranks #1 with 88.0% ('Strongly Recommend'), while Frontend Engineer David Kim receives 30.0% ('Reject'), demonstrating accurate candidate differentiation."*

---

### Phase 5: Output Artifact Verification (4:45 – 5:30)
**Screen Setup**: Open `data/output/evaluation_report.md` in Preview mode.
**Talking Points**:
> *"Here is the generated `evaluation_report.md` written purely through MCP:
> - Clean Executive Summary Scorecard with ranks, composite match scores, and database Registry IDs.
> - Detailed candidate breakdowns highlighting direct skills matched, identified gaps, and strengths.
> - Structured JSON output is also stored in `data/output/screening_results.json` and `screening_registry.json` for external HR system integration."*

---

### Phase 6: Automated Test Suite & Wrap-Up (5:30 – 6:00)
**Terminal Command**:
```powershell
.\.venv\Scripts\python -m pytest tests/ -v
```
**Talking Points**:
> *"Finally, we run our automated test suite covering unit tests, protocol conformance, sandboxing security, batching, directory watching, and full agent integration.
> All 15 tests pass with 100% success!
>
> In summary, we have built a complete, production-ready, JSON-RPC 2.0 compliant MCP architecture with LangGraph agent integration and Multi-MCP capabilities. Thank you!"*

---

## 💡 Quick Video Presentation Pro-Tips
1. **Interactive Demo Runner**: If you prefer a guided script that steps through each phase automatically, you can simply run:
   ```powershell
   .\.venv\Scripts\python scripts/run_demo.py
   ```
   Press `[Enter]` to proceed between each phase!
2. **Resolution**: Record at 1080p (1920x1080) with a readable terminal font size (14–16pt).
3. **Pacing**: Speak at a steady, confident pace; pause briefly when terminal outputs appear so evaluators can read the logs.
