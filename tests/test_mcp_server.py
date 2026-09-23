"""
Tests for Part A: Filesystem MCP Server
=======================================
Verifies MCP protocol conformance, tool interfaces, resource discovery,
and sandboxing security constraints.
"""

import os
import pytest
from pathlib import Path
from filesystem_mcp_server import (
    read_file,
    write_file,
    list_directory,
    search_files,
    get_file_info,
    get_resume_resource,
    get_job_resource,
    sanitize_path,
    SANDBOX_ROOT
)


class TestFilesystemMCPServer:
    """Unit and integration test cases for Filesystem MCP tools and resources."""

    def test_list_directory(self):
        """Verify list_directory returns resumes with valid metadata."""
        entries = list_directory("data/resumes")
        assert isinstance(entries, list)
        assert len(entries) >= 5
        filenames = [e["name"] for e in entries]
        assert "alex_rivers_ai_engineer.txt" in filenames
        assert "marcus_vance_devops.json" in filenames
        for entry in entries:
            assert "path" in entry
            assert "type" in entry
            assert "size_bytes" in entry

    def test_read_file_success(self):
        """Verify reading a text resume returns non-empty string."""
        content = read_file("data/resumes/alex_rivers_ai_engineer.txt")
        assert isinstance(content, str)
        assert "Alex Rivers" in content
        assert "LangGraph" in content

    def test_read_file_not_found(self):
        """Verify FileNotFoundError is raised when file does not exist."""
        with pytest.raises(FileNotFoundError):
            read_file("data/resumes/non_existent_candidate.txt")

    def test_write_file_and_verify(self):
        """Verify write_file creates file and returns success metadata."""
        test_path = "data/output/pytest_test_artifact.txt"
        test_content = "MCP standardized write test payload"
        result = write_file(test_path, test_content, overwrite=True)
        assert result["status"] == "success"
        assert result["bytes_written"] == len(test_content)

        # Read back to verify
        read_back = read_file(test_path)
        assert read_back == test_content

    def test_get_file_info(self):
        """Verify get_file_info metadata fields."""
        info = get_file_info("data/resumes/alex_rivers_ai_engineer.txt")
        assert info["exists"] is True
        assert info["is_file"] is True
        assert info["extension"] == ".txt"
        assert info["line_count"] > 10
        assert info["size_bytes"] > 0

    def test_search_files(self):
        """Verify search_files finds matching lines and files."""
        matches = search_files("data/resumes", query="LangGraph", pattern="*.txt")
        assert isinstance(matches, list)
        assert len(matches) >= 2
        file_paths = [m["path"] for m in matches]
        assert any("alex_rivers" in p for p in file_paths)

    def test_resume_resource(self):
        """Verify resume:// resource resolver."""
        content = get_resume_resource("alex_rivers_ai_engineer.txt")
        assert "Alex Rivers" in content
        assert "Stanford University" in content

    def test_job_resource(self):
        """Verify job:// resource resolver."""
        content = get_job_resource("job_senior_ai_engineer.txt")
        assert "Senior AI / Agent Systems Engineer" in content

    def test_sandbox_security_traversal_blocked(self):
        """Verify that directory traversal attacks outside sandbox are blocked."""
        with pytest.raises(PermissionError) as exc_info:
            sanitize_path("../../windows/win.ini")
        assert "Access denied" in str(exc_info.value)

        with pytest.raises(PermissionError):
            read_file("../../../secret_keys.env")
