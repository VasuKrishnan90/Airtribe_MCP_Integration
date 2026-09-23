"""
Tests for New MCP-Specific Capabilities: batch_process() and watch_directory()
=============================================================================
"""

import time
import pytest
from pathlib import Path
from filesystem_mcp_server import batch_process, watch_directory, write_file


class TestBatchAndWatchCapabilities:
    """Test suite verifying high-throughput batching and real-time directory monitoring."""

    def test_batch_process_all_resumes(self):
        """Verify batch_process successfully parses all resumes in data/resumes."""
        result = batch_process(directory_path="data/resumes", action="parse_resume")

        assert result["status"] == "success"
        assert result["total_files"] >= 5
        assert result["processed_count"] == result["total_files"]
        assert result["error_count"] == 0
        assert "duration_ms" in result
        assert result["duration_ms"] < 500.0  # High-throughput constraint

        # Verify candidate records
        names = [c["candidate_name"] for c in result["results"]]
        assert "Alex Rivers" in names
        assert "Priya Sharma" in names
        assert "Sarah Chen" in names
        assert "Marcus Vance" in names

        # Verify parsed skills
        alex = next(c for c in result["results"] if c["candidate_name"] == "Alex Rivers")
        assert "python" in alex["skills"]
        assert "langgraph" in alex["skills"]
        assert "mcp" in alex["skills"]
        assert alex["experience_years"] == 6

    def test_batch_process_specific_files(self):
        """Verify batch_process handles targeted file path subsets."""
        target_files = [
            "data/resumes/alex_rivers_ai_engineer.txt",
            "data/resumes/david_kim_frontend.txt"
        ]
        result = batch_process(file_paths=target_files)

        assert result["processed_count"] == 2
        names = [c["candidate_name"] for c in result["results"]]
        assert "Alex Rivers" in names
        assert "David Kim" in names

    def test_watch_directory_snapshot(self):
        """Verify watch_directory returns valid instant status when duration is 0."""
        result = watch_directory("data/resumes", duration_seconds=0)

        assert result["status"] == "completed"
        assert result["initial_file_count"] >= 5
        assert result["events_count"] == 0

    def test_watch_directory_detects_new_file_drop(self):
        """
        Verify watch_directory detects newly dropped resumes during observation window.
        Simulates an incoming candidate drop in background while watching.
        """
        import threading

        test_dropped_filename = "resume_test_simulated_drop.txt"
        test_dropped_path = f"data/resumes/{test_dropped_filename}"

        def drop_resume_after_delay():
            time.sleep(0.4)
            write_file(
                test_dropped_path,
                "Candidate: Jordan Lake\nTitle: AI Engineer\nSkills: Python, MCP\n5 years experience"
            )

        # Launch background drop thread
        drop_thread = threading.Thread(target=drop_resume_after_delay)
        drop_thread.start()

        # Watch directory for 1.5 seconds
        watch_result = watch_directory("data/resumes", duration_seconds=1.5, poll_interval=0.2)
        drop_thread.join()

        # Cleanup test file
        test_file = Path(test_dropped_path)
        if test_file.exists():
            test_file.unlink()

        # Assertions
        assert watch_result["status"] == "completed"
        created_events = [e for e in watch_result["events"] if e["event_type"] == "created"]
        assert len(created_events) >= 1
        assert any(e["filename"] == test_dropped_filename for e in created_events)
        assert test_dropped_filename in watch_result["new_resumes"]
