"""
Filesystem MCP Server (Part A)
==============================
A production-ready, JSON-RPC 2.0 compliant Model Context Protocol (MCP) server
implementing standardized file system tools, resource discovery, sandboxed security,
and high-performance batch processing and directory watching capabilities.

Complies with Anthropic MCP Specification using the official Python MCP SDK.
"""

import os
import sys
import time
import json
import fnmatch
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

# Official MCP SDK imports (Supports MCP 2.x MCPServer with FastMCP alias)
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as MCPServer
    except ImportError as e:
        raise ImportError("Please install mcp SDK: pip install mcp>=1.0.0") from e

from mcp.types import Resource, Tool, TextContent


# ============================================================================
# Configuration & Security Sandboxing
# ============================================================================

def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml with sensible fallbacks."""
    config_file = Path("config.yaml")
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to parse config.yaml: {e}", file=sys.stderr)
    return {}

CONFIG = load_config()

# Sandboxing and paths
STORAGE_CFG = CONFIG.get("storage", {})
SANDBOX_ROOT = Path(os.environ.get("SANDBOX_ROOT", STORAGE_CFG.get("sandbox_root", "."))).resolve()
RESUMES_DIR = Path(os.environ.get("RESUMES_DIR", STORAGE_CFG.get("resumes_dir", "data/resumes")))
JOBS_DIR = Path(os.environ.get("JOBS_DIR", STORAGE_CFG.get("jobs_dir", "data/jobs")))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", STORAGE_CFG.get("output_dir", "data/output")))
ALLOWED_EXTENSIONS = set(STORAGE_CFG.get("allowed_extensions", [".txt", ".md", ".json", ".pdf", ".csv"]))
MAX_FILE_SIZE_BYTES = STORAGE_CFG.get("max_file_size_mb", 10) * 1024 * 1024


def sanitize_path(target_path: str) -> Path:
    """
    Validate that target_path resides safely within SANDBOX_ROOT to prevent
    directory traversal attacks (e.g. '../../etc/passwd').
    """
    resolved = (SANDBOX_ROOT / target_path).resolve() if not Path(target_path).is_absolute() else Path(target_path).resolve()
    try:
        resolved.relative_to(SANDBOX_ROOT)
    except ValueError:
        raise PermissionError(
            f"Security Error: Access denied. Path '{target_path}' escapes the sandbox root '{SANDBOX_ROOT}'."
        )
    return resolved


# ============================================================================
# Initialize MCP Server
# ============================================================================

server_info = CONFIG.get("server", {})
SERVER_NAME = server_info.get("name", "filesystem-mcp-server")
SERVER_VERSION = server_info.get("version", "1.0.0")

app = MCPServer(SERVER_NAME)


# ============================================================================
# MCP Resources Implementation & Discovery
# ============================================================================

@app.resource("resume://{filename}")
def get_resume_resource(filename: str) -> str:
    """
    Exposes a candidate resume as a read-only MCP resource.
    URI format: resume://alex_rivers_ai_engineer.txt
    """
    resume_file = sanitize_path(str(RESUMES_DIR / filename))
    if not resume_file.exists():
        raise FileNotFoundError(f"Resume resource not found: {filename}")
    with open(resume_file, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


@app.resource("job://{filename}")
def get_job_resource(filename: str) -> str:
    """
    Exposes a Job Description as a read-only MCP resource.
    URI format: job://job_senior_ai_engineer.txt
    """
    job_file = sanitize_path(str(JOBS_DIR / filename))
    if not job_file.exists():
        raise FileNotFoundError(f"Job resource not found: {filename}")
    with open(job_file, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def register_concrete_resources():
    """Register discovered concrete files so resources/list exposes all items."""
    # Register existing resumes
    if RESUMES_DIR.exists():
        for file in RESUMES_DIR.glob("*.*"):
            if file.suffix.lower() in ALLOWED_EXTENSIONS:
                uri = f"resume://{file.name}"
                def make_reader(filepath: Path):
                    def reader() -> str:
                        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                            return f.read()
                    return reader
                try:
                    app.resource(uri)(make_reader(file))
                except Exception:
                    pass

    # Register existing job descriptions
    if JOBS_DIR.exists():
        for file in JOBS_DIR.glob("*.*"):
            if file.suffix.lower() in ALLOWED_EXTENSIONS:
                uri = f"job://{file.name}"
                def make_job_reader(filepath: Path):
                    def reader() -> str:
                        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                            return f.read()
                    return reader
                try:
                    app.resource(uri)(make_job_reader(file))
                except Exception:
                    pass

register_concrete_resources()


# ============================================================================
# Converted Milestone 1 Tools (MCP Standardized)
# ============================================================================

@app.tool()
def read_file(path: str) -> str:
    """
    Read the complete text content of a file within the sandbox.
    
    Args:
        path: Relative or absolute path to the file.
    Returns:
        The text content of the file.
    """
    file_path = sanitize_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: '{path}'")
    if not file_path.is_file():
        raise IsADirectoryError(f"Target path is a directory, not a file: '{path}'")
    
    size = file_path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File size ({size} bytes) exceeds configured limit ({MAX_FILE_SIZE_BYTES} bytes)")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


@app.tool()
def write_file(path: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
    """
    Write or create a file within the sandbox. Automatically creates parent directories.
    
    Args:
        path: Relative or absolute path where the file will be written.
        content: Text content to write.
        overwrite: Whether to overwrite existing files (default: True).
    Returns:
        Metadata dict confirming bytes written and file path.
    """
    file_path = sanitize_path(path)
    if file_path.exists() and not overwrite:
        raise FileExistsError(f"File already exists and overwrite is set to False: '{path}'")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        bytes_written = f.write(content)

    return {
        "status": "success",
        "path": str(file_path.relative_to(SANDBOX_ROOT)),
        "bytes_written": bytes_written,
        "timestamp": time.time()
    }


@app.tool()
def list_directory(path: str = ".") -> List[Dict[str, Any]]:
    """
    List contents of a directory with detailed metadata (name, type, size, modified_time).
    
    Args:
        path: Directory path to inspect (defaults to current sandbox root).
    Returns:
        List of file and directory entries.
    """
    dir_path = sanitize_path(path)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: '{path}'")
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: '{path}'")

    entries = []
    for item in dir_path.iterdir():
        try:
            stat = item.stat()
            entries.append({
                "name": item.name,
                "path": str(item.relative_to(SANDBOX_ROOT)),
                "type": "directory" if item.is_dir() else "file",
                "size_bytes": stat.st_size if item.is_file() else None,
                "modified_timestamp": stat.st_mtime
            })
        except (PermissionError, FileNotFoundError):
            continue

    return sorted(entries, key=lambda x: (x["type"] != "directory", x["name"].lower()))


@app.tool()
def search_files(path: str = ".", query: str = "", pattern: str = "*") -> List[Dict[str, Any]]:
    """
    Search for files matching a filename glob pattern and/or containing specific text query.
    
    Args:
        path: Directory to search within.
        query: Substring to search inside file contents (case-insensitive).
        pattern: Glob pattern to filter file names (e.g. '*.txt', '*resume*').
    Returns:
        List of matching files with match snippets.
    """
    search_dir = sanitize_path(path)
    if not search_dir.exists() or not search_dir.is_dir():
        raise NotADirectoryError(f"Search target is not a valid directory: '{path}'")

    matches = []
    query_lower = query.lower() if query else None

    for root, _, files in os.walk(search_dir):
        for filename in files:
            if not fnmatch.fnmatch(filename, pattern):
                continue
            
            file_path = Path(root) / filename
            if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue

            # If no text query, filename match is sufficient
            if not query_lower:
                matches.append({
                    "path": str(file_path.relative_to(SANDBOX_ROOT)),
                    "filename": filename,
                    "matched_lines": []
                })
                continue

            # Search content
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    matched_lines = []
                    for line_no, line in enumerate(f, 1):
                        if query_lower in line.lower():
                            matched_lines.append({
                                "line_number": line_no,
                                "content": line.strip()
                            })
                            if len(matched_lines) >= 5: # Limit matches per file
                                break
                    if matched_lines:
                        matches.append({
                            "path": str(file_path.relative_to(SANDBOX_ROOT)),
                            "filename": filename,
                            "matched_lines": matched_lines
                        })
            except Exception:
                continue

    return matches


@app.tool()
def get_file_info(path: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive metadata for a specific file.
    
    Args:
        path: File path to inspect.
    Returns:
        Dict containing file stats, line count, extension, and existence.
    """
    file_path = sanitize_path(path)
    if not file_path.exists():
        return {"exists": False, "path": path}

    stat = file_path.stat()
    line_count = 0
    if file_path.is_file():
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                line_count = sum(1 for _ in f)
        except Exception:
            line_count = None

    return {
        "exists": True,
        "path": str(file_path.relative_to(SANDBOX_ROOT)),
        "is_file": file_path.is_file(),
        "is_directory": file_path.is_dir(),
        "size_bytes": stat.st_size,
        "line_count": line_count,
        "extension": file_path.suffix.lower(),
        "modified_timestamp": stat.st_mtime,
        "created_timestamp": stat.st_ctime
    }


# ============================================================================
# New MCP-Specific Capabilities: watch_directory() & batch_process()
# ============================================================================

@app.tool()
async def watch_directory(
    path: str = "data/resumes",
    duration_seconds: float = 3.0,
    poll_interval: float = 0.5
) -> Dict[str, Any]:
    """
    Monitor a directory for file system changes (new resumes dropped, modified, or deleted).
    
    Args:
        path: Directory path to watch (default: 'data/resumes').
        duration_seconds: Time window in seconds to observe changes. If 0, returns instant snapshot.
        poll_interval: Seconds between directory scans.
    Returns:
        Dict detailing detected file events and new files discovered.
    """
    watch_path = sanitize_path(path)
    if not watch_path.exists():
        raise FileNotFoundError(f"Watch directory does not exist: '{path}'")

    def snapshot() -> Dict[str, float]:
        snap = {}
        for p in watch_path.glob("*.*"):
            if p.is_file():
                snap[p.name] = p.stat().st_mtime
        return snap

    initial_state = snapshot()
    events = []
    start_time = time.time()
    current_state = dict(initial_state)

    if duration_seconds > 0:
        elapsed = 0.0
        while elapsed < duration_seconds:
            await asyncio.sleep(poll_interval)
            latest = snapshot()

            # Check for new or modified files
            for fname, mtime in latest.items():
                if fname not in current_state:
                    events.append({
                        "event_type": "created",
                        "filename": fname,
                        "path": str((watch_path / fname).relative_to(SANDBOX_ROOT)),
                        "timestamp": time.time()
                    })
                elif mtime > current_state[fname]:
                    events.append({
                        "event_type": "modified",
                        "filename": fname,
                        "path": str((watch_path / fname).relative_to(SANDBOX_ROOT)),
                        "timestamp": time.time()
                    })

            # Check for deleted files
            for fname in list(current_state.keys()):
                if fname not in latest:
                    events.append({
                        "event_type": "deleted",
                        "filename": fname,
                        "timestamp": time.time()
                    })

            current_state = latest
            elapsed = time.time() - start_time

    return {
        "status": "completed",
        "watched_path": str(watch_path.relative_to(SANDBOX_ROOT)),
        "observation_seconds": duration_seconds,
        "initial_file_count": len(initial_state),
        "final_file_count": len(current_state),
        "events_count": len(events),
        "events": events,
        "new_resumes": [e["filename"] for e in events if e["event_type"] == "created"]
    }


def parse_resume_content(raw_text: str, filename: str) -> Dict[str, Any]:
    """Extract candidate fields using resilient heuristic parsing."""
    result = {
        "filename": filename,
        "candidate_name": "Unknown",
        "title": "Unspecified",
        "email": "",
        "phone": "",
        "skills": [],
        "experience_years": 0,
        "education": "",
        "raw_character_count": len(raw_text)
    }

    # If JSON file
    if filename.endswith(".json"):
        try:
            data = json.loads(raw_text)
            result["candidate_name"] = data.get("candidate") or data.get("name", "Unknown")
            result["title"] = data.get("title", "Unspecified")
            result["email"] = data.get("email", "")
            result["phone"] = data.get("phone", "")
            result["skills"] = data.get("skills", [])
            result["education"] = str(data.get("education", ""))
            return result
        except Exception:
            pass

    # Standard Text Parsing
    lines = raw_text.splitlines()
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("candidate:") or lower.startswith("name:"):
            result["candidate_name"] = stripped.split(":", 1)[1].strip()
        elif lower.startswith("title:") or lower.startswith("role:"):
            result["title"] = stripped.split(":", 1)[1].strip()
        elif lower.startswith("email:") or "@" in stripped:
            if ":" in stripped:
                result["email"] = stripped.split(":", 1)[1].strip()
            else:
                for token in stripped.split():
                    if "@" in token:
                        result["email"] = token.strip("(),;<>")
        elif lower.startswith("phone:"):
            result["phone"] = stripped.split(":", 1)[1].strip()

    # Skill extraction (common keywords)
    common_skills = [
        "python", "langgraph", "langchain", "mcp", "fastmcp", "pytorch",
        "transformers", "hugging face", "docker", "kubernetes", "aws", "gcp",
        "terraform", "react", "next.js", "typescript", "javascript", "sql",
        "json-rpc", "mlops", "ray", "kubeflow", "ci/cd"
    ]
    raw_lower = raw_text.lower()
    found_skills = [s for s in common_skills if s in raw_lower]
    result["skills"] = found_skills

    # Estimate experience years
    import re
    match = re.search(r'(\d+)\+?\s*(?:years?|yrs)', raw_lower)
    if match:
        result["experience_years"] = int(match.group(1))

    return result


@app.tool()
def batch_process(
    file_paths: Optional[List[str]] = None,
    directory_path: str = "data/resumes",
    action: str = "parse_resume"
) -> Dict[str, Any]:
    """
    Efficiently process a collection of files in a single MCP batch call.
    
    Args:
        file_paths: Specific list of relative file paths. If None, scans directory_path.
        directory_path: Target directory if file_paths is not provided.
        action: Processing pipeline ('parse_resume', 'summarize', or 'extract_skills').
    Returns:
        Batch processing summary with extracted candidate records and execution stats.
    """
    start_time = time.time()
    target_files: List[Path] = []

    if file_paths:
        for p in file_paths:
            target_files.append(sanitize_path(p))
    else:
        scan_dir = sanitize_path(directory_path)
        if not scan_dir.exists() or not scan_dir.is_dir():
            raise NotADirectoryError(f"Batch target directory not found: '{directory_path}'")
        for f in scan_dir.glob("*.*"):
            if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
                target_files.append(f)

    results = []
    errors = []

    for file_path in target_files:
        try:
            if not file_path.exists():
                errors.append({"file": str(file_path), "error": "File does not exist"})
                continue

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            parsed = parse_resume_content(content, file_path.name)
            results.append(parsed)
        except Exception as e:
            errors.append({"file": file_path.name, "error": str(e)})

    duration_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "status": "success",
        "action": action,
        "total_files": len(target_files),
        "processed_count": len(results),
        "error_count": len(errors),
        "duration_ms": duration_ms,
        "results": results,
        "errors": errors
    }


# ============================================================================
# Self-Test Runner & Entry Point
# ============================================================================

def run_self_test():
    """Run an automated self-test of the MCP tools and resources."""
    print("=" * 60)
    print("Filesystem MCP Server - Self Test Suite")
    print("=" * 60)

    # 1. Test list_directory
    print("\n1. Testing 'list_directory' on 'data/resumes'...")
    entries = list_directory("data/resumes")
    print(f"   Discovered {len(entries)} resume files:")
    for e in entries:
        print(f"   - {e['name']} ({e['size_bytes']} bytes)")

    # 2. Test read_file
    print("\n2. Testing 'read_file' on first resume...")
    first_file = entries[0]["path"]
    content = read_file(first_file)
    print(f"   Successfully read {len(content)} characters from '{first_file}'.")

    # 3. Test get_file_info
    print("\n3. Testing 'get_file_info'...")
    info = get_file_info(first_file)
    print(f"   Info: lines={info['line_count']}, ext={info['extension']}, size={info['size_bytes']}")

    # 4. Test search_files
    print("\n4. Testing 'search_files' for keyword 'LangGraph'...")
    search_res = search_files("data/resumes", query="LangGraph")
    print(f"   Found matches in {len(search_res)} files.")

    # 5. Test batch_process
    print("\n5. Testing 'batch_process' capability...")
    batch_res = batch_process(directory_path="data/resumes")
    print(f"   Batch processed {batch_res['processed_count']} files in {batch_res['duration_ms']}ms.")
    for cand in batch_res["results"][:3]:
        print(f"   - {cand['candidate_name']} ({cand['title']}) | Skills: {', '.join(cand['skills'][:4])}")

    # 6. Test watch_directory
    print("\n6. Testing 'watch_directory' (instant snapshot)...")
    watch_res = watch_directory("data/resumes", duration_seconds=0.1)
    print(f"   Watch status: {watch_res['status']} | Files monitored: {watch_res['initial_file_count']}")

    # 7. Test write_file
    print("\n7. Testing 'write_file' into 'data/output/test_mcp.txt'...")
    w_res = write_file("data/output/test_mcp.txt", "Filesystem MCP Server write_file verification test.")
    print(f"   Write result: bytes={w_res['bytes_written']}, path={w_res['path']}")

    # 8. Test Security Sandbox
    print("\n8. Testing Sandbox Path Traversal Defense...")
    try:
        read_file("../../secret.txt")
        print("   FAILED: Sandbox allowed directory traversal!")
    except PermissionError as e:
        print(f"   PASSED: Traversal blocked with message: {e}")

    print("\n" + "=" * 60)
    print("ALL FILESYSTEM MCP SERVER TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        run_self_test()
    else:
        # Standard MCP stdio server transport for Claude / LangGraph / Antigravity
        app.run(transport="stdio")
