# Contributing

Thanks for contributing to **Blender MCP**.

## Git Flow

This repository uses Git Flow:

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready releases only |
| `develop` | Integration branch for the next release |
| `feature/*` | New features (branch from `develop`) |
| `release/*` | Release preparation (branch from `develop`) |
| `hotfix/*` | Urgent production fixes (branch from `main`) |

### Feature workflow

```bash
git checkout develop
git pull origin develop
git checkout -b feature/short-description
# ... work ...
uv sync
uv run pytest
git push -u origin HEAD
```

Open a pull request into **`develop`**.

### Release workflow

```bash
git checkout develop
git checkout -b release/x.y.z
# bump version in pyproject.toml + src/blender_mcp/__init__.py
# update CHANGELOG.md, final fixes
# PR into main and develop after release
```

### Cutting a release (Actions)

Preferred: run **Release** (`.github/workflows/release.yml`) from the Actions tab:

1. Choose branch `main` (Git Flow)
2. Enter version without `v` (e.g. `0.1.1`)
3. Workflow bumps `pyproject.toml` + `__version__`, updates `CHANGELOG.md`, tags `vX.Y.Z`, creates the GitHub Release, then dispatches **CD**

**CD** (`.github/workflows/cd.yml`) builds wheels, attaches assets, refreshes Pages, and publishes to PyPI when repo variable `PUBLISH_PYPI=true` and secret `PYPI_API_TOKEN` are set.

Optional: set secret `RELEASE_TOKEN` (PAT with `contents` + `actions`) so tag pushes and workflow dispatches always chain reliably.

Manual tag alternative:

```bash
git checkout main
git pull
git tag v0.1.0
git push origin v0.1.0
```

### Hotfix workflow

```bash
git checkout main
git checkout -b hotfix/short-description
# fix, test, update CHANGELOG.md
# PR into main and develop
```

## Tooling

- Use **uv** only (`uv sync`, `uv run`)
- Python **3.11+** (pinned in `.python-version`)
- Run before opening a PR:

```bash
uv sync
uv run pytest
uv run ruff check src tests
```

## Code guidelines

- Keep the MCP server free of `bpy` imports
- Blender API work belongs in `blender_addon/`
- Prefer structured tool results over unstructured text
- Do not commit secrets, API keys, or `.env` files
- Do not present unimplemented tools as complete

## Pull requests

- Target the correct base branch (`develop` for features)
- Fill out `.github/PULL_REQUEST_TEMPLATE.md`
- Keep PRs focused and reviewable
- Link related issues

## Issues

Use the templates under `.github/ISSUE_TEMPLATE/`.

## License

By contributing, you agree that your contributions are licensed under the MIT License.
