"""Typer entrypoint for the inferflow CLI."""

from __future__ import annotations

import json
import pathlib
from typing import Any

import questionary
import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from inferflow_cli.io import (
    check_prereqs,
    discover_pipelines,
    discover_steps,
    discover_tasks,
    ensure_local_env,
    load_inferflow_config,
    write_default_inferflow_config,
)

console = Console()
app = typer.Typer(help="Inferflow developer CLI")
task_app = typer.Typer(help="Manage tasks")
step_app = typer.Typer(help="Manage steps")
pipeline_app = typer.Typer(help="Manage pipelines")

app.add_typer(task_app, name="task")
app.add_typer(step_app, name="step")
app.add_typer(pipeline_app, name="pipeline")


def _repo_root() -> pathlib.Path:
    """Resolve the current repository root.

    :returns: Nearest parent directory containing tasks/ and steps/.
    """
    current = pathlib.Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "tasks").is_dir() and (candidate / "steps").is_dir():
            return candidate
    return current


def _render_header(title: str) -> None:
    """Render a consistent Rich header panel.

    :param title: Header title text.
    """
    console.print(Panel.fit(f"[bold cyan]{title}[/bold cyan]"))


@app.command()
def init(non_interactive: bool = typer.Option(False, help="Skip interactive prompts.")) -> None:
    """Initialize or validate inferflow.yaml in the current repository."""
    repo_root = _repo_root()
    config_path = repo_root / "inferflow.yaml"

    _render_header("Inferflow Init")

    if not config_path.exists():
        if non_interactive:
            project_name = repo_root.name
            registry = "ghcr.io/jgallego9"
        else:
            project_name = (
                questionary.text("Project name", default=repo_root.name).ask()
                or repo_root.name
            )
            registry = (
                questionary.text("Registry", default="ghcr.io/jgallego9").ask()
                or "ghcr.io/jgallego9"
            )

        write_default_inferflow_config(repo_root, project_name, registry)
        ensure_local_env(repo_root)
        console.print("[green]Created inferflow.yaml and .env[/green]")
    else:
        config = load_inferflow_config(repo_root)
        prereqs = check_prereqs()

        table = Table(title="Environment prerequisites")
        table.add_column("Check")
        table.add_column("Status")

        for name, ok in prereqs.items():
            table.add_row(name, "[green]ok[/green]" if ok else "[red]missing[/red]")

        table.add_row("config", f"[green]{config.name}[/green]")
        console.print(table)

    console.print(
        Panel(
            "Next steps:\n"
            "1) inferflow task list\n"
            "2) inferflow step list\n"
            "3) inferflow pipeline list",
            title="Ready",
        )
    )


@task_app.command("list")
def task_list() -> None:
    """List all registered tasks from tasks/*/schema.json."""
    repo_root = _repo_root()
    tasks = discover_tasks(repo_root)

    table = Table(title="Tasks")
    table.add_column("Task")
    table.add_column("Description")

    for task in tasks:
        table.add_row(task.name, task.description)

    console.print(table)


@step_app.command("list")
def step_list() -> None:
    """List all steps discovered from steps/*/step.yaml."""
    repo_root = _repo_root()
    steps = discover_steps(repo_root)

    table = Table(title="Steps")
    table.add_column("Step")
    table.add_column("Task")
    table.add_column("Version")

    for step in steps:
        table.add_row(step.name, step.task, step.version)

    console.print(table)


@pipeline_app.command("list")
def pipeline_list() -> None:
    """List all pipeline definitions from pipelines/*/pipeline.yaml."""
    repo_root = _repo_root()
    pipelines = discover_pipelines(repo_root)

    table = Table(title="Pipelines")
    table.add_column("Pipeline")
    table.add_column("Steps")
    table.add_column("Description")

    for pipeline in pipelines:
        table.add_row(pipeline.name, str(len(pipeline.steps)), pipeline.description)

    console.print(table)


def _required_inputs_for_task(tasks_root: pathlib.Path, task_name: str) -> set[str]:
    """Get required input tensor names for a task.

    :param tasks_root: Task root directory.
    :param task_name: Task identifier.
    :returns: Set of required input tensor names.
    """
    schema_path = tasks_root / task_name / "schema.json"
    if not schema_path.exists():
        return set()

    raw = json.loads(schema_path.read_text(encoding="utf-8"))
    inputs = raw.get("inputs", [])
    return {str(item["name"]) for item in inputs if item.get("required", False)}


def _outputs_for_task(tasks_root: pathlib.Path, task_name: str) -> set[str]:
    """Get output tensor names for a task.

    :param tasks_root: Task root directory.
    :param task_name: Task identifier.
    :returns: Set of output tensor names.
    """
    schema_path = tasks_root / task_name / "schema.json"
    if not schema_path.exists():
        return set()

    raw = json.loads(schema_path.read_text(encoding="utf-8"))
    outputs = raw.get("outputs", [])
    return {str(item["name"]) for item in outputs}


@pipeline_app.command("validate")
def pipeline_validate(name: str = typer.Argument(..., help="Pipeline directory name.")) -> None:
    """Validate task compatibility across sequential pipeline steps."""
    repo_root = _repo_root()
    pipeline_path = repo_root / "pipelines" / name / "pipeline.yaml"

    if not pipeline_path.exists():
        raise typer.BadParameter(f"Pipeline not found: {name}")

    raw = yaml.safe_load(pipeline_path.read_text(encoding="utf-8"))
    steps: list[dict[str, Any]] = list(raw.get("steps", []))

    tasks_root = repo_root / "tasks"
    issues: list[str] = []

    for i in range(len(steps) - 1):
        left = steps[i]
        right = steps[i + 1]

        left_task = str(left.get("task", ""))
        right_task = str(right.get("task", ""))

        produced = _outputs_for_task(tasks_root, left_task)
        required = _required_inputs_for_task(tasks_root, right_task)

        missing = required - produced
        if missing:
            issues.append(
                f"{left.get('id', left_task)} -> {right.get('id', right_task)} missing: {sorted(missing)}"
            )

    if issues:
        console.print("[red]Validation failed[/red]")
        for item in issues:
            console.print(f" - {item}")
        raise typer.Exit(code=1)

    console.print(f"[green]Pipeline '{name}' is valid[/green]")


if __name__ == "__main__":
    app()
