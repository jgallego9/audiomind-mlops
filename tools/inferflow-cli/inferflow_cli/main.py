"""Typer entrypoint for the inferflow CLI."""

from __future__ import annotations

import json
import pathlib
import subprocess
import time
from typing import Any
from urllib.parse import urlparse

import httpx
import questionary
import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
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

DEFAULT_API_URL = "http://localhost:8000"

console = Console()
app = typer.Typer(help="Inferflow developer CLI")
task_app = typer.Typer(help="Manage tasks")
step_app = typer.Typer(help="Manage steps")
pipeline_app = typer.Typer(help="Manage pipelines")
models_app = typer.Typer(help="Manage model cache and readiness")
job_app = typer.Typer(help="Inspect detached jobs")

app.add_typer(task_app, name="task")
app.add_typer(step_app, name="step")
app.add_typer(pipeline_app, name="pipeline")
app.add_typer(models_app, name="models")
app.add_typer(job_app, name="job")


def _repo_root() -> pathlib.Path:
    """Resolve the current repository root.

    :returns: Nearest parent directory containing `tasks/` and `steps/`.
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


def _exit_with_error(message: str, code: int = 1) -> None:
    """Print an error and terminate.

    :param message: Human-readable error message.
    :param code: Process exit code.
    """
    console.print(f"[red]{message}[/red]")
    raise typer.Exit(code=code)


def _run_command(command: list[str], cwd: pathlib.Path | None = None) -> str:
    """Run a shell command and return stdout.

    :param command: Command tokens.
    :param cwd: Optional working directory.
    :returns: Captured stdout text.
    :raises typer.Exit: If command fails.
    """
    proc = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or "unknown error"
        _exit_with_error(f"Command failed: {' '.join(command)}\n{stderr}")
    return proc.stdout.strip()


def _load_yaml_file(path: pathlib.Path) -> dict[str, Any]:
    """Load YAML as a dictionary.

    :param path: YAML file path.
    :returns: Parsed dictionary.
    :raises typer.Exit: If parsing fails.
    """
    try:
        return dict(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    except Exception as exc:  # pragma: no cover
        _exit_with_error(f"Invalid YAML in {path}: {exc}")


def _default_dirs(repo_root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    """Return tasks/steps/pipelines directories.

    :param repo_root: Repository root.
    :returns: Tuple of `(tasks_root, steps_root, pipelines_root)`.
    """
    try:
        config = load_inferflow_config(repo_root)
        return (
            repo_root / config.tasks_dir,
            repo_root / config.steps_dir,
            repo_root / config.pipelines_dir,
        )
    except Exception:
        return (repo_root / "tasks", repo_root / "steps", repo_root / "pipelines")


def _read_json_file(path: pathlib.Path) -> dict[str, Any]:
    """Read JSON file as dictionary.

    :param path: JSON file path.
    :returns: Parsed object.
    """
    try:
        return dict(json.loads(path.read_text(encoding="utf-8")))
    except Exception as exc:  # pragma: no cover
        _exit_with_error(f"Invalid JSON in {path}: {exc}")


def _required_inputs_for_task(tasks_root: pathlib.Path, task_name: str) -> set[str]:
    """Get required input tensor names for a task.

    :param tasks_root: Task root directory.
    :param task_name: Task identifier.
    :returns: Set of required input tensor names.
    """
    schema_path = tasks_root / task_name / "schema.json"
    if not schema_path.exists():
        return set()

    raw = _read_json_file(schema_path)
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

    raw = _read_json_file(schema_path)
    outputs = raw.get("outputs", [])
    return {str(item["name"]) for item in outputs}


def _infer_step_endpoint(step_name: str) -> str:
    """Infer a default local endpoint for a step.

    :param step_name: Step name.
    :returns: URL base.
    """
    return f"http://{step_name}:8000"


def _pipeline_file(repo_root: pathlib.Path, name: str) -> pathlib.Path:
    """Return pipeline.yaml path for a pipeline name.

    :param repo_root: Repository root.
    :param name: Pipeline directory name.
    :returns: Absolute path to pipeline definition.
    """
    _, _, pipelines_root = _default_dirs(repo_root)
    return pipelines_root / name / "pipeline.yaml"


def _pipeline_step_defs(repo_root: pathlib.Path, name: str) -> list[dict[str, Any]]:
    """Load pipeline step definitions.

    :param repo_root: Repository root.
    :param name: Pipeline directory name.
    :returns: List of step dictionaries.
    """
    pipeline_path = _pipeline_file(repo_root, name)
    if not pipeline_path.exists():
        _exit_with_error(f"Pipeline not found: {name}")
    raw = _load_yaml_file(pipeline_path)
    return list(raw.get("steps", []))


def _request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Issue an HTTP request and parse JSON response.

    :param method: HTTP method.
    :param url: Request URL.
    :param payload: Optional JSON body.
    :returns: Parsed JSON dictionary.
    :raises typer.Exit: If request fails.
    """
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.request(method, url, json=payload)
            response.raise_for_status()
            body = response.json()
            return body if isinstance(body, dict) else {"data": body}
    except Exception as exc:
        _exit_with_error(f"HTTP request failed for {url}: {exc}")


def _parse_json_input(input_value: str) -> dict[str, Any]:
    """Parse CLI `--input` payload.

    Supports inline JSON or `@path.json`.

    :param input_value: User-provided input.
    :returns: Parsed JSON object.
    """
    if input_value.startswith("@"):
        source = pathlib.Path(input_value[1:])
        if not source.exists():
            _exit_with_error(f"Input file not found: {source}")
        if source.suffix.lower() == ".json":
            return _read_json_file(source)
        return {"input_path": str(source)}

    try:
        parsed = json.loads(input_value)
        if isinstance(parsed, dict):
            return parsed
        _exit_with_error("Input JSON must be an object.")
    except json.JSONDecodeError:
        return {"raw_input": input_value}


def _bump_semver(version: str, kind: str) -> str:
    """Bump semantic version string.

    :param version: Current version (`MAJOR.MINOR.PATCH`).
    :param kind: One of `patch`, `minor`, `major`.
    :returns: Bumped version.
    """
    parts = version.strip().split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        _exit_with_error(f"Invalid semver version: {version}")
    major, minor, patch = map(int, parts)
    if kind == "patch":
        patch += 1
    elif kind == "minor":
        minor += 1
        patch = 0
    else:
        major += 1
        minor = 0
        patch = 0
    return f"{major}.{minor}.{patch}"


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


@task_app.command("show")
def task_show(name: str = typer.Argument(..., help="Task name.")) -> None:
    """Show full schema and compatible steps for a task.

    :param name: Task name.
    """
    repo_root = _repo_root()
    tasks_root, _, _ = _default_dirs(repo_root)
    schema_path = tasks_root / name / "schema.json"
    if not schema_path.exists():
        _exit_with_error(f"Task not found: {name}")

    schema = _read_json_file(schema_path)
    steps = [step for step in discover_steps(repo_root) if step.task == name]

    console.print(Syntax(json.dumps(schema, indent=2), "json"))

    table = Table(title="Compatible steps")
    table.add_column("Step")
    table.add_column("Version")
    if steps:
        for step in steps:
            table.add_row(step.name, step.version)
    else:
        table.add_row("-", "-")
    console.print(table)


@task_app.command("new")
def task_new(
    name: str = typer.Argument(..., help="New task name."),
    non_interactive: bool = typer.Option(False, help="Use defaults without prompts."),
) -> None:
    """Create a new task schema under tasks/<name>/schema.json.

    :param name: New task name.
    :param non_interactive: Disable prompts and use defaults.
    """
    repo_root = _repo_root()
    tasks_root, _, _ = _default_dirs(repo_root)
    task_dir = tasks_root / name
    schema_path = task_dir / "schema.json"
    if schema_path.exists():
        _exit_with_error(f"Task already exists: {name}")

    description = f"Task contract for {name}"
    input_name = "input"
    output_name = "output"

    if not non_interactive:
        description = questionary.text("Task description", default=description).ask() or description
        input_name = questionary.text("Primary input tensor name", default=input_name).ask() or input_name
        output_name = questionary.text("Primary output tensor name", default=output_name).ask() or output_name

    task_dir.mkdir(parents=True, exist_ok=True)
    schema = {
        "task": name,
        "version": "1.0",
        "description": description,
        "inputs": [
            {
                "name": input_name,
                "datatype": "BYTES",
                "shape": [1],
                "description": "Primary input",
                "required": True,
            }
        ],
        "outputs": [
            {
                "name": output_name,
                "datatype": "BYTES",
                "shape": [1],
                "description": "Primary output",
            }
        ],
    }
    schema_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    console.print(f"[green]Created {schema_path}[/green]")


@step_app.command("list")
def step_list() -> None:
    """List all steps discovered from steps/*/step.yaml."""
    repo_root = _repo_root()
    steps = discover_steps(repo_root)

    table = Table(title="Steps")
    table.add_column("Step")
    table.add_column("Task")
    table.add_column("Version")
    table.add_column("Built")

    for step in steps:
        step_root = step.path.parent
        has_image = (step_root / "Dockerfile").exists()
        table.add_row(
            step.name,
            step.task,
            step.version,
            "yes" if has_image else "no",
        )

    console.print(table)


@step_app.command("new")
def step_new(
    task: str = typer.Argument(..., help="Task name."),
    implementation: str = typer.Argument(..., help="Implementation suffix."),
) -> None:
    """Scaffold a new step package from task schema.

    :param task: Task name.
    :param implementation: Step implementation suffix.
    """
    repo_root = _repo_root()
    tasks_root, steps_root, _ = _default_dirs(repo_root)
    schema_path = tasks_root / task / "schema.json"
    if not schema_path.exists():
        _exit_with_error(f"Task schema not found: {schema_path}")

    schema = _read_json_file(schema_path)
    step_name = f"{task}-{implementation}"
    step_root = steps_root / step_name
    app_root = step_root / "app"
    tests_root = step_root / "tests"

    if step_root.exists():
        _exit_with_error(f"Step already exists: {step_name}")

    app_root.mkdir(parents=True, exist_ok=True)
    tests_root.mkdir(parents=True, exist_ok=True)

    input_name = str(schema.get("inputs", [{}])[0].get("name", "input"))
    output_name = str(schema.get("outputs", [{}])[0].get("name", "output"))

    (app_root / "__init__.py").write_text("", encoding="utf-8")
    (app_root / "config.py").write_text(
        "from pydantic_settings import BaseSettings, SettingsConfigDict\n\n\n"
        "class Settings(BaseSettings):\n"
        "    \"\"\"Runtime settings for the scaffolded step.\n\n"
        "    :param model_config: Prefix for environment variables.\n"
        "    \"\"\"\n\n"
        f"    model_config = SettingsConfigDict(env_prefix=\"{task.upper().replace('-', '_')}_STEP_\")\n",
        encoding="utf-8",
    )
    (app_root / "step.py").write_text(
        "from __future__ import annotations\n\n"
        "from typing import TYPE_CHECKING\n\n"
        "from inferflow_step_sdk.base import BaseStep\n"
        "from inferflow_step_sdk.models import InferRequest, InferResponse, MetadataTensor, Tensor\n\n"
        "if TYPE_CHECKING:\n"
        "    from app.config import Settings\n\n\n"
        f"class {task.title().replace('-', '').replace('_', '')}{implementation.title().replace('-', '').replace('_', '')}Step(BaseStep):\n"
        "    \"\"\"Scaffolded step implementation.\"\"\"\n\n"
        "    def __init__(self, settings: Settings) -> None:\n"
        "        self._settings = settings\n\n"
        "    @property\n"
        "    def name(self) -> str:\n"
        f"        return \"{step_name}\"\n\n"
        "    @property\n"
        "    def version(self) -> str:\n"
        "        return \"1\"\n\n"
        "    @property\n"
        "    def task(self) -> str:\n"
        f"        return \"{task}\"\n\n"
        "    @property\n"
        "    def implementation(self) -> str:\n"
        f"        return \"{implementation}\"\n\n"
        "    @property\n"
        "    def inputs(self) -> list[MetadataTensor]:\n"
        f"        return [MetadataTensor(name=\"{input_name}\", datatype=\"BYTES\", shape=[1])]\n\n"
        "    @property\n"
        "    def outputs(self) -> list[MetadataTensor]:\n"
        f"        return [MetadataTensor(name=\"{output_name}\", datatype=\"BYTES\", shape=[1])]\n\n"
        "    async def predict(self, request: InferRequest) -> InferResponse:\n"
        "        \"\"\"Implement model inference.\"\"\"\n"
        "        raise NotImplementedError(\"Implement predict() for this step\")\n",
        encoding="utf-8",
    )
    (app_root / "main.py").write_text(
        "import uvicorn\n"
        "from fastapi import FastAPI\n\n"
        "from app.config import Settings\n"
        "from app.step import "
        f"{task.title().replace('-', '').replace('_', '')}{implementation.title().replace('-', '').replace('_', '')}Step\n\n\n"
        "def create_app() -> FastAPI:\n"
        "    \"\"\"Create FastAPI app for this step.\n\n"
        "    :returns: FastAPI instance exposing KServe V2 endpoints.\n"
        "    \"\"\"\n"
        "    settings = Settings()\n"
        "    step = "
        f"{task.title().replace('-', '').replace('_', '')}{implementation.title().replace('-', '').replace('_', '')}Step(settings)\n"
        "    return step.build_app()\n\n\n"
        "app = create_app()\n\n"
        "if __name__ == \"__main__\":\n"
        "    uvicorn.run(\"app.main:app\", host=\"0.0.0.0\", port=8080, log_level=\"info\")\n",
        encoding="utf-8",
    )
    (tests_root / "test_step.py").write_text(
        "def test_scaffold_placeholder() -> None:\n"
        "    assert True\n",
        encoding="utf-8",
    )
    (step_root / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (step_root / "step.yaml").write_text(
        yaml.safe_dump(
            {
                "name": step_name,
                "version": "1",
                "task": task,
                "description": f"Scaffolded step for task {task}",
                "port": 8080,
                "inputs": schema.get("inputs", []),
                "outputs": schema.get("outputs", []),
                "env": {},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (step_root / "pyproject.toml").write_text(
        "[project]\n"
        f"name = \"step-{step_name}\"\n"
        "version = \"0.1.0\"\n"
        f"description = \"Inferflow step: {task} via {implementation}\"\n"
        "requires-python = \">=3.13\"\n"
        "dependencies = [\n"
        "  \"inferflow-step-sdk\",\n"
        "  \"pydantic-settings>=2.0\",\n"
        "  \"uvicorn[standard]>=0.30\",\n"
        "]\n\n"
        "[tool.uv]\npackage = false\n\n"
        "[tool.uv.sources]\n"
        "inferflow-step-sdk = { workspace = true }\n",
        encoding="utf-8",
    )
    (step_root / "Dockerfile").write_text(
        "FROM python:3.13-slim\n\n"
        "WORKDIR /app\n"
        "COPY --from=ghcr.io/astral-sh/uv:0.4.30 /uv /usr/local/bin/uv\n"
        "ENV UV_SYSTEM_PYTHON=1\n"
        "COPY pyproject.toml ./\n"
        "RUN uv pip install --no-cache -r pyproject.toml\n"
        "COPY app/ ./app/\n"
        "EXPOSE 8080\n"
        "CMD [\"python\", \"-m\", \"app.main\"]\n",
        encoding="utf-8",
    )

    console.print(f"[green]Scaffolded step {step_name} at {step_root}[/green]")


@step_app.command("test")
def step_test(name: str = typer.Argument(..., help="Step directory name.")) -> None:
    """Run pytest for one step.

    :param name: Step directory name.
    """
    repo_root = _repo_root()
    _, steps_root, _ = _default_dirs(repo_root)
    tests_root = steps_root / name / "tests"
    if not tests_root.exists():
        _exit_with_error(f"Step tests not found: {tests_root}")
    output = _run_command(["uv", "run", "pytest", str(tests_root), "-q"], cwd=repo_root)
    if output:
        console.print(output)


@step_app.command("build")
def step_build(name: str = typer.Argument(..., help="Step directory name.")) -> None:
    """Build step container image locally.

    :param name: Step directory name.
    """
    repo_root = _repo_root()
    _, steps_root, _ = _default_dirs(repo_root)
    step_root = steps_root / name
    version_file = step_root / "VERSION"
    if not version_file.exists():
        _exit_with_error(f"VERSION not found for step: {name}")
    version = version_file.read_text(encoding="utf-8").strip()

    image = f"ghcr.io/jgallego9/inferflow-step-{name}:v{version}"
    output = _run_command(
        [
            "docker",
            "buildx",
            "build",
            "--load",
            "-t",
            image,
            "-f",
            str(step_root / "Dockerfile"),
            str(step_root),
        ],
        cwd=repo_root,
    )
    console.print(output or f"Built image: {image}")


@step_app.command("push")
def step_push(
    name: str = typer.Argument(..., help="Step directory name."),
    bump: str | None = typer.Option(
        None,
        help="Optional semver bump before push (patch|minor|major).",
    ),
) -> None:
    """Push step image to registry and optionally bump VERSION.

    :param name: Step directory name.
    :param bump: Optional semver bump strategy.
    """
    repo_root = _repo_root()
    _, steps_root, _ = _default_dirs(repo_root)
    step_root = steps_root / name
    version_file = step_root / "VERSION"
    if not version_file.exists():
        _exit_with_error(f"VERSION not found for step: {name}")

    version = version_file.read_text(encoding="utf-8").strip()
    if bump:
        if bump not in {"patch", "minor", "major"}:
            _exit_with_error("--bump must be one of patch, minor, major")
        version = _bump_semver(version, bump)
        version_file.write_text(version + "\n", encoding="utf-8")
        console.print(f"[green]Updated VERSION to {version}[/green]")

    image = f"ghcr.io/jgallego9/inferflow-step-{name}:v{version}"
    _run_command(["docker", "push", image], cwd=repo_root)
    console.print(f"[green]Pushed {image}[/green]")


@step_app.command("show")
def step_show(
    name: str = typer.Argument(..., help="Step name."),
    url: str | None = typer.Option(None, help="Step URL base (default: inferred host)."),
) -> None:
    """Fetch live metadata from a running step endpoint.

    :param name: Step name.
    :param url: Optional base URL.
    """
    base = url or _infer_step_endpoint(name)
    data = _request_json("GET", f"{base}/v2/models/{name}")
    console.print(Syntax(json.dumps(data, indent=2), "json"))


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


@pipeline_app.command("new")
def pipeline_new(name: str = typer.Argument(..., help="Pipeline name.")) -> None:
    """Create a new pipeline scaffold.

    :param name: Pipeline name.
    """
    repo_root = _repo_root()
    _, _, pipelines_root = _default_dirs(repo_root)
    target_dir = pipelines_root / name
    pipeline_path = target_dir / "pipeline.yaml"
    if pipeline_path.exists():
        _exit_with_error(f"Pipeline already exists: {name}")

    target_dir.mkdir(parents=True, exist_ok=True)
    template = {
        "name": name,
        "version": "1.0",
        "description": f"Pipeline {name}",
        "trigger": {"type": "redis-stream", "stream": f"pipelines:{name}:jobs"},
        "steps": [
            {"id": "step-1", "task": "replace-me", "url": "http://replace-me:8000"},
        ],
    }
    pipeline_path.write_text(yaml.safe_dump(template, sort_keys=False), encoding="utf-8")
    console.print(f"[green]Created {pipeline_path}[/green]")


@pipeline_app.command("validate")
def pipeline_validate(name: str = typer.Argument(..., help="Pipeline directory name.")) -> None:
    """Validate task compatibility across sequential pipeline steps."""
    repo_root = _repo_root()
    steps = _pipeline_step_defs(repo_root, name)
    tasks_root, _, _ = _default_dirs(repo_root)
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


@pipeline_app.command("dev")
def pipeline_dev(name: str = typer.Argument(..., help="Pipeline name.")) -> None:
    """Start local compose services required by one pipeline.

    :param name: Pipeline name.
    """
    repo_root = _repo_root()
    step_defs = _pipeline_step_defs(repo_root, name)
    services = ["api-gateway", "worker", "redis", "qdrant"]

    for step in step_defs:
        parsed = urlparse(str(step.get("url", "")))
        host = parsed.hostname
        if host and host not in services:
            services.append(host)

    command = ["docker", "compose", "up", "-d", *services]
    output = _run_command(command, cwd=repo_root)
    console.print(output or f"Started services: {', '.join(services)}")


@pipeline_app.command("run")
def pipeline_run(
    name: str = typer.Argument(..., help="Pipeline name."),
    input_data: str = typer.Option(..., "--input", help="Input JSON or @file path."),
    detach: bool = typer.Option(False, help="Return job id without waiting."),
    api_url: str = typer.Option(DEFAULT_API_URL, help="Gateway API base URL."),
) -> None:
    """Run a pipeline through runtime API.

    :param name: Pipeline name.
    :param input_data: Inline JSON or file path.
    :param detach: Return immediately with job id.
    :param api_url: API base URL.
    """
    payload = _parse_json_input(input_data)
    run_payload = {"input": payload}

    run_urls = [
        f"{api_url}/v1/pipelines/{name}/run",
        f"{api_url}/v1/pipelines/{name}/jobs",
    ]
    response: dict[str, Any] | None = None

    for run_url in run_urls:
        try:
            response = _request_json("POST", run_url, run_payload)
            break
        except typer.Exit:
            response = None
            continue

    if response is None:
        _exit_with_error("Unable to start pipeline run on available endpoints")

    job_id = str(response.get("job_id") or response.get("id") or "")
    if not job_id:
        console.print(Syntax(json.dumps(response, indent=2), "json"))
        return

    console.print(f"[green]Started job {job_id}[/green]")
    if detach:
        return

    for _ in range(120):
        status = _request_json("GET", f"{api_url}/jobs/{job_id}")
        state = str(status.get("status", "unknown"))
        console.print(f"status={state}")
        if state.lower() in {"completed", "failed", "error"}:
            console.print(Syntax(json.dumps(status, indent=2), "json"))
            return
        time.sleep(1)

    _exit_with_error("Timed out waiting for job completion")


@pipeline_app.command("deploy")
def pipeline_deploy(
    name: str = typer.Argument(..., help="Pipeline name."),
    env: str = typer.Option("dev", help="Target environment key from inferflow.yaml."),
) -> None:
    """Deploy pipeline using environment strategy.

    :param name: Pipeline name.
    :param env: Environment key.
    """
    del name
    repo_root = _repo_root()
    config = load_inferflow_config(repo_root)
    target = config.environments.get(env)
    if target is None:
        _exit_with_error(f"Environment not found in inferflow.yaml: {env}")

    namespace = target.namespace or "inferflow"
    if target.deploy == "helm":
        values = target.helm_values or "infra/helm/inferflow/values.yaml"
        output = _run_command(
            [
                "helm",
                "upgrade",
                "--install",
                "inferflow",
                "infra/helm/inferflow",
                "--namespace",
                namespace,
                "--create-namespace",
                "-f",
                values,
            ],
            cwd=repo_root,
        )
        console.print(output)
        return

    if target.deploy == "argocd":
        if not target.argocd_app:
            _exit_with_error("argocd_app is required for deploy: argocd")
        output = _run_command(["argocd", "app", "sync", target.argocd_app], cwd=repo_root)
        console.print(output)
        return

    _exit_with_error(f"Unsupported deploy strategy: {target.deploy}")


@pipeline_app.command("status")
def pipeline_status(
    name: str = typer.Argument(..., help="Pipeline name."),
    env: str = typer.Option("dev", help="Target environment key."),
    api_url: str = typer.Option(DEFAULT_API_URL, help="Gateway API base URL."),
) -> None:
    """Show pipeline status from runtime API or Kubernetes.

    :param name: Pipeline name.
    :param env: Environment key.
    :param api_url: API base URL.
    """
    repo_root = _repo_root()
    try:
        data = _request_json("GET", f"{api_url}/v1/pipelines/{name}/status")
        console.print(Syntax(json.dumps(data, indent=2), "json"))
        return
    except typer.Exit:
        pass

    config = load_inferflow_config(repo_root)
    target = config.environments.get(env)
    namespace = target.namespace if target else "inferflow"

    output = _run_command(
        [
            "kubectl",
            "get",
            "deploy",
            "-n",
            namespace,
            "-l",
            f"inferflow.io/pipeline={name}",
            "-o",
            "wide",
        ],
        cwd=repo_root,
    )
    console.print(output)


@pipeline_app.command("logs")
def pipeline_logs(
    name: str = typer.Argument(..., help="Pipeline name."),
    step: str = typer.Option(..., "--step", help="Step ID label."),
    env: str = typer.Option("dev", help="Target environment key."),
    follow: bool = typer.Option(False, help="Follow logs."),
) -> None:
    """Stream logs for one pipeline step.

    :param name: Pipeline name.
    :param step: Step ID label.
    :param env: Environment key.
    :param follow: Whether to follow logs.
    """
    repo_root = _repo_root()
    config = load_inferflow_config(repo_root)
    target = config.environments.get(env)
    namespace = target.namespace if target else "inferflow"

    command = [
        "kubectl",
        "logs",
        "-n",
        namespace,
        "-l",
        f"inferflow.io/pipeline={name},inferflow.io/step={step}",
        "--tail",
        "200",
    ]
    if follow:
        command.append("-f")
    output = _run_command(command, cwd=repo_root)
    console.print(output)


@pipeline_app.command("scale")
def pipeline_scale(
    name: str = typer.Argument(..., help="Pipeline name."),
    step: str = typer.Option(..., "--step", help="Step ID label."),
    replicas: int = typer.Option(..., "--replicas", min=1, help="Replica count."),
    env: str = typer.Option("dev", help="Target environment key."),
) -> None:
    """Scale one pipeline step deployment.

    :param name: Pipeline name.
    :param step: Step ID label.
    :param replicas: Replica count.
    :param env: Environment key.
    """
    repo_root = _repo_root()
    config = load_inferflow_config(repo_root)
    target = config.environments.get(env)
    namespace = target.namespace if target else "inferflow"

    output = _run_command(
        [
            "kubectl",
            "scale",
            "deploy",
            "-n",
            namespace,
            "-l",
            f"inferflow.io/pipeline={name},inferflow.io/step={step}",
            f"--replicas={replicas}",
        ],
        cwd=repo_root,
    )
    console.print(output)


@pipeline_app.command("rollback")
def pipeline_rollback(
    name: str = typer.Argument(..., help="Pipeline name (informational)."),
    env: str = typer.Option("dev", help="Target environment key."),
    revision: int = typer.Option(0, help="Helm revision to roll back to (0 = previous)."),
) -> None:
    """Rollback Helm release for runtime chart.

    :param name: Pipeline name.
    :param env: Environment key.
    :param revision: Target Helm revision.
    """
    del name
    repo_root = _repo_root()
    config = load_inferflow_config(repo_root)
    target = config.environments.get(env)
    namespace = target.namespace if target else "inferflow"

    if revision > 0:
        command = ["helm", "rollback", "inferflow", str(revision), "-n", namespace]
    else:
        command = ["helm", "rollback", "inferflow", "-n", namespace]

    output = _run_command(command, cwd=repo_root)
    console.print(output)


@pipeline_app.command("metrics")
def pipeline_metrics(
    name: str = typer.Argument(..., help="Pipeline name."),
    env: str = typer.Option("dev", help="Target environment key."),
    api_url: str = typer.Option(DEFAULT_API_URL, help="Gateway API base URL."),
) -> None:
    """Show runtime metrics payload for one pipeline.

    :param name: Pipeline name.
    :param env: Environment key.
    :param api_url: API base URL.
    """
    del env
    data = _request_json("GET", f"{api_url}/v1/pipelines/{name}/metrics")
    console.print(Syntax(json.dumps(data, indent=2), "json"))


@models_app.command("prefetch")
def models_prefetch(name: str = typer.Argument(..., help="Pipeline name.")) -> None:
    """Probe step readiness to warm model caches.

    :param name: Pipeline name.
    """
    repo_root = _repo_root()
    step_defs = _pipeline_step_defs(repo_root, name)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True) as progress:
        for step in step_defs:
            step_id = str(step.get("id", "step"))
            url = str(step.get("url", "")).rstrip("/")
            if not url:
                continue
            task_id = progress.add_task(f"Checking {step_id}", total=None)
            ready_url = f"{url}/v2/health/ready"
            for _ in range(20):
                try:
                    with httpx.Client(timeout=3.0) as client:
                        response = client.get(ready_url)
                        if response.status_code == 200:
                            progress.update(task_id, description=f"{step_id} ready")
                            break
                except Exception:
                    pass
                time.sleep(1)
            progress.remove_task(task_id)

    console.print(f"[green]Model prefetch checks completed for pipeline {name}[/green]")


@models_app.command("status")
def models_status(name: str = typer.Argument(..., help="Pipeline name.")) -> None:
    """Show per-step model metadata status.

    :param name: Pipeline name.
    """
    repo_root = _repo_root()
    step_defs = _pipeline_step_defs(repo_root, name)

    table = Table(title=f"Model status for {name}")
    table.add_column("Step")
    table.add_column("Model")
    table.add_column("Status")

    for step in step_defs:
        step_id = str(step.get("id", "step"))
        url = str(step.get("url", "")).rstrip("/")
        if not url:
            table.add_row(step_id, "-", "missing url")
            continue

        metadata_url = f"{url}/v2/models/{step_id}"
        try:
            data = _request_json("GET", metadata_url)
            model_name = str(data.get("name", step_id))
            table.add_row(step_id, model_name, "ready")
        except typer.Exit:
            table.add_row(step_id, "-", "unreachable")

    console.print(table)


@models_app.command("clear")
def models_clear(name: str = typer.Argument(..., help="Pipeline name.")) -> None:
    """Clear local model cache path for a pipeline.

    :param name: Pipeline name.
    """
    repo_root = _repo_root()
    cache_path = repo_root / ".cache" / "inferflow" / "models" / name

    if not cache_path.exists():
        console.print(f"[yellow]No local cache found at {cache_path}[/yellow]")
        return

    confirmed = questionary.confirm(
        f"Delete local cache directory {cache_path}?",
        default=False,
    ).ask()
    if not confirmed:
        console.print("Aborted.")
        return

    _run_command(["rm", "-rf", str(cache_path)], cwd=repo_root)
    console.print(f"[green]Deleted {cache_path}[/green]")


@job_app.command("status")
def job_status(
    job_id: str = typer.Argument(..., help="Job identifier."),
    api_url: str = typer.Option(DEFAULT_API_URL, help="Gateway API base URL."),
) -> None:
    """Show status payload for one job.

    :param job_id: Job identifier.
    :param api_url: API base URL.
    """
    data = _request_json("GET", f"{api_url}/jobs/{job_id}")
    console.print(Syntax(json.dumps(data, indent=2), "json"))


@job_app.command("result")
def job_result(
    job_id: str = typer.Argument(..., help="Job identifier."),
    api_url: str = typer.Option(DEFAULT_API_URL, help="Gateway API base URL."),
) -> None:
    """Show result payload for one job.

    :param job_id: Job identifier.
    :param api_url: API base URL.
    """
    urls = [f"{api_url}/jobs/{job_id}/result", f"{api_url}/jobs/{job_id}"]
    for url in urls:
        try:
            data = _request_json("GET", url)
            result = data.get("result", data)
            console.print(Syntax(json.dumps(result, indent=2), "json"))
            return
        except typer.Exit:
            continue
    _exit_with_error(f"No result endpoint available for job {job_id}")


if __name__ == "__main__":
    app()
