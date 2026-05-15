# Contributing

Thanks for contributing to Inferflow MLOps.

## Workflow

1. Fork the repository.
2. Create a branch from `main` using one of these prefixes:
   - `feat/<short-topic>`
   - `fix/<short-topic>`
   - `step/<task-impl>`
3. Implement the change with focused commits.
4. Run checks locally:

```bash
uv sync --all-packages --dev
make ci
```

5. Open a pull request using the PR template.

## Commit convention

Use Conventional Commits:

- `feat: ...`
- `fix: ...`
- `chore: ...`
- `docs: ...`
- `refactor: ...`
- `test: ...`

Breaking changes:

- `feat!: ...` or include `BREAKING CHANGE:` in the body.

## Pre-commit setup

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

## Pull request expectations

- Keep PRs small and reviewable.
- Include tests for behavioral changes.
- Update docs for user-facing changes.
- Link the issue being solved.

## Adding a new step

1. Add task schema in `tasks/<task>/schema.json`.
2. Add step package in `steps/<task>-<impl>/`.
3. Add tests in `steps/<task>-<impl>/tests/`.
4. Add or update `VERSION`.
5. Validate with `make ci`.
