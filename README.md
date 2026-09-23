# Airtribe — Model Context Protocol (MCP) Integration

Production-ready implementation of Anthropic's **Model Context Protocol (MCP)**, converting custom local file system tools into standardized JSON-RPC 2.0 compliant MCP servers and refactoring a **LangGraph Matching Agent** to communicate purely over MCP client interfaces.

---

## 🎯 Project Overview & Deliverables

### Part A: Filesystem MCP Server Implementation (50%)
- **`filesystem_mcp_server.py`**:
  - Full JSON-RPC 2.0 protocol compliance via Anthropic's official Python MCP SDK (`mcp`).
  - Converts all Milestone 1 file tools into standardized MCP tools: `read_file`, `write_file`, `list_directory`, `search_files`, `get_file_info`.
  - Exposes candidate resumes and job specifications as discoverable MCP Resources (`resume://{filename}`, `job://{filename}`).
  - **New MCP Capabilities**:
    - `watch_directory(path, duration_seconds, poll_interval)`: Real-time file system observer detecting added/modified resumes.
    - `batch_process(directory_path, action)`: High-performance batch ingestion parsing multiple resumes concurrently in <5ms.
  - **Security Sandboxing**: Strict path traversal prevention ensuring operations cannot escape the workspace root.

### Part B: Agent Refactoring & Multi-MCP Integration (30% + Bonus)
- **`matching_agent.py`**:
  - Built with **LangGraph StateGraph**.
  - **Zero Direct File I/O**: Completely eliminated `open()`, `os.listdir()`, etc. in agent nodes; all interactions route through MCP.
  - **Multi-MCP Bonus Integration**: Connects to a secondary server (`secondary_mcp_server.py`) to fetch live market salary benchmarks, skill taxonomy weights, and persist candidate evaluations to a database registry (`screening_registry.json`).
  - Evaluates candidates, computes composite match scores (0–100%), and writes markdown scorecard reports and structured JSON summaries via MCP.

### Verification & Demonstration
- **Automated Test Suite**: 15 comprehensive unit and integration tests across protocol, batching, directory watching, sandboxing, and agent workflow (`15/15 passed`).
- **`scripts/run_demo.py`**: Interactive CLI runner walking through the entire 5–6 minute demonstration.
- **`scripts/simulate_resume_drop.py`**: Live demonstration of real-time resume event detection.
- **`ARCHITECTURE.md`**: Complete system architecture, JSON-RPC 2.0 specification, and Mermaid state machine diagrams.
- **`DEMO_GUIDE.md`**: Step-by-step 5–6 minute video recording script with talking points.

---

## 📂 Repository Structure

```
d:\Airtribe - MCP integration\
├── .venv/                         # Python 3.14 virtual environment
├── config.yaml                    # Server configuration & sandbox rules
├── requirements.txt               # Dependencies (mcp, langgraph, pytest, etc.)
├── README.md                      # Project documentation
├── ARCHITECTURE.md                # System design & protocol specifications
├── DEMO_GUIDE.md                  # 5-6 minute video recording script
│
├── filesystem_mcp_server.py       # [Part A] Primary Filesystem MCP Server
├── secondary_mcp_server.py        # [Part B Bonus] Market Intelligence & Registry MCP Server
├── mcp_client.py                  # Standard MCP Stdio Client & MultiMCPManager
├── matching_agent.py              # [Part B] Refactored LangGraph Matching Agent
│
├── data/
│   ├── resumes/                   # Sample candidate resumes (Alex Rivers, Priya Sharma, etc.)
│   ├── jobs/                      # Sample Job Descriptions (Senior AI Engineer, Full Stack)
│   └── output/                    # Generated evaluation reports, JSON results & DB registry
│
├── tests/
│   ├── test_mcp_server.py         # Tests for tools, resources, and sandboxing
│   ├── test_batch_and_watch.py    # Tests for watch_directory() and batch_process()
│   └── test_matching_agent.py     # End-to-end LangGraph agent workflow test
│
└── scripts/
    ├── run_demo.py                # Interactive 5-minute video demo runner
    └── simulate_resume_drop.py    # Live directory watch demonstration
```

---

## 🚀 Quickstart & Usage

### 1. Environment Setup
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run MCP Server Self-Tests
Verify that both MCP servers conform to protocol standards:
```powershell
# Test Primary Filesystem MCP Server
python filesystem_mcp_server.py --self-test

# Test Secondary Market Intelligence MCP Server (Bonus)
python secondary_mcp_server.py --self-test
```

### 3. Run the Refactored LangGraph Matching Agent
Execute the end-to-end agent workflow purely through MCP servers:
```powershell
python matching_agent.py
```
*Evaluates candidate resumes against `job_senior_ai_engineer.txt`, fetches salary benchmarks, scores candidates, stores records in the database registry, and generates `data/output/evaluation_report.md`.*

To evaluate against a different job role:
```powershell
python matching_agent.py job_fullstack_engineer.txt
```

### 4. Demonstrate Real-Time Directory Watching
Simulate an applicant dropping a new resume while the MCP watcher is active:
```powershell
python scripts/simulate_resume_drop.py
```

### 5. Run the Automated Demo for the Submission Video
Run the guided interactive presentation:
```powershell
# Interactive mode (press Enter between phases)
python scripts/run_demo.py

# Or automated mode
python scripts/run_demo.py --auto
```

### 6. Run Test Suite
```powershell
pytest tests/ -v
```

---

## 📊 Sample Agent Output Scorecard

When executed on `job_senior_ai_engineer.txt`, the agent outputs:

| Rank | Candidate | Match Score | Recommendation | Experience | Registry ID |
| :--- | :--- | :---: | :--- | :---: | :--- |
| 1 | **Alex Rivers** | `88.0%` | Strongly Recommend | 6 yrs | `REC-1790173215-alex_r` |
| 2 | **Priya Sharma** | `85.2%` | Strongly Recommend | 5 yrs | `REC-1790173215-priya_` |
| 3 | **Sarah Chen** | `69.9%` | Proceed to Interview | 4 yrs | `REC-1790173215-sarah_` |
| 4 | **Marcus Vance** | `33.0%` | Reject | 0 yrs | `REC-1790173215-marcus` |
| 5 | **David Kim** | `30.0%` | Reject | 7 yrs | `REC-1790173215-david_` |

All scorecards and candidate evaluations are saved in:
- Markdown Scorecard: [`data/output/evaluation_report.md`](file:///d:/Airtribe%20-%20MCP%20integration/data/output/evaluation_report.md)
- Structured JSON: [`data/output/screening_results.json`](file:///d:/Airtribe%20-%20MCP%20integration/data/output/screening_results.json)
- Candidate DB Registry: [`data/output/screening_registry.json`](file:///d:/Airtribe%20-%20MCP%20integration/data/output/screening_registry.json)
