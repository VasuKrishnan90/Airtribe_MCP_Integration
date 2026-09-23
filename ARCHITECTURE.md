# System Architecture & Protocol Specification

This document details the architectural design, protocol specifications, security sandboxing, and state machine interactions for the **Model Context Protocol (MCP) Integration** project.

---

## 1. High-Level System Architecture

The system decouples agentic reasoning from file system operations and market intelligence by introducing **Model Context Protocol (MCP)** servers communicating over standardized JSON-RPC 2.0 via `stdio` transport.

```mermaid
flowchart TB
    subgraph AgentLayer ["LangGraph Agent & Client Layer"]
        Agent["matching_agent.py<br/>(LangGraph StateGraph Engine)"]
        MultiMCP["mcp_client.py<br/>(MultiMCPManager & Stdio Client)"]
        Agent <-->|Invokes Tools & Reads Resources| MultiMCP
    end

    subgraph MCPLayer ["MCP Server Layer (JSON-RPC 2.0 Stdio Subprocesses)"]
        FSServer["filesystem_mcp_server.py<br/>(Part A: Filesystem MCP Server)"]
        MarketServer["secondary_mcp_server.py<br/>(Part B: Market Intelligence MCP Server)"]
        MultiMCP <-->|JSON-RPC 2.0 over Stdio| FSServer
        MultiMCP <-->|JSON-RPC 2.0 over Stdio| MarketServer
    end

    subgraph Capabilities ["Server Capabilities & Tool Registry"]
        FSTools["Tools:<br/>• read_file()<br/>• write_file()<br/>• list_directory()<br/>• search_files()<br/>• get_file_info()<br/>• watch_directory()<br/>• batch_process()"]
        FSResources["Resources:<br/>• resume://{filename}<br/>• job://{filename}"]
        MarketTools["Bonus Tools:<br/>• benchmark_market_role()<br/>• calculate_skill_weight()<br/>• store_candidate_evaluation()"]
        MarketResources["Resources:<br/>• market://benchmark/{role}<br/>• registry://candidate/{name}"]

        FSServer --> FSTools
        FSServer --> FSResources
        MarketServer --> MarketTools
        MarketServer --> MarketResources
    end

    subgraph StorageLayer ["Sandboxed Local Storage"]
        Resumes["data/resumes/<br/>(Candidate Resumes)"]
        Jobs["data/jobs/<br/>(Job Descriptions)"]
        Output["data/output/<br/>(Scorecards & Registry DB)"]

        FSTools <-->|Sandboxed I/O| Resumes
        FSTools <-->|Sandboxed I/O| Jobs
        FSTools <-->|Sandboxed I/O| Output
        MarketTools <-->|JSON Registry I/O| Output
    end
```

---

## 2. State Machine & Agent ↔ MCP Workflow

The LangGraph agent is orchestrated as a directed acyclic state graph (`StateGraph(MatchingState)`). Every single data read, parse, query, and write operation is executed through MCP client tool/resource calls.

```mermaid
sequenceDiagram
    autonumber
    participant Agent as LangGraph Agent (matching_agent.py)
    participant Client as MultiMCPManager (mcp_client.py)
    participant FSMCP as Filesystem MCP Server
    participant MarketMCP as Market Intelligence MCP Server
    participant Disk as Sandboxed File Storage

    Note over Agent,MarketMCP: Phase 1: Handshake & Discovery
    Agent->>Client: Initialize MultiMCP Session
    Client->>FSMCP: initialize + list_tools + list_resources
    FSMCP-->>Client: Tool list (7 tools) & Resource URIs
    Client->>MarketMCP: initialize + list_tools
    MarketMCP-->>Client: Tool list (3 bonus tools)

    Note over Agent,FSMCP: Phase 2: Job Specification Ingestion
    Agent->>Client: read_resource("job://job_senior_ai_engineer.txt")
    Client->>FSMCP: resources/read {"uri": "job://job_senior_ai_engineer.txt"}
    FSMCP->>Disk: Read sandboxed job file
    Disk-->>FSMCP: Raw Job Spec
    FSMCP-->>Client: Resource contents
    Client-->>Agent: Parsed Role Criteria (4+ yrs, 11 critical skills)

    Note over Agent,FSMCP: Phase 3: Resume Discovery & Batch Ingestion
    Agent->>Client: call_tool("filesystem", "list_directory", {"path": "data/resumes"})
    Client->>FSMCP: tools/call list_directory
    FSMCP-->>Client: Discovered 5 resume files
    Client-->>Agent: Candidate files list
    Agent->>Client: call_tool("filesystem", "batch_process", {"directory_path": "data/resumes"})
    Client->>FSMCP: tools/call batch_process
    FSMCP->>Disk: Concurrently reads & parses 5 files
    Disk-->>FSMCP: Content
    FSMCP-->>Client: Structured Candidate Objects (parsed in ~2ms)
    Client-->>Agent: 5 parsed candidate records

    Note over Agent,MarketMCP: Phase 4: Market Intelligence & Benchmarking (Bonus)
    Agent->>Client: call_tool("market", "benchmark_market_role", {"role_title": "Senior AI Engineer"})
    Client->>MarketMCP: tools/call benchmark_market_role
    MarketMCP-->>Client: Median Salary: $185,000, Demand: Very High
    Client-->>Agent: Market Benchmark Data

    Note over Agent,MarketMCP: Phase 5: Candidate Scoring & Database Registry
    loop For each candidate (1..5)
        Agent->>Client: call_tool("market", "calculate_skill_weight", candidate_skills)
        Client->>MarketMCP: tools/call calculate_skill_weight
        MarketMCP-->>Client: Relevance Score + Matched/Missing Core Skills
        Client-->>Agent: Skill weighting score
        Agent->>Agent: Compute Composite Match Score & Recommendation
        Agent->>Client: call_tool("market", "store_candidate_evaluation", record)
        Client->>MarketMCP: tools/call store_candidate_evaluation
        MarketMCP->>Disk: Persist to data/output/screening_registry.json
        MarketMCP-->>Client: Registry ID (e.g. REC-1790173215-alex_r)
        Client-->>Agent: Confirmation
    end

    Note over Agent,FSMCP: Phase 6: Report Generation & Persistence
    Agent->>Client: call_tool("filesystem", "write_file", {"path": "data/output/evaluation_report.md", "content": ...})
    Client->>FSMCP: tools/call write_file (Markdown)
    FSMCP->>Disk: Write evaluation_report.md
    FSMCP-->>Client: Success confirmation
    Agent->>Client: call_tool("filesystem", "write_file", {"path": "data/output/screening_results.json", "content": ...})
    Client->>FSMCP: tools/call write_file (JSON)
    FSMCP->>Disk: Write screening_results.json
    FSMCP-->>Client: Success confirmation
    Client-->>Agent: Workflow Completed Successfully
```

---

## 3. Protocol Specifications: JSON-RPC 2.0

All communication follows the Anthropic Model Context Protocol specification over stdio.

### 3.1 Tool Call Example: `batch_process`

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "batch_process",
    "arguments": {
      "directory_path": "data/resumes",
      "action": "parse_resume"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"status\":\"success\",\"total_files\":5,\"processed_count\":5,\"duration_ms\":3.62,\"results\":[...]}"
      }
    ],
    "isError": false
  }
}
```

### 3.2 Resource Read Example: `job://job_senior_ai_engineer.txt`

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "resources/read",
  "params": {
    "uri": "job://job_senior_ai_engineer.txt"
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "contents": [
      {
        "uri": "job://job_senior_ai_engineer.txt",
        "mimeType": "text/plain",
        "text": "Job Title: Senior AI / Agent Systems Engineer\n..."
      }
    ]
  }
}
```

---

## 4. Security Sandboxing Model

The Filesystem MCP Server implements strict boundary validation:
1. **Root Enclosure**: All paths passed to any tool or resource are resolved via `sanitize_path()`.
2. **Path Traversal Defense**: The resolved path must be relative to `SANDBOX_ROOT`. If a path contains `../` attempting to escape the project workspace, a `PermissionError` is thrown and mapped to an MCP tool error.
3. **Extension Whitelist**: Only allowed formats (`.txt`, `.md`, `.json`, `.pdf`, `.csv`) are processed.
4. **File Size Limits**: File size threshold prevents denial-of-service / memory exhaustion.
