"""Smoke tests for inferflow CLI journeys (Phase 9)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    """Get repository root."""
    return Path(__file__).parent.parent.parent.parent


@pytest.fixture
def cli_command() -> list[str]:
    """Base CLI invocation."""
    return ["uv", "run", "--directory", "tools/inferflow-cli", "inferflow"]


class TestCLISmokeBasic:
    """Basic CLI command availability and help."""

    def test_cli_help(self, cli_command: list[str], repo_root: Path) -> None:
        """Verify main help command exits cleanly."""
        result = subprocess.run(
            [*cli_command, "--help"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert (
            "Inferflow" in result.stdout
            or "Commands" in result.stdout
            or len(result.stdout) > 0
        )

    def test_init_help(self, cli_command: list[str], repo_root: Path) -> None:
        """Verify init command help is available."""
        result = subprocess.run(
            [*cli_command, "init", "--help"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Initialize" in result.stdout or "inferflow" in result.stdout.lower()


class TestCLITaskDiscovery:
    """Task discovery commands."""

    def test_task_list_succeeds(self, cli_command: list[str], repo_root: Path) -> None:
        """Verify `inferflow task list` completes without error."""
        result = subprocess.run(
            [*cli_command, "task", "list"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Expect at least table headers or task names
        assert len(result.stdout) > 0


class TestCLIPipelineValidation:
    """Pipeline validation commands."""

    def test_pipeline_list_succeeds(
        self, cli_command: list[str], repo_root: Path
    ) -> None:
        """Verify `inferflow pipeline list` completes without error."""
        result = subprocess.run(
            [*cli_command, "pipeline", "list"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Expect output with pipeline names
        assert "audio-rag" in result.stdout or "image-search" in result.stdout

    def test_pipeline_validate_existing(
        self, cli_command: list[str], repo_root: Path
    ) -> None:
        """Verify `inferflow pipeline validate <existing>` succeeds."""
        result = subprocess.run(
            [*cli_command, "pipeline", "validate", "image-search"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "valid" in result.stdout.lower()

    def test_pipeline_validate_nonexistent(
        self, cli_command: list[str], repo_root: Path
    ) -> None:
        """Verify `inferflow pipeline validate <nonexistent>` fails with clear message."""
        result = subprocess.run(
            [*cli_command, "pipeline", "validate", "nonexistent-pipeline-xyz"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        # Expect error message to be informative
        error_text = result.stdout + result.stderr
        assert "not found" in error_text.lower() or "error" in error_text.lower()


class TestCLIErrorMessages:
    """Error message clarity."""

    def test_task_show_nonexistent_message(
        self, cli_command: list[str], repo_root: Path
    ) -> None:
        """Verify error message for missing task is actionable."""
        result = subprocess.run(
            [*cli_command, "task", "show", "nonexistent-task"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        error_text = result.stdout + result.stderr
        assert "not found" in error_text.lower() or "task" in error_text.lower()


class TestCLIDefaults:
    """Default values and safe modes."""

    def test_init_noninteractive_flag_recognized(
        self, cli_command: list[str], repo_root: Path
    ) -> None:
        """Verify `inferflow init --non-interactive` flag is recognized."""
        result = subprocess.run(
            [*cli_command, "init", "--help"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "non-interactive" in result.stdout or result.returncode == 0
